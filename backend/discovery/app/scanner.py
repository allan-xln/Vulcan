from __future__ import annotations

import asyncio
import math
import re
import socket
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network
from itertools import islice
from typing import Iterable


class NetworkScopeError(ValueError):
    pass


@dataclass(frozen=True)
class ScanPolicy:
    allowed_networks: tuple[str, ...]
    denied_networks: tuple[str, ...] = ()
    excluded_addresses: tuple[str, ...] = ()
    allowed_protocols: tuple[str, ...] = ("icmp", "dns")
    allowed_tcp_ports: tuple[int, ...] = ()
    concurrency: int = 8
    timeout_ms: int = 750
    max_targets: int = 256


@dataclass(frozen=True)
class TargetObservation:
    ip_address: str
    present: bool
    hostname: str | None = None
    latency_ms: float | None = None
    open_ports: tuple[int, ...] = ()
    errors: tuple[str, ...] = field(default_factory=tuple)


def build_targets(
    policy: ScanPolicy,
    *,
    allow_public_networks: bool = False,
    global_max_targets: int = 256,
) -> list[str]:
    if not policy.allowed_networks:
        raise NetworkScopeError("discovery requires at least one allowed network")

    allowed = [ip_network(value, strict=True) for value in policy.allowed_networks]
    denied = [ip_network(value, strict=True) for value in policy.denied_networks]
    excluded = {ip_address(value) for value in policy.excluded_addresses}

    if not allow_public_networks:
        public = [
            str(network)
            for network in allowed
            if not (network.is_private or network.is_loopback or network.is_link_local)
        ]
        if public:
            raise NetworkScopeError(f"public networks are blocked: {', '.join(public)}")

    effective_limit = min(policy.max_targets, global_max_targets)
    if effective_limit < 1:
        raise NetworkScopeError("max target limit must be positive")

    targets: list[str] = []
    for network in allowed:
        for address in islice(network.hosts(), effective_limit + 1):
            if address in excluded:
                continue
            if any(address in denied_network for denied_network in denied):
                continue
            targets.append(str(address))
            if len(targets) > effective_limit:
                raise NetworkScopeError(
                    f"allowed scope exceeds the limit of {effective_limit} targets"
                )
    return targets


def effective_tcp_ports(policy: ScanPolicy, globally_allowed_ports: Iterable[int]) -> tuple[int, ...]:
    if "tcp_connect" not in policy.allowed_protocols:
        return ()
    global_allowlist = set(globally_allowed_ports)
    requested = tuple(sorted(set(policy.allowed_tcp_ports)))
    blocked = [port for port in requested if port not in global_allowlist]
    if blocked:
        raise NetworkScopeError(
            f"TCP ports outside the worker allowlist: {', '.join(str(port) for port in blocked)}"
        )
    return requested


def effective_timeout_ms(policy: ScanPolicy, global_max_timeout_ms: int) -> int:
    if global_max_timeout_ms < 100:
        raise NetworkScopeError("global timeout limit must be at least 100 ms")
    return max(100, min(policy.timeout_ms, global_max_timeout_ms))


async def _reverse_dns(address: str, timeout_seconds: float) -> tuple[str | None, str | None]:
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(socket.gethostbyaddr, address),
            timeout=timeout_seconds,
        )
        return result[0], None
    except (TimeoutError, OSError, socket.herror):
        return None, "reverse_dns_unavailable"


async def _ping(address: str, timeout_seconds: float) -> tuple[bool, float | None, str | None]:
    flag = "-6" if isinstance(ip_address(address), IPv6Address) else "-4"
    try:
        process = await asyncio.create_subprocess_exec(
            "ping",
            flag,
            "-c",
            "1",
            "-W",
            str(max(1, math.ceil(timeout_seconds))),
            address,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds + 1)
    except (FileNotFoundError, TimeoutError):
        return False, None, "icmp_unavailable"
    if process.returncode != 0:
        return False, None, None
    match = re.search(rb"time[=<]([0-9.]+)\s*ms", stdout)
    latency = float(match.group(1)) if match else None
    return True, latency, None


async def _tcp_connect(address: str, port: int, timeout_seconds: float) -> bool:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(address, port),
            timeout=timeout_seconds,
        )
        del reader
        writer.close()
        await writer.wait_closed()
        return True
    except (TimeoutError, OSError):
        return False


async def scan_target(
    address: str,
    *,
    protocols: tuple[str, ...],
    tcp_ports: tuple[int, ...],
    timeout_ms: int,
) -> TargetObservation:
    timeout_seconds = timeout_ms / 1000
    present = False
    latency_ms: float | None = None
    hostname: str | None = None
    errors: list[str] = []
    open_ports: list[int] = []

    if "icmp" in protocols:
        present, latency_ms, error = await _ping(address, timeout_seconds)
        if error:
            errors.append(error)

    if "dns" in protocols or "reverse_dns" in protocols:
        hostname, error = await _reverse_dns(address, timeout_seconds)
        if error:
            errors.append(error)

    if tcp_ports:
        results = await asyncio.gather(
            *(_tcp_connect(address, port, timeout_seconds) for port in tcp_ports)
        )
        open_ports = [port for port, is_open in zip(tcp_ports, results, strict=True) if is_open]
        present = present or bool(open_ports)

    return TargetObservation(
        ip_address=address,
        present=present,
        hostname=hostname,
        latency_ms=latency_ms,
        open_ports=tuple(open_ports),
        errors=tuple(errors),
    )


async def scan_policy(
    policy: ScanPolicy,
    *,
    allow_public_networks: bool,
    global_max_targets: int,
    global_max_concurrency: int,
    global_max_timeout_ms: int,
    globally_allowed_tcp_ports: tuple[int, ...],
) -> list[TargetObservation]:
    targets = build_targets(
        policy,
        allow_public_networks=allow_public_networks,
        global_max_targets=global_max_targets,
    )
    ports = effective_tcp_ports(policy, globally_allowed_tcp_ports)
    timeout_ms = effective_timeout_ms(policy, global_max_timeout_ms)
    semaphore = asyncio.Semaphore(min(policy.concurrency, global_max_concurrency))

    async def limited_scan(address: str) -> TargetObservation:
        async with semaphore:
            return await scan_target(
                address,
                protocols=policy.allowed_protocols,
                tcp_ports=ports,
                timeout_ms=timeout_ms,
            )

    return await asyncio.gather(*(limited_scan(address) for address in targets))

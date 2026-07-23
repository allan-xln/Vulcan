import pytest

from app.scanner import (
    NetworkScopeError,
    ScanPolicy,
    build_targets,
    effective_tcp_ports,
    effective_timeout_ms,
)


def test_build_targets_applies_denylist_and_exclusions() -> None:
    targets = build_targets(
        ScanPolicy(
            allowed_networks=("10.20.30.0/29",),
            denied_networks=("10.20.30.4/31",),
            excluded_addresses=("10.20.30.2",),
            max_targets=8,
        ),
        global_max_targets=16,
    )

    assert targets == ["10.20.30.1", "10.20.30.3", "10.20.30.6"]


def test_build_targets_blocks_public_networks_by_default() -> None:
    with pytest.raises(NetworkScopeError, match="public networks are blocked"):
        build_targets(
            ScanPolicy(allowed_networks=("8.8.8.0/30",), max_targets=4),
            allow_public_networks=False,
            global_max_targets=16,
        )


def test_build_targets_rejects_scope_over_global_limit() -> None:
    with pytest.raises(NetworkScopeError, match="exceeds the limit"):
        build_targets(
            ScanPolicy(allowed_networks=("10.10.10.0/24",), max_targets=256),
            global_max_targets=32,
        )


def test_tcp_connect_requires_protocol_and_global_allowlist() -> None:
    disabled = effective_tcp_ports(
        ScanPolicy(
            allowed_networks=("10.0.0.0/30",),
            allowed_protocols=("icmp",),
            allowed_tcp_ports=(22,),
        ),
        (22, 443),
    )
    assert disabled == ()

    with pytest.raises(NetworkScopeError, match="outside the worker allowlist"):
        effective_tcp_ports(
            ScanPolicy(
                allowed_networks=("10.0.0.0/30",),
                allowed_protocols=("tcp_connect",),
                allowed_tcp_ports=(23,),
            ),
            (22, 443),
        )

    allowed = effective_tcp_ports(
        ScanPolicy(
            allowed_networks=("10.0.0.0/30",),
            allowed_protocols=("tcp_connect",),
            allowed_tcp_ports=(443, 22),
        ),
        (22, 443),
    )
    assert allowed == (22, 443)


def test_timeout_is_capped_by_the_worker() -> None:
    policy = ScanPolicy(allowed_networks=("10.0.0.0/30",), timeout_ms=8000)

    assert effective_timeout_ms(policy, 2000) == 2000

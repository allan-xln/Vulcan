from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from typing import Iterable
from uuid import UUID


@dataclass(frozen=True)
class NormalizedEventRecord:
    normalized_event_id: UUID
    tenant_id: UUID
    workstation_id: UUID | None
    agent_installation_id: UUID | None
    normalized_event_type: str
    occurred_at: datetime
    session_id: str | None
    username: str | None
    app_name: str | None
    process_name: str | None
    idle_threshold_seconds: int | None


@dataclass(frozen=True)
class SessionSliceFact:
    tenant_id: UUID
    workstation_id: UUID | None
    agent_installation_id: UUID | None
    session_id: str
    username: str | None
    start_normalized_event_id: UUID
    end_normalized_event_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    start_event_type: str
    end_event_type: str | None
    closure_reason: str
    is_open: bool


@dataclass(frozen=True)
class IdleWindowFact:
    tenant_id: UUID
    workstation_id: UUID | None
    agent_installation_id: UUID | None
    session_id: str
    start_normalized_event_id: UUID
    end_normalized_event_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    idle_threshold_seconds: int | None
    closure_reason: str
    is_open: bool


@dataclass(frozen=True)
class ApplicationUsageFact:
    tenant_id: UUID
    workstation_id: UUID | None
    agent_installation_id: UUID | None
    session_id: str | None
    app_name: str
    process_name: str | None
    focus_start_normalized_event_id: UUID
    focus_end_normalized_event_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    end_reason: str
    is_open: bool


SESSION_START_TYPES = {"session_login", "session_unlock"}
SESSION_END_TYPES = {"session_lock", "session_logout"}
IDLE_START_TYPES = {"idle_start"}
IDLE_END_TYPES = {"idle_end"}
APP_FOCUS_TYPES = {"foreground_application_change"}
APP_USAGE_END_TYPES = {"foreground_application_change", "idle_start", "session_lock", "session_logout"}


def _duration_seconds(started_at: datetime, ended_at: datetime | None) -> int | None:
    if ended_at is None:
        return None
    return max(0, int((ended_at - started_at).total_seconds()))


def derive_session_slices(events: Iterable[NormalizedEventRecord]) -> list[SessionSliceFact]:
    facts: list[SessionSliceFact] = []
    sorted_events = sorted(
        (event for event in events if event.session_id and event.normalized_event_type in SESSION_START_TYPES | SESSION_END_TYPES),
        key=lambda item: (item.tenant_id, item.workstation_id or UUID(int=0), item.session_id or "", item.occurred_at, item.normalized_event_id),
    )

    for (_, workstation_id, session_id), grouped_events_iter in groupby(
        sorted_events,
        key=lambda item: (item.tenant_id, item.workstation_id, item.session_id),
    ):
        open_start: NormalizedEventRecord | None = None
        grouped_events = list(grouped_events_iter)

        for event in grouped_events:
            if event.normalized_event_type in SESSION_START_TYPES:
                if open_start is not None:
                    facts.append(
                        SessionSliceFact(
                            tenant_id=open_start.tenant_id,
                            workstation_id=open_start.workstation_id,
                            agent_installation_id=open_start.agent_installation_id,
                            session_id=open_start.session_id or "",
                            username=open_start.username,
                            start_normalized_event_id=open_start.normalized_event_id,
                            end_normalized_event_id=event.normalized_event_id,
                            started_at=open_start.occurred_at,
                            ended_at=event.occurred_at,
                            duration_seconds=_duration_seconds(open_start.occurred_at, event.occurred_at),
                            start_event_type=open_start.normalized_event_type,
                            end_event_type=event.normalized_event_type,
                            closure_reason="superseded_by_new_session_start",
                            is_open=False,
                        )
                    )
                open_start = event
                continue

            if event.normalized_event_type in SESSION_END_TYPES and open_start is not None:
                facts.append(
                    SessionSliceFact(
                        tenant_id=open_start.tenant_id,
                        workstation_id=open_start.workstation_id,
                        agent_installation_id=open_start.agent_installation_id,
                        session_id=open_start.session_id or "",
                        username=open_start.username,
                        start_normalized_event_id=open_start.normalized_event_id,
                        end_normalized_event_id=event.normalized_event_id,
                        started_at=open_start.occurred_at,
                        ended_at=event.occurred_at,
                        duration_seconds=_duration_seconds(open_start.occurred_at, event.occurred_at),
                        start_event_type=open_start.normalized_event_type,
                        end_event_type=event.normalized_event_type,
                        closure_reason="explicit_session_end",
                        is_open=False,
                    )
                )
                open_start = None

        if open_start is not None:
            facts.append(
                SessionSliceFact(
                    tenant_id=open_start.tenant_id,
                    workstation_id=open_start.workstation_id,
                    agent_installation_id=open_start.agent_installation_id,
                    session_id=open_start.session_id or "",
                    username=open_start.username,
                    start_normalized_event_id=open_start.normalized_event_id,
                    end_normalized_event_id=None,
                    started_at=open_start.occurred_at,
                    ended_at=None,
                    duration_seconds=None,
                    start_event_type=open_start.normalized_event_type,
                    end_event_type=None,
                    closure_reason="open_session",
                    is_open=True,
                )
            )

    return facts


def derive_idle_windows(events: Iterable[NormalizedEventRecord]) -> list[IdleWindowFact]:
    facts: list[IdleWindowFact] = []
    sorted_events = sorted(
        (event for event in events if event.session_id and event.normalized_event_type in IDLE_START_TYPES | IDLE_END_TYPES | SESSION_END_TYPES),
        key=lambda item: (item.tenant_id, item.workstation_id or UUID(int=0), item.session_id or "", item.occurred_at, item.normalized_event_id),
    )

    for _, grouped_events_iter in groupby(
        sorted_events,
        key=lambda item: (item.tenant_id, item.workstation_id, item.session_id),
    ):
        open_start: NormalizedEventRecord | None = None
        grouped_events = list(grouped_events_iter)

        for event in grouped_events:
            if event.normalized_event_type in IDLE_START_TYPES:
                if open_start is not None:
                    facts.append(
                        IdleWindowFact(
                            tenant_id=open_start.tenant_id,
                            workstation_id=open_start.workstation_id,
                            agent_installation_id=open_start.agent_installation_id,
                            session_id=open_start.session_id or "",
                            start_normalized_event_id=open_start.normalized_event_id,
                            end_normalized_event_id=event.normalized_event_id,
                            started_at=open_start.occurred_at,
                            ended_at=event.occurred_at,
                            duration_seconds=_duration_seconds(open_start.occurred_at, event.occurred_at),
                            idle_threshold_seconds=open_start.idle_threshold_seconds,
                            closure_reason="superseded_by_new_idle_start",
                            is_open=False,
                        )
                    )
                open_start = event
                continue

            if open_start is None:
                continue

            if event.normalized_event_type in IDLE_END_TYPES:
                closure_reason = "explicit_idle_end"
            elif event.normalized_event_type in SESSION_END_TYPES:
                closure_reason = "closed_by_session_end"
            else:
                continue

            facts.append(
                IdleWindowFact(
                    tenant_id=open_start.tenant_id,
                    workstation_id=open_start.workstation_id,
                    agent_installation_id=open_start.agent_installation_id,
                    session_id=open_start.session_id or "",
                    start_normalized_event_id=open_start.normalized_event_id,
                    end_normalized_event_id=event.normalized_event_id,
                    started_at=open_start.occurred_at,
                    ended_at=event.occurred_at,
                    duration_seconds=_duration_seconds(open_start.occurred_at, event.occurred_at),
                    idle_threshold_seconds=open_start.idle_threshold_seconds,
                    closure_reason=closure_reason,
                    is_open=False,
                )
            )
            open_start = None

        if open_start is not None:
            facts.append(
                IdleWindowFact(
                    tenant_id=open_start.tenant_id,
                    workstation_id=open_start.workstation_id,
                    agent_installation_id=open_start.agent_installation_id,
                    session_id=open_start.session_id or "",
                    start_normalized_event_id=open_start.normalized_event_id,
                    end_normalized_event_id=None,
                    started_at=open_start.occurred_at,
                    ended_at=None,
                    duration_seconds=None,
                    idle_threshold_seconds=open_start.idle_threshold_seconds,
                    closure_reason="open_idle_window",
                    is_open=True,
                )
            )

    return facts


def derive_application_usage_facts(events: Iterable[NormalizedEventRecord]) -> list[ApplicationUsageFact]:
    facts: list[ApplicationUsageFact] = []
    sorted_events = sorted(
        (event for event in events if event.normalized_event_type in APP_FOCUS_TYPES | APP_USAGE_END_TYPES),
        key=lambda item: (
            item.tenant_id,
            item.workstation_id or UUID(int=0),
            item.session_id or "",
            item.occurred_at,
            item.normalized_event_id,
        ),
    )

    for _, grouped_events_iter in groupby(
        sorted_events,
        key=lambda item: (item.tenant_id, item.workstation_id, item.session_id),
    ):
        open_focus: NormalizedEventRecord | None = None
        grouped_events = list(grouped_events_iter)

        for event in grouped_events:
            if event.normalized_event_type == "foreground_application_change":
                if open_focus is not None:
                    facts.append(
                        ApplicationUsageFact(
                            tenant_id=open_focus.tenant_id,
                            workstation_id=open_focus.workstation_id,
                            agent_installation_id=open_focus.agent_installation_id,
                            session_id=open_focus.session_id,
                            app_name=open_focus.app_name or "unknown",
                            process_name=open_focus.process_name,
                            focus_start_normalized_event_id=open_focus.normalized_event_id,
                            focus_end_normalized_event_id=event.normalized_event_id,
                            started_at=open_focus.occurred_at,
                            ended_at=event.occurred_at,
                            duration_seconds=_duration_seconds(open_focus.occurred_at, event.occurred_at),
                            end_reason="app_switch",
                            is_open=False,
                        )
                    )
                open_focus = event
                continue

            if open_focus is None:
                continue

            if event.normalized_event_type == "idle_start":
                end_reason = "idle_start"
            elif event.normalized_event_type in SESSION_END_TYPES:
                end_reason = "session_end"
            else:
                continue

            facts.append(
                ApplicationUsageFact(
                    tenant_id=open_focus.tenant_id,
                    workstation_id=open_focus.workstation_id,
                    agent_installation_id=open_focus.agent_installation_id,
                    session_id=open_focus.session_id,
                    app_name=open_focus.app_name or "unknown",
                    process_name=open_focus.process_name,
                    focus_start_normalized_event_id=open_focus.normalized_event_id,
                    focus_end_normalized_event_id=event.normalized_event_id,
                    started_at=open_focus.occurred_at,
                    ended_at=event.occurred_at,
                    duration_seconds=_duration_seconds(open_focus.occurred_at, event.occurred_at),
                    end_reason=end_reason,
                    is_open=False,
                )
            )
            open_focus = None

        if open_focus is not None:
            facts.append(
                ApplicationUsageFact(
                    tenant_id=open_focus.tenant_id,
                    workstation_id=open_focus.workstation_id,
                    agent_installation_id=open_focus.agent_installation_id,
                    session_id=open_focus.session_id,
                    app_name=open_focus.app_name or "unknown",
                    process_name=open_focus.process_name,
                    focus_start_normalized_event_id=open_focus.normalized_event_id,
                    focus_end_normalized_event_id=None,
                    started_at=open_focus.occurred_at,
                    ended_at=None,
                    duration_seconds=None,
                    end_reason="open_focus_window",
                    is_open=True,
                )
            )

    return facts


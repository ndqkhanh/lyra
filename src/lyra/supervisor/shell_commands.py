"""
Fleet CLI — terminal commands for managing the Lyra agent fleet.

Usage::

    lyra fleet start agent_config.yaml
    lyra fleet status
    lyra fleet kill <session_id>
    lyra fleet logs <session_id>
    lyra fleet top
    lyra fleet stop

Each command is a function in this module, registered under the ``lyra fleet``
subcommand group via the ``cmd`` entry point or imported directly.
"""

from __future__ import annotations

import datetime
import shutil
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

from lyra.supervisor.fleet import AgentConfig, FleetOrchestrator, FleetStatus, SessionProgress

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_time(dt: datetime.datetime | None) -> str:
    """Format a datetime for display, or '--' if None."""
    if dt is None:
        return " -- "
    return dt.strftime("%H:%M:%S")


def _fmt_duration(seconds: float) -> str:
    """Format a duration in seconds to human-readable."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h{minutes:02d}m{secs:02d}s"


def _fmt_cost(cost: float) -> str:
    """Format cost, adding unit."""
    if cost < 1.0:
        return f"{cost * 1000:.0f}m"
    return f"{cost:.2f}"


def _term_width() -> int:
    """Return terminal width (default 80)."""
    try:
        return shutil.get_terminal_size().columns
    except (ImportError, ValueError):
        return 80


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


def cmd_fleet_start(
    fleet: FleetOrchestrator,
    agent_config: AgentConfig,
) -> str:
    """Start a new agent session in the fleet.

    Args:
        fleet: The FleetOrchestrator instance.
        agent_config: Configuration for the agent to spawn.

    Returns:
        A human-readable result string.
    """
    try:
        session_id = fleet.spawn_agent(agent_config)
        return (
            f"Agent '{agent_config.name}' spawned successfully.\n"
            f"Session ID: {session_id}"
        )
    except RuntimeError as exc:
        return f"ERROR: {exc}"
    except Exception as exc:
        logger.exception("fleet_start_failed", name=agent_config.name)
        return f"ERROR: Failed to start agent: {exc}"


def cmd_fleet_stop(fleet: FleetOrchestrator) -> str:
    """Stop all active sessions in the fleet.

    Args:
        fleet: The FleetOrchestrator instance.

    Returns:
        A human-readable result string.
    """
    try:
        status = fleet.fleet_status()
        stopped: list[str] = []
        for sp in status.sessions:
            try:
                fleet.kill_session(sp.session_id)
                stopped.append(sp.session_id)
            except Exception as exc:
                logger.warning(
                    "fleet_stop_partial_fail",
                    session_id=sp.session_id,
                    error=str(exc),
                )

        if stopped:
            return f"Stopped {len(stopped)} session(s)."
        return "No active sessions to stop."
    except Exception as exc:
        return f"ERROR: {exc}"


def cmd_fleet_status(fleet: FleetOrchestrator) -> str:
    """Render a table of all sessions in the fleet.

    Args:
        fleet: The FleetOrchestrator instance.

    Returns:
        A formatted table string.
    """
    try:
        status = fleet.fleet_status()
    except Exception as exc:
        return f"ERROR: {exc}"

    if status.total_sessions == 0:
        return "Fleet is empty. Use 'lyra fleet start' to spawn an agent."

    lines: list[str] = []
    width = _term_width()

    # Header
    now = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"LYRA FLEET STATUS  |  {now}")
    lines.append(f"Total: {status.total_sessions}  "
                 f"Active: {status.active_count}  "
                 f"Stagnant: {status.stagnant_count}  "
                 f"GPU: {status.gpu_allocated_count}")
    lines.append("")

    if width < 80:
        # Narrow terminal: condensed view
        line_fmt = "{sel} {sid:12s} {st:4s} {chk:3s} {cost:6s} {stg}"
        lines.append(line_fmt.format(
            sel=" ", sid="SESSION", st="ST", chk="CK", cost="COST", stg="STG"
        ))
        lines.append("-" * width)
        for sp in status.sessions:
            state_str = _session_state_char(fleet, sp.session_id)
            chk_str = f"{sp.checkpoint_count:2d}" if sp.checkpoint_count else " 0"
            stg_str = f"L{sp.stagnation_level}" if sp.stagnation_level else "  "
            lines.append(line_fmt.format(
                sel=" ",
                sid=sp.session_id[:12],
                st=state_str,
                chk=chk_str,
                cost=_fmt_cost(sp.cost_estimate),
                stg=stg_str,
            ))
    else:
        # Wide terminal: full table
        line_fmt = (
            "{sel} {sid:14s} {name:20s} {st:8s} {upt:10s} "
            "{chk:5s} {cost:8s} {stg:12s} {gpu:4s}"
        )
        header = line_fmt.format(
            sel=" ",
            sid="SESSION ID",
            name="NAME",
            st="STATE",
            upt="UPTIME",
            chk="CHK",
            cost="COST",
            stg="STAGNATION",
            gpu="GPU",
        )
        lines.append(header)
        lines.append("-" * width)

        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)

        for sp in status.sessions:
            info = fleet.get_session_info(sp.session_id)
            name = info.name[:20] if info else sp.session_id[:20]
            state_str = info.state.value[:8] if info else "UNKNOWN"
            uptime_str = ""
            if info:
                uptime = (now_utc - info.created_at).total_seconds()
                uptime_str = _fmt_duration(uptime)

            chk_str = str(sp.checkpoint_count)
            stg_str = f"L{sp.stagnation_level}" if sp.stagnation_level else "OK"
            gpu_str = "Y" if sp.gpu_allocated else ""

            lines.append(line_fmt.format(
                sel=" ",
                sid=sp.session_id[:14],
                name=name,
                st=state_str,
                upt=uptime_str,
                chk=chk_str,
                cost=_fmt_cost(sp.cost_estimate),
                stg=stg_str,
                gpu=gpu_str,
            ))

    return "\n".join(lines)


def cmd_fleet_kill(fleet: FleetOrchestrator, session_id: str) -> str:
    """Gracefully shut down a session.

    Args:
        fleet: The FleetOrchestrator instance.
        session_id: The session to kill.

    Returns:
        A human-readable result string.
    """
    info = fleet.get_session_info(session_id)
    if info is None:
        return f"Session '{session_id}' not found."

    try:
        fleet.kill_session(session_id)
        return f"Session '{session_id}' ({info.name}) killed successfully."
    except Exception as exc:
        logger.exception("fleet_kill_failed", session_id=session_id)
        return f"ERROR: Failed to kill session '{session_id}': {exc}"


def cmd_fleet_logs(
    fleet: FleetOrchestrator,
    session_id: str,
    tail_lines: int = 20,
) -> str:
    """Tail session output.

    In this implementation, session logs are retrieved from the fleet's
    checkpoint manager, if available.

    Args:
        fleet: The FleetOrchestrator instance.
        session_id: The session to inspect.
        tail_lines: Number of tail lines to show (default 20).

    Returns:
        Log output as a string.
    """
    info = fleet.get_session_info(session_id)
    if info is None:
        return f"Session '{session_id}' not found."

    lines: list[str] = []
    now_str = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"Logs for session '{session_id}' ({info.name}) — {now_str}")
    lines.append(f"  State: {info.state.value}")
    lines.append(f"  Working dir: {info.working_dir}")
    lines.append(f"  Created: {info.created_at.isoformat()}")
    lines.append(f"  Last active: {info.last_active.isoformat()}")
    lines.append("")

    # Try to fetch log content from checkpoints
    checkpoint_data = None
    try:
        if fleet._checkpoint_manager is not None:
            # Get the most recent checkpoint content
            checkpoints = fleet._checkpoint_manager.list_checkpoints(session_id)
            if checkpoints:
                latest = checkpoints[-1]
                checkpoint_data = fleet._checkpoint_manager.recover(session_id)
    except Exception:
        pass

    if checkpoint_data:
        lines.append("=== Last Checkpoint State ===")
        for key, value in list(checkpoint_data.items())[:tail_lines]:
            lines.append(f"  {key}: {value}")
    else:
        lines.append("(No log data available. Checkpoint manager may not be configured.)")

    return "\n".join(lines)


def cmd_fleet_top(
    fleet: FleetOrchestrator,
    circuit_breaker: Any | None = None,
) -> str:
    """Render an htop-like live fleet view.

    This is a one-shot snapshot (repeated calls create a live effect).
    For an interactive version, use FleetTUI.

    Args:
        fleet: The FleetOrchestrator instance.
        circuit_breaker: Optional ConfidenceCircuitBreaker for circuit status.

    Returns:
        A terminal-formatted string.
    """
    import os
    import threading

    try:
        status = fleet.fleet_status()
    except Exception as exc:
        return f"ERROR: {exc}"

    width = _term_width()
    now_str = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = []

    # Summary bar
    lines.append(f"LYRA FLEET TOP  |  {now_str}")
    lines.append(f"  Sessions: {status.total_sessions}  "
                 f"Active: {status.active_count}  "
                 f"Stagnant: {status.stagnant_count}  "
                 f"GPU Used: {status.gpu_allocated_count}")
    lines.append("")

    # Daemon health (if available via fleet's parent class)
    try:
        health = fleet.daemon_status()
        lines.append(f"  Daemon uptime: {_fmt_duration(health.uptime_seconds)}  "
                     f"CPU: {health.cpu_percent:.1f}%  "
                     f"Memory: {health.memory_usage_mb:.0f}MB  "
                     f"Error rate: {health.error_rate:.1f}/min")
    except (AttributeError, Exception):
        pass

    lines.append("")

    # Column header
    fmt = (
        "{sel:4s} {sid:14s} {name:20s} {state:8s} {stg:4s} "
        "{cost:8s} {chk:5s} {gpu:4s} {process:8s}"
    )
    lines.append(fmt.format(
        sel="PID",
        sid="SESSION ID",
        name="NAME",
        state="STATE",
        stg="STAG",
        cost="COST",
        chk="CHK",
        gpu="GPU",
        process="PROCESS",
    ))
    lines.append("-" * width)

    now_utc = datetime.datetime.now(tz=datetime.timezone.utc)

    for i, sp in enumerate(status.sessions):
        info = fleet.get_session_info(sp.session_id)
        name = info.name[:20] if info else sp.session_id[:20]
        state_val = info.state.value[:8] if info else "UNKNOWN"
        stg_str = f"L{sp.stagnation_level}"
        gpu_str = "Y" if sp.gpu_allocated else ""
        process_str = info.process_state.value[:8] if info else ""

        # Circuit breaker indicator
        cb_indicator = ""
        if circuit_breaker is not None:
            try:
                health_cb = circuit_breaker.session_health(sp.session_id)
                if health_cb is not None and health_cb.circuit_state.value != "CLOSED":
                    cb_indicator = f" [{health_cb.circuit_state.value}]"
            except Exception:
                pass

        lines.append(fmt.format(
            sel=f"{i:>4d}",
            sid=sp.session_id[:14],
            name=name,
            state=state_val,
            stg=stg_str,
            cost=_fmt_cost(sp.cost_estimate),
            chk=str(sp.checkpoint_count),
            gpu=gpu_str,
            process=process_str,
        ) + cb_indicator)

    return "\n".join(lines)


def cmd_fleet_list(fleet: FleetOrchestrator) -> str:
    """Alias for cmd_fleet_status.

    Args:
        fleet: The FleetOrchestrator instance.

    Returns:
        A formatted table string.
    """
    return cmd_fleet_status(fleet)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _session_state_char(fleet: FleetOrchestrator, session_id: str) -> str:
    """Return a single-character state indicator."""
    info = fleet.get_session_info(session_id)
    if info is None:
        return "?"
    state = info.state.value
    if state == "WORKING":
        return "R"  # running
    if state == "IDLE":
        return "I"
    if state == "STOPPED":
        return "S"
    if state == "FAILED":
        return "F"
    if state == "COMPLETED":
        return "C"
    if state == "NEEDS_INPUT":
        return "W"  # waiting
    return "?"

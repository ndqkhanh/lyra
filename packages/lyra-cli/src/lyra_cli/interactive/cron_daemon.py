"""Driver-side glue that boots a :class:`CronDaemon` for the REPL.

The :class:`lyra_core.cron.daemon.CronDaemon` already implements the
ticker, the schedule arithmetic, and the per-job runner contract —
everything the REPL needs is a callable that turns a ``CronJob`` into
an actual :class:`AgentLoop` invocation. This module provides that
runner and exposes start/stop hooks the driver wires into REPL boot
and teardown.

Honours ``LYRA_DISABLE_CRON_DAEMON=1`` so paranoid CI / test runs
can opt out without changing the rest of the boot flow.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

__all__ = ["start_cron_daemon", "stop_cron_daemon"]


def start_cron_daemon(session: Any) -> Optional[Any]:
    """Spawn the cron daemon thread for ``session`` if not already running.

    Returns the live :class:`CronDaemon` (cached on
    ``session.cron_daemon``) or ``None`` when the daemon couldn't be
    started — missing lyra-core, env-disabled, or sqlite open
    failure. Always best-effort: a missing cron daemon must not
    prevent the REPL from starting.
    """
    if os.environ.get("LYRA_DISABLE_CRON_DAEMON", "").strip().lower() in (
        "1", "true", "yes", "on"
    ):
        return None
    daemon = getattr(session, "cron_daemon", None)
    if daemon is not None and getattr(daemon, "is_running", lambda: False)():
        return daemon
    try:
        from lyra_core.cron.daemon import CronDaemon

        from .session import _cron_store_for, _ensure_subagent_registry
    except Exception:
        return None
    try:
        store = _cron_store_for(session)
    except Exception:
        return None

    def _runner(job: Any) -> None:
        reg = _ensure_subagent_registry(session)
        if reg is None:
            return
        prompt = job.prompt or ""
        try:
            reg.spawn(prompt, subagent_type="cron")
        except Exception:
            # Per the CronDaemon contract, runner failures are
            # isolated — we never propagate to the tick loop.
            pass

    try:
        daemon = CronDaemon(store=store, runner=_runner, tick_interval=2.0)
        daemon.start()
    except Exception:
        return None
    session.cron_daemon = daemon
    return daemon


def stop_cron_daemon(session: Any) -> None:
    """Stop ``session.cron_daemon`` if alive. Idempotent and quiet."""
    daemon = getattr(session, "cron_daemon", None)
    if daemon is None:
        return
    try:
        daemon.stop(timeout=2.0)
    except Exception:
        pass
    session.cron_daemon = None

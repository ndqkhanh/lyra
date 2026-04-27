"""Scheduled automations (/cron) for Lyra — hermes-agent parity.

This package ships three orthogonal pieces:

* :mod:`lyra_core.cron.schedule` — expression parsing and ``next_run``.
* :mod:`lyra_core.cron.store` — JSON-backed job persistence.
* :mod:`lyra_core.cron.scheduler` — tick loop that runs due jobs.

The CLI plumbs these together via ``lyra_cli.interactive.cron.handle_cron``
so the ``/cron`` slash command and the ``hermes cron ...`` CLI stay
decoupled from prompt-toolkit.
"""
from __future__ import annotations

from .daemon import CronDaemon
from .schedule import Schedule, ScheduleParseError, parse_schedule
from .store import CronJob, CronStore

__all__ = [
    "CronDaemon",
    "CronJob",
    "CronStore",
    "Schedule",
    "ScheduleParseError",
    "parse_schedule",
]

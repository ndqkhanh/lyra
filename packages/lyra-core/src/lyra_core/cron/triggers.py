"""L312-6 — after-event triggers for the cron subsystem.

Three new trigger types beyond the standard cron-time schedule:

- ``after sess-<id> +<N>m`` — fires N minutes after a session ends.
- ``on git-push <ref>`` — fires when a ``git push`` to ``ref`` is
  observed (filesystem mtime check on `.git/refs/<ref>`).
- ``on signal <SIGNAME>`` — fires when a POSIX signal is received.

The triggers are *waker* primitives — they don't replace the cron
schedule; they wake the daemon's :meth:`CronDaemon.run_event_loop`
mid-sleep so jobs gated by these conditions can fire sooner.

The contract surface is minimal — :class:`EventTrigger` exposes
``arm()`` (start watching) and ``fired()`` (poll: True iff the event
has happened since the last call). Each implementation is self-clearing
on ``fired()`` so consumers see one `True` per real event.
"""
from __future__ import annotations

import os
import signal as _signal
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


__all__ = [
    "EventTrigger",
    "GitPushTrigger",
    "SignalTrigger",
    "AfterSessionTrigger",
]


class EventTrigger:
    """Abstract trigger interface.

    Subclasses implement :meth:`arm` (idempotent setup) and
    :meth:`fired` (consume-once polling).
    """

    def arm(self) -> None:  # pragma: no cover - default no-op
        return None

    def fired(self) -> bool:
        raise NotImplementedError

    def wake(self, evt: threading.Event) -> None:
        """Set the daemon's stop-or-poke event when the trigger fires.

        Default: subclasses override this to register a callback that
        sets ``evt`` when the trigger condition is satisfied. The base
        implementation is best-effort — repeated calls are safe.
        """
        if self.fired():
            evt.set()


# --- 1. SignalTrigger ------------------------------------------------- #


@dataclass
class SignalTrigger(EventTrigger):
    """Fire when a POSIX signal arrives.

    On non-POSIX platforms, ``arm()`` is a no-op and ``fired()`` always
    returns False — the trigger is effectively disabled.
    """

    signum: int = _signal.SIGUSR1 if hasattr(_signal, "SIGUSR1") else 0
    _seen: bool = field(default=False, init=False)
    _previous: Optional[object] = field(default=None, init=False)

    def arm(self) -> None:
        if not self.signum or not hasattr(_signal, "signal"):
            return
        try:
            self._previous = _signal.signal(self.signum, self._handler)
        except (ValueError, OSError, RuntimeError):
            # Signal handlers can only be set in the main thread on
            # some platforms — fall back to disabled.
            self._previous = None

    def disarm(self) -> None:
        if self._previous is not None and hasattr(_signal, "signal"):
            try:
                _signal.signal(self.signum, self._previous)
            except (ValueError, OSError, RuntimeError):
                pass
            self._previous = None

    def _handler(self, _signum, _frame):
        self._seen = True

    def fired(self) -> bool:
        if self._seen:
            self._seen = False
            return True
        return False


# --- 2. GitPushTrigger ----------------------------------------------- #


@dataclass
class GitPushTrigger(EventTrigger):
    """Fire when ``.git/refs/<ref>`` mtime advances.

    Cheap: a single ``stat`` call per ``fired()``. Works for any ref
    written by ``git push`` / ``git update-ref``.
    """

    repo: Path
    ref: str = "heads/main"
    _last_mtime: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        self.repo = Path(self.repo)

    def _ref_path(self) -> Path:
        return self.repo / ".git" / "refs" / self.ref

    def arm(self) -> None:
        p = self._ref_path()
        try:
            self._last_mtime = p.stat().st_mtime
        except OSError:
            self._last_mtime = 0.0

    def fired(self) -> bool:
        p = self._ref_path()
        try:
            mt = p.stat().st_mtime
        except OSError:
            return False
        if mt > self._last_mtime:
            self._last_mtime = mt
            return True
        return False


# --- 3. AfterSessionTrigger ------------------------------------------ #


@dataclass
class AfterSessionTrigger(EventTrigger):
    """Fire when ``session_id`` is observed in the lifecycle bus's session-end stream.

    Composes with ``LifecycleBus`` from L311-1's lifecycle module. The
    integration is lazy — the trigger doesn't import the bus; the
    daemon supplies whatever observer hook it has.
    """

    session_id: str
    _seen: bool = field(default=False, init=False)

    def notify_session_end(self, session_id: str) -> None:
        """Public surface — bus subscriber calls this with the ending session id."""
        if session_id == self.session_id:
            self._seen = True

    def fired(self) -> bool:
        if self._seen:
            self._seen = False
            return True
        return False

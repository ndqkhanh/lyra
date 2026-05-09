"""L311-1 — Anthropic Agent Teams runtime (lead-and-spokes).

Imports the Feb-2026 Anthropic Agent Teams architecture
([`docs/250-anthropic-agent-teams.md`](../../../../../../docs/250-anthropic-agent-teams.md))
into Lyra. Coexists with the existing MetaGPT-style sequential
:class:`~lyra_core.teams.registry.TeamPlan`; the two shapes are
complementary — sequential pipeline for SOP-shaped work, lead-and-spokes
runtime for naturally-parallel work.

The runtime is **filesystem-coordinated**, **process-isolated**, and
**lead-managed**:

* ``LeadSession`` is the only orchestrator (no nesting, no leadership
  transfer — matches Claude Code's ``LBL-AT-NEST`` / ``LBL-AT-PROMOTE``).
* Each ``Teammate`` is a callable plus per-teammate metadata; in
  production, callers wire it to a full ``InteractiveSession`` (one
  session per teammate); in tests, callers wire it to a deterministic
  stub.
* Coordination state lives under ``team_dir/`` — a ``SharedTaskList``
  (filesystem with POSIX file-locking) and a per-teammate ``Mailbox``.
* Lifecycle events (``team.teammate_idle`` / ``team.task_created`` /
  ``team.task_completed`` / ``team.spawn`` / ``team.shutdown``) are
  emitted on :func:`lyra_core.hir.events.emit` so existing trace
  subscribers (LangSmith, Langfuse, OTel) light up without code
  changes.
* Cost guard: ``LBL-AT-COST`` warns at K=6 teammates, blocks at K=10
  unless ``allow_unsafe_token_overage=True`` is passed at construction
  time. Mirrors Anthropic's documented 7× plan-mode token cost.

Usage::

    from lyra_core.teams.agent_teams import LeadSession, TeammateSpec

    lead = LeadSession.create(
        team_name="auth-refactor",
        team_dir=tmp_path / "teams",
        executor=my_executor,        # (TeammateSpec, str) -> str
    )
    lead.spawn(TeammateSpec(name="security", model="smart"))
    lead.spawn(TeammateSpec(name="performance", model="smart"))
    lead.add_task("Review auth.py for security issues", assign="security")
    lead.add_task("Benchmark request-path latency", assign="performance")
    lead.run_until_idle(timeout_s=60)
    report = lead.shutdown()
    assert report.completed == 2
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

from .mailbox import Mailbox, MailboxMessage
from .shared_tasks import SharedTaskList, TaskState


TeammateMode = Literal["in-process", "tmux", "iterm2", "auto"]
"""Display mode for teammate output. Only ``in-process`` runs work
synchronously in the calling process; ``tmux`` / ``iterm2`` are
metadata-only in this MVP — real pane allocation is a v3.11.x follow-up."""


# Cost-guard constants (LBL-AT-COST). Anthropic recommends 3-5
# teammates with 5-6 tasks each; 7x token cost in plan mode.
TEAMMATE_WARN_THRESHOLD = 5
TEAMMATE_BLOCK_THRESHOLD = 10


# ---- typed errors -----------------------------------------------------


class AgentTeamError(RuntimeError):
    """Base class for Agent Teams errors."""


class TeamCostError(AgentTeamError):
    """Raised when team size exceeds ``TEAMMATE_BLOCK_THRESHOLD``."""


class TeamNestError(AgentTeamError):
    """Raised when a teammate tries to spawn a sub-team. ``LBL-AT-NEST``."""


class TeamPromoteError(AgentTeamError):
    """Raised when callers attempt to transfer leadership. ``LBL-AT-PROMOTE``."""


class TeammateNotFoundError(AgentTeamError):
    """Raised when a mailbox or task targets an unknown teammate."""


class HookBlockedError(AgentTeamError):
    """Raised when a registered hook script blocks an event with exit-code 2.

    Mirrors Claude Code's hook semantics ([`docs/05-hooks.md`](../../../../../../docs/05-hooks.md)):
    user-registered shell scripts can refuse a ``team.task_created`` /
    ``team.task_completed`` / ``team.teammate_idle`` event by exiting
    with status 2. The lead session converts that into this exception.
    """


# ---- data types -------------------------------------------------------


@dataclass(frozen=True)
class TeammateSpec:
    """Specification for one teammate. Frozen — passed to ``LeadSession.spawn``."""

    name: str
    """Lowercase identifier used in mailbox + task assignment."""
    model: Literal["fast", "smart"] = "smart"
    """Lyra two-tier model slot. Defaults to smart for review work."""
    subagent: str | None = None
    """Optional subagent definition name (overrides tool-grant scope)."""
    persona: str | None = None
    """Optional inline persona; falls back to subagent definition or default."""
    metadata: dict[str, Any] = field(default_factory=dict)


# ``Executor`` is the seam between the runtime and the actual LLM-driven
# work. It takes a TeammateSpec and a task body string and returns the
# teammate's textual response. In production, callers wire this to an
# :class:`~lyra_core.loop.AgentLoop` instance (one per teammate); in
# tests, callers wire a deterministic stub.
Executor = Callable[[TeammateSpec, str], str]


@dataclass(frozen=True)
class TeamReport:
    """Aggregated outcome of a ``LeadSession`` lifetime."""

    team_name: str
    spawned: tuple[str, ...]
    completed: int
    pending: int
    blocked: int
    in_progress: int
    failed: int
    elapsed_s: float
    mailbox_messages: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "team_name": self.team_name,
            "spawned": list(self.spawned),
            "completed": self.completed,
            "pending": self.pending,
            "blocked": self.blocked,
            "in_progress": self.in_progress,
            "failed": self.failed,
            "elapsed_s": round(self.elapsed_s, 4),
            "mailbox_messages": self.mailbox_messages,
        }


# ---- LeadSession ------------------------------------------------------


_LIFECYCLE_BUS_REGISTRY: list[Any] = []


def register_lifecycle_bus(bus: Any) -> None:
    """Register a :class:`~lyra_core.hooks.lifecycle.LifecycleBus` so team
    events fan out to its subscribers in addition to ``hir.events``.

    Idempotent: registering the same bus twice is a no-op. Used by
    long-running agent processes that already have a bus they want
    team events on (CLI session, ACP server, daemons).
    """
    if bus not in _LIFECYCLE_BUS_REGISTRY:
        _LIFECYCLE_BUS_REGISTRY.append(bus)


def unregister_lifecycle_bus(bus: Any) -> None:
    if bus in _LIFECYCLE_BUS_REGISTRY:
        _LIFECYCLE_BUS_REGISTRY.remove(bus)


def _emit(name: str, /, **attrs: Any) -> None:
    """Best-effort lifecycle emission. Fans out to:

    1. ``lyra_core.hir.events.emit`` — every registered hir subscriber.
    2. Every registered :class:`LifecycleBus` (if any) — typed enum-based
       subscribers.

    Both fan-out paths are wrapped in try/except so a misbehaving
    subscriber cannot break the team runtime.
    """
    try:
        from lyra_core.hir import events  # local import — optional dep

        events.emit(name, **attrs)
    except Exception:
        pass
    if not _LIFECYCLE_BUS_REGISTRY:
        return
    try:
        from lyra_core.hooks.lifecycle import LifecycleEvent

        try:
            event = LifecycleEvent(name)
        except ValueError:
            event = None
    except Exception:
        event = None
    if event is None:
        return
    for bus in tuple(_LIFECYCLE_BUS_REGISTRY):
        try:
            bus.emit(event, dict(attrs))
        except Exception:
            pass


class LeadSession:
    """The single orchestrator of an Agent Team.

    A ``LeadSession`` owns the ``team_dir/``, the shared task list, and
    the mailboxes. Teammates are added via :meth:`spawn`; tasks via
    :meth:`add_task` (or peer-side via the mailbox). The lead drives
    the runtime by repeatedly calling :meth:`step` (or the convenience
    :meth:`run_until_idle`).

    The lead is *not* a teammate — it does not claim tasks. Mirrors
    Anthropic's lead-and-spokes architecture exactly.
    """

    def __init__(
        self,
        *,
        team_name: str,
        team_dir: Path,
        executor: Executor,
        mode: TeammateMode = "in-process",
        allow_unsafe_token_overage: bool = False,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.team_name = team_name
        self.team_dir = Path(team_dir).resolve()
        self.team_dir.mkdir(parents=True, exist_ok=True)
        self.tasks = SharedTaskList(self.team_dir / "tasks")
        self.mailbox = Mailbox(self.team_dir / "mailbox")
        self.executor = executor
        self.mode: TeammateMode = mode
        self.allow_unsafe_token_overage = allow_unsafe_token_overage
        self._clock = clock or time.time
        self._teammates: dict[str, TeammateSpec] = {}
        self._created_at = self._clock()
        self._failed_count = 0
        # Lead has its own mailbox — peers send `idle` messages to it.
        self.mailbox.ensure("lead")
        _emit("team.create", team=self.team_name, mode=self.mode)

    # ---- factory --------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        team_name: str,
        team_dir: Path,
        executor: Executor,
        mode: TeammateMode = "in-process",
        allow_unsafe_token_overage: bool = False,
    ) -> "LeadSession":
        return cls(
            team_name=team_name,
            team_dir=team_dir,
            executor=executor,
            mode=mode,
            allow_unsafe_token_overage=allow_unsafe_token_overage,
        )

    # ---- spawn ----------------------------------------------------

    def spawn(self, spec: TeammateSpec) -> TeammateSpec:
        """Register a teammate. Cost-guard enforces ``LBL-AT-COST``."""
        if spec.name == "lead":
            raise ValueError("teammate name 'lead' is reserved")
        if spec.name in self._teammates:
            raise ValueError(f"teammate {spec.name!r} already spawned")
        next_size = len(self._teammates) + 1
        if next_size > TEAMMATE_BLOCK_THRESHOLD and not self.allow_unsafe_token_overage:
            raise TeamCostError(
                f"refusing to spawn teammate #{next_size} — exceeds "
                f"LBL-AT-COST block threshold ({TEAMMATE_BLOCK_THRESHOLD}); "
                "pass allow_unsafe_token_overage=True to override."
            )
        self._teammates[spec.name] = spec
        self.mailbox.ensure(spec.name)
        _emit(
            "team.spawn",
            team=self.team_name,
            teammate=spec.name,
            model=spec.model,
            subagent=spec.subagent,
            size=next_size,
        )
        return spec

    @property
    def teammates(self) -> tuple[str, ...]:
        return tuple(self._teammates.keys())

    @property
    def warn_cost(self) -> bool:
        """True when the team has crossed the ``LBL-AT-COST`` warn threshold."""
        return len(self._teammates) > TEAMMATE_WARN_THRESHOLD

    # ---- task ops -------------------------------------------------

    def add_task(
        self,
        title: str,
        *,
        assign: str | None = None,
        depends_on: Iterable[str] = (),
        body: str = "",
    ) -> str:
        """Add a task to the shared list; optionally pre-assign to a teammate.

        Consults the global :class:`TeamHookRegistry` first — registered
        ``team.task_created`` hooks may refuse the action by exiting
        with status 2, in which case :class:`HookBlockedError` is raised
        and the task is *not* created.
        """
        if assign is not None and assign not in self._teammates:
            raise TeammateNotFoundError(
                f"cannot assign task to unknown teammate {assign!r}; "
                f"spawned: {sorted(self._teammates)!r}"
            )
        # Pre-event hook gate — block before mutating shared state.
        gate = self._gate(
            "team.task_created",
            {
                "team": self.team_name,
                "title": title,
                "owner": assign,
                "depends_on": list(depends_on),
            },
        )
        if gate is not None and gate.blocked:
            raise HookBlockedError(
                f"team.task_created blocked by hook: {gate.block_reason}"
            )
        task = self.tasks.create(
            title=title,
            owner=assign,
            depends_on=tuple(depends_on),
            body=body,
        )
        _emit(
            "team.task_created",
            team=self.team_name,
            task_id=task.id,
            owner=assign,
            depends_on=list(depends_on),
        )
        return task.id

    # ---- hook gate ------------------------------------------------

    def _gate(self, event: str, payload: dict[str, Any]):
        """Consult the process-wide TeamHookRegistry. Returns the
        :class:`GateResult` (or None when the registry has no hooks
        for this event)."""
        try:
            from .hooks import HOOKABLE_EVENTS, global_registry
        except Exception:
            return None
        if event not in HOOKABLE_EVENTS:
            return None
        reg = global_registry()
        if not reg.hooks_for(event):
            return None
        return reg.gate(event, payload)  # type: ignore[arg-type]

    def send_to(self, teammate: str, body: str, *, kind: str = "info") -> None:
        """Lead → teammate direct message."""
        if teammate not in self._teammates:
            raise TeammateNotFoundError(f"unknown teammate {teammate!r}")
        self.mailbox.send(sender="lead", recipient=teammate, body=body, kind=kind)

    # ---- step engine ---------------------------------------------

    def step(self) -> int:
        """Execute one round: each idle teammate claims one ready task,
        runs it through ``executor``, marks completion, sends an idle
        notification to the lead.

        Returns the number of tasks completed in this round.
        """
        completed = 0
        for name, spec in self._teammates.items():
            ready = self.tasks.next_ready_for(name)
            if ready is None:
                # Look for unowned ready tasks the teammate can claim.
                ready = self.tasks.claim_unowned(name)
            if ready is None:
                continue
            self.tasks.start(ready.id, owner=name)
            try:
                payload = ready.body or ready.title
                response = self.executor(spec, payload)
            except Exception as e:  # executor failure — mark blocked
                self._failed_count += 1
                self.tasks.fail(ready.id, reason=f"{type(e).__name__}: {e}")
                _emit(
                    "team.task_failed",
                    team=self.team_name,
                    task_id=ready.id,
                    teammate=name,
                    error=str(e),
                )
                continue
            # Pre-complete hook gate — exit-code 2 forces revision
            # by leaving the task as in_progress instead of marking it
            # done. The teammate keeps the claim and may retry on a
            # later step (matches Claude Code's "force revision" hook
            # semantic).
            complete_gate = self._gate(
                "team.task_completed",
                {
                    "team": self.team_name,
                    "task_id": ready.id,
                    "teammate": name,
                    "output": response,
                },
            )
            if complete_gate is not None and complete_gate.blocked:
                # Reset to pending so the teammate can pick it up
                # again on the next round.
                self.tasks.fail(
                    ready.id,
                    reason=f"hook-blocked: {complete_gate.block_reason}",
                )
                _emit(
                    "team.task_failed",
                    team=self.team_name,
                    task_id=ready.id,
                    teammate=name,
                    error=f"hook-blocked completion: {complete_gate.block_reason}",
                )
                continue

            self.tasks.complete(ready.id, output=response)
            completed += 1
            _emit(
                "team.task_completed",
                team=self.team_name,
                task_id=ready.id,
                teammate=name,
            )
            # Idle notification to lead — auto-sent per doc 250 §(d).
            self.mailbox.send(
                sender=name,
                recipient="lead",
                body=f"completed {ready.id}: {ready.title}",
                kind="idle",
            )
            # team.teammate_idle hook gate (advisory — non-blocking even
            # if exit 2 is returned, because the teammate has already
            # finished its claim and there's no work to undo).
            self._gate(
                "team.teammate_idle",
                {
                    "team": self.team_name,
                    "teammate": name,
                    "task_id": ready.id,
                },
            )
            _emit(
                "team.teammate_idle",
                team=self.team_name,
                teammate=name,
                task_id=ready.id,
            )
        return completed

    def run_until_idle(self, *, timeout_s: float = 60.0, poll_s: float = 0.0) -> int:
        """Repeatedly :meth:`step` until no progress is made or the
        deadline passes.

        Returns the total number of tasks completed across all rounds.
        """
        start = self._clock()
        completed = 0
        while True:
            n = self.step()
            completed += n
            if n == 0:
                # No progress this round — done.
                break
            if self._clock() - start > timeout_s:
                break
            if poll_s > 0:
                time.sleep(poll_s)
        return completed

    # ---- shutdown -------------------------------------------------

    def shutdown(self) -> TeamReport:
        """Snapshot final state, emit ``team.shutdown``, return :class:`TeamReport`."""
        snap = self.tasks.summary()
        elapsed = self._clock() - self._created_at
        msgs = self.mailbox.message_count()
        report = TeamReport(
            team_name=self.team_name,
            spawned=tuple(self._teammates.keys()),
            completed=snap.completed,
            pending=snap.pending,
            blocked=snap.blocked,
            in_progress=snap.in_progress,
            failed=self._failed_count,
            elapsed_s=elapsed,
            mailbox_messages=msgs,
        )
        _emit(
            "team.shutdown",
            team=self.team_name,
            report=report.as_dict(),
        )
        return report

    # ---- lead inbox -----------------------------------------------

    def inbox(self) -> list[MailboxMessage]:
        """Return all undelivered messages addressed to the lead."""
        return self.mailbox.read("lead")


__all__ = [
    "AgentTeamError",
    "Executor",
    "HookBlockedError",
    "LeadSession",
    "TeamCostError",
    "TeamNestError",
    "TeamPromoteError",
    "TeammateMode",
    "TeammateNotFoundError",
    "TeammateSpec",
    "TeamReport",
    "TEAMMATE_BLOCK_THRESHOLD",
    "TEAMMATE_WARN_THRESHOLD",
    "register_lifecycle_bus",
    "unregister_lifecycle_bus",
]

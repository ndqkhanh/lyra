"""Routines — cron + webhook + API triggers (v3.7 L37-8).

Anthropic's Claude Code "Routines" let users create multi-step
workflows triggered by cron schedules, GitHub webhooks, or HTTP API
calls. Lyra's existing ``cron/`` module covers schedule-only triggers;
this module extends it to typed :class:`RoutineTrigger`s and a
registry that dispatches to a workflow callable.

Two bright-lines apply (see plan §3):

* ``LBL-ROUTINE-AUTH`` — webhook and API triggers require a matching
  HMAC signature; unsigned firings raise ``RoutineAuthError``.
* ``LBL-ROUTINE-COST`` — invocations count against the program's
  cost envelope; over-cap firings are *deferred* (queued for the
  next window), not silently skipped.
"""
from __future__ import annotations

import enum
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional


_LBL_AUTH: str = "LBL-ROUTINE-AUTH"
_LBL_COST: str = "LBL-ROUTINE-COST"


class TriggerKind(str, enum.Enum):
    CRON = "cron"
    GITHUB_WEBHOOK = "github_webhook"
    HTTP_API = "http_api"


class RoutineAuthError(RuntimeError):
    """Raised when a webhook / API trigger fails HMAC verification."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"{_LBL_AUTH}: {reason}")
        self.bright_line = _LBL_AUTH


# --- Triggers --------------------------------------------------------------


@dataclass(frozen=True)
class CronTrigger:
    """Schedule-driven trigger. ``expression`` mirrors cron syntax."""

    kind: TriggerKind = TriggerKind.CRON
    expression: str = "0 */1 * * *"          # default: hourly
    timezone: str = "UTC"


@dataclass(frozen=True)
class GitHubWebhookTrigger:
    """GitHub webhook trigger (HMAC-signed via X-Hub-Signature-256)."""

    kind: TriggerKind = TriggerKind.GITHUB_WEBHOOK
    repo: str = ""                            # "owner/repo"
    events: tuple[str, ...] = ("push",)       # webhook event names

    def matches(self, *, repo: str, event: str) -> bool:
        if self.repo and self.repo != repo:
            return False
        return event in self.events


@dataclass(frozen=True)
class HttpApiTrigger:
    """HTTP API trigger — caller sends a signed POST."""

    kind: TriggerKind = TriggerKind.HTTP_API
    path: str = "/routines/fire"


RoutineTrigger = Any   # CronTrigger | GitHubWebhookTrigger | HttpApiTrigger


# --- HMAC verification -----------------------------------------------------


def verify_github_signature(*, secret: bytes, body: bytes,
                            received_signature: str) -> None:
    """GitHub uses ``sha256=<hex>`` in the ``X-Hub-Signature-256`` header."""
    if not received_signature.startswith("sha256="):
        raise RoutineAuthError("missing sha256= prefix on GitHub signature")
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_signature):
        raise RoutineAuthError("GitHub HMAC signature mismatch")


def verify_api_signature(*, secret: bytes, body: bytes,
                          received_signature: str) -> None:
    """Lyra's API trigger uses a raw hex HMAC-SHA256 over the body."""
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_signature):
        raise RoutineAuthError("API HMAC signature mismatch")


# --- Routine + Registry ----------------------------------------------------


@dataclass(frozen=True)
class RoutineInvocation:
    """One firing of a routine."""

    routine_name: str
    trigger_kind: TriggerKind
    payload: dict[str, Any]
    fired_ts: float
    deferred: bool = False
    bright_line: Optional[str] = None
    reason: str = ""


# Workflow callable signature: ``(routine_name, payload) -> Any``.
WorkflowFn = Callable[[str, dict[str, Any]], Any]


@dataclass
class Routine:
    """One named routine with a typed trigger and a workflow."""

    name: str
    trigger: RoutineTrigger
    workflow: str                             # registered workflow id
    secret: bytes = b""                       # for webhook/api auth
    cost_per_firing: float = 1.0


@dataclass
class RoutineRegistry:
    """In-memory registry of routines + dispatch with HMAC + cost guards."""

    workflows: dict[str, WorkflowFn] = field(default_factory=dict)
    routines: dict[str, Routine] = field(default_factory=dict)
    cost_envelope: float = float("inf")
    cost_spent: float = 0.0
    deferred_queue: list[RoutineInvocation] = field(default_factory=list)
    invocations: list[RoutineInvocation] = field(default_factory=list)

    def register_workflow(self, workflow_id: str, fn: WorkflowFn) -> None:
        if workflow_id in self.workflows:
            raise ValueError(f"workflow {workflow_id!r} already registered")
        self.workflows[workflow_id] = fn

    def register_routine(self, routine: Routine) -> None:
        if routine.name in self.routines:
            raise ValueError(f"routine {routine.name!r} already registered")
        if routine.workflow not in self.workflows:
            raise ValueError(
                f"routine {routine.name!r} references unknown workflow "
                f"{routine.workflow!r}"
            )
        self.routines[routine.name] = routine

    def fire_cron(self, routine_name: str,
                  *, payload: Optional[dict[str, Any]] = None) -> RoutineInvocation:
        routine = self._routine(routine_name)
        if not isinstance(routine.trigger, CronTrigger):
            raise ValueError(
                f"routine {routine_name!r} is not cron-triggered "
                f"(trigger.kind={routine.trigger.kind})"
            )
        return self._invoke(routine, payload or {}, TriggerKind.CRON)

    def fire_github_webhook(
        self,
        routine_name: str,
        *,
        body: bytes,
        signature: str,
        repo: str,
        event: str,
    ) -> RoutineInvocation:
        routine = self._routine(routine_name)
        if not isinstance(routine.trigger, GitHubWebhookTrigger):
            raise ValueError(
                f"routine {routine_name!r} is not github_webhook-triggered"
            )
        if not routine.trigger.matches(repo=repo, event=event):
            raise ValueError(
                f"routine {routine_name!r} does not subscribe to "
                f"event={event!r} repo={repo!r}"
            )
        verify_github_signature(
            secret=routine.secret, body=body, received_signature=signature,
        )
        payload = json.loads(body.decode("utf-8")) if body else {}
        payload.setdefault("_repo", repo)
        payload.setdefault("_event", event)
        return self._invoke(routine, payload, TriggerKind.GITHUB_WEBHOOK)

    def fire_http_api(
        self,
        routine_name: str,
        *,
        body: bytes,
        signature: str,
    ) -> RoutineInvocation:
        routine = self._routine(routine_name)
        if not isinstance(routine.trigger, HttpApiTrigger):
            raise ValueError(
                f"routine {routine_name!r} is not http_api-triggered"
            )
        verify_api_signature(
            secret=routine.secret, body=body, received_signature=signature,
        )
        payload = json.loads(body.decode("utf-8")) if body else {}
        return self._invoke(routine, payload, TriggerKind.HTTP_API)

    def replay_deferred(self) -> list[RoutineInvocation]:
        """Re-attempt deferred invocations now that the cost envelope may
        have headroom. Returns the list of *now-fired* invocations."""
        replayed: list[RoutineInvocation] = []
        still_deferred: list[RoutineInvocation] = []
        for inv in self.deferred_queue:
            routine = self.routines.get(inv.routine_name)
            if routine is None:
                continue
            if self.cost_spent + routine.cost_per_firing > self.cost_envelope:
                still_deferred.append(inv)
                continue
            new_inv = self._invoke(routine, inv.payload, inv.trigger_kind)
            replayed.append(new_inv)
        self.deferred_queue = still_deferred
        return replayed

    # --- internal --------------------------------------------------------

    def _routine(self, name: str) -> Routine:
        if name not in self.routines:
            raise KeyError(f"unknown routine {name!r}")
        return self.routines[name]

    def _invoke(self, routine: Routine, payload: dict[str, Any],
                trigger_kind: TriggerKind) -> RoutineInvocation:
        # LBL-ROUTINE-COST: defer when over envelope.
        if self.cost_spent + routine.cost_per_firing > self.cost_envelope:
            inv = RoutineInvocation(
                routine_name=routine.name,
                trigger_kind=trigger_kind,
                payload=dict(payload),
                fired_ts=time.time(),
                deferred=True,
                bright_line=_LBL_COST,
                reason=(
                    f"{_LBL_COST}: cost {self.cost_spent:.1f} + firing "
                    f"{routine.cost_per_firing:.1f} would exceed envelope "
                    f"{self.cost_envelope:.1f}; deferred"
                ),
            )
            self.deferred_queue.append(inv)
            self.invocations.append(inv)
            return inv
        # Run.
        self.workflows[routine.workflow](routine.name, payload)
        self.cost_spent += routine.cost_per_firing
        inv = RoutineInvocation(
            routine_name=routine.name,
            trigger_kind=trigger_kind,
            payload=dict(payload),
            fired_ts=time.time(),
        )
        self.invocations.append(inv)
        return inv


__all__ = [
    "CronTrigger",
    "GitHubWebhookTrigger",
    "HttpApiTrigger",
    "Routine",
    "RoutineAuthError",
    "RoutineInvocation",
    "RoutineRegistry",
    "TriggerKind",
    "WorkflowFn",
    "verify_api_signature",
    "verify_github_signature",
]

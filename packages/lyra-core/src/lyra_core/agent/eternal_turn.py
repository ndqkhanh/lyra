"""L4.1 — wrap an :class:`AgentLoop` so each user turn is durable.

The core trick: we do **not** modify ``AgentLoop`` itself. Instead we wrap
its dependencies (the tool dict and the LLM) with journal-aware proxies,
and run the whole turn as a single Restate workflow step.

What this delivers
------------------
* **Cross-turn durability.** Every turn is one Restate invocation; a
  process death between turns loses nothing.
* **Per-turn deadline.** ``deadline_per_turn_s`` wraps the whole turn in
  :func:`asyncio.wait_for`.
* **Tool-level idempotent replay.** Tools dispatched inside a turn that
  later crashes are *not* re-executed on replay — the journal returns
  the recorded result. Side-effecting tools (file writes, HTTP POSTs)
  must opt in by declaring ``__eternal_idempotent__ = True`` on the
  callable; opt-in is the safe default for read-only tools.
* **Workflow-level circuit breaker.** Repeated turn failures within a
  sliding window quarantine the workflow class.

What this does NOT deliver
--------------------------
* **Mid-turn step-by-step replay.** If a turn is killed mid-LLM-call,
  the *whole* turn replays from the start. Per-step replay inside the
  loop requires step boundaries inside ``loop.py`` — a follow-up.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from harness_eternal import CircuitBreaker
from harness_eternal.restate import LocalRuntime, RestateRuntime, step, workflow
from harness_eternal.restate.journal import Journal

from .eternal_llm import JournaledLLM


# ---------------------------------------------------------------------------
# Tool proxies — sync-friendly, journal-backed idempotency
# ---------------------------------------------------------------------------


def _stable_args_hash(arguments: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(arguments), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _tool_is_idempotent(fn: Callable[..., Any]) -> bool:
    """Tools opt in by declaring ``__eternal_idempotent__ = True``.

    Tools that don't declare are assumed to be safe to re-run (the AgentLoop
    treats every tool call as fresh today). Side-effecting tools should
    declare ``False`` — those are NOT memoized, so a crash mid-turn that
    completed the side-effect WILL re-fire it on replay. Such tools should
    declare their own internal idempotency.
    """
    return getattr(fn, "__eternal_idempotent__", False)


class JournaledTools(dict):
    """Drop-in replacement for ``AgentLoop.tools``.

    On dispatch, consults the activity table — if a record exists for
    ``(turn_id, tool_name, args_hash)``, returns the stored result without
    invoking the underlying tool. Otherwise, invokes the tool and records
    the result.
    """

    def __init__(
        self,
        inner: Mapping[str, Callable[..., Any]],
        *,
        journal: Journal,
        turn_id: str,
    ) -> None:
        super().__init__()
        self._journal = journal
        self._turn_id = turn_id
        for name, fn in inner.items():
            self[name] = self._wrap(name, fn)

    def _wrap(self, name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        if not _tool_is_idempotent(fn):
            return fn

        journal = self._journal
        turn_id = self._turn_id

        def _wrapped(**kwargs):
            key = f"{turn_id}:{name}:{_stable_args_hash(kwargs)}"
            recorded = journal.lookup_activity(key)
            if recorded is not None:
                return recorded
            result = fn(**kwargs)
            journal.record_activity(idempotency_key=key, result=result)
            return result

        _wrapped.__name__ = getattr(fn, "__name__", name)
        return _wrapped


# ---------------------------------------------------------------------------
# Eternal turn wrapper
# ---------------------------------------------------------------------------


@dataclass
class EternalAgentLoop:
    """Wraps a regular :class:`AgentLoop` for durable, deadlined turns.

    Construct this once per session. Call :meth:`run_conversation_durable`
    instead of ``loop.run_conversation`` for every user turn.
    """

    loop: Any  # AgentLoop — duck-typed so we don't import it here
    runtime: LocalRuntime | RestateRuntime
    breaker: CircuitBreaker = field(default_factory=lambda: CircuitBreaker(after=5))
    deadline_per_turn_s: int = 600
    workflow_name: str = "lyra.turn"

    def __post_init__(self) -> None:
        @workflow(name=self.workflow_name)
        async def _turn_workflow(ctx, user_text: str, session_id: str) -> dict:
            # The whole turn is one journaled step.
            return await step(
                ctx,
                lambda: asyncio.to_thread(
                    self._invoke_loop, user_text, session_id, ctx.invocation_id
                ),
                step_name="run_conversation",
            )

        self.runtime.register(_turn_workflow, name=self.workflow_name)
        self._workflow = _turn_workflow

    def run_conversation(self, user_text: str, *, session_id: str) -> "_TurnView":
        """``AgentLoop``-shaped alias for :meth:`run_conversation_durable`.

        Returns a lightweight view object exposing the same ``final_text``,
        ``iterations``, ``tool_calls``, ``stopped_by`` attributes that
        ``TurnResult`` does, so callers expecting ``AgentLoop.run_conversation``
        (e.g., :class:`SubagentRunner`) can use ``EternalAgentLoop`` as a
        drop-in replacement.

        For quarantined / errored turns the view's ``stopped_by`` reflects
        the eternal-mode reason ("quarantined").
        """
        result = self.run_conversation_durable(user_text, session_id=session_id)
        return _TurnView(
            final_text=str(result.get("final_text") or ""),
            iterations=int(result.get("iterations") or 0),
            tool_calls=list(result.get("tool_calls") or []),
            stopped_by=str(result.get("stopped_by") or "end_turn"),
        )

    def run_conversation_durable(
        self,
        user_text: str,
        *,
        session_id: str,
    ) -> dict:
        """Synchronous, durable entry point. Returns ``TurnResult.__dict__``.

        The dict-shape return is intentional — Restate's journal serialises
        results via JSON; we therefore convert TurnResult to a dict.
        Callers that want the dataclass back can pass it to
        ``TurnResult(**result)`` (after popping any additional fields).
        """
        if self.breaker.is_quarantined(self.workflow_name):
            return {
                "stopped_by": "quarantined",
                "quarantine_reason": (
                    f"workflow {self.workflow_name!r} is quarantined; "
                    "write 'unblock' to HUMAN_DIRECTIVE.md to clear"
                ),
                "iterations": 0,
                "final_text": "",
                "tool_calls": [],
            }

        # Each turn gets a unique invocation_id so concurrent turns do not
        # share journal rows.
        digest = hashlib.sha256(
            f"{session_id}|{time.time()}|{user_text}".encode("utf-8")
        ).hexdigest()[:16]
        invocation_id = f"{self.workflow_name}:{digest}"

        async def _do() -> dict:
            return await self.runtime.invoke(
                self.workflow_name, user_text, session_id,
                invocation_id=invocation_id,
            )

        try:
            return asyncio.run(
                asyncio.wait_for(_do(), timeout=self.deadline_per_turn_s)
                if self.deadline_per_turn_s > 0
                else _do()
            )
        except asyncio.TimeoutError as exc:
            self.breaker.record_failure(self.workflow_name)
            raise TimeoutError(
                f"turn exceeded {self.deadline_per_turn_s}s deadline"
            ) from exc
        except Exception:
            self.breaker.record_failure(self.workflow_name)
            raise

    def _invoke_loop(
        self, user_text: str, session_id: str, invocation_id: str
    ) -> dict:
        """Run the AgentLoop with journaled LLM and tools for this turn.

        On crash + replay (same invocation_id), the JournaledLLM returns
        recorded results at each iteration position and the
        JournaledTools returns recorded results for opt-in idempotent
        tools — together they reconstruct the same messages list and
        tool-dispatch sequence deterministically.
        """
        original_tools = self.loop.tools
        original_llm = self.loop.llm
        try:
            self.loop.tools = JournaledTools(
                original_tools or {},
                journal=self.runtime.journal,
                turn_id=invocation_id,
            )
            # Only wrap the LLM when one is actually present and callable —
            # some test stubs run without an LLM, and stubs that don't
            # expose .generate / __call__ shouldn't crash the wrapper.
            if original_llm is not None and (
                hasattr(original_llm, "generate") or callable(original_llm)
            ):
                self.loop.llm = JournaledLLM(
                    inner=original_llm,
                    journal=self.runtime.journal,
                    turn_id=invocation_id,
                )
            tr = self.loop.run_conversation(user_text, session_id=session_id)
        finally:
            self.loop.tools = original_tools
            self.loop.llm = original_llm
        self.breaker.record_success(self.workflow_name)
        return {
            "final_text": tr.final_text,
            "iterations": tr.iterations,
            "tool_calls": tr.tool_calls,
            "stopped_by": tr.stopped_by,
        }


@dataclass
class _TurnView:
    """Read-only view exposing the AgentLoop ``TurnResult`` shape."""

    final_text: str
    iterations: int
    tool_calls: list
    stopped_by: str


__all__ = [
    "EternalAgentLoop",
    "JournaledTools",
]

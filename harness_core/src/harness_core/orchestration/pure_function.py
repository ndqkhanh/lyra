"""Pure-function agent base class with replayable trajectories.

The contract:
    1. Agent decisions are deterministic given the input fingerprint
       (model, context, prior_messages, tool_results).
    2. Side-effecting tools (writes, mutations, network egress) must be
       declared via :class:`SideEffectLog` so they can be skipped on replay.
    3. Replay rehydrates a recorded trajectory without re-executing
       side-effects — the policy decides; the log re-plays what happened.

This is the structural answer to "non-deterministic agents can't be RL-trained,
audited at <1% FPR, or branched safely." Python can't enforce purity at runtime;
the pattern is to *separate* the policy (which is pure) from the effect (which
is logged + gated).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol


@dataclass
class AgentDecision:
    """A pure decision: what the agent wants to do next.

    The decision is a function of the fingerprint (input + context + history).
    Re-running with the same fingerprint must produce the same decision.
    """

    action: str  # "tool_call" | "answer" | "delegate" | "stop"
    payload: dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""  # sha256 of the (input, context, history) tuple

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.action, "payload": self.payload, "fingerprint": self.fingerprint}


@dataclass
class SideEffectRecord:
    """A logged side-effect with the data needed to skip it on replay."""

    call_id: str
    tool_name: str
    args: dict[str, Any]
    result: Any
    timestamp: float = field(default_factory=time.time)
    is_replayable: bool = True  # False = must re-execute (e.g. network read)

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "args": self.args,
            "result": self.result,
            "timestamp": self.timestamp,
            "is_replayable": self.is_replayable,
        }


@dataclass
class SideEffectLog:
    """Append-only log of side-effects for replay + audit.

    The agent's policy proposes :class:`AgentDecision`s deterministically;
    the gated runner executes side-effecting tools and writes to this log.
    """

    records: list[SideEffectRecord] = field(default_factory=list)

    def append(self, record: SideEffectRecord) -> None:
        self.records.append(record)

    def find(self, call_id: str) -> Optional[SideEffectRecord]:
        for r in self.records:
            if r.call_id == call_id:
                return r
        return None

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(r.to_dict(), sort_keys=True) for r in self.records)


def decision_fingerprint(*, prompt: str, context: dict[str, Any], history: list[dict[str, Any]]) -> str:
    """Stable hash of the inputs that determine an agent decision.

    Two trajectories with the same fingerprint must produce the same
    :class:`AgentDecision` — this is what makes replay sound.
    """
    payload = json.dumps(
        {"prompt": prompt, "context": context, "history": history},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _PolicyProtocol(Protocol):
    """An agent policy is any callable returning a deterministic decision."""

    def __call__(self, *, prompt: str, context: dict[str, Any], history: list[dict[str, Any]]) -> AgentDecision: ...


class PureFunctionAgent:
    """Base class enforcing the pure-function contract structurally.

    Subclasses implement ``policy(...)`` (pure). The base class wires the
    fingerprint, manages the side-effect log, and provides ``replay(...)``.
    """

    def __init__(self, *, policy: Optional[_PolicyProtocol] = None) -> None:
        self.log = SideEffectLog()
        self._policy = policy

    def policy(self, *, prompt: str, context: dict[str, Any], history: list[dict[str, Any]]) -> AgentDecision:
        """Override or pass a policy in __init__. Default raises."""
        if self._policy is None:
            raise NotImplementedError("Subclass PureFunctionAgent and override policy(...)")
        return self._policy(prompt=prompt, context=context, history=history)

    def decide(self, *, prompt: str, context: dict[str, Any], history: list[dict[str, Any]]) -> AgentDecision:
        """Make a decision; stamp the fingerprint."""
        fp = decision_fingerprint(prompt=prompt, context=context, history=history)
        decision = self.policy(prompt=prompt, context=context, history=history)
        decision.fingerprint = fp
        return decision

    def execute_side_effect(
        self,
        *,
        call_id: str,
        tool_name: str,
        args: dict[str, Any],
        runner: Callable[[dict[str, Any]], Any],
        is_replayable: bool = True,
    ) -> Any:
        """Run a side-effecting tool through the gated path; log the result."""
        result = runner(args)
        self.log.append(
            SideEffectRecord(
                call_id=call_id,
                tool_name=tool_name,
                args=args,
                result=result,
                is_replayable=is_replayable,
            )
        )
        return result


@dataclass
class TrajectoryReplay:
    """Replay a recorded trajectory without re-executing side-effects.

    Walks the log in order; for each record, returns the recorded result if
    ``is_replayable`` is True, otherwise re-runs the supplied ``runner``.
    """

    log: SideEffectLog

    def replay_call(self, *, call_id: str, runner: Optional[Callable[[dict[str, Any]], Any]] = None) -> Any:
        record = self.log.find(call_id)
        if record is None:
            raise KeyError(f"call_id {call_id!r} not in log")
        if record.is_replayable:
            return record.result
        if runner is None:
            raise ValueError(f"call_id {call_id!r} marked non-replayable but no runner supplied")
        return runner(record.args)

    def verify_decision(
        self,
        *,
        agent: PureFunctionAgent,
        prompt: str,
        context: dict[str, Any],
        history: list[dict[str, Any]],
        expected_fingerprint: str,
    ) -> bool:
        """Re-run the policy; assert the fingerprint matches.

        Used in sabotage-detection: a trajectory whose policy doesn't reproduce
        the expected fingerprint is candidate for review.
        """
        decision = agent.decide(prompt=prompt, context=context, history=history)
        return decision.fingerprint == expected_fingerprint

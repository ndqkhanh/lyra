"""L311-1 — :class:`Executor` adapters bridging :class:`LeadSession` to
real LLM-backed runtimes.

The :class:`LeadSession` runtime accepts any callable matching the
:type:`Executor` signature ``(TeammateSpec, str) -> str``. In tests
that callable is a deterministic stub; in production it should be a
real LLM-driven loop. This module supplies two stock adapters:

* :class:`AgentLoopExecutor` — wraps a per-teammate
  :class:`~lyra_core.agent.loop.AgentLoop` (one fresh
  :class:`AgentLoop` per teammate, isolated context).
* :class:`CallableLLMExecutor` — wraps a bare callable
  ``(prompt: str) -> str`` (e.g. an :class:`AnthropicLLM` ``chat`` wrap)
  for cases that don't need full loop semantics.

Both adapters honor :class:`TeammateSpec.model` by deferring to the
caller-supplied per-model factory: callers pass a
``loop_factory(teammate_spec) -> AgentLoop`` and the adapter does the
rest. The seam keeps the adapter LLM-provider agnostic and lets each
teammate hold its own model slot ("fast" vs "smart" vs explicit slug).

The adapter also pre-pins the teammate's persona / subagent into the
session prompt: every spawned teammate reads its
:class:`TeammateSpec.persona` (or ``subagent`` if no inline persona)
before its first user message so the worktree-isolated session sees a
focused brief.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from .agent_teams import Executor, TeammateSpec


class _SupportsRunConversation(Protocol):
    """Minimal protocol the AgentLoop adapter needs."""

    def run_conversation(self, user_text: str, *, session_id: str) -> Any: ...


LoopFactory = Callable[[TeammateSpec], _SupportsRunConversation]
"""Caller-provided factory: spec → fresh AgentLoop. The adapter never
caches loops across calls — one fresh loop per ``execute()`` so each
turn starts with a clean context. Production callers can implement
their own caching policy by returning a wrapper that re-uses an inner
loop while still presenting a fresh session_id."""


# ---- AgentLoopExecutor -----------------------------------------------


@dataclass
class AgentLoopExecutor:
    """Wraps a per-teammate :class:`AgentLoop` as an :type:`Executor`.

    Each call constructs a fresh loop via ``loop_factory`` and runs one
    turn. Persona injection is done by prepending the teammate's
    persona (or subagent name) to the user payload as a *system header*
    block so the LLM sees the role brief on every turn.

    Why prepend instead of using a real system prompt? Because the
    :class:`AgentLoop` API takes ``user_text`` only — system prompts
    are usually wired through the LLM provider config. We prepend a
    structured marker instead so the wrapped LLM still sees the
    persona without us having to thread a system-prompt slot
    everywhere.
    """

    loop_factory: LoopFactory
    persona_template: str = (
        "[teammate=%(name)s, model=%(model)s, subagent=%(subagent)s]\n"
        "%(persona)s\n\n"
        "[task]\n%(task)s\n"
    )
    session_id_prefix: str = "team"
    extract_text: Callable[[Any], str] = field(
        default=lambda result: getattr(result, "final_text", "") or ""
    )

    def __call__(self, spec: TeammateSpec, body: str) -> str:
        loop = self.loop_factory(spec)
        text = self.persona_template % {
            "name": spec.name,
            "model": spec.model,
            "subagent": spec.subagent or "—",
            "persona": (spec.persona or "Default Lyra teammate persona.").strip(),
            "task": body,
        }
        result = loop.run_conversation(
            text, session_id=f"{self.session_id_prefix}.{spec.name}"
        )
        return self.extract_text(result)


# ---- CallableLLMExecutor ---------------------------------------------


@dataclass
class CallableLLMExecutor:
    """Wraps a bare ``(prompt: str) -> str`` callable as an :type:`Executor`.

    Useful when the wrapped LLM is already a high-level chat client
    that handles tool dispatch internally (e.g.
    :class:`AnthropicLLM.chat` adapter), and the team runtime doesn't
    need the full :class:`AgentLoop` semantics.
    """

    chat_fn: Callable[[str], str]
    persona_template: str = (
        "[teammate=%(name)s, model=%(model)s]\n"
        "%(persona)s\n\n"
        "[task]\n%(task)s\n"
    )

    def __call__(self, spec: TeammateSpec, body: str) -> str:
        prompt = self.persona_template % {
            "name": spec.name,
            "model": spec.model,
            "persona": (spec.persona or "Default Lyra teammate persona.").strip(),
            "task": body,
        }
        return str(self.chat_fn(prompt))


# ---- factory helpers --------------------------------------------------


def make_executor_from_factory(loop_factory: LoopFactory) -> Executor:
    """Convenience factory — wraps a loop factory as an Executor."""
    return AgentLoopExecutor(loop_factory=loop_factory)


def make_executor_from_chat(chat_fn: Callable[[str], str]) -> Executor:
    """Convenience factory — wraps a bare chat callable as an Executor."""
    return CallableLLMExecutor(chat_fn=chat_fn)


__all__ = [
    "AgentLoopExecutor",
    "CallableLLMExecutor",
    "LoopFactory",
    "make_executor_from_chat",
    "make_executor_from_factory",
]

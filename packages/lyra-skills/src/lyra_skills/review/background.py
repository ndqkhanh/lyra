"""Forked-loop skill review — ported from hermes-agent.

``spawn_skill_review(loop, *, session_id)`` runs a nested
:class:`lyra_core.agent.loop.AgentLoop` with the
:data:`SKILL_REVIEW_PROMPT` as the user turn. The forked loop shares the
parent's ``llm``, ``tools`` and ``store`` but gets its own small budget
and an empty plugin list so it cannot spawn further reviews or interact
with the REPL driver.

The review is fire-and-forget from the agent's perspective: the parent
``AgentLoop`` submits the call to its ``review_executor`` and continues.
In tests we wire a synchronous executor so behavior is deterministic.
"""

from __future__ import annotations

from typing import Any

SKILL_REVIEW_PROMPT = (
    "You just completed an agentic task. Review the turn you just finished "
    "and decide whether any reusable *skill* should be created, updated, or "
    "removed. If yes, call the `skill_manage` tool with the appropriate op "
    "(create, patch, list, delete). If the turn does not warrant a change, "
    "reply with a one-line note and stop. Keep the review short — this runs "
    "in the background and must not block the user."
)


def spawn_skill_review(loop: Any, *, session_id: str) -> str:
    """Run a forked skill-review AgentLoop and return its final text.

    The fork is safe by construction: it inherits the parent's
    ``tools`` (so ``skill_manage`` is callable) but runs with an empty
    plugin list and a fresh :class:`IterationBudget`, so neither side
    can re-trigger the other's review.
    """
    from lyra_core.agent.loop import AgentLoop, IterationBudget

    fork = AgentLoop(
        llm=loop.llm,
        tools=loop.tools,
        store=loop.store,
        plugins=[],
        budget=IterationBudget(max=5),
        skill_nudge_interval=10**9,  # effectively disabled in the fork
        review_executor=None,
    )
    child_session = f"{session_id}::skill-review"
    result = fork.run_conversation(SKILL_REVIEW_PROMPT, session_id=child_session)
    return result.final_text or ""


__all__ = ["SKILL_REVIEW_PROMPT", "spawn_skill_review"]

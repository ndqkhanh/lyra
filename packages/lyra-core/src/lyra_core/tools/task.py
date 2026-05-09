"""Task-tool subagent fork (opencode pattern, Python port).

Exposes :func:`task` — an LLM-callable tool that forks a *child*
:class:`AgentLoop` for a focused subtask, isolating budget and token
accounting from the parent turn. Mirrors ``packages/opencode/src/tool/task.ts``
but written in Python against ``lyra_core.agent.loop.AgentLoop``.

Subagent types:

- ``general``  — general-purpose nested agent (default)
- ``plan``     — planning-focused; typically read-only tools, higher max iter
- ``explore``  — read-only exploration fork; bans writes/shell mutation

The tool returns a :class:`TaskResult`-shaped dict so LLM-facing JSON is
stable and agent plans can be composed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping

from ..agent.loop import AgentLoop, IterationBudget, TurnResult

SubagentType = Literal["general", "plan", "explore"]

_DEFAULT_BUDGETS: Mapping[str, int] = {
    "general": 15,
    "plan": 25,
    "explore": 10,
}


@dataclass
class TaskResult:
    """Serializable result shape for the :func:`task` tool."""

    subagent_type: str
    final_text: str
    iterations: int
    tool_calls: list[dict]
    stopped_by: str

    def to_dict(self) -> dict:
        return {
            "subagent_type": self.subagent_type,
            "final_text": self.final_text,
            "iterations": self.iterations,
            "tool_calls": self.tool_calls,
            "stopped_by": self.stopped_by,
        }


def _filter_tools(
    tools: Mapping[str, Callable[..., Any]] | None,
    subagent_type: SubagentType,
) -> dict[str, Callable[..., Any]]:
    """Produce the tool set exposed to a child agent.

    ``explore`` forbids write/mutation-shaped tools; ``plan`` is
    permissive but avoids the task-tool itself (no infinite recursion);
    ``general`` forwards everything except ``task`` to prevent fork
    bombs on buggy models.
    """
    if not tools:
        return {}
    banned = {"task"}
    if subagent_type == "explore":
        # Conservative deny-list of names commonly associated with writes.
        banned.update({"write", "bash", "shell", "edit", "apply_patch", "patch"})
    return {name: fn for name, fn in tools.items() if name not in banned}


def make_task_tool(
    *,
    llm: Any,
    tools: Mapping[str, Callable[..., Any]] | None,
    store: Any,
    plugins: list | None = None,
    parent_session_id: str | None = None,
    worktree_manager: Any | None = None,
) -> Callable[..., dict]:
    """Build the LLM-callable ``task`` tool bound to the parent context.

    The returned callable is intended to be registered in the parent
    ``AgentLoop.tools`` mapping under the name ``"task"``.

    Args:
        worktree_manager: Optional object implementing
            ``allocate(*, scope_id) -> Worktree`` and ``cleanup(wt)``.
            When supplied and the caller passes ``worktree=True``, the
            child agent runs against a freshly allocated git worktree so
            that any mutations are scoped to the fork. Cleanup is
            guaranteed even if the child raises.
    """

    def task(
        description: str,
        *,
        subagent_type: SubagentType = "general",
        max_iterations: int | None = None,
        worktree: bool = False,
    ) -> dict:
        """Fork a focused subagent for a scoped task.

        Args:
            description: One-line task description handed to the child
                agent as its initial user turn.
            subagent_type: Which subagent preset to run.
            max_iterations: Optional per-fork LLM call cap; defaults to
                the preset for ``subagent_type``.
            worktree: If True, allocate a git worktree for the fork via
                ``worktree_manager`` and tear it down afterwards.

        Returns:
            A :class:`TaskResult`-shaped dict (see ``to_dict``).
        """
        if worktree and worktree_manager is None:
            raise ValueError(
                "task(worktree=True) requires a worktree_manager to be "
                "passed to make_task_tool(...)"
            )

        budget = IterationBudget(
            max=int(max_iterations or _DEFAULT_BUDGETS.get(subagent_type, 15))
        )
        session_id = f"{parent_session_id or 'session'}::task::{subagent_type}"

        allocated_wt = None
        if worktree and worktree_manager is not None:
            allocated_wt = worktree_manager.allocate(scope_id=session_id)

        try:
            child = AgentLoop(
                llm=llm,
                tools=_filter_tools(tools, subagent_type),
                store=store,
                plugins=list(plugins or []),
                budget=budget,
            )
            result: TurnResult = child.run_conversation(
                description, session_id=session_id
            )
        finally:
            if allocated_wt is not None and worktree_manager is not None:
                worktree_manager.cleanup(allocated_wt)

        return TaskResult(
            subagent_type=subagent_type,
            final_text=result.final_text,
            iterations=result.iterations,
            tool_calls=result.tool_calls,
            stopped_by=result.stopped_by,
        ).to_dict()

    task.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "task",
        "description": (
            "Fork a scoped subagent for a focused task. Use for "
            "exploration, planning, or anything that would otherwise "
            "blow the parent's iteration budget."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "subagent_type": {
                    "type": "string",
                    "enum": ["general", "plan", "explore"],
                    "default": "general",
                },
                "max_iterations": {"type": "integer", "minimum": 1, "maximum": 100},
                "worktree": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Isolate the fork inside a git worktree when a "
                        "worktree_manager is wired at tool construction."
                    ),
                },
            },
            "required": ["description"],
        },
    }
    return task


__all__ = ["TaskResult", "SubagentType", "make_task_tool"]

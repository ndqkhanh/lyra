"""harness_core.teams — Agent-Teams primitives (lead-and-spokes coordination).

Per the README's File **250** (Anthropic Agent Teams) — extracts the four
reusable primitives from the experimental Claude Code v2.1.32+ feature:

    1. Lead-and-spokes runtime — one lead agent dispatches to N spokes.
    2. Shared task list — common task queue all spokes claim from.
    3. Peer mailbox — agent-to-agent messaging (point-to-point + broadcast).
    4. Cost accounting — track per-agent + team-aggregate token spend
       (composes with :class:`harness_core.evals.BudgetController` to surface
       the 7×-multiplier overhead Anthropic flagged in plan-mode).

Composes with:
    - :mod:`harness_core.orchestration` — agents are :class:`PureFunctionAgent`
      policies; team coordination is replayable.
    - :mod:`harness_core.isolation` — each agent gets its own context
      namespace; cross-agent reads require explicit grants.
    - :mod:`harness_core.evals.equal_budget` — team budget is shared; per-agent
      sub-budgets enforce fair-share.

Used by Syndicate (the multi-agent platform), Polaris (Chief-Editor research
team), Mentat-Learn (multi-channel persona spokes), Lyra subagents.
"""
from __future__ import annotations

from .mailbox import Mailbox, MailboxRouter, Message
from .task_list import Task, TaskList, TaskStatus
from .team import AgentRole, AgentTeam

__all__ = [
    "AgentRole",
    "AgentTeam",
    "Mailbox",
    "MailboxRouter",
    "Message",
    "Task",
    "TaskList",
    "TaskStatus",
]

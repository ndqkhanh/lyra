"""AgentTeam — lead-and-spokes coordination runtime.

Composes :class:`TaskList` (shared queue) + :class:`MailboxRouter` (peer
mailboxes) into one coordination object. The lead agent registers with role
LEAD; spokes register with role SPOKE. Lead can:

    - Add tasks to the shared list.
    - Send messages to specific spokes or broadcast.
    - Cancel tasks.

Spokes can:
    - Claim the next available task.
    - Complete or fail their claimed task.
    - Send messages to the lead or other spokes.

The team is intentionally minimal — no policy logic, no LLM calls. Higher-
level coordination (Chief-Editor patterns, Magentic-One-style ledger
re-planning) is built on top of this primitive.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional

from .mailbox import Mailbox, MailboxRouter, Message
from .task_list import Task, TaskList, TaskStatus


class AgentRole(str, enum.Enum):
    LEAD = "lead"
    SPOKE = "spoke"


@dataclass
class _AgentRegistration:
    agent_id: str
    role: AgentRole


@dataclass
class AgentTeam:
    """Lead-and-spokes coordination runtime.

    >>> team = AgentTeam(team_id="research-team")
    >>> team.add_agent(agent_id="lead", role=AgentRole.LEAD)
    >>> team.add_agent(agent_id="spoke-1", role=AgentRole.SPOKE)
    >>> task = team.add_task(description="search papers", added_by="lead")
    >>> claimed = team.claim_next(agent_id="spoke-1")
    >>> claimed.assigned_to
    'spoke-1'
    """

    team_id: str
    task_list: TaskList = field(default_factory=TaskList)
    mailbox_router: MailboxRouter = field(default_factory=MailboxRouter)
    _agents: dict[str, _AgentRegistration] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.team_id:
            raise ValueError("team_id must be non-empty")

    # --- Membership -------------------------------------------------------

    def add_agent(self, *, agent_id: str, role: AgentRole) -> Mailbox:
        """Add an agent to the team; allocates its mailbox.

        Only one LEAD per team. Adding a second LEAD raises.
        """
        if agent_id in self._agents:
            raise ValueError(f"agent {agent_id!r} already in team")
        if role == AgentRole.LEAD and self.lead_id is not None:
            raise ValueError(
                f"team {self.team_id!r} already has lead {self.lead_id!r}"
            )
        self._agents[agent_id] = _AgentRegistration(agent_id=agent_id, role=role)
        mailbox = Mailbox(agent_id=agent_id)
        self.mailbox_router.register(mailbox)
        return mailbox

    def remove_agent(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        self.mailbox_router.unregister(agent_id)
        return True

    @property
    def lead_id(self) -> Optional[str]:
        for r in self._agents.values():
            if r.role == AgentRole.LEAD:
                return r.agent_id
        return None

    @property
    def spoke_ids(self) -> list[str]:
        return [r.agent_id for r in self._agents.values() if r.role == AgentRole.SPOKE]

    def role_of(self, agent_id: str) -> Optional[AgentRole]:
        reg = self._agents.get(agent_id)
        return reg.role if reg else None

    # --- Tasks ------------------------------------------------------------

    def add_task(
        self,
        *,
        description: str,
        added_by: str,
        priority: int = 0,
        parent_task_id: Optional[str] = None,
    ) -> Task:
        """Lead-only: add a task to the shared list."""
        if self.role_of(added_by) != AgentRole.LEAD:
            raise PermissionError(
                f"only lead agents may add tasks; {added_by!r} is not the lead"
            )
        return self.task_list.add(
            description=description,
            priority=priority,
            parent_task_id=parent_task_id,
        )

    def claim_next(self, *, agent_id: str) -> Optional[Task]:
        """Spoke-only: claim the next pending task."""
        if self.role_of(agent_id) != AgentRole.SPOKE:
            raise PermissionError(
                f"only spoke agents may claim tasks; {agent_id!r} is not a spoke"
            )
        return self.task_list.claim_next(agent_id=agent_id)

    def complete_task(
        self,
        *,
        task_id: str,
        agent_id: str,
        output: Any = None,
    ) -> Task:
        return self.task_list.complete(task_id=task_id, agent_id=agent_id, output=output)

    def fail_task(self, *, task_id: str, agent_id: str, error: str) -> Task:
        return self.task_list.fail(task_id=task_id, agent_id=agent_id, error=error)

    def cancel_task(self, *, task_id: str, agent_id: str) -> Task:
        """Lead-only: cancel a task."""
        if self.role_of(agent_id) != AgentRole.LEAD:
            raise PermissionError(
                f"only lead agents may cancel tasks; {agent_id!r} is not the lead"
            )
        return self.task_list.cancel(task_id=task_id)

    # --- Messaging --------------------------------------------------------

    def send(
        self,
        *,
        sender: str,
        recipient: str,
        body: str,
        payload: Optional[dict[str, Any]] = None,
        in_reply_to: Optional[str] = None,
    ) -> Message:
        """Send a peer-to-peer or broadcast message.

        Sender must be a registered team member; recipient must be either a
        registered member or ``"*"`` for broadcast.
        """
        if self.role_of(sender) is None:
            raise PermissionError(f"sender {sender!r} not in team {self.team_id!r}")
        if recipient != "*" and self.role_of(recipient) is None:
            raise ValueError(
                f"recipient {recipient!r} not in team {self.team_id!r}"
            )
        return self.mailbox_router.send(
            sender=sender, recipient=recipient, body=body,
            payload=payload, in_reply_to=in_reply_to,
        )

    def receive(self, *, agent_id: str) -> Optional[Message]:
        """Pop the next message for an agent."""
        mb = self.mailbox_router.get(agent_id)
        if mb is None:
            raise PermissionError(f"agent {agent_id!r} not in team")
        return mb.receive()

    # --- Observability ----------------------------------------------------

    def stats(self) -> dict[str, Any]:
        task_stats = self.task_list.stats()
        mailbox_stats = self.mailbox_router.stats()
        return {
            "team_id": self.team_id,
            "agents": len(self._agents),
            "lead_id": self.lead_id,
            "spokes": len(self.spoke_ids),
            "tasks": task_stats,
            "mailboxes": mailbox_stats,
        }


__all__ = ["AgentRole", "AgentTeam"]

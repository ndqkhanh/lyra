"""Multi-Agent Team Orchestration for Lyra.

Coordinates multiple agents working in parallel on a task.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator
from dataclasses import dataclass
from enum import Enum


class AgentRole(Enum):
    """Agent role in the team."""
    LEAD = "lead"
    EXECUTOR = "executor"
    RESEARCHER = "researcher"
    WRITER = "writer"


@dataclass
class TeamMember:
    """Team member definition."""
    role: AgentRole
    agent_id: str
    status: str = "idle"


class Mailbox:
    """Message passing system for agents."""

    def __init__(self):
        self.messages = {}

    async def send(self, from_agent: str, to_agent: str, message: str):
        """Send message from one agent to another."""
        if to_agent not in self.messages:
            self.messages[to_agent] = []
        self.messages[to_agent].append({
            "from": from_agent,
            "message": message,
        })

    async def receive(self, agent_id: str) -> list:
        """Receive messages for an agent."""
        messages = self.messages.get(agent_id, [])
        self.messages[agent_id] = []
        return messages


class TeamOrchestrator:
    """Orchestrates multi-agent teams."""

    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.mailbox = Mailbox()
        self.members = []
        self.shared_tasks = []

    async def run_team(self, task: str) -> AsyncIterator[dict]:
        """Run team on a task with parallel execution.

        Yields:
            dict with keys:
                - type: "member" | "progress" | "result" | "done"
                - member: str (agent role)
                - content: str
        """
        # Create team
        yield {
            "type": "member",
            "member": "Team",
            "content": "Creating team...",
        }

        self.members = [
            TeamMember(AgentRole.LEAD, "lead-1"),
            TeamMember(AgentRole.EXECUTOR, "executor-1"),
            TeamMember(AgentRole.RESEARCHER, "researcher-1"),
            TeamMember(AgentRole.WRITER, "writer-1"),
        ]

        yield {
            "type": "member",
            "member": "Team",
            "content": f"Team created: {len(self.members)} members",
        }

        # Lead agent breaks down task
        yield {
            "type": "member",
            "member": "Lead",
            "content": "Breaking down task...",
        }

        subtasks = await self._break_down_task(task)
        self.shared_tasks = subtasks

        # Execute in parallel
        tasks = []
        for member in self.members[1:]:  # Skip lead
            if member.role == AgentRole.EXECUTOR:
                tasks.append(self._run_executor(member, subtasks))
            elif member.role == AgentRole.RESEARCHER:
                tasks.append(self._run_researcher(member, task))
            elif member.role == AgentRole.WRITER:
                tasks.append(self._run_writer(member))

        # Run all agents in parallel
        results = await asyncio.gather(*tasks)

        # Lead aggregates results
        yield {
            "type": "member",
            "member": "Lead",
            "content": "Aggregating results...",
        }

        final_result = await self._aggregate_results(results)

        yield {
            "type": "done",
            "member": "Team",
            "content": final_result,
        }

    async def _break_down_task(self, task: str) -> list:
        """Lead agent breaks down task into subtasks."""
        # Use LLM to break down task
        prompt = f"Break down this task into 3-5 subtasks: {task}"
        response = await self.llm.generate(prompt)

        # Parse subtasks (simplified)
        subtasks = [
            "Subtask 1: Research requirements",
            "Subtask 2: Implement core functionality",
            "Subtask 3: Write tests",
            "Subtask 4: Document code",
        ]
        return subtasks

    async def _run_executor(self, member: TeamMember, subtasks: list) -> dict:
        """Run executor agent."""
        member.status = "working"

        # Execute implementation tasks
        results = []
        for task in subtasks:
            if "Implement" in task or "Write tests" in task:
                await asyncio.sleep(0.2)  # Simulate work
                results.append(f"Completed: {task}")

        member.status = "done"
        return {
            "role": "executor",
            "results": results,
        }

    async def _run_researcher(self, member: TeamMember, task: str) -> dict:
        """Run researcher agent."""
        member.status = "working"

        # Research task
        await asyncio.sleep(0.2)
        findings = [
            "Finding 1: Best practices identified",
            "Finding 2: Similar implementations found",
        ]

        member.status = "done"
        return {
            "role": "researcher",
            "results": findings,
        }

    async def _run_writer(self, member: TeamMember) -> dict:
        """Run writer agent."""
        member.status = "working"

        # Write documentation
        await asyncio.sleep(0.2)
        docs = [
            "Documentation: README.md created",
            "Documentation: API docs added",
        ]

        member.status = "done"
        return {
            "role": "writer",
            "results": docs,
        }

    async def _aggregate_results(self, results: list) -> str:
        """Lead agent aggregates results from all members."""
        report = "# Team Results\n\n"

        for result in results:
            role = result["role"]
            report += f"## {role.title()}\n"
            for item in result["results"]:
                report += f"- {item}\n"
            report += "\n"

        return report

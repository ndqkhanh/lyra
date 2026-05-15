"""Multi-agent orchestration - OpenAgentd inspired lazy-spawn pattern."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mailbox import TeamMailbox
from .member import TeamMember


@dataclass
class Blueprint:
    """Agent blueprint definition."""

    name: str
    source_path: Path
    description: str
    capabilities: list[str]


class LyraTeam:
    """Multi-agent research team with lazy-spawn members."""

    def __init__(self, blueprints_dir: Path | None = None):
        self.blueprints_dir = blueprints_dir or Path(".lyra/blueprints")
        self.blueprints: dict[str, Blueprint] = {}
        self.members: dict[str, TeamMember] = {}
        self.mailbox = TeamMailbox()
        self._instance_counters: dict[str, int] = {}

        # Load blueprints
        self._load_blueprints()

    def _load_blueprints(self) -> None:
        """Load agent blueprints from disk."""
        if not self.blueprints_dir.exists():
            return

        for blueprint_file in self.blueprints_dir.glob("*.md"):
            blueprint = self._parse_blueprint(blueprint_file)
            if blueprint:
                self.blueprints[blueprint.name] = blueprint

    def _parse_blueprint(self, path: Path) -> Blueprint | None:
        """Parse blueprint from markdown file.

        Args:
            path: Path to blueprint file

        Returns:
            Blueprint or None if invalid
        """
        try:
            content = path.read_text()
            # TODO: Parse frontmatter for capabilities
            name = path.stem
            return Blueprint(
                name=name,
                source_path=path,
                description=f"Agent blueprint: {name}",
                capabilities=[],
            )
        except Exception:
            return None

    async def spawn(
        self, blueprint_name: str, instance_id: int | None = None
    ) -> TeamMember:
        """Materialize a member instance from blueprint.

        Args:
            blueprint_name: Name of blueprint to spawn
            instance_id: Optional instance ID (auto-assigned if None)

        Returns:
            Team member instance
        """
        if blueprint_name not in self.blueprints:
            raise ValueError(f"Blueprint not found: {blueprint_name}")

        blueprint = self.blueprints[blueprint_name]

        # Auto-assign instance ID
        if instance_id is None:
            if blueprint_name not in self._instance_counters:
                self._instance_counters[blueprint_name] = 0
            self._instance_counters[blueprint_name] += 1
            instance_id = self._instance_counters[blueprint_name]

        # Build instance handle
        handle = f"{blueprint_name}#{instance_id}"

        # Check if already spawned
        if handle in self.members:
            return self.members[handle]

        # Create member
        member = TeamMember(
            name=handle,
            blueprint=blueprint,
            mailbox=self.mailbox,
        )

        # Register with mailbox
        self.mailbox.register(handle, member.activate)

        # Store member
        self.members[handle] = member

        return member

    async def send_message(
        self, to: str, content: str, from_agent: str
    ) -> None:
        """Send message via mailbox.

        Args:
            to: Target agent handle
            content: Message content
            from_agent: Sender agent name
        """
        await self.mailbox.send(
            to=to,
            message={"content": content, "from": from_agent},
        )

    async def broadcast(self, content: str, from_agent: str) -> None:
        """Broadcast message to all members.

        Args:
            content: Message content
            from_agent: Sender agent name
        """
        await self.mailbox.broadcast(
            message={"content": content, "from": from_agent},
            exclude=from_agent,
        )

    def list_blueprints(self) -> list[str]:
        """List available blueprint names."""
        return list(self.blueprints.keys())

    def list_members(self) -> list[str]:
        """List active member handles."""
        return list(self.members.keys())

    async def dismiss(self, handle: str) -> None:
        """Dismiss a member instance.

        Args:
            handle: Member handle to dismiss
        """
        if handle in self.members:
            member = self.members[handle]
            await member.shutdown()
            del self.members[handle]
            self.mailbox.unregister(handle)

    async def shutdown(self) -> None:
        """Shutdown all members and cleanup."""
        for handle in list(self.members.keys()):
            await self.dismiss(handle)

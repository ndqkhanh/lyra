"""
Team Configuration - Team collaboration and shared settings.

Features:
- Shared configuration profiles
- Team-wide prompt templates
- Shared skill library
- Team analytics
- Usage quotas and limits
- Role-based access control
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class UserRole(Enum):
    """User role."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


@dataclass
class TeamMember:
    """Team member."""

    user_id: str
    username: str
    email: str
    role: UserRole
    joined_at: datetime = field(default_factory=datetime.now)


@dataclass
class UsageQuota:
    """Usage quota."""

    tokens_limit: int
    cost_limit: float
    tokens_used: int = 0
    cost_used: float = 0.0


@dataclass
class PromptTemplate:
    """Prompt template."""

    id: str
    name: str
    description: str
    template: str
    variables: List[str] = field(default_factory=list)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TeamConfig:
    """Team configuration."""

    team_id: str
    team_name: str
    created_at: datetime
    settings: Dict[str, Any] = field(default_factory=dict)
    members: List[TeamMember] = field(default_factory=list)
    quotas: Dict[str, UsageQuota] = field(default_factory=dict)


class TeamManager:
    """
    Team manager.

    Features:
    - Team configuration
    - Member management
    - Shared templates
    - Usage quotas
    - Role-based access
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize team manager.

        Args:
            storage_path: Path to team storage directory
        """
        self.storage_path = storage_path or Path.home() / ".lyra" / "teams"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_team: Optional[TeamConfig] = None
        self.templates: List[PromptTemplate] = []

    def create_team(
        self,
        team_id: str,
        team_name: str,
        settings: Optional[Dict[str, Any]] = None,
    ) -> TeamConfig:
        """
        Create new team.

        Args:
            team_id: Team ID
            team_name: Team name
            settings: Team settings

        Returns:
            Team configuration
        """
        config = TeamConfig(
            team_id=team_id,
            team_name=team_name,
            created_at=datetime.now(),
            settings=settings or {},
        )
        self.current_team = config
        return config

    def add_member(
        self,
        user_id: str,
        username: str,
        email: str,
        role: UserRole = UserRole.MEMBER,
    ) -> TeamMember:
        """
        Add team member.

        Args:
            user_id: User ID
            username: Username
            email: Email
            role: User role

        Returns:
            Team member
        """
        if not self.current_team:
            raise ValueError("No active team")

        member = TeamMember(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
        )
        self.current_team.members.append(member)
        return member

    def remove_member(self, user_id: str):
        """
        Remove team member.

        Args:
            user_id: User ID
        """
        if not self.current_team:
            raise ValueError("No active team")

        self.current_team.members = [
            m for m in self.current_team.members if m.user_id != user_id
        ]

    def update_member_role(self, user_id: str, role: UserRole):
        """
        Update member role.

        Args:
            user_id: User ID
            role: New role
        """
        if not self.current_team:
            raise ValueError("No active team")

        for member in self.current_team.members:
            if member.user_id == user_id:
                member.role = role
                break

    def set_quota(self, user_id: str, tokens_limit: int, cost_limit: float):
        """
        Set usage quota for user.

        Args:
            user_id: User ID
            tokens_limit: Token limit
            cost_limit: Cost limit
        """
        if not self.current_team:
            raise ValueError("No active team")

        quota = UsageQuota(
            tokens_limit=tokens_limit,
            cost_limit=cost_limit,
        )
        self.current_team.quotas[user_id] = quota

    def update_usage(self, user_id: str, tokens: int, cost: float):
        """
        Update usage for user.

        Args:
            user_id: User ID
            tokens: Tokens used
            cost: Cost incurred
        """
        if not self.current_team:
            raise ValueError("No active team")

        if user_id in self.current_team.quotas:
            quota = self.current_team.quotas[user_id]
            quota.tokens_used += tokens
            quota.cost_used += cost

    def check_quota(self, user_id: str) -> bool:
        """
        Check if user is within quota.

        Args:
            user_id: User ID

        Returns:
            True if within quota
        """
        if not self.current_team:
            return True

        if user_id not in self.current_team.quotas:
            return True

        quota = self.current_team.quotas[user_id]
        return (
            quota.tokens_used < quota.tokens_limit
            and quota.cost_used < quota.cost_limit
        )

    def add_template(
        self,
        template_id: str,
        name: str,
        description: str,
        template: str,
        variables: Optional[List[str]] = None,
        created_by: str = "",
    ) -> PromptTemplate:
        """
        Add prompt template.

        Args:
            template_id: Template ID
            name: Template name
            description: Template description
            template: Template text
            variables: Template variables
            created_by: Creator user ID

        Returns:
            Prompt template
        """
        prompt_template = PromptTemplate(
            id=template_id,
            name=name,
            description=description,
            template=template,
            variables=variables or [],
            created_by=created_by,
        )
        self.templates.append(prompt_template)
        return prompt_template

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        Get template by ID.

        Args:
            template_id: Template ID

        Returns:
            Prompt template or None
        """
        for template in self.templates:
            if template.id == template_id:
                return template
        return None

    def list_templates(self) -> List[PromptTemplate]:
        """
        List all templates.

        Returns:
            List of templates
        """
        return self.templates

    def save_team(self):
        """Save team configuration to storage."""
        if not self.current_team:
            raise ValueError("No active team")

        team_data = {
            "team_id": self.current_team.team_id,
            "team_name": self.current_team.team_name,
            "created_at": self.current_team.created_at.isoformat(),
            "settings": self.current_team.settings,
            "members": [
                {
                    "user_id": m.user_id,
                    "username": m.username,
                    "email": m.email,
                    "role": m.role.value,
                    "joined_at": m.joined_at.isoformat(),
                }
                for m in self.current_team.members
            ],
            "quotas": {
                user_id: {
                    "tokens_limit": quota.tokens_limit,
                    "cost_limit": quota.cost_limit,
                    "tokens_used": quota.tokens_used,
                    "cost_used": quota.cost_used,
                }
                for user_id, quota in self.current_team.quotas.items()
            },
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "template": t.template,
                    "variables": t.variables,
                    "created_by": t.created_by,
                    "created_at": t.created_at.isoformat(),
                }
                for t in self.templates
            ],
        }

        team_file = self.storage_path / f"{self.current_team.team_id}.json"
        with open(team_file, "w") as f:
            json.dump(team_data, f, indent=2)

    def load_team(self, team_id: str):
        """
        Load team configuration from storage.

        Args:
            team_id: Team ID
        """
        team_file = self.storage_path / f"{team_id}.json"
        if not team_file.exists():
            raise FileNotFoundError(f"Team not found: {team_id}")

        with open(team_file, "r") as f:
            team_data = json.load(f)

        self.current_team = TeamConfig(
            team_id=team_data["team_id"],
            team_name=team_data["team_name"],
            created_at=datetime.fromisoformat(team_data["created_at"]),
            settings=team_data["settings"],
            members=[
                TeamMember(
                    user_id=m["user_id"],
                    username=m["username"],
                    email=m["email"],
                    role=UserRole(m["role"]),
                    joined_at=datetime.fromisoformat(m["joined_at"]),
                )
                for m in team_data["members"]
            ],
            quotas={
                user_id: UsageQuota(
                    tokens_limit=q["tokens_limit"],
                    cost_limit=q["cost_limit"],
                    tokens_used=q["tokens_used"],
                    cost_used=q["cost_used"],
                )
                for user_id, q in team_data["quotas"].items()
            },
        )

        self.templates = [
            PromptTemplate(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                template=t["template"],
                variables=t["variables"],
                created_by=t["created_by"],
                created_at=datetime.fromisoformat(t["created_at"]),
            )
            for t in team_data.get("templates", [])
        ]

    def get_team_analytics(self) -> Dict[str, Any]:
        """
        Get team analytics.

        Returns:
            Analytics dictionary
        """
        if not self.current_team:
            return {}

        total_tokens = sum(q.tokens_used for q in self.current_team.quotas.values())
        total_cost = sum(q.cost_used for q in self.current_team.quotas.values())

        role_counts = {}
        for member in self.current_team.members:
            role_counts[member.role.value] = role_counts.get(member.role.value, 0) + 1

        return {
            "team_id": self.current_team.team_id,
            "team_name": self.current_team.team_name,
            "total_members": len(self.current_team.members),
            "role_distribution": role_counts,
            "total_tokens_used": total_tokens,
            "total_cost": total_cost,
            "total_templates": len(self.templates),
        }

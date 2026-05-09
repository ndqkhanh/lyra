"""L312-2 — Ralph PRD: ``prd.json`` schema + serializer.

Mirrors snarktank's prd.json shape exactly so existing snarktank PRDs
work unmodified::

    {
      "project": "MyApp",
      "branchName": "ralph/task-priority",
      "description": "Task Priority System",
      "userStories": [
        {
          "id": "US-001",
          "title": "Add priority field",
          "description": "As a developer...",
          "acceptanceCriteria": ["...", "..."],
          "priority": 1,
          "passes": false,
          "notes": ""
        }
      ]
    }
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


__all__ = ["Prd", "UserStory", "load_prd", "save_prd"]


@dataclass
class UserStory:
    """One PRD user story with acceptance criteria and pass flag."""

    id: str
    title: str = ""
    description: str = ""
    acceptanceCriteria: list[str] = field(default_factory=list)
    priority: int = 100
    passes: bool = False
    notes: str = ""


@dataclass
class Prd:
    """Top-level PRD document."""

    project: str = ""
    branchName: str = ""
    description: str = ""
    userStories: list[UserStory] = field(default_factory=list)

    def next_pending_story(self) -> Optional[UserStory]:
        """Highest-priority story with ``passes=False`` (lowest priority int)."""
        pending = [s for s in self.userStories if not s.passes]
        if not pending:
            return None
        return min(pending, key=lambda s: s.priority)

    def all_passing(self) -> bool:
        return bool(self.userStories) and all(s.passes for s in self.userStories)

    def mark_pass(self, story_id: str) -> None:
        for s in self.userStories:
            if s.id == story_id:
                s.passes = True
                return
        raise KeyError(f"unknown story id {story_id!r}")

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "branchName": self.branchName,
            "description": self.description,
            "userStories": [
                {
                    "id": s.id, "title": s.title, "description": s.description,
                    "acceptanceCriteria": list(s.acceptanceCriteria),
                    "priority": s.priority, "passes": s.passes, "notes": s.notes,
                }
                for s in self.userStories
            ],
        }


def load_prd(path: Path | str) -> Prd:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    stories = [
        UserStory(
            id=str(s["id"]),
            title=str(s.get("title", "")),
            description=str(s.get("description", "")),
            acceptanceCriteria=list(s.get("acceptanceCriteria", []) or []),
            priority=int(s.get("priority", 100)),
            passes=bool(s.get("passes", False)),
            notes=str(s.get("notes", "")),
        )
        for s in (data.get("userStories") or [])
    ]
    return Prd(
        project=str(data.get("project", "")),
        branchName=str(data.get("branchName", "")),
        description=str(data.get("description", "")),
        userStories=stories,
    )


def save_prd(prd: Prd, path: Path | str) -> None:
    p = Path(path)
    p.write_text(json.dumps(prd.to_dict(), indent=2) + "\n", encoding="utf-8")

"""Automated changelog generation from git history and conventional commits."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class ChangeType(StrEnum):
    FEAT = "feat"
    FIX = "fix"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    CHORE = "chore"
    PERF = "perf"
    CI = "ci"


@dataclass(frozen=True)
class ChangeEntry:
    change_type: ChangeType
    scope: str
    description: str
    commit_hash: str = ""
    breaking: bool = False

    def to_markdown(self) -> str:
        prefix = "**BREAKING** " if self.breaking else ""
        scope_str = f"({self.scope})" if self.scope else ""
        return f"- {prefix}{self.change_type.value}{scope_str}: {self.description}"


@dataclass
class ChangelogGenerator:
    """Generates changelogs from commit messages following conventional commits."""

    version: str = "0.0.0"
    repo_path: str = "."
    _entries: list[ChangeEntry] = field(default_factory=list)

    CONVENTIONAL_PATTERN = re.compile(
        r"^(?P<type>feat|fix|refactor|docs|test|chore|perf|ci)"
        r"(?P<breaking>!)?"
        r"(?:\((?P<scope>[^)]+)\))?"
        r":\s*(?P<description>.+)$",
        re.IGNORECASE,
    )

    def parse_commit(self, message: str, commit_hash: str = "") -> ChangeEntry | None:
        match = self.CONVENTIONAL_PATTERN.match(message.strip())
        if not match:
            return None

        entry = ChangeEntry(
            change_type=ChangeType(match.group("type").lower()),
            scope=match.group("scope") or "",
            description=match.group("description").strip(),
            commit_hash=commit_hash,
            breaking=match.group("breaking") is not None,
        )
        self._entries.append(entry)
        return entry

    def parse_commits(self, messages: list[str]) -> list[ChangeEntry]:
        entries = []
        for msg in messages:
            entry = self.parse_commit(msg)
            if entry is not None:
                entries.append(entry)
        return entries

    def clear(self) -> None:
        self._entries.clear()

    def generate(self, version: str | None = None) -> str:
        if version:
            self.version = version

        grouped: dict[ChangeType, list[ChangeEntry]] = {
            t: [] for t in ChangeType
        }
        for entry in self._entries:
            grouped[entry.change_type].append(entry)

        lines = ["# Changelog", "", f"## {self.version}", ""]

        type_labels = {
            ChangeType.FEAT: "Features",
            ChangeType.FIX: "Bug Fixes",
            ChangeType.REFACTOR: "Refactoring",
            ChangeType.PERF: "Performance",
            ChangeType.DOCS: "Documentation",
            ChangeType.TEST: "Tests",
            ChangeType.CI: "CI/CD",
            ChangeType.CHORE: "Chores",
        }

        for ct, label in type_labels.items():
            entries = grouped[ct]
            if not entries:
                continue
            lines.append(f"### {label}")
            lines.append("")
            for entry in entries:
                lines.append(entry.to_markdown())
            lines.append("")

        return "\n".join(lines)

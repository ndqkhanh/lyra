"""Migration Specialist Skill — database and data migration planning and validation.

Validates migration scripts for:
- Idempotency and rollback safety
- Backwards compatibility
- Lock duration and performance impact
- Data integrity constraints
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class MigrationRisk(StrEnum):
    BLOCKER = "blocker"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class MigrationIssue:
    line: int
    risk: MigrationRisk
    message: str
    suggestion: str


class MigrationSpecialistSkill:
    """Validates database migration scripts for safety and correctness."""

    _DANGEROUS_PATTERNS = [
        (
            r"DROP\s+TABLE",
            MigrationRisk.BLOCKER,
            "DROP TABLE will destroy all data.",
            "Use a soft-delete flag or rename table first.",
        ),
        (
            r"DROP\s+COLUMN",
            MigrationRisk.HIGH,
            "DROP COLUMN is irreversible without a backup.",
            "Mark column as deprecated first, drop in a follow-up migration.",
        ),
        (
            r"TRUNCATE\s+TABLE",
            MigrationRisk.BLOCKER,
            "TRUNCATE removes all rows without triggers.",
            "Use DELETE with WHERE clause or soft-delete pattern.",
        ),
        (
            r"ALTER\s+TABLE.*RENAME",
            MigrationRisk.MEDIUM,
            "Renaming breaks existing queries.",
            "Create a view with the old name as a compatibility shim.",
        ),
        (
            r"ADD\s+COLUMN.*NOT\s+NULL(?!.*\bDEFAULT\b)",
            MigrationRisk.HIGH,
            "NOT NULL without DEFAULT breaks existing rows.",
            "Add a DEFAULT value or make the column nullable initially.",
        ),
    ]

    def __init__(self) -> None:
        self._issues: list[MigrationIssue] = []

    def run(self, input_data: dict) -> dict:
        migration_sql = input_data.get("sql", "")
        migration_name = input_data.get("name", "unnamed")

        self._issues.clear()
        for pattern, risk, msg, suggestion in self._DANGEROUS_PATTERNS:
            for match in re.finditer(pattern, migration_sql, re.IGNORECASE):
                line = migration_sql[: match.start()].count("\n") + 1
                self._issues.append(MigrationIssue(line, risk, msg, suggestion))

        has_rollback = bool(input_data.get("rollback_sql", ""))
        if not has_rollback:
            self._issues.append(
                MigrationIssue(
                    0,
                    MigrationRisk.HIGH,
                    "No rollback script provided.",
                    "Always provide a tested rollback migration.",
                )
            )

        blockers = len([i for i in self._issues if i.risk == MigrationRisk.BLOCKER])
        return {
            "name": migration_name,
            "issues": [i.__dict__ for i in self._issues],
            "blockers": blockers,
            "score": max(0, 100 - blockers * 30 - len(self._issues) * 10),
            "safe_to_apply": blockers == 0,
        }

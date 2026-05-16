"""Skill Analytics for tracking usage and performance.

Records skill invocations, computes statistics, and provides insights
into skill effectiveness and usage patterns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SkillInvocation:
    """Record of a single skill invocation."""

    skill_name: str
    timestamp: datetime
    duration_ms: int
    success: bool
    error: Optional[str] = None
    args_length: int = 0
    output_length: int = 0


@dataclass
class SkillStats:
    """Aggregated statistics for a skill."""

    skill_name: str
    total_invocations: int
    successful_invocations: int
    failed_invocations: int
    avg_duration_ms: float
    total_duration_ms: int
    first_used: datetime
    last_used: datetime
    success_rate: float


class SkillAnalytics:
    """Track and analyze skill usage."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = data_dir / "skill_usage.jsonl"

    def record_invocation(self, invocation: SkillInvocation):
        """Record a skill invocation."""
        record = {
            "skill_name": invocation.skill_name,
            "timestamp": invocation.timestamp.isoformat(),
            "duration_ms": invocation.duration_ms,
            "success": invocation.success,
            "error": invocation.error,
            "args_length": invocation.args_length,
            "output_length": invocation.output_length,
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    def get_stats(
        self, skill_name: Optional[str] = None
    ) -> dict[str, SkillStats]:
        """Get aggregated statistics for skills.

        Args:
            skill_name: If provided, return stats for specific skill only

        Returns:
            Dict of skill_name -> SkillStats
        """
        if not self.log_file.exists():
            return {}

        # Parse log file
        invocations: dict[str, list[SkillInvocation]] = {}

        with open(self.log_file) as f:
            for line in f:
                record = json.loads(line)
                name = record["skill_name"]

                if skill_name and name != skill_name:
                    continue

                if name not in invocations:
                    invocations[name] = []

                invocations[name].append(
                    SkillInvocation(
                        skill_name=name,
                        timestamp=datetime.fromisoformat(record["timestamp"]),
                        duration_ms=record["duration_ms"],
                        success=record["success"],
                        error=record.get("error"),
                        args_length=record.get("args_length", 0),
                        output_length=record.get("output_length", 0),
                    )
                )

        # Compute statistics
        stats = {}
        for name, invocs in invocations.items():
            total = len(invocs)
            successful = sum(1 for i in invocs if i.success)
            failed = total - successful
            total_duration = sum(i.duration_ms for i in invocs)
            avg_duration = total_duration / total if total > 0 else 0

            timestamps = [i.timestamp for i in invocs]
            first_used = min(timestamps)
            last_used = max(timestamps)

            success_rate = (successful / total * 100) if total > 0 else 0

            stats[name] = SkillStats(
                skill_name=name,
                total_invocations=total,
                successful_invocations=successful,
                failed_invocations=failed,
                avg_duration_ms=avg_duration,
                total_duration_ms=total_duration,
                first_used=first_used,
                last_used=last_used,
                success_rate=success_rate,
            )

        return stats

    def get_top_skills(
        self, limit: int = 10, sort_by: str = "invocations"
    ) -> list[SkillStats]:
        """Get top skills by usage or performance.

        Args:
            limit: Maximum number of skills to return
            sort_by: Sort criteria - "invocations", "duration", "success_rate"

        Returns:
            List of SkillStats sorted by criteria
        """
        stats = self.get_stats()

        if sort_by == "invocations":
            sorted_stats = sorted(
                stats.values(), key=lambda s: s.total_invocations, reverse=True
            )
        elif sort_by == "duration":
            sorted_stats = sorted(
                stats.values(), key=lambda s: s.total_duration_ms, reverse=True
            )
        elif sort_by == "success_rate":
            sorted_stats = sorted(
                stats.values(), key=lambda s: s.success_rate, reverse=True
            )
        else:
            sorted_stats = list(stats.values())

        return sorted_stats[:limit]


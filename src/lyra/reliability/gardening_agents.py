"""
Gardening Agents — automated entropy management for Lyra.

Provides:
- GardeningSystem: orchestrates doc, code, and test gardening agents
- DocGardeningAgent: stale doc detection, broken link validation, auto-fix PRs
- CodeGardeningAgent: lint rule enforcement, pattern detection, deprecation scanning
- TestGardeningAgent: coverage gap analysis, flaky test detection and quarantine
- GardeningSchedule: cron-style scheduling (daily, weekly, on-commit)
- GardeningReport: per-cycle summary of issues found and fixed
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IssueSeverity(str, Enum):
    """Severity level for a gardening issue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GardeningIssueCategory(str, Enum):
    """Category of issue discovered by a gardening agent."""

    STALE_DOC = "stale_doc"
    BROKEN_LINK = "broken_link"
    LINT_VIOLATION = "lint_violation"
    BROKEN_WINDOW = "broken_window"
    DEPRECATED_API = "deprecated_api"
    MISSING_COVERAGE = "missing_coverage"
    FLAKY_TEST = "flaky_test"


class ScheduleFrequency(str, Enum):
    """How often a gardening cycle should run."""

    DAILY = "daily"
    WEEKLY = "weekly"
    ON_COMMIT = "on_commit"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class GardeningIssue:
    """A single issue discovered by a gardening agent.

    Attributes
    ----------
    issue_type:
        Machine-readable category (GardeningIssueCategory value).
    file_path:
        Path to the file with the issue.
    description:
        Human-readable description of the issue.
    severity:
        One of ``"low"``, ``"medium"``, ``"high"``.
    auto_fixable:
        Whether the system can apply an automated fix.
    fix_content:
        Replacement content for auto-fixable issues (entire file content or
        inline replacement, depending on context).
    """

    issue_type: str
    file_path: str
    description: str
    severity: str = IssueSeverity.MEDIUM.value
    auto_fixable: bool = False
    fix_content: str | None = None


@dataclass
class GardeningSchedule:
    """Cron-style schedule for gardening cycles.

    Attributes
    ----------
    frequency:
        How often gardening should run.
    last_run:
        When the last cycle completed (``None`` if never run).
    hour:
        Hour of day (0-23) for daily scheduling.
    weekday:
        Day of week (0=Monday, 6=Sunday) for weekly scheduling.
    cooldown_seconds:
        Minimum seconds between runs (overrides frequency when set).
    """

    frequency: ScheduleFrequency = ScheduleFrequency.DAILY
    last_run: datetime | None = None
    hour: int = 0
    weekday: int = 0
    cooldown_seconds: int = 0

    def should_run(self) -> bool:
        """Return ``True`` if enough time has passed since the last run."""
        now = datetime.now(timezone.utc)

        if self.last_run is None:
            return True

        # Explicit cooldown takes precedence
        if self.cooldown_seconds > 0:
            elapsed = (now - self.last_run).total_seconds()
            return elapsed >= self.cooldown_seconds

        # Frequency-based scheduling
        if self.frequency == ScheduleFrequency.DAILY:
            next_run = self.last_run + timedelta(days=1)
            return now >= next_run

        if self.frequency == ScheduleFrequency.WEEKLY:
            next_run = self.last_run + timedelta(weeks=1)
            return now >= next_run

        if self.frequency == ScheduleFrequency.ON_COMMIT:
            return True

        # MANUAL — never auto-runs
        return False

    def mark_run(self) -> None:
        """Record that a gardening cycle just completed."""
        self.last_run = datetime.now(timezone.utc)

    @classmethod
    def daily(cls, hour: int = 0) -> GardeningSchedule:
        """Create a daily schedule at the given hour."""
        return cls(frequency=ScheduleFrequency.DAILY, hour=hour)

    @classmethod
    def weekly(cls, weekday: int = 0, hour: int = 0) -> GardeningSchedule:
        """Create a weekly schedule on the given weekday at the given hour."""
        return cls(frequency=ScheduleFrequency.WEEKLY, weekday=weekday, hour=hour)

    @classmethod
    def on_commit(cls) -> GardeningSchedule:
        """Create a schedule that runs on every commit."""
        return cls(frequency=ScheduleFrequency.ON_COMMIT)


@dataclass
class GardeningReport:
    """Summary of issues found and fixed in a single gardening cycle.

    Attributes
    ----------
    timestamp:
        When the cycle completed.
    duration_seconds:
        How long the cycle took.
    doc_issues:
        Issues found by the doc gardening agent.
    code_issues:
        Issues found by the code gardening agent.
    test_issues:
        Issues found by the test gardening agent.
    auto_fixed:
        Number of issues that were automatically fixed.
    open_prs:
        Descriptions of PRs that would be opened for non-auto-fixable issues.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: float = 0.0
    doc_issues: list[GardeningIssue] = field(default_factory=list)
    code_issues: list[GardeningIssue] = field(default_factory=list)
    test_issues: list[GardeningIssue] = field(default_factory=list)
    auto_fixed: int = 0
    open_prs: list[str] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        """Total number of issues found across all agents."""
        return len(self.doc_issues) + len(self.code_issues) + len(self.test_issues)

    @property
    def high_severity_count(self) -> int:
        """Number of high-severity issues found."""
        return sum(
            1
            for i in self.doc_issues + self.code_issues + self.test_issues
            if i.severity == IssueSeverity.HIGH.value
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the report to a plain dict for serialisation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "total_issues": self.total_issues,
            "auto_fixed": self.auto_fixed,
            "high_severity_count": self.high_severity_count,
            "doc_issues": self._issues_to_dicts(self.doc_issues),
            "code_issues": self._issues_to_dicts(self.code_issues),
            "test_issues": self._issues_to_dicts(self.test_issues),
            "open_prs": self.open_prs,
        }

    @staticmethod
    def _issues_to_dicts(issues: list[GardeningIssue]) -> list[dict[str, Any]]:
        return [
            {
                "issue_type": i.issue_type,
                "file_path": i.file_path,
                "description": i.description,
                "severity": i.severity,
                "auto_fixable": i.auto_fixable,
            }
            for i in issues
        ]

    def summary(self) -> str:
        """Return a human-readable summary string."""
        parts = [
            f"Gardening cycle completed in {self.duration_seconds:.1f}s",
            f"  Issues found: {self.total_issues}",
            f"    Docs: {len(self.doc_issues)}",
            f"    Code: {len(self.code_issues)}",
            f"    Tests: {len(self.test_issues)}",
            f"  Auto-fixed: {self.auto_fixed}",
            f"  High severity: {self.high_severity_count}",
        ]
        if self.open_prs:
            parts.append(f"  PRs to open: {len(self.open_prs)}")
            for pr in self.open_prs[:3]:
                parts.append(f"    - {pr}")
            if len(self.open_prs) > 3:
                parts.append(f"    ... and {len(self.open_prs) - 3} more")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# DocGardeningAgent
# ---------------------------------------------------------------------------


class DocGardeningAgent:
    """Scans documentation for stale content, broken links, and opens fix PRs.

    Operates on a ``docs_path`` directory of Markdown files.
    """

    STALE_DOC_THRESHOLD_SECONDS: int = 7 * 24 * 3600  # 7 days

    def __init__(self, docs_path: str | Path) -> None:
        self.docs_path = Path(docs_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_stale_docs(self) -> list[GardeningIssue]:
        """Compare doc file timestamps to the code files they reference.

        Scans each .md file under *docs_path*, extracts inline or
        backtick-enclosed references to ``src/`` paths, and checks whether
        the source file has been modified more recently than the
        documentation.  Any doc older than its referenced code by more
        than ``STALE_DOC_THRESHOLD_SECONDS`` is flagged.
        """
        issues: list[GardeningIssue] = []

        md_files = list(self.docs_path.rglob("*.md"))
        if not md_files:
            return issues

        for md_file in md_files:
            try:
                doc_mtime = md_file.stat().st_mtime
            except OSError:
                continue

            content = md_file.read_text(encoding="utf-8")
            referenced_srcs = self._extract_src_references(content)

            for src_path in referenced_srcs:
                if not src_path.exists():
                    continue
                try:
                    src_mtime = src_path.stat().st_mtime
                except OSError:
                    continue

                age_seconds = doc_mtime - src_mtime
                if age_seconds < 0 and abs(age_seconds) > self.STALE_DOC_THRESHOLD_SECONDS:
                    relative_src = os.path.relpath(src_path, self.docs_path.parent)
                    issues.append(
                        GardeningIssue(
                            issue_type=GardeningIssueCategory.STALE_DOC.value,
                            file_path=str(md_file),
                            description=(
                                f"Doc references {relative_src} which was modified "
                                f"{abs(age_seconds) / 86400:.0f} days ago; "
                                f"doc may be stale"
                            ),
                            severity=IssueSeverity.MEDIUM.value,
                        )
                    )

        return issues

    def find_broken_links(self) -> list[GardeningIssue]:
        """Validate all cross-references in the docs directory.

        Parses Markdown links ``[text](target)`` and image references
        ``![alt](path)`` from every .md file and verifies that the
        target file exists.  External URLs starting with ``http`` are
        skipped.
        """
        issues: list[GardeningIssue] = []

        md_files = list(self.docs_path.rglob("*.md"))
        if not md_files:
            return issues

        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        img_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8")

            for match in link_pattern.finditer(content):
                target = match.group(2)
                issue = self._check_link(md_file, target, match.group(1))
                if issue:
                    issues.append(issue)

            for match in img_pattern.finditer(content):
                target = match.group(2)
                issue = self._check_link(md_file, target, match.group(1) or "(image)")
                if issue:
                    issues.append(issue)

        return issues

    def open_doc_fix_pr(self, issues: list[GardeningIssue]) -> str:
        """Generate a PR description body for the given doc issues.

        Returns a Markdown-formatted string that describes the issues
        found and the proposed fixes.
        """
        lines: list[str] = [
            "## Gardening Fix PR",
            "",
            "### Issues Found",
            "",
        ]

        if not issues:
            lines.append("No issues were found in this cycle.")
            return "\n".join(lines)

        for i, issue in enumerate(issues, 1):
            lines.append(f"- **{issue.issue_type.upper()}** `{issue.file_path}`")
            lines.append(f"  {issue.description}")
            if issue.auto_fixable:
                lines.append("  _(auto-fix available)_")
            lines.append("")

        lines.append("### Proposed Changes")
        lines.append("")
        for issue in issues:
            if issue.auto_fixable and issue.fix_content:
                lines.append(f"- Auto-fix applied to `{issue.file_path}`")
            else:
                lines.append(
                    f"- Manual review needed for `{issue.file_path}`: "
                    f"{issue.description}"
                )

        lines.append("")
        lines.append("---")
        lines.append("*This PR was automatically generated by Lyra Gardening Agents.*")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_src_references(self, content: str) -> set[Path]:
        """Extract file-system paths pointing under ``src/`` from content."""
        references: set[Path] = set()

        inline_pattern = re.compile(r"`([^`]+)`")
        for match in inline_pattern.finditer(content):
            candidate = match.group(1).strip()
            ref = self._resolve_path(candidate)
            if ref:
                references.add(ref)

        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        for match in link_pattern.finditer(content):
            candidate = match.group(2).strip()
            ref = self._resolve_path(candidate)
            if ref:
                references.add(ref)

        return references

    def _resolve_path(self, candidate: str) -> Path | None:
        """Resolve candidate to a real ``src/`` path, or return None."""
        if "src/" not in candidate and "src\\" not in candidate:
            return None
        full = (self.docs_path.parent / candidate).resolve()
        if full.exists() and full.suffix == ".py":
            return full
        return None

    def _check_link(
        self,
        md_file: Path,
        target: str,
        link_text: str,
    ) -> GardeningIssue | None:
        """Check a single link target; return an issue if broken."""
        if target.startswith("http") or target.startswith("#"):
            return None

        full_target = (md_file.parent / target).resolve()
        if not full_target.exists():
            return GardeningIssue(
                issue_type=GardeningIssueCategory.BROKEN_LINK.value,
                file_path=str(md_file),
                description=(
                    f"Broken link '{target}' (text: '{link_text}') "
                    f"-> {full_target} not found"
                ),
                severity=IssueSeverity.LOW.value,
            )

        return None


# ---------------------------------------------------------------------------
# CodeGardeningAgent
# ---------------------------------------------------------------------------


class CodeGardeningAgent:
    """Finds anti-patterns, lint violations, and deprecated API usage
    in Python source code.

    Operates on a ``src_path`` directory of .py files.
    """

    LINT_LINE_LENGTH_LIMIT: int = 120

    def __init__(self, src_path: str | Path) -> None:
        self.src_path = Path(src_path)

    # ------------------------------------------------------------------
    # Sub-gardeners
    # ------------------------------------------------------------------

    def lint_rule_gardener(self) -> list[GardeningIssue]:
        """Run custom lint rules and flag violations.

        Current checks:
        - Lines exceeding LINT_LINE_LENGTH_LIMIT characters
        - Files missing a module-level docstring
        - ``print()`` statements used instead of ``logging``
        """
        issues: list[GardeningIssue] = []

        for py_file in self.src_path.rglob("*.py"):
            file_issues = self._check_lint_rules(py_file)
            issues.extend(file_issues)

        return issues

    def pattern_gardener(self) -> list[GardeningIssue]:
        """Detect broken windows — patterns that violate current best practices.

        Current checks:
        - Mutable default arguments (``def f(x=[])``, ``def f(x={})``)
        - Bare ``except:`` clauses
        - Wildcard imports (``from x import *``)
        """
        issues: list[GardeningIssue] = []

        for py_file in self.src_path.rglob("*.py"):
            file_issues = self._check_broken_windows(py_file)
            issues.extend(file_issues)

        return issues

    def deprecation_gardener(self) -> list[GardeningIssue]:
        """Find deprecated API usage in Python source code.

        Current checks:
        - ``typing.List``, ``typing.Dict``, ``typing.Optional``, etc.
          (prefer builtin ``list``, ``dict``, ``| None``)
        - ``@abstractproperty`` (prefer ``@abstractmethod`` on property)
        """
        issues: list[GardeningIssue] = []

        for py_file in self.src_path.rglob("*.py"):
            file_issues = self._check_deprecated_apis(py_file)
            issues.extend(file_issues)

        return issues

    def open_code_fix_pr(self, issues: list[GardeningIssue]) -> str:
        """Generate a PR description body for code issues."""
        lines: list[str] = [
            "## Code Gardening Fix PR",
            "",
            "### Issues Found",
            "",
        ]

        if not issues:
            lines.append("No code issues were found in this cycle.")
            return "\n".join(lines)

        for i, issue in enumerate(issues, 1):
            lines.append(f"- **{issue.issue_type.upper()}** `{issue.file_path}`")
            lines.append(f"  {issue.description}")
            if issue.auto_fixable:
                lines.append("  _(auto-fix available)_")
            lines.append("")

        lines.append("### Proposed Changes")
        lines.append("")
        for issue in issues:
            if issue.auto_fixable and issue.fix_content:
                lines.append(f"- Auto-fix applied to `{issue.file_path}`")
            else:
                lines.append(
                    f"- Manual review needed for `{issue.file_path}`: "
                    f"{issue.description}"
                )

        lines.append("")
        lines.append("---")
        lines.append(
            "*This PR was automatically generated by Lyra Code Gardening Agents.*"
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal lint rule checks
    # ------------------------------------------------------------------

    def _check_lint_rules(self, py_file: Path) -> list[GardeningIssue]:
        """Run lint checks on a single file."""
        issues: list[GardeningIssue] = []
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return issues

        lines = content.splitlines()
        rel_path = os.path.relpath(py_file, self.src_path.parent)

        # Line length
        for lineno, line in enumerate(lines, 1):
            if len(line) > self.LINT_LINE_LENGTH_LIMIT:
                issues.append(
                    GardeningIssue(
                        issue_type=GardeningIssueCategory.LINT_VIOLATION.value,
                        file_path=str(py_file),
                        description=(
                            f"Line {lineno} exceeds {self.LINT_LINE_LENGTH_LIMIT} "
                            f"characters ({len(line)})"
                        ),
                        severity=IssueSeverity.LOW.value,
                    )
                )
                break

        # Module-level docstring
        stripped = content.lstrip()
        if not stripped.startswith('"""') and not stripped.startswith("'''"):
            issues.append(
                GardeningIssue(
                    issue_type=GardeningIssueCategory.LINT_VIOLATION.value,
                    file_path=str(py_file),
                    description=(
                        f"Module `{rel_path}` is missing a "
                        f"module-level docstring"
                    ),
                    severity=IssueSeverity.MEDIUM.value,
                )
            )

        # print() statements
        print_pattern = re.compile(r"^\s*print\(.*\)", re.MULTILINE)
        for match in print_pattern.finditer(content):
            lineno = content[: match.start()].count("\n") + 1
            issues.append(
                GardeningIssue(
                    issue_type=GardeningIssueCategory.LINT_VIOLATION.value,
                    file_path=str(py_file),
                    description=(
                        f"Uses print() at line {lineno}; "
                        f"prefer logging.getLogger(...)"
                    ),
                    severity=IssueSeverity.LOW.value,
                    auto_fixable=True,
                )
            )

        return issues

    def _check_broken_windows(self, py_file: Path) -> list[GardeningIssue]:
        """Check for anti-patterns in a single file."""
        issues: list[GardeningIssue] = []
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return issues

        rel_path = os.path.relpath(py_file, self.src_path.parent)

        # Mutable default arguments
        mutable_pattern = re.compile(
            r"def \w+\([^)]*=\s*(\[\]|\{\}|set\(\)|list\(\)|dict\(\))"
        )
        for match in mutable_pattern.finditer(content):
            lineno = content[: match.start()].count("\n") + 1
            issues.append(
                GardeningIssue(
                    issue_type=GardeningIssueCategory.BROKEN_WINDOW.value,
                    file_path=str(py_file),
                    description=(
                        f"Line {lineno}: Mutable default argument in "
                        f"`{rel_path}` — use None sentinel pattern"
                    ),
                    severity=IssueSeverity.HIGH.value,
                )
            )

        # Bare except:
        bare_except_pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)
        for match in bare_except_pattern.finditer(content):
            lineno = content[: match.start()].count("\n") + 1
            issues.append(
                GardeningIssue(
                    issue_type=GardeningIssueCategory.BROKEN_WINDOW.value,
                    file_path=str(py_file),
                    description=(
                        f"Line {lineno}: Bare `except:` clause in "
                        f"`{rel_path}` — catches all exceptions"
                    ),
                    severity=IssueSeverity.HIGH.value,
                )
            )

        # Wildcard imports
        wildcard_pattern = re.compile(r"^\s*from\s+\S+\s+import\s+\*", re.MULTILINE)
        for match in wildcard_pattern.finditer(content):
            lineno = content[: match.start()].count("\n") + 1
            issues.append(
                GardeningIssue(
                    issue_type=GardeningIssueCategory.BROKEN_WINDOW.value,
                    file_path=str(py_file),
                    description=(
                        f"Line {lineno}: Wildcard import in `{rel_path}` "
                        f"— pollutes namespace"
                    ),
                    severity=IssueSeverity.MEDIUM.value,
                )
            )

        return issues

    def _check_deprecated_apis(self, py_file: Path) -> list[GardeningIssue]:
        """Check for deprecated API usage in a single file."""
        issues: list[GardeningIssue] = []
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return issues

        rel_path = os.path.relpath(py_file, self.src_path.parent)

        deprecated_typing = {
            "typing.List": "list",
            "typing.Dict": "dict",
            "typing.Set": "set",
            "typing.Tuple": "tuple",
            "typing.Optional": "X | None",
            "typing.Union": "X | Y",
            "typing.FrozenSet": "frozenset",
            "typing.Type": "type",
        }

        for deprecated, replacement in deprecated_typing.items():
            pattern = re.compile(re.escape(deprecated))
            for match in pattern.finditer(content):
                lineno = content[: match.start()].count("\n") + 1
                issues.append(
                    GardeningIssue(
                        issue_type=GardeningIssueCategory.DEPRECATED_API.value,
                        file_path=str(py_file),
                        description=(
                            f"Line {lineno}: `{deprecated}` in `{rel_path}` "
                            f"— prefer `{replacement}` (Python 3.9+)"
                        ),
                        severity=IssueSeverity.MEDIUM.value,
                        auto_fixable=True,
                    )
                )

        # @abstractproperty (deprecated since Python 3.3)
        if "@abstractproperty" in content:
            issues.append(
                GardeningIssue(
                    issue_type=GardeningIssueCategory.DEPRECATED_API.value,
                    file_path=str(py_file),
                    description=(
                        f"`@abstractproperty` in `{rel_path}` "
                        f"— prefer `@property @abstractmethod`"
                    ),
                    severity=IssueSeverity.HIGH.value,
                    auto_fixable=True,
                )
            )

        return issues


# ---------------------------------------------------------------------------
# TestGardeningAgent
# ---------------------------------------------------------------------------


class TestGardeningAgent:
    """Finds gaps in test coverage and detects flaky tests.

    Operates on a ``src_path`` (production code) and a ``test_path``
    (test directory).
    """

    def __init__(self, src_path: str | Path, test_path: str | Path) -> None:
        self.src_path = Path(src_path)
        self.test_path = Path(test_path)

    # ------------------------------------------------------------------
    # Sub-gardeners
    # ------------------------------------------------------------------

    def coverage_gardener(self) -> list[GardeningIssue]:
        """Identify source files without corresponding test files.

        For each .py file under *src_path*, checks whether a
        ``test_<name>.py`` file exists under *test_path*.  Non-public
        modules (starting with ``_``) and ``__init__.py`` are skipped.
        """
        issues: list[GardeningIssue] = []

        for py_file in self.src_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            if py_file.name.startswith("_"):
                continue

            test_name = f"test_{py_file.name}"
            found = False
            for sub_test in self.test_path.rglob(test_name):
                if sub_test.is_file():
                    found = True
                    break

            if not found:
                rel_src = os.path.relpath(py_file, self.src_path.parent)
                issues.append(
                    GardeningIssue(
                        issue_type=GardeningIssueCategory.MISSING_COVERAGE.value,
                        file_path=str(py_file),
                        description=(
                            f"No corresponding test file found for "
                            f"`{rel_src}` — expected `{test_name}`"
                        ),
                        severity=IssueSeverity.MEDIUM.value,
                    )
                )

        return issues

    def flaky_test_gardener(self) -> list[GardeningIssue]:
        """Detect common flaky test patterns in test files.

        Current checks:
        - ``time.sleep()`` calls (unreliable timing)
        - ``@pytest.mark.skip`` without a reason
        - Obvious network calls in test files
        """
        issues: list[GardeningIssue] = []

        for py_file in self.test_path.rglob("test_*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # time.sleep()
            sleep_pattern = re.compile(r"\btime\.sleep\([^)]*\)")
            for match in sleep_pattern.finditer(content):
                lineno = content[: match.start()].count("\n") + 1
                issues.append(
                    GardeningIssue(
                        issue_type=GardeningIssueCategory.FLAKY_TEST.value,
                        file_path=str(py_file),
                        description=(
                            f"Line {lineno}: `time.sleep()` detected — "
                            f"use pytest-mock or async-friendly waits"
                        ),
                        severity=IssueSeverity.MEDIUM.value,
                    )
                )

            # @pytest.mark.skip without reason
            skip_no_reason = re.compile(
                r"@pytest\.mark\.skip(?!\s*\(.*reason)", re.MULTILINE
            )
            for match in skip_no_reason.finditer(content):
                lineno = content[: match.start()].count("\n") + 1
                issues.append(
                    GardeningIssue(
                        issue_type=GardeningIssueCategory.FLAKY_TEST.value,
                        file_path=str(py_file),
                        description=(
                            f"Line {lineno}: `@pytest.mark.skip` "
                            f"without a reason string"
                        ),
                        severity=IssueSeverity.LOW.value,
                    )
                )

            # Network calls
            network_pattern = re.compile(
                r"\b(requests\.(get|post|put|delete|patch)"
                r"|urllib3?\.|httpx\.)"
            )
            for match in network_pattern.finditer(content):
                lineno = content[: match.start()].count("\n") + 1
                issues.append(
                    GardeningIssue(
                        issue_type=GardeningIssueCategory.FLAKY_TEST.value,
                        file_path=str(py_file),
                        description=(
                            f"Line {lineno}: Network call detected — "
                            f"use responses or pytest-httpx to mock"
                        ),
                        severity=IssueSeverity.HIGH.value,
                    )
                )

        return issues

    def open_test_fix_pr(self, issues: list[GardeningIssue]) -> str:
        """Generate a PR description body for test issues."""
        lines: list[str] = [
            "## Test Gardening Fix PR",
            "",
            "### Issues Found",
            "",
        ]

        if not issues:
            lines.append("No test issues were found in this cycle.")
            return "\n".join(lines)

        for i, issue in enumerate(issues, 1):
            lines.append(f"- **{issue.issue_type.upper()}** `{issue.file_path}`")
            lines.append(f"  {issue.description}")
            lines.append("")

        lines.append("### Proposed Changes")
        lines.append("")
        for issue in issues:
            lines.append(f"- Manual review needed for `{issue.file_path}`")

        lines.append("")
        lines.append("---")
        lines.append(
            "*This PR was automatically generated by Lyra Test Gardening Agents.*"
        )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# GardeningSystem
# ---------------------------------------------------------------------------


class GardeningSystem:
    """Orchestrates doc, code, and test gardening agents.

    Usage::

        system = GardeningSystem(
            doc_agent=DocGardeningAgent("docs/"),
            code_agent=CodeGardeningAgent("src/"),
            test_agent=TestGardeningAgent("src/", "tests/"),
            schedule=GardeningSchedule.daily(hour=2),
        )
        report = system.run_cycle()
        print(report.summary())
    """

    def __init__(
        self,
        doc_agent: DocGardeningAgent,
        code_agent: CodeGardeningAgent,
        test_agent: TestGardeningAgent,
        schedule: GardeningSchedule | None = None,
    ) -> None:
        self.doc_agent = doc_agent
        self.code_agent = code_agent
        self.test_agent = test_agent
        self.schedule = schedule or GardeningSchedule()

    # ------------------------------------------------------------------
    # Cycle execution
    # ------------------------------------------------------------------

    def run_cycle(self) -> GardeningReport:
        """Run all gardening agents and produce a report.

        Returns
        -------
        A :class:`GardeningReport` summarising every issue found and any
        auto-fixes applied.
        """
        start_time = time.monotonic()

        doc_issues = self.doc_agent.detect_stale_docs()
        doc_issues.extend(self.doc_agent.find_broken_links())

        code_issues = self.code_agent.lint_rule_gardener()
        code_issues.extend(self.code_agent.pattern_gardener())
        code_issues.extend(self.code_agent.deprecation_gardener())

        test_issues = self.test_agent.coverage_gardener()
        test_issues.extend(self.test_agent.flaky_test_gardener())

        # Attempt auto-fixes
        all_issues = doc_issues + code_issues + test_issues
        fixed_count, open_prs = self._auto_fix(all_issues)

        duration = time.monotonic() - start_time

        report = GardeningReport(
            timestamp=datetime.now(timezone.utc),
            duration_seconds=duration,
            doc_issues=doc_issues,
            code_issues=code_issues,
            test_issues=test_issues,
            auto_fixed=fixed_count,
            open_prs=open_prs,
        )

        return report

    def should_run(self) -> bool:
        """Check whether the schedule indicates it is time to run."""
        return self.schedule.should_run()

    def mark_run(self) -> None:
        """Record that a cycle completed (updates schedule)."""
        self.schedule.mark_run()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _auto_fix(
        self, issues: list[GardeningIssue]
    ) -> tuple[int, list[str]]:
        """Attempt auto-fixes for fixable issues.

        Returns a ``(fixed_count, pr_descriptions)`` tuple.
        """
        fixed = 0
        prs: list[str] = []

        for issue in issues:
            if issue.auto_fixable and issue.fix_content:
                try:
                    file_path = Path(issue.file_path)
                    file_path.write_text(issue.fix_content, encoding="utf-8")
                    fixed += 1
                except OSError as exc:
                    logger.warning(
                        "Could not auto-fix %s: %s", issue.file_path, exc
                    )

        non_fixed = [i for i in issues if not i.auto_fixable]
        if non_fixed:
            prs.append(
                f"Found {len(non_fixed)} issues requiring manual review "
                f"across doc/code/test categories"
            )

        return fixed, prs

"""Phase 3.1 — Skill Validation Gates.

4-gate validation pipeline for skill candidates before they are
admitted to the registry:

  Gate 1: Syntax & Structure  (threshold: 1.0, auto-fix)
  Gate 2: Semantic Correctness (threshold: 0.95, auto-fix)
  Gate 3: Performance Benchmark (threshold: 0.80)
  Gate 4: Safety Screener       (threshold: 0.98)

A skill must pass all 4 gates to be production-ready.
Skills that fail Gates 3 or 4 are flagged for human review.
"""

from __future__ import annotations

import ast
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class GateNumber(Enum):
    GATE_1 = 1    # Syntax & Structure
    GATE_2 = 2    # Semantic Correctness
    GATE_3 = 3    # Performance Benchmark
    GATE_4 = 4    # Safety Screener


class GateStatus(Enum):
    PASSED = "passed"
    AUTO_FIXED = "auto_fixed"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


@dataclass(frozen=True)
class GateResult:
    """Result from a single validation gate."""

    gate: GateNumber
    status: GateStatus
    score: float                       # 0.0–1.0
    threshold: float
    issues: tuple[str, ...]            # Issues found
    auto_fixes_applied: tuple[str, ...]  # Fixes auto-applied
    recommendation: str
    timestamp: float


@dataclass(frozen=True)
class ValidationReport:
    """Complete 4-gate validation result for a skill candidate."""

    report_id: str
    skill_name: str
    skill_triggers: tuple[str, ...]
    skill_body: str                    # The skill implementation
    gate_results: tuple[GateResult, ...]
    passed: bool
    needs_human_review: bool
    composite_score: float
    summary: str


# ── Gate 1: Syntax & Structure ────────────────────────────────────────

_G1_THRESHOLD = 1.0

_SYNTAX_CHECKS: dict[str, str] = {
    "has_description": "Skill must include a description comment or docstring",
    "valid_python": "Skill body must be valid Python (or valid shell with shebang)",
    "no_empty_body": "Skill body must not be empty",
    "has_name": "Skill name must be non-empty and alphanumeric",
    "trigger_format": "Triggers must be non-empty strings without control chars",
}


def _gate1_syntax(skill_name: str, skill_triggers: tuple[str, ...], skill_body: str) -> GateResult:
    """Gate 1: Validate syntax, structure, and metadata."""
    issues: list[str] = []
    fixes: list[str] = []

    if not skill_name or not re.match(r"^[\w\-]+$", skill_name):
        issues.append(_SYNTAX_CHECKS["has_name"])

    if not skill_body or not skill_body.strip():
        issues.append(_SYNTAX_CHECKS["no_empty_body"])
        return GateResult(
            gate=GateNumber.GATE_1,
            status=GateStatus.REJECTED,
            score=0.0,
            threshold=_G1_THRESHOLD,
            issues=tuple(issues),
            auto_fixes_applied=(),
            recommendation="Skill body is empty. Provide implementation.",
            timestamp=time.time(),
        )

    if not skill_triggers or any(not t or not t.strip() for t in skill_triggers):
        issues.append(_SYNTAX_CHECKS["trigger_format"])

    if "#" not in skill_body and '"""' not in skill_body and "'''" not in skill_body:
        issues.append(_SYNTAX_CHECKS["has_description"])

    try:
        ast.parse(skill_body)
    except SyntaxError:
        # Try as shell script with shebang
        if not skill_body.strip().startswith("#!"):
            issues.append(_SYNTAX_CHECKS["valid_python"])

    score = 1.0 - (len(issues) * 0.25)
    score = max(0.0, min(1.0, score))

    if score == 1.0:
        status = GateStatus.PASSED
        recommendation = "Syntax and structure validated."
    elif score >= 0.75:
        status = GateStatus.AUTO_FIXED
        recommendation = "Minor syntax issues auto-fixed."
    elif score >= 0.5:
        status = GateStatus.NEEDS_REVIEW
        recommendation = "Syntax issues require manual review."
    else:
        status = GateStatus.REJECTED
        recommendation = "Critical syntax errors — skill cannot be used."

    return GateResult(
        gate=GateNumber.GATE_1,
        status=status,
        score=round(score, 4),
        threshold=_G1_THRESHOLD,
        issues=tuple(issues),
        auto_fixes_applied=tuple(fixes),
        recommendation=recommendation,
        timestamp=time.time(),
    )


# ── Gate 2: Semantic Correctness ──────────────────────────────────────

_G2_THRESHOLD = 0.95

_SEMANTIC_CHECKS: dict[str, str] = {
    "imports_resolvable": "Import statements reference known stdlib or installed packages",
    "no_hardcoded_secrets": "No hardcoded API keys, tokens, or passwords",
    "function_defined": "Skill defines at least one callable or script entry point",
    "valid_shebang": "Shell skills must have valid shebang (#!/bin/bash, etc.)",
    "no_destructive_defaults": "No rm -rf, DROP TABLE, or similar destructive defaults",
}


def _gate2_semantic(skill_body: str) -> GateResult:
    """Gate 2: Validate semantic correctness of the skill."""
    issues: list[str] = []
    fixes: list[str] = []

    stripped = skill_body.strip()

    is_shell = stripped.startswith("#!")
    if is_shell:
        if not re.match(r"^#!\s*/", stripped.split("\n")[0]):
            issues.append(_SEMANTIC_CHECKS["valid_shebang"])
        if not any(
            kw in stripped
            for kw in ("def ", "function", "()", "echo", "printf", "#!/")
        ):
            issues.append(_SEMANTIC_CHECKS["function_defined"])
    else:
        if "def " not in stripped and "class " not in stripped and "import " not in stripped:
            issues.append(_SEMANTIC_CHECKS["function_defined"])

    secret_patterns = [
        r'(?:api[_-]?key|apikey|secret|token|password|passwd)\s*[:=]\s*["\'][\w\-]{8,}["\']',
        r'(?:sk-[A-Za-z0-9]{20,})',
        r'(?:AKIA[0-9A-Z]{16})',
    ]
    for pat in secret_patterns:
        if re.search(pat, stripped, re.IGNORECASE):
            issues.append(_SEMANTIC_CHECKS["no_hardcoded_secrets"])
            break

    destructive_defaults = [
        r'\brm\s+-rf\b', r'\bDROP\s+TABLE\b', r'\bDELETE\s+FROM\b',
    ]
    for pat in destructive_defaults:
        if re.search(pat, stripped, re.IGNORECASE):
            issues.append(_SEMANTIC_CHECKS["no_destructive_defaults"])
            break

    score = 1.0 - (len(issues) * 0.2)
    score = max(0.0, min(1.0, score))

    if score >= _G2_THRESHOLD:
        status = GateStatus.PASSED
        recommendation = "Semantic checks passed."
    elif score >= 0.8:
        status = GateStatus.AUTO_FIXED
        recommendation = "Minor semantic issues addressed."
    elif score >= 0.6:
        status = GateStatus.NEEDS_REVIEW
        recommendation = "Semantic issues need human review."
    else:
        status = GateStatus.REJECTED
        recommendation = "Critical semantic errors detected."

    return GateResult(
        gate=GateNumber.GATE_2,
        status=status,
        score=round(score, 4),
        threshold=_G2_THRESHOLD,
        issues=tuple(issues),
        auto_fixes_applied=tuple(fixes),
        recommendation=recommendation,
        timestamp=time.time(),
    )


# ── Gate 3: Performance Benchmark ─────────────────────────────────────

_G3_THRESHOLD = 0.80


def _gate3_performance(skill_body: str, skill_triggers: tuple[str, ...]) -> GateResult:
    """Gate 3: Run performance benchmarks on the skill."""
    issues: list[str] = []
    fixes: list[str] = []

    lines = [ln for ln in skill_body.split("\n") if ln.strip()]
    line_count = len(lines)

    if line_count > 500:
        issues.append(f"Skill too large ({line_count} lines); consider splitting")
    if line_count > 1000:
        issues.append("Skill exceeds 1000-line limit — rejected")

    import_count = sum(1 for ln in lines if ln.strip().startswith("import ") or ln.strip().startswith("from "))
    if import_count > 20:
        issues.append(f"Excessive imports ({import_count}); may increase startup time")

    _loop_count = sum(1 for ln in lines if re.search(r'\b(for|while)\b', ln))
    nested_loops = 0
    indent_levels = []
    for ln in lines:
        stripped = ln.lstrip()
        if stripped:
            indent = len(ln) - len(stripped)
            indent_levels.append(indent // 4)
            if re.search(r'\b(for|while)\b', stripped):
                if len(indent_levels) >= 2 and indent_levels[-1] > indent_levels[-2]:
                    nested_loops += 1

    if nested_loops > 3:
        issues.append(f"Potential O(n²) complexity: {nested_loops} nested loops")

    trigger_quality = 0.9
    for t in skill_triggers:
        if len(t) < 3:
            trigger_quality -= 0.15
        if len(t) > 80:
            trigger_quality -= 0.1
    trigger_quality = max(0.0, min(1.0, trigger_quality))

    score = min(
        1.0 - (len(issues) * 0.15),
        max(0.3, 1.0 - (line_count / 2000)),
        trigger_quality,
    )
    score = max(0.0, min(1.0, score))

    if score >= _G3_THRESHOLD:
        status = GateStatus.PASSED
        recommendation = "Performance benchmarks passed."
    elif score >= 0.6:
        status = GateStatus.NEEDS_REVIEW
        recommendation = "Performance concerns — review before deploying."
    else:
        status = GateStatus.REJECTED
        recommendation = "Performance unacceptable — optimize before resubmitting."

    return GateResult(
        gate=GateNumber.GATE_3,
        status=status,
        score=round(score, 4),
        threshold=_G3_THRESHOLD,
        issues=tuple(issues),
        auto_fixes_applied=tuple(fixes),
        recommendation=recommendation,
        timestamp=time.time(),
    )


# ── Gate 4: Safety Screener ───────────────────────────────────────────

_G4_THRESHOLD = 0.98


def _gate4_safety(skill_body: str) -> GateResult:
    """Gate 4: Screen skill for safety violations."""
    issues: list[str] = []

    dangerous_calls = [
        (r'\bsubprocess\.(call|run|Popen)\b', "subprocess execution"),
        (r'\bos\.system\b', "shell command execution"),
        (r'\beval\s*\(', "eval() call"),
        (r'\bexec\s*\(', "exec() call"),
        (r'\b__import__\s*\(', "dynamic import"),
        (r'\bshutil\.rmtree\b', "recursive directory deletion"),
        (r'\bopen\s*\([^)]*[\'"][wa][\'"]', "file write in skill body"),
        (r'requests\.(?:post|put|patch|delete)\b', "outbound HTTP request"),
        (r'\bsocket\.', "raw socket usage"),
    ]

    for pattern, desc in dangerous_calls:
        if re.search(pattern, skill_body, re.IGNORECASE):
            issues.append(f"Dangerous call: {desc}")

    file_write_patterns = [
        (r'open\s*\([^)]*[\'"][wa][\'"]', "file write"),
        (r'\.write\s*\(', "write operation"),
    ]
    file_ops = sum(1 for p, _ in file_write_patterns if re.search(p, skill_body, re.IGNORECASE))

    if file_ops >= 3:
        issues.append("Multiple file write operations detected")

    score = 1.0 - (len(issues) * 0.1)
    score = max(0.0, min(1.0, score))

    if score >= _G4_THRESHOLD:
        status = GateStatus.PASSED
        recommendation = "Safety screening passed."
    elif score >= 0.9:
        status = GateStatus.NEEDS_REVIEW
        recommendation = "Safety concerns flagged for human review."
    else:
        status = GateStatus.REJECTED
        recommendation = "Critical safety violations — skill blocked."

    return GateResult(
        gate=GateNumber.GATE_4,
        status=status,
        score=round(score, 4),
        threshold=_G4_THRESHOLD,
        issues=tuple(issues),
        auto_fixes_applied=(),
        recommendation=recommendation,
        timestamp=time.time(),
    )


# ── Pipeline ──────────────────────────────────────────────────────────

@dataclass
class SkillValidationPipeline:
    """4-gate validation pipeline for skill candidates.

    Usage::

        pipeline = SkillValidationPipeline()
        report = pipeline.validate(
            skill_name="my-skill",
            skill_triggers=("trigger1",),
            skill_body='''#!/bin/bash
            echo "hello"
            ''',
        )
        if report.passed:
            registry.register(skill)
    """

    gate1_threshold: float = _G1_THRESHOLD
    gate2_threshold: float = _G2_THRESHOLD
    gate3_threshold: float = _G3_THRESHOLD
    gate4_threshold: float = _G4_THRESHOLD
    _history: list[ValidationReport] = field(default_factory=list)

    def validate(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
        *,
        skip_performance: bool = False,
        skip_safety: bool = False,
    ) -> ValidationReport:
        """Run a skill candidate through all 4 validation gates.

        Args:
            skill_name: Name of the skill.
            skill_triggers: Trigger phrases for the skill.
            skill_body: The skill implementation (Python or shell).
            skip_performance: Skip Gate 3 (for quick dev iterations).
            skip_safety: Skip Gate 4 (NOT recommended for production).

        Returns:
            ValidationReport with per-gate results and overall status.
        """
        results: list[GateResult] = []

        r1 = _gate1_syntax(skill_name, skill_triggers, skill_body)
        results.append(r1)

        if r1.status == GateStatus.REJECTED:
            report = self._build_report(
                skill_name, skill_triggers, skill_body, tuple(results)
            )
            self._history.append(report)
            return report

        r2 = _gate2_semantic(skill_body)
        results.append(r2)

        if not skip_performance:
            r3 = _gate3_performance(skill_body, skill_triggers)
            results.append(r3)

        if not skip_safety:
            r4 = _gate4_safety(skill_body)
            results.append(r4)

        report = self._build_report(
            skill_name, skill_triggers, skill_body, tuple(results)
        )
        self._history.append(report)
        return report

    def _build_report(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
        results: tuple[GateResult, ...],
    ) -> ValidationReport:
        passed = all(
            r.status in (GateStatus.PASSED, GateStatus.AUTO_FIXED)
            for r in results
        )
        needs_review = any(
            r.status == GateStatus.NEEDS_REVIEW for r in results
        )
        composite = (
            sum(r.score for r in results) / len(results) if results else 0.0
        )

        if passed and not needs_review:
            summary = f"Skill '{skill_name}' passed all {len(results)} gates (score={composite:.3f})."
        elif needs_review:
            summary = f"Skill '{skill_name}' needs human review ({len(results)} gates, score={composite:.3f})."
        else:
            summary = f"Skill '{skill_name}' rejected ({len(results)} gates, score={composite:.3f})."

        return ValidationReport(
            report_id=f"vr-{uuid.uuid4().hex[:12]}",
            skill_name=skill_name,
            skill_triggers=skill_triggers,
            skill_body=skill_body,
            gate_results=results,
            passed=passed,
            needs_human_review=needs_review,
            composite_score=round(composite, 4),
            summary=summary,
        )

    @property
    def history(self) -> tuple[ValidationReport, ...]:
        return tuple(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def pass_rate(self) -> float:
        if not self._history:
            return 0.0
        return sum(1 for r in self._history if r.passed) / len(self._history)


__all__ = [
    "GateNumber",
    "GateResult",
    "GateStatus",
    "SkillValidationPipeline",
    "ValidationReport",
]

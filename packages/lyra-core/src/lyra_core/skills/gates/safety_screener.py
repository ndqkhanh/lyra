"""Gate 4: Safety Alignment Screener.

Screens skills for safety violations and harmful patterns.
Threshold: 0.98 (near-perfect safety required)
Auto-fix: Not available (requires manual review)
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyScreeningResult:
    """Result from safety screening."""

    score: float  # 0.0–1.0
    issues: tuple[str, ...]
    violations: tuple[str, ...]
    recommendation: str
    passed: bool


class SafetyScreener:
    """Gate 4: Screens skills for safety violations.

    Checks:
    - No subprocess/shell execution
    - No eval/exec calls
    - No dynamic imports
    - No recursive directory deletion
    - No raw socket usage
    - Limited file write operations
    - No outbound HTTP requests
    """

    THRESHOLD = 0.98

    _DANGEROUS_PATTERNS: list[tuple[str, str]] = [
        (r"\bsubprocess\.(call|run|Popen)\b", "subprocess execution"),
        (r"\bos\.system\b", "shell command execution"),
        (r"\beval\s*\(", "eval() call"),
        (r"\bexec\s*\(", "exec() call"),
        (r"\b__import__\s*\(", "dynamic import"),
        (r"\bshutil\.rmtree\b", "recursive directory deletion"),
        (r'\bopen\s*\([^)]*[\'"][wa][\'"]', "file write in skill body"),
        (r"requests\.(?:post|put|patch|delete)\b", "outbound HTTP request"),
        (r"\bsocket\.", "raw socket usage"),
        (r"\bpickle\.loads?\b", "pickle deserialization (unsafe)"),
        (r"\byaml\.load\b(?!\s*\(.*Loader\s*=)", "unsafe YAML load"),
    ]

    def validate(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
    ) -> SafetyScreeningResult:
        """Screen a skill for safety violations.

        Args:
            skill_name: Name of the skill
            skill_triggers: Trigger phrases for the skill
            skill_body: The skill implementation code

        Returns:
            SafetyScreeningResult with score, issues, violations, and recommendation
        """
        issues: list[str] = []
        violations: list[str] = []

        # Check for dangerous calls
        for pattern, desc in self._DANGEROUS_PATTERNS:
            if re.search(pattern, skill_body, re.IGNORECASE):
                issue = f"Dangerous call: {desc}"
                issues.append(issue)
                violations.append(desc)

        # Check for multiple file write operations
        file_write_patterns = [
            (r'open\s*\([^)]*[\'"][wa][\'"]', "file write"),
            (r"\.write\s*\(", "write operation"),
        ]
        file_ops = sum(1 for p, _ in file_write_patterns if re.search(p, skill_body, re.IGNORECASE))

        if file_ops >= 3:
            issues.append("Multiple file write operations detected")
            violations.append("excessive_file_writes")

        # Check for network operations
        network_patterns = [
            r"\burllib\.",
            r"\bhttplib\.",
            r"\bhttp\.client\.",
            r"\bftplib\.",
        ]
        for pat in network_patterns:
            if re.search(pat, skill_body, re.IGNORECASE):
                issues.append("Network operation detected")
                violations.append("network_operation")
                break

        # Calculate score
        score = 1.0 - (len(issues) * 0.1)
        score = max(0.0, min(1.0, score))

        # Determine status and recommendation
        if score >= self.THRESHOLD:
            recommendation = "Safety screening passed."
            passed = True
        elif score >= 0.9:
            recommendation = "Safety concerns flagged for human review."
            passed = False
        else:
            recommendation = "Critical safety violations — skill blocked."
            passed = False

        return SafetyScreeningResult(
            score=round(score, 4),
            issues=tuple(issues),
            violations=tuple(violations),
            recommendation=recommendation,
            passed=passed,
        )

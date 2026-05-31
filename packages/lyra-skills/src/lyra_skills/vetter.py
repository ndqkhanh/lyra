"""
Skill Vetter — Proteus-inspired security auditing for third-party skill ecosystems.

Per Proteus (Zhou, arXiv 2026): current skill vetting substantially underestimates
residual risk against adaptive, feedback-driven attackers. Single-shot audits miss
>93% of attacks (SkillVetter bypassed ≥93% every cell; AI-Infra-Guard admitted
up to 41.3% joint-success).

This module provides multi-round adversarial vetting for skills installed from
third-party marketplaces. It complements the SelfEvolver's SafetyAudit (which
checks self-evolved skills) by focusing on EXTERNAL threat models.

Five-axis attack space (from Proteus):
1. Prompt injection — hidden instructions that override skill behavior
2. Tool abuse — skill invokes dangerous tools with elevated permissions
3. Data exfiltration — skill leaks environment data to external hosts
4. Supply chain — skill depends on malicious packages or fetches remote code
5. Persistence — skill modifies system state to survive removal

Mitigation: iterative audit-sandbox-oracle pipeline with path expansion
(alternative attack implementations) and surface expansion (transfer to new
attack objectives).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class AttackAxis(str, Enum):
    """Five-axis attack space for skill ecosystems (Proteus taxonomy)."""
    PROMPT_INJECTION = "prompt_injection"
    TOOL_ABUSE = "tool_abuse"
    DATA_EXFILTRATION = "data_exfiltration"
    SUPPLY_CHAIN = "supply_chain"
    PERSISTENCE = "persistence"


class VettingVerdict(str, Enum):
    """Outcome of a single vetting round."""
    PASS = "pass"       # No issues found this round
    FLAG = "flag"       # Suspicious — needs deeper review
    BLOCK = "block"     # Definitively dangerous — reject
    UNCERTAIN = "uncertain"  # Cannot determine (requires oracle)


class VettingSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class VettingFinding:
    """A single finding from a vetting round."""
    finding_id: str
    axis: AttackAxis
    severity: VettingSeverity
    description: str
    evidence: str = ""
    line: int | None = None
    bypass_variants: list[str] = field(default_factory=list)


@dataclass
class VettingReport:
    """Aggregate report from one or more vetting rounds."""
    skill_id: str
    skill_source: str = ""  # marketplace URL, git repo, etc.
    rounds_completed: int = 0
    findings: list[VettingFinding] = field(default_factory=list)
    passed: bool = False
    blocked: bool = False
    attack_surface: dict[str, int] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == VettingSeverity.CRITICAL)

    @property
    def has_blockers(self) -> bool:
        return any(
            f.severity in (VettingSeverity.CRITICAL, VettingSeverity.HIGH)
            for f in self.findings
        )

    @property
    def summary(self) -> str:
        if self.blocked:
            return (
                f"BLOCKED: {len(self.findings)} findings "
                f"({self.critical_count} critical) across {self.rounds_completed} rounds"
            )
        if self.passed:
            return f"PASSED: {self.rounds_completed} rounds, no issues"
        return f"FLAGGED: {len(self.findings)} findings, further review needed"


# ---------------------------------------------------------------------------
# Detection Patterns
# ---------------------------------------------------------------------------


# Prompt injection: hidden instructions that override skill behavior
_PROMPT_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+must", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"\[system\]\(.*?\)", re.IGNORECASE),
    re.compile(r"override\s+(all\s+)?(safety|security|guard)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(constraint|rule|limit)", re.IGNORECASE),
]

# Tool abuse: dangerous tool invocations
_TOOL_ABUSE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\brm\s+-rf\s+/", re.IGNORECASE),
    re.compile(r"\bcurl\s+.*\|\s*(bash|sh|python|perl)", re.IGNORECASE),
    re.compile(r"\bwget\s+.*-O\s+.*\|\s*(bash|sh)", re.IGNORECASE),
    re.compile(r"\bchmod\s+(777|ugo\+rwx)", re.IGNORECASE),
    re.compile(r"\beval\s*\(.*\)", re.IGNORECASE),
    re.compile(r"\bexec\s*\(.*\)", re.IGNORECASE),
    re.compile(r"\bsubprocess\.(call|run|Popen)\s*\(.*shell\s*=\s*True", re.IGNORECASE),
    re.compile(r"\bos\.system\s*\(.*\)", re.IGNORECASE),
]

# Data exfiltration: sending data to external hosts
_EXFILTRATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)\b(api_key|secret|token|password|credential)\s*[=:]\s*['\"][^'\"]{20,}['\"]"),
    re.compile(r"\brequests\.(post|put)\s*\(.*(webhook|slack|discord|telegram)", re.IGNORECASE),
    re.compile(r"\bcurl\s+.*(-d|--data).*(webhook|hook\.)", re.IGNORECASE),
    re.compile(r"\bsmtplib\.SMTP", re.IGNORECASE),
    re.compile(r"\bopen\s*\(.*(\.env|credentials|\.secret)", re.IGNORECASE),
    re.compile(r"\bos\.environ\s*\[", re.IGNORECASE),
    re.compile(r"\b__import__\s*\(\s*['\"]os['\"]\s*\)\s*\.\s*environ", re.IGNORECASE),
]

# Supply chain: malicious dependencies or remote code loading
_SUPPLY_CHAIN_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bpip\s+install\s+", re.IGNORECASE),
    re.compile(r"\bnpm\s+(install|i)\s+", re.IGNORECASE),
    re.compile(r"\bgit\s+clone\s+", re.IGNORECASE),
    re.compile(r"\bimportlib\.(import_module|load_source)\s*\(", re.IGNORECASE),
    re.compile(r"\b__import__\s*\(.*\)", re.IGNORECASE),
    re.compile(r"\bcompile\s*\(.*\)\s*exec\s*\(.*\)", re.IGNORECASE),
    re.compile(r"\burllib\.request\.urlretrieve\s*\(.*\)", re.IGNORECASE),
    re.compile(r"\bwget\.download\s*\(.*\)", re.IGNORECASE),
]

# Persistence: modifying system state to survive removal
_PERSISTENCE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bcrontab\s+", re.IGNORECASE),
    re.compile(r"\bsystemctl\s+(enable|start)\s+", re.IGNORECASE),
    re.compile(r"\blaunchctl\s+(load|submit)\s+", re.IGNORECASE),
    re.compile(r"\.bashrc|\.zshrc|\.profile|\.bash_profile", re.IGNORECASE),
    re.compile(r"/etc/(cron\.|systemd/system|launchd)", re.IGNORECASE),
    re.compile(r"\bwrite\s*\(.*(\.bashrc|\.zshrc|\.profile)", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Skill Vetter
# ---------------------------------------------------------------------------


class SkillVetter:
    """Multi-round adversarial vetting for third-party skill safety.

    Implements the audit-sandbox-oracle pipeline from Proteus. Each round:
    1. Audits the skill against all 5 attack axes
    2. Runs the skill in a sandbox (if configured) to observe runtime behavior
    3. Consults an oracle (stronger model or human) for uncertain findings
    4. Expands attack surface: path expansion (find alternative bypasses) and
       surface expansion (transfer patterns to new attack objectives)

    Key finding from Proteus: single-round audits miss >90% of adaptive attacks.
    Multi-round iterative vetting with path/surface expansion is required.
    """

    # Detection patterns per attack axis
    _AXIS_PATTERNS: dict[AttackAxis, list[re.Pattern]] = {
        AttackAxis.PROMPT_INJECTION: _PROMPT_INJECTION_PATTERNS,
        AttackAxis.TOOL_ABUSE: _TOOL_ABUSE_PATTERNS,
        AttackAxis.DATA_EXFILTRATION: _EXFILTRATION_PATTERNS,
        AttackAxis.SUPPLY_CHAIN: _SUPPLY_CHAIN_PATTERNS,
        AttackAxis.PERSISTENCE: _PERSISTENCE_PATTERNS,
    }

    # Severity per axis for findings
    _AXIS_SEVERITY: dict[AttackAxis, VettingSeverity] = {
        AttackAxis.PROMPT_INJECTION: VettingSeverity.CRITICAL,
        AttackAxis.TOOL_ABUSE: VettingSeverity.CRITICAL,
        AttackAxis.DATA_EXFILTRATION: VettingSeverity.CRITICAL,
        AttackAxis.SUPPLY_CHAIN: VettingSeverity.HIGH,
        AttackAxis.PERSISTENCE: VettingSeverity.HIGH,
    }

    def __init__(
        self,
        max_rounds: int = 5,
        sandbox_enabled: bool = False,
        oracle_fn: Callable[[VettingFinding], VettingVerdict] | None = None,
    ) -> None:
        self._max_rounds = max_rounds
        self._sandbox_enabled = sandbox_enabled
        self._oracle_fn = oracle_fn
        self._total_vetted: int = 0
        self._total_blocked: int = 0

    def vet_skill(
        self,
        skill_id: str,
        content: str,
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> VettingReport:
        """Vet a third-party skill across multiple adversarial rounds.

        Args:
            skill_id: Unique skill identifier.
            content: Full skill content (SKILL.md body text).
            source: Where the skill came from (marketplace URL, repo, etc.).
            metadata: Additional metadata (dependencies, author, version).

        Returns:
            VettingReport with accumulated findings across all rounds.
        """
        self._total_vetted += 1
        report = VettingReport(
            skill_id=skill_id,
            skill_source=source,
            attack_surface={axis.value: 0 for axis in AttackAxis},
        )

        for round_num in range(1, self._max_rounds + 1):
            round_findings = self._audit_round(content, metadata or {})

            # Apply sandbox validation for uncertain findings
            if self._sandbox_enabled:
                round_findings = self._sandbox_validate(round_findings, content)

            # Apply oracle for uncertain findings
            if self._oracle_fn:
                for finding in round_findings:
                    if finding.severity == VettingSeverity.LOW:
                        verdict = self._oracle_fn(finding)
                        if verdict == VettingVerdict.BLOCK:
                            finding.severity = VettingSeverity.HIGH

            report.findings.extend(round_findings)

            # Update attack surface counts
            for finding in round_findings:
                report.attack_surface[finding.axis.value] += 1

            # Check for blockers — if critical findings, block immediately
            if any(f.severity == VettingSeverity.CRITICAL for f in round_findings):
                report.blocked = True
                break

            # Path expansion: generate alternative bypass variants
            content = self._expand_attack_surface(content, round_findings)

            # If no new findings, skill passes
            if not round_findings:
                report.passed = True
                break

        report.rounds_completed = round_num

        if report.blocked:
            self._total_blocked += 1

        return report

    def _audit_round(
        self, content: str, metadata: dict[str, Any],
    ) -> list[VettingFinding]:
        """Run a single audit round against all 5 attack axes."""
        findings: list[VettingFinding] = []

        for axis in AttackAxis:
            for i, pattern in enumerate(self._AXIS_PATTERNS[axis]):
                for match in pattern.finditer(content):
                    # Determine line number
                    line_num = content[:match.start()].count("\n") + 1
                    severity = self._AXIS_SEVERITY[axis]
                    finding_id = hashlib.sha256(
                        f"{axis.value}:{i}:{match.group()}".encode()
                    ).hexdigest()[:12]

                    findings.append(VettingFinding(
                        finding_id=finding_id,
                        axis=axis,
                        severity=severity,
                        description=(
                            f"{axis.value}: matched pattern '{pattern.pattern[:60]}' "
                            f"at line {line_num}"
                        ),
                        evidence=match.group()[:200],
                        line=line_num,
                        bypass_variants=[],  # populated in path expansion
                    ))

        # Check metadata for supply chain risks
        if deps := metadata.get("dependencies", []):
            for dep in deps:
                findings.append(VettingFinding(
                    finding_id=hashlib.sha256(f"dep:{dep}".encode()).hexdigest()[:12],
                    axis=AttackAxis.SUPPLY_CHAIN,
                    severity=VettingSeverity.MEDIUM,
                    description=f"External dependency: {dep}",
                    evidence=dep,
                ))

        return findings

    def _sandbox_validate(
        self,
        findings: list[VettingFinding],
        content: str,
    ) -> list[VettingFinding]:
        """Validate findings by running the skill in a sandbox.

        In a production deployment, this would execute the skill in a Firecracker
        microVM or gVisor sandbox and observe runtime behavior. For now, this is
        a structural validation: check that flagged patterns are in executable
        code paths, not in documentation or comments.
        """
        validated: list[VettingFinding] = []
        for finding in findings:
            # Check if the finding is in a code block (more dangerous)
            # vs a documentation section (less dangerous)
            evidence_line = finding.evidence
            if evidence_line and not self._is_in_documentation(content, evidence_line):
                validated.append(finding)
            else:
                # Downgrade findings in documentation sections
                finding.severity = min(
                    finding.severity, VettingSeverity.LOW,  # type: ignore[arg-type]
                )
                validated.append(finding)
        return validated

    @staticmethod
    def _is_in_documentation(content: str, evidence: str) -> bool:
        """Heuristic: check if the evidence appears in a documentation section."""
        try:
            idx = content.index(evidence)
        except ValueError:
            return False
        # Check if preceded by markdown heading patterns (##, ###, etc.)
        preceding = content[max(0, idx - 500):idx]
        return bool(re.search(
            r"^#{1,4}\s+(description|usage|example|note|reference|see also)",
            preceding,
            re.MULTILINE | re.IGNORECASE,
        ))

    def _expand_attack_surface(
        self,
        content: str,
        findings: list[VettingFinding],
    ) -> str:
        """Generate attack surface expansion for the next round.

        Path expansion: for each finding, generate alternative bypass variants
        that the attacker might use if the obvious pattern is blocked.

        Surface expansion: mutate the content slightly to test whether existing
        patterns can be transferred to new attack objectives.
        """
        for finding in findings:
            # Generate bypass variants by common obfuscation techniques
            evidence = finding.evidence
            variants = []

            # Variant 1: case obfuscation
            variants.append(
                "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(evidence))
            )
            # Variant 2: whitespace insertion
            variants.append(re.sub(r"(\W)", r"  \1  ", evidence))
            # Variant 3: string concatenation
            if len(evidence) > 4:
                mid = len(evidence) // 2
                variants.append(f'"{evidence[:mid]}" + "{evidence[mid:]}"')

            finding.bypass_variants = variants

        # Surface expansion: mutate content with bypass variants
        expanded = content
        for finding in findings:
            for variant in finding.bypass_variants[:1]:  # apply most likely variant
                expanded += f"\n# Bypass variant test: {variant}\n"

        return expanded if findings else content

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_vetted": self._total_vetted,
            "total_blocked": self._total_blocked,
            "block_rate": (
                self._total_blocked / self._total_vetted
                if self._total_vetted > 0 else 0.0
            ),
            "max_rounds": self._max_rounds,
            "sandbox_enabled": self._sandbox_enabled,
            "oracle_available": self._oracle_fn is not None,
        }


# ---------------------------------------------------------------------------
# Quick vetting utilities
# ---------------------------------------------------------------------------


def quick_vet(skill_id: str, content: str, source: str = "") -> VettingReport:
    """Run a single-round vetting pass for fast security checks.

    Use for rapid screening of many skills. For thorough auditing,
    use SkillVetter with multiple rounds.
    """
    vetter = SkillVetter(max_rounds=1)
    return vetter.vet_skill(skill_id, content, source)


def is_safe(skill_id: str, content: str) -> bool:
    """Quick safety check — returns True if skill passes single-round vetting."""
    report = quick_vet(skill_id, content)
    return not report.blocked

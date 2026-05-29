"""
Design Reviewer Skill - Design document review and analysis.

Given a design doc, produces:
- Design pattern assessment
- Anti-pattern detection
- Scalability analysis
- Security review
- Improvement suggestions with rationale

Outputs structured design review report.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DesignQuality(StrEnum):
    """Quality assessment levels."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    ADEQUATE = "ADEQUATE"
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"
    POOR = "POOR"


class ReviewCategory(StrEnum):
    """Categories of design review findings."""

    PATTERN_USAGE = "pattern_usage"
    ANTI_PATTERN = "anti_pattern"
    SCALABILITY = "scalability"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    PERFORMANCE = "performance"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"


@dataclass(frozen=True)
class DesignPatternAssessment:
    """Assessment of a design pattern used in the design."""

    pattern_name: str
    detected: bool
    usage_quality: str
    appropriateness: str
    recommendation: str


@dataclass(frozen=True)
class AntiPatternDetection:
    """An anti-pattern detected in the design."""

    anti_pattern_name: str
    description: str
    location: str
    impact: str
    suggested_refactoring: str
    severity: str


@dataclass(frozen=True)
class ScalabilityFinding:
    """Scalability-related finding."""

    aspect: str
    current_state: str
    risk_level: str
    bottleneck_description: str
    recommendation: str
    estimated_scale_limit: str


@dataclass(frozen=True)
class DesignReviewFinding:
    """A single design review finding."""

    id: str
    category: ReviewCategory
    title: str
    description: str
    rationale: str
    suggestion: str
    quality: DesignQuality
    effort_to_fix: str


@dataclass(frozen=True)
class ImprovementSuggestion:
    """An improvement suggestion with rationale."""

    area: str
    suggestion: str
    rationale: str
    expected_impact: str
    implementation_difficulty: str


@dataclass(frozen=True)
class DesignReviewReport:
    """Complete design review report."""

    design_title: str
    overall_quality: DesignQuality
    pattern_assessments: tuple[DesignPatternAssessment, ...]
    anti_patterns: tuple[AntiPatternDetection, ...]
    scalability_findings: tuple[ScalabilityFinding, ...]
    findings: tuple[DesignReviewFinding, ...]
    improvements: tuple[ImprovementSuggestion, ...]
    score_summary: dict[str, Any]


# ---------------------------------------------------------------------------
# Patterns to check
# ---------------------------------------------------------------------------
_COMMON_PATTERNS: list[tuple[str, list[str], str]] = [
    ("Repository Pattern", ["repository", "data access", "dao"], "Data access abstraction layer"),
    ("Factory Pattern", ["factory", "creator", "builder"], "Object creation encapsulation"),
    (
        "Observer Pattern",
        ["observer", "event", "listener", "pub/sub", "publish-subscribe"],
        "Event-driven communication",
    ),
    (
        "Strategy Pattern",
        ["strategy", "policy", "algorithm", "pluggable"],
        "Interchangeable algorithms",
    ),
    ("Singleton Pattern", ["singleton", "global", "shared instance"], "Single instance guarantee"),
    (
        "Dependency Injection",
        ["dependency injection", "di", "inversion of control", "ioc"],
        "Dependency management",
    ),
    ("Circuit Breaker", ["circuit breaker", "circuit_breaker", "resilience"], "Failure handling"),
    (
        "CQRS",
        ["cqrs", "command query", "read model", "write model"],
        "Command-Query Responsibility Segregation",
    ),
    (
        "Event Sourcing",
        ["event sourcing", "event store", "event log"],
        "Event-based state management",
    ),
]

_ANTI_PATTERNS: list[tuple[str, list[str], str, str]] = [
    (
        "God Class",
        ["god class", "god object", "blob", "utility class"],
        "A class with too many responsibilities",
        "HIGH",
    ),
    (
        "Spaghetti Code",
        ["spaghetti", "tight coupling", "circular dependency"],
        "Unstructured interdependent code",
        "HIGH",
    ),
    (
        "Golden Hammer",
        ["golden hammer", "over-engineering", "overuse"],
        "Applying a familiar solution everywhere",
        "MEDIUM",
    ),
    (
        "Singleton Overuse",
        ["excessive singleton", "global state"],
        "Overuse of global state via singletons",
        "MEDIUM",
    ),
    (
        "Magic Numbers",
        ["magic number", "magic string", "hardcoded"],
        "Hardcoded values without named constants",
        "LOW",
    ),
]


class DesignReviewer:
    """Design review skill producing structured review reports."""

    def run(self, input_data: dict) -> dict:
        """Run design review.

        Args:
            input_data: Dictionary with keys:
                - design_doc: Design document text to review
                - design_title: Optional design title (default "Design Document")

        Returns:
            Dictionary with design review report data.
        """
        design_doc = input_data.get("design_doc", "")
        if not design_doc:
            return {"error": "No design document provided"}

        title = input_data.get("design_title", "Design Document")
        doc_lower = design_doc.lower()

        patterns = self._assess_patterns(doc_lower)
        anti_patterns = self._detect_anti_patterns(doc_lower)
        scalability = self._assess_scalability(doc_lower)
        findings = self._generate_findings(doc_lower, patterns, anti_patterns)
        improvements = self._generate_improvements(doc_lower)
        overall = self._compute_overall_quality(patterns, anti_patterns, scalability)
        score_summary = self._compute_scores(patterns, anti_patterns, scalability, findings)

        return DesignReviewReport(
            design_title=title,
            overall_quality=overall,
            pattern_assessments=tuple(patterns),
            anti_patterns=tuple(anti_patterns),
            scalability_findings=tuple(scalability),
            findings=tuple(findings),
            improvements=tuple(improvements),
            score_summary=score_summary,
        ).__dict__ | {
            "pattern_assessments": [p.__dict__ for p in patterns],
            "anti_patterns": [a.__dict__ for a in anti_patterns],
            "scalability_findings": [s.__dict__ for s in scalability],
            "findings": [f.__dict__ for f in findings],
            "improvements": [i.__dict__ for i in improvements],
        }

    @staticmethod
    def _assess_patterns(design_lower: str) -> list[DesignPatternAssessment]:
        assessments: list[DesignPatternAssessment] = []
        for pattern_name, keywords, _ in _COMMON_PATTERNS:
            detected = any(kw in design_lower for kw in keywords)
            if detected:
                quality = (
                    "Good"
                    if pattern_name
                    in ("Repository Pattern", "Dependency Injection", "Circuit Breaker")
                    else "Fair"
                )
                appropriateness = (
                    "Appropriate for this context"
                    if quality == "Good"
                    else "Consider applicability"
                )
                recommendation = (
                    "Keep and maintain this pattern"
                    if quality == "Good"
                    else "Verify this pattern solves the right problem"
                )
            else:
                quality = "N/A"
                appropriateness = "Not applicable or not yet evaluated"
                recommendation = f"Consider whether {pattern_name} would benefit this design"
            assessments.append(
                DesignPatternAssessment(
                    pattern_name=pattern_name,
                    detected=detected,
                    usage_quality=quality,
                    appropriateness=appropriateness,
                    recommendation=recommendation,
                )
            )
        return assessments

    @staticmethod
    def _detect_anti_patterns(
        design_lower: str,
    ) -> list[AntiPatternDetection]:
        detections: list[AntiPatternDetection] = []
        for name, keywords, desc, severity in _ANTI_PATTERNS:
            if any(kw in design_lower for kw in keywords):
                detections.append(
                    AntiPatternDetection(
                        anti_pattern_name=name,
                        description=desc,
                        location="Throughout design (keyword matched)",
                        impact=(
                            "Major architectural concern"
                            if severity == "HIGH"
                            else "Quality concern"
                        ),
                        suggested_refactoring=f"Refactor to eliminate {name.lower()} pattern",
                        severity=severity,
                    )
                )
        return detections

    @staticmethod
    def _assess_scalability(design_lower: str) -> list[ScalabilityFinding]:
        findings_list: list[ScalabilityFinding] = []

        has_horizontal = (
            "horizontal" in design_lower
            or "auto-scaling" in design_lower
            or "scale out" in design_lower
        )
        has_sharding = "shard" in design_lower or "partition" in design_lower
        has_cache = "cache" in design_lower or "caching" in design_lower
        has_queue = (
            "queue" in design_lower or "async" in design_lower or "message broker" in design_lower
        )

        findings_list.append(
            ScalabilityFinding(
                aspect="Compute Scaling",
                current_state=(
                    "Horizontal scaling addressed" if has_horizontal else "Not explicitly addressed"
                ),
                risk_level="LOW" if has_horizontal else "HIGH",
                bottleneck_description="Single compute instance limits throughput",
                recommendation="Design for horizontal scaling with stateless application servers",
                estimated_scale_limit=(
                    "10x with horizontal scaling" if has_horizontal else "< 2x without it"
                ),
            )
        )

        findings_list.append(
            ScalabilityFinding(
                aspect="Data Scaling",
                current_state=(
                    "Sharding/partitioning addressed"
                    if has_sharding
                    else "Not explicitly addressed"
                ),
                risk_level="LOW" if has_sharding else "HIGH",
                bottleneck_description="Single database becomes bottleneck as data grows",
                recommendation=(
                    "Implement data partitioning strategy (e.g., hash-based or range-based"
                    "sharding)"
                ),
                estimated_scale_limit="100x with sharding" if has_sharding else "< 5x without it",
            )
        )

        findings_list.append(
            ScalabilityFinding(
                aspect="Caching Strategy",
                current_state=(
                    "Caching strategy addressed" if has_cache else "Not explicitly addressed"
                ),
                risk_level="MEDIUM" if has_cache else "HIGH",
                bottleneck_description="Repeated computations and database queries under load",
                recommendation=(
                    "Implement multi-tier caching (L1: in-memory, L2: distributed Redis)"
                ),
                estimated_scale_limit=(
                    "Caching can improve throughput 10-100x for read-heavy workloads"
                ),
            )
        )

        findings_list.append(
            ScalabilityFinding(
                aspect="Async Processing",
                current_state=(
                    "Async/queue pattern addressed" if has_queue else "Not explicitly addressed"
                ),
                risk_level="LOW" if has_queue else "MEDIUM",
                bottleneck_description="Synchronous processing blocks resources under load",
                recommendation="Use message queues for decoupling and buffering",
                estimated_scale_limit="Async processing enables 10x+ of synchronous throughput",
            )
        )

        return findings_list

    @staticmethod
    def _generate_findings(
        design_lower: str,
        patterns: list[DesignPatternAssessment],
        anti_patterns: list[AntiPatternDetection],
    ) -> list[DesignReviewFinding]:
        findings_list: list[DesignReviewFinding] = []
        finding_id = 0

        # Pattern coverage finding
        detected_count = sum(1 for p in patterns if p.detected)
        if detected_count < 3:
            finding_id += 1
            findings_list.append(
                DesignReviewFinding(
                    id=f"DRF-{finding_id:03d}",
                    category=ReviewCategory.PATTERN_USAGE,
                    title="Limited design pattern usage",
                    description=(
                        f"Only {detected_count} common design patterns detected in the design"
                    ),
                    rationale="Design patterns provide proven solutions to recurring problems",
                    suggestion="Consider applying additional patterns appropriate to the domain",
                    quality=DesignQuality.NEEDS_IMPROVEMENT,
                    effort_to_fix="Medium",
                )
            )

        # Anti-pattern finding
        if anti_patterns:
            for ap in anti_patterns:
                finding_id += 1
                findings_list.append(
                    DesignReviewFinding(
                        id=f"DRF-{finding_id:03d}",
                        category=ReviewCategory.ANTI_PATTERN,
                        title=f"Anti-pattern detected: {ap.anti_pattern_name}",
                        description=ap.description,
                        rationale=(
                            "Anti-patterns indicate design problems that will compound over time"
                        ),
                        suggestion=ap.suggested_refactoring,
                        quality=DesignQuality.NEEDS_IMPROVEMENT,
                        effort_to_fix="High" if ap.severity == "HIGH" else "Medium",
                    )
                )

        # Scalability finding
        if "scalability" not in design_lower and "scale" not in design_lower:
            finding_id += 1
            findings_list.append(
                DesignReviewFinding(
                    id=f"DRF-{finding_id:03d}",
                    category=ReviewCategory.SCALABILITY,
                    title="Scalability not addressed",
                    description=(
                        "Design document does not discuss scalability requirements or strategy"
                    ),
                    rationale=(
                        "Scalability is a critical non-functional requirement for production"
                        "systems"
                    ),
                    suggestion=(
                        "Add a scalability section covering expected load, bottlenecks, and"
                        "scaling approach"
                    ),
                    quality=DesignQuality.NEEDS_IMPROVEMENT,
                    effort_to_fix="Medium",
                )
            )

        # Monitoring finding
        if "monitor" not in design_lower and "observability" not in design_lower:
            finding_id += 1
            findings_list.append(
                DesignReviewFinding(
                    id=f"DRF-{finding_id:03d}",
                    category=ReviewCategory.COMPLETENESS,
                    title="Monitoring and observability not discussed",
                    description="No mention of logging, metrics, tracing, or alerting",
                    rationale=(
                        "Production systems require observability for operation and debugging"
                    ),
                    suggestion=(
                        "Add observability section covering logs, metrics, traces, and dashboards"
                    ),
                    quality=DesignQuality.ADEQUATE,
                    effort_to_fix="Medium",
                )
            )

        # Error handling finding
        if "error handling" not in design_lower and "error" not in design_lower:
            finding_id += 1
            findings_list.append(
                DesignReviewFinding(
                    id=f"DRF-{finding_id:03d}",
                    category=ReviewCategory.COMPLETENESS,
                    title="Error handling strategy missing",
                    description="Design does not explicitly cover error handling and recovery",
                    rationale="Robust error handling is essential for system reliability",
                    suggestion=(
                        "Add error handling patterns: retries, circuit breakers, graceful"
                        "degradation"
                    ),
                    quality=DesignQuality.ADEQUATE,
                    effort_to_fix="Medium",
                )
            )

        return findings_list

    @staticmethod
    def _generate_improvements(design_lower: str) -> list[ImprovementSuggestion]:
        suggestions: list[ImprovementSuggestion] = [
            ImprovementSuggestion(
                area="Documentation",
                suggestion="Add a glossary of terms and architectural decision records (ADRs)",
                rationale=(
                    "Improves onboarding and documents design rationale for future maintainers"
                ),
                expected_impact="Reduces onboarding time and design drift",
                implementation_difficulty="Low",
            ),
            ImprovementSuggestion(
                area="Testing Strategy",
                suggestion="Define testing strategy: unit, integration, contract, and E2E tests",
                rationale="Ensures quality at every level and catches regressions early",
                expected_impact="Higher confidence in deployments, fewer production issues",
                implementation_difficulty="Low",
            ),
            ImprovementSuggestion(
                area="Security",
                suggestion=(
                    "Add a security section covering authentication, authorization, and data"
                    "protection"
                ),
                rationale=(
                    "Security is often an afterthought; addressing it in design prevents costly"
                    "rework"
                ),
                expected_impact="Reduces security vulnerabilities and compliance risks",
                implementation_difficulty="Medium",
            ),
            ImprovementSuggestion(
                area="Data Flow Diagrams",
                suggestion="Add sequence diagrams for critical user flows and data flows",
                rationale="Visualizing flows exposes hidden complexity and integration issues",
                expected_impact="Earlier detection of design flaws and integration problems",
                implementation_difficulty="Low",
            ),
            ImprovementSuggestion(
                area="Migration Plan",
                suggestion="Include a phased rollout and rollback plan",
                rationale="Reduces deployment risk and provides clear path to recovery",
                expected_impact="Safer deployments and faster recovery from issues",
                implementation_difficulty="Medium",
            ),
        ]

        if "deployment" not in design_lower and "release" not in design_lower:
            suggestions.append(
                ImprovementSuggestion(
                    area="Deployment",
                    suggestion="Add deployment strategy: blue-green, canary, or rolling update",
                    rationale="Defines how changes reach production with minimal risk",
                    expected_impact="Zero-downtime deployments and quick rollbacks",
                    implementation_difficulty="Medium",
                )
            )

        return suggestions

    @staticmethod
    def _compute_overall_quality(
        patterns: list[DesignPatternAssessment],
        anti_patterns: list[AntiPatternDetection],
        scalability: list[ScalabilityFinding],
    ) -> DesignQuality:
        detected_patterns = sum(1 for p in patterns if p.detected)
        anti_pattern_count = len(anti_patterns)
        high_risk_scalability = sum(1 for s in scalability if s.risk_level == "HIGH")

        if detected_patterns >= 4 and anti_pattern_count == 0 and high_risk_scalability == 0:
            return DesignQuality.EXCELLENT
        if detected_patterns >= 3 and anti_pattern_count <= 1 and high_risk_scalability <= 1:
            return DesignQuality.GOOD
        if detected_patterns >= 2 and anti_pattern_count <= 2:
            return DesignQuality.ADEQUATE
        if anti_pattern_count >= 3:
            return DesignQuality.POOR
        return DesignQuality.NEEDS_IMPROVEMENT

    @staticmethod
    def _compute_scores(
        patterns: list[DesignPatternAssessment],
        anti_patterns: list[AntiPatternDetection],
        scalability: list[ScalabilityFinding],
        findings: list[DesignReviewFinding],
    ) -> dict[str, Any]:
        pattern_score = min(100, sum(1 for p in patterns if p.detected) * 12)
        anti_pattern_penalty = min(40, len(anti_patterns) * 10)
        scalability_score = max(
            0,
            100
            - sum(25 for s in scalability if s.risk_level == "HIGH")
            - sum(15 for s in scalability if s.risk_level == "MEDIUM"),
        )
        findings_count = len(findings)
        findings_penalty = min(30, findings_count * 5)

        overall = max(
            0, min(100, pattern_score + scalability_score - anti_pattern_penalty - findings_penalty)
        )

        return {
            "pattern_score": pattern_score,
            "anti_pattern_penalty": anti_pattern_penalty,
            "scalability_score": scalability_score,
            "findings_penalty": findings_penalty,
            "overall_score": overall,
            "pass_threshold": 60,
            "passed": overall >= 60,
        }

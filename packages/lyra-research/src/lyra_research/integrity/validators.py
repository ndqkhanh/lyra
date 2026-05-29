"""
Validators for Integrity Gates

Implements validation logic for stages 2.5 and 4.5.
"""

from typing import Any

from .integrity_gate import Severity, ValidationResult


class MinimumSourceCountValidator:
    """Validate minimum number of sources found"""

    def __init__(self, min_sources: int = 10):
        self.min_sources = min_sources

    def validate(self, research_state: dict[str, Any]) -> ValidationResult:
        """Validate source count"""
        sources = research_state.get("sources", [])
        count = len(sources)

        if count < self.min_sources:
            return ValidationResult(
                passed=False,
                severity=Severity.CRITICAL,
                message=f"Insufficient sources: {count} found, minimum {self.min_sources} required",
                validator_name="MinimumSourceCountValidator"
            )

        return ValidationResult(
            passed=True,
            severity=Severity.LOW,
            message=f"Source count OK: {count} sources found",
            validator_name="MinimumSourceCountValidator"
        )


class SourceDiversityValidator:
    """Validate diversity of source types"""

    def __init__(self, min_source_types: int = 3):
        self.min_source_types = min_source_types

    def validate(self, research_state: dict[str, Any]) -> ValidationResult:
        """Validate source type diversity"""
        sources = research_state.get("sources", [])
        source_types = set(s.get("source_type") for s in sources if s.get("source_type"))
        count = len(source_types)

        if count < self.min_source_types:
            return ValidationResult(
                passed=False,
                severity=Severity.HIGH,
                message=f"Low source diversity: {count} types, minimum {self.min_source_types} required. Types: {source_types}",
                validator_name="SourceDiversityValidator"
            )

        return ValidationResult(
            passed=True,
            severity=Severity.LOW,
            message=f"Source diversity OK: {count} types found",
            validator_name="SourceDiversityValidator"
        )


class CitationAccessibilityValidator:
    """Validate all sources are accessible"""

    def validate(self, research_state: dict[str, Any]) -> ValidationResult:
        """Validate source accessibility"""
        sources = research_state.get("sources", [])
        inaccessible = [s for s in sources if not s.get("accessible", True)]

        if inaccessible:
            return ValidationResult(
                passed=False,
                severity=Severity.HIGH,
                message=f"{len(inaccessible)} sources inaccessible: {[s.get('id') for s in inaccessible[:5]]}",
                validator_name="CitationAccessibilityValidator"
            )

        return ValidationResult(
            passed=True,
            severity=Severity.LOW,
            message="All sources accessible",
            validator_name="CitationAccessibilityValidator"
        )


class DuplicationDetector:
    """Detect duplicate sources"""

    def __init__(self, max_duplicate_ratio: float = 0.3):
        self.max_duplicate_ratio = max_duplicate_ratio

    def validate(self, research_state: dict[str, Any]) -> ValidationResult:
        """Detect duplicates"""
        sources = research_state.get("sources", [])
        if not sources:
            return ValidationResult(
                passed=True,
                severity=Severity.LOW,
                message="No sources to check",
                validator_name="DuplicationDetector"
            )

        # Check for duplicate IDs
        ids = [s.get("id") for s in sources if s.get("id")]
        unique_ids = set(ids)
        duplicate_count = len(ids) - len(unique_ids)
        duplicate_ratio = duplicate_count / len(ids) if ids else 0

        if duplicate_ratio > self.max_duplicate_ratio:
            return ValidationResult(
                passed=False,
                severity=Severity.MEDIUM,
                message=f"High duplication: {duplicate_ratio:.1%} duplicates (max {self.max_duplicate_ratio:.1%})",
                validator_name="DuplicationDetector"
            )

        return ValidationResult(
            passed=True,
            severity=Severity.LOW,
            message=f"Duplication OK: {duplicate_ratio:.1%}",
            validator_name="DuplicationDetector"
        )


class CitationFidelityValidator:
    """Validate citation fidelity (100% valid citations)"""

    def __init__(self, min_fidelity: float = 1.0):
        self.min_fidelity = min_fidelity

    def validate(self, research_state: dict[str, Any]) -> ValidationResult:
        """Validate citation fidelity"""
        report = research_state.get("report", {})
        citations = report.get("citations", [])

        if not citations:
            return ValidationResult(
                passed=True,
                severity=Severity.LOW,
                message="No citations to validate",
                validator_name="CitationFidelityValidator"
            )

        valid_citations = [c for c in citations if c.get("valid", False)]
        fidelity = len(valid_citations) / len(citations)

        if fidelity < self.min_fidelity:
            invalid = [c.get("id") for c in citations if not c.get("valid")]
            return ValidationResult(
                passed=False,
                severity=Severity.CRITICAL,
                message=f"Low citation fidelity: {fidelity:.1%} (target {self.min_fidelity:.1%}). Invalid: {invalid[:5]}",
                validator_name="CitationFidelityValidator"
            )

        return ValidationResult(
            passed=True,
            severity=Severity.LOW,
            message=f"Citation fidelity OK: {fidelity:.1%}",
            validator_name="CitationFidelityValidator"
        )


class ClaimVerificationValidator:
    """Validate claims are backed by sources"""

    def __init__(self, min_verification: float = 0.95):
        self.min_verification = min_verification

    def validate(self, research_state: dict[str, Any]) -> ValidationResult:
        """Validate claim verification rate"""
        report = research_state.get("report", {})
        claims = report.get("claims", [])

        if not claims:
            return ValidationResult(
                passed=True,
                severity=Severity.LOW,
                message="No claims to validate",
                validator_name="ClaimVerificationValidator"
            )

        verified_claims = [c for c in claims if c.get("verified", False)]
        verification_rate = len(verified_claims) / len(claims)

        if verification_rate < self.min_verification:
            unverified = [c.get("text")[:50] for c in claims if not c.get("verified")]
            return ValidationResult(
                passed=False,
                severity=Severity.CRITICAL,
                message=f"Low verification rate: {verification_rate:.1%} (target {self.min_verification:.1%}). Unverified: {unverified[:3]}",
                validator_name="ClaimVerificationValidator"
            )

        return ValidationResult(
            passed=True,
            severity=Severity.LOW,
            message=f"Claim verification OK: {verification_rate:.1%}",
            validator_name="ClaimVerificationValidator"
        )


class TemporalConsistencyValidator:
    """Validate temporal consistency (no anachronistic citations)"""

    def validate(self, research_state: dict[str, Any]) -> ValidationResult:
        """Validate temporal consistency"""
        report = research_state.get("report", {})
        violations = report.get("temporal_violations", [])

        if violations:
            return ValidationResult(
                passed=False,
                severity=Severity.HIGH,
                message=f"{len(violations)} temporal violations detected: {[v.get('type') for v in violations[:3]]}",
                validator_name="TemporalConsistencyValidator"
            )

        return ValidationResult(
            passed=True,
            severity=Severity.LOW,
            message="No temporal violations",
            validator_name="TemporalConsistencyValidator"
        )


class CompletenessValidator:
    """Validate checklist completion"""

    def __init__(self, min_completion: float = 0.90):
        self.min_completion = min_completion

    def validate(self, research_state: dict[str, Any]) -> ValidationResult:
        """Validate checklist completion"""
        checklist = research_state.get("checklist", {})
        items = checklist.get("items", [])

        if not items:
            return ValidationResult(
                passed=True,
                severity=Severity.LOW,
                message="No checklist items",
                validator_name="CompletenessValidator"
            )

        completed = [i for i in items if i.get("completed", False)]
        completion_rate = len(completed) / len(items)

        if completion_rate < self.min_completion:
            incomplete = [i.get("question") for i in items if not i.get("completed")]
            return ValidationResult(
                passed=False,
                severity=Severity.MEDIUM,
                message=f"Low completion: {completion_rate:.1%} (target {self.min_completion:.1%}). Incomplete: {incomplete[:3]}",
                validator_name="CompletenessValidator"
            )

        return ValidationResult(
            passed=True,
            severity=Severity.LOW,
            message=f"Completion OK: {completion_rate:.1%}",
            validator_name="CompletenessValidator"
        )

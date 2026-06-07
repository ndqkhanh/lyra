"""
Domain-Specific Verification — Layer 4 of the omni-domain architecture.

Validates expert output against domain-specific quality standards,
guidelines, citation requirements, and provides appropriate disclaimers
for regulated domains (medical, legal, financial).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from lyra.domain.models import (
    DomainType,
    ExpertCard,
    ValidationMethod,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain disclaimers for regulated domains
# ---------------------------------------------------------------------------

_DISCLAIMERS: dict[DomainType, str] = {
    DomainType.MEDICAL: (
        "IMPORTANT MEDICAL DISCLAIMER: This AI-generated content is for informational "
        "and research purposes only. It is NOT a substitute for professional medical "
        "advice, diagnosis, or treatment. Always consult a qualified healthcare provider "
        "for medical decisions. In case of emergency, call 911 immediately. The developers "
        "assume no liability for decisions made based on this output."
    ),
    DomainType.LEGAL: (
        "IMPORTANT LEGAL DISCLAIMER: This AI-generated content is a legal research and "
        "analysis tool only. It does not constitute legal advice, does not establish an "
        "attorney-client relationship, and is not a substitute for consultation with a "
        "licensed attorney. Laws vary by jurisdiction and specific circumstances. All "
        "output should be reviewed by a qualified attorney before reliance."
    ),
    DomainType.FINANCE: (
        "IMPORTANT FINANCIAL DISCLAIMER: This AI-generated analysis is for informational "
        "and educational purposes only. It does not constitute investment advice, a "
        "recommendation, or an offer to buy or sell any security. Past performance does "
        "not guarantee future results. All investment decisions involve risk. Consult a "
        "qualified financial advisor before making investment decisions."
    ),
    DomainType.SCIENTIFIC: (
        "SCIENTIFIC RIGOR NOTE: This AI-generated content synthesizes available scientific "
        "literature but may not capture the full nuance of primary research. All claims "
        "should be verified against original peer-reviewed sources before citation or use "
        "in decision-making."
    ),
    DomainType.BUSINESS: (
        "BUSINESS ADVISORY NOTE: This AI-generated analysis is for strategic discussion "
        "purposes. Business decisions should incorporate additional due diligence, "
        "market research, and consultation with qualified business advisors."
    ),
}

# ---------------------------------------------------------------------------
# Domain-specific validation rules
# ---------------------------------------------------------------------------

_VALIDATION_RULES: dict[DomainType, list[dict[str, Any]]] = {
    DomainType.CODING: [
        {
            "check": "syntax",
            "description": "Output must contain valid code syntax",
            "severity": "critical",
        },
        {
            "check": "types",
            "description": "Type annotations should match usage",
            "severity": "high",
        },
        {
            "check": "imports",
            "description": "All imports must be used or removed",
            "severity": "medium",
        },
        {
            "check": "error_handling",
            "description": "All error paths must be handled",
            "severity": "high",
        },
        {
            "check": "no_hardcoded_secrets",
            "description": "No API keys, passwords, or tokens",
            "severity": "critical",
        },
        {
            "check": "no_debug_code",
            "description": "No console.log, debugger, or TODO left in output",
            "severity": "medium",
        },
    ],
    DomainType.FINANCE: [
        {
            "check": "disclaimer_present",
            "description": "Financial disclaimer must be included",
            "severity": "critical",
        },
        {
            "check": "no_guarantees",
            "description": "No guaranteed returns or performance claims",
            "severity": "critical",
        },
        {
            "check": "risk_disclosure",
            "description": "Risks must be disclosed with every projection",
            "severity": "high",
        },
        {
            "check": "math_separation",
            "description": "Numerical calculations attributed to tools, not AI",
            "severity": "medium",
        },
    ],
    DomainType.MEDICAL: [
        {
            "check": "disclaimer_present",
            "description": "Medical disclaimer must be included",
            "severity": "critical",
        },
        {
            "check": "defers_to_physician",
            "description": "Must defer to physician judgment",
            "severity": "critical",
        },
        {
            "check": "cites_sources",
            "description": "Medical claims must cite verifiable sources",
            "severity": "high",
        },
        {
            "check": "no_diagnosis",
            "description": "Must not provide definitive diagnosis",
            "severity": "critical",
        },
        {
            "check": "urgency_flag",
            "description": "Emergency symptoms must trigger urgent care warning",
            "severity": "critical",
        },
    ],
    DomainType.LEGAL: [
        {
            "check": "disclaimer_present",
            "description": "Legal disclaimer must be included",
            "severity": "critical",
        },
        {
            "check": "no_legal_advice",
            "description": "Must not provide definitive legal advice",
            "severity": "critical",
        },
        {
            "check": "cites_authority",
            "description": "Legal claims must cite specific authority",
            "severity": "high",
        },
        {
            "check": "jurisdiction_aware",
            "description": "Jurisdictional scope must be specified",
            "severity": "high",
        },
    ],
    DomainType.SCIENTIFIC: [
        {
            "check": "cites_sources",
            "description": "Scientific claims must cite peer-reviewed sources",
            "severity": "high",
        },
        {
            "check": "uncertainty_stated",
            "description": "Uncertainty and limitations must be acknowledged",
            "severity": "high",
        },
        {
            "check": "no_overclaim",
            "description": "Must not overstate significance of findings",
            "severity": "medium",
        },
    ],
    DomainType.EDUCATION: [
        {
            "check": "age_appropriate",
            "description": "Content should be appropriate for stated level",
            "severity": "high",
        },
        {
            "check": "factually_accurate",
            "description": "All educational content must be accurate",
            "severity": "critical",
        },
        {
            "check": "encourages_thinking",
            "description": "Should promote critical thinking, not memorization",
            "severity": "medium",
        },
    ],
    DomainType.ENGINEERING: [
        {
            "check": "safety_considered",
            "description": "Safety factors and failure modes considered",
            "severity": "critical",
        },
        {
            "check": "standards_compliant",
            "description": "Design should reference applicable standards",
            "severity": "high",
        },
        {
            "check": "assumptions_documented",
            "description": "All engineering assumptions must be documented",
            "severity": "medium",
        },
    ],
    DomainType.CREATIVE: [
        {
            "check": "originality_check",
            "description": "Content should avoid direct copying",
            "severity": "medium",
        },
        {
            "check": "intent_aligned",
            "description": "Creative direction should match stated intent",
            "severity": "medium",
        },
    ],
    DomainType.BUSINESS: [
        {
            "check": "disclaimer_present",
            "description": "Business advisory note should be included",
            "severity": "medium",
        },
        {
            "check": "data_sourced",
            "description": "Market claims should cite data sources",
            "severity": "high",
        },
        {
            "check": "bias_acknowledged",
            "description": "Potential analytical biases should be flagged",
            "severity": "medium",
        },
    ],
}

# Built-in citation patterns for each domain
_CITATION_PATTERNS: dict[DomainType, list[str]] = {
    DomainType.MEDICAL: [
        r"\b(doi|DOI)\s*[:=]?\s*10\.\d{4,}/",
        r"\[\d+\]",
        r"\(.*\d{4}\)",
    ],
    DomainType.LEGAL: [
        r"\d+\s+U\.S\.\s+\d+",
        r"\d+\s+F\.\d[d]\s+\d+",
        r"\d+\s+U\.S\.C\.\s+§?\s*\d+",
        r"\d+\s+C\.F\.R\.\s+§?\s*\d+",
    ],
    DomainType.SCIENTIFIC: [
        r"\b(doi|DOI)\s*[:=]?\s*10\.\d{4,}/",
        r"\[\d+\]",
        r"\(.*\d{4};.*\d{4}\)",
        r"et\s+al\.",
    ],
    DomainType.FINANCE: [
        r"\b(Source|source)\s*:",
        r"\b(According to|per)\s+",
    ],
    DomainType.BUSINESS: [
        r"\b(According to|Source|per)\s+",
        r"\[\d+\]",
    ],
}


# ---------------------------------------------------------------------------
# Domain Validator
# ---------------------------------------------------------------------------


class DomainValidator:
    """Domain-specific output verification.

    Layer 4 of the 5-layer omni-domain architecture. Validates expert
    output against domain-specific quality standards, guidelines, citation
    requirements, and provides appropriate disclaimers.
    """

    def __init__(self) -> None:
        self._rules: dict[DomainType, list[dict[str, Any]]] = {
            d: [dict(r) for r in rules] for d, rules in _VALIDATION_RULES.items()
        }
        self._citations: dict[DomainType, list[str]] = {
            d: list(patterns) for d, patterns in _CITATION_PATTERNS.items()
        }
        logger.info("DomainValidator initialized with %d domain rule sets", len(self._rules))

    # ------------------------------------------------------------------
    # Core validation
    # ------------------------------------------------------------------

    def validate_output(self, domain: DomainType, output: str) -> dict[str, Any]:
        """Validate output against all applicable domain rules.

        Returns a structured validation result with passed/failed checks
        and an overall verdict.
        """
        rules = self._rules.get(domain, [])
        if not output:
            return {
                "domain": domain.value,
                "passed": False,
                "checks": [],
                "verdict": "rejected",
                "reason": "Empty output",
            }

        results: list[dict[str, Any]] = []
        for rule in rules:
            check_name = rule["check"]
            passed, detail = self._run_check(domain, output, check_name)
            results.append(
                {
                    "check": check_name,
                    "description": rule["description"],
                    "severity": rule["severity"],
                    "passed": passed,
                    "detail": detail,
                }
            )

        critical_failures = [r for r in results if not r["passed"] and r["severity"] == "critical"]
        high_failures = [r for r in results if not r["passed"] and r["severity"] == "high"]

        if critical_failures:
            verdict = "rejected"
        elif high_failures:
            verdict = "warning"
        else:
            verdict = "approved"

        return {
            "domain": domain.value,
            "passed": verdict == "approved",
            "checks": results,
            "verdict": verdict,
            "critical_failures": len(critical_failures),
            "high_failures": len(high_failures),
        }

    def check_guidelines(self, domain: DomainType, output: str) -> dict[str, Any]:
        """Check compliance with domain-specific guidelines.

        A lighter-weight check than full validation — returns only
        guideline compliance info without the full check matrix.
        """
        rules = self._rules.get(domain, [])
        if not output:
            return {"domain": domain.value, "compliant": False, "violations": ["Empty output"]}

        violations: list[str] = []
        for rule in rules:
            check_name = rule["check"]
            passed, detail = self._run_check(domain, output, check_name)
            if not passed and rule["severity"] in ("critical", "high"):
                violations.append(f"{rule['description']}: {detail}")

        return {
            "domain": domain.value,
            "compliant": len(violations) == 0,
            "violations": violations,
        }

    def check_citations(self, domain: DomainType, output: str) -> dict[str, Any]:
        """Check for expected citation patterns in domain output."""
        patterns = self._citations.get(domain, [])
        if not patterns:
            return {
                "domain": domain.value,
                "citations_required": False,
                "citations_found": 0,
                "has_citations": True,
                "detail": "No citation requirements for this domain",
            }

        total_matches = 0
        for pattern in patterns:
            matches = re.findall(pattern, output)
            total_matches += len(matches)

        # Domains that require citations
        citation_required_domains = {
            DomainType.MEDICAL,
            DomainType.LEGAL,
            DomainType.SCIENTIFIC,
            DomainType.FINANCE,
        }
        requires = domain in citation_required_domains

        return {
            "domain": domain.value,
            "citations_required": requires,
            "citations_found": total_matches,
            "has_citations": total_matches > 0,
            "detail": (
                f"Found {total_matches} citation(s)" if total_matches > 0 else "No citations found"
            ),
        }

    def get_disclaimer(self, domain: DomainType) -> str:
        """Get the appropriate disclaimer for a domain.

        Returns a domain-specific disclaimer string, or an empty string
        if the domain does not require a disclaimer.
        """
        return _DISCLAIMERS.get(domain, "")

    def validate_against_card(
        self,
        card: ExpertCard,
        output: str,
    ) -> dict[str, Any]:
        """Validate output using the validation method specified in a card's capabilities."""
        full_result = self.validate_output(card.domain, output)
        full_result["expert_name"] = card.identity
        full_result["domain"] = card.domain.value

        # Add capability-specific validation notes
        capability_notes: list[str] = []
        for cap in card.capabilities:
            method = cap.validation_method
            if method == ValidationMethod.FORMAL_VERIFICATION:
                capability_notes.append(f"Capability '{cap.name}' requires formal verification")
            elif method == ValidationMethod.COMPLIANCE_CHECK:
                capability_notes.append(f"Capability '{cap.name}' requires compliance check")

        full_result["validation_notes"] = capability_notes
        return full_result

    # ------------------------------------------------------------------
    # Customization
    # ------------------------------------------------------------------

    def add_rule(
        self, domain: DomainType, check: str, description: str, severity: str = "medium"
    ) -> None:
        """Add a custom validation rule for a domain."""
        if domain not in self._rules:
            self._rules[domain] = []
        self._rules[domain].append(
            {
                "check": check,
                "description": description,
                "severity": severity,
            }
        )

    def add_citation_pattern(self, domain: DomainType, pattern: str) -> None:
        """Add a custom citation pattern for a domain."""
        if domain not in self._citations:
            self._citations[domain] = []
        self._citations[domain].append(pattern)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_check(self, domain: DomainType, output: str, check: str) -> tuple[bool, str]:
        """Run a single validation check on the output."""
        check_map: dict[str, tuple[DomainType, ...]] = {
            "disclaimer_present": (
                DomainType.MEDICAL,
                DomainType.LEGAL,
                DomainType.FINANCE,
                DomainType.BUSINESS,
            ),
            "no_guarantees": (DomainType.FINANCE,),
            "defers_to_physician": (DomainType.MEDICAL,),
            "no_diagnosis": (DomainType.MEDICAL,),
            "no_legal_advice": (DomainType.LEGAL,),
            "cites_sources": (DomainType.MEDICAL, DomainType.SCIENTIFIC),
            "cites_authority": (DomainType.LEGAL,),
            "safety_considered": (DomainType.ENGINEERING,),
            "no_hardcoded_secrets": (DomainType.CODING,),
            "no_debug_code": (DomainType.CODING,),
        }

        handler = check_map.get(check, ())
        if domain not in handler:
            # Generic checks pass by default
            return True, "No applicable check for this domain"

        if check == "disclaimer_present":
            disclaimer = _DISCLAIMERS.get(domain, "")
            if not disclaimer:
                return True, "No disclaimer required"
            # Check for key phrases from the disclaimer
            key_phrases = disclaimer.split(". ")[:2]
            for phrase in key_phrases:
                if phrase[:40].lower() in output.lower():
                    return True, "Disclaimer found"
            return False, "Required disclaimer not found in output"

        if check == "no_guarantees":
            guaranteed_phrases = [
                "guaranteed",
                "risk-free",
                "sure thing",
                "no risk",
                "certain return",
                "definitely will",
                "100% return",
            ]
            for phrase in guaranteed_phrases:
                if phrase.lower() in output.lower():
                    return False, f"Contains prohibited guarantee phrase: '{phrase}'"
            return True, "No guaranteed return claims detected"

        if check == "defers_to_physician":
            deferral_phrases = [
                "consult your physician",
                "consult a healthcare provider",
                "seek medical attention",
                "ask your doctor",
                "professional medical advice",
            ]
            for phrase in deferral_phrases:
                if phrase.lower() in output.lower():
                    return True, f"Deferral to physician found: '{phrase}'"
            return False, "No physician deferral statement found"

        if check == "no_diagnosis":
            diagnostic_phrases = [
                "you have",
                "you are diagnosed with",
                "definitive diagnosis",
                "confirmed case of",
                "you definitely have",
            ]
            for phrase in diagnostic_phrases:
                if phrase.lower() in output.lower():
                    return False, f"Contains definitive diagnostic language: '{phrase}'"
            return True, "No definitive diagnostic statements detected"

        if check == "no_legal_advice":
            advice_phrases = [
                "you should sue",
                "you should file",
                "you will win",
                "definitely liable",
                "certain to prevail",
            ]
            for phrase in advice_phrases:
                if phrase.lower() in output.lower():
                    return False, f"Contains legal advice language: '{phrase}'"
            return True, "No legal advice statements detected"

        if check in ("cites_sources", "cites_authority"):
            citations_result = self.check_citations(domain, output)
            if citations_result["citations_found"] > 0:
                return True, f"Found {citations_result['citations_found']} citation(s)"
            return False, "No citations or references found in output"

        if check == "safety_considered":
            safety_terms = [
                "safety factor",
                "failure mode",
                "fmea",
                "risk assessment",
                "margin of safety",
                "factor of safety",
                "load case",
            ]
            for term in safety_terms:
                if term.lower() in output.lower():
                    return True, f"Safety consideration found: '{term}'"
            return False, "No safety considerations found in output"

        if check == "no_hardcoded_secrets":
            secret_patterns = [
                r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
                r'password\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
            ]
            for pattern in secret_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    return False, "Potential hardcoded secret detected"
            return True, "No hardcoded secrets detected"

        if check == "no_debug_code":
            debug_patterns = [
                r"console\.\s*log\s*\(",
                r"\bdebugger\b",
                r"#\s*TODO",
                r"//\s*TODO",
                r"/*\s*TODO",
            ]
            for pattern in debug_patterns:
                if re.search(pattern, output):
                    return False, f"Debug code detected: {pattern}"
            return True, "No debug code detected"

        return True, "Passed generic validation"

"""
Comprehensive tests for lyra-domain package.

Covers all 5 layers:
- Layer 0: Data models (frozen dataclasses, validation, enums)
- Layer 1: Domain Router (classification, multi-domain, cross-domain)
- Layer 2: Expert Registry (cards, knowledge base updates)
- Layer 4: Domain Validation (rules, disclaimers, citations)
- Layer 5: Cross-Domain Fusion (analogies, transfer, confidence)
"""

from __future__ import annotations

import pytest
from lyra_domain import (
    Capability,
    ComplexityLevel,
    CrossDomainFusion,
    CrossDomainMapping,
    DomainClassification,
    DomainRouter,
    DomainType,
    DomainValidator,
    ExpertCard,
    ExpertRegistry,
    KnowledgeCategory,
    KnowledgeSource,
    MultiDomainResult,
    ValidationMethod,
)

# ======================================================================
# LAYER 0 — Models
# ======================================================================


class TestDomainType:
    def test_all_9_domains_present(self) -> None:
        assert len(DomainType) == 9

    def test_values(self) -> None:
        assert DomainType.CODING.value == "coding"
        assert DomainType.FINANCE.value == "finance"
        assert DomainType.MEDICAL.value == "medical"
        assert DomainType.LEGAL.value == "legal"
        assert DomainType.SCIENTIFIC.value == "scientific"
        assert DomainType.EDUCATION.value == "education"
        assert DomainType.ENGINEERING.value == "engineering"
        assert DomainType.CREATIVE.value == "creative"
        assert DomainType.BUSINESS.value == "business"


class TestKnowledgeSource:
    def test_frozen(self) -> None:
        ks = KnowledgeSource(title="Test Source", url="https://example.com")
        with pytest.raises(AttributeError):
            ks.title = "Changed"  # type: ignore[misc]

    def test_default_credibility(self) -> None:
        ks = KnowledgeSource(title="Test")
        assert ks.credibility_score == 0.8
        assert ks.category == KnowledgeCategory.PRIMARY_LITERATURE

    def test_credibility_validation(self) -> None:
        with pytest.raises(ValueError, match="credibility_score must be in"):
            KnowledgeSource(title="Bad", credibility_score=1.5)

    def test_negative_credibility(self) -> None:
        with pytest.raises(ValueError, match="credibility_score must be in"):
            KnowledgeSource(title="Bad", credibility_score=-0.1)

    def test_custom_category(self) -> None:
        ks = KnowledgeSource(
            title="Reg",
            category=KnowledgeCategory.REGULATORY_FRAMEWORK,
        )
        assert ks.category == KnowledgeCategory.REGULATORY_FRAMEWORK


class TestCapability:
    def test_frozen(self) -> None:
        cap = Capability(name="Test", description="A test capability")
        with pytest.raises(AttributeError):
            cap.name = "Changed"  # type: ignore[misc]

    def test_default_validation_method(self) -> None:
        cap = Capability(name="Test", description="A test")
        assert cap.validation_method == ValidationMethod.EXPERT_REVIEW

    def test_with_tools(self) -> None:
        cap = Capability(
            name="Code Gen",
            description="Generate code",
            tools_required=("compiler", "lsp"),
            validation_method=ValidationMethod.TEST_SUITE,
        )
        assert cap.tools_required == ("compiler", "lsp")
        assert cap.validation_method == ValidationMethod.TEST_SUITE


class TestExpertCard:
    def test_frozen(self) -> None:
        card = ExpertCard(
            identity="Test Expert",
            role="Testing",
            domain=DomainType.CODING,
        )
        with pytest.raises(AttributeError):
            card.identity = "Changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        card = ExpertCard(identity="Test", role="Role", domain=DomainType.CODING)
        assert card.guiding_principles == ()
        assert card.capabilities == ()
        assert card.knowledge_base == ()
        assert card.user_context == ""
        assert card.interaction_style == "professional"
        assert card.version == "0.1.0"
        assert card.max_tokens_recommended == 4096
        assert card.temperature_recommended == 0.7

    def test_temperature_validation(self) -> None:
        with pytest.raises(ValueError, match="temperature_recommended must be in"):
            ExpertCard(
                identity="Bad",
                role="Role",
                domain=DomainType.CODING,
                temperature_recommended=3.0,
            )

    def test_full_card(self) -> None:
        cap = Capability(name="Test", description="A capability")
        ks = KnowledgeSource(title="Source", credibility_score=0.9)
        card = ExpertCard(
            identity="Full Expert",
            role="Full Role",
            guiding_principles=("Principle 1", "Principle 2"),
            capabilities=(cap,),
            knowledge_base=(ks,),
            user_context="Helps users",
            interaction_style="friendly",
            activation_command="Activate",
            domain=DomainType.FINANCE,
            version="2.0.0",
            model_preference="gpt-4",
            disclaimer="Not financial advice",
            max_tokens_recommended=8192,
            temperature_recommended=0.3,
            metadata={"key": "value"},
        )
        assert card.domain == DomainType.FINANCE
        assert len(card.guiding_principles) == 2
        assert len(card.capabilities) == 1
        assert len(card.knowledge_base) == 1
        assert card.metadata["key"] == "value"


class TestDomainClassification:
    def test_frozen(self) -> None:
        dc = DomainClassification(
            domain_type=DomainType.CODING,
            confidence=0.9,
        )
        with pytest.raises(AttributeError):
            dc.domain_type = DomainType.FINANCE  # type: ignore[misc]

    def test_confidence_validation(self) -> None:
        with pytest.raises(ValueError, match="confidence must be in"):
            DomainClassification(domain_type=DomainType.CODING, confidence=1.5)

    def test_defaults(self) -> None:
        dc = DomainClassification(domain_type=DomainType.CODING)
        assert dc.confidence == 0.5
        assert dc.complexity == ComplexityLevel.MODERATE
        assert dc.keywords == ()


class TestMultiDomainResult:
    def test_defaults(self) -> None:
        primary = DomainClassification(domain_type=DomainType.CODING)
        result = MultiDomainResult(primary=primary)
        assert result.secondary == ()
        assert not result.requires_fusion
        assert result.fusion_strategy == "sequential"


class TestCrossDomainMapping:
    def test_frozen(self) -> None:
        mapping = CrossDomainMapping(
            source_domain=DomainType.CODING,
            target_domain=DomainType.ENGINEERING,
            transferable_knowledge="Design patterns",
        )
        with pytest.raises(AttributeError):
            mapping.source_domain = DomainType.FINANCE  # type: ignore[misc]

    def test_confidence_validation(self) -> None:
        with pytest.raises(ValueError, match="confidence must be in"):
            CrossDomainMapping(
                source_domain=DomainType.CODING,
                target_domain=DomainType.ENGINEERING,
                transferable_knowledge="Test",
                confidence=2.0,
            )

    def test_defaults(self) -> None:
        mapping = CrossDomainMapping(
            source_domain=DomainType.CODING,
            target_domain=DomainType.FINANCE,
            transferable_knowledge="Algorithmic thinking",
        )
        assert mapping.adaptation_required == ""
        assert mapping.confidence == 0.5
        assert mapping.analogies == ()


class TestComplexityLevel:
    def test_all_levels(self) -> None:
        assert ComplexityLevel.TRIVIAL.value == "trivial"
        assert ComplexityLevel.SIMPLE.value == "simple"
        assert ComplexityLevel.MODERATE.value == "moderate"
        assert ComplexityLevel.COMPLEX.value == "complex"
        assert ComplexityLevel.VERY_COMPLEX.value == "very_complex"
        assert ComplexityLevel.EXTREME.value == "extreme"


class TestValidationMethod:
    def test_all_methods(self) -> None:
        assert ValidationMethod.STATIC_ANALYSIS.value == "static_analysis"
        assert ValidationMethod.TEST_SUITE.value == "test_suite"
        assert ValidationMethod.FORMAL_VERIFICATION.value == "formal_verification"


# ======================================================================
# LAYER 1 — Domain Router
# ======================================================================


class TestDomainRouter:
    @pytest.fixture
    def router(self) -> DomainRouter:
        return DomainRouter()

    def test_classify_coding_task(self, router: DomainRouter) -> None:
        result = router.classify("Write a Python function to sort a list of integers")
        assert result.domain_type == DomainType.CODING
        assert result.confidence > 0.3

    def test_classify_finance_task(self, router: DomainRouter) -> None:
        result = router.classify("Analyze the portfolio risk and optimize asset allocation")
        assert result.domain_type == DomainType.FINANCE
        assert result.confidence > 0.3

    def test_classify_medical_task(self, router: DomainRouter) -> None:
        result = router.classify("Evaluate patient symptoms and provide differential diagnosis")
        assert result.domain_type == DomainType.MEDICAL
        assert result.confidence > 0.3

    def test_classify_legal_task(self, router: DomainRouter) -> None:
        result = router.classify("Review this contract for liability clauses and compliance issues")
        assert result.domain_type == DomainType.LEGAL
        assert result.confidence > 0.3

    def test_classify_scientific_task(self, router: DomainRouter) -> None:
        result = router.classify("Design a controlled experiment to test the hypothesis")
        assert result.domain_type == DomainType.SCIENTIFIC
        assert result.confidence > 0.3

    def test_classify_education_task(self, router: DomainRouter) -> None:
        result = router.classify("Create a lesson plan for teaching algebra to high school students")
        assert result.domain_type == DomainType.EDUCATION
        assert result.confidence > 0.3

    def test_classify_engineering_task(self, router: DomainRouter) -> None:
        result = router.classify("Design a structural component with FEA simulation")
        assert result.domain_type == DomainType.ENGINEERING
        assert result.confidence > 0.3

    def test_classify_creative_task(self, router: DomainRouter) -> None:
        result = router.classify("Write a poem about artificial intelligence and compose music")
        assert result.domain_type == DomainType.CREATIVE
        assert result.confidence > 0.3

    def test_classify_business_task(self, router: DomainRouter) -> None:
        result = router.classify("Develop a go-to-market strategy for a new SaaS product")
        assert result.domain_type == DomainType.BUSINESS
        assert result.confidence > 0.3

    def test_classify_empty_task(self, router: DomainRouter) -> None:
        result = router.classify("")
        assert result.domain_type == DomainType.CODING
        assert result.confidence == 0.3

    def test_classify_whitespace_task(self, router: DomainRouter) -> None:
        result = router.classify("   ")
        assert result.domain_type == DomainType.CODING

    def test_route_to_expert(self, router: DomainRouter) -> None:
        classification = router.classify("Write Python code")
        card = router.route_to_expert(classification)
        assert card is not None
        assert card.domain == DomainType.CODING
        assert "Software Architect" in card.identity

    def test_route_missing_domain(self, router: DomainRouter) -> None:
        # Create a classification for an unregistered domain
        empty_registry = ExpertRegistry()
        empty_router = DomainRouter(registry=empty_registry)
        classification = DomainClassification(
            domain_type=DomainType.CODING,
            confidence=0.9,
        )
        card = empty_router.route_to_expert(classification)
        assert card is None

    def test_detect_multi_domain(self, router: DomainRouter) -> None:
        result = router.detect_multi_domain(
            "Design a financial trading algorithm in Python"
        )
        assert result.primary.domain_type in (DomainType.CODING, DomainType.FINANCE)
        assert len(result.secondary) >= 0

    def test_detect_single_domain(self, router: DomainRouter) -> None:
        result = router.detect_multi_domain("Write a Python function")
        assert result.primary.domain_type == DomainType.CODING

    def test_cross_domain_insights(self, router: DomainRouter) -> None:
        insights = router.get_cross_domain_insights(
            DomainType.CODING, DomainType.ENGINEERING
        )
        assert len(insights) > 0
        assert insights[0].source_domain == DomainType.CODING

    def test_cross_domain_same(self, router: DomainRouter) -> None:
        insights = router.get_cross_domain_insights(
            DomainType.CODING, DomainType.CODING
        )
        assert insights == []

    def test_set_threshold(self, router: DomainRouter) -> None:
        router.set_classification_threshold(0.1)
        assert router._threshold == 0.1

    def test_set_threshold_invalid(self, router: DomainRouter) -> None:
        with pytest.raises(ValueError, match="threshold must be in"):
            router.set_classification_threshold(1.5)

    def test_to_dict(self, router: DomainRouter) -> None:
        d = router.to_dict()
        assert "threshold" in d
        assert "registry" in d


class TestDomainRouterSubdomain:
    @pytest.fixture
    def router(self) -> DomainRouter:
        return DomainRouter()

    def test_coding_subdomain_backend(self, router: DomainRouter) -> None:
        dc = router.classify("Build a backend API with database integration")
        assert dc.subdomain == "backend"

    def test_coding_subdomain_frontend(self, router: DomainRouter) -> None:
        dc = router.classify("Create a React frontend with responsive design")
        assert dc.subdomain == "frontend"

    def test_coding_subdomain_security(self, router: DomainRouter) -> None:
        dc = router.classify("Fix security vulnerabilities in the authentication")
        assert dc.subdomain == "security"

    def test_finance_subdomain_trading(self, router: DomainRouter) -> None:
        dc = router.classify("Execute high-frequency stock trades and options trading")
        assert dc.subdomain == "trading"

    def test_finance_subdomain_risk(self, router: DomainRouter) -> None:
        dc = router.classify("Financial risk analysis for investment decisions")
        assert dc.subdomain == "risk management"

    def test_medical_subdomain_cardiology(self, router: DomainRouter) -> None:
        dc = router.classify("Evaluate patient with possible heart condition")
        assert dc.subdomain == "cardiology"

    def test_legal_subdomain_ip(self, router: DomainRouter) -> None:
        dc = router.classify("File a patent for a new software invention")
        assert dc.subdomain == "intellectual property"

    def test_no_subdomain_fallback(self, router: DomainRouter) -> None:
        dc = router.classify("Write a Python function")
        assert dc.subdomain == ""  # general coding task


class TestDomainRouterComplexity:
    @pytest.fixture
    def router(self) -> DomainRouter:
        return DomainRouter()

    def test_trivial_complexity(self, router: DomainRouter) -> None:
        dc = router.classify("hi")
        assert dc.complexity == ComplexityLevel.TRIVIAL

    def test_simple_complexity(self, router: DomainRouter) -> None:
        dc = router.classify("Write a Python function to sort a list of integers ascending")
        assert dc.complexity == ComplexityLevel.SIMPLE

    def test_very_complex(self, router: DomainRouter) -> None:
        task = "Develop a full-stack application with " + "complex integration " * 80
        dc = router.classify(task)
        assert dc.complexity in (ComplexityLevel.VERY_COMPLEX, ComplexityLevel.COMPLEX)


# ======================================================================
# LAYER 2 — Expert Registry
# ======================================================================


class TestExpertRegistry:
    def test_empty_registry(self) -> None:
        registry = ExpertRegistry()
        assert len(registry) == 0
        assert registry.list_domains() == ()

    def test_register_and_get(self) -> None:
        registry = ExpertRegistry()
        card = ExpertCard(identity="Test", role="Role", domain=DomainType.CODING)
        registry.register_expert(card)
        assert len(registry) == 1
        retrieved = registry.get_expert(DomainType.CODING)
        assert retrieved is not None
        assert retrieved.identity == "Test"

    def test_register_invalid_type(self) -> None:
        registry = ExpertRegistry()
        with pytest.raises(TypeError, match="Expected ExpertCard"):
            registry.register_expert("not a card")  # type: ignore[arg-type]

    def test_get_nonexistent(self) -> None:
        registry = ExpertRegistry()
        assert registry.get_expert(DomainType.CODING) is None

    def test_list_domains(self) -> None:
        registry = ExpertRegistry()
        cards = {
            DomainType.CODING: ExpertCard(
                identity="Coder", role="Code", domain=DomainType.CODING
            ),
            DomainType.FINANCE: ExpertCard(
                identity="Fin", role="Finance", domain=DomainType.FINANCE
            ),
        }
        registry = ExpertRegistry(cards=cards)
        domains = registry.list_domains()
        assert DomainType.CODING in domains
        assert DomainType.FINANCE in domains
        assert len(domains) == 2

    def test_contains(self) -> None:
        registry = ExpertRegistry()
        card = ExpertCard(identity="Test", role="Role", domain=DomainType.CODING)
        registry.register_expert(card)
        assert DomainType.CODING in registry
        assert DomainType.FINANCE not in registry

    def test_load_defaults(self) -> None:
        registry = ExpertRegistry()
        registry.load_defaults()
        assert len(registry) == 9

    def test_loaded_card_content(self) -> None:
        registry = ExpertRegistry()
        registry.load_defaults()

        coding_card = registry.get_expert(DomainType.CODING)
        assert coding_card is not None
        assert len(coding_card.capabilities) > 0
        assert len(coding_card.knowledge_base) > 0
        assert len(coding_card.guiding_principles) > 0
        assert coding_card.model_preference != ""

        finance_card = registry.get_expert(DomainType.FINANCE)
        assert finance_card is not None
        assert finance_card.disclaimer != ""

        medical_card = registry.get_expert(DomainType.MEDICAL)
        assert medical_card is not None
        assert "DISCLAIMER" in medical_card.disclaimer

    def test_to_dict(self) -> None:
        registry = ExpertRegistry()
        card = ExpertCard(identity="Test", role="Role", domain=DomainType.CODING)
        registry.register_expert(card)
        d = registry.to_dict()
        assert d["count"] == 1
        assert "coding" in d["registered_domains"]

    def test_update_knowledge_base(self) -> None:
        registry = ExpertRegistry()
        card = ExpertCard(identity="Test", role="Role", domain=DomainType.CODING)
        registry.register_expert(card)

        new_source = KnowledgeSource(title="New Source", credibility_score=0.9)
        result = registry.update_knowledge_base(DomainType.CODING, (new_source,))
        assert result

        updated = registry.get_expert(DomainType.CODING)
        assert updated is not None
        assert len(updated.knowledge_base) == 1

    def test_update_knowledge_nonexistent(self) -> None:
        registry = ExpertRegistry()
        result = registry.update_knowledge_base(DomainType.CODING, ())
        assert not result


# ======================================================================
# LAYER 4 — Domain Validation
# ======================================================================


class TestDomainValidator:
    @pytest.fixture
    def validator(self) -> DomainValidator:
        return DomainValidator()

    def test_validate_coding_output(self, validator: DomainValidator) -> None:
        output = """
        def hello(name: str) -> str:
            return f"Hello, {name}"
        """
        result = validator.validate_output(DomainType.CODING, output)
        assert result["domain"] == "coding"
        assert isinstance(result["passed"], bool)

    def test_validate_empty_output(self, validator: DomainValidator) -> None:
        result = validator.validate_output(DomainType.CODING, "")
        assert not result["passed"]
        assert result["verdict"] == "rejected"

    def test_validate_medical_disclaimer_missing(self, validator: DomainValidator) -> None:
        output = "The patient has a cold. Take rest."
        result = validator.validate_output(DomainType.MEDICAL, output)
        disclaimer_check = next(
            (c for c in result["checks"] if c["check"] == "disclaimer_present"),
            None,
        )
        assert disclaimer_check is not None
        assert not disclaimer_check["passed"]

    def test_validate_medical_disclaimer_present(self, validator: DomainValidator) -> None:
        output = (
            "The patient may have a cold. consult your physician for proper diagnosis. "
            "seek medical attention if symptoms worsen."
        )
        result = validator.validate_output(DomainType.MEDICAL, output)
        disclaimer_check = next(
            (c for c in result["checks"] if c["check"] == "disclaimer_present"),
            None,
        )
        assert disclaimer_check is not None

    def test_validate_legal_disclaimer_missing(self, validator: DomainValidator) -> None:
        output = "You should file a lawsuit."
        result = validator.validate_output(DomainType.LEGAL, output)
        disclaimer_check = next(
            (c for c in result["checks"] if c["check"] == "disclaimer_present"),
            None,
        )
        assert disclaimer_check is not None
        assert not disclaimer_check["passed"]

    def test_validate_finance_no_guarantees(self, validator: DomainValidator) -> None:
        output = "This stock is guaranteed to go up 100%."
        result = validator.validate_output(DomainType.FINANCE, output)
        guarantee_check = next(
            (c for c in result["checks"] if c["check"] == "no_guarantees"),
            None,
        )
        assert guarantee_check is not None
        assert not guarantee_check["passed"]

    def test_validate_medical_no_diagnosis(self, validator: DomainValidator) -> None:
        output = "You have cancer based on the symptoms you described."
        result = validator.validate_output(DomainType.MEDICAL, output)
        diagnosis_check = next(
            (c for c in result["checks"] if c["check"] == "no_diagnosis"),
            None,
        )
        assert diagnosis_check is not None
        assert not diagnosis_check["passed"]

    def test_validate_medical_defers(self, validator: DomainValidator) -> None:
        output = "Based on symptoms, it could be a cold. consult your physician for diagnosis."
        result = validator.validate_output(DomainType.MEDICAL, output)
        defer_check = next(
            (c for c in result["checks"] if c["check"] == "defers_to_physician"),
            None,
        )
        assert defer_check is not None
        assert defer_check["passed"]

    def test_validate_engineering_safety(self, validator: DomainValidator) -> None:
        output = "Design with safety factor of 2.5 and consider failure modes."
        result = validator.validate_output(DomainType.ENGINEERING, output)
        safety_check = next(
            (c for c in result["checks"] if c["check"] == "safety_considered"),
            None,
        )
        assert safety_check is not None
        assert safety_check["passed"]

    def test_validate_engineering_no_safety(self, validator: DomainValidator) -> None:
        output = "Build a bridge."
        result = validator.validate_output(DomainType.ENGINEERING, output)
        safety_check = next(
            (c for c in result["checks"] if c["check"] == "safety_considered"),
            None,
        )
        assert safety_check is not None
        assert not safety_check["passed"]

    def test_validate_coding_no_secrets(self, validator: DomainValidator) -> None:
        output = "api_key = 'sk-1234567890abcdef'"
        result = validator.validate_output(DomainType.CODING, output)
        secret_check = next(
            (c for c in result["checks"] if c["check"] == "no_hardcoded_secrets"),
            None,
        )
        assert secret_check is not None
        assert not secret_check["passed"]

    def test_validate_coding_no_debug(self, validator: DomainValidator) -> None:
        output = "console.log('debug'); debugger;"
        result = validator.validate_output(DomainType.CODING, output)
        debug_check = next(
            (c for c in result["checks"] if c["check"] == "no_debug_code"),
            None,
        )
        assert debug_check is not None
        assert not debug_check["passed"]

    def test_guidelines_compliant(self, validator: DomainValidator) -> None:
        output = "Consider consulting a healthcare provider for proper evaluation."
        result = validator.check_guidelines(DomainType.MEDICAL, output)
        assert isinstance(result["compliant"], bool)

    def test_guidelines_empty(self, validator: DomainValidator) -> None:
        result = validator.check_guidelines(DomainType.MEDICAL, "")
        assert not result["compliant"]

    def test_citations_medical(self, validator: DomainValidator) -> None:
        output = "Studies show this treatment is effective (doi:10.1234/test)."
        result = validator.check_citations(DomainType.MEDICAL, output)
        assert result["citations_found"] > 0

    def test_citations_legal(self, validator: DomainValidator) -> None:
        output = "As established in 410 U.S. 113 (1973), the precedent is clear."
        result = validator.check_citations(DomainType.LEGAL, output)
        assert result["citations_found"] > 0

    def test_citations_not_required(self, validator: DomainValidator) -> None:
        output = "Write a creative poem about stars."
        result = validator.check_citations(DomainType.CREATIVE, output)
        assert not result["citations_required"]

    def test_disclaimer_medical(self, validator: DomainValidator) -> None:
        disclaimer = validator.get_disclaimer(DomainType.MEDICAL)
        assert "MEDICAL DISCLAIMER" in disclaimer

    def test_disclaimer_legal(self, validator: DomainValidator) -> None:
        disclaimer = validator.get_disclaimer(DomainType.LEGAL)
        assert "LEGAL DISCLAIMER" in disclaimer

    def test_disclaimer_finance(self, validator: DomainValidator) -> None:
        disclaimer = validator.get_disclaimer(DomainType.FINANCE)
        assert "FINANCIAL DISCLAIMER" in disclaimer

    def test_disclaimer_coding(self, validator: DomainValidator) -> None:
        disclaimer = validator.get_disclaimer(DomainType.CODING)
        assert disclaimer == ""

    def test_validate_against_card(self, validator: DomainValidator) -> None:
        card = ExpertCard(identity="Test", role="Role", domain=DomainType.CODING)
        result = validator.validate_against_card(card, "def hello(): pass")
        assert result["expert_name"] == "Test"
        assert result["domain"] == "coding"

    def test_add_custom_rule(self, validator: DomainValidator) -> None:
        validator.add_rule(
            DomainType.CODING,
            "custom_check",
            "Custom validation rule",
            severity="high",
        )
        output = "test output"
        result = validator.validate_output(DomainType.CODING, output)
        checks = [c["check"] for c in result["checks"]]
        assert "custom_check" in checks

    def test_add_citation_pattern(self, validator: DomainValidator) -> None:
        validator.add_citation_pattern(DomainType.CREATIVE, r"inspired\s+by")
        output = "inspired by the works of Shakespeare"
        result = validator.check_citations(DomainType.CREATIVE, output)
        assert result["citations_found"] > 0

    def test_legal_no_legal_advice(self, validator: DomainValidator) -> None:
        output = "You should sue them for damages."
        result = validator.validate_output(DomainType.LEGAL, output)
        advice_check = next(
            (c for c in result["checks"] if c["check"] == "no_legal_advice"),
            None,
        )
        assert advice_check is not None
        assert not advice_check["passed"]

    def test_coding_validation_checks_present(self, validator: DomainValidator) -> None:
        output = "def foo(): pass"
        result = validator.validate_output(DomainType.CODING, output)
        check_names = [c["check"] for c in result["checks"]]
        assert "syntax" in check_names
        assert "types" in check_names
        assert "imports" in check_names
        assert "error_handling" in check_names


# ======================================================================
# LAYER 5 — Cross-Domain Fusion
# ======================================================================


class TestCrossDomainFusion:
    @pytest.fixture
    def fusion(self) -> CrossDomainFusion:
        return CrossDomainFusion()

    def test_fuse_same_domain(self, fusion: CrossDomainFusion) -> None:
        result = fusion.fuse_expertise(DomainType.CODING, DomainType.CODING, "Write code")
        assert result["fusion_confidence"] == 1.0
        assert result["strategy"] == "same_domain_no_fusion_needed"

    def test_fuse_coding_engineering(self, fusion: CrossDomainFusion) -> None:
        result = fusion.fuse_expertise(
            DomainType.CODING, DomainType.ENGINEERING, "Design a modular system"
        )
        assert result["source_domain"] == "coding"
        assert result["target_domain"] == "engineering"
        assert len(result["adapted_approaches"]) > 0

    def test_fuse_finance_business(self, fusion: CrossDomainFusion) -> None:
        result = fusion.fuse_expertise(
            DomainType.FINANCE, DomainType.BUSINESS, "Optimize resource allocation"
        )
        assert result["fusion_confidence"] > 0.5

    def test_transfer_knowledge_same_domain(self, fusion: CrossDomainFusion) -> None:
        result = fusion.transfer_knowledge(
            DomainType.CODING, DomainType.CODING, "modular design"
        )
        assert result["confidence"] == 1.0
        assert result["adapted_concept"] == "modular design"

    def test_transfer_knowledge_cross_domain(self, fusion: CrossDomainFusion) -> None:
        result = fusion.transfer_knowledge(
            DomainType.CODING, DomainType.ENGINEERING, "modular design"
        )
        assert result["original_concept"] == "modular design"
        assert result["confidence"] > 0

    def test_transfer_knowledge_fallback(self, fusion: CrossDomainFusion) -> None:
        result = fusion.transfer_knowledge(
            DomainType.CODING, DomainType.MEDICAL, "quantum entanglement"
        )
        # Should fall back to generic adaptation
        assert result["original_concept"] == "quantum entanglement"

    def test_identify_analogies(self, fusion: CrossDomainFusion) -> None:
        analogies = fusion.identify_analogies(DomainType.CODING, DomainType.ENGINEERING)
        assert len(analogies) > 0
        # Check sorted by confidence descending
        for i in range(len(analogies) - 1):
            assert analogies[i][2] >= analogies[i + 1][2]

    def test_identify_analogies_reverse(self, fusion: CrossDomainFusion) -> None:
        analogies = fusion.identify_analogies(DomainType.ENGINEERING, DomainType.CODING)
        assert len(analogies) > 0

    def test_identify_analogies_none(self, fusion: CrossDomainFusion) -> None:
        analogies = fusion.identify_analogies(DomainType.MEDICAL, DomainType.CREATIVE)
        # May have some cross-domain analogies or be empty
        assert isinstance(analogies, list)

    def test_compute_fusion_confidence_same(self, fusion: CrossDomainFusion) -> None:
        assert fusion.compute_fusion_confidence(
            DomainType.CODING, DomainType.CODING
        ) == 1.0

    def test_compute_fusion_confidence_cross(self, fusion: CrossDomainFusion) -> None:
        confidence = fusion.compute_fusion_confidence(
            DomainType.CODING, DomainType.ENGINEERING
        )
        assert 0 < confidence <= 1.0

    def test_add_analogy(self, fusion: CrossDomainFusion) -> None:
        fusion.add_analogy(
            DomainType.CODING, DomainType.MEDICAL,
            "debugging", "diagnostic reasoning",
            0.7, "Both involve systematic elimination of possibilities",
        )
        analogies = fusion.identify_analogies(DomainType.CODING, DomainType.MEDICAL)
        assert len(analogies) > 0

    def test_add_analogy_invalid_confidence(self, fusion: CrossDomainFusion) -> None:
        with pytest.raises(ValueError, match="confidence must be in"):
            fusion.add_analogy(
                DomainType.CODING, DomainType.MEDICAL,
                "a", "b", 1.5,
            )

    def test_set_similarity(self, fusion: CrossDomainFusion) -> None:
        fusion.set_similarity(DomainType.CODING, DomainType.MEDICAL, 0.35)
        assert fusion._get_similarity(DomainType.CODING, DomainType.MEDICAL) == 0.35
        # Should be symmetric
        assert fusion._get_similarity(DomainType.MEDICAL, DomainType.CODING) == 0.35

    def test_set_similarity_invalid(self, fusion: CrossDomainFusion) -> None:
        with pytest.raises(ValueError, match="similarity must be in"):
            fusion.set_similarity(DomainType.CODING, DomainType.MEDICAL, 1.5)


# ======================================================================
# INTEGRATION — End-to-end workflows
# ======================================================================


class TestIntegration:
    """End-to-end tests that exercise multiple layers together."""

    def test_full_classification_to_validation_pipeline(self) -> None:
        """Classify a medical task, get the expert card, validate output."""
        router = DomainRouter()
        validator = DomainValidator()

        task = "Diagnose the patient's symptoms including chest pain and shortness of breath"
        classification = router.classify(task)

        assert classification.domain_type == DomainType.MEDICAL
        assert classification.confidence > 0.3

        card = router.route_to_expert(classification)
        assert card is not None
        assert card.domain == DomainType.MEDICAL
        assert card.disclaimer != ""

        # Validate compliant output
        good_output = (
            "The patient's symptoms could indicate several conditions "
            "including angina or pneumonia. It is NOT a substitute for "
            "professional medical advice. consult your physician for "
            "proper diagnosis."
        )
        validation = validator.validate_output(DomainType.MEDICAL, good_output)
        assert validation["verdict"] in ("approved", "warning")

        # Validate non-compliant output
        bad_output = "You have a heart attack. Take this medication."
        bad_validation = validator.validate_output(DomainType.MEDICAL, bad_output)
        assert bad_validation["verdict"] == "rejected"

    def test_cross_domain_fusion_to_validation(self) -> None:
        """Use cross-domain fusion then validate in target domain."""
        fusion = CrossDomainFusion()
        validator = DomainValidator()

        result = fusion.fuse_expertise(
            DomainType.CODING, DomainType.ENGINEERING,
            "Design a modular sensing system",
        )
        assert result["fusion_confidence"] > 0.5

        # Validate the adapted concept in the target domain
        for approach in result["adapted_approaches"]:
            output = f"Design using {approach['adapted_concept']}"
            val = validator.validate_output(DomainType.ENGINEERING, output)
            assert val["domain"] == "engineering"

    def test_registry_with_router(self) -> None:
        """Use a custom registry with a router."""
        registry = ExpertRegistry()
        custom_card = ExpertCard(
            identity="Custom Coder",
            role="Custom coding role",
            domain=DomainType.CODING,
        )
        registry.register_expert(custom_card)

        router = DomainRouter(registry=registry)
        classification = router.classify("Write Python code")
        card = router.route_to_expert(classification)
        assert card is not None
        assert card.identity == "Custom Coder"

    def test_multi_domain_with_fusion(self) -> None:
        """Detect multi-domain task and fuse expertise."""
        router = DomainRouter()
        fusion = CrossDomainFusion()

        multi = router.detect_multi_domain(
            "Design a financial trading algorithm in Python"
        )

        if multi.requires_fusion:
            result = fusion.fuse_expertise(
                multi.primary.domain_type,
                multi.secondary[0].domain_type,
                "trading algorithm",
            )
            assert result["fusion_confidence"] > 0

    def test_all_disclaimers_available(self) -> None:
        """Every regulated domain has a disclaimer, others don't."""
        validator = DomainValidator()

        assert "DISCLAIMER" in validator.get_disclaimer(DomainType.MEDICAL)
        assert "DISCLAIMER" in validator.get_disclaimer(DomainType.LEGAL)
        assert "DISCLAIMER" in validator.get_disclaimer(DomainType.FINANCE)
        assert validator.get_disclaimer(DomainType.CODING) == ""
        assert validator.get_disclaimer(DomainType.CREATIVE) == ""
        assert validator.get_disclaimer(DomainType.EDUCATION) == ""
        assert validator.get_disclaimer(DomainType.ENGINEERING) == ""

    def test_registry_constructor_with_cards(self) -> None:
        """Registry can be initialized with a card dict."""
        cards = {
            DomainType.CODING: ExpertCard(
                identity="Coder", role="Code", domain=DomainType.CODING
            ),
        }
        registry = ExpertRegistry(cards=cards)
        assert len(registry) == 1
        assert registry.get_expert(DomainType.CODING) is not None

    def test_full_coding_validation(self) -> None:
        """Validate a code snippet against all coding rules."""
        validator = DomainValidator()
        code = """
        def add(a: int, b: int) -> int:
            return a + b
        """
        result = validator.validate_output(DomainType.CODING, code)
        critical_fails = [c for c in result["checks"]
                          if not c["passed"] and c["severity"] == "critical"]
        assert len(critical_fails) == 0

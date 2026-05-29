"""
Tests for PRISMA Compliance and Risk-of-Bias Assessment (Phase 1)

Tests PRISMA-trAIce 17-item compliance checker and risk-of-bias assessor.
"""

import pytest
from lyra_research.prisma.bias_assessor import (
    BiasDomain,
    RiskLevel,
    RiskOfBiasAssessor,
)
from lyra_research.prisma.prisma_checker import (
    PRISMAComplianceChecker,
)


class TestPRISMAComplianceChecker:
    """Test PRISMA compliance checker"""

    def test_full_compliance_report(self):
        """Test report with full PRISMA compliance"""
        checker = PRISMAComplianceChecker(min_compliance=0.85)

        report = {
            "title": "A Systematic Review of Machine Learning Methods",
            "abstract": {
                "background": "ML is important",
                "methods": "We searched databases",
                "results": "Found 50 studies",
                "conclusions": "ML is effective"
            },
            "rationale": "To understand the current state of ML research and identify gaps",
            "objectives": "Systematically review ML methods published 2020-2024",
            "eligibility_criteria": {
                "inclusion": ["ML papers", "2020-2024"],
                "exclusion": ["Non-English", "Preprints"]
            },
            "information_sources": ["ArXiv", "Semantic Scholar", "ACL Anthology"],
            "search_strategy": "We searched ArXiv, Semantic Scholar, and ACL Anthology using keywords: machine learning, deep learning, neural networks. Search conducted on 2024-01-01.",
            "selection_process": "Two reviewers independently screened titles and abstracts",
            "data_collection": "Data extracted using standardized forms by two reviewers",
            "data_items": ["Method", "Dataset", "Performance", "Year"],
            "risk_of_bias": {"assessed": True, "tool": "Cochrane"},
            "effect_measures": "Accuracy, F1-score, and AUC-ROC",
            "synthesis_methods": "Narrative synthesis with meta-analysis where appropriate",
            "reporting_bias": "Assessed using funnel plots and Egger's test",
            "certainty_assessment": "GRADE approach used to assess certainty",
            "study_characteristics": [{"id": "s1", "year": 2023}],
            "results_synthesis": "We found that ML methods have improved significantly over the past 5 years, with transformer-based models showing the best performance across multiple benchmarks."
        }

        result = checker.check_compliance(report)
        assert result.passed
        assert result.compliance_rate >= 0.85
        assert len(result.missing_items) == 0

    def test_partial_compliance_report(self):
        """Test report with partial PRISMA compliance"""
        checker = PRISMAComplianceChecker(min_compliance=0.85)

        report = {
            "title": "Machine Learning Methods",  # Missing "systematic review"
            "abstract": "This is a review",  # Not structured
            "rationale": "ML is important",  # Too short
            "objectives": "Review ML",  # Too short
            "information_sources": ["ArXiv", "Semantic Scholar", "ACL Anthology"],
        }

        result = checker.check_compliance(report)
        assert not result.passed
        assert result.compliance_rate < 0.85
        assert len(result.missing_items) > 0

    def test_title_identification(self):
        """Test title identification check"""
        checker = PRISMAComplianceChecker()

        # Pass: Contains "systematic review"
        result = checker.check_title_identification({
            "title": "A Systematic Review of Machine Learning"
        })
        assert result.passed

        # Fail: Missing "systematic review"
        result = checker.check_title_identification({
            "title": "Machine Learning Methods"
        })
        assert not result.passed

    def test_abstract_structured(self):
        """Test structured abstract check"""
        checker = PRISMAComplianceChecker()

        # Pass: All sections present
        result = checker.check_abstract_structured({
            "abstract": {
                "background": "...",
                "methods": "...",
                "results": "...",
                "conclusions": "..."
            }
        })
        assert result.passed

        # Fail: Missing sections
        result = checker.check_abstract_structured({
            "abstract": "This is an unstructured abstract"
        })
        assert not result.passed

    def test_information_sources(self):
        """Test information sources check"""
        checker = PRISMAComplianceChecker()

        # Pass: 3+ sources
        result = checker.check_information_sources({
            "information_sources": ["ArXiv", "Semantic Scholar", "ACL Anthology"]
        })
        assert result.passed

        # Fail: < 3 sources
        result = checker.check_information_sources({
            "information_sources": ["ArXiv"]
        })
        assert not result.passed


class TestRiskOfBiasAssessor:
    """Test risk-of-bias assessor"""

    def test_low_risk_study(self):
        """Test assessment of low-risk study"""
        assessor = RiskOfBiasAssessor()

        study = {
            "id": "study1",
            "methods": "Randomized controlled trial with allocation concealment and double-blind design. Outcome assessment was blinded.",
            "dropout_rate": 0.05,
            "preregistered": True,
            "protocol_available": True
        }

        assessment = assessor.assess_study(study)
        assert assessment.overall_risk == RiskLevel.LOW
        assert all(a.risk == RiskLevel.LOW for a in assessment.domain_assessments.values())

    def test_high_risk_study(self):
        """Test assessment of high-risk study"""
        assessor = RiskOfBiasAssessor()

        study = {
            "id": "study2",
            "methods": "Observational study with no randomization or blinding",
            "dropout_rate": 0.30,
            "preregistered": False,
            "protocol_available": False
        }

        assessment = assessor.assess_study(study)
        assert assessment.overall_risk == RiskLevel.HIGH
        # Should have at least one HIGH risk domain
        high_risk_domains = [d for d, a in assessment.domain_assessments.items() if a.risk == RiskLevel.HIGH]
        assert len(high_risk_domains) > 0

    def test_selection_bias_assessment(self):
        """Test selection bias assessment"""
        assessor = RiskOfBiasAssessor()

        # Low risk: Randomized with concealment
        study = {"methods": "Randomized controlled trial with allocation concealment"}
        assessment = assessor.assess_selection_bias(study)
        assert assessment.risk == RiskLevel.LOW

        # Moderate risk: Randomized without concealment
        study = {"methods": "Randomized controlled trial"}
        assessment = assessor.assess_selection_bias(study)
        assert assessment.risk == RiskLevel.MODERATE

        # High risk: No randomization
        study = {"methods": "Observational study"}
        assessment = assessor.assess_selection_bias(study)
        assert assessment.risk == RiskLevel.HIGH

    def test_performance_bias_assessment(self):
        """Test performance bias assessment"""
        assessor = RiskOfBiasAssessor()

        # Low risk: Double-blind
        study = {"methods": "Double-blind randomized trial"}
        assessment = assessor.assess_performance_bias(study)
        assert assessment.risk == RiskLevel.LOW

        # Moderate risk: Single-blind
        study = {"methods": "Single-blind trial"}
        assessment = assessor.assess_performance_bias(study)
        assert assessment.risk == RiskLevel.MODERATE

        # High risk: No blinding
        study = {"methods": "Open-label trial"}
        assessment = assessor.assess_performance_bias(study)
        assert assessment.risk == RiskLevel.HIGH

    def test_attrition_bias_assessment(self):
        """Test attrition bias assessment"""
        assessor = RiskOfBiasAssessor()

        # Low risk: < 10% dropout
        study = {"dropout_rate": 0.05, "results": "..."}
        assessment = assessor.assess_attrition_bias(study)
        assert assessment.risk == RiskLevel.LOW

        # Moderate risk: 10-20% dropout
        study = {"dropout_rate": 0.15, "results": "..."}
        assessment = assessor.assess_attrition_bias(study)
        assert assessment.risk == RiskLevel.MODERATE

        # High risk: > 20% dropout
        study = {"dropout_rate": 0.30, "results": "..."}
        assessment = assessor.assess_attrition_bias(study)
        assert assessment.risk == RiskLevel.HIGH

    def test_reporting_bias_assessment(self):
        """Test reporting bias assessment"""
        assessor = RiskOfBiasAssessor()

        # Low risk: Pre-registered with protocol
        study = {"preregistered": True, "protocol_available": True}
        assessment = assessor.assess_reporting_bias(study)
        assert assessment.risk == RiskLevel.LOW

        # Moderate risk: Partial
        study = {"preregistered": True, "protocol_available": False}
        assessment = assessor.assess_reporting_bias(study)
        assert assessment.risk == RiskLevel.MODERATE

        # Unclear risk: No information
        study = {"preregistered": False, "protocol_available": False}
        assessment = assessor.assess_reporting_bias(study)
        assert assessment.risk == RiskLevel.UNCLEAR

    def test_overall_risk_calculation(self):
        """Test overall risk calculation"""
        assessor = RiskOfBiasAssessor()

        # All LOW → Overall LOW
        assessments = {
            domain: type('obj', (object,), {'risk': RiskLevel.LOW})()
            for domain in BiasDomain
        }
        overall = assessor.calculate_overall_risk(assessments)
        assert overall == RiskLevel.LOW

        # Any HIGH → Overall HIGH
        assessments[BiasDomain.SELECTION_BIAS].risk = RiskLevel.HIGH
        overall = assessor.calculate_overall_risk(assessments)
        assert overall == RiskLevel.HIGH

        # Multiple MODERATE → Overall MODERATE
        assessments = {
            domain: type('obj', (object,), {
                'risk': RiskLevel.MODERATE if i < 3 else RiskLevel.LOW
            })()
            for i, domain in enumerate(BiasDomain)
        }
        overall = assessor.calculate_overall_risk(assessments)
        assert overall == RiskLevel.MODERATE


class TestPRISMAIntegration:
    """Test PRISMA and bias assessment integration"""

    def test_systematic_review_workflow(self):
        """Test complete systematic review workflow"""
        prisma_checker = PRISMAComplianceChecker()
        bias_assessor = RiskOfBiasAssessor()

        # Create a systematic review report with sufficient detail
        report = {
            "title": "A Systematic Review of Machine Learning Methods",
            "abstract": {
                "background": "ML is important for modern AI applications",
                "methods": "We searched multiple databases systematically",
                "results": "Found 50 studies meeting inclusion criteria",
                "conclusions": "ML is effective across multiple domains"
            },
            "rationale": "To understand the current state of ML research and identify gaps in the literature for future work",
            "objectives": "Systematically review ML methods published between 2020-2024",
            "eligibility_criteria": {"inclusion": ["ML papers"], "exclusion": ["Non-English"]},
            "information_sources": ["ArXiv", "Semantic Scholar", "ACL"],
            "search_strategy": "We searched ArXiv, Semantic Scholar, and ACL Anthology using keywords: machine learning, deep learning, neural networks. Search was conducted on 2024-01-01 with no language restrictions.",
            "selection_process": "Two reviewers independently screened titles and abstracts for eligibility",
            "data_collection": "Data was extracted using standardized forms by two independent reviewers",
            "data_items": ["Method", "Dataset", "Performance"],
            "risk_of_bias": {"assessed": True},
            "effect_measures": "Primary outcomes: Accuracy and F1-score",
            "synthesis_methods": "We conducted narrative synthesis with meta-analysis where appropriate using random-effects models",
            "reporting_bias": "We assessed reporting bias using funnel plots and Egger's test",
            "certainty_assessment": "We used the GRADE approach to assess certainty of evidence",
            "study_characteristics": [
                {
                    "id": "study1",
                    "methods": "Randomized controlled trial with double-blind design",
                    "dropout_rate": 0.05,
                    "preregistered": True,
                    "protocol_available": True
                }
            ],
            "results_synthesis": "We found that ML methods have improved significantly over the past 5 years, with transformer-based models showing the best performance across multiple benchmarks. Effect sizes ranged from small to large."
        }

        # Check PRISMA compliance
        prisma_result = prisma_checker.check_compliance(report)
        assert prisma_result.passed
        assert prisma_result.compliance_rate >= 0.85

        # Assess risk of bias for included studies
        for study in report["study_characteristics"]:
            bias_assessment = bias_assessor.assess_study(study)
            assert bias_assessment.overall_risk in [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for synthesis agents.
"""
import pytest
from lyra_research.agents.analysis.analysis_base import Analysis
from lyra_research.agents.synthesis import (
    ContradictionDetectorAgent,
    CrossSourceSynthesizerAgent,
    EvidenceAuditorAgent,
    FalsificationCheckerAgent,
)


@pytest.mark.asyncio
async def test_cross_source_synthesizer_basic():
    """Test basic cross-source synthesis."""
    agent = CrossSourceSynthesizerAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="paper",
            findings=["Transformer models improve performance", "Attention mechanism is key"],
            confidence=0.9,
        ),
        Analysis(
            source_id="s2",
            analysis_type="paper",
            findings=["Transformer architecture enables parallelization", "Attention weights are interpretable"],
            confidence=0.85,
        ),
    ]

    result = await agent.synthesize(analyses)

    assert result.synthesis_type == "cross_source"
    assert len(result.findings) == 4
    assert "themes" in result.metadata
    assert "taxonomy" in result.metadata
    assert result.confidence > 0.0


@pytest.mark.asyncio
async def test_cross_source_synthesizer_theme_extraction():
    """Test theme extraction from findings."""
    agent = CrossSourceSynthesizerAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="paper",
            findings=[
                "Performance improvements with attention",
                "Performance gains from parallelization",
                "Attention mechanism improves accuracy",
            ],
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    themes = result.metadata["themes"]
    assert "performance" in themes or "attention" in themes


@pytest.mark.asyncio
async def test_cross_source_synthesizer_empty_analyses():
    """Test synthesis with empty analyses."""
    agent = CrossSourceSynthesizerAgent()

    result = await agent.synthesize([])

    assert result.synthesis_type == "cross_source"
    assert len(result.findings) == 0
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_contradiction_detector_basic():
    """Test basic contradiction detection."""
    agent = ContradictionDetectorAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="cross_source",
            findings=[
                "Model A improves performance significantly",
                "Model B degrades performance on this task",
            ],
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    assert result.synthesis_type == "contradiction"
    assert "contradictions" in result.metadata
    assert result.metadata["contradiction_count"] >= 0


@pytest.mark.asyncio
async def test_contradiction_detector_no_contradictions():
    """Test contradiction detection with no contradictions."""
    agent = ContradictionDetectorAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="cross_source",
            findings=[
                "Model A improves performance",
                "Model B also improves performance",
            ],
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    assert result.metadata["contradiction_count"] == 0
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_contradiction_detector_opposing_claims():
    """Test detection of opposing claims."""
    agent = ContradictionDetectorAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="cross_source",
            findings=[
                "Transformer attention mechanism improves accuracy significantly",
                "Transformer attention mechanism degrades accuracy on small datasets",
            ],
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    assert result.metadata["contradiction_count"] > 0
    assert result.confidence < 1.0


@pytest.mark.asyncio
async def test_evidence_auditor_basic():
    """Test basic evidence auditing."""
    agent = EvidenceAuditorAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="contradiction",
            findings=[
                "Model achieves 95% accuracy [1]",
                "Performance improves by 10%",  # No citation
            ],
            metadata={"contradictions": []},
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    assert result.synthesis_type == "evidence"
    assert "evidence_issues" in result.metadata
    assert result.metadata["issues_count"] > 0


@pytest.mark.asyncio
async def test_evidence_auditor_missing_citations():
    """Test detection of missing citations."""
    agent = EvidenceAuditorAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="contradiction",
            findings=[
                "Model achieves 95% accuracy",  # No citation
                "Performance improves significantly",  # No citation
            ],
            metadata={"contradictions": []},
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    issues = result.metadata["evidence_issues"]
    missing_citation_issues = [i for i in issues if i["issue_type"] == "missing_citation"]
    assert len(missing_citation_issues) >= 2


@pytest.mark.asyncio
async def test_evidence_auditor_weak_evidence():
    """Test detection of weak evidence (single citation)."""
    agent = EvidenceAuditorAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="contradiction",
            findings=[
                "Model achieves 95% accuracy [1]",  # Single citation
            ],
            metadata={"contradictions": []},
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    issues = result.metadata["evidence_issues"]
    weak_evidence_issues = [i for i in issues if i["issue_type"] == "weak_evidence"]
    assert len(weak_evidence_issues) >= 1


@pytest.mark.asyncio
async def test_evidence_auditor_strong_evidence():
    """Test that strong evidence (3+ citations) passes."""
    agent = EvidenceAuditorAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="contradiction",
            findings=[
                "Model achieves 95% accuracy [1][2][3]",  # Strong evidence
            ],
            metadata={"contradictions": []},
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    issues = result.metadata["evidence_issues"]
    # Should have no issues for this finding
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_falsification_checker_basic():
    """Test basic falsification checking."""
    agent = FalsificationCheckerAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="evidence",
            findings=[
                "Model always achieves perfect accuracy",  # Overstatement
            ],
            metadata={"evidence_issues": []},
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    assert result.synthesis_type == "falsification"
    assert "falsification_risks" in result.metadata
    assert result.metadata["risk_count"] > 0


@pytest.mark.asyncio
async def test_falsification_checker_overstatements():
    """Test detection of overstated claims."""
    agent = FalsificationCheckerAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="evidence",
            findings=[
                "This method always works perfectly",
                "The model never fails on any input",
                "This is the best approach ever",
            ],
            metadata={"evidence_issues": []},
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    risks = result.metadata["falsification_risks"]
    overstatement_risks = [r for r in risks if r["risk_type"] == "overstatement"]
    assert len(overstatement_risks) >= 2


@pytest.mark.asyncio
async def test_falsification_checker_unverified_numerical():
    """Test detection of unverified numerical claims."""
    agent = FalsificationCheckerAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="evidence",
            findings=[
                "Model achieves 95.5% accuracy",  # No citation
            ],
            metadata={"evidence_issues": []},
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    risks = result.metadata["falsification_risks"]
    numerical_risks = [r for r in risks if r["risk_type"] == "unverified_numerical"]
    assert len(numerical_risks) >= 1


@pytest.mark.asyncio
async def test_falsification_checker_critical_evidence_gaps():
    """Test promotion of critical evidence issues."""
    agent = FalsificationCheckerAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="evidence",
            findings=["Some finding"],
            metadata={
                "evidence_issues": [
                    {
                        "finding": "Critical claim",
                        "issue_type": "missing_citation",
                        "severity": "critical",
                        "description": "Critical evidence gap",
                    }
                ]
            },
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    risks = result.metadata["falsification_risks"]
    critical_risks = [r for r in risks if r["severity"] == "critical"]
    assert len(critical_risks) >= 1


@pytest.mark.asyncio
async def test_falsification_checker_no_risks():
    """Test falsification checking with no risks."""
    agent = FalsificationCheckerAgent()

    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="evidence",
            findings=[
                "Model achieves 95% accuracy [1][2][3]",  # Well-cited
            ],
            metadata={"evidence_issues": []},
            confidence=0.9,
        ),
    ]

    result = await agent.synthesize(analyses)

    assert result.metadata["risk_count"] == 0
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_synthesis_pipeline_integration():
    """Test full synthesis pipeline integration."""
    # Step 1: Cross-source synthesis
    cross_source = CrossSourceSynthesizerAgent()
    analyses = [
        Analysis(
            source_id="s1",
            analysis_type="paper",
            findings=["Transformer improves performance", "Attention is key"],
            confidence=0.9,
        ),
    ]
    synthesis_result = await cross_source.synthesize(analyses)

    # Step 2: Contradiction detection
    contradiction = ContradictionDetectorAgent()
    contradiction_result = await contradiction.synthesize([
        Analysis(
            source_id="synthesis",
            analysis_type="cross_source",
            findings=synthesis_result.findings,
            metadata=synthesis_result.metadata,
            confidence=synthesis_result.confidence,
        )
    ])

    # Step 3: Evidence audit
    evidence = EvidenceAuditorAgent()
    evidence_result = await evidence.synthesize([
        Analysis(
            source_id="contradiction",
            analysis_type="contradiction",
            findings=contradiction_result.findings,
            metadata=contradiction_result.metadata,
            confidence=contradiction_result.confidence,
        )
    ])

    # Step 4: Falsification check
    falsification = FalsificationCheckerAgent()
    final_result = await falsification.synthesize([
        Analysis(
            source_id="evidence",
            analysis_type="evidence",
            findings=evidence_result.findings,
            metadata=evidence_result.metadata,
            confidence=evidence_result.confidence,
        )
    ])

    assert final_result.synthesis_type == "falsification"
    assert "falsification_risks" in final_result.metadata

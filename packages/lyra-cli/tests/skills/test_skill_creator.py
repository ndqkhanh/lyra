"""Tests for skill creator."""

import pytest
from lyra_cli.skills.skill_creator import (
    SkillCreator,
    ExecutionTrace,
    PatternType,
    CreationSource,
)


@pytest.fixture
def creator():
    """Create a fresh creator instance."""
    return SkillCreator(min_confidence=0.7, min_novelty=0.3)


@pytest.fixture
def sample_trace():
    """Create a sample execution trace."""
    return ExecutionTrace(
        trace_id="trace_001",
        task_description="write unit tests for the authentication module",
        steps=(
            "Read the authentication module code",
            "Identify test cases",
            "Write test file with pytest",
            "Run tests to verify",
            "Check coverage report",
        ),
        tools_used=("Read", "Write", "Bash"),
        success=True,
        duration_ms=5000.0,
        tokens_used=2000,
    )


@pytest.fixture
def error_recovery_trace():
    """Create a trace with error recovery."""
    return ExecutionTrace(
        trace_id="trace_002",
        task_description="fix the failing test",
        steps=(
            "Run tests",
            "Identify failing test",
            "Debug the issue",
            "Fix the code",
            "Verify tests pass",
        ),
        tools_used=("Bash", "Read", "Edit"),
        success=True,
        duration_ms=3000.0,
        tokens_used=1500,
        error_message="AssertionError: expected 5, got 3",
    )


class TestSkillCreator:
    """Test suite for SkillCreator."""

    def test_analyze_successful_trace(self, creator, sample_trace):
        """Test analyzing a successful execution trace."""
        patterns = creator.analyze_trace(sample_trace)

        assert len(patterns) > 0
        assert creator.stats.total_traces_analyzed == 1
        assert creator.stats.patterns_extracted > 0

    def test_analyze_failed_trace_returns_empty(self, creator):
        """Test that failed traces are not analyzed."""
        failed_trace = ExecutionTrace(
            trace_id="trace_fail",
            task_description="attempt something",
            steps=("Try", "Fail"),
            tools_used=("Bash",),
            success=False,
            duration_ms=1000.0,
            tokens_used=500,
        )

        patterns = creator.analyze_trace(failed_trace)

        assert len(patterns) == 0

    def test_extract_tool_sequence_pattern(self, creator, sample_trace):
        """Test extraction of tool sequence patterns."""
        patterns = creator.analyze_trace(sample_trace)

        # Should extract tool sequence pattern
        tool_patterns = [p for p in patterns if p.pattern_type == PatternType.TOOL_SEQUENCE]
        assert len(tool_patterns) > 0

        tool_pattern = tool_patterns[0]
        assert "Read" in tool_pattern.description
        assert tool_pattern.confidence > 0.0

    def test_extract_decision_point_pattern(self, creator):
        """Test extraction of decision point patterns."""
        trace = ExecutionTrace(
            trace_id="trace_decision",
            task_description="conditional logic",
            steps=(
                "Check if file exists",
                "If exists, read it",
                "Otherwise, create new file",
            ),
            tools_used=("Read", "Write"),
            success=True,
            duration_ms=2000.0,
            tokens_used=1000,
        )

        patterns = creator.analyze_trace(trace)

        decision_patterns = [p for p in patterns if p.pattern_type == PatternType.DECISION_POINT]
        assert len(decision_patterns) > 0

    def test_extract_error_recovery_pattern(self, creator, error_recovery_trace):
        """Test extraction of error recovery patterns."""
        patterns = creator.analyze_trace(error_recovery_trace)

        error_patterns = [p for p in patterns if p.pattern_type == PatternType.ERROR_RECOVERY]
        assert len(error_patterns) > 0

        error_pattern = error_patterns[0]
        assert "AssertionError" in error_pattern.description

    def test_extract_domain_heuristics(self, creator, sample_trace):
        """Test extraction of domain-specific heuristics."""
        patterns = creator.analyze_trace(sample_trace)

        heuristic_patterns = [p for p in patterns if p.pattern_type == PatternType.DOMAIN_HEURISTIC]
        assert len(heuristic_patterns) > 0

    def test_pattern_occurrence_counting(self, creator, sample_trace):
        """Test that repeated patterns increment occurrence count."""
        # Analyze same trace twice
        creator.analyze_trace(sample_trace)
        creator.analyze_trace(sample_trace)

        # Get patterns
        patterns = creator.get_high_confidence_patterns(min_occurrences=2)

        # Should have patterns with occurrence_count >= 2
        assert len(patterns) > 0
        assert all(p.occurrence_count >= 2 for p in patterns)

    def test_propose_skill_from_patterns(self, creator, sample_trace):
        """Test skill proposal generation."""
        patterns = creator.analyze_trace(sample_trace)

        proposal = creator.propose_skill(patterns)

        assert proposal is not None
        assert proposal.name
        assert proposal.description
        assert proposal.category
        assert len(proposal.triggers) > 0
        assert len(proposal.content) > 0
        assert proposal.confidence >= creator.min_confidence

    def test_propose_skill_requires_high_confidence(self, creator):
        """Test that low-confidence patterns are filtered out."""
        # Create low-confidence patterns
        from lyra_cli.skills.skill_creator import ExtractedPattern

        low_conf_pattern = ExtractedPattern(
            pattern_type=PatternType.TOOL_SEQUENCE,
            description="Low confidence pattern",
            trigger_conditions=("trigger",),
            steps=("step1",),
            confidence=0.3,  # Below threshold
            occurrence_count=1,
            source_traces=("trace_001",),
        )

        proposal = creator.propose_skill([low_conf_pattern])

        assert proposal is None  # Should be rejected

    def test_propose_skill_checks_novelty(self, creator, sample_trace):
        """Test that novelty checking works."""
        patterns = creator.analyze_trace(sample_trace)

        # Register existing skill with similar name
        creator.register_existing_skill("tool-sequence-skill")

        proposal = creator.propose_skill(patterns, name="tool-sequence-skill")

        # Should be rejected due to low novelty
        assert proposal is None or proposal.novelty_score < creator.min_novelty

    def test_skill_md_generation(self, creator, sample_trace):
        """Test SKILL.md content generation."""
        patterns = creator.analyze_trace(sample_trace)
        proposal = creator.propose_skill(patterns)

        assert proposal is not None

        # Check frontmatter
        assert "---" in proposal.content
        assert f"name: {proposal.name}" in proposal.content
        assert f"description: {proposal.description}" in proposal.content
        assert "triggers:" in proposal.content
        assert "tags:" in proposal.content

        # Check content sections
        assert "# " in proposal.content  # Has heading
        assert "## When to Use" in proposal.content
        assert "## Workflow" in proposal.content

    def test_accept_proposal_updates_stats(self, creator, sample_trace):
        """Test that accepting proposals updates statistics."""
        patterns = creator.analyze_trace(sample_trace)
        proposal = creator.propose_skill(patterns)

        assert proposal is not None

        creator.accept_proposal(proposal)

        stats = creator.get_stats()
        assert stats["skills_accepted"] == 1
        assert proposal.name in creator._existing_skills

    def test_reject_proposal_updates_stats(self, creator, sample_trace):
        """Test that rejecting proposals updates statistics."""
        patterns = creator.analyze_trace(sample_trace)
        proposal = creator.propose_skill(patterns)

        assert proposal is not None

        creator.reject_proposal(proposal)

        stats = creator.get_stats()
        assert stats["skills_rejected"] == 1

    def test_get_patterns_by_type(self, creator, sample_trace, error_recovery_trace):
        """Test filtering patterns by type."""
        creator.analyze_trace(sample_trace)
        creator.analyze_trace(error_recovery_trace)

        tool_patterns = creator.get_patterns_by_type(PatternType.TOOL_SEQUENCE)
        error_patterns = creator.get_patterns_by_type(PatternType.ERROR_RECOVERY)

        assert len(tool_patterns) > 0
        assert len(error_patterns) > 0

    def test_get_high_confidence_patterns(self, creator, sample_trace):
        """Test getting patterns with multiple occurrences."""
        # Analyze trace multiple times
        for _ in range(5):
            creator.analyze_trace(sample_trace)

        high_conf = creator.get_high_confidence_patterns(min_occurrences=3)

        assert len(high_conf) > 0
        assert all(p.occurrence_count >= 3 for p in high_conf)

    def test_custom_name_and_category(self, creator, sample_trace):
        """Test proposing skill with custom name and category."""
        patterns = creator.analyze_trace(sample_trace)

        proposal = creator.propose_skill(
            patterns,
            name="custom-skill",
            category="custom-category",
        )

        assert proposal is not None
        assert proposal.name == "custom-skill"
        assert proposal.category == "custom-category"

    def test_stats_tracking(self, creator, sample_trace):
        """Test comprehensive statistics tracking."""
        # Analyze traces
        creator.analyze_trace(sample_trace)
        creator.analyze_trace(sample_trace)

        # Propose skills
        patterns = creator.analyze_trace(sample_trace)
        proposal = creator.propose_skill(patterns)

        if proposal:
            creator.accept_proposal(proposal)

        stats = creator.get_stats()

        assert stats["total_traces_analyzed"] == 3
        assert stats["patterns_extracted"] > 0
        assert stats["skills_proposed"] > 0
        assert stats["acceptance_rate"] >= 0.0

    def test_empty_patterns_returns_none(self, creator):
        """Test that empty pattern list returns None."""
        proposal = creator.propose_skill([])
        assert proposal is None

    def test_novelty_calculation_with_no_existing_skills(self, creator, sample_trace):
        """Test novelty is high when no existing skills."""
        patterns = creator.analyze_trace(sample_trace)
        proposal = creator.propose_skill(patterns)

        assert proposal is not None
        assert proposal.novelty_score > 0.5  # Should be novel

    def test_source_traces_tracked(self, creator, sample_trace):
        """Test that source traces are tracked in proposals."""
        patterns = creator.analyze_trace(sample_trace)
        proposal = creator.propose_skill(patterns)

        assert proposal is not None
        assert len(proposal.source_traces) > 0
        assert sample_trace.trace_id in proposal.source_traces

    def test_tools_extraction(self, creator, sample_trace):
        """Test that tools are extracted from patterns."""
        patterns = creator.analyze_trace(sample_trace)
        proposal = creator.propose_skill(patterns)

        assert proposal is not None
        assert len(proposal.tools) > 0

    def test_triggers_extraction(self, creator, sample_trace):
        """Test that triggers are extracted from patterns."""
        patterns = creator.analyze_trace(sample_trace)
        proposal = creator.propose_skill(patterns)

        assert proposal is not None
        assert len(proposal.triggers) > 0

    def test_confidence_averaging(self, creator):
        """Test that proposal confidence is average of pattern confidences."""
        from lyra_cli.skills.skill_creator import ExtractedPattern

        patterns = [
            ExtractedPattern(
                pattern_type=PatternType.TOOL_SEQUENCE,
                description="Pattern 1",
                trigger_conditions=("trigger",),
                steps=("step",),
                confidence=0.8,
                occurrence_count=1,
                source_traces=("trace_001",),
            ),
            ExtractedPattern(
                pattern_type=PatternType.TOOL_SEQUENCE,
                description="Pattern 2",
                trigger_conditions=("trigger",),
                steps=("step",),
                confidence=0.9,
                occurrence_count=1,
                source_traces=("trace_001",),
            ),
        ]

        proposal = creator.propose_skill(patterns)

        assert proposal is not None
        # Average of 0.8 and 0.9 = 0.85
        assert proposal.confidence == pytest.approx(0.85)

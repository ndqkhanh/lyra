"""Comprehensive detector accuracy tests with 20 prompts."""

import pytest
from lyra_cli.spec_kit.detector import Detector


@pytest.mark.asyncio
async def test_spec_worthy_prompts():
    """Test prompts that should be detected as spec-worthy."""
    detector = Detector()

    spec_worthy_prompts = [
        "Build me a deep-research orchestrator that runs 5 sub-agents in parallel",
        "Implement a TUI like Claude Code with hierarchical trees and progress indicators",
        "Add a skill marketplace where users can discover and install community skills",
        "Create an end-to-end testing framework for Lyra with snapshot testing",
        "Design a context optimization system with sliding windows and semantic retrieval",
        "Build a multi-agent system for code review with parallel analysis",
        "Implement a plugin architecture for extending Lyra with custom tools",
        "Create a distributed task queue system with Redis backend",
        "Design and implement a real-time collaboration feature for pair programming",
        "Build a comprehensive logging and monitoring dashboard for agent activities",
    ]

    for prompt in spec_worthy_prompts:
        verdict = await detector.classify(prompt)
        assert verdict.spec_worthy, f"Failed to detect spec-worthy: {prompt[:50]}..."
        assert verdict.confidence >= 0.7, f"Low confidence ({verdict.confidence}) for: {prompt[:50]}..."


@pytest.mark.asyncio
async def test_not_spec_worthy_prompts():
    """Test prompts that should NOT be detected as spec-worthy."""
    detector = Detector()

    not_spec_worthy_prompts = [
        "Fix the typo in README",
        "Run the tests",
        "Show me the agent integration code",
        "Update line 42 in detector.py to use confidence >= 0.7",
        "/model switch to opus",
        "What does this function do?",
        "Explain the detector logic",
        "Check if the build passes",
        "Bump version to 1.2.0",
        "Add a comment to line 15",
    ]

    for prompt in not_spec_worthy_prompts:
        verdict = await detector.classify(prompt)
        assert not verdict.spec_worthy, f"False positive for: {prompt}"
        assert verdict.confidence < 0.7, f"High confidence ({verdict.confidence}) for simple task: {prompt}"


@pytest.mark.asyncio
async def test_bypass_conditions():
    """Test always-bypass conditions."""
    detector = Detector()

    # Slash commands
    verdict = await detector.classify("/model switch to opus")
    assert not verdict.spec_worthy
    assert verdict.exemption_reason == "slash command"

    # Already active
    verdict = await detector.classify("Build a system", active_phase="drafting_spec")
    assert not verdict.spec_worthy
    assert verdict.exemption_reason == "spec-kit already running"


@pytest.mark.asyncio
async def test_detector_latency():
    """Test detector performance."""
    detector = Detector()

    # Rule-based path should be fast
    verdict = await detector.classify("Fix typo")
    assert verdict.latency_ms < 10, f"Rule-based too slow: {verdict.latency_ms}ms"

    # Spec-worthy should also be fast (no LLM call needed)
    verdict = await detector.classify("Build me a complex system with multiple components")
    assert verdict.latency_ms < 10, f"Spec-worthy detection too slow: {verdict.latency_ms}ms"

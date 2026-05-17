"""Simple test for Phase 1 detector."""

import asyncio
from lyra_cli.spec_kit.detector import Detector
from lyra_cli.spec_kit.orchestrator import Orchestrator


async def test_detector():
    """Test detector with sample prompts."""
    detector = Detector()

    # Test spec-worthy prompt
    prompt1 = "Build me a deep-research orchestrator that runs 5 sub-agents in parallel"
    verdict1 = await detector.classify(prompt1)
    print(f"Prompt: {prompt1[:50]}...")
    print(f"Spec-worthy: {verdict1.spec_worthy}, Confidence: {verdict1.confidence:.2f}")
    print(f"Reasoning: {verdict1.reasoning}\n")

    # Test not spec-worthy prompt
    prompt2 = "Fix the typo in README"
    verdict2 = await detector.classify(prompt2)
    print(f"Prompt: {prompt2}")
    print(f"Spec-worthy: {verdict2.spec_worthy}, Confidence: {verdict2.confidence:.2f}")
    print(f"Reasoning: {verdict2.reasoning}\n")

    # Test slash command bypass
    prompt3 = "/model switch to opus"
    verdict3 = await detector.classify(prompt3)
    print(f"Prompt: {prompt3}")
    print(f"Spec-worthy: {verdict3.spec_worthy}, Confidence: {verdict3.confidence:.2f}")
    print(f"Reasoning: {verdict3.reasoning}\n")


async def test_orchestrator():
    """Test orchestrator intercept."""
    orchestrator = Orchestrator()

    prompt = "Create an end-to-end testing framework"
    result = await orchestrator.maybe_intercept(prompt)
    print(f"Intercepted: {result.intercepted}")


if __name__ == "__main__":
    print("=== Testing Phase 1: Detector ===\n")
    asyncio.run(test_detector())
    print("\n=== Testing Phase 1: Orchestrator ===\n")
    asyncio.run(test_orchestrator())

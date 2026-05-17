"""Test Phase 2: State machine and orchestration."""

import asyncio
from pathlib import Path
from lyra_cli.spec_kit.orchestrator import Orchestrator


async def test_state_machine():
    """Test full state machine flow."""
    orchestrator = Orchestrator()

    # Test spec-worthy prompt (same as Phase 1)
    prompt = "Build me a deep-research orchestrator that runs 5 sub-agents in parallel"
    print(f"Testing prompt: {prompt}\n")

    # First check detector
    verdict = await orchestrator.detector.classify(prompt)
    print(f"Detector verdict: spec_worthy={verdict.spec_worthy}, confidence={verdict.confidence}")

    result = await orchestrator.maybe_intercept(prompt)

    print(f"\nIntercepted: {result.intercepted}")
    print(f"Feature ID: {result.feature_id}")
    print(f"Error: {result.error}")

    # Check if files were created
    if result.feature_id:
        feature_dir = Path("specs") / result.feature_id
        print(f"\nFeature directory: {feature_dir}")
        print(f"Exists: {feature_dir.exists()}")

        if feature_dir.exists():
            files = list(feature_dir.glob("*.md"))
            print(f"Files created: {[f.name for f in files]}")


if __name__ == "__main__":
    print("=== Testing Phase 2: State Machine ===\n")
    asyncio.run(test_state_machine())

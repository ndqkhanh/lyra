"""harness_core.examples — runnable end-to-end demos.

These exist as both **documentation** (copy-paste starting points for any
consumer project) and **integration tests** (verifying the whole stack
composes). Each demo:

    1. Builds the substrate (graph + documents + HippoRAG index).
    2. Wires the operators with stub LLMs/retrievers (deterministic).
    3. Composes gates + cache + budget into a MultiHopPipeline.
    4. Wraps it in a typed MultiHopProgram with a Signature.
    5. Runs a query end-to-end + asserts the canonical trajectory.

Production deployments swap StubLLM/StubRetriever for real Anthropic/OpenAI
LMs and BGE-M3/Voyage embedders — the wiring stays the same.
"""
from __future__ import annotations

from .end_to_end_demo import (
    DemoOutput,
    build_demo_pipeline,
    build_demo_program,
    run_research_demo,
)

__all__ = [
    "DemoOutput",
    "build_demo_pipeline",
    "build_demo_program",
    "run_research_demo",
]

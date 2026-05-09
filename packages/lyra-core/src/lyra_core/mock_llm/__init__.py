"""Mock-LLM parity harness for E2E CLI tests (claw-code parity).

Ships a scripted fake that speaks the Anthropic-style ``generate`` +
``stream_generate`` surface so the whole interactive CLI stack can be
driven end-to-end in CI without ever touching the network.

Reference: ``claw-code/rust/crates/rusty-claude-cli/tests/mock_parity_harness.rs``.
"""
from __future__ import annotations

from .harness import (
    MockLLMError,
    ScenarioCase,
    ScriptedLLM,
    StreamChunk,
)

__all__ = [
    "MockLLMError",
    "ScenarioCase",
    "ScriptedLLM",
    "StreamChunk",
]

"""Contract tests for the context-window preflight estimator.

Mirrors claw-code's preflight logic: estimate input tokens before
sending the request and refuse to call the API if the estimate
exceeds the model's context window. The estimator uses a 4 chars/token
heuristic — fast, dependency-free, and conservative enough that real
tokenizer counts only ever come in *under* our estimate (typical real
ratio is closer to 3.5).
"""
from __future__ import annotations

import pytest

from lyra_core.providers.preflight import (
    CONTEXT_WINDOW,
    ContextWindowExceeded,
    PreflightReport,
    estimate_input_tokens,
    preflight,
)


def test_small_request_passes() -> None:
    report = preflight(
        model="claude-opus-4.5",
        messages=[{"role": "user", "content": "hi"}],
        system="",
        tools=[],
        max_output=1_000,
    )
    assert isinstance(report, PreflightReport)
    assert report.estimated_input_tokens > 0
    assert report.would_exceed is False


def test_oversized_request_raises() -> None:
    huge = "x" * 4 * 250_000
    with pytest.raises(ContextWindowExceeded) as exc:
        preflight(
            model="claude-opus-4.5",
            messages=[{"role": "user", "content": huge}],
            system="",
            tools=[],
            max_output=10_000,
        )
    assert "claude-opus-4.5" in str(exc.value)
    assert "200000" in str(exc.value).replace(",", "")


def test_unknown_model_passes_unchecked() -> None:
    report = preflight(
        model="something-not-in-registry",
        messages=[{"role": "user", "content": "x" * 4_000_000}],
        system="",
        tools=[],
        max_output=1_000,
    )
    assert report.would_exceed is False
    assert report.context_window is None


def test_estimate_counts_system_and_tools() -> None:
    base = estimate_input_tokens(
        messages=[{"role": "user", "content": "hi"}],
        system="",
        tools=[],
    )
    with_sys = estimate_input_tokens(
        messages=[{"role": "user", "content": "hi"}],
        system="you are a helpful assistant",
        tools=[],
    )
    assert with_sys > base


def test_max_output_is_subtracted_from_window() -> None:
    with pytest.raises(ContextWindowExceeded):
        preflight(
            model="claude-opus-4.5",
            messages=[{"role": "user", "content": "x" * (4 * 150_000)}],
            system="",
            tools=[],
            max_output=60_000,
        )


def test_context_window_table_includes_known_models() -> None:
    assert "claude-opus-4.5" in CONTEXT_WINDOW
    assert CONTEXT_WINDOW["claude-opus-4.5"] >= 200_000


def test_estimate_handles_multimodal_content() -> None:
    msg = {
        "role": "user",
        "content": [
            {"type": "text", "text": "hello"},
            {"type": "image_url", "image_url": {"url": "https://example.com/x.png"}},
        ],
    }
    n = estimate_input_tokens(messages=[msg], system="", tools=[])
    assert n > 0

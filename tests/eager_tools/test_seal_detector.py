"""Tests for eager tools seal detection."""

import time

import pytest

from lyra_cli.eager_tools import SealDetector, StreamChunk


def test_seal_detection_on_id_transition():
    """Tool sealed when ID changes."""
    detector = SealDetector()

    # First tool
    chunk1 = StreamChunk(tool_call_id="tool_1", name="read_file")
    sealed = detector.process_chunk(chunk1)
    assert len(sealed) == 0  # Not sealed yet

    # Second tool (seals first)
    chunk2 = StreamChunk(tool_call_id="tool_2", name="search")
    sealed = detector.process_chunk(chunk2)
    assert len(sealed) == 1
    assert sealed[0].tool_call_id == "tool_1"
    assert sealed[0].tool_name == "read_file"


def test_seal_detection_accumulates_arguments():
    """Arguments accumulate across chunks."""
    detector = SealDetector()

    # First chunk with name
    chunk1 = StreamChunk(tool_call_id="tool_1", name="read_file")
    detector.process_chunk(chunk1)

    # Second chunk with arguments
    chunk2 = StreamChunk(tool_call_id="tool_1", arguments={"path": "test.py"})
    detector.process_chunk(chunk2)

    # Third chunk seals it
    chunk3 = StreamChunk(tool_call_id="tool_2", name="search")
    sealed = detector.process_chunk(chunk3)

    assert len(sealed) == 1
    assert sealed[0].tool_name == "read_file"
    assert sealed[0].arguments == {"path": "test.py"}


def test_seal_detection_latency():
    """Seal detection under 5ms."""
    detector = SealDetector()
    chunk = StreamChunk(tool_call_id="tool_1", name="read_file")

    start = time.perf_counter()
    detector.process_chunk(chunk)
    duration = time.perf_counter() - start

    assert duration < 0.005  # 5ms


def test_reset_clears_state():
    """Reset clears detector state."""
    detector = SealDetector()

    chunk = StreamChunk(tool_call_id="tool_1", name="read_file")
    detector.process_chunk(chunk)

    detector.reset()

    assert detector.current_id is None
    assert detector.current_buffer == {}

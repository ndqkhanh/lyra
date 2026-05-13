"""Unit tests for session_reader."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.transparency.session_reader import (
    read_session_tokens,
    read_last_tool,
    extract_session_id,
)


@pytest.fixture
def session_file(tmp_path: Path) -> Path:
    p = tmp_path / "abc123.jsonl"
    records = [
        {"session_id": "abc123", "usage": {"input_tokens": 100, "output_tokens": 50}},
        {"content": [{"type": "tool_use", "name": "Bash"}, {"type": "text", "text": "hi"}]},
        {"content": [{"type": "tool_use", "name": "Edit"}]},
    ]
    p.write_text("\n".join(json.dumps(r) for r in records))
    return p


@pytest.mark.unit
def test_read_tokens(session_file: Path) -> None:
    tokens_in, tokens_out = read_session_tokens(session_file)
    assert tokens_in == 100
    assert tokens_out == 50


@pytest.mark.unit
def test_read_last_tool(session_file: Path) -> None:
    assert read_last_tool(session_file) == "Edit"


@pytest.mark.unit
def test_extract_session_id(session_file: Path) -> None:
    assert extract_session_id(session_file) == "abc123"


@pytest.mark.unit
def test_extract_session_id_falls_back_to_stem(tmp_path: Path) -> None:
    p = tmp_path / "mysession.jsonl"
    p.write_text('{"no_session_id": true}\n')
    assert extract_session_id(p) == "mysession"


@pytest.mark.unit
def test_read_tokens_missing_file(tmp_path: Path) -> None:
    tokens_in, tokens_out = read_session_tokens(tmp_path / "missing.jsonl")
    assert tokens_in == 0
    assert tokens_out == 0

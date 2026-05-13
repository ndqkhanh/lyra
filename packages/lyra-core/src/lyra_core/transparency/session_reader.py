"""Read Claude Code session state from local files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


_CLAUDE_ROOT = Path.home() / ".claude" / "projects"


def _iter_jsonl(path: Path) -> Iterator[dict]:
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def read_session_tokens(session_jsonl: Path) -> tuple[int, int]:
    """Return (tokens_in, tokens_out) summed across all turns."""
    tokens_in = 0
    tokens_out = 0
    for record in _iter_jsonl(session_jsonl):
        usage = record.get("usage") or {}
        tokens_in += int(usage.get("input_tokens", 0))
        tokens_out += int(usage.get("output_tokens", 0))
    return tokens_in, tokens_out


def read_last_tool(session_jsonl: Path) -> str:
    """Return the most recent tool_name used in the session."""
    last_tool = ""
    for record in _iter_jsonl(session_jsonl):
        for block in record.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                last_tool = block.get("name", "")
    return last_tool


def list_session_files(root: Path = _CLAUDE_ROOT) -> list[Path]:
    """Return all *.jsonl session files under the Claude projects root."""
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.jsonl"))


def extract_session_id(path: Path) -> str:
    """Extract session ID from a JSONL file — first record's session_id or stem."""
    for record in _iter_jsonl(path):
        sid = record.get("session_id") or record.get("sessionId", "")
        if sid:
            return str(sid)
        break
    return path.stem

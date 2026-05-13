"""Unit tests for process_scanner."""
from __future__ import annotations

import pytest
from lyra_core.transparency.process_scanner import _matches_agent, RawProcess


@pytest.mark.unit
def test_matches_claude_command() -> None:
    assert _matches_agent("claude --dangerously-skip-permissions")


@pytest.mark.unit
def test_matches_node_claude() -> None:
    assert _matches_agent("/usr/local/bin/node /usr/lib/claude-code/dist/main.js")


@pytest.mark.unit
def test_does_not_match_unrelated() -> None:
    assert not _matches_agent("python manage.py runserver")
    assert not _matches_agent("vim myfile.py")


@pytest.mark.unit
def test_raw_process_frozen() -> None:
    rp = RawProcess(pid=123, command="claude", cwd="/tmp", cpu_pct=1.0, rss_mb=50.0, started_at=0.0)
    assert rp.pid == 123
    with pytest.raises(Exception):
        rp.pid = 999  # type: ignore[misc]

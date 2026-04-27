"""Wave-F Task 15 — frontier UX bundle contract (/split, /vote, /observe,
/ide, /catch-up)."""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def _session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path)


# ---- /split --------------------------------------------------------


def test_split_usage(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/split")
    assert "usage" in res.output.lower()


def test_split_queues_task(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/split run unit tests on module auth")
    s.dispatch("/split run unit tests on module billing")
    assert len(s.split_queue) == 2
    assert "auth" in s.split_queue[0]


# ---- /vote ---------------------------------------------------------


def test_vote_records_and_tallies(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/vote rust")
    s.dispatch("/vote rust")
    s.dispatch("/vote go")
    res = s.dispatch("/vote results")
    assert "rust — 2" in res.output
    assert "go — 1" in res.output


def test_vote_clear_empties_ledger(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/vote x")
    s.dispatch("/vote clear")
    res = s.dispatch("/vote results")
    assert "no votes" in res.output


def test_vote_usage_when_empty(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/vote")
    assert "usage" in res.output.lower()


# ---- /observe ------------------------------------------------------


def test_observe_default_off(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/observe status")
    assert "observe: off" in res.output


def test_observe_on_and_off(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/observe on")
    assert s.observe_mode is True
    s.dispatch("/observe off")
    assert s.observe_mode is False


def test_observe_tail_without_notes(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/observe tail")
    assert "no notes" in res.output


def test_observe_tail_with_notes(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.observation_log = ["note 1", "note 2", "note 3"]
    res = s.dispatch("/observe tail")
    assert "note 3" in res.output


# ---- /ide ----------------------------------------------------------


def test_ide_list_lists_bridges(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/ide list")
    assert "vscode" in res.output
    assert "current:" in res.output


def test_ide_set_switches_bridge(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/ide set cursor")
    assert getattr(s, "ide_bridge", None) == "cursor"


def test_ide_set_unknown_friendly(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/ide set notepad")
    assert "unknown" in res.output.lower()


def test_ide_open_renders_argv(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    s = _session(tmp_path)
    s.dispatch("/ide set cursor")
    res = s.dispatch("/ide open main.py:5:3")
    assert "cursor" in res.output
    assert "main.py:5:3" in res.output


def test_ide_open_bad_line(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    s = _session(tmp_path)
    res = s.dispatch("/ide open main.py:abc")
    assert "could not parse" in res.output


# ---- /catch-up -----------------------------------------------------


def test_catchup_emits_briefing(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/split plan the refactor")
    s.dispatch("/vote rust")
    res = s.dispatch("/catch-up")
    assert "catch-up briefing" in res.output.lower()
    assert "tdd phase" in res.output.lower()
    assert "split queue" in res.output.lower()

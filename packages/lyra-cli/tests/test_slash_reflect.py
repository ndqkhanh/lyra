"""Phase J.4 (v3.1.0): ``/reflect`` — Reflexion retrospective loop.

Locked surface:

1. ``/reflect`` lists the current memory + auto-inject state.
2. ``/reflect on`` / ``/reflect off`` toggle ``session.reflexion_enabled``.
3. ``/reflect add fail :: lesson`` records a Reflection bound to the
   most recent user prompt.
4. ``/reflect tag rust,tdd fail :: lesson`` records a tagged lesson.
5. ``/reflect clear`` empties the memory.
6. Malformed commands emit a friendly usage hint.
7. The on-disk snapshot lives at ``<repo>/.lyra/reflexion.json``.
"""
from __future__ import annotations

import json
from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def test_reflect_list_empty(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/reflect")
    text = out.output
    assert "auto-inject: off" in text
    assert "no lessons yet" in text


def test_reflect_on_off_toggle(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    assert s.reflexion_enabled is False
    s.dispatch("/reflect on")
    assert s.reflexion_enabled is True
    s.dispatch("/reflect off")
    assert s.reflexion_enabled is False


def test_reflect_add_records_lesson_against_last_task(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("write a failing test for /foo")  # plain-text turn
    out = s.dispatch("/reflect add fail :: forgot the fixture wiring")
    assert "added lesson #1" in out.output
    snap = tmp_path / ".lyra" / "reflexion.json"
    assert snap.exists()
    payload = json.loads(snap.read_text())
    assert len(payload) == 1
    assert payload[0]["verdict"] == "fail"
    assert "fixture" in payload[0]["lesson"]
    assert payload[0]["task"] == "write a failing test for /foo"


def test_reflect_add_requires_separator(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/reflect add fail forgot the separator")
    assert "missing '::'" in out.output


def test_reflect_tag_records_tags(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/reflect tag rust,tdd fail :: missing trait import")
    assert "tags=rust,tdd" in out.output
    payload = json.loads((tmp_path / ".lyra" / "reflexion.json").read_text())
    assert payload[0]["tags"] == ["rust", "tdd"]


def test_reflect_tag_requires_two_words(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/reflect tag rust")
    assert "usage:" in out.output.lower()


def test_reflect_clear_empties_memory(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("anything")
    s.dispatch("/reflect add fail :: l1")
    s.dispatch("/reflect add pass :: l2")
    out = s.dispatch("/reflect clear")
    assert "cleared" in out.output
    payload = json.loads((tmp_path / ".lyra" / "reflexion.json").read_text())
    assert payload == []


def test_reflect_unknown_subcommand_is_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/reflect nonsense")
    assert "usage:" in out.output.lower()


def test_reflect_list_after_add_shows_lesson(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("anything")
    s.dispatch("/reflect add fail :: forgot the precondition")
    out = s.dispatch("/reflect")
    assert "[fail]" in out.output
    assert "precondition" in out.output

"""L312-5 — HUMAN_DIRECTIVE.md watcher contract tests.

Eight cases:

1. Missing file → None.
2. Empty file → None.
3. Populated file → text returned + file truncated.
4. Same file unchanged after consumption → None.
5. mtime advance after consumption → text returned again.
6. Archive directory created on first consumption.
7. Archive files are numbered sequentially.
8. Archive write failure does not block consumption.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from lyra_core.loops.directive import HumanDirective


def test_missing_file_returns_none(tmp_path: Path):
    d = HumanDirective(path=tmp_path / "HUMAN_DIRECTIVE.md")
    assert d.consume_if_changed() is None


def test_empty_file_returns_none(tmp_path: Path):
    p = tmp_path / "HUMAN_DIRECTIVE.md"
    p.write_text("")
    d = HumanDirective(path=p)
    assert d.consume_if_changed() is None


def test_populated_file_returns_text_and_truncates(tmp_path: Path):
    p = tmp_path / "HUMAN_DIRECTIVE.md"
    p.write_text("STOP")
    d = HumanDirective(path=p)
    text = d.consume_if_changed()
    assert text == "STOP"
    # Live file truncated so the next directive is a fresh event.
    assert p.read_text() == ""


def test_unchanged_file_returns_none_after_consumption(tmp_path: Path):
    p = tmp_path / "HUMAN_DIRECTIVE.md"
    p.write_text("first directive")
    d = HumanDirective(path=p)
    assert d.consume_if_changed() == "first directive"
    # Truncated; second consume sees empty.
    assert d.consume_if_changed() is None


def test_mtime_advance_after_consumption_returns_new_text(tmp_path: Path):
    p = tmp_path / "HUMAN_DIRECTIVE.md"
    p.write_text("first")
    d = HumanDirective(path=p)
    assert d.consume_if_changed() == "first"
    # New directive — write again; bump mtime explicitly because some
    # filesystems have second-resolution mtimes.
    time.sleep(0.01)
    p.write_text("second")
    new_mtime = p.stat().st_mtime + 2.0
    os.utime(p, (new_mtime, new_mtime))
    assert d.consume_if_changed() == "second"


def test_archive_dir_created_on_first_consumption(tmp_path: Path):
    p = tmp_path / "HUMAN_DIRECTIVE.md"
    p.write_text("hi")
    d = HumanDirective(path=p)
    assert not (tmp_path / "directives").exists()
    d.consume_if_changed()
    assert (tmp_path / "directives").exists()
    archived = list((tmp_path / "directives").glob("*.md"))
    assert len(archived) == 1
    assert archived[0].read_text() == "hi"


def test_archives_numbered_sequentially(tmp_path: Path):
    p = tmp_path / "HUMAN_DIRECTIVE.md"
    d = HumanDirective(path=p)
    for i in range(3):
        p.write_text(f"directive {i}")
        new_mtime = time.time() + (i + 1) * 2.0
        os.utime(p, (new_mtime, new_mtime))
        assert d.consume_if_changed() == f"directive {i}"
    archive = sorted((tmp_path / "directives").glob("*.md"))
    assert len(archive) == 3
    # Numbered 001-, 002-, 003-.
    for i, f in enumerate(archive, start=1):
        assert f.name.startswith(f"{i:03d}-")


def test_archive_write_failure_does_not_block(tmp_path: Path):
    """Inject an archive directory at a path where mkdir fails (a file)."""
    p = tmp_path / "HUMAN_DIRECTIVE.md"
    archive_blocker = tmp_path / "directives"
    archive_blocker.write_text("I am a file, not a dir")  # blocks mkdir

    p.write_text("hi")
    d = HumanDirective(path=p)
    # Must return the text even though archive can't be written.
    assert d.consume_if_changed() == "hi"

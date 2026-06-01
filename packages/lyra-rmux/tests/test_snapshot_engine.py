"""Tests for lyra_rmux.snapshot_engine."""

import json
import os
import tempfile
import pytest

from lyra_rmux.snapshot_engine import SnapshotEngine
from lyra_rmux.models import Snapshot


@pytest.fixture
def engine() -> SnapshotEngine:
    return SnapshotEngine()


# ------------------------------------------------------------------
# capture
# ------------------------------------------------------------------


def test_capture(engine: SnapshotEngine) -> None:
    snap = engine.capture("pane-1", ("line1", "line2"))
    assert snap.pane_id == "pane-1"
    assert snap.lines == ("line1", "line2")
    assert snap.cursor_row == 1
    assert snap.cursor_col == 5


def test_capture_empty(engine: SnapshotEngine) -> None:
    snap = engine.capture("pane-2", ())
    assert snap.lines == ()
    assert snap.cursor_row == 0
    assert snap.cursor_col == 0


def test_capture_archives(engine: SnapshotEngine) -> None:
    engine.capture("pane-3", ("a",))
    engine.capture("pane-3", ("b",))
    assert engine.snapshot_count("pane-3") == 2


# ------------------------------------------------------------------
# diff
# ------------------------------------------------------------------


def test_diff_no_history(engine: SnapshotEngine) -> None:
    assert engine.diff("unknown") is None


def test_diff_single_snapshot(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("hello",))
    assert engine.diff("p1") is None


def test_diff_added_lines(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("hello",))
    engine.capture("p1", ("hello", "world"))
    d = engine.diff("p1")
    assert d is not None
    assert "+world" in d


def test_diff_removed_lines(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("a", "b", "c"))
    engine.capture("p1", ("a", "c"))
    d = engine.diff("p1")
    assert d is not None
    assert "-b" in d


def test_diff_unchanged(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("same",))
    engine.capture("p1", ("same",))
    d = engine.diff("p1")
    assert d is not None
    assert " same" in d
    assert "+" not in d
    assert "-" not in d


def test_diff_between_snapshots(engine: SnapshotEngine) -> None:
    a = Snapshot(pane_id="p", lines=("old1", "old2"))
    b = Snapshot(pane_id="p", lines=("new1", "new2"))
    d = engine.diff_between("p", a, b)
    assert "-old1" in d
    assert "+new1" in d


# ------------------------------------------------------------------
# replay
# ------------------------------------------------------------------


def test_replay_no_history(engine: SnapshotEngine) -> None:
    assert engine.replay("unknown") is None


def test_replay(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("first line of output",))
    engine.capture("p1", ("second line",))
    replay = engine.replay("p1")
    assert replay is not None
    assert len(replay) == 2
    assert "[0]" in replay[0]
    assert "[1]" in replay[1]


# ------------------------------------------------------------------
# serialize / deserialize
# ------------------------------------------------------------------


def test_serialize_roundtrip(engine: SnapshotEngine) -> None:
    snap = Snapshot(pane_id="p1", lines=("a", "b"), cursor_row=1, cursor_col=1)
    raw = engine.serialize_snapshot(snap)
    restored = engine.deserialize_snapshot(raw)
    assert restored.pane_id == snap.pane_id
    assert restored.lines == snap.lines
    assert restored.cursor_row == snap.cursor_row
    assert restored.cursor_col == snap.cursor_col


def test_serialize_valid_json(engine: SnapshotEngine) -> None:
    snap = Snapshot(pane_id="p", lines=("x",))
    raw = engine.serialize_snapshot(snap)
    parsed = json.loads(raw)
    assert parsed["pane_id"] == "p"
    assert parsed["lines"] == ["x"]


# ------------------------------------------------------------------
# save / load
# ------------------------------------------------------------------


def test_save_and_load(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("snapshot1",))
    engine.capture("p1", ("snapshot2",))

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name

    try:
        written = engine.save(path=path)
        assert written == path

        engine2 = SnapshotEngine()
        count = engine2.load(path=path)
        assert count == 2
        assert engine2.snapshot_count("p1") == 2
    finally:
        os.unlink(path)


def test_load_nonexistent(engine: SnapshotEngine) -> None:
    count = engine.load("/nonexistent/path.json")
    assert count == 0


# ------------------------------------------------------------------
# history / clear / count
# ------------------------------------------------------------------


def test_history(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("a",))
    engine.capture("p1", ("b",))
    engine.capture("p1", ("c",))
    hist = engine.history("p1")
    assert len(hist) == 3


def test_history_limit(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("a",))
    engine.capture("p1", ("b",))
    engine.capture("p1", ("c",))
    hist = engine.history("p1", limit=2)
    assert len(hist) == 2


def test_clear_pane(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("a",))
    engine.capture("p2", ("b",))
    engine.clear("p1")
    assert engine.snapshot_count("p1") == 0
    assert engine.snapshot_count("p2") == 1


def test_clear_all(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("a",))
    engine.capture("p2", ("b",))
    engine.clear()
    assert engine.snapshot_count() == 0


def test_count_total(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("a",))
    engine.capture("p1", ("b",))
    engine.capture("p2", ("c",))
    assert engine.snapshot_count() == 3


def test_count_pane(engine: SnapshotEngine) -> None:
    engine.capture("p1", ("a",))
    assert engine.snapshot_count("p1") == 1
    assert engine.snapshot_count("p2") == 0

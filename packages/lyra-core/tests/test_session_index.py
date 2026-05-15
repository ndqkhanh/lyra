"""v3.13 P0-1 — index-first session-resume surface.

Covers :mod:`lyra_core.memory.session_index`, the progressive-
disclosure layer stolen from ``thedotmack/claude-mem``. Both
backends are exercised:

* The in-memory :class:`ReasoningBank` (fast unit-test path; no
  filesystem, no timestamps).
* The :class:`SqliteReasoningBank` (production path; real
  ``inserted_at`` rendering, real anchor-by-time timeline).

The tests target the *contract* documented in the v2
context-engineering report:

* Index rows are tiny — no bodies.
* The rendered table fits inside ``max_bytes`` and ends with the
  steer-the-agent footer.
* Search returns rows only, falls back to recency on empty query.
* Timeline returns chronological neighbours and is empty for an
  unknown anchor.
* ``get_observation`` is the *one* call that returns the full body.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from lyra_core.memory.reasoning_bank import (
    Lesson,
    ReasoningBank,
    Trajectory,
    TrajectoryOutcome,
)
from lyra_core.memory.reasoning_bank_store import SqliteReasoningBank
from lyra_core.memory.session_index import (
    IndexRow,
    get_observation,
    index_rows,
    render_session_index,
    search_index,
    timeline_around,
)


# --- shared fixtures ------------------------------------------------------ #


class _NoopDistiller:
    """Distiller stub that yields nothing — every test seeds lessons
    directly via ``record_lesson``. Returns a ``Sequence[Lesson]``
    to satisfy the ``Distiller`` protocol exactly."""

    def distill(self, trajectory: Trajectory) -> tuple[Lesson, ...]:
        del trajectory  # unused — stub satisfies protocol shape only
        return ()


def _lesson(
    lid: str,
    *,
    polarity: TrajectoryOutcome = TrajectoryOutcome.SUCCESS,
    title: str = "Test lesson",
    body: str = "x" * 200,
    sigs: tuple[str, ...] = ("python", "testing"),
) -> Lesson:
    return Lesson(
        id=lid,
        polarity=polarity,
        title=title,
        body=body,
        task_signatures=sigs,
        source_trajectory_ids=(f"traj-{lid}",),
    )


@pytest.fixture
def mem_bank() -> ReasoningBank:
    """In-memory bank seeded with 4 lessons (2 success / 2 failure)."""
    bank = ReasoningBank(distiller=_NoopDistiller())
    bank.record_lesson(_lesson("a", title="Always validate user input"))
    bank.record_lesson(
        _lesson(
            "b",
            polarity=TrajectoryOutcome.FAILURE,
            title="Did not unmount listener on cleanup",
        )
    )
    bank.record_lesson(_lesson("c", title="Use bisect for sorted insertion"))
    bank.record_lesson(
        _lesson(
            "d",
            polarity=TrajectoryOutcome.FAILURE,
            title="String concat in tight loop is O(N²)",
        )
    )
    return bank


@pytest.fixture
def sqlite_bank(tmp_path: Path) -> SqliteReasoningBank:
    """SQLite bank seeded with 4 lessons; uses real julianday timestamps."""
    db = tmp_path / "reasoning_bank.sqlite"
    bank = SqliteReasoningBank(distiller=_NoopDistiller(), db_path=db)
    bank.record_lesson(_lesson("a", title="Always validate user input"))
    bank.record_lesson(
        _lesson(
            "b",
            polarity=TrajectoryOutcome.FAILURE,
            title="Did not unmount listener on cleanup",
        )
    )
    bank.record_lesson(_lesson("c", title="Use bisect for sorted insertion"))
    bank.record_lesson(
        _lesson(
            "d",
            polarity=TrajectoryOutcome.FAILURE,
            title="String concat in tight loop is O(N²)",
        )
    )
    return bank


# --- IndexRow shape ------------------------------------------------------- #


class TestIndexRowShape:
    def test_rows_carry_no_body(self, mem_bank: ReasoningBank) -> None:
        rows = index_rows(mem_bank)
        for r in rows:
            # The dataclass must not even have a ``body`` attribute
            # — leaking it would defeat the whole point.
            assert not hasattr(r, "body")

    def test_rows_carry_token_estimate(self, mem_bank: ReasoningBank) -> None:
        rows = index_rows(mem_bank)
        # Every seeded lesson has a 200-char body; rough chars/4 → 50.
        for r in rows:
            assert r.body_tokens == 50

    def test_rows_carry_polarity_emoji(self, mem_bank: ReasoningBank) -> None:
        rows = index_rows(mem_bank)
        by_id = {r.id: r for r in rows}
        assert by_id["a"].type_emoji == "🟢"  # success
        assert by_id["b"].type_emoji == "🔴"  # failure

    def test_title_truncates_long_strings(self) -> None:
        bank = ReasoningBank(distiller=_NoopDistiller())
        bank.record_lesson(_lesson("x", title="A" * 200))
        rows = index_rows(bank)
        assert len(rows[0].title) <= 60
        assert rows[0].title.endswith("…")


# --- render_session_index ------------------------------------------------- #


class TestRenderSessionIndex:
    def test_empty_bank_returns_stub(self) -> None:
        bank = ReasoningBank(distiller=_NoopDistiller())
        out = render_session_index(bank)
        assert "no past lessons" in out

    def test_includes_header_and_footer(self, mem_bank: ReasoningBank) -> None:
        out = render_session_index(mem_bank)
        assert "| ID | Ago | T | Title | Tok |" in out
        # Footer steers the model into the right workflow.
        assert "fetch a full lesson" in out
        assert "10x token savings" in out

    def test_respects_max_bytes(self, mem_bank: ReasoningBank) -> None:
        # 4 rows at ~80 bytes each would clear 200B easily; cap to
        # 200 bytes and verify we drop rows rather than overflowing.
        out = render_session_index(mem_bank, max_bytes=200)
        assert len(out) <= 200

    def test_default_under_1kb(self, mem_bank: ReasoningBank) -> None:
        out = render_session_index(mem_bank)
        assert len(out) <= 1024

    def test_lists_lesson_ids_truncated(self, mem_bank: ReasoningBank) -> None:
        out = render_session_index(mem_bank)
        # IDs are short here so all four should appear.
        for lid in ("a", "b", "c", "d"):
            assert f"`{lid}`" in out

    def test_sqlite_path_renders_real_ago_string(
        self, sqlite_bank: SqliteReasoningBank
    ) -> None:
        out = render_session_index(sqlite_bank)
        # Right after insertion, every lesson should be < 60s old.
        # Possible values: "0s".."59s".
        assert any(f"{n}s" in out for n in range(0, 60))


# --- search_index --------------------------------------------------------- #


class TestSearchIndex:
    def test_returns_rows_only(self, mem_bank: ReasoningBank) -> None:
        rows = search_index(mem_bank, query="python")
        assert all(isinstance(r, IndexRow) for r in rows)

    def test_empty_query_falls_back_to_recency(
        self, mem_bank: ReasoningBank
    ) -> None:
        # Should match what index_rows returns (most-recent first).
        rows = search_index(mem_bank, query="")
        idx = index_rows(mem_bank)
        assert rows == idx

    def test_polarity_filter(self, mem_bank: ReasoningBank) -> None:
        rows = search_index(
            mem_bank, query="python",
            polarity=TrajectoryOutcome.FAILURE,
        )
        # All seeded lessons share signatures ("python", "testing")
        # so a python-match returns hits filtered by polarity.
        assert all(r.type_emoji == "🔴" for r in rows)


# --- timeline_around ------------------------------------------------------ #


class TestTimelineAround:
    def test_unknown_anchor_returns_empty(
        self, mem_bank: ReasoningBank
    ) -> None:
        assert timeline_around(mem_bank, "nope") == ()

    def test_returns_chronological_neighbours(
        self, mem_bank: ReasoningBank
    ) -> None:
        rows = timeline_around(mem_bank, "c", window=1)
        ids = [r.id for r in rows]
        # ``mem_bank`` seeded order: a, b, c, d. window=1 → b, c, d.
        assert ids == ["b", "c", "d"]

    def test_sqlite_path_orders_by_inserted_at(
        self, sqlite_bank: SqliteReasoningBank
    ) -> None:
        rows = timeline_around(sqlite_bank, "c", window=2)
        ids = [r.id for r in rows]
        assert "c" in ids
        # Anchor sits in the middle of the window (or at the edge
        # when the bank ran out of neighbours on one side).
        assert ids.index("c") in (1, 2)


# --- get_observation ------------------------------------------------------ #


class TestGetObservation:
    def test_returns_full_body(self, mem_bank: ReasoningBank) -> None:
        lesson = get_observation(mem_bank, "a")
        assert lesson is not None
        assert lesson.body == "x" * 200
        assert lesson.title == "Always validate user input"

    def test_unknown_id_returns_none(self, mem_bank: ReasoningBank) -> None:
        assert get_observation(mem_bank, "nope") is None

    def test_sqlite_path_returns_full_body(
        self, sqlite_bank: SqliteReasoningBank
    ) -> None:
        lesson = get_observation(sqlite_bank, "a")
        assert lesson is not None
        assert lesson.body == "x" * 200
        # SQLite store also hydrates signatures + trajectory ids.
        assert lesson.task_signatures == ("python", "testing")
        assert lesson.source_trajectory_ids == ("traj-a",)


# --- bank parity ---------------------------------------------------------- #


def test_in_memory_bank_has_all_lessons() -> None:
    """v3.13 added ``all_lessons`` to the in-memory bank for parity
    with the SQLite store. Regression-guard the surface."""
    bank = ReasoningBank(distiller=_NoopDistiller())
    bank.record_lesson(_lesson("x", title="T1"))
    bank.record_lesson(_lesson("y", title="T2"))
    lessons = bank.all_lessons()
    # Most-recent-first ordering matches SQLite.
    assert [l.id for l in lessons] == ["y", "x"]


def test_in_memory_all_lessons_filters_polarity() -> None:
    bank = ReasoningBank(distiller=_NoopDistiller())
    bank.record_lesson(_lesson("ok", polarity=TrajectoryOutcome.SUCCESS))
    bank.record_lesson(_lesson("err", polarity=TrajectoryOutcome.FAILURE))
    only_fail = bank.all_lessons(polarity=TrajectoryOutcome.FAILURE)
    assert [l.id for l in only_fail] == ["err"]

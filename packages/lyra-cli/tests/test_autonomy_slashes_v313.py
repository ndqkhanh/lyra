"""v3.13 — autonomy-slash REPL surface.

Covers the four new slashes that wire the v3.12 autonomy substrate
(``lyra_core.contracts``, ``lyra_core.loops.{directive,store}``) into the
interactive REPL:

* ``/directive`` — append to ``HUMAN_DIRECTIVE.md``
* ``/contract`` — show / set the ``AgentContract`` budget envelope
* ``/autopilot`` — list supervised loops from the SQLite ``LoopStore``
* ``/continue`` — queue an explicit re-feed onto ``pending_task``

Each test seam isolates filesystem state with ``tmp_path`` + ``LYRA_HOME``
so dev-box artefacts can't leak in.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# --- shared helpers -------------------------------------------------------- #


def _make_session(tmp_path: Path, session_id: str = "s-test"):
    """Minimal InteractiveSession-shaped object for handler tests.

    The real InteractiveSession is heavyweight; the v3.13 slashes only
    touch ``session_id`` and ``pending_task``, so a dataclass-light
    stub keeps tests fast and decoupled from REPL bring-up.
    """
    class _S:
        pass

    s = _S()
    s.session_id = session_id
    s.pending_task = None
    return s


# --- /directive ----------------------------------------------------------- #


class TestCmdDirective:
    def test_writes_to_human_directive(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_directive

        s = _make_session(tmp_path)
        res = _cmd_directive(s, "switch to a slower model after 5 iterations")

        live = tmp_path / "loops" / "s-test" / "HUMAN_DIRECTIVE.md"
        assert live.exists()
        assert "switch to a slower model" in live.read_text()
        assert "directive appended" in res.output

    def test_empty_args_lists_archive(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_directive

        s = _make_session(tmp_path)
        # First call writes nothing (no archive yet).
        res = _cmd_directive(s, "")
        assert "no archived directives" in res.output

    def test_appends_not_overwrites(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_directive

        s = _make_session(tmp_path)
        _cmd_directive(s, "first")
        _cmd_directive(s, "second")

        live = tmp_path / "loops" / "s-test" / "HUMAN_DIRECTIVE.md"
        body = live.read_text()
        assert "first" in body
        assert "second" in body

    def test_session_id_namespaces_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_directive

        a = _make_session(tmp_path, session_id="sess-A")
        b = _make_session(tmp_path, session_id="sess-B")
        _cmd_directive(a, "for A")
        _cmd_directive(b, "for B")

        assert (tmp_path / "loops" / "sess-A" / "HUMAN_DIRECTIVE.md").exists()
        assert (tmp_path / "loops" / "sess-B" / "HUMAN_DIRECTIVE.md").exists()


# --- /contract ------------------------------------------------------------ #


class TestCmdContract:
    def test_show_default_unbounded(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_contract

        s = _make_session(tmp_path)
        res = _cmd_contract(s, "show")

        assert "contract state:" in res.output
        assert "pending" in res.output
        assert "(unbounded)" in res.output

    def test_set_max_usd(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_contract

        s = _make_session(tmp_path)
        res = _cmd_contract(s, "set max_usd=2.50")
        assert "contract.budget.max_usd = 2.5" in res.output

        # subsequent show reflects the set
        out = _cmd_contract(s, "show").output
        assert "budget.max_usd:   2.5" in out

    def test_set_max_iterations(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_contract

        s = _make_session(tmp_path)
        _cmd_contract(s, "set max_iterations=50")
        out = _cmd_contract(s, "show").output
        assert "budget.max_iter:  50" in out

    def test_set_unknown_key_rejected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_contract

        s = _make_session(tmp_path)
        res = _cmd_contract(s, "set frobnicate=42")
        assert "unknown key" in res.output

    def test_set_non_numeric_rejected(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_contract

        s = _make_session(tmp_path)
        res = _cmd_contract(s, "set max_usd=cheap")
        assert "is not a number" in res.output

    def test_set_composes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Successive sets must preserve earlier fields."""
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_contract

        s = _make_session(tmp_path)
        _cmd_contract(s, "set max_usd=1.00")
        _cmd_contract(s, "set max_iterations=10")
        out = _cmd_contract(s, "show").output
        assert "budget.max_usd:   1.0" in out
        assert "budget.max_iter:  10" in out


# --- /autopilot ----------------------------------------------------------- #


class TestCmdAutopilot:
    def test_no_store_yet(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_autopilot

        s = _make_session(tmp_path)
        res = _cmd_autopilot(s, "status")
        assert "no autopilot store" in res.output

    def test_status_lists_running_loops(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_autopilot
        from lyra_core.loops.store import LoopRecord, LoopStore

        db = tmp_path / "loops" / "loops.sqlite"
        db.parent.mkdir(parents=True, exist_ok=True)
        store = LoopStore(db_path=db)
        store.upsert(
            LoopRecord(
                id="lp-1",
                kind="ralph",
                state="running",
                run_dir=str(tmp_path / "loops" / "lp-1"),
                created_at=0.0,
                updated_at=0.0,
                cum_usd=0.42,
                iter_count=3,
            )
        )

        s = _make_session(tmp_path)
        res = _cmd_autopilot(s, "status")
        assert "1 running loop" in res.output
        assert "lp-1" in res.output
        assert "iter=3" in res.output

    def test_status_no_running_when_only_completed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("LYRA_HOME", str(tmp_path))
        from lyra_cli.interactive.session import _cmd_autopilot
        from lyra_core.loops.store import LoopRecord, LoopStore

        db = tmp_path / "loops" / "loops.sqlite"
        db.parent.mkdir(parents=True, exist_ok=True)
        store = LoopStore(db_path=db)
        store.upsert(
            LoopRecord(
                id="lp-old",
                kind="ralph",
                state="completed",
                run_dir=str(tmp_path / "loops" / "lp-old"),
                created_at=0.0,
                updated_at=0.0,
            )
        )

        s = _make_session(tmp_path)
        assert "no running loops" in _cmd_autopilot(s, "status").output
        # but `list` shows it
        assert "lp-old" in _cmd_autopilot(s, "list").output


# --- /continue ------------------------------------------------------------ #


class TestCmdContinue:
    def test_queues_pending_task(self, tmp_path: Path) -> None:
        from lyra_cli.interactive.session import _cmd_continue

        s = _make_session(tmp_path)
        res = _cmd_continue(s, "")
        assert s.pending_task == "continue"
        assert "queued" in res.output

    def test_custom_followup(self, tmp_path: Path) -> None:
        from lyra_cli.interactive.session import _cmd_continue

        s = _make_session(tmp_path)
        _cmd_continue(s, "now run the tests")
        assert s.pending_task == "now run the tests"

    def test_refuses_double_queue(self, tmp_path: Path) -> None:
        from lyra_cli.interactive.session import _cmd_continue

        s = _make_session(tmp_path)
        s.pending_task = "earlier"
        res = _cmd_continue(s, "later")
        assert "already queued" in res.output
        assert s.pending_task == "earlier"


# --- registry sanity ----------------------------------------------------- #


def test_v313_slashes_registered() -> None:
    from lyra_cli.interactive.session import COMMAND_REGISTRY

    names = {c.name for c in COMMAND_REGISTRY}
    for n in ("directive", "contract", "autopilot", "continue"):
        assert n in names, f"slash /{n} not registered"


def test_v313_slashes_have_args_hint() -> None:
    from lyra_cli.interactive.session import COMMAND_REGISTRY

    by_name = {c.name: c for c in COMMAND_REGISTRY}
    for n in ("directive", "contract", "autopilot", "continue"):
        spec = by_name[n]
        assert spec.args_hint, f"/{n} missing args_hint"
        assert spec.category == "tools-agents"

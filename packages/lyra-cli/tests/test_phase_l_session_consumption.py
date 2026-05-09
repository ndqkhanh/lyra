"""Phase L (v3.2.0) — session consumption tests.

Covers the user-facing surface added in v3.2:

* Per-turn metadata roundtrip (``_TurnSnapshot`` ↔ ``turns.jsonl``)
* ``lyra session list`` / ``lyra session show`` text + JSON output
* ``lyra --resume <id>`` / ``--continue`` / ``--session ID``
* ``/history --verbose`` rendering

Tests are *behavioural* — they exercise the public CLI surface via
``CliRunner`` and the slash commands via the same dispatch table the
REPL uses. No mocks of internal collaborators; the only seam we touch
is the test fixture's ``LYRA_HOME`` / cwd isolation (autouse from
:mod:`tests.conftest`). That keeps the suite robust against
implementation refactors (e.g. swapping the JSONL layout for SQLite
later — the tests would still pass as long as the CLI surface stays
the same).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lyra_cli.__main__ import app
from lyra_cli.interactive.session import (
    InteractiveSession,
    _TurnSnapshot,
    _resolve_session_reference,
)


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _seed_session(
    repo_root: Path,
    session_id: str,
    *,
    rows: list[dict] | None = None,
    name: str | None = None,
    forked_from: str | None = None,
) -> Path:
    """Write a synthetic ``turns.jsonl`` + ``meta.json`` under the repo.

    Returns the session directory. Used to fabricate sessions without
    spinning up the full REPL — keeps the tests deterministic and fast.
    """
    sd = repo_root / ".lyra" / "sessions" / session_id
    sd.mkdir(parents=True, exist_ok=True)
    if rows is None:
        rows = [
            {
                "kind": "turn",
                "line": "hello",
                "mode": "agent",
                "turn": 1,
                "pending_task": None,
                "cost_usd": 0.001,
                "tokens_used": 50,
                "model": "deepseek-flash",
                "ts": time.time(),
                "tokens_in": 30,
                "tokens_out": 20,
                "cost_delta_usd": 0.001,
                "latency_ms": 250.0,
            },
            {
                "kind": "chat",
                "user": "hello",
                "assistant": "hi there",
                "model": "deepseek-flash",
                "ts": time.time(),
                "tokens_in": 30,
                "tokens_out": 20,
                "cost_delta_usd": 0.001,
                "latency_ms": 250.0,
            },
        ]
    log = sd / "turns.jsonl"
    with log.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    meta: dict[str, object] = {
        "session_id": session_id,
        "created_at": "2026-04-27T13:00:00",
    }
    if name:
        meta["name"] = name
    if forked_from:
        meta["forked_from"] = forked_from
    (sd / "meta.json").write_text(json.dumps(meta, indent=2))
    return sd


# ---------------------------------------------------------------------
# _TurnSnapshot enrichment (L.3)
# ---------------------------------------------------------------------


def test_turn_snapshot_carries_new_optional_fields() -> None:
    """v3.2: snapshot has model/ts/tokens_in/tokens_out/cost_delta/latency_ms."""
    snap = _TurnSnapshot(
        line="x",
        mode="agent",
        turn=1,
        pending_task=None,
        cost_usd=0.0,
        tokens_used=0,
    )
    # All defaults are None — back-compat with pre-v3.2 callers.
    assert snap.model is None
    assert snap.ts is None
    assert snap.tokens_in is None
    assert snap.tokens_out is None
    assert snap.cost_delta_usd is None
    assert snap.latency_ms is None

    enriched = _TurnSnapshot(
        line="y",
        mode="plan",
        turn=2,
        pending_task=None,
        cost_usd=0.5,
        tokens_used=100,
        model="deepseek-pro",
        ts=1700000000.0,
        tokens_in=60,
        tokens_out=40,
        cost_delta_usd=0.001,
        latency_ms=420.0,
    )
    assert enriched.model == "deepseek-pro"
    assert enriched.ts == 1700000000.0
    assert enriched.tokens_in == 60
    assert enriched.tokens_out == 40
    assert enriched.cost_delta_usd == pytest.approx(0.001)
    assert enriched.latency_ms == pytest.approx(420.0)


def test_persist_turn_writes_optional_fields_only_when_set(
    tmp_path: Path,
) -> None:
    """Old turns omit the new keys; enriched ones include them."""
    s = InteractiveSession(
        repo_root=tmp_path,
        model="auto",
        sessions_root=tmp_path / ".lyra" / "sessions",
        session_id="s1",
    )
    bare = _TurnSnapshot(
        line="bare",
        mode="agent",
        turn=1,
        pending_task=None,
        cost_usd=0.0,
        tokens_used=0,
    )
    rich = _TurnSnapshot(
        line="rich",
        mode="agent",
        turn=2,
        pending_task=None,
        cost_usd=0.001,
        tokens_used=10,
        model="deepseek-flash",
        ts=1700000123.5,
        tokens_in=5,
        tokens_out=5,
        cost_delta_usd=0.001,
        latency_ms=12.5,
    )
    s._persist_turn(bare)
    s._persist_turn(rich)

    log = (tmp_path / ".lyra" / "sessions" / "s1" / "turns.jsonl").read_text()
    rows = [json.loads(line) for line in log.splitlines() if line.strip()]
    assert len(rows) == 2

    # Bare row must NOT have the optional v3.2 keys at all (back-compat).
    for k in ("model", "ts", "tokens_in", "tokens_out",
              "cost_delta_usd", "latency_ms"):
        assert k not in rows[0], f"unexpected {k!r} in bare row"

    # Rich row carries every new field.
    assert rows[1]["model"] == "deepseek-flash"
    assert rows[1]["ts"] == pytest.approx(1700000123.5)
    assert rows[1]["tokens_in"] == 5
    assert rows[1]["tokens_out"] == 5
    assert rows[1]["cost_delta_usd"] == pytest.approx(0.001)
    assert rows[1]["latency_ms"] == pytest.approx(12.5)


def test_persist_turn_bootstraps_meta_json_with_created_at(
    tmp_path: Path,
) -> None:
    """First write should drop a meta.json so ``session show`` always
    has ``created_at`` (Phase L UX)."""
    s = InteractiveSession(
        repo_root=tmp_path,
        model="auto",
        sessions_root=tmp_path / ".lyra" / "sessions",
        session_id="s2",
    )
    snap = _TurnSnapshot(
        line="x",
        mode="agent",
        turn=1,
        pending_task=None,
        cost_usd=0.0,
        tokens_used=0,
    )
    s._persist_turn(snap)
    meta = json.loads(
        (tmp_path / ".lyra" / "sessions" / "s2" / "meta.json").read_text()
    )
    assert meta["session_id"] == "s2"
    assert isinstance(meta["created_at"], str)
    # Idempotent — second write must not stomp on the recorded value.
    original = meta["created_at"]
    time.sleep(0.01)
    s._persist_turn(snap)
    again = json.loads(
        (tmp_path / ".lyra" / "sessions" / "s2" / "meta.json").read_text()
    )
    assert again["created_at"] == original


# ---------------------------------------------------------------------
# resume / continue / session ID resolution (L.9)
# ---------------------------------------------------------------------


def test_resolve_session_reference_latest_picks_most_recent(
    tmp_path: Path,
) -> None:
    """``latest`` returns the most recently modified session id."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    older = _seed_session(tmp_path, "older")
    time.sleep(0.05)
    newer = _seed_session(tmp_path, "newer")
    # Force mtime ordering even on coarse filesystems.
    import os

    os.utime(older / "turns.jsonl", (1, 1))
    os.utime(newer / "turns.jsonl", (2, 2))

    target = _resolve_session_reference("latest", sessions_root, fallback="x")
    assert target == "newer"


def test_resolve_session_reference_unique_prefix_match(tmp_path: Path) -> None:
    """A unique id-prefix resolves; an ambiguous one returns the
    raw reference so the caller's "no such session" path can list
    the candidates."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    _seed_session(tmp_path, "abc-001")
    _seed_session(tmp_path, "xyz-999")

    target = _resolve_session_reference("abc", sessions_root, fallback="X")
    assert target == "abc-001"

    # Ambiguous prefix → original reference unchanged; the caller
    # then prints "unknown session: 'abc'" and lists available ids.
    _seed_session(tmp_path, "abc-002")
    target = _resolve_session_reference("abc", sessions_root, fallback="FB")
    assert target == "abc"


def test_resolve_session_reference_latest_with_empty_dir_returns_fallback(
    tmp_path: Path,
) -> None:
    """``latest`` with no sessions on disk → fallback (so the caller
    can show ``no such session: '<live-id>'`` rather than crash)."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    target = _resolve_session_reference(
        "latest", sessions_root, fallback="LIVE-ID"
    )
    assert target == "LIVE-ID"


# ---------------------------------------------------------------------
# `lyra session list` / `lyra session show` (L.5 + L.6)
# ---------------------------------------------------------------------


def test_session_list_text_shows_recency_msgs_mode_model(tmp_path: Path) -> None:
    """The new ``lyra session list`` shows mode + model + msgs columns."""
    _seed_session(tmp_path, "alpha")
    _seed_session(
        tmp_path,
        "beta",
        rows=[
            {
                "kind": "turn",
                "line": "hi",
                "mode": "plan",
                "turn": 1,
                "pending_task": None,
                "cost_usd": 0.002,
                "tokens_used": 75,
                "model": "deepseek-pro",
                "ts": time.time(),
            }
        ],
    )

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["session", "list", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    out = result.output
    # Recency-sorted, newest-first; both ids show up.
    assert "alpha" in out
    assert "beta" in out
    # Mode + model columns rendered.
    assert "agent" in out or "plan" in out
    assert "deepseek-flash" in out or "deepseek-pro" in out


def test_session_list_json_emits_structured_payload(tmp_path: Path) -> None:
    _seed_session(tmp_path, "gamma", name="rename-me")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["session", "list", "--repo-root", str(tmp_path), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert len(payload) == 1
    row = payload[0]
    for k in (
        "session_id",
        "name",
        "msgs",
        "turns",
        "modified_unix",
        "modified_iso",
        "mode",
        "model",
        "cost_usd",
        "tokens",
        "path",
    ):
        assert k in row, f"missing key: {k!r}"
    assert row["session_id"] == "gamma"
    assert row["name"] == "rename-me"


def test_session_list_empty_dir_prints_friendly_hint(tmp_path: Path) -> None:
    """Zero sessions → no traceback, friendly hint instead."""
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["session", "list", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "no sessions yet" in result.output or "lyra --continue" in result.output


def test_session_show_resolves_latest_and_prints_manifest(tmp_path: Path) -> None:
    _seed_session(tmp_path, "delta-001")
    _seed_session(tmp_path, "delta-002")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["session", "show", "latest", "--repo-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    out = result.output
    # Manifest rows we promise in the spec.
    for label in ("repo", "path", "modified", "mode", "model", "turns", "msgs", "cost"):
        assert label in out, f"missing manifest label: {label!r}"


def test_session_show_unique_prefix_resolves(tmp_path: Path) -> None:
    _seed_session(tmp_path, "epsilon-aaa")
    _seed_session(tmp_path, "zeta-bbb")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["session", "show", "eps", "--repo-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert "epsilon-aaa" in result.output


def test_session_show_unknown_id_exits_nonzero_with_hint(tmp_path: Path) -> None:
    _seed_session(tmp_path, "eta-001")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["session", "show", "nope", "--repo-root", str(tmp_path)],
    )
    assert result.exit_code != 0
    # Prints unknown-session diagnostic + lists available ids.
    assert "unknown session" in result.output
    assert "eta-001" in result.output


def test_session_show_verbose_walks_jsonl(tmp_path: Path) -> None:
    _seed_session(tmp_path, "theta")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [
            "session",
            "show",
            "theta",
            "--repo-root",
            str(tmp_path),
            "--verbose",
        ],
    )
    assert result.exit_code == 0, result.output
    out = result.output
    assert "turn-by-turn breakdown" in out
    assert "deepseek-flash" in out


def test_session_show_json_includes_events_when_verbose(tmp_path: Path) -> None:
    _seed_session(tmp_path, "iota")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [
            "session",
            "show",
            "iota",
            "--repo-root",
            str(tmp_path),
            "--json",
            "--verbose",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["session_id"] == "iota"
    assert "events" in payload
    assert len(payload["events"]) == 2  # turn + chat


# ---------------------------------------------------------------------
# `--resume / --continue / --session` (L.4)
# ---------------------------------------------------------------------


def test_root_callback_continue_maps_to_latest(tmp_path: Path, monkeypatch) -> None:
    """``lyra --continue`` should pass ``resume_id="latest"`` to driver.run."""
    _seed_session(tmp_path, "kappa")

    captured: dict[str, object] = {}

    def fake_run(**kw):
        captured.update(kw)
        return 0

    import lyra_cli.interactive.driver as drv

    monkeypatch.setattr(drv, "run", fake_run)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["--repo-root", str(tmp_path), "--continue"],
    )
    assert result.exit_code == 0, result.output
    assert captured["resume_id"] == "latest"
    assert captured["pin_session_id"] is None


def test_root_callback_resume_id_passed_through(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(**kw):
        captured.update(kw)
        return 0

    import lyra_cli.interactive.driver as drv

    monkeypatch.setattr(drv, "run", fake_run)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["--repo-root", str(tmp_path), "--resume", "abc-123"],
    )
    assert result.exit_code == 0, result.output
    assert captured["resume_id"] == "abc-123"


def test_root_callback_session_pins_id(tmp_path: Path, monkeypatch) -> None:
    """``--session ID`` sets *both* resume_id and pin_session_id so the
    REPL resumes when the id exists OR creates a fresh session pinned
    to that id when it doesn't."""
    captured: dict[str, object] = {}

    def fake_run(**kw):
        captured.update(kw)
        return 0

    import lyra_cli.interactive.driver as drv

    monkeypatch.setattr(drv, "run", fake_run)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        ["--repo-root", str(tmp_path), "--session", "pin-me"],
    )
    assert result.exit_code == 0, result.output
    assert captured["resume_id"] == "pin-me"
    assert captured["pin_session_id"] == "pin-me"


# ---------------------------------------------------------------------
# `/history --verbose` (L.8)
# ---------------------------------------------------------------------


def test_history_verbose_prints_per_turn_metrics() -> None:
    """``/history --verbose`` walks ``_turns_log`` and prints model/ms/cost."""
    from lyra_cli.interactive.session import _cmd_history

    s = InteractiveSession(repo_root=Path("/tmp"), model="auto")
    s.history = ["hello", "world"]
    s._turns_log = [
        _TurnSnapshot(
            line="hello",
            mode="agent",
            turn=1,
            pending_task=None,
            cost_usd=0.001,
            tokens_used=50,
            model="deepseek-flash",
            ts=1700000000.0,
            tokens_in=30,
            tokens_out=20,
            cost_delta_usd=0.001,
            latency_ms=250.0,
        ),
    ]
    res = _cmd_history(s, "--verbose")
    text = res.output
    # Plain-text mirror so non-TTY still gets the data.
    assert "deepseek-flash" in text
    assert "in=30" in text
    assert "out=20" in text
    # Cost line is formatted with $.
    assert "cost=$" in text


def test_history_concise_mode_unchanged() -> None:
    """Without ``--verbose`` the existing numbered-list output stays put."""
    from lyra_cli.interactive.session import _cmd_history

    s = InteractiveSession(repo_root=Path("/tmp"), model="auto")
    s.history = ["one", "two", "three"]
    res = _cmd_history(s, "")
    assert "one" in res.output and "two" in res.output and "three" in res.output
    # No cost / token columns when not verbose.
    assert "cost=" not in res.output

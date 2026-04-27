"""Tests for the new feature wave inspired by Claude Code, sst/opencode,
and Hermes Agent.

Scope (one test file so it's easy to run together):

- Expanded mode set: ``plan``, ``build``, ``run``, ``explore``, ``retro``.
- New slash commands: /compact /context /cost /stats /diff /export
  /rewind /resume /fork /sessions /rename /theme /vim /keybindings
  /tools /agents /spawn /mcp /map /blame /trace /self /badges /budget
  /btw /handoff /pair /wiki /effort /ultrareview /review /tdd-gate
  /models.
- Tool registry scaffold (``lyra_cli.interactive.tools``).
- Session persistence (``lyra_cli.interactive.store``).
- HIR JSONL event logger (``lyra_cli.interactive.hir``).
- Multi-prefix completer (``@file``, ``#skill``).
- Theme palettes (``lyra_cli.interactive.themes``).

Tests assert on the plain-text ``output`` channel (so they remain TTY-
free) and additionally check that the ``renderable`` slot is populated
for every command users can look at — that's the dual-channel contract
documented in :mod:`lyra_cli.interactive.session`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.interactive import hir as hir_mod
from lyra_cli.interactive import store as store_mod
from lyra_cli.interactive import themes
from lyra_cli.interactive.completer import (
    SlashCompleter,
    _last_token,
    _walk_repo,
)
from lyra_cli.interactive.session import (
    SLASH_COMMANDS,
    InteractiveSession,
    _MODE_CYCLE,
    _VALID_MODES,
)
from lyra_cli.interactive.tools import (
    registered_tools,
    tool_by_name,
    tools_of_risk,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(
        repo_root=tmp_path,
        model="claude-opus-4.7",
    )


# ---------------------------------------------------------------------------
# Mode taxonomy (v3.2.0 Claude-Code 4-mode set: agent / plan / debug / ask)
# ---------------------------------------------------------------------------


def test_mode_set_is_the_claude_code_four() -> None:
    assert set(_VALID_MODES) == {"agent", "plan", "debug", "ask"}


@pytest.mark.parametrize("mode", ["agent", "plan", "debug", "ask"])
def test_each_mode_has_a_handler(
    session: InteractiveSession, mode: str
) -> None:
    """Every valid mode must accept plain text without raising."""
    session.mode = mode
    result = session.dispatch("look at logging.py")
    assert result.renderable is not None
    assert mode in result.output.lower()


def test_mode_cycle_order_matches_documented_sequence() -> None:
    # v3.2.0: Tab cycle is ``agent → plan → ask → debug`` so the two
    # execution-capable modes (agent, debug) sit at opposite ends and
    # a single Tab press never accidentally toggles between them.
    assert _MODE_CYCLE == ("agent", "plan", "ask", "debug")


def test_slash_mode_accepts_agent(session: InteractiveSession) -> None:
    result = session.dispatch("/mode agent")
    assert session.mode == "agent"
    assert result.new_mode == "agent"


def test_slash_mode_accepts_ask(session: InteractiveSession) -> None:
    result = session.dispatch("/mode ask")
    assert session.mode == "ask"
    assert result.new_mode == "ask"


def test_slash_mode_accepts_legacy_build_alias(session: InteractiveSession) -> None:
    """v1.x / v2.x ``build`` muscle memory still works — remaps to ``agent``."""
    result = session.dispatch("/mode build")
    assert session.mode == "agent"
    assert result.new_mode == "agent"


def test_slash_mode_accepts_legacy_explore_alias(session: InteractiveSession) -> None:
    """v1.x / v2.x ``explore`` muscle memory still works — remaps to ``ask``."""
    result = session.dispatch("/mode explore")
    assert session.mode == "ask"
    assert result.new_mode == "ask"


# ---------------------------------------------------------------------------
# New slash commands — every one must be registered + ship a renderable
# ---------------------------------------------------------------------------


_NEW_COMMANDS_NO_ARGS: tuple[str, ...] = (
    "/compact",
    "/context",
    "/cost",
    "/stats",
    "/diff",
    "/keybindings",
    "/tools",
    "/agents",
    "/mcp",
    "/map",
    "/blame",
    "/trace",
    "/self",
    "/badges",
    "/btw something",
    "/handoff",
    "/pair",
    "/wiki",
    "/effort",
    "/effort high",
    "/ultrareview",
    "/review",
    "/tdd-gate",
    "/tdd-gate on",
    "/tdd-gate off",
    "/sessions",
    "/resume",
    "/fork",
    "/fork named",
    "/rename my-session",
    "/export",
    "/models",
    "/models ",
    "/spawn migrate views",
    "/budget",
    "/budget 5",
    "/budget off",
)


@pytest.mark.parametrize("line", _NEW_COMMANDS_NO_ARGS)
def test_new_commands_dispatch_cleanly_with_renderable(
    session: InteractiveSession, line: str
) -> None:
    result = session.dispatch(line)
    assert result.renderable is not None, (
        f"{line!r} should ship a Rich renderable for the TTY path"
    )
    # Plain output is non-empty so the non-TTY path has something to print.
    assert result.output, f"{line!r} produced an empty plain output"


@pytest.mark.parametrize(
    "name",
    sorted(SLASH_COMMANDS.keys()),
)
def test_every_registered_command_has_a_help_doc(name: str) -> None:
    """Defence-in-depth: prevent shipping a command without a help doc."""
    from lyra_cli.interactive.session import slash_description

    desc = slash_description(name)
    assert desc, f"command /{name} has no help description"


# ---------------------------------------------------------------------------
# /compact — must reduce token count
# ---------------------------------------------------------------------------


def test_compact_reduces_token_count(session: InteractiveSession) -> None:
    session.tokens_used = 10_000
    result = session.dispatch("/compact")
    assert session.tokens_used < 10_000
    assert "compact" in result.output.lower() or "compress" in result.output.lower()


# ---------------------------------------------------------------------------
# /rewind — must restore state from the previous turn
# ---------------------------------------------------------------------------


def test_rewind_restores_previous_state(session: InteractiveSession) -> None:
    # /rewind must restore the pending_task slot, so this test stays
    # in plan mode where plain-text input populates that slot.
    session.dispatch("/mode plan")
    session.dispatch("first task")
    assert session.turn == 1
    assert session.pending_task == "first task"
    session.dispatch("second task")
    assert session.turn == 2

    result = session.dispatch("/rewind")
    assert session.turn == 1
    assert "rewound" in result.output.lower() or "rewind" in result.output.lower()
    session.dispatch("/rewind")
    assert session.turn == 0


def test_rewind_when_empty_is_explicit(session: InteractiveSession) -> None:
    result = session.dispatch("/rewind")
    assert "nothing to rewind" in result.output.lower()


# ---------------------------------------------------------------------------
# /budget — set + clear + reject bad input
# ---------------------------------------------------------------------------


def test_budget_set_then_clear(session: InteractiveSession) -> None:
    session.dispatch("/budget 7.50")
    assert session.budget_cap_usd == 7.5
    session.dispatch("/budget off")
    assert session.budget_cap_usd is None


def test_budget_rejects_non_numeric(session: InteractiveSession) -> None:
    result = session.dispatch("/budget banana")
    assert "bad budget" in result.output.lower()
    assert session.budget_cap_usd is None


# ---------------------------------------------------------------------------
# /vim — toggle behaviour
# ---------------------------------------------------------------------------


def test_vim_toggle_flips_state(session: InteractiveSession) -> None:
    assert session.vim_mode is False
    session.dispatch("/vim")
    assert session.vim_mode is True
    session.dispatch("/vim")
    assert session.vim_mode is False
    session.dispatch("/vim on")
    assert session.vim_mode is True
    session.dispatch("/vim off")
    assert session.vim_mode is False


# ---------------------------------------------------------------------------
# /theme — list, set, reject
# ---------------------------------------------------------------------------


def test_theme_default_is_aurora(session: InteractiveSession) -> None:
    assert session.theme == "aurora"


def test_theme_switch_updates_state(session: InteractiveSession) -> None:
    result = session.dispatch("/theme candy")
    assert session.theme == "candy"
    assert "candy" in result.output


def test_theme_unknown_value_is_rejected(
    session: InteractiveSession,
) -> None:
    result = session.dispatch("/theme strawberry")
    assert session.theme == "aurora"
    assert "unknown theme" in result.output.lower()


def test_theme_module_returns_palette() -> None:
    aurora = themes.get("aurora")
    assert aurora["accent"]
    # Falling back on unknown keeps the UI rendering rather than crashing.
    fallback = themes.get("does-not-exist")
    assert fallback == aurora


# ---------------------------------------------------------------------------
# /tools — surfaces the registry
# ---------------------------------------------------------------------------


def test_tools_command_lists_builtins(session: InteractiveSession) -> None:
    result = session.dispatch("/tools")
    out = result.output
    for tool in ("Read", "Write", "Edit", "Glob", "Grep", "Bash", "MCP"):
        assert tool in out, f"{tool!r} missing from /tools output"


def test_tool_registry_returns_known_tools() -> None:
    tools = registered_tools()
    names = {t["name"] for t in tools}
    assert {"Read", "Write", "Edit", "Bash", "MCP"}.issubset(names)


def test_tool_registry_lookup_by_name() -> None:
    tool = tool_by_name("read")
    assert tool is not None
    assert tool["name"] == "Read"


def test_tool_registry_filters_by_risk() -> None:
    high = tools_of_risk(["high"])
    assert all(t["risk"] == "high" for t in high)
    assert any(t["name"] == "Bash" for t in high)


# ---------------------------------------------------------------------------
# /stats — counters track slash + bash + file mentions
# ---------------------------------------------------------------------------


def test_stats_counts_history_kinds(session: InteractiveSession) -> None:
    session.dispatch("look at code")
    session.dispatch("/help")
    session.dispatch("!ls")
    session.dispatch("@README.md")
    result = session.dispatch("/stats")
    out = result.output
    assert "1" in out  # at least one of each counter
    assert "stats" not in out.lower() or "slash" in out.lower()


# ---------------------------------------------------------------------------
# /badges — usage frequency table
# ---------------------------------------------------------------------------


def test_badges_aggregates_slash_usage(session: InteractiveSession) -> None:
    session.dispatch("/help")
    session.dispatch("/help")
    session.dispatch("/status")
    result = session.dispatch("/badges")
    assert "/help" in result.output
    assert "/status" in result.output


# ---------------------------------------------------------------------------
# Store (session persistence)
# ---------------------------------------------------------------------------


def test_store_round_trip(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, model="opus", mode="agent")
    s.dispatch("hello")
    s.dispatch("/mode debug")
    s.cost_usd = 0.42
    s.tokens_used = 1_234
    s.deep_think = True
    s.theme = "candy"
    s.budget_cap_usd = 12.5

    path = store_mod.save(s, name="snapshot-1")
    assert path.exists()

    loaded = store_mod.load(tmp_path, "snapshot-1")
    assert loaded.model == "opus"
    assert loaded.mode == "debug"
    assert loaded.cost_usd == pytest.approx(0.42)
    assert loaded.tokens_used == 1_234
    assert loaded.deep_think is True
    assert loaded.theme == "candy"
    assert loaded.budget_cap_usd == pytest.approx(12.5)
    assert loaded.history == ["hello", "/mode debug"]


def test_store_load_most_recent(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("a")
    store_mod.save(s, name="first")
    s.dispatch("b")
    store_mod.save(s, name="second")
    loaded = store_mod.load(tmp_path)  # no id → most recent
    assert loaded.history[-1] == "b"


def test_store_list_sessions_orders_newest_first(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    store_mod.save(s, name="alpha")
    s.dispatch("turn")
    store_mod.save(s, name="beta")
    entries = store_mod.list_sessions(tmp_path)
    assert [e["name"] for e in entries[:2]] == ["beta", "alpha"]


def test_store_load_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        store_mod.load(tmp_path, "nope")


def test_store_fork_creates_separate_snapshot(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("a")
    s.dispatch("b")
    path = store_mod.fork(s, name="my-branch")
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["name"] == "my-branch"
    assert payload["state"]["history"] == ["a", "b"]


# ---------------------------------------------------------------------------
# HIR JSONL event logger
# ---------------------------------------------------------------------------


def test_hir_writes_one_event_per_line(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    with hir_mod.HIRLogger(log_path) as hir:
        hir.on_session_start(repo_root=tmp_path, model="opus", mode="plan")
        hir.on_prompt(turn=1, mode="plan", line="hello")
        hir.on_slash(turn=1, name="status", args="")
        hir.on_bash(
            turn=1,
            command="ls",
            exit_code=0,
            stdout_bytes=42,
            stderr_bytes=0,
        )
        hir.on_mode_change(turn=2, from_mode="plan", to_mode="agent")
        hir.on_session_end(turns=2, cost_usd=0.0, tokens=0)

    lines = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    kinds = [r["kind"] for r in lines]
    assert kinds == [
        "session.start",
        "user.prompt",
        "slash.dispatch",
        "bash.run",
        "mode.change",
        "session.end",
    ]
    for record in lines:
        assert "ts" in record
        assert "data" in record


def test_hir_disabled_logger_is_silent(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    hir = hir_mod.HIRLogger(log_path, enabled=False)
    hir.on_prompt(turn=1, mode="plan", line="hi")
    hir.close()
    assert not log_path.exists()


def test_hir_default_path_lands_under_lyra(tmp_path: Path) -> None:
    expected = tmp_path / ".lyra" / "sessions" / "events.jsonl"
    assert hir_mod.default_event_path(tmp_path) == expected


# ---------------------------------------------------------------------------
# Multi-prefix completer (@file + #skill + /slash)
# ---------------------------------------------------------------------------


def _completions(
    completer: SlashCompleter, text: str
) -> list[str]:
    """Pull plain completion strings out of the completer for assertions."""
    from prompt_toolkit.document import Document

    doc = Document(text, cursor_position=len(text))
    return [c.text for c in completer.get_completions(doc, object())]


def test_completer_slash_emits_known_commands(tmp_path: Path) -> None:
    completer = SlashCompleter(repo_root=tmp_path)
    completions = _completions(completer, "/h")
    assert "help" in completions
    assert "history" in completions


def test_completer_at_lists_repo_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# hi", encoding="utf-8")
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "main.py").write_text("print()", encoding="utf-8")

    completer = SlashCompleter(repo_root=tmp_path)
    completions = _completions(completer, "@")
    assert "README.md" in completions
    assert "src/main.py" in completions


def test_completer_at_filters_by_substring(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("", encoding="utf-8")
    completer = SlashCompleter(repo_root=tmp_path)
    completions = _completions(completer, "@CHANGE")
    assert "CHANGELOG.md" in completions
    assert "README.md" not in completions


def test_completer_at_skips_ignored_dirs(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "ok.py").write_text("", encoding="utf-8")
    completer = SlashCompleter(repo_root=tmp_path)
    completions = _completions(completer, "@")
    assert "src/ok.py" in completions
    assert not any("node_modules" in c for c in completions)


def test_completer_hash_lists_skill_packs(tmp_path: Path) -> None:
    completer = SlashCompleter(repo_root=tmp_path)
    completions = _completions(completer, "#")
    assert "atomic-skills" in completions
    assert "tdd-sprint" in completions


def test_last_token_handles_whitespace() -> None:
    assert _last_token("") == ""
    assert _last_token("hello") == "hello"
    assert _last_token("look at @src/") == "@src/"
    assert _last_token("done ") == ""


def test_walk_repo_returns_relative_posix_paths(tmp_path: Path) -> None:
    sub = tmp_path / "deep" / "nested"
    sub.mkdir(parents=True)
    (sub / "file.py").write_text("", encoding="utf-8")
    paths = list(_walk_repo(tmp_path))
    assert "deep/nested/file.py" in paths


# ---------------------------------------------------------------------------
# /status — surfaces the new flags so users can see what's on
# ---------------------------------------------------------------------------


def test_status_surfaces_deep_think_and_theme(
    session: InteractiveSession,
) -> None:
    session.deep_think = True
    session.theme = "candy"
    session.budget_cap_usd = 3.0
    result = session.dispatch("/status")
    out = result.output.lower()
    assert "deep" in out
    assert "candy" in out
    assert "$3.00" in result.output


# ---------------------------------------------------------------------------
# /handoff + /export — content sanity
# ---------------------------------------------------------------------------


def test_handoff_mentions_session_essentials(
    session: InteractiveSession,
) -> None:
    session.dispatch("ship CSV export")
    result = session.dispatch("/handoff")
    out = result.output.lower()
    assert "handoff" in out


def test_export_lists_target_path(session: InteractiveSession) -> None:
    result = session.dispatch("/export")
    assert ".lyra" in result.output


# ---------------------------------------------------------------------------
# /effort — accepts known levels, rejects unknown
# ---------------------------------------------------------------------------


def test_effort_accepts_known_levels(session: InteractiveSession) -> None:
    for level in ("low", "medium", "high", "ultra"):
        result = session.dispatch(f"/effort {level}")
        assert level in result.output.lower()


def test_effort_rejects_unknown(session: InteractiveSession) -> None:
    result = session.dispatch("/effort banana")
    assert "unknown effort" in result.output.lower()

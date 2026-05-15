"""Contract tests for the Phase 5 Lyra pickers.

Two layers:

  * Pure entry-builder functions (``model_entries``, ``skill_entries``,
    ``mcp_entries``) — exercised against fixtures with no Textual at
    all. This is where the bulk of the assertions live.
  * Filter helper (``_fuzzy_filter``) — covers prefix / substring /
    subsequence scoring.

We don't drive a real Textual app — the picker base's ListView and
ModalScreen wiring is glue over the entry layer; mounting a full
Textual app per test would multiply runtime by 100×.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.tui_v2.modals.base import Entry, _fuzzy_filter, _subsequence
from lyra_cli.tui_v2.modals.mcp import mcp_entries
from lyra_cli.tui_v2.modals.model import PROVIDERS, model_entries
from lyra_cli.tui_v2.modals.skill import skill_entries


# ---------------------------------------------------------------------
# _fuzzy_filter
# ---------------------------------------------------------------------


def _e(key: str, label: str = "", desc: str = "") -> Entry:
    return Entry(key=key, label=label or key, description=desc)


def test_fuzzy_filter_empty_query_returns_all() -> None:
    entries = [_e("a"), _e("b"), _e("c")]
    assert _fuzzy_filter(entries, "") == entries
    assert _fuzzy_filter(entries, "   ") == entries


def test_fuzzy_filter_prefix_beats_substring_beats_subsequence() -> None:
    entries = [
        _e("zsubseq", "z-s-u-b-s-e-q"),  # subsequence only
        _e("xsubstr", "has sub inside"),  # substring
        _e("sub_prefix", "sub prefix wins"),  # prefix
    ]
    out = _fuzzy_filter(entries, "sub")
    # Prefix match first, then substring, then subsequence
    assert out[0].key == "sub_prefix"
    assert out[1].key == "xsubstr"
    assert out[2].key == "zsubseq"


def test_fuzzy_filter_case_insensitive() -> None:
    entries = [_e("anthropic"), _e("openai")]
    out = _fuzzy_filter(entries, "ANT")
    assert out and out[0].key == "anthropic"


def test_fuzzy_filter_no_match_returns_empty() -> None:
    entries = [_e("alpha"), _e("beta")]
    assert _fuzzy_filter(entries, "zzz") == []


@pytest.mark.parametrize(
    "needle,haystack,expected",
    [
        ("", "anything", True),
        ("abc", "a-x-b-y-c", True),
        ("abc", "cba", False),
        ("abc", "ac", False),
        ("ant", "anthropic", True),
    ],
)
def test_subsequence(needle: str, haystack: str, expected: bool) -> None:
    assert _subsequence(needle, haystack) is expected


# ---------------------------------------------------------------------
# model_entries
# ---------------------------------------------------------------------


def test_model_entries_includes_full_provider_catalogue() -> None:
    entries = model_entries()
    keys = [e.key for e in entries]
    # Same set as PROVIDERS — order matters too (auto first).
    assert keys == list(PROVIDERS)


def test_model_entries_marks_current_with_bullet() -> None:
    entries = model_entries(current="deepseek")
    by_key = {e.key: e for e in entries}
    assert "●" in by_key["deepseek"].label
    # All others get a space prefix.
    assert "●" not in by_key["anthropic"].label


def test_model_entries_auto_has_no_env_var() -> None:
    entries = model_entries()
    auto = next(e for e in entries if e.key == "auto")
    assert auto.meta is not None
    assert "auth" in auto.meta and auto.meta["auth"] == "none required"


def test_model_entries_local_providers_marked_no_auth() -> None:
    entries = model_entries()
    by_key = {e.key: e for e in entries}
    for local in ("ollama", "lmstudio", "mock"):
        assert by_key[local].meta is not None
        assert by_key[local].meta["auth"] == "none required"


def test_model_entries_configured_flag_reflects_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake")
    # Hide auth.json keys too — provider_has_credentials also checks store.
    monkeypatch.setattr(
        "lyra_core.auth.store.get_api_key", lambda _p: None, raising=False
    )
    entries = model_entries()
    by_key = {e.key: e for e in entries}
    assert by_key["deepseek"].meta is not None
    assert by_key["deepseek"].meta["configured"] == "yes"
    assert by_key["anthropic"].meta is not None
    assert by_key["anthropic"].meta["configured"] == "no"


def test_model_entries_unconfigured_description_mentions_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "lyra_core.auth.store.get_api_key", lambda _p: None, raising=False
    )
    entries = model_entries()
    anthropic = next(e for e in entries if e.key == "anthropic")
    assert "ANTHROPIC_API_KEY" in anthropic.description


# ---------------------------------------------------------------------
# skill_entries
# ---------------------------------------------------------------------


def test_skill_entries_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lyra_cli.tui_v2.commands import skills_mcp

    monkeypatch.setattr(skills_mcp, "_SKILLS_GLOBAL", tmp_path / "no-global")
    assert skill_entries(tmp_path) == []


def test_skill_entries_renders_source_and_description(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lyra_cli.tui_v2.commands import skills_mcp

    monkeypatch.setattr(skills_mcp, "_SKILLS_GLOBAL", tmp_path / "no-global")
    skill_dir = tmp_path / ".claude" / "skills" / "weather-check"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: weather-check\ndescription: Fetches weather forecast.\n---\nbody"
    )
    entries = skill_entries(tmp_path)
    assert len(entries) == 1
    e = entries[0]
    assert e.key == "weather-check"
    assert "[project]" in e.label
    assert "weather forecast" in e.description.lower()


# ---------------------------------------------------------------------
# mcp_entries
# ---------------------------------------------------------------------


def test_mcp_entries_empty(tmp_path: Path) -> None:
    assert mcp_entries(tmp_path) == []


def test_mcp_entries_renders_transport(tmp_path: Path) -> None:
    cfg = tmp_path / ".lyra" / "mcp.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({
        "mcpServers": {
            "fs": {"command": "mcp-server-fs"},
            "remote": {"url": "https://api.example.com/mcp"},
        }
    }))
    entries = mcp_entries(tmp_path)
    by_key = {e.key: e for e in entries}
    assert {"fs", "remote"} == set(by_key)
    assert "stdio" in by_key["fs"].description
    assert "http" in by_key["remote"].description


# ---------------------------------------------------------------------
# Modal class smoke (no Textual mount — just construction)
# ---------------------------------------------------------------------


def test_modals_construct_without_error(tmp_path: Path) -> None:
    """All three pickers construct cleanly with realistic inputs.

    Bypassing ModalScreen's heavy init via __new__ — we just want to
    confirm the entries() override fires and returns a list.
    """
    from lyra_cli.tui_v2.modals import McpPicker, ModelPicker, SkillPicker

    # ModelPicker
    picker = ModelPicker.__new__(ModelPicker)
    picker._current = "auto"
    assert isinstance(picker.entries(), list)

    # SkillPicker
    picker_s = SkillPicker.__new__(SkillPicker)
    picker_s._working_dir = tmp_path
    assert isinstance(picker_s.entries(), list)

    # McpPicker
    picker_m = McpPicker.__new__(McpPicker)
    picker_m._working_dir = tmp_path
    assert isinstance(picker_m.entries(), list)

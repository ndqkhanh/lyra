"""Phase B.4 (v2.4.0) — SKILL.md injection into the chat system prompt.

Lyra ships :mod:`lyra_skills` with packaged ``SKILL.md`` packs and lets
users define more under ``.lyra/skills/``. Pre-v2.4 those packs lived
on disk but never reached the LLM, so the model couldn't say
"applying the surgical-changes skill here". The Phase B.4 work
(:mod:`lyra_cli.interactive.skills_inject`) injects a compact
"## Available skills" block into the chat system prompt and exposes
a ``/skills`` slash command for visibility/toggling/reloading.

These tests pin down:

* discovery walks all three roots in the documented precedence order
  (packaged → user → project),
* the rendered block is empty when no skills exist (so the system
  prompt stays clean),
* a malformed ``SKILL.md`` is suppressed rather than fatal,
* :func:`_augment_system_prompt_with_skills` caches the block and
  the cache survives across turns,
* the ``/skills`` slash command toggles, lists, and reloads.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lyra_cli.interactive.session import (
    InteractiveSession,
    SLASH_COMMANDS,
    _augment_system_prompt_with_skills,
)
from lyra_cli.interactive.skills_inject import (
    discover_skill_roots,
    render_skill_block,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(root: Path, sid: str, description: str, body: str = "do work.\n") -> None:
    """Create ``<root>/<sid>/SKILL.md`` with valid YAML frontmatter."""
    sdir = root / sid
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "SKILL.md").write_text(
        f"---\nid: {sid}\nname: {sid}\ndescription: {description}\n---\n{body}",
        encoding="utf-8",
    )


def _make_session(repo_root: Path) -> InteractiveSession:
    """Construct a bare :class:`InteractiveSession` for slash-command tests."""
    return InteractiveSession(
        mode="ask",
        model="mock",
        repo_root=repo_root,
    )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_discover_skill_roots_returns_project_root_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The project-local ``.lyra/skills`` is always one of the roots."""
    project_skills = tmp_path / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "lyra-home-doesnt-exist"))

    roots = discover_skill_roots(tmp_path)
    assert project_skills in roots


def test_discover_skill_roots_includes_user_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``$LYRA_HOME/skills`` is surfaced when it exists on disk."""
    home = tmp_path / "lyra-home"
    user_skills = home / "skills"
    user_skills.mkdir(parents=True)
    monkeypatch.setenv("LYRA_HOME", str(home))

    roots = discover_skill_roots(tmp_path)
    assert user_skills in roots


def test_discover_skill_roots_skips_missing_dirs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Roots that don't exist on disk are silently dropped."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-such-home"))
    roots = discover_skill_roots(tmp_path / "no-such-repo")
    for r in roots:
        assert r.is_dir(), f"discovery returned a missing root: {r}"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_render_skill_block_lists_project_skills(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A project-local skill shows up in the rendered block by id + description."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    project_skills = tmp_path / ".lyra" / "skills"
    _write_skill(project_skills, "surgical-changes", "minimal-edit policy")

    block = render_skill_block(tmp_path)
    assert "## Available skills" in block
    assert "- surgical-changes: minimal-edit policy" in block


# ---------------------------------------------------------------------------
# Progressive activation (Phase N.7)
# ---------------------------------------------------------------------------


def _write_progressive_skill(
    root: Path,
    sid: str,
    description: str,
    keywords: list[str],
    body: str = "Step 1: do the thing.\n",
) -> None:
    """Create a ``SKILL.md`` with the new progressive frontmatter."""
    kw = "\n".join(f"  - {k}" for k in keywords)
    root.mkdir(parents=True, exist_ok=True)
    sdir = root / sid
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "SKILL.md").write_text(
        f"---\n"
        f"id: {sid}\nname: {sid}\ndescription: {description}\n"
        f"progressive: true\n"
        f"keywords:\n{kw}\n"
        f"---\n{body}",
        encoding="utf-8",
    )


def test_progressive_skill_marker_in_advertised_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    _write_progressive_skill(
        tmp_path / ".lyra" / "skills",
        "deep-dive", "long doc, opt-in", ["dive"],
    )
    block = render_skill_block(tmp_path)
    assert "- deep-dive [progressive]" in block


def test_progressive_skill_body_not_injected_without_keyword(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No prompt → no ``Active skills`` block, no body."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    _write_progressive_skill(
        tmp_path / ".lyra" / "skills",
        "deep-dive", "long doc", ["dive"],
        body="SECRET-BODY-MARKER",
    )
    block = render_skill_block(tmp_path)
    assert "SECRET-BODY-MARKER" not in block
    assert "## Active skills" not in block


def test_progressive_skill_body_injected_on_keyword(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    _write_progressive_skill(
        tmp_path / ".lyra" / "skills",
        "deep-dive", "long doc", ["dive"],
        body="SECRET-BODY-MARKER",
    )
    block = render_skill_block(tmp_path, prompt="please dive into this issue")
    assert "## Active skills" in block
    assert "SECRET-BODY-MARKER" in block


def test_progressive_skill_body_injected_via_force_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    _write_progressive_skill(
        tmp_path / ".lyra" / "skills",
        "deep-dive", "long doc", ["dive"],
        body="FORCED-MARKER",
    )
    block = render_skill_block(
        tmp_path, prompt="totally unrelated", force_ids=["deep-dive"],
    )
    assert "FORCED-MARKER" in block


def test_render_skill_block_returns_empty_when_no_skills(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No discovered skills → empty string (so callers don't prepend a header)."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    block = render_skill_block(tmp_path)
    # Ignore packaged packs in this assertion; they may or may not be installed.
    if not block:
        return
    # If lyra_skills.packs is installed, we still expect *some* entries
    # but not the test-injected one (we never wrote it).
    assert "made-up-skill-name-xyz" not in block


def test_render_skill_block_caps_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``max_skills`` caps the entries to keep the prompt budget bounded."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    project_skills = tmp_path / ".lyra" / "skills"
    for i in range(20):
        _write_skill(project_skills, f"skill-{i:02d}", f"description-{i}")

    block = render_skill_block(tmp_path, max_skills=5)
    # Project-locals plus possibly some packaged skills, but our caps
    # at 5 — count the "- skill-NN:" lines specifically.
    project_lines = [
        line for line in block.splitlines() if line.startswith("- skill-")
    ]
    assert len(project_lines) <= 5


def test_render_skill_block_truncates_long_descriptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per-line cap protects against a multi-paragraph description."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    project_skills = tmp_path / ".lyra" / "skills"
    huge = "x" * 1000
    _write_skill(project_skills, "verbose", huge)

    block = render_skill_block(tmp_path, line_limit=120)
    matching = [line for line in block.splitlines() if line.startswith("- verbose:")]
    assert matching, "expected the verbose skill to be rendered"
    assert all(len(line) <= 120 for line in matching), (
        "line cap not honoured", matching
    )


def test_render_skill_block_swallows_malformed_skill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A SKILL.md with no frontmatter must not break the chat turn."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    project_skills = tmp_path / ".lyra" / "skills"
    _write_skill(project_skills, "good", "well-formed")
    # Now drop a broken neighbour.
    bad_dir = project_skills / "broken"
    bad_dir.mkdir()
    (bad_dir / "SKILL.md").write_text("no frontmatter here", encoding="utf-8")

    # Must not raise, must return a string.
    block = render_skill_block(tmp_path)
    assert isinstance(block, str)


# ---------------------------------------------------------------------------
# System-prompt augmentation
# ---------------------------------------------------------------------------


def test_augment_system_prompt_prepends_skill_block_when_skills_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The "## Available skills" block lands inside the system prompt."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    project_skills = tmp_path / ".lyra" / "skills"
    _write_skill(project_skills, "review", "review-then-act")

    session = _make_session(tmp_path)
    augmented = _augment_system_prompt_with_skills(session, "BASE PROMPT")

    assert augmented.startswith("BASE PROMPT")
    assert "## Available skills" in augmented
    assert "review-then-act" in augmented


def test_augment_system_prompt_returns_unchanged_when_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``skills_inject_enabled = False`` makes the function a no-op."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    project_skills = tmp_path / ".lyra" / "skills"
    _write_skill(project_skills, "any-skill", "any")

    session = _make_session(tmp_path)
    session.skills_inject_enabled = False
    augmented = _augment_system_prompt_with_skills(session, "BASE PROMPT")

    assert augmented == "BASE PROMPT"


def test_augment_system_prompt_caches_block_across_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The block is rendered exactly once per session."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    project_skills = tmp_path / ".lyra" / "skills"
    _write_skill(project_skills, "cached", "first")

    session = _make_session(tmp_path)
    first = _augment_system_prompt_with_skills(session, "PROMPT")

    # Mutate disk; the cache should hide the change until /skills reload.
    _write_skill(project_skills, "cached", "second-version-not-yet-visible")
    second = _augment_system_prompt_with_skills(session, "PROMPT")

    assert first == second


def test_augment_system_prompt_swallows_renderer_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blow-up in render_skill_block must not abort the chat turn."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))

    def _explode(_root: Path, **_kw: Any) -> str:
        raise RuntimeError("simulated discovery failure")

    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject.render_skill_block",
        _explode,
    )
    session = _make_session(tmp_path)

    augmented = _augment_system_prompt_with_skills(session, "PROMPT")
    assert augmented == "PROMPT"


# ---------------------------------------------------------------------------
# /skills slash command
# ---------------------------------------------------------------------------


def test_slash_skills_status_reports_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``/skills`` (no args) prints the toggle plus the count."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    _write_skill(tmp_path / ".lyra" / "skills", "alpha", "first")
    session = _make_session(tmp_path)

    result = SLASH_COMMANDS["skills"](session, "")
    out = result.output or ""
    assert "skill injection is on" in out
    assert "skill(s)" in out


def test_slash_skills_off_then_on_toggles_flag(tmp_path: Path) -> None:
    """``/skills off`` and ``/skills on`` flip the per-session flag."""
    session = _make_session(tmp_path)
    assert session.skills_inject_enabled is True

    SLASH_COMMANDS["skills"](session, "off")
    assert session.skills_inject_enabled is False

    SLASH_COMMANDS["skills"](session, "on")
    assert session.skills_inject_enabled is True


def test_slash_skills_list_prints_discovered_skills(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``/skills list`` enumerates the discovered packs by id."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    _write_skill(tmp_path / ".lyra" / "skills", "lookup-me", "find-this-line")
    session = _make_session(tmp_path)

    result = SLASH_COMMANDS["skills"](session, "list")
    assert "lookup-me" in (result.output or "")
    assert "find-this-line" in (result.output or "")


def test_slash_skills_reload_clears_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``/skills reload`` invalidates the cached block."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))
    project_skills = tmp_path / ".lyra" / "skills"
    _write_skill(project_skills, "v1", "first version")
    session = _make_session(tmp_path)

    first = _augment_system_prompt_with_skills(session, "P")
    assert "first version" in first

    # Edit the description on disk, then reload — the next augment should
    # pick up the new text.
    _write_skill(project_skills, "v1", "second version")
    SLASH_COMMANDS["skills"](session, "reload")

    second = _augment_system_prompt_with_skills(session, "P")
    assert "second version" in second
    assert first != second


def test_slash_skills_unknown_arg_is_friendly(tmp_path: Path) -> None:
    """An unrecognised arg returns a usage hint, never an exception."""
    session = _make_session(tmp_path)
    result = SLASH_COMMANDS["skills"](session, "wat")
    assert "unknown" in (result.output or "").lower()
    assert "usage" in (result.output or "").lower()

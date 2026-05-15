"""v3.6.0 4-mode taxonomy contract — permission-flavoured rename.

Why this file exists:
    v3.6.0 replaced the v3.2 Claude-Code-style behavioural mode set
    (``agent / plan / debug / ask``) with a permission-flavoured one
    that mirrors the ``Edit automatically / Ask before edits / Plan
    mode / Auto mode`` picker users see in modern coding-assistant
    UIs:

      - ``edit_automatically`` (default; full-access execution, no
        per-write confirmation)
      - ``ask_before_edits``   (full-access execution, but pauses
        for confirmation before every write or destructive call)
      - ``plan_mode``          (read-only collaborative design)
      - ``auto_mode``          (heuristic router that picks one of
        the three above per turn)

    The dedicated ``debug`` mode is gone — its systematic-debugging
    discipline survives as a regular skill the user invokes
    manually. The dedicated ``ask`` mode (read-only Q&A) is also
    gone; the closest preserved behaviour is ``plan_mode``, which
    remaps automatically.

    Every legacy name (v3.2: agent/plan/debug/ask; pre-v3.2:
    build/run/explore/retro) is remapped to the canonical v3.6 mode
    on session construction so old settings.json files keep
    working. This test pins all of those contracts so a future
    refactor can't re-introduce the regression silently.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.keybinds import _MODE_CYCLE_TAB
from lyra_cli.interactive.session import (
    _LEGACY_MODE_REMAP,
    _LYRA_MODE_PREAMBLE,
    _MODE_BLURBS,
    _MODE_HANDLERS,
    _MODE_SYSTEM_PROMPTS,
    _VALID_MODES,
    InteractiveSession,
    _classify_for_auto_mode,
    _cmd_mode,
)

# ---------------------------------------------------------------------------
# Kernel taxonomy — exactly 4 modes, names match the v3.6 picker
# ---------------------------------------------------------------------------


def test_valid_modes_are_exactly_the_v36_four() -> None:
    """``_VALID_MODES`` is the canonical source-of-truth for the 4 modes."""
    assert _VALID_MODES == (
        "edit_automatically",
        "ask_before_edits",
        "plan_mode",
        "auto_mode",
    )


def test_default_mode_is_edit_automatically(tmp_path: Path) -> None:
    """A bare ``InteractiveSession()`` lands in ``edit_automatically`` mode."""
    s = InteractiveSession(repo_root=tmp_path)
    assert s.mode == "edit_automatically"


def test_default_mode_aligns_permission_to_normal(tmp_path: Path) -> None:
    """``edit_automatically`` boots with ``permission_mode == 'normal'``."""
    s = InteractiveSession(repo_root=tmp_path)
    assert s.permission_mode == "normal"


def test_ask_before_edits_mode_aligns_permission_to_strict(tmp_path: Path) -> None:
    """Booting in ``ask_before_edits`` flips ``permission_mode`` to ``strict``."""
    s = InteractiveSession(repo_root=tmp_path, mode="ask_before_edits")
    assert s.mode == "ask_before_edits"
    assert s.permission_mode == "strict"


def test_mode_handlers_cover_every_valid_mode() -> None:
    """Every mode in ``_VALID_MODES`` has a registered plain-text handler."""
    assert set(_MODE_HANDLERS.keys()) == set(_VALID_MODES)


def test_mode_system_prompts_cover_every_valid_mode_except_auto() -> None:
    """Every mode except auto_mode has a mode-specific system prompt.

    auto_mode borrows the prompt of its sub-mode at dispatch time —
    the ``_AUTO_MODE_SYSTEM_PROMPT`` exists as a fallback in case
    the router misses, but it should never be the active prompt
    in a healthy run.
    """
    assert set(_MODE_SYSTEM_PROMPTS.keys()) == set(_VALID_MODES)


def test_mode_blurbs_cover_every_valid_mode() -> None:
    """``_MODE_BLURBS`` (used by ``/mode list``) lists all 4 modes in order."""
    blurb_names = tuple(name for name, _ in _MODE_BLURBS)
    assert blurb_names == _VALID_MODES


def test_tab_cycle_is_a_permutation_of_valid_modes() -> None:
    """``_MODE_CYCLE_TAB`` (Tab key rotation) covers every valid mode exactly once."""
    assert set(_MODE_CYCLE_TAB) == set(_VALID_MODES)
    assert len(_MODE_CYCLE_TAB) == len(_VALID_MODES)


def test_tab_cycle_separates_the_two_write_capable_modes() -> None:
    """``edit_automatically`` and ``ask_before_edits`` must not be adjacent.

    Otherwise a single Tab press could silently flip the user
    between "edits land" and "edits land after a confirmation",
    which is exactly the kind of foot-gun the rotation order
    exists to prevent.
    """
    n = len(_MODE_CYCLE_TAB)
    for i in range(n):
        a = _MODE_CYCLE_TAB[i]
        b = _MODE_CYCLE_TAB[(i + 1) % n]
        assert not {a, b} == {"edit_automatically", "ask_before_edits"}, (
            f"Tab cycle has the two write-capable modes adjacent at "
            f"positions {i}/{(i + 1) % n} — single Tab would flip "
            f"between auto-edit and confirm-edit silently"
        )


# ---------------------------------------------------------------------------
# System-prompt preamble: enumerates the 4 modes + disclaims TDD phases
# ---------------------------------------------------------------------------


def test_preamble_enumerates_all_four_modes_in_order() -> None:
    """The shared preamble lists every v3.6 mode by name.

    Critical: the LLM relies on this preamble to ground its "how
    many modes do you have" answer. Removing or renaming a mode
    here is the regression we're guarding against.
    """
    for mode_name in _VALID_MODES:
        assert mode_name in _LYRA_MODE_PREAMBLE, (
            f"preamble must mention {mode_name!r} — without it the LLM "
            f"will hallucinate from training-data residue"
        )


def test_preamble_disclaims_tdd_phases_as_modes() -> None:
    """RED / GREEN / REFACTOR are TDD phases inside the edit modes, not modes."""
    text = _LYRA_MODE_PREAMBLE.lower()
    assert "red" in text and "green" in text and "refactor" in text
    assert "opt-in plugin" in text or "not a separate mode" in text or "not a mode" in text
    assert "exactly four" in text or "exactly 4" in text


def test_preamble_disclaims_legacy_v32_mode_names() -> None:
    """Legacy v3.2 names (agent/plan/debug/ask) must not be presented as live modes."""
    text = _LYRA_MODE_PREAMBLE.lower()
    # The preamble may *mention* the legacy names while disclaiming
    # them — that's fine. What we forbid is presenting them in the
    # "you operate in one of four modes" enumeration. The new
    # enumeration uses explicit underscored names so a substring
    # check is unambiguous.
    assert "legacy aliases" in text or "legacy alias" in text


def test_every_mode_prompt_carries_the_preamble() -> None:
    """All four mode-specific prompts inherit the 4-mode enumeration."""
    for mode_name, prompt in _MODE_SYSTEM_PROMPTS.items():
        assert _LYRA_MODE_PREAMBLE in prompt, (
            f"mode={mode_name!r} prompt missing preamble — the LLM will "
            f"hallucinate modes when this prompt is the active one"
        )


def test_no_mode_prompt_calls_tdd_phase_a_mode() -> None:
    """Defensive: no per-mode override accidentally re-introduces TDD-as-mode language."""
    bad_phrases = (
        "red mode", "green mode", "refactor mode",
        "build mode",  # legacy v2.x; must be gone
        "agent mode", "debug mode", "ask mode",  # legacy v3.2; must be gone as live modes
    )
    for mode_name, prompt in _MODE_SYSTEM_PROMPTS.items():
        prompt_lower = prompt.lower()
        for bad in bad_phrases:
            assert bad not in prompt_lower, (
                f"mode={mode_name!r} prompt still contains {bad!r} — "
                f"this is the v3.6 rename regression"
            )


# ---------------------------------------------------------------------------
# Legacy alias remap — every prior mode name keeps working
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "legacy,canonical",
    [
        # v3.2.0 → v3.6.0
        ("agent", "edit_automatically"),
        ("plan",  "plan_mode"),
        ("debug", "auto_mode"),
        ("ask",   "plan_mode"),
        # pre-v3.2 → v3.6.0
        ("build",   "edit_automatically"),
        ("run",     "edit_automatically"),
        ("explore", "plan_mode"),
        ("retro",   "auto_mode"),
    ],
)
def test_legacy_mode_remap_at_construction(
    tmp_path: Path, legacy: str, canonical: str
) -> None:
    """Constructing with any legacy mode name canonicalises automatically."""
    s = InteractiveSession(repo_root=tmp_path, mode=legacy)
    assert s.mode == canonical, (
        f"legacy mode {legacy!r} must remap to {canonical!r} on boot — "
        f"otherwise old settings.json files break the user's session"
    )


def test_legacy_remap_table_covers_every_pre_v36_mode() -> None:
    """Sanity: the legacy table covers all four prior taxonomies."""
    expected = {
        "agent", "plan", "debug", "ask",     # v3.2
        "build", "run", "explore", "retro",  # pre-v3.2
    }
    assert set(_LEGACY_MODE_REMAP.keys()) == expected
    for canonical in _LEGACY_MODE_REMAP.values():
        assert canonical in _VALID_MODES


def test_slash_mode_accepts_short_alias(tmp_path: Path) -> None:
    """``/mode agent`` switches to ``edit_automatically``.

    v3.7+ promoted the short labels (``agent`` / ``plan`` / ``ask`` /
    ``auto``) to first-class names rather than legacy aliases — typing
    them lands silently on the matching canonical mode. The output
    surfaces both the short label the user typed and the canonical ID
    in parens so the permission posture stays unambiguous.
    """
    s = InteractiveSession(repo_root=tmp_path, mode="plan_mode")
    result = _cmd_mode(s, "agent")
    assert s.mode == "edit_automatically"
    assert result.new_mode == "edit_automatically"
    # Output shows both the short label and the canonical ID.
    assert "agent" in result.output
    assert "edit_automatically" in result.output


def test_slash_mode_rejects_unknown_string(tmp_path: Path) -> None:
    """A genuinely unknown mode name still surfaces a friendly error."""
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_mode(s, "wibble")
    assert s.mode == "edit_automatically"
    out = result.output.lower()
    assert "unknown mode" in out
    for valid in _VALID_MODES:
        assert valid in result.output


def test_slash_mode_list_shows_exactly_four_modes(tmp_path: Path) -> None:
    """``/mode list`` lists exactly the 4 canonical v3.6 modes."""
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_mode(s, "list")
    out = result.output
    for mode_name in _VALID_MODES:
        assert mode_name in out


# ---------------------------------------------------------------------------
# auto_mode router — pure-function classification contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt,expected",
    [
        # plan_mode wins on read-only intent
        ("explain how the agent loop works", "plan_mode"),
        ("how does the planner pick steps?", "plan_mode"),
        ("what is the difference between fast and smart slots?", "plan_mode"),
        ("design a caching layer for subagents", "plan_mode"),
        # bare question with no edit verb → plan_mode
        ("which provider is fastest?", "plan_mode"),
        # risky / destructive → ask_before_edits
        ("delete the old migration file", "ask_before_edits"),
        ("git push --force to origin/main", "ask_before_edits"),
        ("drop table users in production", "ask_before_edits"),
        # default → edit_automatically
        ("add a login button", "edit_automatically"),
        ("write a unit test for the parser", "edit_automatically"),
        ("rename foo to bar", "edit_automatically"),
        # empty → safe default
        ("", "edit_automatically"),
    ],
)
def test_auto_mode_classifier(prompt: str, expected: str) -> None:
    """The classifier is the public contract for auto_mode routing."""
    assert _classify_for_auto_mode(prompt) == expected


def test_auto_mode_handler_annotates_with_chosen_sub_mode(tmp_path: Path) -> None:
    """auto_mode dispatches to a sub-handler and annotates the result.

    We use a non-LLM-bound smoke check — the handler short-circuits
    on classification, calls the sub-handler, and prepends the
    ``[auto_mode → X]`` notice. We only assert on the notice
    prefix because the underlying chat handler will fail fast in
    the test environment (no real LLM provider wired).
    """
    s = InteractiveSession(repo_root=tmp_path, mode="auto_mode")
    handler = _MODE_HANDLERS["auto_mode"]
    result = handler(s, "explain how the agent loop works")
    # The chat handler in the test env returns an error path — that's
    # fine. We only need the annotation to confirm routing happened.
    assert result.output.startswith("[auto_mode → plan_mode]")


# ---------------------------------------------------------------------------
# Mode panel rendering: default colour fall-through preserved
# ---------------------------------------------------------------------------


def test_chat_renderable_default_mode_renders_a_title() -> None:
    """``chat_renderable()`` with no mode kwarg still produces a titled panel.

    We don't pin the exact title text here — the v3.6 default
    happens to use ``edit_automatically`` but the contract is
    "panel renders without crashing and surfaces *some* mode
    label". The kernel taxonomy test above is what pins the
    actual default mode name.
    """
    from lyra_cli.interactive.output import chat_renderable

    panel = chat_renderable("hi")
    title_str = str(panel.title)
    assert title_str  # non-empty title

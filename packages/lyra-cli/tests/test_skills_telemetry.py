"""Phase O.2 — per-turn skill activation telemetry.

Phase N.7 added progressive skill loading but the live REPL caller
(``_augment_system_prompt_with_skills``) ignored the per-turn user
line, so the activation path never actually fired in production.
Phase O.2 fixes that and adds the telemetry plumbing the rest of
Phase O depends on:

1. :func:`render_skill_block_with_activations` returns *both* the
   rendered block and the structured list of activated skill ids
   (with the reason each was selected). This is what the REPL uses
   so it knows which skills to credit / debit on the ledger after
   the turn settles.

2. :class:`SkillActivationRecorder` subscribes to lifecycle events
   (``turn_complete`` → success, ``turn_rejected`` → failure) and
   appends a :class:`SkillOutcome` to the ledger for each skill that
   activated this turn.

Together these close the Read–Write loop: the router *reads* skills
in (Phase O.6), the recorder *writes* outcomes back, and Phase O.4 /
O.5 use the resulting history to rewrite weak skills and propose
new ones.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest


# ── render_skill_block_with_activations ──────────────────────────


def test_render_with_activations_returns_text_and_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Progressive skill + matching prompt → activated_ids contains it."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))

    skills_dir = tmp_path / ".lyra" / "skills"
    _write_progressive_skill(
        skills_dir, "deep-dive", "long doc",
        keywords=["dive"], body="DEEP-MARKER",
    )

    from lyra_cli.interactive.skills_inject import (
        render_skill_block_with_activations,
    )

    result = render_skill_block_with_activations(
        tmp_path, prompt="please dive into the bug",
    )
    assert "DEEP-MARKER" in result.text
    assert "deep-dive" in result.activated_ids
    assert result.activation_reasons["deep-dive"]


def test_render_with_activations_empty_when_no_keyword(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No prompt → no activations (the bug Phase N.7 promised to fix)."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))

    _write_progressive_skill(
        tmp_path / ".lyra" / "skills", "deep-dive", "long doc",
        keywords=["dive"],
    )

    from lyra_cli.interactive.skills_inject import (
        render_skill_block_with_activations,
    )

    result = render_skill_block_with_activations(tmp_path)
    assert result.activated_ids == []
    assert "## Active skills" not in result.text


def test_render_with_activations_handles_force_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forcing an id surfaces it even when the prompt doesn't match."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))

    _write_progressive_skill(
        tmp_path / ".lyra" / "skills", "deep-dive", "long doc",
        keywords=["dive"], body="FORCED-X",
    )

    from lyra_cli.interactive.skills_inject import (
        render_skill_block_with_activations,
    )

    result = render_skill_block_with_activations(
        tmp_path,
        prompt="totally unrelated talk",
        force_ids=("deep-dive",),
    )
    assert "deep-dive" in result.activated_ids
    assert "FORCED-X" in result.text


def test_render_classic_helper_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The original ``render_skill_block`` still returns just text."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "no-home"))

    _write_progressive_skill(
        tmp_path / ".lyra" / "skills", "deep-dive", "x", ["dive"],
    )

    from lyra_cli.interactive.skills_inject import render_skill_block

    text = render_skill_block(tmp_path, prompt="dive in")
    assert isinstance(text, str)
    assert "deep-dive" in text


# ── SkillActivationRecorder ──────────────────────────────────────


def test_recorder_marks_success_on_turn_complete(tmp_path: Path) -> None:
    """``turn_complete`` lifecycle → success outcome on the ledger."""
    from lyra_cli.interactive.skills_telemetry import SkillActivationRecorder
    from lyra_skills.ledger import OUTCOME_SUCCESS, load_ledger

    ledger_path = tmp_path / "ledger.json"
    rec = SkillActivationRecorder(ledger_path=ledger_path)
    rec.note_activation(
        session_id="s1", turn=1, skill_id="x",
        reason="keyword: dive",
    )
    rec.on_turn_complete(session_id="s1", turn=1)

    s = load_ledger(ledger_path).get("x")
    assert s.successes == 1
    assert s.failures == 0
    assert s.history[-1].kind == OUTCOME_SUCCESS
    assert s.history[-1].detail == "keyword: dive"


def test_recorder_marks_failure_on_turn_rejected(tmp_path: Path) -> None:
    """``turn_rejected`` → failure with the reason captured."""
    from lyra_cli.interactive.skills_telemetry import SkillActivationRecorder
    from lyra_skills.ledger import OUTCOME_FAILURE, load_ledger

    ledger_path = tmp_path / "ledger.json"
    rec = SkillActivationRecorder(ledger_path=ledger_path)
    rec.note_activation(
        session_id="s1", turn=2, skill_id="y", reason="forced",
    )
    rec.on_turn_rejected(
        session_id="s1", turn=2, reason="provider_init_failed",
    )

    s = load_ledger(ledger_path).get("y")
    assert s.failures == 1
    assert s.successes == 0
    assert s.last_failure_reason == "provider_init_failed"
    assert s.history[-1].kind == OUTCOME_FAILURE


def test_recorder_clears_state_per_turn(tmp_path: Path) -> None:
    """Each turn's activation set is independent of the previous one."""
    from lyra_cli.interactive.skills_telemetry import SkillActivationRecorder
    from lyra_skills.ledger import load_ledger

    ledger_path = tmp_path / "ledger.json"
    rec = SkillActivationRecorder(ledger_path=ledger_path)

    rec.note_activation(session_id="s", turn=1, skill_id="a", reason="r1")
    rec.on_turn_complete(session_id="s", turn=1)

    rec.note_activation(session_id="s", turn=2, skill_id="b", reason="r2")
    rec.on_turn_rejected(session_id="s", turn=2, reason="oops")

    led = load_ledger(ledger_path)
    assert led.get("a").successes == 1
    assert led.get("a").failures == 0
    assert led.get("b").successes == 0
    assert led.get("b").failures == 1


def test_recorder_no_op_when_no_activations(tmp_path: Path) -> None:
    """A turn without activations leaves the ledger empty (no zero rows)."""
    from lyra_cli.interactive.skills_telemetry import SkillActivationRecorder
    from lyra_skills.ledger import load_ledger

    ledger_path = tmp_path / "ledger.json"
    rec = SkillActivationRecorder(ledger_path=ledger_path)
    rec.on_turn_complete(session_id="s", turn=1)
    led = load_ledger(ledger_path)
    assert led.skills == {}


def test_recorder_uses_session_now_as_default_ts(tmp_path: Path) -> None:
    """Ledger ``last_used_at`` is populated from a real timestamp."""
    from lyra_cli.interactive.skills_telemetry import SkillActivationRecorder
    from lyra_skills.ledger import load_ledger

    ledger_path = tmp_path / "ledger.json"
    rec = SkillActivationRecorder(ledger_path=ledger_path)

    before = time.time()
    rec.note_activation(session_id="s", turn=1, skill_id="z", reason="x")
    rec.on_turn_complete(session_id="s", turn=1)
    after = time.time()

    s = load_ledger(ledger_path).get("z")
    assert before - 1 <= s.last_used_at <= after + 1


# ── helpers ──────────────────────────────────────────────────────


def _write_progressive_skill(
    root: Path,
    sid: str,
    description: str,
    keywords: list[str],
    body: str = "Step 1: do the thing.\n",
) -> None:
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

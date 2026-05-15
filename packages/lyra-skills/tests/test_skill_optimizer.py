"""Phase O.7 — closed-loop SKILL.md optimizer (Executor/Analyst/Mutator).

These tests exercise the optimizer with a scripted LLM stub so the
loop logic is verified without spending real provider tokens. The
stub maps prompt-prefix → canned JSON response.
"""
from __future__ import annotations

import json
from typing import Callable

import pytest

from lyra_skills.optimizer import (
    MutationStrategy,
    OptimizeScenario,
    SkillMutation,
    _apply_mutation,
    _parse_json_obj,
    optimize_skill,
)


# ── Test doubles ─────────────────────────────────────────────────


class ScriptedLLM:
    """Tiny stub that returns canned answers keyed by the system prompt.

    Tests provide a routing function ``decide(prompt, system) -> str``
    so we can assert call counts and respond differently per role.
    """

    def __init__(self, decide: Callable[[str, str], str]) -> None:
        self.decide = decide
        self.calls: list[tuple[str, str]] = []

    def call(self, prompt: str, *, system: str = "", max_tokens: int = 2048) -> str:
        self.calls.append((system, prompt))
        return self.decide(prompt, system)


def _executor_reply(passed: bool, reason: str = "") -> str:
    return json.dumps({"passed": passed, "reason": reason})


def _analyst_reply(
    *,
    strategy: str = "add_example",
    target: str = "examples",
    diagnosis: str = "skill lacks concrete example",
) -> str:
    return json.dumps(
        {
            "diagnosis": diagnosis,
            "target_section": target,
            "strategy": strategy,
        }
    )


def _mutator_reply(
    *, old: str, new: str, reasoning: str = "anchor a concrete example"
) -> str:
    return json.dumps(
        {"old_text": old, "new_text": new, "reasoning": reasoning}
    )


# ── Schema / parsing tests ──────────────────────────────────────


def test_parse_json_obj_strips_markdown_fences():
    text = "```json\n{\"passed\": true}\n```"
    assert _parse_json_obj(text) == {"passed": True}


def test_parse_json_obj_falls_back_to_embedded_object():
    text = "sure thing: {\"passed\": false, \"reason\": \"oops\"}"
    assert _parse_json_obj(text) == {"passed": False, "reason": "oops"}


def test_parse_json_obj_empty_dict_on_garbage():
    assert _parse_json_obj("not json at all") == {}
    assert _parse_json_obj("") == {}


def test_apply_mutation_rejects_missing_anchor():
    body = "# Skill\n\n1. step one\n"
    mut = SkillMutation(
        strategy=MutationStrategy.ADD_EXAMPLE,
        target_section="examples",
        old_text="step two",
        new_text="step two\n2. step three",
    )
    new_body, applied = _apply_mutation(body, mut)
    assert applied is False
    assert new_body == body


def test_apply_mutation_rejects_ambiguous_anchor():
    body = "step one\nstep one\n"
    mut = SkillMutation(
        strategy=MutationStrategy.ADD_EXAMPLE,
        target_section="steps",
        old_text="step one",
        new_text="step one X",
    )
    _new, applied = _apply_mutation(body, mut)
    assert applied is False


def test_apply_mutation_replaces_unique_anchor():
    body = "before\nMARKER\nafter\n"
    mut = SkillMutation(
        strategy=MutationStrategy.RESTRUCTURE,
        target_section="middle",
        old_text="MARKER",
        new_text="REPLACED",
    )
    new_body, applied = _apply_mutation(body, mut)
    assert applied is True
    assert new_body == "before\nREPLACED\nafter\n"


# ── Loop behaviour tests ────────────────────────────────────────


def test_optimize_early_terminates_if_initial_score_meets_target():
    scenarios = [OptimizeScenario("p1", "did it work?")]
    llm = ScriptedLLM(lambda _p, _s: _executor_reply(True))

    result = optimize_skill(
        "demo",
        current_md="body",
        scenarios=scenarios,
        llm=llm,
        max_rounds=20,
        target_pass_rate=1.0,
    )
    assert result.target_reached is True
    assert result.initial_score == 1.0
    assert result.final_score == 1.0
    assert result.rounds == []


def test_optimize_accepts_mutation_that_improves_score():
    """Round 1: pre-score 0.0, mutation lands, post-score 1.0 → accepted."""
    scenarios = [OptimizeScenario("p1", "did it work?")]
    initial_body = "# skill\nFOO\n"

    # Track scoring calls: we need executor to return False on the
    # initial body, then True on the mutated body. Easiest is to
    # condition on the body content via the prompt template.
    def decide(prompt: str, system: str) -> str:
        if "diagnose why" in system.lower():
            return _analyst_reply(strategy="add_example", target="body")
        if "ONE small edit" in system:
            return _mutator_reply(old="FOO", new="FOO-BAR")
        # Executor — pass once the mutation has been applied.
        if "FOO-BAR" in prompt:
            return _executor_reply(True)
        return _executor_reply(False, "missing bar")

    llm = ScriptedLLM(decide)
    result = optimize_skill(
        "demo",
        current_md=initial_body,
        scenarios=scenarios,
        llm=llm,
        max_rounds=5,
    )

    assert result.initial_score == 0.0
    assert result.final_score == 1.0
    assert result.target_reached is True
    assert len(result.rounds) == 1
    assert result.rounds[0].accepted is True
    assert result.rounds[0].mutation is not None
    assert result.rounds[0].mutation.strategy == MutationStrategy.ADD_EXAMPLE
    assert "FOO-BAR" in result.final_md
    assert result.diff  # non-empty unified diff


def test_optimize_reverts_mutation_that_does_not_help():
    """Mutation lands but doesn't change pass rate → not accepted."""
    scenarios = [OptimizeScenario("p1", "did it work?")]
    initial_body = "# skill\nFOO\n"

    def decide(prompt: str, system: str) -> str:
        if "diagnose" in system.lower():
            return _analyst_reply()
        if "ONE small edit" in system:
            return _mutator_reply(old="FOO", new="QUX")
        # Executor always says fail.
        return _executor_reply(False, "still bad")

    llm = ScriptedLLM(decide)
    result = optimize_skill(
        "demo",
        current_md=initial_body,
        scenarios=scenarios,
        llm=llm,
        max_rounds=2,
    )
    assert result.final_score == 0.0
    assert result.target_reached is False
    # No round should be accepted because score never rose.
    assert all(r.accepted is False for r in result.rounds)
    # Best-so-far remains the original body.
    assert result.final_md == initial_body


def test_optimize_records_error_when_mutation_anchor_missing():
    scenarios = [OptimizeScenario("p1", "did it work?")]

    def decide(prompt: str, system: str) -> str:
        if "diagnose" in system.lower():
            return _analyst_reply()
        if "ONE small edit" in system:
            return _mutator_reply(old="NOT-IN-BODY", new="X")
        return _executor_reply(False)

    llm = ScriptedLLM(decide)
    result = optimize_skill(
        "demo",
        current_md="hello world",
        scenarios=scenarios,
        llm=llm,
        max_rounds=2,
    )
    assert all(
        r.error == "mutation old_text not found verbatim" for r in result.rounds
    )
    assert result.final_score == 0.0


def test_optimize_max_rounds_caps_loop():
    scenarios = [OptimizeScenario("p1", "did it work?")]
    counter = {"n": 0}

    def decide(prompt: str, system: str) -> str:
        if "diagnose" in system.lower():
            return _analyst_reply()
        if "ONE small edit" in system:
            counter["n"] += 1
            # Mutate uniquely each round but never improve.
            return _mutator_reply(old="FOO", new=f"FOO{counter['n']}")
        return _executor_reply(False)

    llm = ScriptedLLM(decide)
    result = optimize_skill(
        "demo",
        current_md="FOO",
        scenarios=scenarios,
        llm=llm,
        max_rounds=3,
    )
    assert len(result.rounds) == 3


def test_optimize_on_round_callback_fires_per_iteration():
    seen: list[int] = []

    def hook(r):
        seen.append(r.round_no)

    scenarios = [OptimizeScenario("p1", "did it work?")]

    def decide(prompt: str, system: str) -> str:
        if "diagnose" in system.lower():
            return _analyst_reply()
        if "ONE small edit" in system:
            return _mutator_reply(old="FOO", new="BAR")
        return _executor_reply(False)

    llm = ScriptedLLM(decide)
    optimize_skill(
        "demo",
        current_md="FOO",
        scenarios=scenarios,
        llm=llm,
        max_rounds=2,
        on_round=hook,
    )
    assert seen == [1, 2]


def test_optimize_rejects_empty_scenarios():
    with pytest.raises(ValueError, match="at least one scenario"):
        optimize_skill(
            "demo",
            current_md="body",
            scenarios=[],
            llm=ScriptedLLM(lambda _p, _s: ""),
        )


def test_optimize_rejects_unknown_strategy_from_analyst():
    scenarios = [OptimizeScenario("p1", "did it work?")]

    def decide(prompt: str, system: str) -> str:
        if "diagnose" in system.lower():
            return _analyst_reply(strategy="rewrite_everything")
        return _executor_reply(False)

    llm = ScriptedLLM(decide)
    with pytest.raises(ValueError, match="unknown strategy"):
        optimize_skill(
            "demo",
            current_md="body",
            scenarios=scenarios,
            llm=llm,
        )


# ── Mutation-log persistence (Phase O.7) ────────────────────────


def test_mutation_record_round_trip_through_log(tmp_path, monkeypatch):
    from lyra_skills.ledger import (
        MutationRecord,
        append_mutation,
        load_mutations,
    )

    log = tmp_path / "skill_mutations.jsonl"

    rec = MutationRecord(
        ts=1700000000.0,
        skill_id="tdd-discipline",
        round_no=3,
        strategy="add_example",
        pre_score=0.5,
        post_score=0.8,
        accepted=True,
        target_section="examples",
        reasoning="anchored a python repro",
    )
    append_mutation(rec, path=log)
    append_mutation(
        MutationRecord(
            ts=1700000100.0,
            skill_id="other",
            round_no=1,
            strategy="restructure",
            pre_score=0.3,
            post_score=0.2,
            accepted=False,
        ),
        path=log,
    )

    rows = load_mutations(path=log)
    assert len(rows) == 2
    assert rows[0].skill_id == "tdd-discipline"
    assert rows[0].accepted is True
    assert rows[0].pre_score == 0.5

    filtered = load_mutations("other", path=log)
    assert len(filtered) == 1
    assert filtered[0].skill_id == "other"


def test_mutation_log_skips_malformed_lines(tmp_path):
    from lyra_skills.ledger import append_mutation, MutationRecord, load_mutations

    log = tmp_path / "skill_mutations.jsonl"
    append_mutation(
        MutationRecord(
            ts=1.0,
            skill_id="x",
            round_no=1,
            strategy="add_example",
            pre_score=0.0,
            post_score=1.0,
            accepted=True,
        ),
        path=log,
    )
    # Inject a malformed line after the good one.
    with open(log, "a", encoding="utf-8") as f:
        f.write("not json at all\n")
        f.write("\n")  # blank line
        f.write("{\"not\": \"a record\"}\n")  # parses but missing fields

    rows = load_mutations(path=log)
    # The bad-shape JSON parses as an empty record (fields default);
    # confirm we kept the good row and didn't crash.
    assert len(rows) >= 1
    assert any(r.skill_id == "x" for r in rows)

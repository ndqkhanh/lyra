"""Tests for compaction_controller.py (Phase 2)."""
from __future__ import annotations

import pytest

from lyra_core.context.compaction_controller import (
    CompactionController,
    DecisionPreservingPrompt,
    EssentialsInjector,
)


# ---------------------------------------------------------------------------
# CompactionController.check
# ---------------------------------------------------------------------------


def test_no_compact_below_trigger():
    ctrl = CompactionController(trigger_pct=0.60)
    decision = ctrl.check(0.55)
    assert not decision.should_compact
    assert "no compaction needed" in decision.reason


def test_compact_at_trigger():
    ctrl = CompactionController(trigger_pct=0.60)
    decision = ctrl.check(0.60)
    assert decision.should_compact
    assert "proactive" in decision.reason


def test_compact_above_trigger():
    ctrl = CompactionController(trigger_pct=0.60)
    decision = ctrl.check(0.75)
    assert decision.should_compact


def test_compact_at_ralph_threshold():
    ctrl = CompactionController(trigger_pct=0.60, ralph_pct=0.85)
    decision = ctrl.check(0.85)
    assert decision.should_compact
    assert "urgent" in decision.reason


def test_compact_above_ralph():
    ctrl = CompactionController(trigger_pct=0.60, ralph_pct=0.85)
    decision = ctrl.check(0.95)
    assert decision.should_compact
    assert "urgent" in decision.reason


def test_utilisation_stored_in_decision():
    ctrl = CompactionController(trigger_pct=0.60)
    d = ctrl.check(0.72)
    assert d.utilisation == pytest.approx(0.72)
    assert d.trigger_pct == pytest.approx(0.60)


def test_invalid_trigger_pct():
    with pytest.raises(ValueError):
        CompactionController(trigger_pct=0.0)
    with pytest.raises(ValueError):
        CompactionController(trigger_pct=1.0)
    with pytest.raises(ValueError):
        CompactionController(trigger_pct=1.5)


def test_invalid_ralph_below_trigger():
    with pytest.raises(ValueError):
        CompactionController(trigger_pct=0.70, ralph_pct=0.65)


# ---------------------------------------------------------------------------
# CompactionController.select_summariser_model
# ---------------------------------------------------------------------------


def test_select_cheap_model_few_invariants():
    ctrl = CompactionController()
    model = ctrl.select_summariser_model("haiku", "sonnet", invariant_count=2)
    assert model == "haiku"


def test_select_smart_model_many_invariants():
    ctrl = CompactionController()
    model = ctrl.select_summariser_model(
        "haiku", "sonnet", invariant_count=10, invariant_threshold=6
    )
    assert model == "sonnet"


def test_select_cheap_at_threshold_minus_one():
    ctrl = CompactionController()
    model = ctrl.select_summariser_model(
        "haiku", "sonnet", invariant_count=5, invariant_threshold=6
    )
    assert model == "haiku"


def test_select_smart_at_threshold():
    ctrl = CompactionController()
    model = ctrl.select_summariser_model(
        "haiku", "sonnet", invariant_count=6, invariant_threshold=6
    )
    assert model == "sonnet"


# ---------------------------------------------------------------------------
# DecisionPreservingPrompt
# ---------------------------------------------------------------------------


def test_prompt_contains_key_sections():
    prompt = DecisionPreservingPrompt(max_tokens=500)
    text = prompt.render()
    assert "DECISIONS" in text
    assert "CONVENTIONS" in text
    assert "rationale" in text
    assert "500" in text


def test_prompt_as_system_message():
    prompt = DecisionPreservingPrompt()
    msg = prompt.as_system_message()
    assert msg["role"] == "system"
    assert isinstance(msg["content"], str)
    assert len(msg["content"]) > 0


def test_prompt_with_extra_instruction():
    prompt = DecisionPreservingPrompt()
    new_prompt = prompt.with_extra("Preserve all database schema decisions.")
    assert "Preserve all database schema decisions." in new_prompt.render()
    # original unchanged
    assert "Preserve all database schema decisions." not in prompt.render()


def test_prompt_multiple_extras():
    prompt = DecisionPreservingPrompt()
    p2 = prompt.with_extra("rule 1").with_extra("rule 2")
    text = p2.render()
    assert "rule 1" in text
    assert "rule 2" in text


def test_prompt_immutable_original_with_extra():
    prompt = DecisionPreservingPrompt(extra_instructions=["existing"])
    _ = prompt.with_extra("added")
    assert "added" not in prompt.render()


# ---------------------------------------------------------------------------
# EssentialsInjector
# ---------------------------------------------------------------------------


def test_inject_empty_essentials_noop():
    injector = EssentialsInjector()
    msgs = [{"role": "user", "content": "hello"}]
    result = injector.inject(msgs)
    assert result == msgs


def test_add_and_render():
    injector = EssentialsInjector()
    injector.add("Never mock the database.")
    injector.add("Always validate at system boundaries.")
    text = injector.render()
    assert "Never mock the database." in text
    assert "Always validate at system boundaries." in text
    assert "Context Essentials" in text


def test_inject_prepends_system_message():
    injector = EssentialsInjector()
    injector.add("No hardcoded secrets.")
    msgs = [{"role": "user", "content": "hi"}]
    result = injector.inject(msgs)
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert "No hardcoded secrets." in result[0]["content"]
    assert result[1] == msgs[0]


def test_no_duplicate_rules():
    injector = EssentialsInjector()
    injector.add("Rule A")
    injector.add("Rule A")
    assert injector.rules().count("Rule A") == 1


def test_remove_rule():
    injector = EssentialsInjector()
    injector.add("Rule A")
    injector.add("Rule B")
    removed = injector.remove(0)
    assert removed == "Rule A"
    assert injector.rules() == ["Rule B"]


def test_rules_returns_copy():
    injector = EssentialsInjector()
    injector.add("Rule A")
    rules = injector.rules()
    rules.append("injected")
    assert "injected" not in injector.rules()


def test_inject_does_not_mutate_original():
    injector = EssentialsInjector()
    injector.add("some rule")
    original = [{"role": "user", "content": "q"}]
    result = injector.inject(original)
    assert len(original) == 1  # original unchanged
    assert len(result) == 2


def test_save_and_load_essentials(tmp_path):
    path = tmp_path / "essentials.json"
    inj1 = EssentialsInjector(store_path=path)
    inj1.add("Rule 1")
    inj1.add("Rule 2")

    inj2 = EssentialsInjector(store_path=path)
    assert inj2.rules() == ["Rule 1", "Rule 2"]


def test_load_from_file(tmp_path):
    rules_file = tmp_path / "rules.txt"
    rules_file.write_text("# comment\nRule Alpha\nRule Beta\n\n")
    injector = EssentialsInjector()
    injector.load_from_file(rules_file)
    assert "Rule Alpha" in injector.rules()
    assert "Rule Beta" in injector.rules()
    assert not any(r.startswith("#") for r in injector.rules())


def test_load_corrupt_essentials_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{{not json}}")
    injector = EssentialsInjector(store_path=path)
    assert injector.rules() == []

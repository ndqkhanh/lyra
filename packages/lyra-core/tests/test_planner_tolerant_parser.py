"""Phase 4 — ``load_plan`` tolerates the 6 representative LLM output shapes.

Real LLMs (especially the cost-friendly ones we default to: DeepSeek,
Qwen) don't always emit exactly ``---\\n…\\n---\\n# Plan: …``. They
sometimes:

* prepend a sentence of prose ("Sure, here's the plan:"),
* code-fence the YAML block with ` ``` `,
* skip the frontmatter entirely and just write Markdown,
* return JSON because the prompt mentioned "structured output",
* break the closing fence,
* return pure prose.

v2.1.x's planner blew up on every shape except (1) and surfaced it as
``plan rejected: plan block not found (no '---' frontmatter fence)``.
v2.1.7 makes the parser tolerant: if it can't find a strict fenced
plan, it falls through to looser detectors and finally to a
prose-synthesizer that constructs a minimal valid Plan from the task
description. The user no longer has to drop ``--no-plan`` to work
around bored model output.
"""
from __future__ import annotations

import json

import pytest

from lyra_core.plan.artifact import Plan, PlanValidationError, load_plan


_FRONTMATTER = (
    "session_id: test-01HZZ\n"
    "created_at: 2026-04-26T20:00:00Z\n"
    "planner_model: deepseek-chat\n"
    "estimated_cost_usd: 0.001\n"
    "goal_hash: sha256:0a0a0a0a0a0a0a0a0a0a0a\n"
)

_BODY = (
    "# Plan: ship the parser\n\n"
    "## Acceptance tests\n"
    "- tests/test_parser.py::test_basic\n\n"
    "## Expected files\n"
    "- src/parser.py\n\n"
    "## Forbidden files\n\n"
    "## Feature items\n"
    "1. **(test_gen)** Write a failing test for the parser entry point\n"
    "2. **(edit)** Implement the smallest diff that passes\n\n"
    "## Open questions\n\n"
    "## Notes\n"
    "Tolerance matrix Phase 4.\n"
)


def _strict_text() -> str:
    return f"---\n{_FRONTMATTER}---\n\n{_BODY}"


# --------------------------------------------------------------------- #
# Shape 1 — strict: existing contract, must keep working.
# --------------------------------------------------------------------- #


def test_strict_frontmatter_still_parses() -> None:
    plan = load_plan(_strict_text())
    assert isinstance(plan, Plan)
    assert plan.title == "ship the parser"
    assert plan.planner_model == "deepseek-chat"
    assert len(plan.feature_items) == 2


# --------------------------------------------------------------------- #
# Shape 2 — prose prefix in front of the fence.
# --------------------------------------------------------------------- #


def test_prose_prefix_then_fenced_plan_parses() -> None:
    text = (
        "Sure! Here's the plan you asked for. Let me know if you want "
        "any tweaks.\n\n" + _strict_text()
    )
    plan = load_plan(text)
    assert plan.title == "ship the parser"


# --------------------------------------------------------------------- #
# Shape 3 — code-fenced YAML frontmatter.
# --------------------------------------------------------------------- #


def test_code_fenced_yaml_treated_as_frontmatter() -> None:
    text = "```yaml\n" + _FRONTMATTER + "```\n\n" + _BODY
    plan = load_plan(text)
    assert plan.title == "ship the parser"
    assert plan.planner_model == "deepseek-chat"


# --------------------------------------------------------------------- #
# Shape 4 — no frontmatter at all, just Markdown.
# --------------------------------------------------------------------- #


def test_missing_frontmatter_is_synthesized_with_defaults() -> None:
    plan = load_plan(_BODY)
    assert plan.title == "ship the parser"
    assert plan.planner_model  # non-empty (fallback fills it)
    assert plan.session_id  # non-empty (fallback fills it)


# --------------------------------------------------------------------- #
# Shape 5 — pure prose: no headers, no frontmatter, just text.
# --------------------------------------------------------------------- #


def test_pure_prose_synthesizes_minimal_plan() -> None:
    """When the model just says 'I will do X', synthesize a minimal Plan."""
    text = (
        "I will refactor the payment module to use the new API. "
        "First write tests, then update the call sites, then run "
        "the integration suite."
    )
    plan = load_plan(text, task_hint="refactor payment module")
    assert isinstance(plan, Plan)
    assert plan.title  # non-empty
    assert len(plan.feature_items) >= 1
    # The original prose must be preserved somewhere so the user can
    # see what the LLM actually said.
    assert "payment" in plan.notes.lower() or "payment" in plan.title.lower()


# --------------------------------------------------------------------- #
# Shape 6 — JSON object response.
# --------------------------------------------------------------------- #


def test_json_response_is_translated_to_plan() -> None:
    payload = {
        "plan": {
            "title": "ship the parser",
            "planner_model": "deepseek-chat",
            "feature_items": [
                {
                    "skill": "test_gen",
                    "description": "Write a failing parser test",
                }
            ],
            "acceptance_tests": ["tests/test_parser.py::test_basic"],
            "expected_files": ["src/parser.py"],
        }
    }
    text = json.dumps(payload)
    plan = load_plan(text)
    assert plan.title == "ship the parser"
    assert plan.planner_model == "deepseek-chat"
    assert plan.feature_items[0].skill == "test_gen"


# --------------------------------------------------------------------- #
# Pathological inputs — empty, whitespace only — fail loudly.
# --------------------------------------------------------------------- #


def test_empty_text_raises() -> None:
    with pytest.raises(PlanValidationError):
        load_plan("")


def test_whitespace_only_raises() -> None:
    with pytest.raises(PlanValidationError):
        load_plan("   \n\n   ")

"""Red tests for the plan artifact schema and YAML-frontmatter Markdown format.

Contract from docs/blocks/02-plan-mode.md:
    ---
    session_id: <ulid>
    created_at: <iso>
    planner_model: <model-id>
    estimated_cost_usd: <float>
    goal_hash: sha256:<hex>
    ---

    # Plan: <title>

    ## Acceptance tests
    - <test ref>

    ## Expected files
    - <path>

    ## Forbidden files
    - <path>

    ## Feature items
    1. **(atomic-skill)** <description>

    ## Open questions
    - <question>

    ## Notes
    <free text>
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from lyra_core.plan.artifact import (
    FeatureItem,
    Plan,
    PlanValidationError,
    load_plan,
    render_plan,
)


def _sample_plan() -> Plan:
    return Plan(
        session_id="01HXK2N000000000000000001",
        created_at="2026-04-22T14:23:00Z",
        planner_model="anthropic/claude-opus-4-7",
        estimated_cost_usd=1.20,
        goal_hash="sha256:abcdef0123456789",
        title="Add dark mode toggle",
        acceptance_tests=[
            "tests/settings/test_theme_toggle.py::test_visible",
            "tests/settings/test_theme_toggle.py::test_persists",
        ],
        expected_files=[
            "src/settings/ThemeToggle.tsx",
            "src/settings/useTheme.ts",
        ],
        forbidden_files=["package.json"],
        feature_items=[
            FeatureItem(skill="localize", description="Find theme read/write sites"),
            FeatureItem(skill="test_gen", description="Write failing tests"),
            FeatureItem(skill="edit", description="Implement useTheme hook"),
        ],
        open_questions=["Which storage key?"],
        notes="Referenced skills: localize, test_gen, edit",
    )


# --- happy-path round-trip -----------------------------------------------------


def test_render_contains_frontmatter_and_sections() -> None:
    text = render_plan(_sample_plan())
    assert text.startswith("---\n")
    assert "session_id: 01HXK2N000000000000000001" in text
    assert "goal_hash: sha256:abcdef0123456789" in text
    assert "# Plan: Add dark mode toggle" in text
    assert "## Acceptance tests" in text
    assert "## Expected files" in text
    assert "## Forbidden files" in text
    assert "## Feature items" in text
    assert "## Open questions" in text


def test_render_then_load_is_identity() -> None:
    original = _sample_plan()
    text = render_plan(original)
    loaded = load_plan(text)
    assert loaded.session_id == original.session_id
    assert loaded.title == original.title
    assert loaded.acceptance_tests == original.acceptance_tests
    assert loaded.expected_files == original.expected_files
    assert loaded.forbidden_files == original.forbidden_files
    assert [(f.skill, f.description) for f in loaded.feature_items] == [
        (f.skill, f.description) for f in original.feature_items
    ]
    assert loaded.open_questions == original.open_questions


def test_render_escapes_special_markdown_in_description() -> None:
    plan = _sample_plan()
    plan.feature_items.append(
        FeatureItem(skill="edit", description="Fix `#hashtag` and *asterisks*")
    )
    text = render_plan(plan)
    assert "Fix `#hashtag` and *asterisks*" in text


# --- validation ----------------------------------------------------------------


def test_plan_rejects_empty_title() -> None:
    with pytest.raises((ValidationError, ValueError)):
        Plan(
            session_id="s1",
            created_at="2026-04-22T00:00:00Z",
            planner_model="m",
            estimated_cost_usd=0.0,
            goal_hash="sha256:00",
            title="",
            acceptance_tests=["t"],
            expected_files=[],
            forbidden_files=[],
            feature_items=[FeatureItem(skill="edit", description="do x")],
            open_questions=[],
            notes="",
        )


def test_plan_rejects_no_feature_items() -> None:
    with pytest.raises((ValidationError, ValueError)):
        Plan(
            session_id="s1",
            created_at="2026-04-22T00:00:00Z",
            planner_model="m",
            estimated_cost_usd=0.0,
            goal_hash="sha256:00",
            title="t",
            acceptance_tests=["t"],
            expected_files=[],
            forbidden_files=[],
            feature_items=[],
            open_questions=[],
            notes="",
        )


def test_plan_requires_acceptance_tests_or_test_gen_item() -> None:
    """Lint: if no acceptance_tests, there must be at least one test_gen feature."""
    plan = Plan(
        session_id="s1",
        created_at="2026-04-22T00:00:00Z",
        planner_model="m",
        estimated_cost_usd=0.0,
        goal_hash="sha256:00",
        title="t",
        acceptance_tests=[],
        expected_files=[],
        forbidden_files=[],
        feature_items=[FeatureItem(skill="edit", description="no tests at all")],
        open_questions=[],
        notes="",
    )
    with pytest.raises(PlanValidationError):
        plan.lint()


def test_plan_lints_clean_if_test_gen_present_without_tests() -> None:
    plan = Plan(
        session_id="s1",
        created_at="2026-04-22T00:00:00Z",
        planner_model="m",
        estimated_cost_usd=0.0,
        goal_hash="sha256:00",
        title="t",
        acceptance_tests=[],
        expected_files=[],
        forbidden_files=[],
        feature_items=[
            FeatureItem(skill="test_gen", description="write failing tests"),
            FeatureItem(skill="edit", description="impl"),
        ],
        open_questions=[],
        notes="",
    )
    plan.lint()  # must not raise


def test_plan_lints_rejects_dup_feature_items() -> None:
    plan = Plan(
        session_id="s1",
        created_at="2026-04-22T00:00:00Z",
        planner_model="m",
        estimated_cost_usd=0.0,
        goal_hash="sha256:00",
        title="t",
        acceptance_tests=["t"],
        expected_files=[],
        forbidden_files=[],
        feature_items=[
            FeatureItem(skill="edit", description="do x"),
            FeatureItem(skill="edit", description="do x"),
        ],
        open_questions=[],
        notes="",
    )
    with pytest.raises(PlanValidationError):
        plan.lint()


def test_load_plan_synthesizes_when_frontmatter_missing() -> None:
    """Phase 4 (v2.1.7) — missing frontmatter is no longer fatal.

    The tolerant parser synthesizes minimal frontmatter (session_id +
    sha256 goal_hash) from defaults, emits a ``planner.format_drift``
    HIR event, and returns a usable Plan. The behavior change is
    documented in spec §7.2.
    """
    text = (
        "# Plan: hello\n\n"
        "## Acceptance tests\n- t\n\n"
        "## Feature items\n1. **(test_gen)** add a failing test\n"
    )
    plan = load_plan(text)
    assert plan.title == "hello"
    # Synth defaults always produce non-empty required fields.
    assert plan.session_id
    assert plan.goal_hash.startswith("sha256:")


def test_load_plan_falls_back_when_yaml_malformed() -> None:
    """Phase 4 — malformed YAML still produces a Plan via the prose fallback.

    Previously (v2.0.x) this raised; tolerant parsing now treats a
    broken fence as if it weren't a fence at all and falls through to
    the no-frontmatter / prose synthesizer.
    """
    text = "---\nsession_id: :::\n---\n# Plan: hello\n"
    plan = load_plan(text)
    assert plan is not None
    # Either the synthesized-frontmatter path (title="hello") or the
    # prose path (title from prose) is acceptable here.
    assert plan.title

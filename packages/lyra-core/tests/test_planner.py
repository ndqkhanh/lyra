"""Red tests for the Planner sub-loop.

Contract from docs/blocks/02-plan-mode.md:
    - Planner runs under PermissionMode.PLAN → writes DENIED
    - Planner uses read-only tools (Read/Glob/Grep)
    - Planner emits a Plan artifact (Markdown + YAML frontmatter)
    - If the Planner attempts writes, they are blocked (deny, not ask)
"""
from __future__ import annotations

from pathlib import Path

from harness_core.models import MockLLM
from harness_core.tools import ToolRegistry

from lyra_core.plan.planner import PlannerResult, run_planner
from lyra_core.tools import register_builtin_tools

# ---------------------------------------------------------------------------
# Core contract: planner is read-only
# ---------------------------------------------------------------------------


def test_planner_denies_writes(repo: Path) -> None:
    """If the planner tries to Write, it must be blocked."""
    llm = MockLLM(
        scripted_outputs=[
            {
                "text": "let me try to edit",
                "tool_calls": [
                    {"id": "c1", "name": "Write", "args": {"path": "src/x.py", "content": "x"}}
                ],
            },
            {
                "text": (
                    "---\n"
                    "session_id: 01HPLAN00000000000000000\n"
                    "created_at: 2026-04-22T00:00:00Z\n"
                    "planner_model: mock\n"
                    "estimated_cost_usd: 0.0\n"
                    "goal_hash: sha256:00\n"
                    "---\n"
                    "# Plan: Demo\n\n"
                    "## Acceptance tests\n- tests/test_x.py::test_y\n\n"
                    "## Expected files\n- src/x.py\n\n"
                    "## Forbidden files\n\n"
                    "## Feature items\n1. **(edit)** do the thing\n\n"
                    "## Open questions\n\n"
                    "## Notes\nplan produced\n"
                ),
            },
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, repo_root=repo)

    result = run_planner(
        task="please add a thing",
        llm=llm,
        tools=tools,
        repo_root=repo,
        session_id="01HPLAN00000000000000000",
    )
    assert isinstance(result, PlannerResult)
    # Write attempt must have been blocked.
    assert result.blocked_write_attempts >= 1
    # Produced plan survives despite the blocked attempt.
    assert result.plan is not None
    assert result.plan.title == "Demo"
    # File was NOT created.
    assert not (repo / "src" / "x.py").exists()


def test_planner_allows_reads(repo: Path) -> None:
    (repo / "README.md").write_text("# hello")
    llm = MockLLM(
        scripted_outputs=[
            {
                "text": "reading",
                "tool_calls": [
                    {"id": "c1", "name": "Read", "args": {"path": "README.md"}}
                ],
            },
            {
                "text": (
                    "---\n"
                    "session_id: 01HPLAN00000000000000000\n"
                    "created_at: 2026-04-22T00:00:00Z\n"
                    "planner_model: mock\n"
                    "estimated_cost_usd: 0.0\n"
                    "goal_hash: sha256:00\n"
                    "---\n"
                    "# Plan: Demo\n\n"
                    "## Acceptance tests\n- tests/test_x.py::test_y\n\n"
                    "## Expected files\n- src/x.py\n\n"
                    "## Forbidden files\n\n"
                    "## Feature items\n1. **(edit)** do the thing\n\n"
                    "## Open questions\n\n"
                    "## Notes\n\n"
                ),
            },
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, repo_root=repo)

    result = run_planner(
        task="please add a thing",
        llm=llm,
        tools=tools,
        repo_root=repo,
        session_id="01HPLAN00000000000000000",
    )
    assert result.plan is not None
    assert result.blocked_write_attempts == 0


def test_planner_returns_result_with_plan_and_diagnostics(repo: Path) -> None:
    llm = MockLLM(
        scripted_outputs=[
            {
                "text": (
                    "---\n"
                    "session_id: 01HPLAN00000000000000000\n"
                    "created_at: 2026-04-22T00:00:00Z\n"
                    "planner_model: mock\n"
                    "estimated_cost_usd: 0.0\n"
                    "goal_hash: sha256:00\n"
                    "---\n"
                    "# Plan: Demo\n\n"
                    "## Acceptance tests\n- tests/test_x.py::test_y\n\n"
                    "## Expected files\n- src/x.py\n\n"
                    "## Forbidden files\n\n"
                    "## Feature items\n1. **(edit)** do the thing\n\n"
                    "## Open questions\n\n"
                    "## Notes\n\n"
                ),
            },
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, repo_root=repo)
    result = run_planner(
        task="t",
        llm=llm,
        tools=tools,
        repo_root=repo,
        session_id="01HPLAN00000000000000000",
    )
    assert result.plan is not None
    assert result.cost_usd >= 0
    assert result.steps >= 1
    assert result.transcript  # non-empty


def test_planner_rejects_plan_that_fails_lint(repo: Path) -> None:
    """Planner output with no acceptance tests and no test_gen → lint failure."""
    llm = MockLLM(
        scripted_outputs=[
            {
                "text": (
                    "---\n"
                    "session_id: 01HPLAN00000000000000000\n"
                    "created_at: 2026-04-22T00:00:00Z\n"
                    "planner_model: mock\n"
                    "estimated_cost_usd: 0.0\n"
                    "goal_hash: sha256:00\n"
                    "---\n"
                    "# Plan: Demo\n\n"
                    "## Acceptance tests\n\n"
                    "## Expected files\n\n"
                    "## Forbidden files\n\n"
                    "## Feature items\n1. **(edit)** do the thing\n\n"
                    "## Open questions\n\n"
                    "## Notes\n\n"
                ),
            },
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, repo_root=repo)
    result = run_planner(
        task="t",
        llm=llm,
        tools=tools,
        repo_root=repo,
        session_id="01HPLAN00000000000000000",
    )
    assert result.plan is None
    assert result.lint_error is not None
    assert "acceptance" in result.lint_error.lower() or "test_gen" in result.lint_error.lower()


def test_planner_synthesizes_when_output_is_pure_prose(repo: Path) -> None:
    """Phase 4 (v2.1.7) — pure-prose output now synthesizes a Plan.

    Previously this returned ``result.plan is None``; the tolerant
    parser introduced in v2.1.7 (spec §7.2) produces a minimal Plan
    from the prose so the run can continue. The original prose is
    preserved in ``Plan.notes`` so a human reviewer can audit what
    the model said.
    """
    llm = MockLLM(
        scripted_outputs=[
            {"text": "sorry I cannot produce a plan"},
        ]
    )
    tools = ToolRegistry()
    register_builtin_tools(tools, repo_root=repo)
    result = run_planner(
        task="t",
        llm=llm,
        tools=tools,
        repo_root=repo,
        session_id="01HPLAN00000000000000000",
    )
    assert result.plan is not None, "tolerant parser must synthesize from prose"
    assert "sorry" in result.plan.notes.lower() or "plan" in result.plan.notes.lower()
    # No parse or lint error — the synthesizer produces a valid Plan.
    assert result.parse_error is None
    assert result.lint_error is None

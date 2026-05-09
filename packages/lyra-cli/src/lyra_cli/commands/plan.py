"""`lyra plan <task>` — produce a plan artifact under Plan Mode."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import typer
from harness_core.tools import ToolRegistry
from rich.console import Console

from lyra_core.plan import (
    ApprovalOutcome,
    approve_plan,
    plan_skip_decision,
    render_plan,
    run_planner,
)
from lyra_core.tools import register_builtin_tools

from ..llm_factory import build_llm
from ..paths import RepoLayout

_console = Console()


def plan_command(
    task: str = typer.Argument(..., help="What you want Lyra to plan."),
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo to operate in."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Auto-approve the plan (CI flag)."
    ),
    llm: str = typer.Option(
        "auto",
        "--llm",
        help=(
            "LLM provider. auto (default) tries Anthropic → OpenAI → "
            "Gemini → DeepSeek → xAI → Groq → Cerebras → Mistral → "
            "OpenRouter → LM Studio → Ollama → mock. Explicit values: "
            "mock, anthropic, openai, openai-reasoning, gemini, "
            "deepseek, xai, groq, cerebras, mistral, openrouter, "
            "lmstudio, ollama."
        ),
    ),
) -> None:
    """Produce a plan artifact for a task without executing it."""
    repo_root = repo_root.resolve()
    layout = RepoLayout(repo_root=repo_root)
    layout.ensure()

    skip = plan_skip_decision(task)
    if skip.skip:
        _console.print(
            f"[yellow]heuristic says plan is optional[/yellow]: {skip.reason}"
        )

    session_id = _new_session_id()
    tools = ToolRegistry()
    register_builtin_tools(tools, repo_root=repo_root)

    provider = build_llm(llm, task_hint=task, session_id=session_id)
    result = run_planner(
        task=task,
        llm=provider,
        tools=tools,
        repo_root=repo_root,
        session_id=session_id,
    )

    if result.plan is None:
        err = result.parse_error or result.lint_error or "unknown planner failure"
        _console.print(f"[red]Planner failed[/red]: {err}")
        raise typer.Exit(code=2)

    plan_text = render_plan(result.plan)
    plan_path = layout.plans_dir / f"{session_id}.md"
    plan_path.write_text(plan_text)
    _console.print(f"[green]Plan written[/green] to {plan_path}")

    decision = approve_plan(result.plan, auto_approve=auto_approve)
    if decision.outcome is ApprovalOutcome.APPROVED:
        _console.print(f"[green]plan approved[/green] by {decision.approver_kind}")
    else:
        _console.print(
            f"[yellow]plan not approved[/yellow] ({decision.outcome.value}): "
            f"{decision.reason}"
        )
        raise typer.Exit(code=1)


def _new_session_id() -> str:
    ts = datetime.now(timezone.utc).isoformat()
    return "s_" + hashlib.sha256(ts.encode("utf-8")).hexdigest()[:20]

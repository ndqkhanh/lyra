"""``lyra run <task>`` — execute a task end-to-end (plan-gated by default).

v2.1 wires the actual agent loop. Pre-2.1 this command stopped after
the planner approved (with a literal "Phase 2 stops here") and the
operator never saw an answer; that was the central bug behind the
"my DeepSeek key works in `doctor` but `lyra run` does nothing"
report. Now: planner → approval → :class:`harness_core.AgentLoop` →
final answer rendered to the console.

v2.1.2 polishes the output to claude-code class:

* a one-line **header** that names the active provider/model and
  current mode (``plan`` / ``no-plan`` / ``auto-approve``) so the
  user sees *which* backend answered;
* the agent's final reply rendered inside a labelled Rich
  :class:`~rich.panel.Panel` rather than dumped naked;
* a footer line with a clean ``stop_reason`` (no
  ``StopReason.END_TURN`` Python repr leak), ``steps`` count, ``tool
  calls`` count, optional ``blocked`` count, and **elapsed time**.

The formatting helpers (``_format_*``) are pure / no-I/O so they
test independently from typer / Console and can be reused by the
REPL's ``/run`` command later.
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

import typer
from harness_core.loop import AgentLoop, LoopResult
from harness_core.messages import StopReason
from harness_core.tools import ToolRegistry
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from lyra_core.plan import (
    ApprovalOutcome,
    approve_plan,
    plan_skip_decision,
    render_plan,
    run_planner,
)
from lyra_core.tools import register_builtin_tools

from .. import __version__ as _LYRA_VERSION
from ..llm_factory import NoProviderConfigured, build_llm, describe_selection
from ..paths import RepoLayout

_console = Console()


# ---------------------------------------------------------------------------
# Output formatting helpers (pure)
# ---------------------------------------------------------------------------
#
# These render-only helpers turn agent state into Rich renderables so
# the typer command body stays focused on orchestration. Each is
# pure (no I/O, no module-level Console) so the unit tests in
# ``test_run_render.py`` can exercise them without spinning up Rich.


def _format_stop_reason(
    reason: Union[str, StopReason, None],
) -> str:
    """Strip ``StopReason.`` from the ``str(enum)`` representation.

    On Python < 3.11, ``str(StopReason.END_TURN)`` returns the
    enum's qualified name (``"StopReason.END_TURN"``) rather than
    its ``.value`` (``"end_turn"``). The agent loop hands us
    whichever it got, so we normalise both shapes here. Empty /
    ``None`` is treated as ``"end_turn"`` (the success default) so
    the footer never reads ``stop_reason: ``.
    """
    if reason is None or reason == "":
        return "end_turn"
    if isinstance(reason, StopReason):
        return reason.value
    s = str(reason)
    if s.startswith("StopReason."):
        return s[len("StopReason.") :].lower()
    return s


def _format_elapsed(seconds: float) -> str:
    """``1.4s`` for sub-minute, ``1m23s`` past 60s.

    The breakpoint at 60s keeps the footer column from sprawling into
    ``120.0s``-wide territory while still letting users distinguish
    ``0.3s`` from ``0.9s`` (cache-hit vs cold-start tells).
    """
    if seconds < 60.0:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remainder = int(round(seconds - minutes * 60))
    if remainder == 60:
        # ``59.6s`` rounded up — bump the minute, zero the seconds.
        minutes += 1
        remainder = 0
    return f"{minutes}m{remainder:02d}s"


def _format_run_header(*, provider_label: str, mode: str) -> Text:
    """Build the top-of-run header line.

    Format::

        Lyra v2.1.2 · deepseek · deepseek-v4-pro · no-plan

    The ``provider_label`` comes from :func:`describe_selection`
    which already produces ``"deepseek · deepseek-v4-pro"`` style
    output, so we just append the mode. This keeps the header the
    single source of truth for the *resolved* backend across the
    REPL banner, ``lyra doctor``, and now ``lyra run``.
    """
    line = Text(no_wrap=False)
    line.append(f"Lyra v{_LYRA_VERSION}", style="bold cyan")
    line.append("  ·  ", style="dim")
    line.append(provider_label, style="bold green")
    line.append("  ·  ", style="dim")
    line.append(mode, style="bold magenta")
    return line


def _format_token_usage(usage: Optional[dict]) -> Optional[str]:
    """Compact "7 in / 4 out" or "11 tokens" string from a usage dict.

    Returns ``None`` when the dict is missing / empty / all-zero so
    the footer skips the column entirely (keeps the line clean for
    local providers that don't report tokens). When only
    ``total_tokens`` is reported, render that as ``11 tokens``
    rather than the misleading ``0 in / 0 out``.
    """
    if not usage:
        return None
    p = int(usage.get("prompt_tokens") or 0)
    c = int(usage.get("completion_tokens") or 0)
    t = int(usage.get("total_tokens") or 0)
    if p == 0 and c == 0 and t == 0:
        return None
    if p == 0 and c == 0 and t > 0:
        return f"{t} tokens"
    return f"{p} in / {c} out"


def _format_run_footer(
    result: LoopResult,
    *,
    elapsed_s: float,
    usage: Optional[dict] = None,
) -> Text:
    """Build the bottom-of-run stats line.

    Examples::

        done · 1 step · 0 tools · 7 in / 4 out · 1.4s
        done · 5 steps · 7 tools · 2 blocked · 1234 in / 567 out · 12.7s
        max_steps · 20 steps · 14 tools · 3m02s
        done · 1 step · 0 tools · 1.4s        # local provider, no usage block

    ``done`` leads on clean ``end_turn`` so successful completion
    pops; everything else (``max_steps``, ``error``, ``tool_use``)
    surfaces the raw stop reason so soft-failures don't masquerade
    as success. Token usage is shown when the provider returned a
    non-zero ``usage`` block — its presence is hard proof a real
    API answered (mocks never report tokens).
    """
    reason = _format_stop_reason(result.stop_reason)
    leader = "done" if reason == "end_turn" else reason

    step_word = "step" if result.steps == 1 else "steps"
    tool_word = "tool" if result.tool_calls_count == 1 else "tools"

    parts = [
        leader,
        f"{result.steps} {step_word}",
        f"{result.tool_calls_count} {tool_word}",
    ]
    if result.blocked_calls_count:
        parts.append(f"{result.blocked_calls_count} blocked")
    usage_str = _format_token_usage(usage)
    if usage_str:
        parts.append(usage_str)
    parts.append(_format_elapsed(elapsed_s))

    line = Text(no_wrap=False)
    style_for_leader = "bold green" if leader == "done" else "bold yellow"
    for i, part in enumerate(parts):
        if i == 0:
            line.append(part, style=style_for_leader)
        else:
            line.append(part, style="dim")
        if i < len(parts) - 1:
            line.append(" · ", style="dim")
    return line


def _render_answer_panel(final_text: str) -> Optional[Panel]:
    """Wrap the agent's final reply in a labelled Rich panel.

    Returns ``None`` when there's nothing to render — callers should
    skip printing rather than emit an empty box.
    """
    if not final_text:
        return None
    return Panel(
        final_text,
        title="[bold]answer[/bold]",
        title_align="left",
        border_style="cyan",
        padding=(0, 1),
    )


def run_command(
    task: str = typer.Argument(..., help="What you want Lyra to do."),
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo to operate in."
    ),
    no_plan: bool = typer.Option(
        False, "--no-plan", help="Bypass Plan Mode (trivial tasks only)."
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Auto-approve produced plan (CI flag)."
    ),
    llm: str = typer.Option(
        "auto",
        "--llm",
        "--model",
        help=(
            "LLM provider. auto (default) tries Anthropic → OpenAI → "
            "Gemini → DeepSeek → xAI → Groq → Cerebras → Mistral → "
            "Qwen (DashScope) → OpenRouter → LM Studio → Ollama, then "
            "raises if nothing is configured. Explicit values: mock, "
            "anthropic, openai, openai-reasoning, gemini, deepseek, "
            "xai, groq, cerebras, mistral, qwen, openrouter, lmstudio, "
            "ollama."
        ),
    ),
    max_steps: int = typer.Option(
        20,
        "--max-steps",
        help=(
            "Hard cap on agent loop iterations. Each iteration is one "
            "LLM round-trip (think → act). Defaults to 20, which is "
            "deep enough for nontrivial tasks without being a runaway."
        ),
    ),
) -> None:
    """Run a task end-to-end. Plan Mode is default-on unless the heuristic auto-skips."""
    repo_root = repo_root.resolve()
    layout = RepoLayout(repo_root=repo_root)
    layout.ensure()

    skip = plan_skip_decision(task)
    effective_no_plan = no_plan or skip.skip
    session_id = _new_session_id()

    # Build the provider once — both the planner and the agent loop use
    # the same backend so a single key/quota miss doesn't surface twice.
    try:
        provider = build_llm(llm, task_hint=task, session_id=session_id)
    except NoProviderConfigured as exc:
        _console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    # ---- run header --------------------------------------------------
    # Print *which backend answered* before the work starts. Costs
    # nothing and removes the "wtf, was that even my deepseek key?"
    # ambiguity. ``describe_selection(llm)`` returns the same string
    # the REPL banner uses, so the two surfaces stay in lock-step.
    if effective_no_plan:
        mode_label = "auto-skip" if skip.skip else "no-plan"
    elif auto_approve:
        mode_label = "plan · auto-approve"
    else:
        mode_label = "plan"
    _console.print(
        _format_run_header(
            provider_label=describe_selection(llm),
            mode=mode_label,
        )
    )

    tools = ToolRegistry()
    register_builtin_tools(tools, repo_root=repo_root)

    if not effective_no_plan:
        planner_result = run_planner(
            task=task,
            llm=provider,
            tools=tools,
            repo_root=repo_root,
            session_id=session_id,
        )
        if planner_result.plan is None:
            err = planner_result.parse_error or planner_result.lint_error or "?"
            _console.print(f"[red]Planner failed[/red]: {err}")
            raise typer.Exit(code=2)

        plan_text = render_plan(planner_result.plan)
        (layout.plans_dir / f"{session_id}.md").write_text(plan_text)

        approval = approve_plan(planner_result.plan, auto_approve=auto_approve)
        if approval.outcome is not ApprovalOutcome.APPROVED:
            _console.print(
                f"[red]plan rejected[/red]: {approval.reason} "
                "(use --auto-approve in CI or approve interactively)"
            )
            raise typer.Exit(code=1)
        _console.print(
            f"[green]plan approved by {approval.approver_kind}[/green]"
        )
    else:
        if skip.skip:
            _console.print(
                f"[yellow]plan auto-skipped[/yellow]: {skip.reason}"
            )
        else:
            _console.print("[yellow]plan bypassed via --no-plan[/yellow]")

    # ---- agent loop --------------------------------------------------
    # The provider may already have served the planner; re-use it for
    # execution so a single rate-limited backend isn't double-charged.
    # ``time.monotonic`` (not ``time.time``) so wall-clock jumps
    # during a long run don't poison the elapsed display.
    loop = AgentLoop(llm=provider, tools=tools, max_steps=max_steps)
    started = time.monotonic()
    try:
        result = loop.run(task)
    except Exception as exc:
        # Any provider-level failure (HTTP error, deserialisation crash,
        # tool registry misconfiguration) lands here; surface it in red
        # and bubble out with a non-zero exit so CI catches it.
        elapsed = time.monotonic() - started
        _console.print(
            f"[red]agent run failed[/red] after "
            f"{_format_elapsed(elapsed)}: {exc}"
        )
        raise typer.Exit(code=3) from exc

    elapsed = time.monotonic() - started

    answer = _render_answer_panel(result.final_text)
    if answer is not None:
        _console.print(answer)
    # Surface cumulative token usage when the provider tracks it
    # (every OpenAI-compatible preset does after v2.1.3). Anthropic /
    # Gemini / Ollama may or may not — ``getattr`` keeps us safe and
    # the footer hides the column when nothing useful is available.
    usage = getattr(provider, "cumulative_usage", None)
    _console.print(_format_run_footer(result, elapsed_s=elapsed, usage=usage))

    if result.stop_reason == "max_steps":
        # Loud-but-soft: completing at the step cap usually means the
        # task is too big for one ``run`` invocation. Exit non-zero so
        # CI flags it, but keep the final text printed above so users
        # can see how far the agent got.
        raise typer.Exit(code=4)


def _new_session_id() -> str:
    ts = datetime.now(timezone.utc).isoformat()
    return "s_" + hashlib.sha256(ts.encode("utf-8")).hexdigest()[:20]

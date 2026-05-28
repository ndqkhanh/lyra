"""Lyra CLI entry point.

Subcommands:
    init     — scaffold SOUL.md + .lyra/
    run      — end-to-end task (plan-gated by default)
    plan     — produce a plan artifact only
    doctor   — health check
    session  — list / show sessions
    retro    — session retrospective
    evals    — run the evals harness (golden / red-team / swe-bench-pro / loco-eval)
    evolve   — GEPA-style prompt evolver (Phase J.5)
    brain    — install curated brain bundles (Phase J.1)
    mcp      — manage MCP server config (list / add / remove / doctor)
    acp      — host Lyra as a stdio Agent Client Protocol server

Running ``lyra`` with no subcommand launches the Ink/TypeScript TUI.
"""
from __future__ import annotations

from pathlib import Path

import typer

from . import __version__
from .commands.acp import acp_app
from .commands.agents import agents_app
from .commands.brain import brain_app
from .commands.burn import burn_app
from .commands.connect import connect_command
from .commands.context_opt import context_opt_app
from .commands.doctor import doctor_command
from .commands.evals import evals_command
from .commands.evolve import evolve_command
from .commands.hops import hops_app
from .commands.hud import hud_app
from .commands.init import init_command
from .commands.investigate import investigate_command
from .commands.mcp import mcp_app
from .commands.mcp_memory import mcp_memory_app
from .commands.memory import memory_app
from .commands.model import model_app
from .commands.plan import plan_command
from .commands.ps import ps_app
from .commands.retro import retro_command
from .commands.run import run_command
from .commands.serve import serve_command
from .commands.session import session_app
from .commands.setup import setup_command
from .commands.skill import skill_app
from .commands.skills_view import dag_app, skills_app
from .commands.status import status_app
from .commands.trace import trace_app
from .commands.tree import tree_app


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"lyra {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="lyra",
    help=(
        "Lyra — a general-purpose, CLI-native coding agent harness. "
        "Multi-provider (DeepSeek, OpenAI, Anthropic, Gemini, Ollama, "
        "Bedrock, Vertex, Copilot, OpenAI-compatible). Optional TDD "
        "plugin (off by default; enable with /tdd-gate on or "
        "/config set tdd_gate=on). Run without arguments to start an "
        "interactive session."
    ),
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print Lyra version and exit.",
    ),
    repo_root: Path = typer.Option(
        Path.cwd,
        "--repo-root",
        help="Repository root for the interactive session (default: cwd).",
    ),
    model: str = typer.Option(
        "auto",
        "--model",
        "--llm",
        help=(
            "LLM provider for the interactive session. ``auto`` (default) "
            "picks the best configured backend (DeepSeek → Anthropic → "
            "OpenAI → Gemini → xAI → Groq → Cerebras → Mistral → Qwen → "
            "OpenRouter → LM Studio → Ollama). Pass an explicit name "
            "(anthropic / openai / gemini / deepseek / qwen / ollama / "
            "mock / etc.) to pin one. ``--llm`` is an alias for "
            "``--model`` so muscle memory from `lyra run --llm ...` "
            "works at the REPL too."
        ),
    ),
    budget: float = typer.Option(
        None,
        "--budget",
        help=(
            "One-shot budget cap in USD for this session (e.g. "
            "``--budget 5.00``). Overrides the persisted default in "
            "``~/.lyra/auth.json``. The session refuses new LLM calls "
            "once spend crosses the cap; raise it any time with "
            "``/budget set <usd>`` or persist a new default with "
            "``/budget save <usd>``."
        ),
    ),
    resume: str | None = typer.Option(
        None,
        "--resume",
        "-r",
        metavar="[ID]",
        help=(
            "Resume a saved interactive session by id. ``--resume`` "
            "alone (or ``--resume latest``) attaches to the most "
            "recently modified session under ``<repo>/.lyra/"
            "sessions/``. ``--resume <id>`` (or a unique prefix) "
            "picks a specific session. The REPL boots with the "
            "restored chat history, mode, model, and cost, so a new "
            "prompt continues the previous conversation. List "
            "candidates with ``lyra session list``."
        ),
    ),
    cont: bool = typer.Option(
        False,
        "--continue",
        "-c",
        help=(
            "Shortcut for ``--resume latest``. Mirrors Claude Code's "
            "``claude --continue`` so the most recent session in "
            "this repo picks up where it left off."
        ),
    ),
    session_id: str | None = typer.Option(
        None,
        "--session",
        metavar="ID",
        help=(
            "Pin the interactive session id to ``ID``. If a session "
            "with that id already exists under ``<repo>/.lyra/"
            "sessions/``, the REPL resumes it (same as ``--resume "
            "ID``); otherwise a brand-new session is created with "
            "that id so subsequent ``--resume ID`` attaches back to "
            "this exact run. Useful for scripting and CI."
        ),
    ),
    bare: bool = typer.Option(
        False,
        "--bare",
        help=(
            "Boot in deterministic / no-auto-discovery mode. Skips "
            "skills injection, memory injection, MCP server autoload, "
            "the cron daemon, and ignores any ``permissions``/``hooks`` "
            "blocks in settings.json. Mirrors Claude Code's ``--bare`` "
            "and is the right flag for CI, headless harnesses, or any "
            "time you want a session whose behaviour is fully derived "
            "from the CLI flags alone."
        ),
    ),
    output_format: str = typer.Option(
        "text",
        "--output-format",
        help=(
            "Output format for -p / run mode: text, json, or stream-json. "
            "stream-json emits partial messages for Agent SDK compatibility."
        ),
    ),
    max_turns: int | None = typer.Option(
        None,
        "--max-turns",
        help="Maximum turns before auto-exit (headless / CI safety limit).",
    ),
    max_budget_usd: float | None = typer.Option(
        None,
        "--max-budget-usd",
        help="Maximum budget in USD before auto-exit (headless / CI safety limit).",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        metavar="NAME",
        help="Human-readable session name (stored in session metadata).",
    ),
    effort: str | None = typer.Option(
        None,
        "--effort",
        help=(
            "Effort level for this session: low, medium, high, xhigh, or max. "
            "Controls extended thinking budget and response depth."
        ),
    ),
    add_dir: list[Path] | None = typer.Option(
        None,
        "--add-dir",
        help=(
            "Additional directories the agent can access. Repeatable. "
            "Grants file read/write access beyond the repo root."
        ),
    ),
    settings_path: Path | None = typer.Option(
        None,
        "--settings",
        metavar="PATH",
        help="Path to a custom settings.json file (overrides default locations).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Start with verbose view mode (show full tool outputs).",
    ),
    bg: bool = typer.Option(
        False,
        "--bg",
        help="Dispatch session in background (daemon mode, no TTY attached).",
    ),
    goal: str | None = typer.Option(
        None,
        "--goal",
        metavar="CONDITION",
        help=(
            "Set a goal condition for auto-iteration. After each turn "
            "Lyra checks whether the condition holds and stops when "
            "met or max-turns is reached."
        ),
    ),
    permission_mode: str | None = typer.Option(
        None,
        "--permission-mode",
        metavar="MODE",
        help="Permission mode: default, acceptEdits, plan, auto, dontAsk, or bypassPermissions.",
    ),
    dangerously_skip_permissions: bool = typer.Option(
        False,
        "--dangerously-skip-permissions",
        help="Skip all permission prompts (equivalent to permission_mode=bypassPermissions).",
    ),
) -> None:
    """Lyra."""
    if ctx.invoked_subcommand is not None:
        return

    from .tui_launcher import launch_tui

    typer.echo("Launching Lyra TUI...", err=True)
    raise typer.Exit(launch_tui())


app.command("init")(init_command)
app.command("run")(run_command)
app.command("plan")(plan_command)
app.command("investigate")(investigate_command)
app.command("connect")(connect_command)
app.command("doctor")(doctor_command)
app.command("setup")(setup_command)
app.command("serve")(serve_command)
app.command("retro")(retro_command)
app.command("evals")(evals_command)
app.command("evolve")(evolve_command)
app.add_typer(session_app, name="session")
app.add_typer(mcp_app, name="mcp")
app.add_typer(mcp_memory_app, name="mcp-memory")
app.add_typer(acp_app, name="acp")
app.add_typer(brain_app, name="brain")
app.add_typer(hud_app, name="hud")
app.add_typer(burn_app, name="burn")
app.add_typer(skill_app, name="skill")
app.add_typer(memory_app, name="memory")
app.add_typer(context_opt_app, name="context-opt")
app.add_typer(ps_app, name="ps")
app.add_typer(status_app, name="status")
app.add_typer(trace_app, name="trace")
app.add_typer(tree_app, name="tree")
app.add_typer(model_app, name="model")
app.add_typer(agents_app, name="agents")
app.add_typer(hops_app, name="hops")
app.add_typer(skills_app, name="skills")
app.add_typer(dag_app, name="dag")

# TUI v2 removed in Phase 4 - new CLI (Rich + Typer) is now default


if __name__ == "__main__":  # pragma: no cover
    app()

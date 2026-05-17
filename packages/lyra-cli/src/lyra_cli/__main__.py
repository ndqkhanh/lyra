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

Running ``lyra`` with no subcommand drops into the interactive
shell (Phase 13): a Claude-Code-style REPL with slash commands, status
bar, and a graceful non-TTY fallback.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .commands.acp import acp_app
from .commands.context_opt import context_opt_app
from .commands.ps import ps_app
from .commands.brain import brain_app
from .commands.burn import burn_app
from .commands.connect import connect_command
from .commands.doctor import doctor_command
from .commands.evals import evals_command
from .commands.evolve import evolve_command
from .commands.hud import hud_app
from .commands.init import init_command
from .commands.investigate import investigate_command
from .commands.mcp import mcp_app
from .commands.mcp_memory import mcp_memory_app
from .commands.memory import memory_app
from .commands.plan import plan_command
from .commands.retro import retro_command
from .commands.run import run_command
from .commands.serve import serve_command
from .commands.session import session_app
from .commands.setup import setup_command
from .commands.skill import skill_app
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
    resume: Optional[str] = typer.Option(
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
    session_id: Optional[str] = typer.Option(
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
    legacy: bool = typer.Option(
        False,
        "--legacy",
        help=(
            "Boot the legacy prompt_toolkit REPL instead of the v3.14 "
            "Textual shell. Set ``LYRA_TUI=legacy`` in your shell rc "
            "to make this the default for your account. The legacy "
            "REPL is scheduled for removal in v3.15."
        ),
    ),
    legacy_tui: bool = typer.Option(
        False,
        "--legacy-tui",
        help=(
            "Boot the legacy prompt_toolkit TUI (cli/tui.py) instead of "
            "the new Textual-based tui_v2. The legacy TUI is deprecated "
            "and will be removed in v1.0.0. Use this flag only if you "
            "encounter critical bugs in tui_v2."
        ),
    ),
) -> None:
    """Lyra."""
    if ctx.invoked_subcommand is not None:
        return

    # v3.2.0 (Phase L): unify --resume / --continue / --session into
    # a single ``resume_id`` plumbed through the driver, plus an
    # optional ``pin_session_id`` that takes effect when the id
    # doesn't resolve to an existing session. Precedence mirrors
    # Claude Code:
    #   1. ``--resume <id>`` wins (must already exist; falls back to
    #       a fresh auto-id session with a stderr warning when missing)
    #   2. ``--continue`` is a shortcut for "latest"
    #   3. ``--session <id>`` resumes when the id exists, otherwise
    #      starts a brand-new session with that exact id so subsequent
    #      ``--resume <id>`` attaches back to it
    resume_target: Optional[str] = None
    pin_id: Optional[str] = None
    if resume is not None:
        resume_target = resume or "latest"
    elif cont:
        resume_target = "latest"
    elif session_id:
        resume_target = session_id
        pin_id = session_id

    # v3.15 / Phase 15 — CLI-first architecture. Bare ``lyra`` now opens
    # the streaming CLI (Claude Code style). Three modes available:
    #   * Default: tui_v2 (Textual-based TUI)
    #   * ``lyra --legacy-tui``: Old prompt_toolkit TUI (deprecated)
    #   * ``lyra --legacy``: prompt_toolkit REPL (deprecated)
    # Environment variable LYRA_TUI can override:
    #   * ``LYRA_TUI=tui`` — tui_v2 (default)
    #   * ``LYRA_TUI=legacy`` — prompt_toolkit REPL
    tui_pref = os.environ.get("LYRA_TUI", "tui").strip().lower()

    # Check for --tui flag (not in typer params, check sys.argv)
    import sys

    use_legacy = legacy or tui_pref == "legacy"
    use_legacy_tui = legacy_tui

    if not use_legacy and not use_legacy_tui:
        # Default: Launch tui_v2 (Textual-based TUI)
        try:
            from .tui_v2 import launch_tui_v2

            raise typer.Exit(launch_tui_v2(repo_root=repo_root.resolve(), model=model))
        except ImportError:
            typer.echo(
                "lyra: tui_v2 not available (harness-tui not installed). "
                "Falling back to legacy TUI.",
                err=True,
            )
            use_legacy_tui = True

    if use_legacy_tui:
        # Legacy TUI path (deprecated, will be removed in v1.0.0)
        typer.echo(
            "lyra: launching legacy TUI (cli/tui.py). This TUI is deprecated "
            "and will be removed in v1.0.0. Drop --legacy-tui to use the new "
            "Textual-based tui_v2.",
            err=True,
        )
        from .cli.tui import launch_tui
        exit_code = launch_tui(
            repo_root=repo_root.resolve(),
            model=model,
            budget_cap_usd=budget,
            session_id=session_id,
        )
        raise typer.Exit(exit_code)

    if not use_legacy:
        # This path should not be reached (tui_v2 is default)
        typer.echo(
            "lyra: unexpected path. Falling back to tui_v2.",
            err=True,
        )
        from .tui_v2 import launch_tui_v2
        raise typer.Exit(launch_tui_v2(repo_root=repo_root.resolve(), model=model))

    # Legacy path — surface a one-line deprecation hint via Click's
    # stderr stream so CliRunner can capture it without monkeypatching.
    typer.echo(
        "lyra: launching legacy prompt_toolkit REPL. The v3.14 Textual "
        "shell is now the default; drop --legacy / unset "
        "LYRA_TUI=legacy to use it. (Legacy removed in v3.15.)",
        err=True,
    )

    from .interactive.driver import run as _run_interactive

    # v3.2.0 (Phase L): unify --resume / --continue / --session into
    # a single ``resume_id`` plumbed through the driver, plus an
    # optional ``pin_session_id`` that takes effect when the id
    # doesn't resolve to an existing session. Precedence mirrors
    # Claude Code:
    #   1. ``--resume <id>`` wins (must already exist; falls back to
    #       a fresh auto-id session with a stderr warning when missing)
    #   2. ``--continue`` is a shortcut for "latest"
    #   3. ``--session <id>`` resumes when the id exists, otherwise
    #      starts a brand-new session with that exact id so subsequent
    #      ``--resume <id>`` attaches back to it
    resume_target: Optional[str] = None
    pin_id: Optional[str] = None
    if resume is not None:
        resume_target = resume or "latest"
    elif cont:
        resume_target = "latest"
    elif session_id:
        resume_target = session_id
        pin_id = session_id

    raise typer.Exit(
        _run_interactive(
            repo_root=repo_root,
            model=model,
            budget_cap_usd=budget,
            resume_id=resume_target,
            pin_session_id=pin_id,
            bare=bare,
        )
    )


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

# Optional: harness-tui shell (decoupled from Lyra's primary REPL).
try:  # pragma: no cover — optional import
    from .commands.tui import tui_app

    app.add_typer(tui_app, name="tui", help="Open the Lyra TUI (harness-tui shell).")
except ImportError:
    # harness-tui is an optional dependency; skip if unavailable.
    pass


if __name__ == "__main__":  # pragma: no cover
    app()

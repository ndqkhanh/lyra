"""First-run onboarding wizard for the ``lyra`` REPL.

The contract is intentionally small:

* :func:`should_run_wizard` — returns ``True`` iff the wizard should
  fire on this REPL launch. False for headless invocations (no TTY),
  for users who already have an env-var key, for repeat users who
  saved a key on a previous run, and for users who dismissed the
  wizard with ``/skip-onboarding``.
* :func:`render_welcome` — Rich :class:`~rich.text.Text` shown above
  the connect dialog. Pure: no I/O, no prompts.
* :func:`run_wizard` — the orchestrator. Prints the welcome, calls
  into :mod:`~lyra_cli.interactive.dialog_provider` from Phase 3,
  and returns 0/1 like a Typer command would.
* :func:`dismiss_wizard` — drops a sentinel file in
  ``$LYRA_HOME/.no-onboarding`` so we never re-prompt this user.

By design we never *require* the wizard — it's an offer. The user
can always escape with Ctrl-C, paste a key into their env var, or
run ``lyra connect <provider> --key ...`` non-interactively.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from rich.console import Console
from rich.text import Text

__all__ = [
    "dismiss_wizard",
    "render_welcome",
    "run_wizard",
    "should_run_wizard",
]


# Provider env vars we treat as "user already configured something".
# Kept aligned with :mod:`lyra_cli.providers.openai_compatible` so a
# project-local DEEPSEEK_API_KEY suppresses the wizard the same way
# ANTHROPIC_API_KEY does.
_ENV_VAR_HINTS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "DASHSCOPE_API_KEY",
    "QWEN_API_KEY",
    "XAI_API_KEY",
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
)

_DISMISS_FILENAME = ".no-onboarding"


def _has_env_key() -> bool:
    """True iff at least one provider env var is set to a non-empty value."""
    return any(os.environ.get(var) for var in _ENV_VAR_HINTS)


def _is_dismissed() -> bool:
    """True iff the sentinel file exists in $LYRA_HOME."""
    from lyra_core.auth.store import lyra_home

    return (lyra_home() / _DISMISS_FILENAME).exists()


def _is_tty() -> bool:
    """Both stdin and stdout must be TTYs for the wizard to be safe."""
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except (AttributeError, ValueError):
        return False


def should_run_wizard() -> bool:
    """Return ``True`` iff this looks like a true first-run interactive launch."""
    if not _is_tty():
        return False
    if _has_env_key():
        return False
    if _is_dismissed():
        return False
    from lyra_core.auth.store import has_any_provider

    return not has_any_provider()


def dismiss_wizard() -> None:
    """Persist a sentinel so future launches skip the wizard.

    Used by ``/skip-onboarding`` and by the wizard's "Skip" choice.
    Idempotent — re-creates the file on each call so a partial
    previous run never leaves us in a half-state.
    """
    from lyra_core.auth.store import lyra_home

    home = lyra_home()
    home.mkdir(parents=True, exist_ok=True)
    sentinel = home / _DISMISS_FILENAME
    sentinel.write_text(
        "lyra-onboarding-dismissed\n"
        "Delete this file (or run `lyra connect`) to re-enable the wizard.\n",
        encoding="utf-8",
    )


def render_welcome() -> Text:
    """Build the Rich welcome panel for the wizard's first frame.

    Static content — keeping it pure means tests can render and grep
    without spinning up a Console.
    """
    out = Text()
    out.append("Welcome to Lyra! ", style="bold cyan")
    out.append("Let's connect a provider so we can start building.\n\n", style="cyan")
    out.append(
        "Lyra works with Anthropic, OpenAI, Gemini, DeepSeek, Qwen, "
        "and Ollama out of the box.\n",
        style="dim",
    )
    out.append(
        "We'll save your API key to ~/.lyra/auth.json (mode 0600).\n\n",
        style="dim",
    )
    out.append("Tip: ", style="bold yellow")
    out.append("press Ctrl-C any time to skip this and use env vars instead.\n", style="dim")
    return out


def run_wizard(*, console: Optional[Console] = None) -> int:
    """Drive the welcome panel + provider picker on a fresh-install repo.

    Returns:
        0 — user picked a provider and saved a key.
        1 — user cancelled / aborted.
        2 — picker failed (preflight error, unknown provider, etc.).
    """
    console = console or Console()

    console.print()
    console.print(render_welcome())
    console.print()

    try:
        # Phase 3 ships ``run_provider_dialog`` — same UX whether the
        # user typed ``lyra connect`` or arrived here via the wizard.
        from .dialog_provider import run_provider_dialog

        return run_provider_dialog(None, console=console)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]onboarding skipped.[/yellow] "
                      "Run [cyan]lyra connect[/cyan] when you're ready.")
        return 1

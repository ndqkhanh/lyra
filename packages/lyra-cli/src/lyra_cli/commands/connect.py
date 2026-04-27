"""``lyra connect`` — pick a provider, paste a key, persist it.

Two operating modes:

1. **Non-interactive** (``--key sk-... --no-prompt``) — used by CI, by
   headless setup scripts, and by ``make install-bin`` follow-ups.
   Preflight runs by default; ``--no-preflight`` skips it for offline
   bring-up.
2. **Interactive** — opens a Rich-rendered provider picker, then a
   masked prompt_toolkit input for the API key. Implemented in
   :mod:`~lyra_cli.interactive.dialog_provider` /
   :mod:`~lyra_cli.interactive.dialog_apikey`. Reached when the user
   runs ``lyra connect`` with no arguments, or ``lyra connect <prov>``
   without ``--key``.

Provider name aliases align with :mod:`~lyra_cli.providers.openai_compatible`
so ``lyra connect qwen --key ...`` and ``lyra connect dashscope ...``
both write to a key the auto-cascade can later read.
"""
from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from lyra_core.auth.preflight import preflight
from lyra_core.auth.store import (
    get_api_key,
    list_providers,
    revoke as _revoke_provider,
    save,
)

_console = Console()


# Providers we know how to preflight and what to call them in the UI.
# Order is "first-class above the fold, then everyone else" so the
# picker (Phase 8) can split on the first six names.
FIRST_CLASS = ("anthropic", "openai", "gemini", "deepseek", "qwen", "ollama")
_SUPPORTED = (
    *FIRST_CLASS,
    "xai",
    "groq",
    "cerebras",
    "mistral",
    "openrouter",
    "dashscope",
    "lmstudio",
    "vllm",
    # v2.3.0: cloud-routed Anthropic via Bedrock, cloud-routed Gemini
    # via Vertex AI, and GitHub Copilot. Connect just stores their
    # credentials in auth.json — actual auth setup
    # (boto3 chain / ADC / GitHub OAuth) lives outside Lyra.
    "bedrock",
    "vertex",
    "copilot",
)


def _print_supported_providers() -> None:
    """Render the supported-provider list when the user fat-fingered one."""
    _console.print("[bold]Supported providers:[/bold]")
    _console.print(
        "  • first-class: " + " · ".join(FIRST_CLASS)
    )
    others = [p for p in _SUPPORTED if p not in FIRST_CLASS]
    _console.print("  • additional:  " + " · ".join(others))


def _list_action() -> None:
    """Print every saved provider name (or a friendly ``no providers`` line)."""
    saved = list_providers()
    if not saved:
        _console.print(
            "[yellow]no providers saved yet[/yellow] — run "
            "[cyan]lyra connect <provider>[/cyan] to add one."
        )
        return
    _console.print(
        Panel(
            Text("\n".join(f"  • {p}" for p in saved), style="green"),
            title="Saved providers",
            border_style="green",
        )
    )


def _revoke_action(provider: str) -> int:
    """Remove ``provider`` from auth.json. Idempotent."""
    if provider not in list_providers():
        _console.print(
            f"[yellow]no saved key for {provider}[/yellow] — nothing to revoke."
        )
        return 0
    _revoke_provider(provider)
    _console.print(
        f"[green]✓[/green] revoked saved key for [bold]{provider}[/bold]."
    )
    return 0


def _interactive_dialog(provider: Optional[str]) -> int:
    """Open the Rich + prompt_toolkit interactive picker.

    Imported lazily so non-interactive callers (CI, ``--no-prompt``)
    don't pay the prompt_toolkit import tax. Falls back to a friendly
    message when stdin is not a TTY (e.g. piped from a script that
    forgot to pass ``--key``).
    """
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        _console.print(
            "[red]connect requires a TTY for interactive prompts.[/red]\n"
            "Pass [cyan]--key <api-key> --no-prompt[/cyan] for headless usage."
        )
        return 2
    from ..interactive.dialog_provider import run_provider_dialog

    return run_provider_dialog(provider, console=_console)


def connect_command(
    provider: Optional[str] = typer.Argument(
        None,
        help=(
            "Provider to connect (anthropic, openai, gemini, deepseek, "
            "qwen, ollama, …). Omit to open the interactive picker."
        ),
    ),
    key: Optional[str] = typer.Option(
        None,
        "--key",
        help="API key. With ``--no-prompt`` this disables the masked input.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Optional default model slug to remember alongside the key.",
    ),
    no_prompt: bool = typer.Option(
        False,
        "--no-prompt",
        help="Skip every interactive prompt. Requires --key.",
    ),
    no_preflight: bool = typer.Option(
        False,
        "--no-preflight",
        help="Skip the network round-trip that verifies the key (offline use).",
    ),
    list_saved: bool = typer.Option(
        False,
        "--list",
        help="Print every saved provider and exit.",
    ),
    revoke: bool = typer.Option(
        False,
        "--revoke",
        help="Remove the saved key for <provider>. Combine with the provider name.",
    ),
    timeout: float = typer.Option(
        5.0,
        "--timeout",
        help="Preflight timeout in seconds.",
    ),
) -> None:
    """Connect a provider — non-interactive when ``--key`` is given, picker otherwise."""
    if list_saved:
        _list_action()
        raise typer.Exit(0)

    if revoke:
        if not provider:
            _console.print(
                "[red]--revoke needs a provider name[/red]: "
                "[cyan]lyra connect openai --revoke[/cyan]"
            )
            raise typer.Exit(2)
        raise typer.Exit(_revoke_action(provider))

    if provider is None:
        raise typer.Exit(_interactive_dialog(None))

    if provider not in _SUPPORTED:
        _console.print(f"[red]unknown provider:[/red] {provider}")
        _print_supported_providers()
        raise typer.Exit(2)

    if no_prompt:
        if not key:
            _console.print(
                "[red]--no-prompt requires --key[/red] (no way to ask "
                "for one without a TTY)."
            )
            raise typer.Exit(2)
    elif not key:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            _console.print(
                "[red]connect needs a TTY when no --key is provided[/red]."
            )
            raise typer.Exit(2)
        from ..interactive.dialog_apikey import prompt_api_key

        key = prompt_api_key(provider, console=_console)
        if not key:
            _console.print("[yellow]aborted: no key entered.[/yellow]")
            raise typer.Exit(1)

    existing = get_api_key(provider)
    if existing and existing != key and not no_prompt:
        if sys.stdin.isatty() and sys.stdout.isatty():
            confirm = typer.confirm(
                f"Replace existing key for {provider}?", default=False
            )
            if not confirm:
                _console.print("[yellow]aborted.[/yellow]")
                raise typer.Exit(1)

    # ``bedrock`` / ``vertex`` / ``copilot`` use auth flows that aren't
    # a simple "POST a bearer token to /v1/models": Bedrock walks the
    # boto3 credential chain, Vertex needs Google ADC, Copilot
    # exchanges a GitHub OAuth token for a session token. Their
    # preflight has to live elsewhere (or be deferred to first call),
    # so we skip the generic HTTP preflight and tell the user how to
    # verify manually.
    _PREFLIGHT_DEFERRED = {"bedrock", "vertex", "copilot"}

    if provider in _PREFLIGHT_DEFERRED:
        _console.print(
            f"[dim]preflight skipped for {provider} — "
            "auth chain runs at first chat call.[/dim]"
        )
    elif not no_preflight:
        _console.print(
            f"[dim]preflight {provider} …[/dim]", end="\r"
        )
        result = preflight(provider, key, timeout=timeout)
        _console.print(" " * 40, end="\r")  # clear the spinner line
        if not result.ok:
            _console.print(
                Panel(
                    Text(result.detail, style="red"),
                    title=f"Preflight failed: {provider}",
                    border_style="red",
                )
            )
            raise typer.Exit(2)
        if result.model_count:
            _console.print(
                f"[green]✓[/green] preflight ok — {provider} "
                f"reports {result.model_count} models."
            )
        else:
            _console.print(
                f"[green]✓[/green] preflight ok — {provider}."
            )

    save(provider, key, model=model)
    label = f"{provider}" if not model else f"{provider} · {model}"
    _console.print(
        f"[green]✓[/green] connected [bold]{label}[/bold] — "
        f"key saved to ~/.lyra/auth.json (mode 0600)."
    )
    raise typer.Exit(0)


__all__ = ["connect_command", "FIRST_CLASS"]

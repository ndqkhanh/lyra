"""Provider picker for the interactive connect-flow.

Renders a Rich panel listing the six first-class providers above the
fold ("anthropic / openai / gemini / deepseek / qwen / ollama"), then
the additional names below, and asks the user to enter the provider
name (auto-completed) or a 1-based index. Designed to feel like
opencode's picker but built on stdlib + Rich + ``typer.prompt`` so we
don't fight prompt_toolkit's session over stdin ownership.

The dialog is intentionally minimal: a more elaborate keyboard-driven
state machine lands in Phase 7 alongside the command palette. For
v2.1.6 we just need a usable, headless-fallback-aware way to ask
"which provider?" and then call :mod:`~lyra_cli.commands.connect`'s
non-interactive path with the picked name.
"""
from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

__all__ = ["run_provider_dialog"]


_FIRST_CLASS = ("anthropic", "openai", "gemini", "deepseek", "qwen", "ollama")
_ADDITIONAL = (
    "xai",
    "groq",
    "cerebras",
    "mistral",
    "openrouter",
    "dashscope",
    "lmstudio",
    "vllm",
)


def _render_picker(console: Console, current: Optional[str]) -> None:
    body_lines = ["[bold cyan]First-class[/bold cyan]"]
    for i, name in enumerate(_FIRST_CLASS, 1):
        marker = "→" if name == current else " "
        body_lines.append(f"  {marker} [bold]{i}[/bold]  {name}")
    body_lines.append("")
    body_lines.append("[bold]Additional[/bold]")
    for j, name in enumerate(_ADDITIONAL, len(_FIRST_CLASS) + 1):
        marker = "→" if name == current else " "
        body_lines.append(f"  {marker} [bold]{j}[/bold]  {name}")
    body = Text.from_markup("\n".join(body_lines))
    console.print(
        Panel(
            body,
            title="lyra connect — pick a provider",
            border_style="cyan",
        )
    )


def _resolve_choice(raw: str) -> Optional[str]:
    """Resolve user input to a provider name or ``None`` for invalid."""
    raw = raw.strip().lower()
    if not raw:
        return None
    all_providers = (*_FIRST_CLASS, *_ADDITIONAL)
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(all_providers):
            return all_providers[idx]
        return None
    if raw in all_providers:
        return raw
    matches = [p for p in all_providers if p.startswith(raw)]
    if len(matches) == 1:
        return matches[0]
    return None


def run_provider_dialog(
    initial: Optional[str], *, console: Optional[Console] = None
) -> int:
    """Drive the picker → key prompt → preflight → save loop.

    Args:
        initial: Pre-filled provider name (the user typed
            ``lyra connect``  with no argument so this is None, or
            they typed ``lyra connect deepseek`` and we jumped past
            the picker).
        console: Rich console (uses module default when None).

    Returns:
        Process exit code: 0 success, 1 user cancelled, 2 invalid
        input or preflight failure.
    """
    console = console or Console()

    chosen = initial
    if chosen is None:
        _render_picker(console, current=None)
        try:
            import typer

            raw = typer.prompt(
                "Provider (number or name)", default="", show_default=False
            )
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]aborted.[/yellow]")
            return 1
        chosen = _resolve_choice(raw)
        if chosen is None:
            console.print(f"[red]unknown provider:[/red] {raw}")
            return 2

    # Hand back to the non-interactive path on the connect command,
    # which will prompt for the key (masked) and run preflight.
    from ..commands.connect import connect_command

    try:
        connect_command(
            provider=chosen,
            key=None,
            model=None,
            no_prompt=False,
            no_preflight=False,
            list_saved=False,
            revoke=False,
            timeout=5.0,
        )
    except SystemExit as e:
        # Typer raises typer.Exit which subclasses click.exceptions.Exit;
        # both surface as SystemExit when called outside the CLI. Pass
        # through whatever exit code the connect_command set.
        return int(e.code) if isinstance(e.code, int) else 0
    return 0

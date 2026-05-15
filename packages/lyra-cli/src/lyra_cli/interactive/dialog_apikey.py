"""Masked API-key input for the connect-flow.

Wraps :func:`prompt_toolkit.shortcuts.prompt` so the user's key never
echoes to the terminal (or scroll-back). Falls back to plain
``input()`` when prompt_toolkit isn't usable (no TTY, no terminfo).

Importing this module is cheap; we only pull in prompt_toolkit at
call time so non-interactive flows (``lyra connect deepseek --key
sk-... --no-prompt``) never pay the import.
"""
from __future__ import annotations

from typing import Optional

from rich.console import Console

__all__ = ["prompt_api_key"]


def prompt_api_key(
    provider: str,
    *,
    console: Optional[Console] = None,
) -> str:
    """Prompt for an API key with input masked. Empty input → ``""``.

    The returned string is never logged, never echoed, and never
    persisted by this function — it's the caller's responsibility to
    pass it through preflight + :func:`lyra_core.auth.store.save`.
    """
    from rich.box import ROUNDED
    from rich.panel import Panel
    from rich.text import Text

    console = console or Console()

    # Per-provider env var hint so the user knows the alternative
    # to typing the key right now. Pulled from llm_factory's public
    # ``provider_env_var()`` so this stays the single source of truth.
    try:
        from ..llm_factory import provider_env_var

        env_hint = provider_env_var(provider) or f"{provider.upper()}_API_KEY"
    except Exception:
        env_hint = f"{provider.upper()}_API_KEY"

    body = Text.assemble(
        ("  Paste your ", "bright_white"),
        (provider, "bold #00E5FF"),
        (" API key.\n", "bright_white"),
        ("  Input is hidden — press Enter to abort.\n\n", "italic #6B7280"),
        ("  Alternatives:\n", "bright_white"),
        (f"    • export {env_hint}=…\n", "#7C4DFF"),
        (f"    • lyra connect {provider} --key …", "#7C4DFF"),
    )
    console.print(
        Panel(
            body,
            box=ROUNDED,
            border_style="#00E5FF",
            padding=(1, 2),
            title="[bold #00E5FF]connect[/]",
            title_align="left",
            subtitle=f"[dim]provider: {provider}[/]",
            subtitle_align="right",
        )
    )

    try:
        from prompt_toolkit import prompt as _pt_prompt

        return _pt_prompt("  API key › ", is_password=True).strip()
    except (ImportError, EOFError, KeyboardInterrupt):
        return ""
    except Exception:
        # Some terminals don't expose enough cap for masked input;
        # fall back to plain getpass which is still hidden.
        try:
            from getpass import getpass

            return getpass("  API key › ").strip()
        except Exception:
            return ""

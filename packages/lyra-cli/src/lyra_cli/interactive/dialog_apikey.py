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
    console = console or Console()
    console.print(
        f"[bold]Paste your {provider} API key[/bold] "
        "[dim](input is hidden; press Enter to abort)[/dim]:"
    )
    try:
        from prompt_toolkit import prompt as _pt_prompt

        return _pt_prompt("API key › ", is_password=True).strip()
    except (ImportError, EOFError, KeyboardInterrupt):
        return ""
    except Exception:
        # Some terminals don't expose enough cap for masked input;
        # fall back to plain getpass which is still hidden.
        try:
            from getpass import getpass

            return getpass("API key › ").strip()
        except Exception:
            return ""

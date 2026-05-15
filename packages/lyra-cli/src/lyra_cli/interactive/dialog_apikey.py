"""Masked API-key input and validation for the connect-flow.

Three-tier API so callers can choose how much UX they need:

``validate_api_key(key, provider)``
    Pure function — no I/O. Returns ``(ok, reason)`` by checking
    provider-specific prefix and minimum length.

``prompt_api_key(provider, *, existing_masked, console)``
    One masked prompt. Returns the raw string (empty = aborted).
    Backward-compatible with callers that only pass ``provider``.

``request_api_key(provider, *, store, console, max_attempts)``
    Full UX flow: show existing key → prompt → validate → retry →
    save via :class:`~.key_store.KeyStore` → confirm.
    Returns ``(key, status)`` where *status* is ``"saved"``,
    ``"kept"`` (already had a key, user kept it), or ``"skipped"``.

Importing is cheap; prompt_toolkit is only pulled in at call time
so non-interactive flows (``lyra connect deepseek --key sk-...``)
never pay the import cost.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from .key_store import KeyStore

__all__ = [
    "prompt_api_key",
    "request_api_key",
    "validate_api_key",
]

# ---------------------------------------------------------------------------
# Per-provider validation rules
# ---------------------------------------------------------------------------

# Each entry: (prefix_options, min_length)
# prefix_options: tuple of accepted prefixes, or () to skip prefix check.
_PROVIDER_RULES: dict[str, tuple[tuple[str, ...], int]] = {
    "anthropic":  (("sk-ant-", "sk-an"),        40),
    "openai":     (("sk-",),                     40),
    "deepseek":   (("sk-",),                     30),
    "groq":       (("gsk_",),                    40),
    "xai":        (("xai-",),                    40),
    "openrouter": (("sk-or-",),                  40),
    "cerebras":   (("csk_",),                    40),
    "fireworks":  (("fw_",),                     20),
    "perplexity": (("pplx-",),                   40),
    "copilot":    (("ghp_", "gho_", "github_pat_", "ghu_"), 10),
    "mistral":    ((),                            30),
    "cohere":     ((),                            30),
    "together":   ((),                            30),
    "gemini":     (("AIza",),                    30),
    "qwen":       ((),                            20),
    "dashscope":  ((),                            20),
}

_DEFAULT_MIN_LEN = 16


def validate_api_key(key: str, provider: str) -> tuple[bool, str]:
    """Check *key* against *provider*'s expected format.

    Returns ``(True, "")`` on success or ``(False, reason)`` on failure.
    Unknown providers only check minimum length.
    """
    key = key.strip()
    if not key:
        return False, "key is empty"

    prefixes, min_len = _PROVIDER_RULES.get(
        provider.lower(), ((), _DEFAULT_MIN_LEN)
    )

    if len(key) < min_len:
        return False, f"key looks too short (expected ≥{min_len} chars, got {len(key)})"

    if prefixes and not any(key.startswith(p) for p in prefixes):
        expected = " or ".join(f'"{p}"' for p in prefixes)
        return False, f"{provider} keys usually start with {expected}"

    return True, ""


# ---------------------------------------------------------------------------
# Single masked prompt
# ---------------------------------------------------------------------------


def prompt_api_key(
    provider: str,
    *,
    existing_masked: str | None = None,
    console: Console | None = None,
) -> str:
    """Show an info panel then read a masked key from stdin.

    Returns the stripped key, or ``""`` if the user aborted.
    *existing_masked* (e.g. ``"****ab12"``) is shown as context when
    the user is replacing a previously stored key.
    """
    from rich.box import ROUNDED
    from rich.panel import Panel
    from rich.text import Text

    console = console or Console()

    try:
        from ..llm_factory import provider_env_var
        env_hint = provider_env_var(provider) or f"{provider.upper()}_API_KEY"
    except Exception:
        env_hint = f"{provider.upper()}_API_KEY"

    body = Text()
    body.append("  Paste your ", style="bright_white")
    body.append(provider, style="bold #00E5FF")
    body.append(" API key.\n", style="bright_white")
    if existing_masked:
        body.append(f"  Current key: {existing_masked}\n", style="dim #FACC15")
        body.append("  Press Enter (empty) to keep the existing key.\n\n", style="italic #6B7280")
    else:
        body.append("  Press Enter (empty) to skip.\n\n", style="italic #6B7280")
    body.append("  Alternatives:\n", style="bright_white")
    body.append(f"    • export {env_hint}=…\n", style="#7C4DFF")
    body.append(f"    • lyra connect {provider} --key …", style="#7C4DFF")

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
        return _pt_prompt("  API key >", is_password=True).strip()
    except (ImportError, EOFError, KeyboardInterrupt):
        return ""
    except Exception:
        try:
            from getpass import getpass
            return getpass("  API key >").strip()
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Full request-and-save flow
# ---------------------------------------------------------------------------


def request_api_key(
    provider: str,
    *,
    store: KeyStore,
    console: Console | None = None,
    max_attempts: int = 3,
) -> tuple[str, str]:
    """Prompt, validate, retry, and persist an API key for *provider*.

    Flow:
    1. If a key is already stored, show the masked value and let the
       user keep it by pressing Enter (returns ``(existing, "kept")``).
    2. Prompt for a new key with :func:`prompt_api_key`.
    3. Validate with :func:`validate_api_key`.  On failure, print the
       reason and retry up to *max_attempts* total attempts.
    4. On a valid key, save via ``store.set()`` and stamp env.

    Returns:
        ``(key, status)`` where *status* is one of:

        * ``"saved"``   — new key was entered and persisted
        * ``"kept"``    — existing key was kept (user pressed Enter)
        * ``"skipped"`` — no key entered after all attempts
    """
    from .key_store import mask_key

    console = console or Console()

    existing = store.get(provider)
    existing_key = (existing or {}).get("api_key", "")
    existing_masked = mask_key(existing_key) if existing_key else None

    for attempt in range(1, max_attempts + 1):
        raw = prompt_api_key(
            provider,
            existing_masked=existing_masked,
            console=console,
        )

        if not raw:
            if existing_key:
                console.print(
                    f"  [dim]Keeping existing key ({existing_masked}).[/dim]"
                )
                return existing_key, "kept"
            if attempt < max_attempts:
                console.print(
                    f"  [yellow]No key entered — try again "
                    f"({attempt}/{max_attempts}).[/yellow]"
                )
                continue
            console.print("  [dim]Skipped — no key saved.[/dim]")
            return "", "skipped"

        ok, reason = validate_api_key(raw, provider)
        if not ok:
            console.print(f"  [red]✗ Invalid key:[/red] {reason}")
            if attempt < max_attempts:
                console.print(
                    f"  [yellow]Please try again "
                    f"({attempt}/{max_attempts}).[/yellow]"
                )
                continue
            console.print(
                f"  [red]Giving up after {max_attempts} attempts.[/red]"
            )
            return "", "skipped"

        # Valid key — persist and confirm.
        base_url = (existing or {}).get("base_url")
        store.set(provider, raw, base_url)
        from .key_store import PROVIDER_ENV_VARS
        env = PROVIDER_ENV_VARS.get(provider, "")
        env_note = f"  [dim](${env} set in process env)[/dim]" if env else ""
        console.print(
            f"  [green]✓ Saved {provider} key "
            f"({mask_key(raw)}) → ~/.lyra/credentials.json[/green]"
        )
        if env_note:
            console.print(env_note)
        return raw, "saved"

    return "", "skipped"

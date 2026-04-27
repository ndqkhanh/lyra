"""``lyra setup`` — interactive first-run wizard (Phase N.4).

Drops a fresh user into a working configuration in <60 seconds:

1. Probe the environment (which keys / packages are already there).
2. Pick a default provider — pre-selecting the highest-precedence
   match the cascade would choose.
3. Optionally collect an API key for it (stored in
   ``~/.lyra/.env`` + chmod 600 so a stray ``cat`` doesn't leak it).
4. Pick a default model alias.
5. Write ``~/.lyra/settings.json`` (or update if present) with
   ``default_provider``, ``default_model``, ``config_version``.
6. Re-run :mod:`diagnostics` to confirm the new state.

The wizard is also driveable non-interactively via flags so CI /
docker images can pre-bake config:

    lyra setup --provider deepseek --model deepseek-flash \\
               --api-key-env DEEPSEEK_API_KEY --non-interactive

Pure logic lives in :mod:`lyra_cli.config_io` so unit tests don't
need to spawn a Typer prompt.
"""
from __future__ import annotations

import json as _json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..config_io import (
    LYRA_CONFIG_VERSION,
    load_settings,
    save_settings,
    write_env_file,
)
from ..diagnostics import (
    configured_providers,
    probe_providers,
    run_all,
)


_console = Console()


# Aliases users typically pick per provider. Mirrored from
# :mod:`lyra_core.providers.aliases` so the wizard's pre-fill stays
# in sync with what the provider cascade actually accepts.
_PROVIDER_DEFAULT_MODEL: dict[str, str] = {
    "deepseek": "deepseek-flash",
    "anthropic": "claude-sonnet-4.5",
    "openai": "gpt-5",
    "gemini": "gemini-2.5-pro",
    "xai": "grok-4",
    "groq": "llama-3.3-70b",
    "cerebras": "llama-3.3-70b",
    "mistral": "mistral-large",
    "dashscope": "qwen-max",
    "openrouter": "anthropic/claude-sonnet-4.5",
}


def _user_config_path() -> Path:
    """Where the wizard writes ``settings.json``.

    Honours ``$LYRA_HOME`` so test suites and multi-tenant hosts
    can sandbox the wizard without touching a real ``~/.lyra/``.
    """
    home = os.environ.get("LYRA_HOME")
    base = Path(home) if home else Path.home() / ".lyra"
    return base / "settings.json"


def _user_env_path() -> Path:
    """Same env-var contract as :func:`_user_config_path`, for ``.env``."""
    return _user_config_path().with_name(".env")


def setup_command(
    provider: Optional[str] = typer.Option(
        None, "--provider",
        help="Provider slug to pre-select (deepseek/anthropic/openai/...).",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="Default model alias to record.",
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key",
        help=(
            "Provider API key. Stored under $LYRA_HOME/.env. "
            "Pass `-` to read from stdin (avoid shell history)."
        ),
    ),
    non_interactive: bool = typer.Option(
        False, "--non-interactive",
        help="Fail rather than prompt — for CI / docker images.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit a JSON summary of what landed on disk.",
    ),
) -> None:
    """Run the first-run setup wizard."""
    probes = probe_providers()
    configured = configured_providers(probes)

    chosen_provider = provider or _resolve_provider(
        configured=configured, non_interactive=non_interactive,
    )
    chosen_model = model or _resolve_model(
        provider=chosen_provider, non_interactive=non_interactive,
    )

    # Key collection only happens when the user explicitly passed one
    # OR we're interactive and the chosen provider's key is missing.
    needs_key = chosen_provider not in configured
    if api_key == "-":
        api_key = _read_key_from_stdin()
    if api_key is None and needs_key and not non_interactive:
        if Confirm.ask(
            f"No API key found for [bold]{chosen_provider}[/]. "
            "Save one to $LYRA_HOME/.env now?",
            default=True,
        ):
            api_key = Prompt.ask(
                f"{chosen_provider.upper()} API key",
                password=True,
            )

    written: dict[str, Path] = {}
    if api_key:
        env_path = _user_env_path()
        var = _provider_env_var(chosen_provider)
        write_env_file(env_path, {var: api_key})
        written["env"] = env_path
        # Stamp the env into the *current* process too so the doctor
        # rerun below sees the new key without requiring a shell
        # restart.
        os.environ[var] = api_key

    settings = load_settings(_user_config_path())
    settings.update(
        {
            "config_version": LYRA_CONFIG_VERSION,
            "default_provider": chosen_provider,
            "default_model": chosen_model,
        }
    )
    save_settings(_user_config_path(), settings)
    written["settings"] = _user_config_path()

    final_probes = run_all()
    summary = {
        "provider": chosen_provider,
        "model": chosen_model,
        "wrote": {k: str(v) for k, v in written.items()},
        "ok": all(
            p.ok
            for p in final_probes
            if p.category in ("runtime",) and not p.meta.get("optional")
        ),
        "configured_providers": configured_providers(final_probes),
    }

    if json_out:
        typer.echo(_json.dumps(summary, indent=2))
        return

    table = Table(title="lyra setup — done")
    table.add_column("key")
    table.add_column("value", overflow="fold")
    table.add_row("default provider", chosen_provider)
    table.add_row("default model", chosen_model)
    for k, v in written.items():
        table.add_row(f"wrote {k}", str(v))
    _console.print(table)
    if api_key:
        _console.print(
            "[yellow]Tip:[/] add `set -a; source $HOME/.lyra/.env; set +a` "
            "to your shell profile to load the key on every session."
        )


# ---------------------------------------------------------------------------
# Helpers (kept thin so config_io can carry the heavy lifting)
# ---------------------------------------------------------------------------


def _resolve_provider(*, configured: list[str], non_interactive: bool) -> str:
    """Pick a provider, preferring already-configured ones."""
    if configured:
        first = configured[0]
        if non_interactive:
            return first
        if Confirm.ask(
            f"Use [bold]{first}[/] (already configured) as default provider?",
            default=True,
        ):
            return first
    if non_interactive:
        # No configured provider + no flag = pick the cheapest default
        # (DeepSeek tops the cascade in 2026 for cost-aware coding).
        return "deepseek"
    return Prompt.ask(
        "Default provider",
        choices=list(_PROVIDER_DEFAULT_MODEL.keys()),
        default="deepseek",
    )


def _resolve_model(*, provider: str, non_interactive: bool) -> str:
    """Pick the default model alias for *provider*."""
    fallback = _PROVIDER_DEFAULT_MODEL.get(provider, "deepseek-flash")
    if non_interactive:
        return fallback
    return Prompt.ask("Default model alias", default=fallback)


def _provider_env_var(provider: str) -> str:
    """Map provider slug → canonical env var written to ``.env``."""
    mapping = {
        "deepseek": "DEEPSEEK_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "xai": "XAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "dashscope": "DASHSCOPE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    return mapping.get(provider, f"{provider.upper()}_API_KEY")


def _read_key_from_stdin() -> str:
    """Slurp an API key from stdin, stripping the trailing newline.

    Used by the ``--api-key -`` flag so CI pipelines can pipe a key
    in via secret managers without dropping it into a process arg
    (where it'd show up in ``ps``).
    """
    import sys

    return sys.stdin.read().strip()


__all__ = ["setup_command"]

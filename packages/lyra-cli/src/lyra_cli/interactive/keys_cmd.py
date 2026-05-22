"""ECC-inspired /keys command — view and manage API provider keys.

Ports the 244-line key_store.py credential system into a usable UX:
  • /keys list — show configured providers
  • /keys show <provider> — show provider details (key hidden)
  • /keys set <provider> <key> — set an API key
  • /keys remove <provider> — remove a provider
  • /keys env — show which env vars are set
  • /keys test <provider> — test connectivity (ping the API)

ECC reference: enterprise-controls.md credential management.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from ..commands.registry import CommandResult

# ── Known providers and their env vars ─────────────────────────────────

PROVIDERS: dict[str, dict[str, str]] = {
    "anthropic": {"env": "ANTHROPIC_API_KEY", "url": "https://api.anthropic.com", "color": "yellow"},
    "openai": {"env": "OPENAI_API_KEY", "url": "https://api.openai.com", "color": "green"},
    "deepseek": {"env": "DEEPSEEK_API_KEY", "url": "https://api.deepseek.com", "color": "blue"},
    "gemini": {"env": "GEMINI_API_KEY", "url": "https://generativelanguage.googleapis.com", "color": "cyan"},
    "groq": {"env": "GROQ_API_KEY", "url": "https://api.groq.com", "color": "magenta"},
    "openrouter": {"env": "OPENROUTER_API_KEY", "url": "https://openrouter.ai/api", "color": "dim"},
    "mistral": {"env": "MISTRAL_API_KEY", "url": "https://api.mistral.ai", "color": "cyan"},
    "xai": {"env": "XAI_API_KEY", "url": "https://api.x.ai", "color": "red"},
    "together": {"env": "TOGETHER_API_KEY", "url": "https://api.together.xyz", "color": "blue"},
    "cerebras": {"env": "CEREBRAS_API_KEY", "url": "https://api.cerebras.ai", "color": "green"},
    "qwen": {"env": "DASHSCOPE_API_KEY", "url": "https://dashscope.aliyuncs.com", "color": "dim"},
    "cohere": {"env": "COHERE_API_KEY", "url": "https://api.cohere.com", "color": "green"},
}


def _mask_key(key: str) -> str:
    """Mask an API key for display."""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def _check_env(provider: str) -> tuple[bool, str]:
    """Check if a provider's env var is set."""
    info = PROVIDERS.get(provider)
    if not info:
        return False, "unknown provider"
    env_var = info["env"]
    value = os.environ.get(env_var, "")
    if value:
        return True, _mask_key(value)
    return False, ""


def _test_provider(provider: str) -> str:
    """Test connectivity to a provider's API."""
    info = PROVIDERS.get(provider)
    if not info:
        return "unknown provider"
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(info["url"], method="HEAD")
        req.timeout = 5
        urllib.request.urlopen(req)
        return "reachable"
    except urllib.error.URLError as e:
        return f"unreachable: {e.reason}"
    except Exception as e:
        return f"error: {e}"


# ── Slash command ─────────────────────────────────────────────────────

def cmd_keys(session: Any, args: str) -> CommandResult:
    """View and manage API provider keys.

    Usage:
      /keys list             — list all configured providers
      /keys show <provider>  — show provider details
      /keys set <provider> <key> — set API key (env var)
      /keys remove <provider> — unset env var
      /keys env              — show all set env vars
      /keys test <provider>  — test API connectivity
    """
    parts = args.strip().split() if args.strip() else []
    subcmd = parts[0].lower() if parts else "list"

    # ── /keys list ────────────────────────────────────────────────────
    if subcmd == "list":
        lines = ["[bold]Providers[/]"]
        configured = 0
        for name, info in sorted(PROVIDERS.items()):
            is_set, masked = _check_env(name)
            glyph = "[green]✓[/]" if is_set else "[dim]○[/]"
            color = info["color"]
            if is_set:
                configured += 1
                lines.append(f"  {glyph} [{color}]{name:<12}[/] {masked}")
            else:
                lines.append(f"  {glyph} [{color}]{name:<12}[/]")
        lines.append("")
        lines.append(f"[dim]{configured}/{len(PROVIDERS)} providers configured[/]")
        return CommandResult(
            output=f"{configured}/{len(PROVIDERS)} providers configured",
            renderable="\n".join(lines),
        )

    # ── /keys show <provider> ─────────────────────────────────────────
    if subcmd == "show":
        if len(parts) < 2:
            return CommandResult(output="Usage: /keys show <provider>")
        name = parts[1]
        info = PROVIDERS.get(name)
        if not info:
            return CommandResult(output=f"Unknown provider '{name}'. Try /keys list")

        is_set, masked = _check_env(name)
        lines = [
            f"[bold]{name}[/]",
            f"  Env:   [accent]{info['env']}[/]",
            f"  URL:   [dim]{info['url']}[/]",
            f"  Key:   {'[green]' + masked + '[/]' if is_set else '[red]not set[/]'}",
        ]
        if is_set:
            lines.append(f"  Test:  {_test_provider(name)}")
        return CommandResult(
            output=f"{name}: {'configured' if is_set else 'not configured'}",
            renderable="\n".join(lines),
        )

    # ── /keys set <provider> <key> ────────────────────────────────────
    if subcmd == "set":
        if len(parts) < 3:
            return CommandResult(output="Usage: /keys set <provider> <api_key>")
        name = parts[1]
        key = parts[2]
        info = PROVIDERS.get(name)
        if not info:
            return CommandResult(output=f"Unknown provider '{name}'. Try /keys list")

        os.environ[info["env"]] = key
        return CommandResult(output=f"✓ {info['env']} set for {name}")

    # ── /keys remove <provider> ───────────────────────────────────────
    if subcmd == "remove":
        if len(parts) < 2:
            return CommandResult(output="Usage: /keys remove <provider>")
        name = parts[1]
        info = PROVIDERS.get(name)
        if not info:
            return CommandResult(output=f"Unknown provider '{name}'")
        os.environ.pop(info["env"], None)
        return CommandResult(output=f"✓ Removed {name} (unset {info['env']})")

    # ── /keys env ─────────────────────────────────────────────────────
    if subcmd == "env":
        lines = ["[bold]Environment Variables[/]"]
        count = 0
        for name, info in sorted(PROVIDERS.items()):
            env_var = info["env"]
            value = os.environ.get(env_var, "")
            if value:
                count += 1
                lines.append(f"  [green]✓[/] [accent]{env_var}[/] = {_mask_key(value)}")
        if count == 0:
            lines.append("  [dim]No API keys set in environment[/]")
        return CommandResult(
            output=f"{count} env var(s) set",
            renderable="\n".join(lines),
        )

    # ── /keys test <provider> ─────────────────────────────────────────
    if subcmd == "test":
        if len(parts) < 2:
            return CommandResult(output="Usage: /keys test <provider>")
        name = parts[1]
        info = PROVIDERS.get(name)
        if not info:
            return CommandResult(output=f"Unknown provider '{name}'")
        is_set, _ = _check_env(name)
        if not is_set:
            return CommandResult(output=f"[yellow]⚠[/] {name}: no key set, skipping test")
        result = _test_provider(name)
        return CommandResult(
            output=f"{name}: {result}",
            renderable=f"[bold]{name}[/]  [dim]{info['url']}[/]\n  Result: {'[green]✓[/]' if 'reachable' in result else '[red]✗[/]'} {result}",
        )

    return CommandResult(output="Usage: /keys [list|show|set|remove|env|test]")


__all__ = ["cmd_keys", "PROVIDERS"]

"""ECC-inspired /auth command — OAuth provider status and device flow.

Ports auth.py's DeviceCodeAuth into a usable REPL command:
  /auth list              — show configured providers
  /auth status <provider> — show auth status for a provider
  /auth login <provider>  — start device-code OAuth flow
  /auth logout <provider> — revoke stored token

Also provides AuthStatusWidget for the TUI — a panel showing
which providers are authenticated and token expiry info.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ..commands.registry import CommandResult

# ── Known auth providers ───────────────────────────────────────────────

AUTH_PROVIDERS: dict[str, dict[str, str]] = {
    "github": {"env": "GITHUB_TOKEN", "url": "https://github.com/settings/tokens", "color": "dim"},
    "copilot": {"env": "COPILOT_TOKEN", "url": "https://github.com/settings/copilot", "color": "green"},
    "openai": {"env": "OPENAI_API_KEY", "url": "https://platform.openai.com/api-keys", "color": "green"},
    "anthropic": {"env": "ANTHROPIC_API_KEY", "url": "https://console.anthropic.com", "color": "yellow"},
    "google": {"env": "GOOGLE_API_KEY", "url": "https://aistudio.google.com/app/apikey", "color": "cyan"},
    "huggingface": {"env": "HF_TOKEN", "url": "https://huggingface.co/settings/tokens", "color": "yellow"},
}

TOKEN_DIR = Path.home() / ".lyra" / "tokens"


def _check_provider(name: str) -> dict:
    """Check auth status for a provider."""
    info = AUTH_PROVIDERS.get(name, {})
    env_var = info.get("env", "")
    env_set = bool(os.environ.get(env_var, ""))

    # Check stored token
    token_file = TOKEN_DIR / f"{name}.json"
    stored = token_file.exists()
    expired = False
    expires_at = ""
    if stored:
        try:
            import json
            data = json.loads(token_file.read_text())
            exp = data.get("expires_at", 0)
            if exp and time.time() > exp:
                expired = True
            expires_at = time.strftime("%Y-%m-%d %H:%M", time.localtime(exp)) if exp else ""
        except Exception:
            pass

    return {
        "name": name,
        "env_set": env_set,
        "stored": stored,
        "expired": expired,
        "expires_at": expires_at,
        "url": info.get("url", ""),
        "color": info.get("color", "dim"),
    }


# ── Slash command ──────────────────────────────────────────────────────

def cmd_auth(session: Any, args: str) -> CommandResult:
    """Manage OAuth provider authentication.

    Usage:
      /auth list                — show all providers
      /auth status <provider>   — show auth status
      /auth login <provider>    — start device-code OAuth flow
      /auth logout <provider>   — revoke stored token
    """
    parts = args.strip().split() if args.strip() else []
    subcmd = parts[0].lower() if parts else "list"

    if subcmd == "list":
        lines = ["[bold]Auth Providers[/]"]
        ok = 0
        for name in sorted(AUTH_PROVIDERS):
            status = _check_provider(name)
            info = AUTH_PROVIDERS[name]
            color = info.get("color", "dim")

            if status["stored"]:
                glyph = "[green]✓[/]"
                ok += 1
                expiry = f" [dim](expires {status['expires_at']})[/]" if status["expires_at"] else ""
                lines.append(f"  {glyph} [{color}]{name:<12}[/]{expiry}")
            elif status["env_set"]:
                glyph = "[yellow]✓[/]"
                ok += 1
                lines.append(f"  {glyph} [{color}]{name:<12}[/] [dim](env var)[/]")
            else:
                glyph = "[dim]○[/]"
                lines.append(f"  {glyph} [{color}]{name:<12}[/]")
        lines.append("")
        lines.append(f"[dim]{ok}/{len(AUTH_PROVIDERS)} configured[/]")
        return CommandResult(
            output=f"{ok}/{len(AUTH_PROVIDERS)} auth providers configured",
            renderable="\n".join(lines),
        )

    if subcmd == "status":
        if len(parts) < 2:
            return CommandResult(output="Usage: /auth status <provider>")
        name = parts[1]
        if name not in AUTH_PROVIDERS:
            return CommandResult(output=f"Unknown provider '{name}'")

        status = _check_provider(name)
        lines = [
            f"[bold]{name}[/]",
            f"  Env:     {status['env_set']}",
            f"  Stored:  {status['stored']}",
        ]
        if status["stored"]:
            lines.append(f"  Expired: {status['expired']}")
            if status["expires_at"]:
                lines.append(f"  Expires: {status['expires_at']}")
        lines.append(f"  URL:     [dim]{status['url']}[/]")
        return CommandResult(
            output=f"{name}: {'authenticated' if status['stored'] or status['env_set'] else 'not configured'}",
            renderable="\n".join(lines),
        )

    if subcmd == "login":
        if len(parts) < 2:
            return CommandResult(output="Usage: /auth login <provider>")
        name = parts[1]
        if name not in AUTH_PROVIDERS:
            return CommandResult(output=f"Unknown provider '{name}'")

        # Print instructions for manual key entry
        info = AUTH_PROVIDERS[name]
        lines = [
            f"[bold]Login: {name}[/]",
            f"  1. Visit: [cyan]{info['url']}[/]",
            f"  2. Create/grab an API key",
            f"  3. Set it: [accent]/keys set {name} <your-key>[/]",
        ]
        return CommandResult(
            output=f"Login instructions for {name}",
            renderable="\n".join(lines),
        )

    if subcmd == "logout":
        if len(parts) < 2:
            return CommandResult(output="Usage: /auth logout <provider>")
        name = parts[1]
        token_file = TOKEN_DIR / f"{name}.json"
        if token_file.exists():
            token_file.unlink()
            return CommandResult(output=f"✓ Logged out of {name}")
        return CommandResult(output=f"No stored token for {name}")

    return CommandResult(output="Usage: /auth [list|status|login|logout]")


# ── TUI Widget ─────────────────────────────────────────────────────────

class AuthStatusWidget(Widget):
    """Auth provider status panel — Ctrl+Shift+A to toggle.

    Shows which providers are authenticated with token expiry info.
    """

    DEFAULT_CSS = """
    AuthStatusWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    AuthStatusWidget.collapsed {
        height: 1;
        border: none;
    }

    AuthStatusWidget #auth-header {
        height: 1;
        color: $text-muted;
    }

    AuthStatusWidget #auth-content {
        height: auto;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+a", "toggle_auth", "Auth"),
    ]

    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="auth-header")
        yield Static("", id="auth-content")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_auth(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            hint = "[dim](ctrl+shift+a)[/]"
            ok = sum(1 for n in AUTH_PROVIDERS if _check_provider(n)["stored"] or _check_provider(n)["env_set"])
            total = len(AUTH_PROVIDERS)
            if self.expanded:
                self.query_one("#auth-header", Static).update(
                    f"[bold]Auth[/]  [green]{ok}[/]/{total}  {hint}"
                )
                lines = []
                for name in sorted(AUTH_PROVIDERS):
                    status = _check_provider(name)
                    info = AUTH_PROVIDERS[name]
                    color = info.get("color", "dim")
                    if status["stored"]:
                        exp = f" [dim](exp {status['expires_at'][:10]})[/]" if status["expires_at"] else ""
                        lines.append(f"  [green]✓[/] [{color}]{name:<12}[/]{exp}")
                    elif status["env_set"]:
                        lines.append(f"  [yellow]✓[/] [{color}]{name:<12}[/] [dim](env)[/]")
                    else:
                        lines.append(f"  [dim]○[/] [{color}]{name:<12}[/]")
                self.query_one("#auth-content", Static).update("\n".join(lines))
            else:
                self.query_one("#auth-header", Static).update(
                    f"[bold]Auth[/]  [green]{ok}[/]/{total}  {hint}"
                )
                self.query_one("#auth-content", Static).update("")
        except Exception:
            pass


__all__ = ["cmd_auth", "AuthStatusWidget"]

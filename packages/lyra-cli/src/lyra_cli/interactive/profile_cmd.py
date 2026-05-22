"""Profile system — ECC-inspired identity/persona for the Lyra CLI.

ECC's ``identity.json`` tracks user preferences, technical level, domains,
and preferred style. This module brings the same concept to Lyra with:

  • Persistent ``~/.lyra/profile.json`` with identity metadata
  • ``/profile`` slash command to view/edit preferences
  • ``/whoami`` alias for quick identity peek
  • Auto-detection of technical level from session behavior
  • Domain preferences for skill routing

ECC reference: ``.claude/identity.json`` structure + ``team-config.json``.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from ..commands.registry import CommandResult

# ── Default profile path ───────────────────────────────────────────────

PROFILE_PATH = Path.home() / ".lyra" / "profile.json"


# ── Data model ─────────────────────────────────────────────────────────

@dataclass
class LyraProfile:
    """User profile — persisted to ``~/.lyra/profile.json``.

    Mirrors ECC's identity.json shape.
    """
    version: str = "1.0"
    name: str = ""
    email: str = ""

    # Technical level (auto-detected, can be overridden)
    technical_level: str = "intermediate"  # beginner | intermediate | advanced | expert

    # Preferred interaction style
    verbosity: str = "balanced"  # minimal | balanced | verbose
    code_comments: bool = True
    explanations: bool = True

    # Domain preferences (for skill routing)
    domains: list[str] = field(default_factory=lambda: ["python", "typescript"])

    # Active session preferences
    default_model: str = "auto"
    default_mode: str = "edit_automatically"
    theme: str = "aurora"
    keybindings: str = "default"  # default | vim | emacs

    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    sessions_completed: int = 0

    @property
    def age_days(self) -> int:
        return int((time.time() - self.created_at) / 86400)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        """One-line identity summary for status bar."""
        domains_str = ", ".join(self.domains[:3])
        extra = f" +{len(self.domains) - 3}" if len(self.domains) > 3 else ""
        return (
            f"◆ {self.name or 'anon'} · {self.technical_level} · "
            f"{domains_str}{extra} · {self.verbosity}"
        )

    def render(self) -> str:
        """Full profile render for /profile command."""
        lines = [
            "[bold]Profile[/]",
            f"  Name:        [accent]{self.name or '(not set)'}[/]",
            f"  Email:       [dim]{self.email or '(not set)'}[/]",
            f"  Level:       [cyan]{self.technical_level}[/]",
            f"  Verbosity:   [dim]{self.verbosity}[/]",
            f"  Domains:     [green]{', '.join(self.domains)}[/]",
            f"  Model:       [dim]{self.default_model}[/]",
            f"  Mode:        [dim]{self.default_mode}[/]",
            f"  Theme:       [dim]{self.theme}[/]",
            f"  Sessions:    {self.sessions_completed}",
            f"  Age:         {self.age_days} days",
        ]
        return "\n".join(lines)


# ── Profile I/O ─────────────────────────────────────────────────────────

def load_profile() -> LyraProfile:
    """Load profile from disk, returning defaults if missing."""
    if PROFILE_PATH.exists():
        try:
            data = json.loads(PROFILE_PATH.read_text())
            return LyraProfile(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return LyraProfile()


def save_profile(profile: LyraProfile) -> None:
    """Persist profile to disk."""
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    profile.updated_at = time.time()
    PROFILE_PATH.write_text(json.dumps(profile.to_dict(), indent=2))


# ── Tech level auto-detection ──────────────────────────────────────────

_AUTO_LEVEL_HINTS: dict[str, list[str]] = {
    "beginner": ["/help", "/mode", "/status", "how do I", "what is"],
    "intermediate": ["/compact", "/model", "/skills", "/research"],
    "advanced": ["/workflow", "/undo", "/mcp", "/hud", "/config"],
    "expert": ["/spawn", "/evolve", "/ultrareview", "/trace", "/acp"],
}


def auto_detect_level(used_commands: list[str]) -> str:
    """Guess technical level from recently used slash commands."""
    matched = {"beginner": 0, "intermediate": 0, "advanced": 0, "expert": 0}
    for cmd in used_commands:
        for level, hints in _AUTO_LEVEL_HINTS.items():
            if any(hint.lstrip("/") in cmd for hint in hints):
                matched[level] += 1
    # Return the level with the most matches, defaulting to intermediate
    best = max(matched, key=matched.get)
    return best if matched[best] > 0 else "intermediate"


# ── Slash command handler ──────────────────────────────────────────────

def cmd_profile(session: Any, args: str) -> CommandResult:
    """View or edit your Lyra profile.

    Usage:
      /profile              — show current profile
      /profile set <key> <value>  — set a profile field
      /profile reset        — reset to defaults
      /profile export       — print as JSON
    """
    profile = load_profile()
    parts = args.strip().split(maxsplit=2) if args.strip() else []

    if not parts or parts[0] in ("show", "view"):
        # Show
        return CommandResult(
            output=profile.summary(),
            renderable=profile.render(),
        )

    if parts[0] == "set" and len(parts) >= 3:
        key = parts[1]
        value: Any = parts[2]

        # Type coercion
        field_map = {
            "name": "name", "email": "email",
            "level": "technical_level", "technical_level": "technical_level",
            "verbosity": "verbosity", "verbose": "verbosity",
            "model": "default_model", "default_model": "default_model",
            "mode": "default_mode", "default_mode": "default_mode",
            "theme": "theme",
            "comments": "code_comments", "code_comments": "code_comments",
            "explanations": "explanations",
        }

        attr = field_map.get(key)
        if attr and hasattr(profile, attr):
            current = getattr(profile, attr)
            if isinstance(current, bool):
                value = value.lower() in ("true", "yes", "1", "on")
            elif isinstance(current, int):
                value = int(value)
            elif isinstance(current, list):
                value = [v.strip() for v in value.split(",")]
            setattr(profile, attr, value)
            save_profile(profile)
            return CommandResult(output=f"✓ profile.{attr} = {value}")
        else:
            valid = ", ".join(field_map)
            return CommandResult(output=f"Unknown key '{key}'. Options: {valid}")

    if parts[0] == "reset":
        save_profile(LyraProfile())
        return CommandResult(output="✓ Profile reset to defaults")

    if parts[0] == "export":
        return CommandResult(output=json.dumps(profile.to_dict(), indent=2))

    return CommandResult(output=f"Usage: /profile [show|set <key> <value>|reset|export]")


def cmd_whoami(session: Any, _args: str) -> CommandResult:
    """Quick identity peek — alias for /profile.

    Shows: name, technical level, domains, model.
    """
    profile = load_profile()
    return CommandResult(
        output=profile.summary(),
        renderable=f"[bold]{profile.name or 'anon'}[/] · [cyan]{profile.technical_level}[/] · {', '.join(profile.domains)}",
    )


__all__ = [
    "LyraProfile", "load_profile", "save_profile",
    "cmd_profile", "cmd_whoami", "auto_detect_level",
    "PROFILE_PATH",
]

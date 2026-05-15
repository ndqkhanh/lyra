"""Model router commands — Wave G.

``/route`` slash handler: show or configure the 8-slot model routing policy
(doc 323). State persisted to ``~/.lyra/route-policy.json``.

Follows the ``(session, args: str) -> CommandResult`` contract and never raises.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Routing defaults (doc 323)
# ---------------------------------------------------------------------------

# slot → (tier, model-class-hint, escalate-when)
DEFAULTS: dict[str, tuple[str, str, str]] = {
    "intent":       ("fast",   "haiku-class",  "always"),
    "search":       ("fast",   "haiku-class",  "query-rewrite-fails"),
    "planning":     ("strong", "opus-class",   "multi-system change"),
    "execution":    ("mid",    "sonnet-class", "tool-failure"),
    "synthesis":    ("strong", "opus-class",   "multi-source contradiction"),
    "verification": ("mid",    "sonnet-class", "safety boundary"),
    "review":       ("mid",    "sonnet-class", "large blast radius"),
    "final":        ("strong", "opus-class",   "publishable artifact"),
}

VALID_TIERS = frozenset({"fast", "mid", "strong", "advisor"})

_POLICY_PATH = Path.home() / ".lyra" / "route-policy.json"


# ---------------------------------------------------------------------------
# Result proxy
# ---------------------------------------------------------------------------

def _result_class() -> type:
    try:
        from .session import CommandResult  # type: ignore[attr-defined]
        return CommandResult
    except Exception:
        from lyra_cli.commands.registry import CommandResult as _R
        return _R


def _ok(text: str, renderable: Any = None) -> Any:
    cls = _result_class()
    if renderable is not None:
        return cls(output=text, renderable=renderable)
    return cls(output=text)


# ---------------------------------------------------------------------------
# Policy I/O
# ---------------------------------------------------------------------------

def _load_policy() -> dict[str, tuple[str, str, str]]:
    """Load routing policy from disk, merging with defaults for missing slots."""
    if not _POLICY_PATH.exists():
        return dict(DEFAULTS)
    try:
        raw = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULTS)
    policy: dict[str, tuple[str, str, str]] = dict(DEFAULTS)
    for slot, value in raw.items():
        if slot in DEFAULTS and isinstance(value, list) and len(value) == 3:
            policy[slot] = (str(value[0]), str(value[1]), str(value[2]))
    return policy


def _save_policy(policy: dict[str, tuple[str, str, str]]) -> None:
    _POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialisable = {slot: list(v) for slot, v in policy.items()}
    _POLICY_PATH.write_text(json.dumps(serialisable, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# /route
# ---------------------------------------------------------------------------

def cmd_route(session: Any, args: str) -> Any:
    """Show or configure the 8-slot model routing policy."""
    raw = (args or "").strip()
    parts = raw.split() if raw else []
    sub = parts[0] if parts else "status"

    if sub in ("status", ""):
        return _route_status()
    if sub == "set":
        return _route_set(parts[1:])
    if sub == "reset":
        return _route_reset()
    return _ok(
        f"unknown /route subcommand {sub!r}\n"
        "  usage: /route [status|set <slot> <tier>|reset]"
    )


def _route_status() -> Any:
    try:
        from rich.box import ROUNDED, SIMPLE
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        _has_rich = True
    except ImportError:
        _has_rich = False

    policy = _load_policy()

    tier_colors: dict[str, str] = {
        "fast":    "#7CFFB2",
        "mid":     "#00E5FF",
        "strong":  "#FF2D95",
        "advisor": "#FFC857",
    }

    plain_lines = ["routing policy:"]
    plain_lines.append(f"  {'slot':<14}  {'tier':<8}  {'model':<14}  escalate-when")
    plain_lines.append("  " + "-" * 62)
    for slot, (tier, model, escalate) in policy.items():
        plain_lines.append(f"  {slot:<14}  {tier:<8}  {model:<14}  {escalate}")
    plain = "\n".join(plain_lines)

    if not _has_rich:
        return _ok(plain)

    from rich.box import ROUNDED, SIMPLE
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    t = Table(box=SIMPLE, show_header=True, show_edge=False, pad_edge=False)
    t.add_column("slot",          style="bold #00E5FF",  no_wrap=True, width=14)
    t.add_column("tier",          no_wrap=True, width=9)
    t.add_column("model",         style="#7CFFB2",       no_wrap=True, width=16)
    t.add_column("escalate-when", style="#6B7280")

    for slot, (tier, model, escalate) in policy.items():
        color = tier_colors.get(tier, "#6B7280")
        t.add_row(slot, Text(tier, style=f"bold {color}"), model, escalate)

    source = "default" if not _POLICY_PATH.exists() else str(_POLICY_PATH)
    panel = Panel(
        t,
        box=ROUNDED,
        border_style="#7C4DFF",
        title="[bold #00E5FF]model routing policy[/]",
        title_align="left",
        subtitle=f"[dim]{source}[/]",
        subtitle_align="right",
    )
    return _ok(plain, panel)


def _route_set(parts: list[str]) -> Any:
    if len(parts) < 2:
        return _ok("usage: /route set <slot> <tier>  (tiers: fast | mid | strong | advisor)")

    slot, tier = parts[0], parts[1]
    if slot not in DEFAULTS:
        known = ", ".join(DEFAULTS)
        return _ok(f"unknown slot {slot!r}; valid slots: {known}")
    if tier not in VALID_TIERS:
        return _ok(f"unknown tier {tier!r}; valid tiers: {', '.join(sorted(VALID_TIERS))}")

    policy = _load_policy()
    old_tier, model, escalate = policy[slot]
    policy[slot] = (tier, model, escalate)

    try:
        _save_policy(policy)
    except Exception as exc:
        return _ok(f"failed to save routing policy: {exc}")

    return _ok(f"route set: {slot} → {tier} (was {old_tier})")


def _route_reset() -> Any:
    try:
        _save_policy(dict(DEFAULTS))
    except Exception as exc:
        return _ok(f"failed to reset routing policy: {exc}")
    return _ok("routing policy reset to defaults")


__all__ = ["DEFAULTS", "VALID_TIERS", "cmd_route"]

"""Skin / theme engine for the interactive CLI.

What the user calls a "theme" we model as a :class:`Skin`: a curated bundle
of colour tokens, branding strings, and spinner config that the banner,
status bar, completion menu, prompt symbol, and tool-output prefix all
read from. Switching skins is a one-token swap; the renderers re-pull
their palette on the next prompt tick.

Why a richer model than v1's 7-key TypedDict?

- The 7-key Theme captured ``accent / secondary / danger / success /
  warning / error / dim`` — enough for Rich panels but not enough to
  re-skin the **whole** UI (banner background, status bar bar, completion
  menu, prompt symbol, tool prefix).
- Inspired by ``hermes-agent`` (`hermes_cli/skin_engine.py`), Skin v2
  also carries ``branding`` (agent name, welcome / goodbye text, prompt
  glyph) and ``spinner`` config (faces, verbs, optional wings) so a skin
  can change personality, not just colour.
- User-defined skins drop into ``~/.lyra/skins/<name>.yaml``; the
  loader is no-op when PyYAML isn't installed (we never want a soft dep
  to break the CLI).

Backwards compatibility:

- :func:`get` still returns a :class:`Theme`-shaped dict so v1 callers
  (``themes.get('aurora')['accent']``) keep working.
- :func:`names` lists every built-in skin (8 today: aurora, candy, solar,
  mono — the originals — plus claude, opencode, hermes, sunset).
- The new :func:`skin`, :func:`get_active_skin`, :func:`set_active_skin`,
  and :func:`load_user_skins` helpers expose the rich :class:`Skin`
  objects for renderers that want them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Legacy 7-key Theme — kept so existing call-sites and tests keep working
# ---------------------------------------------------------------------------


class Theme(TypedDict):
    """The original 7-token palette returned by :func:`get`.

    Maps onto a :class:`Skin` like::

        accent    → skin.colors["accent"]
        secondary → skin.colors["secondary"]
        danger    → skin.colors["danger"]
        success   → skin.colors["success"]
        warning   → skin.colors["warning"]
        error     → skin.colors["error"]
        dim       → skin.colors["dim"]
    """

    accent: str
    secondary: str
    danger: str
    success: str
    warning: str
    error: str
    dim: str


_LEGACY_KEYS: tuple[str, ...] = (
    "accent",
    "secondary",
    "danger",
    "success",
    "warning",
    "error",
    "dim",
)


# ---------------------------------------------------------------------------
# Skin dataclass — the rich, drop-in replacement
# ---------------------------------------------------------------------------


@dataclass
class Skin:
    """A complete skin: colours + branding + spinner config + tool overrides.

    Mutable on purpose so :func:`load_user_skins` can mix in user overrides
    over a built-in baseline. Renderers should treat the fields as
    read-only once the active skin is selected.
    """

    name: str
    description: str = ""
    # Color tokens. Keys are intentionally open-ended (a YAML user skin
    # can add its own); renderers use ``.get`` with a sensible default.
    # Built-ins below define a stable set of ~17 tokens.
    colors: dict[str, str] = field(default_factory=dict)
    branding: dict[str, str] = field(default_factory=dict)
    # Spinner config: ``faces`` (list[str]), ``verbs`` (list[str]),
    # ``wings`` (list[tuple[str, str]]). Empty = use renderer defaults.
    spinner: dict[str, Any] = field(default_factory=dict)
    tool_prefix: str = "┊"
    # Tool-specific emoji overrides (e.g. ``{"bash": "⚡", "read": "📖"}``).
    tool_emojis: dict[str, str] = field(default_factory=dict)

    def color(self, key: str, fallback: str = "") -> str:
        """Get a colour token with a string fallback."""
        return self.colors.get(key, fallback)

    def brand(self, key: str, fallback: str = "") -> str:
        """Get a branding string with a fallback."""
        return self.branding.get(key, fallback)

    def legacy_palette(self) -> Theme:
        """Project this skin onto the 7-key :class:`Theme` for v1 callers."""
        return {  # type: ignore[return-value]
            "accent": self.colors.get("accent", "#00E5FF"),
            "secondary": self.colors.get("secondary", "#7C4DFF"),
            "danger": self.colors.get("danger", "#FF2D95"),
            "success": self.colors.get("success", "#7CFFB2"),
            "warning": self.colors.get("warning", "#FFC857"),
            "error": self.colors.get("error", "#FF5370"),
            "dim": self.colors.get("dim", "#6B7280"),
        }

    def merge_overrides(self, override: dict[str, Any]) -> None:
        """Layer a YAML override on top of this skin (mutating)."""
        if not isinstance(override, dict):
            return
        if isinstance(override.get("description"), str):
            self.description = override["description"]
        if isinstance(override.get("tool_prefix"), str):
            self.tool_prefix = override["tool_prefix"]
        for nested in ("colors", "branding", "spinner", "tool_emojis"):
            sub = override.get(nested)
            if isinstance(sub, dict):
                getattr(self, nested).update(sub)


# ---------------------------------------------------------------------------
# Built-in skins (8 total)
# ---------------------------------------------------------------------------
#
# Naming: 4 originals (aurora, candy, solar, mono) so existing tests stay
# green, plus 4 new (claude, opencode, hermes, sunset) for fresh visual
# variety inspired by the reference agents.
#
# Every built-in defines the same set of colour keys; user YAML skins can
# extend with anything they like. Defaults below match the old palette so
# the visual output of the unchanged renderers doesn't drift.

_AURORA = Skin(
    name="aurora",
    description="Default — neon cyan / indigo / pink (banner gradient).",
    colors={
        "accent": "#00E5FF",
        "secondary": "#7C4DFF",
        "danger": "#FF2D95",
        "success": "#7CFFB2",
        "warning": "#FFC857",
        "error": "#FF5370",
        "dim": "#6B7280",
        "banner_border": "#00E5FF",
        "banner_title": "#00E5FF",
        "status_bar_bg": "#0D0D14",
        "status_bar_text": "#A1A7B3",
        "status_bar_strong": "#00E5FF",
        "status_bar_dim": "#3E4048",
        "prompt": "#FFFFFF",
        "completion_menu_bg": "#0D0D14",
        "completion_menu_current_bg": "#1F1F2E",
        "input_rule": "#7C4DFF",
        "response_border": "#00E5FF",
    },
    branding={
        "agent_name": "Lyra",
        "welcome": "ready.",
        "goodbye": "see you next session.",
        "prompt_symbol": "›",
    },
    spinner={
        "faces": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "verbs": [
            "thinking",
            "planning",
            "reading",
            "tracing",
            "compiling",
            "checking",
        ],
        "wings": [],
    },
    tool_prefix="┊",
)

_CANDY = Skin(
    name="candy",
    description="Original candy palette — pink, indigo, mint highlights.",
    colors={
        "accent": "#FF6FD8",
        "secondary": "#3813C2",
        "danger": "#FF4081",
        "success": "#69F0AE",
        "warning": "#FFD54F",
        "error": "#FF1744",
        "dim": "#7A5D7E",
        "banner_border": "#FF6FD8",
        "banner_title": "#FF6FD8",
        "status_bar_bg": "#1A0A1F",
        "status_bar_text": "#E8C5F1",
        "status_bar_strong": "#FF6FD8",
        "status_bar_dim": "#7A5D7E",
        "prompt": "#FFE8F5",
        "completion_menu_bg": "#1A0A1F",
        "completion_menu_current_bg": "#3813C2",
        "input_rule": "#FF6FD8",
        "response_border": "#FF6FD8",
    },
    branding={
        "agent_name": "Lyra · candy",
        "welcome": "sweet on syntax.",
        "goodbye": "stay sweet.",
        "prompt_symbol": "♡",
    },
    spinner={
        "faces": ["✶", "✷", "✸", "✹", "✺", "✹", "✸", "✷"],
        "verbs": ["pondering", "musing", "designing", "remixing"],
        "wings": [],
    },
    tool_prefix="┆",
)

_SOLAR = Skin(
    name="solar",
    description="Solarized — warm amber / orange for light terminals.",
    colors={
        "accent": "#FFB800",
        "secondary": "#C2410C",
        "danger": "#EA580C",
        "success": "#FACC15",
        "warning": "#FDE047",
        "error": "#B91C1C",
        "dim": "#7C5E3C",
        "banner_border": "#C2410C",
        "banner_title": "#FFB800",
        "status_bar_bg": "#1F1A0F",
        "status_bar_text": "#E8D5A8",
        "status_bar_strong": "#FFB800",
        "status_bar_dim": "#7C5E3C",
        "prompt": "#FAEDCD",
        "completion_menu_bg": "#1F1A0F",
        "completion_menu_current_bg": "#3F2C0A",
        "input_rule": "#C2410C",
        "response_border": "#FFB800",
    },
    branding={
        "agent_name": "Lyra · solar",
        "welcome": "daylight mode.",
        "goodbye": "good day.",
        "prompt_symbol": "☀",
    },
    spinner={
        "faces": ["◜", "◠", "◝", "◞", "◡", "◟"],
        "verbs": ["analysing", "computing", "warming up"],
        "wings": [],
    },
    tool_prefix="┊",
)

_MONO = Skin(
    name="mono",
    description="High-contrast greyscale — perfect for screencasts.",
    colors={
        "accent": "#E5E7EB",
        "secondary": "#9CA3AF",
        "danger": "#D1D5DB",
        "success": "#F3F4F6",
        "warning": "#9CA3AF",
        "error": "#E5E7EB",
        "dim": "#6B7280",
        "banner_border": "#E5E7EB",
        "banner_title": "#FFFFFF",
        "status_bar_bg": "#000000",
        "status_bar_text": "#D1D5DB",
        "status_bar_strong": "#FFFFFF",
        "status_bar_dim": "#6B7280",
        "prompt": "#FFFFFF",
        "completion_menu_bg": "#0A0A0A",
        "completion_menu_current_bg": "#1F1F1F",
        "input_rule": "#9CA3AF",
        "response_border": "#FFFFFF",
    },
    branding={
        "agent_name": "Lyra · mono",
        "welcome": "monochrome.",
        "goodbye": "bye.",
        "prompt_symbol": ">",
    },
    spinner={
        "faces": ["·", "•", "●", "•"],
        "verbs": ["working", "running", "checking"],
        "wings": [],
    },
    tool_prefix="|",
)

_CLAUDE = Skin(
    name="claude",
    description="Anthropic-style — warm amber on graphite.",
    colors={
        "accent": "#FF8800",
        "secondary": "#D97706",
        "danger": "#EF4444",
        "success": "#22C55E",
        "warning": "#FBBF24",
        "error": "#DC2626",
        "dim": "#78716C",
        "banner_border": "#FF8800",
        "banner_title": "#FBBF24",
        "status_bar_bg": "#1C1917",
        "status_bar_text": "#E7E5E4",
        "status_bar_strong": "#FBBF24",
        "status_bar_dim": "#78716C",
        "prompt": "#FAFAF9",
        "completion_menu_bg": "#1C1917",
        "completion_menu_current_bg": "#3F3F37",
        "input_rule": "#D97706",
        "response_border": "#FBBF24",
    },
    branding={
        "agent_name": "Lyra · claude",
        "welcome": "extended thinking.",
        "goodbye": "thinking complete. take care.",
        "prompt_symbol": "❯",
    },
    spinner={
        "faces": ["✦", "✧", "✶", "✷", "✸", "✹", "✺", "✹"],
        "verbs": [
            "extending thinking",
            "reasoning step-by-step",
            "considering",
            "constructing",
            "self-checking",
        ],
        "wings": [["·", "·"]],
    },
    tool_prefix="▏",
    tool_emojis={
        "bash": "⚡",
        "read": "📖",
        "write": "✎",
        "edit": "✎",
        "search": "🔍",
        "grep": "🔍",
        "glob": "📂",
    },
)

_OPENCODE = Skin(
    name="opencode",
    description="sst/opencode-style — indigo + neon green developer vibes.",
    colors={
        "accent": "#00FF88",
        "secondary": "#6366F1",
        "danger": "#F43F5E",
        "success": "#10B981",
        "warning": "#FBBF24",
        "error": "#EF4444",
        "dim": "#71717A",
        "banner_border": "#6366F1",
        "banner_title": "#00FF88",
        "status_bar_bg": "#0A0E1A",
        "status_bar_text": "#A1A1AA",
        "status_bar_strong": "#00FF88",
        "status_bar_dim": "#3F3F46",
        "prompt": "#F4F4F5",
        "completion_menu_bg": "#0A0E1A",
        "completion_menu_current_bg": "#1E1B4B",
        "input_rule": "#6366F1",
        "response_border": "#00FF88",
    },
    branding={
        "agent_name": "Lyra · opencode",
        "welcome": "terminal-native.",
        "goodbye": "exit 0.",
        "prompt_symbol": "→",
    },
    spinner={
        "faces": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
        "verbs": ["building", "linking", "compiling", "deploying", "querying"],
        "wings": [],
    },
    tool_prefix="│",
    tool_emojis={
        "bash": "$",
        "read": "◇",
        "write": "◈",
        "edit": "◆",
        "search": "▷",
        "grep": "▷",
    },
)

_HERMES = Skin(
    name="hermes",
    description="NousResearch hermes-agent homage — gold and bronze, kawaii faces.",
    colors={
        "accent": "#FFD700",
        "secondary": "#CD7F32",
        "danger": "#DD4A3A",
        "success": "#7BC96F",
        "warning": "#FFBF00",
        "error": "#EF5350",
        "dim": "#B8860B",
        "banner_border": "#CD7F32",
        "banner_title": "#FFD700",
        "status_bar_bg": "#1A1A2E",
        "status_bar_text": "#FFF8DC",
        "status_bar_strong": "#FFD700",
        "status_bar_dim": "#8B8682",
        "prompt": "#FFF8DC",
        "completion_menu_bg": "#1A1A2E",
        "completion_menu_current_bg": "#333355",
        "input_rule": "#CD7F32",
        "response_border": "#FFD700",
    },
    branding={
        "agent_name": "Lyra · hermes",
        "welcome": "winged messenger.",
        "goodbye": "goodbye! ⚕",
        "prompt_symbol": "❯",
    },
    spinner={
        "faces": [
            "(｡◕‿◕｡)",
            "(◕‿◕✿)",
            "٩(◕‿◕｡)۶",
            "(✿◠‿◠)",
            "( ˘▽˘)っ",
        ],
        "verbs": [
            "pondering",
            "contemplating",
            "musing",
            "cogitating",
            "ruminating",
            "deliberating",
        ],
        "wings": [["⟪", "⟫"], ["▶", "◀"]],
    },
    tool_prefix="┊",
)

_SUNSET = Skin(
    name="sunset",
    description="Pink → amber → indigo gradient — vapourwave energy.",
    colors={
        "accent": "#F472B6",
        "secondary": "#A855F7",
        "danger": "#EF4444",
        "success": "#34D399",
        "warning": "#FBBF24",
        "error": "#F87171",
        "dim": "#9CA3AF",
        "banner_border": "#A855F7",
        "banner_title": "#F472B6",
        "status_bar_bg": "#1E1B2E",
        "status_bar_text": "#E0D7F0",
        "status_bar_strong": "#F472B6",
        "status_bar_dim": "#6B5B8A",
        "prompt": "#FAF5FF",
        "completion_menu_bg": "#1E1B2E",
        "completion_menu_current_bg": "#3B2C5C",
        "input_rule": "#A855F7",
        "response_border": "#F472B6",
    },
    branding={
        "agent_name": "Lyra · sunset",
        "welcome": "golden hour.",
        "goodbye": "see you under the next sunset.",
        "prompt_symbol": "❥",
    },
    spinner={
        "faces": ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"],
        "verbs": ["dreaming", "drifting", "imagining", "weaving"],
        "wings": [],
    },
    tool_prefix="┊",
)


_MIDNIGHT = Skin(
    name="midnight",
    description="Deep-night blues for low-light coding sessions.",
    colors={
        "accent": "#5EEAD4",
        "secondary": "#6366F1",
        "danger": "#FB7185",
        "success": "#34D399",
        "warning": "#FBBF24",
        "error": "#F87171",
        "dim": "#475569",
        "banner_border": "#5EEAD4",
        "banner_title": "#A5F3FC",
        "status_bar_bg": "#020617",
        "status_bar_text": "#94A3B8",
        "status_bar_strong": "#5EEAD4",
        "status_bar_dim": "#1E293B",
        "prompt": "#E0F2FE",
        "completion_menu_bg": "#020617",
        "completion_menu_current_bg": "#1E293B",
        "input_rule": "#6366F1",
        "response_border": "#5EEAD4",
    },
    branding={
        "agent_name": "Lyra · midnight",
        "welcome": "after-dark mode.",
        "goodbye": "rest well.",
        "prompt_symbol": "✦",
    },
    spinner={
        "faces": ["·", "•", "●", "◉", "●", "•"],
        "verbs": ["pondering", "tracing", "synthesising", "drafting"],
        "wings": [],
    },
    tool_prefix="┊",
)

_PAPER = Skin(
    name="paper",
    description="High-contrast paper-white — ideal for screencasts and demos.",
    colors={
        "accent": "#1F2937",
        "secondary": "#4B5563",
        "danger": "#B91C1C",
        "success": "#15803D",
        "warning": "#B45309",
        "error": "#991B1B",
        "dim": "#9CA3AF",
        "banner_border": "#1F2937",
        "banner_title": "#111827",
        "status_bar_bg": "#F9FAFB",
        "status_bar_text": "#374151",
        "status_bar_strong": "#111827",
        "status_bar_dim": "#9CA3AF",
        "prompt": "#111827",
        "completion_menu_bg": "#F9FAFB",
        "completion_menu_current_bg": "#E5E7EB",
        "input_rule": "#4B5563",
        "response_border": "#1F2937",
    },
    branding={
        "agent_name": "Lyra · paper",
        "welcome": "paper trail mode.",
        "goodbye": "filed.",
        "prompt_symbol": "›",
    },
    spinner={
        "faces": ["─", "\\", "│", "/"],
        "verbs": ["reading", "writing", "filing", "checking"],
        "wings": [],
    },
    tool_prefix="·",
)


_BUILT_IN_SKINS: dict[str, Skin] = {
    s.name: s
    for s in (
        _AURORA,
        _CANDY,
        _SOLAR,
        _MONO,
        _CLAUDE,
        _OPENCODE,
        _HERMES,
        _SUNSET,
        _MIDNIGHT,
        _PAPER,
    )
}

# Active skin tracked at module level so the prompt_toolkit renderers and
# the spinner thread can pick it up without threading state through every
# call. The driver may flip this when `/theme <name>` (or `/skin <name>`)
# resolves successfully.
_ACTIVE_SKIN_NAME: str = "aurora"


# ---------------------------------------------------------------------------
# User skin loader (optional PyYAML)
# ---------------------------------------------------------------------------


def _user_skins_dir(home: Path) -> Path:
    """Where user-defined skins live: ``<home>/.lyra/skins``."""
    return home / ".lyra" / "skins"


def load_user_skins(home: Path) -> list[Skin]:
    """Read user skins from ``~/.lyra/skins/*.yaml`` if PyYAML is around.

    Returns an empty list when:

    - PyYAML isn't installed (we never want a soft dep to break the CLI),
    - the skins directory doesn't exist, or
    - none of the files are valid mappings.

    Each YAML file becomes one :class:`Skin`. The schema is forgiving:
    keys we don't recognise are dropped silently. Use the ``parent`` key
    to inherit from a built-in (default: aurora).
    """
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return []
    folder = _user_skins_dir(home)
    if not folder.is_dir():
        return []
    out: list[Skin] = []
    for path in sorted(folder.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        name = data.get("name") or path.stem
        if not isinstance(name, str):
            continue
        parent_name = data.get("parent") if isinstance(data.get("parent"), str) else "aurora"
        parent = _BUILT_IN_SKINS.get(parent_name, _AURORA)
        skin_obj = Skin(
            name=name,
            description=str(data.get("description") or parent.description),
            colors=dict(parent.colors),
            branding=dict(parent.branding),
            spinner=dict(parent.spinner),
            tool_prefix=parent.tool_prefix,
            tool_emojis=dict(parent.tool_emojis),
        )
        skin_obj.merge_overrides(data)
        out.append(skin_obj)
    return out


def install_user_skins(home: Path) -> None:
    """Discover and register every user skin under ``home``.

    Idempotent — re-installing the same skin replaces the previous entry,
    so the user can edit a YAML file and rerun without restarting.
    """
    for s in load_user_skins(home):
        _BUILT_IN_SKINS[s.name] = s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get(name: str) -> Theme:
    """Backwards-compatible accessor: return the legacy 7-key Theme dict.

    Falls back to *aurora* on unknown input so the renderers never crash
    on a typo in user config.
    """
    return _BUILT_IN_SKINS.get(name, _AURORA).legacy_palette()


def skin(name: str) -> Skin:
    """Return the rich :class:`Skin` for *name*, falling back to aurora."""
    return _BUILT_IN_SKINS.get(name, _AURORA)


def names() -> tuple[str, ...]:
    """All registered skin names in insertion order (built-ins first, then YAML)."""
    return tuple(_BUILT_IN_SKINS)


def set_active_skin(name: str) -> Skin:
    """Switch the active skin and return the resolved object.

    Unknown names fall back to aurora and the active marker stays
    pointing at the requested name (so a misnamed entry shows up in
    ``/status`` but doesn't crash the renderers).
    """
    global _ACTIVE_SKIN_NAME
    _ACTIVE_SKIN_NAME = name
    return _BUILT_IN_SKINS.get(name, _AURORA)


def get_active_skin() -> Skin:
    """Return the currently-active :class:`Skin`."""
    return _BUILT_IN_SKINS.get(_ACTIVE_SKIN_NAME, _AURORA)


def active_name() -> str:
    """The name of the active skin (may differ from the resolved skin if unknown)."""
    return _ACTIVE_SKIN_NAME


__all__ = [
    "Skin",
    "Theme",
    "active_name",
    "get",
    "get_active_skin",
    "install_user_skins",
    "load_user_skins",
    "names",
    "set_active_skin",
    "skin",
]

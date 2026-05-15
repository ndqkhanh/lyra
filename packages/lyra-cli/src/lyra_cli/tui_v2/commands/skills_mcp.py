"""``/skill list`` and ``/mcp list`` — read-only inspection.

Both commands surface configured surfaces (Lyra's skills directory and
the MCP server config) so a user landing in the TUI can see what tools
the agent has access to. Mutating ops (``/skill enable``, ``/mcp add``)
are left for Phase 5 (modal-driven editors).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from harness_tui.commands.registry import register_command

if TYPE_CHECKING:  # pragma: no cover
    from harness_tui.app import HarnessApp


_SKILLS_GLOBAL = Path.home() / ".claude" / "skills"


@register_command(
    name="skill",
    description="Skill ops — '/skill' picker · '/skill list' inline",
    category="Lyra",
    examples=["/skill", "/skill list", "/skill pick"],
)
async def cmd_skill(app: "HarnessApp", args: str) -> None:
    verb = (args or "").strip().split(maxsplit=1)[0:1]
    verb = verb[0].lower() if verb else "pick"
    if verb in {"pick", ""}:
        await _open_skill_picker(app)
        return
    if verb not in {"list", "ls"}:
        app.shell.chat_log.write_system(
            "skill: usage — '/skill' (picker) · '/skill list' (inline)"
        )
        return

    skills = _list_skills(Path(app.cfg.working_dir or "."))
    if not skills:
        app.shell.chat_log.write_system(
            "skill: (no skills installed — see https://docs.claude.com/skills)"
        )
        return

    lines = [f"installed skills ({len(skills)}):"]
    for source, name, desc in skills[:40]:
        suffix = "  ·  " + desc[:60] if desc else ""
        lines.append(f"  [{source}] {name}{suffix}")
    if len(skills) > 40:
        lines.append(f"  … {len(skills) - 40} more")
    app.shell.chat_log.write_system("\n".join(lines))


@register_command(
    name="mcp",
    description="MCP ops — '/mcp' picker · '/mcp list' inline",
    category="Lyra",
    examples=["/mcp", "/mcp list", "/mcp pick"],
)
async def cmd_mcp(app: "HarnessApp", args: str) -> None:
    verb = (args or "").strip().split(maxsplit=1)[0:1]
    verb = verb[0].lower() if verb else "pick"
    if verb in {"pick", ""}:
        await _open_mcp_picker(app)
        return
    if verb not in {"list", "ls"}:
        app.shell.chat_log.write_system(
            "mcp: usage — '/mcp' (picker) · '/mcp list' (inline)"
        )
        return

    servers = _list_mcp(Path(app.cfg.working_dir or "."))
    if not servers:
        app.shell.chat_log.write_system(
            "mcp: (no MCP servers configured — see 'lyra mcp add --help')"
        )
        return

    lines = [f"MCP servers ({len(servers)}):"]
    for name, transport in servers:
        lines.append(f"  {name:<24}  {transport}")
    app.shell.chat_log.write_system("\n".join(lines))


# ---------------------------------------------------------------------
# Modal openers (Phase 5)
# ---------------------------------------------------------------------


async def _open_skill_picker(app: "HarnessApp") -> None:
    from ..modals import SkillPicker

    chosen = await app.push_screen(
        SkillPicker(working_dir=Path(app.cfg.working_dir or ".")),
        wait_for_dismiss=True,
    )
    if chosen:
        app.shell.chat_log.write_system(f"skill picked: {chosen}")


async def _open_mcp_picker(app: "HarnessApp") -> None:
    from ..modals import McpPicker

    chosen = await app.push_screen(
        McpPicker(working_dir=Path(app.cfg.working_dir or ".")),
        wait_for_dismiss=True,
    )
    if chosen:
        app.shell.chat_log.write_system(f"mcp picked: {chosen}")


# ---------------------------------------------------------------------
# Discovery helpers (pure / no app side-effects so tests can call them)
# ---------------------------------------------------------------------


def _list_skills(repo_root: Path) -> list[tuple[str, str, str]]:
    """Return (source, name, description) for each visible skill."""
    out: list[tuple[str, str, str]] = []
    for label, base in (
        ("project", repo_root / ".claude" / "skills"),
        ("global", _SKILLS_GLOBAL),
    ):
        if not base.exists():
            continue
        for entry in sorted(base.iterdir()):
            if not entry.is_dir():
                continue
            md = entry / "SKILL.md"
            desc = ""
            if md.exists():
                desc = _extract_description(md)
            out.append((label, entry.name, desc))
    return out


def _extract_description(md: Path) -> str:
    """Pull the ``description:`` value from a Claude-Code-style SKILL.md.

    Only scans the YAML frontmatter (between the first two ``---``
    lines); body text is ignored. Returns ``""`` if not found.
    """
    try:
        text = md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        s = line.strip()
        if s == "---":
            return ""
        if s.lower().startswith("description:"):
            return s.split(":", 1)[1].strip().strip("\"'")
    return ""


def _list_mcp(repo_root: Path) -> list[tuple[str, str]]:
    """Return (name, transport_summary) for each configured MCP server."""
    candidates = (
        repo_root / ".lyra" / "mcp.json",
        repo_root / ".claude" / "settings.json",
        Path.home() / ".lyra" / "mcp.json",
    )
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path in candidates:
        if not path.exists():
            continue
        out.extend(_parse_mcp(path, seen))
    return out


def _parse_mcp(path: Path, seen: set[str]) -> list[tuple[str, str]]:
    """Parse a single MCP-style config; tolerant of partial shapes."""
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    servers = data.get("mcpServers") or data.get("mcp_servers") or {}
    if not isinstance(servers, dict):
        return []
    out: list[tuple[str, str]] = []
    for name, spec in servers.items():
        if name in seen:
            continue
        seen.add(name)
        if not isinstance(spec, dict):
            out.append((name, "(unparsed)"))
            continue
        if "command" in spec:
            cmd = str(spec.get("command", ""))
            out.append((name, f"stdio · {cmd}"))
        elif "url" in spec:
            out.append((name, f"http · {spec['url']}"))
        else:
            out.append((name, "?"))
    return out

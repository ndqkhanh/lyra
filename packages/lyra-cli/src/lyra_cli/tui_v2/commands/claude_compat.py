"""Claude Code compatibility commands for Lyra TUI.

Adds the slash commands that Claude Code users expect:
/agents /memory /compact /goal /effort /diff /permissions
/background /branch /export /rename /rewind /init /hooks /context
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from harness_tui.commands.registry import register_command

if TYPE_CHECKING:  # pragma: no cover
    from harness_tui.app import HarnessApp


# ---------------------------------------------------------------------------
# /agents
# ---------------------------------------------------------------------------

@register_command(
    name="agents",
    description="Show running subagents status",
    category="Lyra",
    examples=["/agents"],
)
async def cmd_agents(app: "HarnessApp", _: str) -> None:
    lines = ["agents:"]
    # Try ProcessRegistry from lyra_core if available
    try:
        from lyra_core.transparency import ProcessRegistry  # type: ignore[reportAttributeAccessIssue]
        procs = ProcessRegistry.instance().all()
        if procs:
            for p in procs:
                state = getattr(p, "state", "?")
                name = getattr(p, "name", str(p))
                lines.append(f"  · [{state}] {name}")
        else:
            lines.append("  (no active subagents)")
    except Exception:
        lines.append("  (process registry unavailable)")
    app.shell.chat_log.write_system("\n".join(lines))


# ---------------------------------------------------------------------------
# /memory
# ---------------------------------------------------------------------------

@register_command(
    name="memory",
    description="Show memory files and CLAUDE.md paths loaded",
    category="Lyra",
    examples=["/memory"],
)
async def cmd_memory(app: "HarnessApp", _: str) -> None:
    candidates = [
        Path.home() / ".claude" / "CLAUDE.md",
        Path("./CLAUDE.md"),
        Path("./.claude/CLAUDE.md"),
    ]
    env_path = os.environ.get("CLAUDE_MD_PATH")
    if env_path:
        candidates = [Path(p.strip()) for p in env_path.split(os.pathsep)] + candidates

    lines = ["memory files:"]
    for p in candidates:
        status = "exists" if p.exists() else "missing"
        display = str(p).replace(str(Path.home()), "~")
        lines.append(f"  · {display} ({status})")

    # Auto-memory path (hash of project path)
    try:
        import hashlib
        cwd = app.cfg.working_dir or os.getcwd()
        h = hashlib.md5(str(Path(cwd).resolve()).encode()).hexdigest()[:8]
        auto_mem = f"~/.claude/projects/{h}/memory/MEMORY.md"
    except Exception:
        auto_mem = "~/.claude/projects/<hash>/memory/MEMORY.md"
    lines.append(f"auto-memory: {auto_mem}")
    app.shell.chat_log.write_system("\n".join(lines))


# ---------------------------------------------------------------------------
# /compact
# ---------------------------------------------------------------------------

@register_command(
    name="compact",
    description="Compact the conversation to save context",
    category="Session",
    examples=["/compact"],
)
async def cmd_compact(app: "HarnessApp", _: str) -> None:
    app.shell.chat_log.write_system("compacting conversation…")
    try:
        if app.cfg.transport is not None:
            await app.cfg.transport.submit("/compact", mode=app.mode)
    except Exception:
        pass
    try:
        app.shell.chat_log.clear()
        app.shell.chat_log.write_system("conversation compacted.")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# /goal
# ---------------------------------------------------------------------------

@register_command(
    name="goal",
    description="Set autonomous goal — '/goal <condition>' or '/goal clear'",
    category="Lyra",
    examples=["/goal", "/goal implement tests for all modules", "/goal clear"],
)
async def cmd_goal(app: "HarnessApp", args: str) -> None:
    arg = (args or "").strip()
    if not arg:
        app.shell.chat_log.write_system(
            "usage: /goal <condition> | /goal clear"
        )
        return
    if arg.lower() == "clear":
        app.shell.chat_log.write_system("goal cleared")
        try:
            setattr(app, "_goal", None)
        except Exception:
            pass
        return
    setattr(app, "_goal", arg)
    app.shell.chat_log.write_system(f"goal set: {arg}")
    try:
        if app.cfg.transport is not None:
            await app.cfg.transport.submit(f"/goal {arg}", mode=app.mode)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# /effort
# ---------------------------------------------------------------------------

_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


@register_command(
    name="effort",
    description="Set effort level — low · medium · high · xhigh · max",
    category="Lyra",
    examples=["/effort", "/effort high", "/effort max"],
)
async def cmd_effort(app: "HarnessApp", args: str) -> None:
    arg = (args or "").strip().lower()
    if not arg:
        current = getattr(app, "_effort_level", "auto")
        app.shell.chat_log.write_system(
            f"effort: {current}  ·  available: {', '.join(_EFFORT_LEVELS)}"
        )
        return
    if arg not in _EFFORT_LEVELS:
        current = getattr(app, "_effort_level", "auto")
        app.shell.chat_log.write_system(
            f"effort: unknown level {arg!r} — available: {', '.join(_EFFORT_LEVELS)}\n"
            f"current: {current}"
        )
        return
    setattr(app, "_effort_level", arg)
    app.shell.chat_log.write_system(f"effort: {arg}")
    try:
        app.shell.status_line.set_segment("effort", arg)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# /diff
# ---------------------------------------------------------------------------

@register_command(
    name="diff",
    description="Show git diff of uncommitted changes",
    category="Lyra",
    examples=["/diff"],
)
async def cmd_diff(app: "HarnessApp", _: str) -> None:
    cwd = app.cfg.working_dir or os.getcwd()
    try:
        stat = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10, cwd=cwd,
        )
        diff = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, timeout=30, cwd=cwd,
        )
    except FileNotFoundError:
        app.shell.chat_log.write_system("diff: git not found")
        return
    except subprocess.TimeoutExpired:
        app.shell.chat_log.write_system("diff: git timed out")
        return
    except Exception as exc:
        app.shell.chat_log.write_system(f"diff: error — {exc}")
        return

    stat_out = (stat.stdout or "").strip()
    diff_out = (diff.stdout or "").strip()

    if not stat_out and not diff_out:
        app.shell.chat_log.write_system("no uncommitted changes")
        return

    body = stat_out
    if diff_out:
        body = body + "\n\n" + diff_out if body else diff_out
    # Truncate very long diffs
    if len(body) > 4000:
        body = body[:4000] + "\n…(truncated)"
    app.shell.chat_log.write_system(body)


# ---------------------------------------------------------------------------
# /permissions
# ---------------------------------------------------------------------------

@register_command(
    name="permissions",
    description="Show permission rules from settings.json",
    category="Lyra",
    examples=["/permissions"],
)
async def cmd_permissions(app: "HarnessApp", _: str) -> None:
    settings_paths = [
        Path.home() / ".claude" / "settings.json",
        Path(".claude") / "settings.json",
    ]
    allow: list[str] = []
    ask: list[str] = []
    deny: list[str] = []

    for path in settings_paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        perms = data.get("permissions", {})
        allow.extend(perms.get("allow", []))
        ask.extend(perms.get("ask", []))
        deny.extend(perms.get("deny", []))

    def fmt(lst: list[str]) -> str:
        return ", ".join(lst) if lst else "(none)"

    lines = [
        "permissions:",
        f"  allow: {fmt(allow)}",
        f"  ask:   {fmt(ask)}",
        f"  deny:  {fmt(deny)}",
        "Edit: ~/.claude/settings.json",
    ]
    app.shell.chat_log.write_system("\n".join(lines))


# ---------------------------------------------------------------------------
# /background
# ---------------------------------------------------------------------------

@register_command(
    name="background",
    description="Background the current session or submit a background prompt",
    category="Session",
    examples=["/background", "/background run tests and fix failures"],
)
async def cmd_background(app: "HarnessApp", _: str) -> None:
    app.shell.chat_log.write_system(
        "background: sessions run in the foreground only in this version.\n"
        "(Use 'ly &' in a separate terminal, or 'tmux new-window ly' for parallel sessions)"
    )


# ---------------------------------------------------------------------------
# /branch
# ---------------------------------------------------------------------------

@register_command(
    name="branch",
    description="Fork the conversation — '/branch <name>'",
    category="Session",
    examples=["/branch", "/branch experiment-1"],
)
async def cmd_branch(app: "HarnessApp", _: str) -> None:
    app.shell.chat_log.write_system(
        "branch: conversation branching is not yet implemented.\n"
        "(Tip: /clear starts a fresh session; /resume <id> returns to an earlier one)"
    )


# ---------------------------------------------------------------------------
# /export
# ---------------------------------------------------------------------------

@register_command(
    name="export",
    description="Export chat log to a file — '/export [filename]'",
    category="Session",
    examples=["/export", "/export chat.txt"],
)
async def cmd_export(app: "HarnessApp", args: str) -> None:
    filename = (args or "").strip()
    if not filename:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"lyra-export-{ts}.txt"

    dest = Path.home() / "Desktop" / filename

    lines: list[str] = []
    try:
        chat_log = app.shell.chat_log
        # Try to extract lines from the internal _lines list
        raw_lines = getattr(chat_log, "_lines", None)
        if raw_lines is not None:
            lines = [str(ln) for ln in raw_lines]
        else:
            # Fallback: iterate children and extract renderable text
            for child in chat_log.children:
                rend = getattr(child, "renderable", None)
                if rend is not None:
                    plain = getattr(rend, "plain", None)
                    lines.append(plain if isinstance(plain, str) else str(rend))
    except Exception as exc:
        app.shell.chat_log.write_system(f"export: failed to read chat log — {exc}")
        return

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(lines), encoding="utf-8")
    except Exception as exc:
        app.shell.chat_log.write_system(f"export: write failed — {exc}")
        return

    app.shell.chat_log.write_system(f"exported to: {dest}")


# ---------------------------------------------------------------------------
# /rename
# ---------------------------------------------------------------------------

@register_command(
    name="rename",
    description="Rename the current session — '/rename <name>'",
    category="Session",
    examples=["/rename my-feature-session"],
)
async def cmd_rename(app: "HarnessApp", args: str) -> None:
    name = (args or "").strip()
    if not name:
        app.shell.chat_log.write_system("usage: /rename <name>")
        return

    try:
        app.shell.header.session_title = name
    except Exception:
        pass

    session_id = getattr(app, "_session_id", None)
    if session_id and hasattr(app, "session_store"):
        try:
            app.session_store.update_title(session_id, name)
        except Exception:
            pass

    app.shell.chat_log.write_system(f"session renamed to: {name}")


# ---------------------------------------------------------------------------
# /rewind
# ---------------------------------------------------------------------------

@register_command(
    name="rewind",
    description="Rewind conversation to a previous state",
    category="Session",
    examples=["/rewind"],
)
async def cmd_rewind(app: "HarnessApp", _: str) -> None:
    app.shell.chat_log.write_system(
        "rewind: use /resume to load a previous session, or ask Lyra to undo specific changes.\n"
        "(Full checkpoint rewind is planned — track progress with /lyra session list)"
    )


# ---------------------------------------------------------------------------
# /init
# ---------------------------------------------------------------------------

@register_command(
    name="init",
    description="Initialize CLAUDE.md for this project",
    category="Lyra",
    examples=["/init"],
)
async def cmd_init(app: "HarnessApp", _: str) -> None:
    target = Path("./CLAUDE.md")
    if target.exists():
        app.shell.chat_log.write_system(
            f"CLAUDE.md already exists at {target.resolve()}"
        )
        return

    cwd = app.cfg.working_dir or os.getcwd()
    project_name = Path(cwd).resolve().name
    content = (
        f"# {project_name}\n\n"
        f"Working directory: {cwd}\n\n"
        "## Project Overview\n\n"
        "(Add project description here)\n\n"
        "## Key Commands\n\n"
        "(Add common commands here)\n"
    )
    try:
        target.write_text(content, encoding="utf-8")
    except Exception as exc:
        app.shell.chat_log.write_system(f"init: failed to create CLAUDE.md — {exc}")
        return
    app.shell.chat_log.write_system(f"CLAUDE.md created at {target.resolve()}")


# ---------------------------------------------------------------------------
# /hooks
# ---------------------------------------------------------------------------

@register_command(
    name="hooks",
    description="Show hook configuration from settings.json",
    category="Lyra",
    examples=["/hooks"],
)
async def cmd_hooks(app: "HarnessApp", _: str) -> None:
    settings_paths = [
        Path.home() / ".claude" / "settings.json",
        Path(".claude") / "settings.json",
    ]
    all_hooks: dict[str, list[dict]] = {}

    for path in settings_paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        hooks = data.get("hooks", {})
        if not isinstance(hooks, dict):
            continue
        for hook_type, entries in hooks.items():
            if hook_type not in all_hooks:
                all_hooks[hook_type] = []
            if isinstance(entries, list):
                all_hooks[hook_type].extend(entries)

    if not all_hooks:
        app.shell.chat_log.write_system("no hooks configured")
        return

    lines = ["hooks:"]
    for hook_type, entries in all_hooks.items():
        lines.append(f"  [{hook_type}]")
        for entry in entries:
            if isinstance(entry, dict):
                matcher = entry.get("matcher", "*")
                hooks_list = entry.get("hooks", [])
                for h in hooks_list:
                    cmd = h.get("command", "(no command)")
                    lines.append(f"    · {matcher}: {cmd}")
            else:
                lines.append(f"    · {entry}")
    app.shell.chat_log.write_system("\n".join(lines))


# ---------------------------------------------------------------------------
# /usage
# ---------------------------------------------------------------------------

@register_command(
    name="usage",
    description="Show session cost and token usage (alias: /cost)",
    category="Session",
    examples=["/usage"],
)
async def cmd_usage(app: "HarnessApp", _: str) -> None:
    s = app.session_totals()
    app.shell.chat_log.write_system(
        f"usage:\n"
        f"  tokens in/out: {s['tokens_in']:,}/{s['tokens_out']:,}\n"
        f"  cost: ${s['cost_usd']:.4f}\n"
        f"  duration: {s.get('duration_s', 0):.0f}s"
    )


# ---------------------------------------------------------------------------
# /config
# ---------------------------------------------------------------------------

@register_command(
    name="config",
    description="Open settings (use /model, /theme, /effort to change settings)",
    category="Session",
    examples=["/config"],
)
async def cmd_config(app: "HarnessApp", _: str) -> None:
    lines = [
        "config:",
        f"  model: {app.cfg.model}",
        f"  mode: {app.mode}",
        f"  effort: {getattr(app, '_effort_level', 'auto')}",
        f"  thinking: {getattr(app, '_thinking_enabled', False)}",
        f"  fast: {getattr(app, '_fast_mode', False)}",
        f"  working dir: {app.cfg.working_dir}",
        "",
        "change settings: /model · /theme · /effort · /mode",
    ]
    app.shell.chat_log.write_system("\n".join(lines))


# ---------------------------------------------------------------------------
# /doctor
# ---------------------------------------------------------------------------

@register_command(
    name="doctor",
    description="Run Lyra health check",
    category="Lyra",
    examples=["/doctor"],
)
async def cmd_doctor(app: "HarnessApp", _: str) -> None:
    import subprocess
    import sys
    app.shell.chat_log.write_system("running doctor…")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "lyra_cli", "doctor"],
            capture_output=True, text=True, timeout=30,
            cwd=app.cfg.working_dir or ".",
        )
        out = (result.stdout or "") + (result.stderr or "")
        app.shell.chat_log.write_system(out[:4096] or "(no output)")
    except Exception as exc:
        app.shell.chat_log.write_system(f"doctor error: {exc}")


# ---------------------------------------------------------------------------
# /copy
# ---------------------------------------------------------------------------

@register_command(
    name="copy",
    description="Copy last assistant response to clipboard",
    category="Session",
    examples=["/copy"],
)
async def cmd_copy(app: "HarnessApp", _: str) -> None:
    # Try the app's built-in copy action if available
    copy_fn = getattr(app, "action_copy_last_response", None)
    if copy_fn is not None:
        if inspect.iscoroutinefunction(copy_fn):
            await copy_fn()
        else:
            copy_fn()
        return
    app.shell.chat_log.write_system("copy: use the app's Ctrl+C to copy selected text")

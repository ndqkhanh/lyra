"""``/session`` subcommands — list, info, switch.

The TUI's session store is harness-tui's SQLite-backed
``SessionStore`` (one row per turn, plus aggregated totals); legacy
Lyra also has session JSON under ``<repo>/.lyra/sessions/``. The v2
commands operate on harness-tui's store — that's what the running app
holds. ``/session resume <id>`` is left for Phase 5 (the Modal pass)
since it needs proper picker UX, not a slash arg.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from harness_tui.commands.registry import register_command

if TYPE_CHECKING:  # pragma: no cover
    from harness_tui.app import HarnessApp


_DEFAULT_LIST_LIMIT = 10


@register_command(
    name="session",
    description="Session ops — '/session list' · '/session info'",
    category="Lyra",
    examples=["/session", "/session list", "/session info"],
)
async def cmd_session(app: "HarnessApp", args: str) -> None:
    parts = (args or "").strip().split(maxsplit=1)
    verb = parts[0].lower() if parts else "info"

    if verb in {"info", ""}:
        _info(app)
        return
    if verb in {"list", "ls"}:
        _list(app, parts[1] if len(parts) > 1 else "")
        return

    app.shell.chat_log.write_system(
        "session: usage — '/session info' · '/session list [N]'"
    )


def _info(app: "HarnessApp") -> None:
    sid = getattr(app, "_session_id", None)
    if not sid:
        app.shell.chat_log.write_system("session: (no active session)")
        return
    totals = app.session_totals()
    app.shell.chat_log.write_system(
        f"session id: {sid}\n"
        f"  tokens in/out: {totals['tokens_in']}/{totals['tokens_out']}\n"
        f"  cost: ${totals['cost_usd']:.4f}"
    )


def _list(app: "HarnessApp", limit_arg: str) -> None:
    try:
        limit = int(limit_arg) if limit_arg else _DEFAULT_LIST_LIMIT
    except ValueError:
        limit = _DEFAULT_LIST_LIMIT
    limit = max(1, min(limit, 50))

    sessions = app.session_store.list(project=app.cfg.name, limit=limit)
    if not sessions:
        app.shell.chat_log.write_system("session: (no recorded sessions yet)")
        return

    lines = [f"recent sessions (top {len(sessions)}):"]
    for s in sessions:
        # SessionRecord fields: id, title, updated_at, tokens_in, tokens_out, cost_usd
        title = (s.title or "(untitled)")[:40]
        lines.append(
            f"  {s.id[:12]}  ·  {title:<40}  ·  ${s.cost_usd:.4f}"
        )
    app.shell.chat_log.write_system("\n".join(lines))

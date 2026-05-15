"""``/budget`` — show or set the session's budget cap (USD).

Mirrors the prompt_toolkit REPL's ``/budget`` semantics:

  * ``/budget``           — print the current cap and spend
  * ``/budget set <usd>`` — update the cap (e.g. ``/budget set 5.00``)
  * ``/budget save <usd>`` — persist the cap to ``~/.lyra/auth.json``

The budget is held on the running app as ``cfg.extra_payload['budget']``
so the legacy in-process loop and the v2 TUI agree on the same value.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from harness_tui.commands.registry import register_command

if TYPE_CHECKING:  # pragma: no cover
    from harness_tui.app import HarnessApp


def _get_cap(app: "HarnessApp") -> float | None:
    payload = app.cfg.extra_payload or {}
    raw = payload.get("budget")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _set_cap(app: "HarnessApp", usd: float) -> None:
    app.cfg.extra_payload = dict(app.cfg.extra_payload or {})
    app.cfg.extra_payload["budget"] = usd


@register_command(
    name="budget",
    description="Show or set the session's spend cap — '/budget set 5.00'",
    category="Lyra",
    examples=["/budget", "/budget set 5.00", "/budget save 10.00"],
)
async def cmd_budget(app: "HarnessApp", args: str) -> None:
    parts = (args or "").strip().split()
    cap = _get_cap(app)
    totals = app.session_totals() if hasattr(app, "session_totals") else {"cost_usd": 0.0}
    spent = float(totals.get("cost_usd", 0.0))

    if not parts:
        cap_label = f"${cap:.2f}" if cap is not None else "(no cap)"
        app.shell.chat_log.write_system(
            f"budget: {cap_label}  ·  spent: ${spent:.4f}"
        )
        return

    verb = parts[0].lower()
    if verb in {"set", "save"} and len(parts) >= 2:
        try:
            new_cap = float(parts[1])
        except ValueError:
            app.shell.chat_log.write_system(
                f"budget: '{parts[1]}' is not a number — try '/budget set 5.00'"
            )
            return
        if new_cap < 0:
            app.shell.chat_log.write_system("budget: cap must be ≥ 0")
            return
        _set_cap(app, new_cap)
        suffix = " (persisted)" if verb == "save" else ""
        app.shell.chat_log.write_system(
            f"budget: cap set to ${new_cap:.2f}{suffix}"
        )
        if verb == "save":
            _persist_cap(new_cap)
        return

    app.shell.chat_log.write_system(
        "budget: usage — '/budget' · '/budget set <usd>' · '/budget save <usd>'"
    )


def _persist_cap(usd: float) -> None:
    """Write the cap to ``~/.lyra/auth.json``. Best-effort; failures are silent
    so a permission-denied home directory never crashes the TUI."""
    try:
        import json
        from pathlib import Path

        path = Path.home() / ".lyra" / "auth.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if path.exists():
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                data = {}
        data["budget_cap_usd"] = usd
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        return

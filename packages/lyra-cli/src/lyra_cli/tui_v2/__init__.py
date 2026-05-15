"""Lyra TUI v2 — Textual shell via harness-tui.

Phase 1 of the v3.14 rewrite: wire the existing harness-tui HarnessApp
to Lyra's real agent loop (replacing MockTransport) and add an opt-in
default-entry switch (``LYRA_TUI=v2 lyra``).

Phases 2–7 progressively port the prompt_toolkit REPL's slash commands,
status segments, sidebar tabs, modals, and finally retire the legacy
interactive package. See ``LYRA_V3_14_TUI_REWRITE_PLAN.md`` for scope.
"""
from __future__ import annotations

import os
from pathlib import Path

from .brand import LYRA_LOGO, lyra_theme
from .transport import LyraTransport

__all__ = [
    "LYRA_LOGO",
    "LyraTransport",
    "is_v2_enabled",
    "launch_tui_v2",
    "lyra_theme",
]


def is_v2_enabled() -> bool:
    """Opt-in check for the v2 TUI as default entry.

    Until the migration completes (Phase 6), bare ``lyra`` still launches
    the prompt_toolkit REPL. Setting ``LYRA_TUI=v2`` flips the default
    so users who want to dogfood the Textual shell can do so without a
    subcommand change.
    """
    return os.environ.get("LYRA_TUI", "").strip().lower() == "v2"


def launch_tui_v2(
    *,
    repo_root: Path,
    model: str = "auto",
    mock: bool = False,
    max_steps: int = 20,
) -> int:
    """Launch the harness-tui HarnessApp wired to Lyra's real backend.

    Returns a shell-style exit code (0 on clean exit).
    """
    from harness_tui import ProjectConfig
    from harness_tui.transport import MockTransport

    from .app import LyraHarnessApp
    from .commands import register_lyra_commands
    from .sidebar import build_lyra_sidebar_tabs

    transport = (
        MockTransport()
        if mock
        else LyraTransport(repo_root=repo_root, model=model, max_steps=max_steps)
    )

    cfg = ProjectConfig(
        name="lyra",
        description="General-purpose, CLI-native agent harness",
        theme=lyra_theme(),
        transport=transport,
        model=model,
        working_dir=str(repo_root),
        sidebar_tabs=build_lyra_sidebar_tabs(repo_root),
        extra_commands=[register_lyra_commands],
    )
    app = LyraHarnessApp(cfg)
    app.run()

    summary = getattr(app, "last_exit_summary", None)
    if summary is not None:
        try:
            print(summary.render())
        except Exception:
            pass
    return 0

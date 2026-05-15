"""LyraHarnessApp — thin Textual subclass that layers Lyra status UX.

harness-tui's ``HarnessApp`` ships a feature-complete shell; this
subclass only overrides what's Lyra-specific:

  * Adds a ``repo`` segment (basename of cwd) on mount
  * Adds a ``turn`` segment that increments each ``TurnStarted``
  * Reformats the ``tokens`` segment as a Hermes-style fill bar with
    threshold colours (the parent shows a plain count)

All other harness-tui behaviour — chat log, tool cards, modals,
sidebar, plan editor, voice mode, auto-test — flows through unchanged
via ``super()`` calls.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import harness_tui as _harness_tui_pkg
from harness_tui import events as ev
from harness_tui.app import HarnessApp, ProjectConfig
from textual.binding import Binding

from .brand import welcome_lines
from .status import format_repo_segment, format_token_bar, format_turn_segment


class LyraHarnessApp(HarnessApp):
    # Textual resolves a relative CSS_PATH relative to the leaf class's file,
    # not the class that declared it (HarnessApp).  Pin to an absolute path so
    # the inherited shell.tcss is always found regardless of where LyraHarnessApp
    # lives in the source tree.
    CSS_PATH = Path(_harness_tui_pkg.__file__).parent / "shell.tcss"
    """HarnessApp with Lyra-specific status-line behaviour."""

    BINDINGS = [
        *HarnessApp.BINDINGS,
        Binding("ctrl+k", "open_command_palette", "Commands", show=False),
        Binding("alt+p", "open_model_picker", "Model", show=False),
        Binding("alt+t", "toggle_thinking", "Thinking", show=False),
        Binding("alt+o", "toggle_fast", "Fast", show=False),
        Binding("alt+m", "cycle_mode", "Mode", show=False),
    ]

    def __init__(self, cfg: ProjectConfig) -> None:
        super().__init__(cfg)
        self._turn_index = 0
        self._thinking_enabled = False
        self._fast_mode = False

    def _post_mount(self) -> None:
        """Replace the parent's generic welcome with the Lyra welcome pane.

        The parent's ``_post_mount`` paints the ASCII logo + a single
        "Welcome to X. /help to open commands." line. Lyra needs the
        Claude-Code-style hint trio (``/help · /status · ⌥?``) plus the
        model/mode/repo summary that legacy REPL users expect on first
        paint. We keep the parent's transport-stream startup intact.
        """
        from lyra_cli import __version__

        # ASCII logo (same as parent).
        if self.cfg.theme.ascii_logo:
            self.shell.chat_log.write(self.cfg.theme.ascii_logo)

        repo_label = format_repo_segment(self.cfg.working_dir or "")
        lines = welcome_lines(
            __version__,
            model=self.cfg.model or "auto",
            mode=self.mode,
            repo=repo_label,
        )
        self.shell.chat_log.write_system("\n".join(lines))

        # Resume the parent's post-mount work — transport stream task.
        import asyncio

        if self.cfg.transport:
            self._stream_task = asyncio.create_task(self._consume_events())

    def on_mount(self) -> None:
        super().on_mount()
        # Seed Lyra-only segments. ``repo`` and ``turn`` don't exist in
        # harness-tui's default segment order, so they appear at the
        # tail of the StatusLine; that's the same position Hermes uses.
        self.shell.status_line.set_segment(
            "repo", format_repo_segment(self.cfg.working_dir)
        )
        self.shell.status_line.set_segment(
            "turn", format_turn_segment(self._turn_index)
        )
        self.shell.status_line.set_segment("effort", "auto")
        self._detect_pr()

    def _detect_pr(self) -> None:
        """Detect open PR via gh CLI and show number in status bar."""
        try:
            result = subprocess.run(
                ["gh", "pr", "view", "--json", "number,state,url,reviewDecision"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=self.cfg.working_dir or ".",
            )
            if result.returncode == 0:
                pr = json.loads(result.stdout)
                number = pr.get("number", "")
                if number:
                    self.shell.status_line.set_segment("pr", f"PR #{number}")
        except Exception:
            pass

    def _handle_event(self, event: Any) -> None:
        super()._handle_event(event)
        # Layer Lyra-only formatting AFTER the parent processed the
        # event — last write wins on the shared StatusLine segment dict.
        if isinstance(event, ev.TurnStarted):
            self._turn_index += 1
            self.shell.status_line.set_segment(
                "turn", format_turn_segment(self._turn_index)
            )
        elif isinstance(event, ev.TurnFinished):
            total = max(0, event.tokens_in) + max(0, event.tokens_out)
            self.shell.status_line.set_segment(
                "tokens", format_token_bar(total)
            )
        elif isinstance(event, ev.ContextBudget):
            # harness-tui already updates the context bar; Lyra also
            # mirrors the live budget into the tokens segment so users
            # see consumption mid-turn, not only at TurnFinished.
            self.shell.status_line.set_segment(
                "tokens", format_token_bar(event.used, event.max)
            )

    async def action_open_command_palette(self) -> None:
        """Open command palette (Ctrl-K) and insert selected command."""
        from .modals.command_palette import CommandPaletteModal

        result = await self.push_screen(CommandPaletteModal())
        if result:
            # Insert the command into the composer
            try:
                composer = self.shell.composer
                composer.text = f"/{result} "
                composer.focus()
            except Exception:
                pass

    def action_open_model_picker(self) -> None:
        asyncio.create_task(self._dispatch_slash("/model"))

    def action_toggle_thinking(self) -> None:
        self._thinking_enabled = not self._thinking_enabled
        state = "on" if self._thinking_enabled else "off"
        self.shell.status_line.set_segment("thinking", f"think:{state}")
        self.notify(f"extended thinking: {state}", severity="information")

    def action_toggle_fast(self) -> None:
        self._fast_mode = not self._fast_mode
        state = "on" if self._fast_mode else "off"
        self.shell.status_line.set_segment(
            "fast", f"fast:{state}" if self._fast_mode else ""
        )
        self.notify(f"fast mode: {state}", severity="information")

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
import time
from pathlib import Path
from typing import Any

import harness_tui as _harness_tui_pkg
from harness_tui import events as ev
from harness_tui.app import HarnessApp, ProjectConfig
from textual.binding import Binding

from .status import format_repo_segment, format_token_bar, format_turn_segment
from .widgets.welcome_card import WelcomeCard
from .widgets.compaction_banner import CompactionBanner
from .widgets.todo_panel import TodoPanel


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
        Binding("ctrl+t", "open_task_panel", "Tasks", show=False),
        Binding("ctrl+b", "open_background_switcher", "Background", show=False),
        Binding("ctrl+o", "toggle_expand", "Expand", show=False),
    ]

    def __init__(self, cfg: ProjectConfig) -> None:
        super().__init__(cfg)
        self._turn_index = 0
        self._thinking_enabled = False
        self._fast_mode = False
        self._active_agents = {}  # Track active agents for progress display
        self._bg_tasks = {}  # Track background tasks
        self._active_tools = {}  # Track active tool executions

        # NEW: Expandable block manager for ctrl+o
        from .expandable import ExpandableBlockManager
        self._expandable_manager = ExpandableBlockManager()

        # Initialize widgets
        self.welcome_card = WelcomeCard()
        self.compaction_banner = CompactionBanner()
        self.todo_panel = TodoPanel()

    def _post_mount(self) -> None:
        """Replace the parent's generic welcome with the Lyra welcome pane.

        The parent's ``_post_mount`` paints the ASCII logo + a single
        "Welcome to X. /help to open commands." line. Lyra needs the
        Claude-Code-style hint trio (``/help · /status · ⌥?``) plus the
        model/mode/repo summary that legacy REPL users expect on first
        paint. We keep the parent's transport-stream startup intact.
        """
        # ASCII logo (same as parent).
        if self.cfg.theme.ascii_logo:
            self.shell.chat_log.write(self.cfg.theme.ascii_logo)

        # Mount and configure WelcomeCard
        self.welcome_card.model = self.cfg.model or "claude-sonnet-4-6"
        self.welcome_card.cwd = str(self.cfg.working_dir or "")
        self.welcome_card.account = getattr(self.cfg, 'account', '') or 'User'
        self.mount(self.welcome_card)

        # Resume the parent's post-mount work — transport stream task.
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

        # Mount TodoPanel to sidebar
        self.mount(self.todo_panel)
        self._update_todo_panel()

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

        # Import Lyra-specific events
        from .events import ContextCompacted
        from .spinner_states import format_spinner_status
        import time

        if isinstance(event, ev.TurnStarted):
            self._turn_index += 1
            self.shell.status_line.set_segment(
                "turn", format_turn_segment(self._turn_index)
            )
            # Track agent for progress display with spinner
            self._active_agents[event.turn_id] = {
                'started_at': time.time(),
                'tokens_in': 0,
                'tokens_out': 0,
                'thinking_s': 0,
            }
            self._update_agents_display()

            # Show spinner status
            spinner_msg = format_spinner_status(
                elapsed_s=0,
                tokens_in=0,
                tokens_out=0,
            )
            self.shell.chat_log.write_system(spinner_msg)

        elif isinstance(event, ev.TurnFinished):
            total = max(0, event.tokens_in) + max(0, event.tokens_out)
            self.shell.status_line.set_segment(
                "tokens", format_token_bar(total)
            )

            # Update agent tracking with final tokens
            elapsed = 0.0
            if event.turn_id in self._active_agents:
                agent = self._active_agents[event.turn_id]
                elapsed = time.time() - agent['started_at']

                # Show final spinner status with complete info
                from .spinner_states import format_spinner_status
                final_spinner = format_spinner_status(
                    elapsed_s=elapsed,
                    tokens_in=event.tokens_in,
                    tokens_out=event.tokens_out,
                    thinking_s=agent.get('thinking_s', 0),
                )
                self.shell.chat_log.write_system(final_spinner)

                # Remove from active agents
                del self._active_agents[event.turn_id]

            self._update_agents_display()

            # Show tip after long operations
            if elapsed > 30:
                self._show_tip("idle")

        elif isinstance(event, ev.ContextBudget):
            # harness-tui already updates the context bar; Lyra also
            # mirrors the live budget into the tokens segment so users
            # see consumption mid-turn, not only at TurnFinished.
            self.shell.status_line.set_segment(
                "tokens", format_token_bar(event.used, event.max)
            )

        elif isinstance(event, ContextCompacted):
            # Handle context compaction notification
            self._show_compaction_notification(event)

        elif isinstance(event, ev.ToolStarted):
            # Track tool execution and create expandable block
            from .expandable import create_tool_block

            self._active_tools[event.call_id] = {
                'name': event.name,
                'started_at': time.time(),
                'status': 'running',
            }

            # Create expandable block for tool output
            summary = f"{event.name}: {getattr(event, 'description', 'running')}…"
            block = create_tool_block(
                tool_name=event.name,
                summary=summary,
                full_output="",  # Will be filled when tool finishes
            )
            self._expandable_manager.add_block(block)

            # Show collapsed summary
            self.shell.chat_log.write_system(block.render())

        elif isinstance(event, ev.ToolFinished):
            # Update tool status
            if event.call_id in self._active_tools:
                tool = self._active_tools[event.call_id]
                tool['status'] = event.status
                tool['duration_ms'] = getattr(event, 'duration_ms', None)
                self._show_tool_card(event.call_id)
                del self._active_tools[event.call_id]

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

    async def action_open_task_panel(self) -> None:
        """Open task panel modal (Ctrl+T)."""
        from .modals.task_panel import TaskPanelModal

        # Get current tasks from status source
        try:
            from ..interactive.status_source import StatusSource
            status = StatusSource()
            task_items = status.snapshot_tasks()

            # Convert TaskItem objects to dicts for TaskPanelModal
            tasks = [
                {
                    'id': str(getattr(t, 'id', '')),
                    'description': getattr(t, 'description', ''),
                    'completed': getattr(t, 'completed', False),
                }
                for t in task_items
            ]
        except Exception:
            tasks = []

        # Show modal
        modal = TaskPanelModal(tasks)
        await self.mount(modal)

    async def action_open_background_switcher(self) -> None:
        """Open background task switcher modal (Ctrl+B)."""
        from .modals.background_switcher import BackgroundSwitcherModal

        # Show modal with current background tasks
        result = await self.push_screen(BackgroundSwitcherModal(self._bg_tasks))
        if result:
            # Switch to selected background task
            self.notify(f"Switched to task: {result}", severity="information")

    async def action_toggle_expand(self) -> None:
        """Toggle expand/collapse for the most recent expandable block (Ctrl+O)."""
        block = self._expandable_manager.toggle_current()
        if block:
            # Re-render the chat log with updated block state
            # The block's render() method will show expanded or collapsed content
            self.shell.chat_log.write_system(block.render())

    def _update_todo_panel(self) -> None:
        """Update TodoPanel with current task data."""
        try:
            from ..interactive.status_source import StatusSource
            status = StatusSource()
            tasks = status.snapshot_tasks()

            # Convert tasks to dict format for TodoPanel
            todo_items = []
            for task in tasks[:5]:  # Show top 5 tasks
                todo_items.append({
                    'id': str(getattr(task, 'id', '')),
                    'label': getattr(task, 'description', 'Task'),
                    'status': 'done' if getattr(task, 'completed', False) else 'pending',
                })

            self.todo_panel.todos = todo_items
        except Exception:
            # Fallback to empty list if status source unavailable
            self.todo_panel.todos = []

    def _show_compaction_notification(self, event) -> None:
        """Display context compaction notification with details."""
        # Update CompactionBanner with event data
        self.compaction_banner.compaction_event = {
            'utilisation_before': event.utilisation_before,
            'utilisation_after': event.utilisation_after,
            'tokens_before': event.tokens_before,
            'tokens_after': event.tokens_after,
            'restored': getattr(event, 'restored', []),
        }

        # Mount banner if not already mounted
        if not self.compaction_banner.is_mounted:
            self.mount(self.compaction_banner)

        # Update status bar
        self.shell.status_line.set_segment("compaction", "[green]✓ compacted[/]")

        # Show contextual tip
        self._show_tip("idle")

    def _show_tip(self, context: str = "idle") -> None:
        """Show a contextual tip in the chat log."""
        from .tips import get_tip

        tip = get_tip(context)
        self.shell.chat_log.write_system(tip)

    def _update_agents_display(self) -> None:
        """Update status bar with current agent count."""
        from .status import format_agents_segment

        running = len(self._active_agents)
        if running <= 0:
            self.shell.status_line.set_segment("agents", "")
            return

        total = running
        tokens = sum(a.get('tokens', 0) for a in self._active_agents.values())

        self.shell.status_line.set_segment(
            "agents",
            format_agents_segment(running, total, tokens)
        )

    def _update_bg_tasks_display(self) -> None:
        """Update status bar with background task count."""
        from .status import format_bg_tasks_segment

        count = len(self._bg_tasks)
        if count > 0:
            self.shell.status_line.set_segment(
                "bg_tasks",
                format_bg_tasks_segment(count)
            )
        else:
            self.shell.status_line.set_segment("bg_tasks", "")

    def _show_tool_card(self, call_id: str) -> None:
        """Display tool execution card."""
        from .status import format_tool_card

        tool = self._active_tools.get(call_id)
        if not tool:
            return

        card = format_tool_card(
            tool['name'],
            tool['status'],
            tool.get('duration_ms'),
        )
        self.shell.chat_log.write_system(card)

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

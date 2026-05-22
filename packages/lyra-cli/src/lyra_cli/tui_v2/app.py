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
from textual.reactive import reactive

from .status import format_repo_segment, format_token_bar, format_turn_segment
from .widgets.welcome_card import WelcomeCard
from .widgets.compaction_banner import CompactionBanner
from .widgets.todo_panel import TodoPanel
from .widgets import (
    ProgressSpinner,
    AgentExecutionPanel,
    MetricsTracker,
    BackgroundTaskPanel,
    ThinkingIndicator,
    PhaseProgress,
)
# Round 2 — lyra-ui bridge widgets
from .widgets import (
    ContextVizWidget,
    AgentDashboardWidget,
    AccessibilityBridge,
    StreamHandlerWidget,
    ResearchFlowWidget,
)
# Round 3 — remaining lyra-ui ports
from .widgets import (
    PerformanceDashboardWidget,
    ResourceMonitorWidget,
    MessageBubbleWidget,
)
from .widgets import MonitorWidget


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
        # New UX bindings
        Binding("ctrl+r", "open_session_manager", "Sessions", show=True),
        Binding("ctrl+n", "open_notifications", "Notifications", show=True),
        Binding("ctrl+w", "toggle_welcome", "Welcome", show=False),
        # Round 2 bindings
        Binding("ctrl+v", "toggle_context_viz", "Context Viz", show=True),
        Binding("ctrl+d", "toggle_dashboard", "Dashboard", show=True),
        Binding("ctrl+f6", "toggle_research", "Research", show=True),
        Binding("ctrl+shift+h", "toggle_high_contrast", "High Contrast", show=True),
        # Round 3 bindings
        Binding("ctrl+shift+d", "toggle_perf", "Performance", show=True),
        Binding("ctrl+shift+r", "toggle_resource_mon", "Resources", show=True),
        Binding("ctrl+shift+s", "open_status_dashboard", "Status", show=True),
        # Round 8 binding
        Binding("ctrl+m", "toggle_monitor", "Monitor", show=True),
    ]

    # Reactive state properties (Constitution I: Single Source of Truth)
    turn_index: reactive[int] = reactive(0)
    thinking_enabled: reactive[bool] = reactive(False)
    fast_mode: reactive[bool] = reactive(False)

    def __init__(self, cfg: ProjectConfig) -> None:
        super().__init__(cfg)
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

        # Initialize UX improvement widgets
        self.progress_spinner = ProgressSpinner()
        self.agent_panel = AgentExecutionPanel()
        self.metrics_tracker = MetricsTracker()
        self.bg_panel = BackgroundTaskPanel()
        self.thinking_indicator = ThinkingIndicator()
        self.phase_progress = PhaseProgress()
        self._agent_panel_expanded = False

        # Round 2 — new UX widgets
        self.context_viz = ContextVizWidget()
        self.agent_dashboard = AgentDashboardWidget()
        self.accessibility_bridge = AccessibilityBridge()
        self.stream_handler = StreamHandlerWidget()
        self.research_flow = ResearchFlowWidget()

        # Round 3 — remaining lyra-ui ports
        self.perf_dashboard = PerformanceDashboardWidget()
        self.resource_mon = ResourceMonitorWidget()
        self.message_bubble = MessageBubbleWidget()

        # Round 8 — new widgets
        self.monitor = MonitorWidget()

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
            "turn", format_turn_segment(self.turn_index)
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
        import time

        if isinstance(event, ev.TurnStarted):
            self.turn_index += 1
            self.shell.status_line.set_segment(
                "turn", format_turn_segment(self.turn_index)
            )

            # Start progress spinner
            self.progress_spinner.start()

            # Track agent for progress display with spinner
            self._active_agents[event.turn_id] = {
                'started_at': time.time(),
                'tokens_in': 0,
                'tokens_out': 0,
                'thinking_s': 0,
            }

            # Add to agent panel
            self.agent_panel.add_agent(
                agent_id=event.turn_id,
                description=f"Turn {self.turn_index}"
            )

            # Start metrics tracking
            self.metrics_tracker.start_operation(
                op_id=event.turn_id,
                op_type="turn"
            )

            self._update_agents_display()

            # Show spinner status
            spinner_msg = self.progress_spinner.next_frame(tokens=0)
            self.shell.chat_log.write_system(spinner_msg)

            # Wire context_viz with initial component data
            if hasattr(self, 'context_viz'):
                self.context_viz.set_component("conversation", total, 200_000)
                self.context_viz.set_component("system", 1000, 200_000)

        elif isinstance(event, ev.TurnFinished):
            total = max(0, event.tokens_in) + max(0, event.tokens_out)
            self.shell.status_line.set_segment(
                "tokens", format_token_bar(total)
            )

            # Update context_viz
            if hasattr(self, 'context_viz'):
                self.context_viz.set_component("conversation", total, 200_000)

            # Stop progress spinner
            self.progress_spinner.stop()

            # Update agent tracking with final tokens
            elapsed = 0.0
            if event.turn_id in self._active_agents:
                agent = self._active_agents[event.turn_id]
                elapsed = time.time() - agent['started_at']

                # Update agent panel
                self.agent_panel.update_agent(
                    agent_id=event.turn_id,
                    tokens=total,
                    status="done"
                )

                # End metrics tracking
                self.metrics_tracker.end_operation(
                    op_id=event.turn_id,
                    tokens_in=event.tokens_in,
                    tokens_out=event.tokens_out,
                    model=getattr(event, 'model', '')
                )

                # Show final metrics
                metrics_summary = self.metrics_tracker.format_summary(event.turn_id)
                if metrics_summary:
                    self.shell.chat_log.write_system(f"✓ {metrics_summary}")

                # Remove from active agents after delay
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

            # Update progress spinner with current token count
            if self._active_agents:
                spinner_msg = self.progress_spinner.next_frame(tokens=event.used)
                # Update the last system message instead of appending
                # (This prevents spam - in production you'd update in place)
                self.shell.chat_log.write_system(spinner_msg)

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

    # ── New UX action handlers ──────────────────────────────────────

    async def action_open_session_manager(self) -> None:
        """Open session manager modal (Ctrl+R)."""
        from .modals.session_manager import SessionManagerModal, SessionEntry

        # Try to load real sessions from session history
        try:
            result = await self.push_screen(SessionManagerModal())
        except Exception:
            return

        if result:
            self.notify(f"Resumed: {result.title}", severity="information")
            self.shell.chat_log.write_system(
                f"[bold cyan]⌂[/] Resumed session: {result.title}"
            )

    async def action_open_notifications(self) -> None:
        """Open notification drawer (Ctrl+N)."""
        from .modals.notification_drawer import NotificationDrawer, NotificationEntry

        notifications: list[NotificationEntry] = []
        if hasattr(self, 'compaction_banner') and self.compaction_banner.compaction_event:
            ev = self.compaction_banner.compaction_event
            notifications.append(NotificationEntry(
                level="info",
                title=f"Context compacted: {ev.get('tokens_before', 0):,} → {ev.get('tokens_after', 0):,} tokens",
            ))

        await self.push_screen(NotificationDrawer(notifications))

    async def action_toggle_welcome(self) -> None:
        """Toggle welcome card (Ctrl+W)."""
        if hasattr(self, 'welcome_card'):
            self.welcome_card.action_toggle_expand()

    # ── Round 2 toggle action handlers ──────────────────────────────

    async def action_toggle_context_viz(self) -> None:
        """Toggle context visualization panel (Ctrl+V)."""
        if hasattr(self, 'context_viz'):
            self.context_viz.action_toggle_visibility()

    async def action_toggle_dashboard(self) -> None:
        """Toggle agent dashboard panel (Ctrl+D)."""
        if hasattr(self, 'agent_dashboard'):
            self.agent_dashboard.action_toggle_dashboard()

    async def action_toggle_research(self) -> None:
        """Toggle research flow panel (Ctrl+F6)."""
        if hasattr(self, 'research_flow'):
            self.research_flow.action_toggle_research()

    async def action_toggle_high_contrast(self) -> None:
        """Toggle high-contrast accessibility mode (Ctrl+Shift+H)."""
        if hasattr(self, 'accessibility_bridge'):
            self.accessibility_bridge.action_toggle_high_contrast()
            state = "on" if self.accessibility_bridge.high_contrast else "off"
            self.shell.status_line.set_segment("a11y", f"hc:{state}")
            self.notify(f"High contrast: {state}", severity="information")

    # ── Round 3 toggle action handlers ──────────────────────────────

    async def action_toggle_perf(self) -> None:
        """Toggle performance dashboard (Ctrl+Shift+D)."""
        if hasattr(self, 'perf_dashboard'):
            self.perf_dashboard.action_toggle_perf()

    async def action_toggle_resource_mon(self) -> None:
        """Toggle resource monitor (Ctrl+Shift+R)."""
        if hasattr(self, 'resource_mon'):
            self.resource_mon.action_toggle_resource_mon()

    async def action_toggle_monitor(self) -> None:
        """Toggle monitor / fleet panel (Ctrl+M)."""
        if hasattr(self, 'monitor'):
            self.monitor.action_toggle_monitor()

    async def action_open_status_dashboard(self) -> None:
        """Open consolidated status dashboard modal (Ctrl+Shift+S)."""
        from .modals.status_dashboard import StatusDashboardModal

        # Gather snapshot from current state
        snapshot = {
            "model_name": getattr(self.cfg, 'model', '') or '',
            "mode_name": getattr(self.cfg, 'mode', '') or 'default',
            "provider_name": getattr(self.cfg, 'provider', '') or '',
            "token_used": self._active_agents and sum(
                a.get('tokens', 0) for a in self._active_agents.values()
            ) or 0,
            "token_max": 200_000,
            "turn_count": self.turn_index,
            "session_duration": 0.0,
            "agent_count": len(self._active_agents) + len(self._bg_tasks),
            "agent_running": len(self._active_agents),
            "bg_task_count": len(self._bg_tasks),
            "memory_mb": getattr(self.resource_mon, 'current_memory_mb', 0.0) if hasattr(self, 'resource_mon') else 0.0,
            "compaction_count": len(getattr(self.context_viz, '_compaction_records', [])),
            "a11y_mode": "high-contrast" if hasattr(self, 'accessibility_bridge') and self.accessibility_bridge.high_contrast else "normal",
        }

        await self.push_screen(StatusDashboardModal(snapshot))

    # ── Legacy action handlers ───────────────────────────────────────

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

        # Toggle background panel visibility
        self.bg_panel.toggle_visibility()

        # Render background panel
        panel_output = self.bg_panel.render()
        if panel_output:
            self.shell.chat_log.write_system(panel_output)
        else:
            # If panel is now hidden or empty, show modal fallback
            result = await self.push_screen(BackgroundSwitcherModal(self._bg_tasks))
            if result:
                # Switch to selected background task
                self.notify(f"Switched to task: {result}", severity="information")

    async def action_toggle_expand(self) -> None:
        """Toggle expand/collapse for the most recent expandable block (Ctrl+O)."""
        # Toggle agent panel expansion
        self._agent_panel_expanded = not self._agent_panel_expanded

        # Render agent panel
        if self.agent_panel.agents:
            panel_output = self.agent_panel.render(expanded=self._agent_panel_expanded)
            if panel_output:
                self.shell.chat_log.write_system(panel_output)

        # Also toggle expandable blocks (original behavior)
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

        # Log compaction in context_viz
        if hasattr(self, 'context_viz'):
            self.context_viz.add_compaction(
                before=event.tokens_before,
                after=event.tokens_after,
                reason=getattr(event, 'reason', 'auto'),
            )
            self.context_viz.set_component("tools", event.tokens_after, 200_000)

        # Log event in agent dashboard
        if hasattr(self, 'agent_dashboard'):
            saved = event.tokens_before - event.tokens_after
            self.agent_dashboard.log_event(
                "info",
                f"Context compacted: {event.tokens_before:,} → {event.tokens_after:,} ({saved:,} saved)"
            )

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
        self.thinking_enabled = not self.thinking_enabled
        state = "on" if self.thinking_enabled else "off"
        self.shell.status_line.set_segment("thinking", f"think:{state}")
        self.notify(f"extended thinking: {state}", severity="information")

        # Start/stop thinking indicator
        if self.thinking_enabled:
            self.thinking_indicator.start_thinking()
        else:
            elapsed = self.thinking_indicator.end_thinking()
            if elapsed > 0:
                self.shell.chat_log.write_system(
                    f"Extended thinking: {elapsed:.1f}s"
                )

    def action_toggle_fast(self) -> None:
        self.fast_mode = not self.fast_mode
        state = "on" if self.fast_mode else "off"
        self.shell.status_line.set_segment(
            "fast", f"fast:{state}" if self.fast_mode else ""
        )
        self.notify(f"fast mode: {state}", severity="information")

"""Lyra TUI - Full Hermes-style prompt_toolkit Application.

Complete TUI implementation with:
- Status bar with model, tokens, cost
- Input area with dynamic height
- Slash command completion
- File path completion
- Auto-suggestions
- Key bindings (Enter, Ctrl+C, Ctrl+D, Alt+Enter, Tab)
- Background agent execution
- Queue-based communication
"""

from __future__ import annotations

import asyncio
import queue
import threading
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    Dimension,
    FormattedTextControl,
    HSplit,
    Layout,
    Window,
)
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import DynamicStyle, Style as PTStyle
from prompt_toolkit.widgets import TextArea

try:
    from prompt_toolkit.cursor_shapes import CursorShape

    STEADY_CURSOR = CursorShape.BLOCK
except (ImportError, AttributeError):
    STEADY_CURSOR = None

from .banner import render_welcome
from .input import SlashCommandAutoSuggest, SlashCommandCompleter
from .spinner import BrailleSpinner


class LyraTUI:
    """Hermes-style TUI for Lyra."""

    def __init__(
        self,
        repo_root: Path,
        model: str,
        budget_cap_usd: float | None = None,
        session_id: str | None = None,
    ):
        self.repo_root = repo_root
        self.model = model
        self.budget_cap_usd = budget_cap_usd
        self.session_id = session_id or "new-session"

        # State
        self._should_exit = False
        self._agent_running = False
        self._command_running = False

        # Queues for communication
        self._pending_input: queue.Queue = queue.Queue()
        self._interrupt_queue: queue.Queue = queue.Queue()

        # History
        history_dir = Path.home() / ".lyra"
        history_dir.mkdir(exist_ok=True)
        self._history_file = history_dir / "history.txt"

        # Stats
        self._total_tokens = 0
        self._total_cost = 0.0
        self._context_tokens = 0
        self._context_length = 200000  # Default context window
        self._turn_count = 0
        self._cache_saved_tokens = 0  # Phase H
        self._verbosity_pending = "full"  # Phase B — applied on agent init

        # Wave 1: spinner — shared instance, start/stop per turn
        self._spinner = BrailleSpinner(invalidate_fn=self._invalidate_status)

        # Wave 2: last tool output (ctrl+o expand)
        self._last_tool_output: str = ""
        self._tool_output_expanded: bool = False

        # Wave 6: interaction mode
        self._mode: str = "chat"  # "chat" | "plan"

        # Wave 7: agent tree for /research and /team
        self._agent_tree: dict[str, dict] = {}

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup prompt_toolkit Application."""
        # Key bindings
        kb = self._create_key_bindings()

        # Input area
        self.input_area = TextArea(
            height=Dimension(min=1, max=8, preferred=1),
            prompt=self._get_prompt,
            style="class:input-area",
            multiline=True,
            wrap_lines=True,
            read_only=Condition(lambda: self._command_running),
            history=FileHistory(str(self._history_file)),
            completer=SlashCommandCompleter(),
            complete_while_typing=True,
            auto_suggest=SlashCommandAutoSuggest(),
        )

        # Dynamic height
        self.input_area.window.height = self._input_height

        # Status bar
        status_bar = Window(
            height=1,
            content=FormattedTextControl(self._get_status_bar_fragments),
            style="class:status-bar",
        )

        # Input rules (decorative lines)
        input_rule_top = Window(height=1, char="─", style="class:input-rule")
        input_rule_bot = Window(height=1, char="─", style="class:input-rule")

        # Completions menu
        completions_menu = CompletionsMenu(max_height=12, scroll_offset=1)

        # Wave 8: keyboard hints footer
        hint_bar = Window(
            height=1,
            content=FormattedTextControl(self._get_hint_bar_fragments),
            style="class:hint-bar",
        )

        # Layout
        layout = Layout(
            HSplit(
                [
                    status_bar,
                    input_rule_top,
                    self.input_area,
                    input_rule_bot,
                    completions_menu,
                    hint_bar,
                ]
            )
        )

        # Wave 6: DynamicStyle so input-rule color changes per mode
        _MODE_RULE_COLORS = {"chat": "#CD7F32", "plan": "#FFD700", "auto": "#FF4444"}

        def _build_style() -> PTStyle:
            rule_color = _MODE_RULE_COLORS.get(self._mode, "#CD7F32")
            return PTStyle.from_dict(
                {
                    "input-area": "#FFF8DC",
                    "placeholder": "#555555 italic",
                    "status-bar": "bg:#1a1a2e #C0C0C0",
                    "status-bar-strong": "bg:#1a1a2e #FFD700 bold",
                    "status-bar-dim": "bg:#1a1a2e #8B8682",
                    "status-bar-good": "bg:#1a1a2e #8FBC8F bold",
                    "status-bar-warn": "bg:#1a1a2e #FFD700 bold",
                    "status-bar-mode-chat": "bg:#1a1a2e #C0C0C0",
                    "status-bar-mode-plan": "bg:#1a1a2e #FFD700 bold",
                    "input-rule": rule_color,
                    "hint-bar": "#444444",
                    "completion-menu": "bg:#1a1a2e #FFF8DC",
                    "completion-menu.completion.current": "bg:#333355 #FFD700",
                }
            )

        style = DynamicStyle(_build_style)

        # Application
        self.app = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
            mouse_support=False,
            cursor=STEADY_CURSOR,
        )

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings."""
        kb = KeyBindings()

        @kb.add("enter")
        def handle_enter(event):
            """Submit input."""
            text = event.app.current_buffer.text
            if text.strip():
                self._pending_input.put(text)
                event.app.current_buffer.reset(append_to_history=True)

        @kb.add("c-c")
        def handle_ctrl_c(event):
            """Interrupt or cancel."""
            if self._agent_running:
                self._interrupt_queue.put("__INTERRUPT__")
            else:
                event.app.current_buffer.reset()

        @kb.add("c-d")
        def handle_ctrl_d(event):
            """Exit if buffer empty."""
            if not event.app.current_buffer.text:
                self._should_exit = True
                event.app.exit()

        @kb.add("c-l")
        def handle_ctrl_l(event):
            """Clear screen."""
            event.app.renderer.clear()

        @kb.add("escape", "enter")  # Alt+Enter
        def handle_alt_enter(event):
            """Insert newline."""
            event.current_buffer.insert_text("\n")

        @kb.add("c-j")  # Ctrl+Enter
        def handle_ctrl_enter(event):
            """Insert newline."""
            event.current_buffer.insert_text("\n")

        @kb.add("s-tab")  # Wave 6: cycle mode
        def handle_shift_tab(event):
            """Shift+Tab: cycle through chat → plan modes."""
            modes = ["chat", "plan"]
            self._mode = modes[(modes.index(self._mode) + 1) % len(modes)]
            mode_icons = {"chat": "●", "plan": "◉"}
            self._print_output(
                f"\n\033[2m◌ Mode: \033[0m\033[1m{self._mode}\033[0m"
                f" {mode_icons.get(self._mode, '')}\n\n"
            )
            self._invalidate_status()

        @kb.add("c-o")  # Wave 2: expand last tool output
        def handle_ctrl_o(event):
            """Ctrl+O: expand/collapse last tool output."""
            if not self._last_tool_output:
                return
            self._tool_output_expanded = not self._tool_output_expanded
            if self._tool_output_expanded:
                self._print_output(
                    f"\n\033[2m↑ Tool output (expanded):\033[0m\n"
                    f"{self._last_tool_output}\n"
                )
            else:
                self._print_output("\n\033[2m↓ Tool output collapsed.\033[0m\n\n")

        return kb

    def _get_prompt(self) -> str:
        """Get prompt text."""
        return "> "

    def _input_height(self) -> int:
        """Calculate dynamic input height."""
        try:
            from prompt_toolkit.application import get_app
            from prompt_toolkit.utils import get_cwidth

            doc = self.input_area.buffer.document
            prompt_width = max(2, get_cwidth(self._get_prompt()))
            available_width = get_app().output.get_size().columns - prompt_width

            visual_lines = 0
            for line in doc.lines:
                line_width = get_cwidth(line)
                if line_width <= 0:
                    visual_lines += 1
                else:
                    # Ceiling division for wrapped lines
                    visual_lines += max(1, -(-line_width // available_width))

            return min(max(visual_lines, 1), 8)
        except Exception:
            return 1

    def _get_status_bar_fragments(self) -> list[tuple[str, str]]:
        """Get status bar formatted text."""
        # Calculate context percentage
        if self._context_length > 0:
            percent = int((self._context_tokens / self._context_length) * 100)
        else:
            percent = 0

        tokens_str = f"{self._total_tokens:,}"
        cost_str = f"${self._total_cost:.4f}"

        cache_saved = getattr(self, "_cache_saved_tokens", 0)
        cache_str = f"{cache_saved // 1000}k" if cache_saved >= 1000 else str(cache_saved)

        verbosity = getattr(self, "_verbosity_pending", "full")
        agent = getattr(self, "_agent", None)
        if agent is not None:
            verbosity = agent.get_verbosity()

        # Context colour: green <70%, yellow 70–85%, red ≥85%
        if percent >= 85:
            ctx_style = "class:status-bar-warn"
        elif percent >= 70:
            ctx_style = "class:status-bar-warn"
        else:
            ctx_style = "class:status-bar-dim"

        # Wave 1: spinner line replaces model when agent is running
        spinner = getattr(self, "_spinner", None)
        if self._agent_running and spinner and spinner.current_line:
            model_fragment: list[tuple[str, str]] = [
                ("class:status-bar-good", spinner.current_line),
                ("class:status-bar-dim", " │ "),
                ("class:status-bar-dim", self.model),
            ]
        else:
            model_fragment = [("class:status-bar-strong", self.model)]

        # Wave 6: mode indicator
        mode = getattr(self, "_mode", "chat")
        mode_icons = {"chat": "●", "plan": "◉"}
        mode_icon = mode_icons.get(mode, "●")
        mode_style = "class:status-bar-mode-plan" if mode == "plan" else "class:status-bar-mode-chat"

        frags: list[tuple[str, str]] = [
            ("class:status-bar", " 🔬 "),
            *model_fragment,
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-dim", f"Tokens: {tokens_str}"),
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-dim", f"Cost: {cost_str}"),
            ("class:status-bar-dim", " │ "),
            (ctx_style, f"Ctx: {percent}%"),
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-good", f"Cache: {cache_str}"),
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-dim", f"Turn: {self._turn_count}"),
            ("class:status-bar-dim", f" [{verbosity}]"),
            ("class:status-bar-dim", " │ "),
            (mode_style, f"{mode} {mode_icon}"),
            ("class:status-bar", " "),
        ]

        return frags

    def _get_hint_bar_fragments(self) -> list[tuple[str, str]]:
        """Wave 8: context-sensitive keyboard hint line."""
        sep = ("class:hint-bar", "  ·  ")
        if self._agent_running:
            hints = [
                ("class:hint-bar", " ctrl+c interrupt agent"),
                sep,
                ("class:hint-bar", "ctrl+o expand tool"),
            ]
        else:
            hints = [
                ("class:hint-bar", " ctrl+c cancel"),
                sep,
                ("class:hint-bar", "ctrl+o expand tool"),
                sep,
                ("class:hint-bar", "ctrl+h history"),
                sep,
                ("class:hint-bar", "ctrl+r search"),
                sep,
                ("class:hint-bar", "shift+tab mode"),
                sep,
                ("class:hint-bar", "/help"),
            ]
        return hints

    def _process_loop(self):
        """Background processing loop.

        Must NOT call asyncio.set_event_loop — doing so poisons the loop
        reference that patch_stdout's _StdoutProxy captures from the main
        thread, causing it to schedule output on this thread's loop
        (which is only running during run_until_complete) and then fall
        back to a direct raw-mode write that mangles ESC bytes.
        asyncio.run() creates and destroys its own loop without touching
        the module-level current-loop pointer.
        """
        while not self._should_exit:
            try:
                user_input = self._pending_input.get(timeout=0.1)
            except queue.Empty:
                continue

            if user_input.startswith("/"):
                self._handle_command(user_input)
            else:
                asyncio.run(self._run_agent(user_input))

    def _handle_command(self, command: str):
        """Handle slash command."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "/exit" or cmd == "/quit":
            self._should_exit = True
            self.app.exit()

        elif cmd == "/help":
            self._print_output("\n\033[1mAvailable Commands:\033[0m\n\n")
            from .input import SLASH_COMMANDS
            for slash_cmd, desc in SLASH_COMMANDS.items():
                self._print_output(f"  \033[36m{slash_cmd:<15}\033[0m {desc}\n")
            self._print_output("\n")

        elif cmd == "/status":
            self._print_output("\n\033[1mSession Status:\033[0m\n")
            self._print_output(f"  Session: \033[35m{self.session_id}\033[0m\n")
            self._print_output(f"  Model: \033[36m{self.model}\033[0m\n")
            self._print_output(f"  Tokens: \033[33m{self._total_tokens:,}\033[0m\n")
            self._print_output(f"  Cost: \033[32m${self._total_cost:.4f}\033[0m\n")
            self._print_output(f"  Context: \033[33m{self._context_tokens:,}\033[0m / \033[33m{self._context_length:,}\033[0m\n\n")

        elif cmd == "/model" or cmd == "/models":
            self._handle_model_command(args)

        elif cmd == "/config" or cmd == "/credentials":
            self._handle_credentials_command(args)

        elif cmd == "/research" or cmd == "/deep-research":
            self._handle_research_command(args)

        elif cmd == "/team":
            self._handle_team_command(args)

        elif cmd == "/memory":
            self._handle_memory_command(args)

        elif cmd == "/reflect":
            self._handle_reflect_command(args)

        elif cmd == "/skills":
            self._handle_skills_command(args)

        elif cmd == "/mcp":
            self._handle_mcp_command(args)

        elif cmd == "/usage" or cmd == "/cost":
            self._print_output("\n\033[1mUsage Statistics:\033[0m\n")
            self._print_output(f"  Total Tokens: \033[33m{self._total_tokens:,}\033[0m\n")
            self._print_output(f"  Total Cost: \033[32m${self._total_cost:.4f}\033[0m\n")
            if self.budget_cap_usd:
                remaining = self.budget_cap_usd - self._total_cost
                percent = (self._total_cost / self.budget_cap_usd) * 100
                self._print_output(f"  Budget: \033[32m${self.budget_cap_usd:.2f}\033[0m\n")
                self._print_output(f"  Remaining: \033[32m${remaining:.4f}\033[0m (\033[33m{percent:.1f}%\033[0m used)\n")
            self._print_output("\n")

        elif cmd == "/clear":
            import os
            os.system('clear' if os.name != 'nt' else 'cls')
            self._print_output("\n\033[2mScreen cleared.\033[0m\n\n")

        elif cmd == "/history":
            self._handle_history_command(args)

        elif cmd == "/verbosity":
            self._handle_verbosity_command(args)

        elif cmd == "/context":
            self._handle_context_command()

        else:
            self._print_output(f"\n\033[31mUnknown command:\033[0m {cmd}\n")
            self._print_output("\033[2mType /help for available commands.\033[0m\n\n")

    def _handle_research_command(self, args: list[str]):
        """Handle /research command."""
        if not args:
            self._print_output("\n\033[33mUsage:\033[0m /research <topic>\n")
            self._print_output("\033[2mExample: /research quantum computing\033[0m\n\n")
            return

        topic = " ".join(args)
        self._print_output(f"\n\033[1m🔬 Starting deep research on:\033[0m {topic}\n\n")

        # Queue research task
        self._pending_input.put(f"__RESEARCH__{topic}")

    def _handle_team_command(self, args: list[str]):
        """Handle /team command."""
        if not args or args[0] != "run":
            self._print_output("\n\033[33mUsage:\033[0m /team run <task>\n")
            self._print_output("\033[2mExample: /team run \"Build a REST API with tests\"\033[0m\n\n")
            return

        task = " ".join(args[1:])
        self._print_output(f"\n\033[1m👥 Starting team on:\033[0m {task}\n\n")

        # Queue team task
        self._pending_input.put(f"__TEAM__{task}")

    def _handle_memory_command(self, args: list[str]):
        """Handle /memory [add <fact>|show|search <q>|archive|stats]."""
        from .memory_manager import MemoryManager

        memory = MemoryManager()

        if not args or args[0] == "stats":
            stats = memory.get_stats()
            self._print_output("\n\033[1mMemory Statistics:\033[0m\n")
            self._print_output(f"  Core facts:       \033[33m{stats['core_facts']}\033[0m  (~{stats['core_tokens_est']} tokens, always in context)\n")
            self._print_output(f"  Archived sessions:\033[33m{stats['archived_sessions']}\033[0m\n")
            self._print_output(f"  Lessons learned:  \033[33m{stats['total_lessons']}\033[0m\n")
            self._print_output(f"  Skills tracked:   \033[33m{stats['skills_tracked']}\033[0m\n\n")
            return

        if args[0] == "show":
            facts = memory.get_core_facts()
            if not facts:
                self._print_output("\n\033[2mNo core facts stored. Use /memory add <fact>\033[0m\n\n")
                return
            self._print_output(f"\n\033[1mCore Memory ({len(facts)} facts, always in context):\033[0m\n")
            for i, fact in enumerate(facts):
                self._print_output(f"  [{i}] {fact}\n")
            self._print_output("\n")
            return

        if args[0] == "add" and len(args) > 1:
            fact = " ".join(args[1:])
            memory.add_core_fact(fact)
            # If agent is running, refresh its memory manager
            if hasattr(self, "_agent") and self._agent._memory_manager is not None:
                self._agent._memory_manager.core_memory.add(fact)
            self._print_output(f"\n\033[32m✓ Core fact added:\033[0m {fact}\n\n")
            return

        if args[0] == "search" and len(args) > 1:
            query = " ".join(args[1:])
            # Search reasoning bank
            lessons = memory.recall(query=query)
            # Search archival
            archived = memory.search_archival(query, limit=3)
            self._print_output(f"\n\033[1mMemory search:\033[0m \033[2m{query}\033[0m\n\n")
            if lessons:
                self._print_output(f"\033[1mLessons ({len(lessons)}):\033[0m\n")
                for lesson in lessons[:5]:
                    self._print_output(f"  \033[36m{lesson.verdict}\033[0m: {lesson.lesson}\n")
            if archived:
                self._print_output(f"\n\033[1mArchived sessions ({len(archived)}):\033[0m\n")
                for summary in archived:
                    self._print_output(f"  {summary[:120]}…\n")
            if not lessons and not archived:
                self._print_output("\033[2mNo results found.\033[0m\n")
            self._print_output("\n")
            return

        if args[0] == "archive":
            agent = getattr(self, "_agent", None)
            if agent is None or agent._context_manager is None:
                self._print_output("\n\033[2mNo active conversation to archive.\033[0m\n\n")
                return
            cm_stats = agent._context_manager.stats()
            summary = agent._context_manager._summary or f"Session with {cm_stats['total_turns']} turns."
            memory.archive_session(self.session_id, summary)
            self._print_output(f"\n\033[32m✓ Session archived\033[0m ({cm_stats['total_turns']} turns → archival store)\n\n")
            return

        self._print_output(
            "\n\033[33mUsage:\033[0m /memory [show|add <fact>|search <q>|archive|stats]\n\n"
        )

    def _handle_reflect_command(self, args: list[str]):
        """Handle /reflect command."""
        if len(args) < 3:
            self._print_output("\n\033[33mUsage:\033[0m /reflect tag:<tags> verdict:<verdict> :: <lesson>\n")
            self._print_output("\033[2mExample: /reflect tag:testing verdict:success :: Always write tests first\033[0m\n\n")
            return

        # Parse command
        tags = []
        verdict = "insight"
        lesson = ""

        for i, arg in enumerate(args):
            if arg.startswith("tag:"):
                tags = arg[4:].split(",")
            elif arg.startswith("verdict:"):
                verdict = arg[8:]
            elif arg == "::":
                lesson = " ".join(args[i+1:])
                break

        if not lesson:
            self._print_output("\n\033[31mError:\033[0m Lesson text required after ::\n\n")
            return

        # Store lesson
        from .memory_manager import MemoryManager
        memory = MemoryManager()
        lesson_id = memory.reflect(tags, verdict, lesson)

        self._print_output(f"\n\033[32m✓ Lesson stored\033[0m (ID: {lesson_id})\n")
        self._print_output(f"  Tags: {', '.join(tags)}\n")
        self._print_output(f"  Verdict: {verdict}\n\n")

    def _handle_skills_command(self, args: list[str]):
        """Handle /skills command."""
        from .skill_manager import SkillManager

        skill_mgr = SkillManager()

        if not args:
            # Show stats
            stats = skill_mgr.get_stats()
            self._print_output("\n\033[1mSkills:\033[0m\n")
            self._print_output(f"  Total: \033[33m{stats['total_skills']}\033[0m\n")
            self._print_output(f"  Directory: {stats['skills_dir']}\n\n")
            return

        if args[0] == "list":
            skills = skill_mgr.list_skills()
            self._print_output(f"\n\033[1mInstalled Skills ({len(skills)}):\033[0m\n\n")
            for skill in skills:
                self._print_output(f"  - {skill}\n")
            self._print_output("\n")

    def _handle_mcp_command(self, args: list[str]):
        """Handle /mcp command."""
        from .skill_manager import MCPManager

        mcp_mgr = MCPManager()

        if not args:
            # Show stats
            stats = mcp_mgr.get_stats()
            self._print_output("\n\033[1mMCP Servers:\033[0m\n")
            self._print_output(f"  Total: \033[33m{stats['total_servers']}\033[0m\n")
            self._print_output(f"  Config: {stats['config_file']}\n\n")
            return

        if args[0] == "list":
            servers = mcp_mgr.list_servers()
            self._print_output(f"\n\033[1mConfigured MCP Servers ({len(servers)}):\033[0m\n\n")
            for server in servers:
                self._print_output(f"  - {server}\n")
            self._print_output("\n")

    def _handle_history_command(self, args: list[str]):
        """Handle /history [clear|show|stats|search <query>]."""
        agent = getattr(self, "_agent", None)

        if not args or args[0] == "show":
            if agent is None:
                self._print_output("\n\033[2mNo conversation started yet.\033[0m\n\n")
                return
            stats = agent.history_stats()
            self._print_output("\n\033[1mConversation Memory:\033[0m\n")
            self._print_output(f"  Total turns: \033[33m{stats.get('total_turns', 0)}\033[0m\n")
            self._print_output(f"  In window:   \033[33m{stats.get('verbatim_turns', 0)}\033[0m turns verbatim\n")
            self._print_output(f"  Summarized:  \033[33m{stats.get('summarized_turns', 0)}\033[0m turns → {stats.get('summary_tokens_est', 0)} tokens\n")
            self._print_output(f"  Compressions run: \033[33m{stats.get('compressions', 0)}\033[0m\n")
            self._print_output(f"  Verbosity: \033[36m{stats.get('verbosity', 'full')}\033[0m\n\n")
            return

        if args[0] == "clear":
            if agent is not None:
                agent.clear_history()
            self._turn_count = 0
            self._total_tokens = 0
            self._total_cost = 0.0
            self._context_tokens = 0
            self._invalidate_status()
            self._print_output("\n\033[32m✓ Conversation memory cleared.\033[0m\n\n")
            return

        if args[0] == "stats":
            if agent is None:
                self._print_output("\n\033[2mNo conversation started yet.\033[0m\n\n")
                return
            stats = agent.history_stats()
            tf = stats.get("tool_filter", {})
            self._print_output("\n\033[1mContext Optimization Stats:\033[0m\n")
            self._print_output(f"  Context used:   \033[33m{stats.get('context_pct', 0):.1f}%\033[0m of {stats.get('context_limit', 0):,} token limit\n")
            self._print_output(f"  Cache saved:    \033[32m{stats.get('cache_saved_tokens', 0):,}\033[0m tokens (Anthropic cache)\n")
            self._print_output(f"  Tool filter:    \033[32m{tf.get('tokens_saved_est', 0):,}\033[0m tokens saved "
                             f"({tf.get('calls', 0)} calls, {100*(1-tf.get('compression_ratio',1)):.0f}% compression)\n")
            self._print_output(f"  Retriever index:\033[33m{stats.get('retriever_size', 0)}\033[0m messages\n")
            self._print_output(f"  Total tokens:   \033[33m{stats.get('total_tokens', 0):,}\033[0m\n")
            self._print_output(f"  Total cost:     \033[32m${stats.get('total_cost', 0):.4f}\033[0m\n\n")
            return

        if args[0] == "search" and len(args) > 1:
            if agent is None:
                self._print_output("\n\033[2mNo conversation started yet.\033[0m\n\n")
                return
            query = " ".join(args[1:])
            results = agent.retrieve_relevant(query, top_k=5)
            self._print_output(f"\n\033[1mSemantic search:\033[0m \033[2m{query}\033[0m\n")
            if not results:
                self._print_output("\033[2mNo relevant turns found.\033[0m\n\n")
                return
            for i, msg in enumerate(results, 1):
                role_color = "\033[36m" if msg["role"] == "user" else "\033[32m"
                preview = msg["content"][:120].replace("\n", " ")
                self._print_output(f"  {i}. {role_color}{msg['role']}\033[0m: {preview}…\n")
            self._print_output("\n")
            return

        self._print_output(
            "\n\033[33mUsage:\033[0m /history [clear|show|stats|search <query>]\n\n"
        )

    def _handle_verbosity_command(self, args: list[str]):
        """Handle /verbosity [lite|full|ultra|off]."""
        if not args:
            agent = getattr(self, "_agent", None)
            current = agent.get_verbosity() if agent else "full"
            self._print_output(f"\n\033[1mCurrent verbosity:\033[0m \033[36m{current}\033[0m\n")
            self._print_output("\033[2mLevels: lite | full (default) | ultra | off\033[0m\n")
            self._print_output("\033[2mUsage: /verbosity <level>\033[0m\n\n")
            return

        level = args[0].lower()
        if level not in ("lite", "full", "ultra", "off"):
            self._print_output(f"\n\033[31mUnknown level:\033[0m {level}\n")
            self._print_output("\033[2mChoose: lite | full | ultra | off\033[0m\n\n")
            return

        agent = getattr(self, "_agent", None)
        if agent is not None:
            agent.set_verbosity(level)

        # Store for when agent is initialized
        self._verbosity_pending = level
        self._print_output(f"\n\033[32m✓ Verbosity set to:\033[0m \033[36m{level}\033[0m\n\n")

    def _handle_context_command(self):
        """Handle /context — show context window and compression metrics."""
        agent = getattr(self, "_agent", None)
        if agent is None:
            self._print_output("\n\033[2mNo conversation started yet.\033[0m\n\n")
            return

        stats = agent.history_stats()
        tf = stats.get("tool_filter", {})
        pct = stats.get("context_pct", 0.0)
        limit = stats.get("context_limit", 0)

        # Context bar
        bar_filled = int(pct / 5)
        bar_color = "\033[31m" if pct >= 85 else "\033[33m" if pct >= 70 else "\033[32m"
        bar = bar_color + "█" * bar_filled + "\033[2m" + "░" * (20 - bar_filled) + "\033[0m"

        self._print_output(f"\n\033[1mContext Window:\033[0m {bar} {pct:.1f}% of {limit:,} tokens\n\n")
        self._print_output("\033[1mHistory (Phase D — sliding window):\033[0m\n")
        self._print_output(f"  Verbatim turns:   {stats.get('verbatim_turns', 0)}\n")
        self._print_output(f"  Summarized turns: {stats.get('summarized_turns', 0)}"
                          f"  → {stats.get('summary_tokens_est', 0)} tokens\n")
        self._print_output(f"  Compressions:     {stats.get('compressions', 0)}\n\n")
        self._print_output("\033[1mOptimizations:\033[0m\n")
        self._print_output(f"  Tool filter (C):  {100*(1-tf.get('compression_ratio',1)):.0f}% reduction"
                          f"  — {tf.get('tokens_saved_est', 0):,} tokens saved\n")
        self._print_output(f"  Cache hits  (H):  {stats.get('cache_saved_tokens', 0):,} tokens saved\n")
        self._print_output(f"  Retriever   (G):  {stats.get('retriever_size', 0)} messages indexed\n")
        self._print_output(f"  Verbosity   (B):  {stats.get('verbosity', 'full')}\n\n")

    def _handle_model_command(self, args: list[str]):
        """Handle /model command."""
        from .credentials import AVAILABLE_MODELS, parse_model_string

        if not args:
            # Wave 5: formatted model picker with ❯/✔ symbols
            self._print_output(
                f"\n\033[1m╭─ Switch Model {'─' * 38}╮\033[0m\n"
            )
            for provider, models in AVAILABLE_MODELS.items():
                self._print_output(
                    f"\033[1m│  {provider.title():<53}\033[0m\033[1m│\033[0m"
                )
                self._print_output(
                    f"\033[2m│  {'─' * 53}│\033[0m"
                )
                for mdl in models:
                    from .credentials import parse_model_string
                    _, cur_name = parse_model_string(self.model)
                    is_current = mdl == cur_name or mdl == self.model
                    cursor = "\033[33m❯\033[0m" if is_current else " "
                    check  = " \033[32m✔\033[0m" if is_current else "  "
                    self._print_output(
                        f"\033[2m│\033[0m {cursor} \033[36m{mdl:<48}\033[0m{check} \033[2m│\033[0m"
                    )
            self._print_output(f"\033[1m╰{'─' * 55}╯\033[0m\n")
            self._print_output(
                "\033[2m  ↑↓ or type: /model <name>  ·  current marked ✔\033[0m\n\n"
            )
        else:
            # Switch model
            new_model = args[0]
            provider, model_name = parse_model_string(new_model)

            self._print_output(f"\n\033[1mSwitching to:\033[0m \033[36m{model_name}\033[0m (\033[33m{provider}\033[0m)\n")

            # Check if credentials are configured
            from .credentials import CredentialManager
            cred_mgr = CredentialManager()
            creds = cred_mgr.get_provider(provider)

            if not creds:
                self._print_output(f"\n\033[33mNo credentials found for {provider}.\033[0m\n")
                self._print_output(f"\033[2mRun: /credentials {provider}\033[0m\n\n")
            else:
                self.model = model_name
                # Force _agent to be re-initialised with the new provider
                # on the next turn; the old instance is bound to the
                # previous model's credentials and must not be reused.
                if hasattr(self, "_agent"):
                    del self._agent
                self._print_output(f"\n\033[32m✓ Model switched to {model_name}\033[0m\n\n")

    def _handle_credentials_command(self, args: list[str]):
        """Handle /credentials command."""
        from .credentials import (
            DEFAULT_BASE_URLS,
            CredentialManager,
            format_credentials_prompt,
        )

        cred_mgr = CredentialManager()

        if not args:
            # Show configured providers
            providers = cred_mgr.list_providers()
            self._print_output("\n\033[1mConfigured Providers:\033[0m\n\n")
            if providers:
                for provider in providers:
                    creds: dict = cred_mgr.get_provider(provider) or {}
                    has_url = "base_url" in creds
                    self._print_output(f"  \033[32m✓\033[0m \033[36m{provider}\033[0m")
                    if has_url:
                        self._print_output(f" (\033[33m{creds['base_url']}\033[0m)")
                    self._print_output("\n")
            else:
                self._print_output("  \033[2mNo providers configured\033[0m\n")

            self._print_output("\n\033[2mUsage: /credentials <provider>\033[0m\n")
            self._print_output("\033[2mExample: /credentials anthropic\033[0m\n\n")
        else:
            # Configure provider
            provider = args[0].lower()
            self._print_output(f"\n{format_credentials_prompt(provider)}\n")
            self._print_output("\033[1mPaste your credentials:\033[0m\n")
            self._print_output("\033[2m(Input will be saved to ~/.lyra/credentials.json)\033[0m\n\n")

            # Note: In real implementation, this would read from input
            # For now, show instructions
            self._print_output(f"\033[33mTo configure {provider}:\033[0m\n")
            self._print_output("1. Get API key from provider\n")
            self._print_output(f"2. Run: export {provider.upper()}_API_KEY='your-key'\n")
            self._print_output("3. Or paste JSON config when prompted\n\n")
            self._print_output(f"\033[2mDefault base URL: {DEFAULT_BASE_URLS.get(provider, 'N/A')}\033[0m\n\n")

    def _invalidate_status(self) -> None:
        """Force the status bar to re-render after stats change."""
        try:
            if getattr(self.app, "_is_running", False):
                self.app.invalidate()
        except Exception:
            pass

    async def _ensure_agent(self) -> None:
        """Lazily initialise TUIAgentIntegration and apply pending settings."""
        if not hasattr(self, "_agent"):
            from .agent_integration import TUIAgentIntegration
            self._agent = TUIAgentIntegration(
                model=self.model,
                repo_root=self.repo_root,
                budget_cap_usd=self.budget_cap_usd,
            )
            await self._agent.initialize()
            # Phase B: apply any verbosity set before agent existed
            self._agent.set_verbosity(self._verbosity_pending)

    def _flush_usage(self) -> None:
        """Pull latest stats from the agent and refresh the status bar."""
        stats = self._agent.get_usage_stats()
        self._total_tokens = stats["total_tokens"]
        self._total_cost = stats["total_cost"]
        self._context_tokens = stats["context_tokens"]
        self._cache_saved_tokens = stats.get("cache_saved_tokens", 0)  # Phase H
        self._invalidate_status()

    async def _stream_to_output(self, prompt: str) -> None:
        """Send *prompt* to the LLM and print the streaming response.

        Line-buffered: each run_in_terminal call emits a complete line so
        the PT redraw cycle never splits an ANSI escape sequence.
        Handles text, tool, usage (Phase H cache stats), and warning events.
        """
        buf = ""
        async for event in self._agent.run_agent(prompt):
            etype = event["type"]

            if etype in ("text", "tool"):
                content = event["content"]
                if etype == "tool":
                    content = f"\033[2m[tool] {content}\033[0m"
                buf += content
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    self._print_output(line)

            elif etype == "tool_display":
                # Wave 2: ⎿ tool use line
                if buf:
                    self._print_output(buf, end="")
                    buf = ""
                meta = event.get("metadata", {})
                name = meta.get("name", event.get("content", "tool"))
                args = meta.get("args", "")
                lines = meta.get("lines", 0)
                output = meta.get("output", "")
                self._last_tool_output = output
                self._tool_output_expanded = False
                suffix = f" ({lines} lines)" if lines else ""
                trunc = " \033[33m[truncated]\033[0m" if meta.get("truncated") else ""
                self._print_output(
                    f"\033[2m⎿  {name} {args}{suffix}{trunc}\033[0m"
                )

            elif etype == "compaction":
                # Wave 3: ✻ compaction notice
                if buf:
                    self._print_output(buf, end="")
                    buf = ""
                meta = event.get("metadata", {})
                turns = meta.get("turns", 0)
                self._print_output(
                    f"\n\033[36m✻ Conversation compacted"
                    f"{f' · {turns} turns → summary' if turns else ''}"
                    f"  \033[2m(ctrl+h for history)\033[0m\n"
                )

            elif etype == "usage":
                self._flush_usage()
                # Wave 3: cache hit notice when savings are meaningful
                meta = event.get("metadata", {})
                cache_read = meta.get("cache_read_tokens", 0)
                if cache_read >= 500:
                    saved_usd = (cache_read / 1_000_000) * 3.0 * 0.9
                    self._print_output(
                        f"\033[2m✶ Cache hit · saved {cache_read:,} tokens"
                        f" (${saved_usd:.4f})\033[0m"
                    )

            elif etype == "warning":
                if buf:
                    self._print_output(buf, end="")
                    buf = ""
                self._print_output(event["content"], end="")

        if buf:
            self._print_output(buf, end="")
        self._print_output("\n")

    async def _run_research_pipeline(self, topic: str) -> None:
        """Real multi-hop deep research pipeline — no more asyncio.sleep() stubs."""
        self._print_output(f"\n\033[1mYou:\033[0m /research {topic}\n")

        try:
            await self._ensure_agent()
        except Exception as e:
            self._print_output(f"\n\033[31mAgent init failed:\033[0m {e}\n\n")
            return

        self._spinner.start_for(f"research {topic}")

        report = ""
        source_count = 0
        fact_count = 0
        provider_name = "?"

        async for event in self._agent.research(topic):
            etype = event.get("type", "")

            if etype == "phase":
                phase = event.get("phase", "")
                desc = event.get("content", "")
                pct = int(event.get("progress", 0) * 100)
                filled = pct // 5
                bar = "\033[36m" + "█" * filled + "\033[2m" + "░" * (20 - filled) + "\033[0m"
                self._print_output(
                    f"\n\033[1m⏺ {phase}\033[0m  \033[2m{desc}\033[0m  {bar} {pct}%"
                )

            elif etype == "finding":
                content = event.get("content", "")
                self._print_output(f"  \033[2m⎿  {content}\033[0m")
                # Track stats from finding lines
                if "sources" in content.lower():
                    import re as _re
                    m = _re.search(r'(\d+)\s+(?:unique\s+)?sources', content)
                    if m:
                        source_count = int(m.group(1))
                if "facts" in content.lower():
                    import re as _re
                    m = _re.search(r'(\d+)\s+(?:cited\s+|total\s+)?facts', content)
                    if m:
                        fact_count = int(m.group(1))
                if "provider:" in content.lower():
                    import re as _re
                    m = _re.search(r'provider:\s*(\w+)', content, _re.I)
                    if m:
                        provider_name = m.group(1)

            elif etype == "progress":
                pct = int(event.get("progress", 0) * 100)
                phase = event.get("phase", "")
                self._print_output(f"  \033[32m✔ {phase} ({pct}%)\033[0m")

            elif etype == "done":
                report = event.get("content", "")

            elif etype == "error":
                err = event.get("content", "unknown error")
                self._print_output(f"\n\033[31m✗ Research error:\033[0m {err}\n")
                self._print_output(
                    "\033[2mTo enable real search, install a provider:\033[0m\n"
                    "  \033[36mpip install duckduckgo-search\033[0m  (zero-key fallback)\n"
                    "  \033[36mpip install exa-py\033[0m + set EXA_API_KEY\n"
                )
                self._spinner.stop()
                return

        self._spinner.stop()

        if report:
            # Print the full report
            self._print_output(
                f"\n\033[1m━━ Research Report ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n"
            )
            # Stream report line by line for nicer display
            for line in report.splitlines():
                if line.startswith("## "):
                    self._print_output(f"\n\033[1m{line}\033[0m")
                elif line.startswith("# "):
                    self._print_output(f"\033[1m{line}\033[0m")
                elif line.startswith("[") and "](http" in line:
                    self._print_output(f"\033[36m{line}\033[0m")
                else:
                    self._print_output(line)

        elapsed = self._spinner.elapsed_str if self._spinner else "?"
        self._print_output(
            f"\n\033[32m✔ Research complete\033[0m  "
            f"\033[2m{source_count} sources · {fact_count} facts · "
            f"via {provider_name} · {elapsed}\033[0m\n"
        )
        self._turn_count += 1
        self._invalidate_status()

    async def _run_agent(self, user_input: str):
        """Run agent with user input.

        Strips internal ``__RESEARCH__`` / ``__TEAM__`` prefixes before
        display, routes research to the 10-phase pipeline, and keeps the
        status bar accurate after every turn.
        """
        self._agent_running = True

        try:
            await self._ensure_agent()

            # ── Route special prefixes ─────────────────────────────────
            if user_input.startswith("__RESEARCH__"):
                topic = user_input[len("__RESEARCH__"):]
                self._spinner.start_for(topic)
                await self._run_research_pipeline(topic)
                return

            if user_input.startswith("__TEAM__"):
                task = user_input[len("__TEAM__"):]
                display = f"/team run {task}"
            else:
                display = user_input

            # ── Normal chat turn ───────────────────────────────────────
            self._print_output(f"\n\033[1mYou:\033[0m {display}\n\n")

            # Wave 6: inject mode instruction into plan mode
            effective_prompt = display
            if self._mode == "plan":
                effective_prompt = (
                    "Think step by step and produce a clear plan before acting.\n\n"
                    + display
                )

            self._spinner.start_for(display)
            self._print_output("\033[1mAgent:\033[0m")

            await self._stream_to_output(effective_prompt)

            elapsed = self._spinner.elapsed_str
            self._spinner.stop()
            self._print_output(f"\033[2m✔ Done in {elapsed}\033[0m")

            self._turn_count += 1
            self._invalidate_status()

        except Exception as e:
            self._print_output(f"\n\033[31mError:\033[0m {e}\n\n")
        finally:
            if self._spinner:
                self._spinner.stop()
            self._agent_running = False
            self._invalidate_status()

    def _print_output(self, text: str, end: str = "\n"):
        """Thread-safe, ANSI-correct terminal output.

        get_app_or_none() uses a ContextVar scoped to the main thread, so
        it returns None from background threads even when the app is running.
        We use self.app directly so the background thread can always reach
        app.loop and schedule via call_soon_threadsafe → run_in_terminal.
        """
        from prompt_toolkit import print_formatted_text as _pt_print
        from prompt_toolkit.application import run_in_terminal
        from prompt_toolkit.formatted_text import ANSI as _PT_ANSI

        full = text + (end if end else "")

        app = self.app
        if not getattr(app, "_is_running", False):
            _pt_print(_PT_ANSI(full), end="")
            return

        try:
            loop = app.loop  # type: ignore[attr-defined]
        except Exception:
            loop = None
        if loop is None:
            _pt_print(_PT_ANSI(full), end="")
            return

        try:
            current = asyncio.get_running_loop()
        except RuntimeError:
            current = None

        if current is loop and loop.is_running():
            run_in_terminal(lambda: _pt_print(_PT_ANSI(full), end=""))
            return

        def _schedule() -> None:
            try:
                run_in_terminal(lambda: _pt_print(_PT_ANSI(full), end=""))
            except Exception:
                try:
                    _pt_print(_PT_ANSI(full), end="")
                except Exception:
                    pass

        try:
            loop.call_soon_threadsafe(_schedule)
        except Exception:
            try:
                _pt_print(_PT_ANSI(full), end="")
            except Exception:
                pass

    def run(self) -> int:
        """Run the TUI application."""
        # Wave 4: two-column welcome dashboard
        from lyra_cli import __version__
        try:
            # Detect provider from model string prefix
            _provider = self.model.split("/")[0] if "/" in self.model else "anthropic"
        except Exception:
            _provider = ""

        print(render_welcome(
            model=self.model,
            version=__version__,
            cwd=str(self.repo_root),
            api_provider=_provider,
        ))

        process_thread = threading.Thread(target=self._process_loop, daemon=True)
        process_thread.start()

        from prompt_toolkit.patch_stdout import patch_stdout
        try:
            with patch_stdout():
                self.app.run()
        except (EOFError, KeyboardInterrupt, BrokenPipeError):
            pass
        finally:
            self._should_exit = True

        return 0


def launch_tui(
    repo_root: Path,
    model: str,
    budget_cap_usd: float | None = None,
    session_id: str | None = None,
) -> int:
    """Launch Lyra TUI."""
    tui = LyraTUI(
        repo_root=repo_root,
        model=model,
        budget_cap_usd=budget_cap_usd,
        session_id=session_id,
    )
    return tui.run()

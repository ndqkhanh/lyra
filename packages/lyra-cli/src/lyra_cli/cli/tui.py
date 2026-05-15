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
import sys
import threading
from pathlib import Path
from typing import Any

from prompt_toolkit import print_formatted_text
from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    Dimension,
    FormattedTextControl,
    HSplit,
    Layout,
    Window,
)
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.widgets import TextArea

try:
    from prompt_toolkit.cursor_shapes import CursorShape

    STEADY_CURSOR = CursorShape.BLOCK
except (ImportError, AttributeError):
    STEADY_CURSOR = None

from .input import SlashCommandAutoSuggest, SlashCommandCompleter


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

        # Layout
        layout = Layout(
            HSplit(
                [
                    status_bar,
                    input_rule_top,
                    self.input_area,
                    input_rule_bot,
                    completions_menu,
                ]
            )
        )

        # Style
        style = PTStyle.from_dict(
            {
                "input-area": "#FFF8DC",
                "placeholder": "#555555 italic",
                "status-bar": "bg:#1a1a2e #C0C0C0",
                "status-bar-strong": "bg:#1a1a2e #FFD700 bold",
                "status-bar-dim": "bg:#1a1a2e #8B8682",
                "status-bar-good": "bg:#1a1a2e #8FBC8F bold",
                "status-bar-warn": "bg:#1a1a2e #FFD700 bold",
                "input-rule": "#CD7F32",
                "completion-menu": "bg:#1a1a2e #FFF8DC",
                "completion-menu.completion.current": "bg:#333355 #FFD700",
            }
        )

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
        # Calculate percentages
        if self._context_length > 0:
            percent = int((self._context_tokens / self._context_length) * 100)
        else:
            percent = 0

        # Format tokens
        tokens_str = f"{self._total_tokens:,}"
        cost_str = f"${self._total_cost:.4f}"

        # Build fragments with Lyra branding
        frags = [
            ("class:status-bar", " 🔬 "),  # Lyra icon (microscope for research)
            ("class:status-bar-strong", self.model),
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-dim", f"Tokens: {tokens_str}"),
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-dim", f"Cost: {cost_str}"),
            ("class:status-bar-dim", " │ "),
            ("class:status-bar-dim", f"Context: {percent}%"),
            ("class:status-bar", " "),
        ]

        return frags

    def _process_loop(self):
        """Background processing loop."""
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while not self._should_exit:
            try:
                user_input = self._pending_input.get(timeout=0.1)
            except queue.Empty:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                self._handle_command(user_input)
            else:
                # Run agent asynchronously
                loop.run_until_complete(self._run_agent(user_input))

        loop.close()

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
            self._print_output(f"\n\033[1mSession Status:\033[0m\n")
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
            self._print_output(f"\n\033[1mUsage Statistics:\033[0m\n")
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
            self._print_output("\n\033[2mHistory cleared.\033[0m\n\n")

        elif cmd == "/history":
            self._print_output("\n\033[1mCommand History:\033[0m\n")
            self._print_output("\033[2mPress Ctrl+R to search history\033[0m\n\n")

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
        """Handle /memory command."""
        from .memory_manager import MemoryManager

        memory = MemoryManager()

        if not args:
            # Show memory stats
            stats = memory.get_stats()
            self._print_output("\n\033[1mMemory Statistics:\033[0m\n")
            self._print_output(f"  Total Lessons: \033[33m{stats['total_lessons']}\033[0m\n")
            self._print_output(f"  Skills Tracked: \033[33m{stats['skills_tracked']}\033[0m\n")
            self._print_output(f"  Playbook Entries: \033[33m{stats['playbook_entries']}\033[0m\n\n")
            return

        if args[0] == "search":
            query = " ".join(args[1:])
            lessons = memory.recall(query=query)
            self._print_output(f"\n\033[1mFound {len(lessons)} lessons:\033[0m\n\n")
            for lesson in lessons[:5]:  # Show top 5
                self._print_output(f"  \033[36m{lesson.verdict}\033[0m: {lesson.lesson}\n")
            self._print_output("\n")

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

    def _handle_model_command(self, args: list[str]):
        """Handle /model command."""
        from .credentials import AVAILABLE_MODELS, parse_model_string

        if not args:
            # Show current model and available models
            self._print_output(f"\n\033[1mCurrent Model:\033[0m \033[36m{self.model}\033[0m\n\n")
            self._print_output("\033[1mAvailable Models:\033[0m\n\n")

            for provider, models in AVAILABLE_MODELS.items():
                self._print_output(f"  \033[1m{provider.title()}:\033[0m\n")
                for model in models:
                    self._print_output(f"    \033[36m{model}\033[0m\n")
                self._print_output("\n")

            self._print_output("\033[2mUsage: /model <model-name>\033[0m\n")
            self._print_output("\033[2mExample: /model claude-opus-4.7\033[0m\n\n")
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
                self._print_output(f"\n\033[32m✓ Model switched to {model_name}\033[0m\n\n")

    def _handle_credentials_command(self, args: list[str]):
        """Handle /credentials command."""
        from .credentials import (
            CredentialManager,
            format_credentials_prompt,
            parse_credential_input,
            DEFAULT_BASE_URLS,
        )

        cred_mgr = CredentialManager()

        if not args:
            # Show configured providers
            providers = cred_mgr.list_providers()
            self._print_output("\n\033[1mConfigured Providers:\033[0m\n\n")
            if providers:
                for provider in providers:
                    creds = cred_mgr.get_provider(provider)
                    has_key = "api_key" in creds
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
            self._print_output(f"1. Get API key from provider\n")
            self._print_output(f"2. Run: export {provider.upper()}_API_KEY='your-key'\n")
            self._print_output(f"3. Or paste JSON config when prompted\n\n")
            self._print_output(f"\033[2mDefault base URL: {DEFAULT_BASE_URLS.get(provider, 'N/A')}\033[0m\n\n")

    async def _run_agent(self, user_input: str):
        """Run agent with user input."""
        self._agent_running = True
        try:
            from .agent_integration import TUIAgentIntegration

            # Initialize agent if needed
            if not hasattr(self, "_agent"):
                self._agent = TUIAgentIntegration(
                    model=self.model,
                    repo_root=self.repo_root,
                    budget_cap_usd=self.budget_cap_usd,
                )
                await self._agent.initialize()

            # Print user input
            self._print_output(f"\n\033[1mYou:\033[0m {user_input}\n\n")
            self._print_output("\033[1mAgent:\033[0m ")

            # Stream agent response
            async for event in self._agent.run_agent(user_input):
                if event["type"] == "text":
                    self._print_output(event["content"], end="")
                elif event["type"] == "tool":
                    self._print_output(f"\033[2m{event['content']}\033[0m", end="")
                elif event["type"] == "usage":
                    # Update stats
                    stats = self._agent.get_usage_stats()
                    self._total_tokens = stats["total_tokens"]
                    self._total_cost = stats["total_cost"]
                    self._context_tokens = stats["context_tokens"]

            self._print_output("\n\n")

        except Exception as e:
            self._print_output(f"\n\033[31mError:\033[0m {e}\n\n")
        finally:
            self._agent_running = False

    def _print_output(self, text: str, end: str = "\n"):
        """Print output to terminal."""
        import sys
        print_formatted_text(ANSI(text), end=end)
        sys.stdout.flush()

    def run(self) -> int:
        """Run the TUI application."""
        # Print welcome banner
        from lyra_cli import __version__
        from .banner import get_banner

        print()
        print(get_banner("claude"))
        print()
        print(f"\033[1mLyra\033[0m \033[2mv{__version__}\033[0m")
        print(
            f"\033[2mModel:\033[0m \033[36m{self.model}\033[0m  "
            f"\033[2mRepo:\033[0m \033[33m{self.repo_root.name}\033[0m  "
            f"\033[2mSession:\033[0m \033[35m{self.session_id}\033[0m"
        )
        print()
        print(
            "\033[2mType \033[0m\033[36m/help\033[0m\033[2m for commands · "
            "\033[0m\033[36m/status\033[0m\033[2m for session info · "
            "\033[0m\033[36m⌥?\033[0m\033[2m for shortcuts\033[0m"
        )
        print()

        # Start background processing thread
        process_thread = threading.Thread(target=self._process_loop, daemon=True)
        process_thread.start()

        # Run application
        try:
            self.app.run()
        except KeyboardInterrupt:
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

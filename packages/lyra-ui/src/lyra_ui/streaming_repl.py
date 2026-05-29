"""
Streaming REPL - Claude Code-style streaming REPL interface.

Features:
- Real-time streaming output
- Rich formatting with syntax highlighting
- Slash command autocomplete
- File mention autocomplete (@file)
- Multi-line input support
- Status bar with metadata
- Tool execution progress display
- Vim-style keyboard navigation
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.text import Text

from lyra_ui.banner import BannerStats, BannerStyle, BannerSystem
from lyra_ui.formatter import RichFormatter
from lyra_ui.keyboard import CommandPalette, QuickActions, VimNavigator
from lyra_ui.streaming import LiveStreamDisplay, StreamHandler


class REPLMode(Enum):
    """REPL mode."""

    AGENT = "agent"
    PLAN = "plan"
    ASK = "ask"
    AUTO = "auto"


@dataclass
class REPLConfig:
    """REPL configuration."""

    mode: REPLMode = REPLMode.AGENT
    model: str = "sonnet"
    streaming: bool = True
    multiline: bool = True
    show_status_bar: bool = True
    show_progress: bool = True
    vim_mode: bool = False
    theme: str = "default"


class LyraCompleter(Completer):
    """
    Lyra command completer with slash commands and file mentions.

    Features:
    - Slash command completion (/command)
    - File mention completion (@file)
    - Skill mention completion (#skill)
    """

    def __init__(self):
        """Initialize completer."""
        self.commands = [
            "help",
            "model",
            "mode",
            "clear",
            "history",
            "exit",
            "skills",
            "agents",
            "memory",
            "plan",
            "execute",
            "status",
            "config",
        ]
        self.files: list[str] = []
        self.skills: list[str] = []

    def get_completions(self, document, complete_event):
        """
        Get completions for current input.

        Args:
            document: Current document
            complete_event: Completion event

        Yields:
            Completion objects
        """
        text = document.text_before_cursor
        word = document.get_word_before_cursor()

        # Slash command completion
        if text.startswith("/"):
            for cmd in self.commands:
                if cmd.startswith(word.lstrip("/")):
                    yield Completion(
                        cmd,
                        start_position=-len(word.lstrip("/")),
                        display=f"/{cmd}",
                        display_meta="command",
                    )

        # File mention completion
        elif "@" in text:
            for file in self.files:
                if file.startswith(word.lstrip("@")):
                    yield Completion(
                        file,
                        start_position=-len(word.lstrip("@")),
                        display=f"@{file}",
                        display_meta="file",
                    )

        # Skill mention completion
        elif "#" in text:
            for skill in self.skills:
                if skill.startswith(word.lstrip("#")):
                    yield Completion(
                        skill,
                        start_position=-len(word.lstrip("#")),
                        display=f"#{skill}",
                        display_meta="skill",
                    )

    def set_files(self, files: list[str]):
        """Set available files for completion."""
        self.files = files

    def set_skills(self, skills: list[str]):
        """Set available skills for completion."""
        self.skills = skills


class StreamingREPL:
    """
    Claude Code-style streaming REPL for Lyra.

    Features:
    - Real-time streaming output
    - Rich formatting
    - Autocomplete
    - Status bar
    - Progress indicators
    - Multi-line input
    """

    def __init__(self, config: REPLConfig | None = None):
        """
        Initialize streaming REPL.

        Args:
            config: REPL configuration
        """
        self.config = config or REPLConfig()
        self.console = Console()
        self.formatter = RichFormatter()
        self.banner_system = BannerSystem(
            console=self.console,
            style=BannerStyle.STANDARD,
        )

        # Components
        self.completer = LyraCompleter()
        self.stream_handler = StreamHandler()
        self.live_display = LiveStreamDisplay()
        self.vim_navigator = VimNavigator()
        self.command_palette = CommandPalette()
        self.quick_actions = QuickActions()

        # Session
        self.session: PromptSession | None = None
        self.history: list[str] = []
        self.running = False

        # Stats
        self.stats = BannerStats()

        # Setup
        self._setup_session()
        self._setup_commands()

    def _setup_session(self):
        """Set up prompt session."""
        # Key bindings
        kb = KeyBindings()

        @kb.add("c-c")
        def _(event):
            """Cancel current operation."""
            self.stream_handler.cancel()

        @kb.add("c-d")
        def _(event):
            """Exit REPL."""
            event.app.exit()

        # Prompt style
        style = Style.from_dict(
            {
                "prompt": "cyan bold",
                "mode": "yellow",
            }
        )

        # Create session
        self.session = PromptSession(
            completer=self.completer,
            style=style,
            key_bindings=kb,
            multiline=self.config.multiline,
            enable_history_search=True,
        )

    def _setup_commands(self):
        """Set up command palette."""
        self.command_palette.register_command(
            "help",
            self._cmd_help,
            category="general",
        )
        self.command_palette.register_command(
            "clear",
            self._cmd_clear,
            category="general",
        )
        self.command_palette.register_command(
            "exit",
            self._cmd_exit,
            category="general",
        )
        self.command_palette.register_command(
            "model",
            self._cmd_model,
            category="config",
        )
        self.command_palette.register_command(
            "mode",
            self._cmd_mode,
            category="config",
        )

    def get_prompt(self) -> HTML:
        """
        Generate dynamic prompt with mode badge.

        Returns:
            Formatted prompt
        """
        mode_badge = self._get_mode_badge()
        return HTML(f"<mode>{mode_badge}</mode> <prompt>></prompt> ")

    def _get_mode_badge(self) -> str:
        """Get mode badge text."""
        badges = {
            REPLMode.AGENT: "[agent]",
            REPLMode.PLAN: "[plan]",
            REPLMode.ASK: "[ask]",
            REPLMode.AUTO: "[auto]",
        }
        return badges.get(self.config.mode, "[agent]")

    async def run(self):
        """Main REPL loop with streaming."""
        self.running = True

        # Display startup banner
        self._display_startup()

        while self.running:
            try:
                # Get user input
                user_input = await self.session.prompt_async(
                    self.get_prompt(),
                )

                if not user_input.strip():
                    continue

                # Add to history
                self.history.append(user_input)

                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Process input and stream response
                await self._process_input(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted[/yellow]")
                continue
            except EOFError:
                break
            except Exception as e:
                self.formatter.print_status(
                    f"Error: {str(e)}",
                    status="error",
                )

        # Display shutdown banner
        self._display_shutdown()

    async def _process_input(self, user_input: str):
        """
        Process user input and stream response.

        Args:
            user_input: User input text
        """
        # Show processing indicator
        with self.console.status("[cyan]Processing...[/cyan]"):
            # Simulate agent processing (replace with actual agent call)
            response_stream = self._mock_agent_stream(user_input)

            # Stream response
            await self._stream_response(response_stream)

    async def _stream_response(self, stream: AsyncIterator[str]):
        """
        Stream response with live display.

        Args:
            stream: Response stream
        """
        self.live_display.start()

        try:
            async for chunk in stream:
                if self.stream_handler.is_cancelled:
                    break

                self.live_display.append_token(chunk)
                self.stats.tokens_used += 1

                # Small delay for smooth rendering
                await asyncio.sleep(0.01)

        finally:
            self.live_display.stop()
            self.console.print()  # New line after stream

    async def _mock_agent_stream(self, user_input: str) -> AsyncIterator[str]:
        """
        Mock agent stream for testing.

        Args:
            user_input: User input

        Yields:
            Response chunks
        """
        response = f"Processing: {user_input}\n\nThis is a mock response. "
        response += "In production, this would be replaced with actual agent streaming."

        for char in response:
            yield char
            await asyncio.sleep(0.02)

    async def _handle_command(self, command: str):
        """
        Handle slash command.

        Args:
            command: Command string
        """
        parts = command[1:].split()
        if not parts:
            return

        cmd_name = parts[0]
        cmd_args = parts[1:]

        # Execute command
        result = self.command_palette.execute_command(cmd_name, *cmd_args)

        if result is not None:
            self.console.print(result)

    def _cmd_help(self) -> str:
        """Show help message."""
        help_text = """
[bold cyan]Lyra Streaming REPL[/bold cyan]

[bold]Commands:[/bold]
  /help       - Show this help
  /model      - Change model (sonnet, opus, haiku)
  /mode       - Change mode (agent, plan, ask, auto)
  /clear      - Clear screen
  /history    - Show command history
  /exit       - Exit REPL

[bold]Quick Actions:[/bold]
  @file       - Mention file
  #skill      - Mention skill
  /command    - Run command

[bold]Keyboard Shortcuts:[/bold]
  Ctrl+C      - Cancel current operation
  Ctrl+D      - Exit REPL
  Tab         - Autocomplete
"""
        return help_text

    def _cmd_clear(self):
        """Clear screen."""
        self.console.clear()

    def _cmd_exit(self):
        """Exit REPL."""
        self.running = False

    def _cmd_model(self, model: str | None = None) -> str:
        """Change model."""
        if model:
            self.config.model = model
            return f"Model changed to: {model}"
        return f"Current model: {self.config.model}"

    def _cmd_mode(self, mode: str | None = None) -> str:
        """Change mode."""
        if mode:
            try:
                self.config.mode = REPLMode(mode)
                return f"Mode changed to: {mode}"
            except ValueError:
                return f"Invalid mode: {mode}"
        return f"Current mode: {self.config.mode.value}"

    def _display_startup(self):
        """Display startup banner."""
        self.banner_system.display(
            title="Lyra Streaming REPL",
            subtitle="Claude Code-style interface",
            status="Ready",
        )
        self.console.print()

    def _display_shutdown(self):
        """Display shutdown message."""
        self.console.print()
        self.formatter.print_status(
            f"Session complete. Commands: {len(self.history)}",
            status="info",
        )

    def set_agent(self, agent: Any):
        """
        Set agent for processing.

        Args:
            agent: Agent instance
        """
        # Store agent reference for actual processing
        pass

    def update_stats(self, **kwargs):
        """
        Update statistics.

        Args:
            **kwargs: Stat updates
        """
        for key, value in kwargs.items():
            if hasattr(self.stats, key):
                setattr(self.stats, key, value)


class ToolProgressDisplay:
    """
    Tool execution progress display.

    Features:
    - Real-time tool execution tracking
    - Progress bars
    - Status indicators
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize tool progress display.

        Args:
            console: Rich console
        """
        self.console = console or Console()
        self.progress: Progress | None = None
        self.tasks: dict[str, int] = {}

    def start(self):
        """Start progress display."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        )
        self.progress.start()

    def stop(self):
        """Stop progress display."""
        if self.progress:
            self.progress.stop()
            self.progress = None

    def add_tool(self, tool_name: str, description: str) -> int:
        """
        Add tool to progress.

        Args:
            tool_name: Tool name
            description: Tool description

        Returns:
            Task ID
        """
        if self.progress:
            task_id = self.progress.add_task(
                f"[cyan]{tool_name}[/cyan]: {description}",
                total=100,
            )
            self.tasks[tool_name] = task_id
            return task_id
        return -1

    def update_tool(self, tool_name: str, progress: float):
        """
        Update tool progress.

        Args:
            tool_name: Tool name
            progress: Progress percentage (0-100)
        """
        if self.progress and tool_name in self.tasks:
            task_id = self.tasks[tool_name]
            self.progress.update(task_id, completed=progress)

    def complete_tool(self, tool_name: str):
        """
        Mark tool as complete.

        Args:
            tool_name: Tool name
        """
        if self.progress and tool_name in self.tasks:
            task_id = self.tasks[tool_name]
            self.progress.update(task_id, completed=100)


class StatusBar:
    """
    Status bar with segmented metadata.

    Features:
    - Mode indicator
    - Model indicator
    - Token count
    - Cost estimate
    - Time elapsed
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize status bar.

        Args:
            console: Rich console
        """
        self.console = console or Console()
        self.mode = "agent"
        self.model = "sonnet"
        self.tokens = 0
        self.cost = 0.0
        self.elapsed = 0.0

    def render(self) -> Panel:
        """
        Render status bar.

        Returns:
            Status bar panel
        """
        text = Text()

        # Mode
        text.append(f"[{self.mode}]", style="yellow")
        text.append(" | ")

        # Model
        text.append(f"Model: {self.model}", style="cyan")
        text.append(" | ")

        # Tokens
        text.append(f"Tokens: {self.tokens:,}", style="green")
        text.append(" | ")

        # Cost
        text.append(f"Cost: ${self.cost:.4f}", style="magenta")
        text.append(" | ")

        # Time
        text.append(f"Time: {self.elapsed:.1f}s", style="blue")

        return Panel(
            text,
            border_style="dim",
            height=3,
        )

    def display(self):
        """Display status bar."""
        panel = self.render()
        self.console.print(panel)

    def update(self, **kwargs):
        """
        Update status bar values.

        Args:
            **kwargs: Values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

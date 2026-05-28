"""CLI implementation of AgentOutputCallback with Fixed Bottom Layout support"""

import time
from typing import Any

from rich.console import Console

from lyra_cli.agent.callbacks import AgentOutputCallback
from lyra_cli.ui.colors import ColorEngine
from lyra_cli.ui.fixed_layout import FixedBottomLayout, StreamingRenderer
from lyra_cli.ui.symbols import SymbolRegistry


class FixedLayoutAgentHandler(AgentOutputCallback):
    """Agent handler that uses fixed bottom layout for Claude Code-style UI"""

    def __init__(self, layout: FixedBottomLayout):
        self.layout = layout
        self.symbols = SymbolRegistry()
        self.colors = ColorEngine()
        self.renderer: StreamingRenderer | None = None
        self.current_turn: str | None = None
        self.turn_start_time: float | None = None
        self.tool_count = 0

    def on_turn_start(self, turn_id: str) -> None:
        """Called when agent turn starts"""
        self.current_turn = turn_id
        self.turn_start_time = time.time()
        self.tool_count = 0

        # Show processing indicator
        symbol = self.symbols.status("running")
        self.layout.append_content(f"{self.colors.yellow(symbol)} Processing your message...")

        # Update status to show working
        self.layout.set_status("  ⏵⏵ working · esc to interrupt")

        # Initialize streaming renderer
        self.renderer = StreamingRenderer(self.layout)

    def on_tool_use(self, tool: str, args: dict[str, Any]) -> None:
        """Called when agent uses a tool"""
        self.tool_count += 1

        # Show tool use with connector
        connector = self.symbols.get("⎿")
        tool_line = f"  {self.colors.dim(connector)}  {tool}"
        self.layout.append_content(tool_line)

    def on_stream_chunk(self, chunk: str) -> None:
        """Called for streaming text chunks"""
        if self.renderer:
            self.renderer.append_delta(chunk)

    def on_turn_end(self, turn_id: str, result: dict[str, Any]) -> None:
        """Called when agent turn ends"""
        # Finalize streaming
        if self.renderer:
            self.renderer.finalize()
            self.renderer = None

        # Calculate duration
        if self.turn_start_time:
            duration = time.time() - self.turn_start_time
            duration_seconds = int(duration)
        else:
            duration_seconds = 0

        # Get token usage
        total_tokens = 0
        if "usage" in result:
            usage = result["usage"]
            total_tokens = usage.get("total_tokens", 0)

        # Show stats line
        symbol = self.symbols.get("✻")  # Use compacted symbol directly
        time_str = self._format_time(duration_seconds)
        token_str = self._format_tokens(total_tokens)

        stats = f"{self.colors.dim(symbol)} {time_str} · {self.tool_count} tool uses · {token_str} tokens"
        self.layout.append_content("")
        self.layout.append_content(stats)

        # Update status back to ready
        self.layout.set_status("  ⏵⏵ ready · shift+tab to cycle")

        # Reset state
        self.current_turn = None
        self.turn_start_time = None
        self.tool_count = 0

    def on_error(self, error: Exception) -> None:
        """Called when error occurs"""
        # Finalize any pending streaming
        if self.renderer:
            self.renderer.finalize()
            self.renderer = None

        # Show error
        self.layout.append_content("")
        self.layout.append_content(f"{self.colors.red('✗')} Error: {error}")

        # Update status
        self.layout.set_status("  ⏵⏵ error · ready for next message")

        # Reset state
        self.current_turn = None
        self.turn_start_time = None

    def on_thinking_start(self) -> None:
        """Called when agent starts thinking"""
        symbol = self.symbols.status("thinking")
        self.layout.append_content(f"{self.colors.yellow(symbol)} Thinking...")
        self.layout.set_status("  ⏵⏵ thinking · esc to interrupt")

    def on_thinking_end(self) -> None:
        """Called when agent finishes thinking"""
        # Thinking end is implicit when streaming starts
        pass

    def _format_time(self, seconds: int) -> str:
        """Format time duration"""
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        remaining = seconds % 60
        return f"{minutes}m {remaining}s"

    def _format_tokens(self, tokens: int) -> str:
        """Format token count"""
        if tokens < 1000:
            return str(tokens)
        elif tokens < 1_000_000:
            return f"{tokens / 1000:.1f}k"
        else:
            return f"{tokens / 1_000_000:.1f}M"


class CLIAgentHandler(AgentOutputCallback):
    """Original CLI implementation for backward compatibility"""

    def __init__(self, console: Console):
        self.console = console
        from lyra_cli.cli.output import OutputFormatter
        self.formatter = OutputFormatter(console)
        self.current_turn: str | None = None
        self.turn_start_time: float | None = None
        self.tool_count = 0

    def on_turn_start(self, turn_id: str) -> None:
        """Called when agent turn starts"""
        self.current_turn = turn_id
        self.turn_start_time = time.time()
        self.tool_count = 0
        self.formatter.status_message("Processing your message...", spinner="⏺")

    def on_tool_use(self, tool: str, args: dict[str, Any]) -> None:
        """Called when agent uses a tool"""
        self.tool_count += 1
        self.console.print(f"  ⎿ {tool}", style="dim")

    def on_stream_chunk(self, chunk: str) -> None:
        """Called for streaming text chunks"""
        self.console.print(chunk, end="", markup=False)

    def on_turn_end(self, turn_id: str, result: dict[str, Any]) -> None:
        """Called when agent turn ends"""
        self.console.print()

        if self.turn_start_time:
            duration = time.time() - self.turn_start_time
            duration_str = f"{duration:.1f}s" if duration < 60 else f"{int(duration/60)}m {int(duration%60)}s"
        else:
            duration_str = "unknown"

        if "usage" in result:
            usage = result["usage"]
            total_tokens = usage.get("total_tokens", 0)
            self.console.print(
                f"\n[dim]✻ Worked for {duration_str} · {self.tool_count} tool uses · {total_tokens:,} tokens[/dim]"
            )
        else:
            self.console.print(
                f"\n[dim]✻ Worked for {duration_str} · {self.tool_count} tool uses[/dim]"
            )

        self.current_turn = None
        self.turn_start_time = None
        self.tool_count = 0

    def on_error(self, error: Exception) -> None:
        """Called when error occurs"""
        self.formatter.error_message(f"Error: {error}")
        self.current_turn = None
        self.turn_start_time = None

    def on_thinking_start(self) -> None:
        """Called when agent starts thinking"""
        self.formatter.status_message("Thinking...", spinner="✶", style="blue")

    def on_thinking_end(self) -> None:
        """Called when agent finishes thinking"""
        pass


# Backward compatibility alias
StreamingAgentHandler = CLIAgentHandler

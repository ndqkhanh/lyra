"""CLI implementation of AgentOutputCallback"""

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from typing import Dict, Any, Optional
import time

from lyra_cli.agent.callbacks import AgentOutputCallback
from lyra_cli.cli.output import OutputFormatter


class CLIAgentHandler:
    """CLI implementation of agent output handling"""

    def __init__(self, console: Console):
        self.console = console
        self.formatter = OutputFormatter(console)
        self.live: Optional[Live] = None
        self.current_turn: Optional[str] = None
        self.turn_start_time: Optional[float] = None
        self.tool_count = 0

    def on_turn_start(self, turn_id: str) -> None:
        """Called when agent turn starts"""
        self.current_turn = turn_id
        self.turn_start_time = time.time()
        self.tool_count = 0
        self.formatter.status_message("Processing your message...", spinner="⏺")

    def on_tool_use(self, tool: str, args: Dict[str, Any]) -> None:
        """Called when agent uses a tool"""
        self.tool_count += 1
        # Show tool use in dim style
        self.console.print(f"  ⎿ {tool}", style="dim")

    def on_stream_chunk(self, chunk: str) -> None:
        """Called for streaming text chunks"""
        # Stream output character by character
        self.console.print(chunk, end="", markup=False)

    def on_turn_end(self, turn_id: str, result: Dict[str, Any]) -> None:
        """Called when agent turn ends"""
        self.console.print()  # New line after streaming

        # Calculate duration
        if self.turn_start_time:
            duration = time.time() - self.turn_start_time
            duration_str = f"{duration:.1f}s" if duration < 60 else f"{int(duration/60)}m {int(duration%60)}s"
        else:
            duration_str = "unknown"

        # Show token usage if available
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
        pass  # Thinking end is implicit when streaming starts

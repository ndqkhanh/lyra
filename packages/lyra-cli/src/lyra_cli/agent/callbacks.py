"""Callback protocol for agent output handling"""

from typing import Protocol, Dict, Any, Optional


class AgentOutputCallback(Protocol):
    """Protocol for handling agent output in CLI"""

    def on_turn_start(self, turn_id: str) -> None:
        """Called when agent turn starts

        Args:
            turn_id: Unique identifier for this turn
        """
        ...

    def on_tool_use(self, tool: str, args: Dict[str, Any]) -> None:
        """Called when agent uses a tool

        Args:
            tool: Name of the tool being used
            args: Arguments passed to the tool
        """
        ...

    def on_stream_chunk(self, chunk: str) -> None:
        """Called for streaming text chunks

        Args:
            chunk: Text chunk from agent response
        """
        ...

    def on_turn_end(self, turn_id: str, result: Dict[str, Any]) -> None:
        """Called when agent turn ends

        Args:
            turn_id: Unique identifier for this turn
            result: Turn result including usage stats
        """
        ...

    def on_error(self, error: Exception) -> None:
        """Called when error occurs

        Args:
            error: Exception that occurred
        """
        ...

    def on_thinking_start(self) -> None:
        """Called when agent starts thinking"""
        ...

    def on_thinking_end(self) -> None:
        """Called when agent finishes thinking"""
        ...

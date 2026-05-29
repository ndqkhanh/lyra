#!/usr/bin/env python3
"""Lyra REPL with Claude Code-style UI - Complete Integration"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

from lyra_cli.events import EventDispatcher, StreamingRenderer
from lyra_cli.ui import (
    AgentTree,
    FixedInputBox,
    ResponseFormatter,
    ScrollManager,
    StatusLine,
    print_welcome_banner,
)


class LyraREPL:
    """Lyra REPL with Claude Code-style UI"""

    def __init__(self):
        # Initialize components
        self.dispatcher = EventDispatcher()
        self.streaming = StreamingRenderer()
        self.input_box = FixedInputBox()
        self.status_line = StatusLine()
        self.formatter = ResponseFormatter()
        self.agent_tree = AgentTree()
        self.scroll = ScrollManager(fixed_height=4)

        # Setup event handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup event handlers"""
        self.dispatcher.on("text.delta", self._on_text_delta)
        self.dispatcher.on("tool.started", self._on_tool_started)
        self.dispatcher.on("turn.finished", self._on_turn_finished)

    def _on_text_delta(self, event):
        """Handle text delta - streaming response"""
        self.streaming.append_delta(event.text)

    def _on_tool_started(self, event):
        """Handle tool started"""
        tool_line = self.formatter.format_tool_call(
            event.name,
            f"{event.input}"
        )
        self.streaming.finalize_line()
        self.streaming.append_line(tool_line)

    def _on_turn_finished(self, event):
        """Handle turn finished"""
        self.streaming.finalize_line()
        stats_line = self.formatter.format_stats_line(
            duration_s=2.5,
            tool_count=3,
            tokens=event.tokens_in + event.tokens_out
        )
        self.streaming.append_line(stats_line)

    def show_welcome(self):
        """Show welcome banner"""
        print_welcome_banner(
            version="0.1.0",
            model="Opus 4.7",
            effort="high",
            provider="Anthropic API",
            user_name="Khanh"
        )

    def render_fixed_ui(self, prompt_text=""):
        """Render fixed UI at bottom"""
        self.input_box.render(prompt_text)
        self.status_line.update("default", ["esc to exit", "enter to send"])

    def simulate_streaming_response(self):
        """Simulate a streaming response to demonstrate UI"""
        # Show active response
        active_line = self.formatter.format_active_response("Analyzing your request...")
        print(active_line)
        print()

        # Render fixed UI
        self.render_fixed_ui("What is Python?")

        # Simulate streaming with delays
        response_parts = [
            "Python is a high-level, interpreted programming language. ",
            "It was created by Guido van Rossum and first released in 1991. ",
            "\n\nPython emphasizes code readability with significant whitespace. ",
            "It supports multiple programming paradigms including:\n",
            "- Object-oriented programming\n",
            "- Functional programming\n",
            "- Procedural programming\n",
            "\n",
            "Python is widely used for:\n",
            "- Web development\n",
            "- Data science\n",
            "- Machine learning\n",
            "- Automation\n"
        ]

        for part in response_parts:
            print(part, end="", flush=True)
            time.sleep(0.1)
            # Re-render fixed UI to keep it at bottom
            self.render_fixed_ui("What is Python?")

        print()
        print()

        # Show stats line
        stats = self.formatter.format_stats_line(2.5, 0, 150)
        print(stats)
        print()

        # Re-render fixed UI one final time
        self.render_fixed_ui()

    def run_demo(self):
        """Run demo showing UI patterns"""
        # Clear screen
        print("\033[2J\033[H")

        # Show welcome
        self.show_welcome()

        # Demo 1: Simple streaming
        print("=" * 80)
        print("DEMO 1: Streaming Response with Fixed UI")
        print("=" * 80)
        print()

        self.simulate_streaming_response()

        time.sleep(2)

        # Demo 2: Tool calls
        print("\n")
        print("=" * 80)
        print("DEMO 2: Tool Calls with Fixed UI")
        print("=" * 80)
        print()

        active = self.formatter.format_active_response("Reading files...")
        print(active)
        print()

        tool1 = self.formatter.format_tool_call("Read", "file.py (228 lines)")
        print(tool1)

        tool2 = self.formatter.format_tool_call("Edit", "src/main.py")
        print(tool2)

        print()
        print("Files analyzed successfully!")
        print()

        stats = self.formatter.format_stats_line(1.5, 2, 500)
        print(stats)
        print()

        # Render fixed UI
        self.render_fixed_ui()

        time.sleep(2)

        # Demo 3: Agent tree
        print("\n")
        print("=" * 80)
        print("DEMO 3: Agent Tree with Fixed UI")
        print("=" * 80)
        print()

        # Add agents
        self.agent_tree.add_agent("agent-1", "Research GitHub repos")
        self.agent_tree.add_agent("agent-2", "Search academic papers")
        self.agent_tree.update_agent("agent-1", tool_count=10, tokens=29700, latest_tool="Bash: gh api")
        self.agent_tree.update_agent("agent-2", tool_count=6, tokens=29900, latest_tool="Web Search: arxiv")

        # Show collapsed
        print(self.agent_tree.render())
        print()

        # Expand
        self.agent_tree.toggle_expand()
        print(self.agent_tree.render())
        print()

        stats = self.formatter.format_stats_line(15.5, 16, 59600)
        print(stats)
        print()

        # Render fixed UI
        self.render_fixed_ui()

        print("\n")
        print("=" * 80)
        print("✓ Demo Complete!")
        print("=" * 80)
        print()
        print("Key features demonstrated:")
        print("  ✓ Fixed input box at bottom (never scrolls away)")
        print("  ✓ Status line below input (always visible)")
        print("  ✓ Streaming content above fixed UI")
        print("  ✓ Tool call display")
        print("  ✓ Agent tree display")
        print("  ✓ Stats line")
        print()


if __name__ == "__main__":
    repl = LyraREPL()
    repl.run_demo()

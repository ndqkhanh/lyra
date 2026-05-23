"""Sequential output REPL - Claude Code style with fixed bottom UI"""

import os
import sys
import time
from typing import Optional, List
from dataclasses import dataclass

from ..events import (
    EventDispatcher,
    StreamingRenderer,
    TurnStarted,
    TextDelta,
    ToolStarted,
    ToolFinished,
    TurnFinished,
)
from ..ui import (
    FixedInputBox,
    StatusLine,
    ResponseFormatter,
    AgentTree,
    print_welcome_banner,
)


@dataclass
class REPLConfig:
    """Configuration for Sequential REPL"""
    context_budget: int = 200000
    permission_mode: str = "ask"  # ask, bypass, deny
    show_context: bool = True
    show_permission_mode: bool = True


class SequentialREPL:
    """REPL with sequential output and fixed bottom UI

    Key features:
    - Content prints line by line (grows downward)
    - Bottom UI (4 lines) re-renders after each line
    - Bottom UI always stays at terminal bottom
    - Context percentage tracking
    - Permission mode display and cycling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-opus-4-20250514",
        config: Optional[REPLConfig] = None
    ):
        # Configuration
        self.config = config or REPLConfig()

        # API client (optional for now)
        self.api_key = api_key
        self.model = model

        # Components
        self.dispatcher = EventDispatcher()
        self.streaming = StreamingRenderer()
        self.input_box = FixedInputBox()
        self.status_line = StatusLine()
        self.formatter = ResponseFormatter()
        self.agent_tree = AgentTree()

        # State
        self.terminal_height = self._get_terminal_height()
        self.terminal_width = self._get_terminal_width()
        self.bottom_ui_height = 4  # divider + input + divider + status

        # Context tracking
        self.context_budget = self.config.context_budget
        self.context_used = 0
        self.permission_mode = self.config.permission_mode

        # Current state
        self.current_mode = "default"
        self.current_hints = ["esc to exit", "enter to send"]
        self.running = True

        # Setup event handlers
        self._setup_event_handlers()

    def _get_terminal_height(self) -> int:
        """Get terminal height"""
        try:
            return os.get_terminal_size().lines
        except OSError:
            return 24  # Default fallback

    def _get_terminal_width(self) -> int:
        """Get terminal width"""
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80  # Default fallback

    def _setup_event_handlers(self):
        """Setup event handlers"""
        self.dispatcher.on("text.delta", self._on_text_delta)
        self.dispatcher.on("tool.started", self._on_tool_started)
        self.dispatcher.on("tool.finished", self._on_tool_finished)
        self.dispatcher.on("turn.finished", self._on_turn_finished)

    def _on_text_delta(self, event):
        """Handle streaming text"""
        # Print text (grows downward)
        print(event.text, end="", flush=True)

        # Update context
        # Note: In real implementation, count tokens properly
        # For now, rough estimate: 1 token ≈ 4 chars
        estimated_tokens = len(event.text) // 4
        self.context_used += estimated_tokens

    def _on_tool_started(self, event):
        """Handle tool started"""
        # Print tool call line
        tool_line = self.formatter.format_tool_call(event.name, str(event.input))
        print(f"\n{tool_line}")

    def _on_tool_finished(self, event):
        """Handle tool finished"""
        if event.status != "ok":
            error_line = self.formatter.format_error(f"Tool failed: {event.status}")
            print(f"\n{error_line}")

    def _on_turn_finished(self, event):
        """Handle turn finished"""
        # Print stats line
        duration = getattr(event, 'duration_s', 0.0)
        stats_line = self.formatter.format_stats_line(
            duration_s=duration,
            tool_count=0,
            tokens=event.tokens_in + event.tokens_out
        )
        print(f"\n\n{stats_line}\n")

        # Update context usage
        total_tokens = event.tokens_in + event.tokens_out
        self.context_used += total_tokens

    def _render_bottom_ui_inline(self):
        """Render bottom UI inline (not fixed at terminal bottom)"""
        # Calculate context percentage
        context_percentage = self._get_context_percentage()

        # Build status parts
        parts = []

        # Add context percentage if enabled
        if self.config.show_context and context_percentage > 0:
            ctx_text = f"{context_percentage}% context"
            # Color code
            if context_percentage < 50:
                ctx_text = f"\033[32m{ctx_text}\033[0m"  # Green
            elif context_percentage < 80:
                ctx_text = f"\033[33m{ctx_text}\033[0m"  # Yellow
            else:
                ctx_text = f"\033[31m{ctx_text}\033[0m"  # Red
            parts.append(ctx_text)

        # Add permission mode if enabled
        if self.config.show_permission_mode:
            mode_text = f"{self.permission_mode} permissions"
            # Color code
            if self.permission_mode == "bypass":
                mode_text = f"\033[33m{mode_text}\033[0m"  # Yellow
            elif self.permission_mode == "ask":
                mode_text = f"\033[32m{mode_text}\033[0m"  # Green
            elif self.permission_mode == "deny":
                mode_text = f"\033[31m{mode_text}\033[0m"  # Red
            parts.append(mode_text)

        # Add hints
        parts.extend(self.current_hints)

        # Build status line
        status_text = f"  ⏵⏵ {self.current_mode}"
        if parts:
            status_text += " · " + " · ".join(parts)

        # Print top divider
        print("─" * self.terminal_width)

    def _get_context_percentage(self) -> int:
        """Get current context usage percentage"""
        if self.context_budget == 0:
            return 0
        return min(100, int((self.context_used / self.context_budget) * 100))

    def update_context(self, tokens_used: int):
        """Update context usage

        Args:
            tokens_used: Number of tokens used in this turn
        """
        self.context_used += tokens_used
        self._update_status_line()

    def set_permission_mode(self, mode: str):
        """Set permission mode

        Args:
            mode: Permission mode (ask, bypass, deny)
        """
        if mode not in ["ask", "bypass", "deny"]:
            raise ValueError(f"Invalid permission mode: {mode}")

        self.permission_mode = mode
        self._update_status_line()

        # Show notification
        print(f"\n  Permission mode: {self.permission_mode}")

    def cycle_permission_mode(self):
        """Cycle through permission modes"""
        modes = ["ask", "bypass", "deny"]
        current_index = modes.index(self.permission_mode)
        next_index = (current_index + 1) % len(modes)

        self.set_permission_mode(modes[next_index])

    def show_welcome(self):
        """Show welcome banner once at startup"""
        print_welcome_banner(
            version="0.1.0",
            model="Opus 4.7",
            effort="high",
            provider="Anthropic API",
            user_name=os.getenv("USER", "User")
        )
        print()  # Blank line after welcome

    def get_user_input(self) -> Optional[str]:
        """Get user input"""
        try:
            # Input is between two divider lines
            user_input = input("❯ ")

            # Print bottom divider after input
            print("─" * self.terminal_width)

            # Print status line below bottom divider
            context_percentage = self._get_context_percentage()
            parts = []

            if self.config.show_context and context_percentage > 0:
                ctx_text = f"{context_percentage}% context"
                if context_percentage < 50:
                    ctx_text = f"\033[32m{ctx_text}\033[0m"
                elif context_percentage < 80:
                    ctx_text = f"\033[33m{ctx_text}\033[0m"
                else:
                    ctx_text = f"\033[31m{ctx_text}\033[0m"
                parts.append(ctx_text)

            if self.config.show_permission_mode:
                mode_text = f"{self.permission_mode} permissions"
                if self.permission_mode == "bypass":
                    mode_text = f"\033[33m{mode_text}\033[0m"
                elif self.permission_mode == "ask":
                    mode_text = f"\033[32m{mode_text}\033[0m"
                elif self.permission_mode == "deny":
                    mode_text = f"\033[31m{mode_text}\033[0m"
                parts.append(mode_text)

            parts.extend(self.current_hints)

            status_text = f"  ⏵⏵ {self.current_mode}"
            if parts:
                status_text += " · " + " · ".join(parts)

            print(status_text)
            print()  # Blank line after status

            if not user_input:
                return None

            # Handle commands
            if user_input.startswith("/"):
                return self._handle_command(user_input)

            return user_input

        except (KeyboardInterrupt, EOFError):
            self.running = False
            return None

    def _handle_command(self, command: str) -> Optional[str]:
        """Handle slash commands"""
        cmd = command.lower().strip()

        if cmd in ["/exit", "/quit"]:
            self.running = False
            return None
        elif cmd == "/clear":
            print("\033[2J\033[H")  # Clear screen
            self.show_welcome()
            return None
        elif cmd == "/help":
            self._show_help()
            return None
        elif cmd == "/mode":
            self.cycle_permission_mode()
            return None
        elif cmd == "/context":
            self._show_context_info()
            return None
        else:
            print(self.formatter.format_warning(f"Unknown command: {command}"))
            return None

    def _show_help(self):
        """Show help message"""
        print()
        print("Available commands:")
        print("  /help     - Show this help message")
        print("  /clear    - Clear screen")
        print("  /mode     - Cycle permission mode (ask/bypass/deny)")
        print("  /context  - Show context usage")
        print("  /exit     - Exit Lyra")
        print()

    def _show_context_info(self):
        """Show context usage information"""
        percentage = self._get_context_percentage()
        print()
        print(f"Context usage: {self.context_used:,} / {self.context_budget:,} tokens ({percentage}%)")
        print()

    def process_message(self, user_message: str):
        """Process user message with Anthropic API"""
        import anthropic

        # Check if API key is available
        if not self.api_key:
            print("\n\x1b[31m✘ Error: No API key provided\x1b[0m")
            print("Set ANTHROPIC_API_KEY environment variable")
            return

        # Emit turn started
        self.dispatcher.emit(TurnStarted(
            turn_id="turn-1",
            user_text=user_message
        ))

        # Show active response
        active_line = self.formatter.format_active_response("Thinking...")
        print(f"\n{active_line}\n")

        try:
            # Create Anthropic client
            client = anthropic.Anthropic(api_key=self.api_key)

            # Stream response from Claude
            assistant_message = ""
            start_time = time.time()

            with client.messages.stream(
                model=self.model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": user_message
                }],
            ) as stream:
                for text in stream.text_stream:
                    assistant_message += text
                    # Emit text delta event
                    self.dispatcher.emit(TextDelta(
                        turn_id="turn-1",
                        text=text
                    ))

            # Get usage stats
            final_message = stream.get_final_message()
            usage = final_message.usage

            # Calculate duration
            duration = time.time() - start_time

            # Create turn finished event with duration
            turn_finished = TurnFinished(
                turn_id="turn-1",
                tokens_in=usage.input_tokens,
                tokens_out=usage.output_tokens,
                stop_reason=final_message.stop_reason or "end_turn"
            )
            # Add duration as attribute
            turn_finished.duration_s = duration

            # Emit turn finished event
            self.dispatcher.emit(turn_finished)

        except Exception as e:
            error_line = self.formatter.format_error(f"Error: {str(e)}")
            print(f"\n{error_line}\n")

    def run(self):
        """Main REPL loop"""
        # Clear screen and show welcome
        print("\033[2J\033[H")
        self.show_welcome()

        # Main loop
        while self.running:
            # Render bottom UI inline (before input)
            self._render_bottom_ui_inline()

            # Get user input
            user_input = self.get_user_input()

            if user_input is None:
                continue

            # Process message (streaming output will push bottom UI down)
            self.process_message(user_input)

        # Cleanup
        print()
        print("Goodbye! 👋")
        print()


def main():
    """Main entry point for testing"""
    # Create and run REPL in demo mode
    repl = SequentialREPL()
    repl.run()


if __name__ == "__main__":
    main()

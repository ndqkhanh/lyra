"""Integrated REPL with Claude Code-style UI"""

import sys

import anthropic

from lyra_cli.events import (
    EventDispatcher,
    StreamingRenderer,
    TextDelta,
    TurnFinished,
    TurnStarted,
)
from lyra_cli.ui import (
    AgentTree,
    ResponseFormatter,
    print_welcome_banner,
)


class IntegratedREPL:
    """Lyra REPL with full Claude Code-style UI integration"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-opus-4-20250514",
        max_tokens: int = 4096
    ):
        # Anthropic client
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

        # Conversation history
        self.messages = []

        # UI Components
        self.dispatcher = EventDispatcher()
        self.streaming = StreamingRenderer()
        self.formatter = ResponseFormatter()
        self.agent_tree = AgentTree()

        # Setup event handlers
        self._setup_handlers()

        # State
        self.running = True

    def _setup_handlers(self):
        """Setup event handlers"""
        self.dispatcher.on("text.delta", self._on_text_delta)
        self.dispatcher.on("tool.started", self._on_tool_started)
        self.dispatcher.on("tool.finished", self._on_tool_finished)
        self.dispatcher.on("turn.finished", self._on_turn_finished)

    def _on_text_delta(self, event):
        """Handle text delta - streaming response"""
        print(event.text, end="", flush=True)
        self.streaming.append_delta(event.text)

    def _on_tool_started(self, event):
        """Handle tool started"""
        tool_line = self.formatter.format_tool_call(
            event.name,
            str(event.input)
        )
        print()
        print(tool_line)
        self.streaming.finalize_line()
        self.streaming.append_line(tool_line)

    def _on_tool_finished(self, event):
        """Handle tool finished"""
        if event.status == "ok":
            # Tool completed successfully
            pass
        else:
            error_line = self.formatter.format_error(f"Tool failed: {event.status}")
            print(error_line)

    def _on_turn_finished(self, event):
        """Handle turn finished"""
        self.streaming.finalize_line()
        print()
        print()

        # Show stats with actual timing
        duration = getattr(event, 'duration_s', 0.0)
        stats_line = self.formatter.format_stats_line(
            duration_s=duration,
            tool_count=0,
            tokens=event.tokens_in + event.tokens_out
        )
        print(stats_line)
        print()

    def show_welcome(self):
        """Show welcome banner"""
        print_welcome_banner(
            version="0.1.0",
            model=self.model.split("-")[1].title() if "-" in self.model else self.model,
            effort="high",
            provider="Anthropic API",
            user_name=None
        )

    def get_user_input(self) -> str | None:
        """Get user input - inline with conversation"""
        try:
            # Simple inline input prompt
            user_input = input(self.formatter.format_prompt() + " ")

            if not user_input:
                return None

            # Handle commands
            if user_input.startswith("/"):
                return self._handle_command(user_input)

            return user_input

        except (KeyboardInterrupt, EOFError):
            self.running = False
            return None

    def _handle_command(self, command: str) -> str | None:
        """Handle slash commands"""
        cmd = command.lower().strip()

        if cmd == "/exit" or cmd == "/quit":
            self.running = False
            return None
        elif cmd == "/clear":
            print("\033[2J\033[H")  # Clear screen
            self.show_welcome()
            return None
        elif cmd == "/help":
            self._show_help()
            return None
        else:
            print(self.formatter.format_warning(f"Unknown command: {command}"))
            return None

    def _show_help(self):
        """Show help message"""
        print()
        print("Available commands:")
        print("  /help   - Show this help message")
        print("  /clear  - Clear screen")
        print("  /exit   - Exit Lyra")
        print()

    def send_message(self, user_message: str):
        """Send message to Claude and stream response"""
        import time
        start_time = time.time()

        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_message
        })

        # Show active response indicator
        active_line = self.formatter.format_active_response("Thinking...")
        print(active_line)
        print()

        # Emit turn started event
        self.dispatcher.emit(TurnStarted(
            turn_id="turn-1",
            user_text=user_message
        ))

        try:
            # Stream response from Claude
            assistant_message = ""

            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=self.messages,
            ) as stream:
                for text in stream.text_stream:
                    assistant_message += text
                    # Emit text delta event
                    self.dispatcher.emit(TextDelta(
                        turn_id="turn-1",
                        text=text
                    ))

            # Add assistant message to history
            self.messages.append({
                "role": "assistant",
                "content": assistant_message
            })

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
            print()
            print(error_line)
            print()

    def run(self):
        """Run the REPL"""
        # Clear screen and show welcome
        print("\033[2J\033[H")
        self.show_welcome()

        # Main loop
        while self.running:
            # Get user input
            user_input = self.get_user_input()

            if user_input is None:
                continue

            # Send message and get response
            self.send_message(user_input)

        # Cleanup
        print()
        print("Goodbye! 👋")
        print()


def main():
    """Main entry point"""
    import os

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    # Create and run REPL
    repl = IntegratedREPL(api_key=api_key)
    repl.run()


if __name__ == "__main__":
    main()

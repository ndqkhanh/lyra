"""
Lyra Chat with Fixed Bottom Layout - Claude Code Style

This module integrates the FixedBottomLayout into Lyra's interactive chat,
providing the exact Claude Code UI experience with fixed input/status at bottom.
"""

from rich.console import Console
from lyra_cli.ui.fixed_layout import FixedBottomLayout, StreamingRenderer
from lyra_cli.ui.renderer import LyraUIRenderer
from lyra_cli.ui.symbols import SymbolRegistry
from lyra_cli.ui.colors import ColorEngine
import sys


class FixedBottomChatUI:
    """
    Chat UI with fixed bottom layout (Claude Code pattern)

    Features:
    - Input box fixed at row (height-2)
    - Status line fixed at row (height)
    - Content streams in scrollable area above
    - Terminal resize handling
    - Streaming response support
    """

    def __init__(self, model: str = "opus"):
        self.layout = FixedBottomLayout()
        self.layout.use_alt_screen = True
        self.renderer = LyraUIRenderer()
        self.symbols = SymbolRegistry()
        self.colors = ColorEngine()
        self.model = model
        self.message_count = 0

    def start(self):
        """Start the chat UI"""
        self.layout.enter_alt_screen()

        # Show welcome banner
        self._show_welcome()

        # Set initial status
        self._update_status("ready")

    def stop(self):
        """Stop the chat UI"""
        self.layout.exit_alt_screen()

    def _show_welcome(self):
        """Show welcome banner"""
        welcome = f"""
╭─────────────────────────────── Lyra v0.1.0 ───────────────────────────────╮
│                                                                            │
│  Welcome back!                                                             │
│                                                                            │
│      ╦  ╦ ╦ ╦═╗ ╔═╗                                                       │
│      ║  ╚╦╝ ╠╦╝ ╠═╣                                                       │
│      ╩═╝ ╩  ╩╚═ ╩ ╩                                                       │
│                                                                            │
│  {self.model.capitalize()} · Claude Code Style UI                                        │
│                                                                            │
╰────────────────────────────────────────────────────────────────────────────╯
"""
        self.layout.append_content(welcome)

    def _update_status(self, mode: str, hints: list[str] = None):
        """Update status line"""
        if hints is None:
            hints = ["shift+tab to cycle"]

        status_parts = [f"  {self.symbols.get('⏵')}{self.symbols.get('⏵')} {mode}"]
        if hints:
            status_parts.append(" · ".join(hints))

        status = " · ".join(status_parts)
        self.layout.set_status(status)

    def show_user_message(self, text: str):
        """Display user message"""
        self.layout.append_content("")
        self.layout.append_content(f"{self.symbols.get('❯')} {text}")
        self.layout.append_content("")
        self.message_count += 1

    def stream_assistant_response(self, response_generator):
        """
        Stream assistant response with fixed bottom UI

        Args:
            response_generator: Generator yielding response chunks
        """
        # Show thinking indicator
        symbol = self.symbols.status("running")
        self.layout.append_content(f"{self.colors.yellow(symbol)} Analyzing your request...")

        # Update status to show working
        self._update_status("working", ["esc to interrupt"])

        # Create streaming renderer
        renderer = StreamingRenderer(self.layout)

        # Stream response
        try:
            for chunk in response_generator:
                renderer.append_delta(chunk)

            renderer.finalize()

        except KeyboardInterrupt:
            renderer.finalize()
            self.layout.append_content("")
            self.layout.append_content(f"{self.colors.yellow('⚠')} Interrupted by user")

        # Update status back to ready
        self._update_status("ready", [f"{self.message_count} messages"])

    def show_tool_call(self, tool_name: str, description: str = ""):
        """Show tool call indicator"""
        connector = self.symbols.get("⎿")
        if description:
            line = f"  {self.colors.dim(connector)}  {tool_name}: {description}"
        else:
            line = f"  {self.colors.dim(connector)}  {tool_name}"
        self.layout.append_content(line)

    def show_stats(self, duration_seconds: int, tool_count: int, tokens: int):
        """Show completion stats"""
        symbol = self.symbols.status("compacted")
        time_str = self._format_time(duration_seconds)
        token_str = self._format_tokens(tokens)

        stats = f"{self.colors.dim(symbol)} {time_str} · {tool_count} tools · {token_str} tokens"
        self.layout.append_content("")
        self.layout.append_content(stats)

    def show_error(self, message: str):
        """Show error message"""
        self.layout.append_content("")
        self.layout.append_content(f"{self.colors.red('✗')} Error: {message}")

    def show_info(self, message: str):
        """Show info message"""
        self.layout.append_content(f"{self.colors.cyan('ℹ')} {message}")

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


def interactive_chat_with_fixed_layout(model: str = "opus"):
    """
    Interactive chat with fixed bottom layout

    This is a drop-in replacement for the current interactive_chat function
    that uses the Claude Code-style fixed bottom UI.
    """
    ui = FixedBottomChatUI(model=model)
    ui.start()

    try:
        # Initialize agent loop
        from lyra_cli.cli.agent_handler import CLIAgentHandler
        from lyra_cli.agent import AgentLoopFactory

        model_map = {
            "opus": "claude-opus-4-20250514",
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-haiku-4-20250514"
        }
        api_model = model_map.get(model.lower(), "claude-opus-4-20250514")

        # Create agent handler that uses our UI
        class FixedLayoutAgentHandler:
            def __init__(self, ui: FixedBottomChatUI):
                self.ui = ui

            def on_tool_call(self, tool_name: str, description: str = ""):
                self.ui.show_tool_call(tool_name, description)

            def on_response_chunk(self, chunk: str):
                # Handled by stream_assistant_response
                pass

            def on_error(self, error: str):
                self.ui.show_error(error)

        handler = FixedLayoutAgentHandler(ui)
        agent_loop = AgentLoopFactory.create_simple_loop(
            callback=handler,
            model=api_model
        )

    except ValueError:
        ui.show_error("API key not configured")
        ui.show_info("Run 'lyra onboard' to set up, or set ANTHROPIC_API_KEY")
        agent_loop = None

    # Main chat loop
    while True:
        try:
            # Get user input (this would need to be integrated with prompt_toolkit)
            # For now, using simple input
            user_input = input()  # This will be replaced with proper input handling

            if not user_input.strip():
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                if user_input.lower() in ["/exit", "/quit", "/q"]:
                    break
                # Handle other commands...
                continue

            # Show user message
            ui.show_user_message(user_input)

            # Stream response
            if agent_loop:
                # This is a simplified example - actual implementation would
                # integrate with the agent loop's streaming response
                def response_generator():
                    # Simulate streaming response
                    response = agent_loop.process_message(user_input)
                    for chunk in response:
                        yield chunk

                ui.stream_assistant_response(response_generator())
                ui.show_stats(duration_seconds=5, tool_count=2, tokens=1234)
            else:
                ui.show_info("Demo mode - run 'lyra onboard' to enable agent")

        except KeyboardInterrupt:
            ui.show_info("Interrupted - type /exit to quit")
        except EOFError:
            break

    ui.stop()


# Integration example for existing chat.py
def integrate_into_existing_chat():
    """
    Example of how to integrate FixedBottomChatUI into existing chat.py

    Replace the current interactive_chat function with:
    """
    example_code = '''
def interactive_chat(model: str = "opus"):
    """Interactive chat loop with fixed bottom UI"""
    from lyra_cli.cli.chat_fixed_layout import FixedBottomChatUI

    ui = FixedBottomChatUI(model=model)
    ui.start()

    try:
        # Initialize agent loop
        agent_handler = CLIAgentHandler(ui)  # Pass ui instead of console
        agent_loop = AgentLoopFactory.create_simple_loop(
            callback=agent_handler,
            model=api_model
        )

        while True:
            # Get user input
            user_input = prompt.get_input()

            # Show user message
            ui.show_user_message(user_input)

            # Stream response
            ui.stream_assistant_response(agent_loop.process_message(user_input))

    finally:
        ui.stop()
'''
    return example_code


if __name__ == "__main__":
    # Demo mode
    print("Starting Lyra with fixed bottom layout...")
    print("This is a demo - press Ctrl+C to exit")
    print()

    ui = FixedBottomChatUI(model="opus")
    ui.start()

    try:
        # Simulate a conversation
        import time

        ui.show_user_message("Hello! Can you verify the UI is working correctly?")

        def demo_response():
            response = """Yes! The UI is working perfectly. Here's what I can verify:

✅ **Fixed Bottom Layout** - The input box and status line stay at the bottom
✅ **Streaming Response** - This text is streaming into the scrollable area
✅ **Symbol System** - All Unicode symbols are rendering correctly
✅ **Color Scheme** - Semantic colors are applied properly

The key feature is that as this response streams in, the input box (❯) and
status line (⏵⏵) remain fixed at rows (height-2) and (height) respectively.

This is exactly how Claude Code works!"""

            for char in response:
                yield char
                time.sleep(0.01)

        ui.stream_assistant_response(demo_response())
        ui.show_stats(duration_seconds=3, tool_count=0, tokens=150)

        print("\n\nDemo complete! Press Enter to exit...")
        input()

    finally:
        ui.stop()

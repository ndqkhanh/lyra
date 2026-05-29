"""Streaming REPL for Lyra - Claude Code style.

Provides an interactive command-line interface with:
- Real-time streaming output
- Multi-line input support
- Session persistence
- Slash command handling
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path

from lyra_cli import __version__

from .formatter import CLIFormatter, get_formatter
from .messages import StreamEvent


# Simple REPL class for backward compatibility
class LyraREPL:
    """Simple REPL loop without fixed bottom layout"""

    def __init__(self, model: str, on_message: Callable[[str], None]):
        self.model = model
        self.on_message = on_message

    def run(self):
        """Main REPL loop"""
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.completion import WordCompleter
            from prompt_toolkit.history import InMemoryHistory
        except ImportError:
            print("Error: prompt_toolkit not installed. Install with: pip install prompt_toolkit")
            return

        history = InMemoryHistory()
        completer = WordCompleter(
            ['/exit', '/quit', '/model', '/clear', '/help'],
            ignore_case=True
        )

        session = PromptSession(
            completer=completer,
            history=history,
            multiline=False
        )

        while True:
            try:
                user_input = session.prompt('❯ ')

                if not user_input.strip():
                    continue

                # Handle slash commands
                if user_input.startswith('/'):
                    if user_input.lower().strip() in ['/exit', '/quit', '/q']:
                        break
                    elif user_input.lower().strip() == '/clear':
                        print('\x1b[2J\x1b[H', end='', flush=True)
                        continue
                    elif user_input.lower().strip() == '/help':
                        print("\n\x1b[36mAvailable Commands:\x1b[0m")
                        print("  /exit, /quit    Exit Lyra")
                        print("  /clear          Clear screen")
                        print("  /model          Switch model")
                        print("  /help           Show this help\n")
                        continue

                # Send to message handler
                self.on_message(user_input)

            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\x1b[31m✘ Error: {e}\x1b[0m")
                import os
                if os.getenv("DEBUG"):
                    import traceback
                    traceback.print_exc()


async def launch_streaming_repl(
    repo_root: Path,
    model: str,
    budget_cap_usd: float | None = None,
    resume_id: str | None = None,
    pin_session_id: str | None = None,
    bare: bool = False,  # noqa: ARG001
) -> int:
    """Launch Claude Code-style streaming REPL.

    Args:
        repo_root: Repository root directory
        model: LLM model to use
        budget_cap_usd: Optional budget cap in USD
        resume_id: Optional session ID to resume
        pin_session_id: Optional session ID to pin
        bare: Skip auto-discovery and hooks

    Returns:
        Exit code (0 for success)
    """
    formatter = get_formatter()

    # TODO: Load or create session
    session_id = pin_session_id or resume_id or "new-session"

    # Print welcome banner
    formatter.print_welcome(
        version=__version__,
        model=model,
        repo=repo_root.name,
        session_id=session_id,
    )

    # Main REPL loop
    while True:
        try:
            # Read user input
            prompt = await read_prompt(formatter)

            if not prompt:
                continue

            # Handle slash commands
            if prompt.startswith("/"):
                await handle_slash_command(prompt, formatter)
                continue

            # Execute agent turn with streaming
            async for event in run_agent_turn(
                prompt=prompt,
                model=model,
                budget_cap=budget_cap_usd,
            ):
                await handle_stream_event(event, formatter)

            # Print newline after turn (no error)
            if hasattr(formatter, 'console') and formatter.use_rich:
                formatter.console.print()
            else:
                formatter.print()

        except KeyboardInterrupt:
            formatter.print("\n^C")
            continue
        except EOFError:
            formatter.print("\nBye!")
            break
        except Exception as exc:
            formatter.print_error(str(exc))
            continue

    return 0


async def read_prompt(formatter: CLIFormatter) -> str:
    """Read user input with rich prompt_toolkit features.

    Returns:
        User input string
    """
    try:
        from pathlib import Path

        from .input import create_prompt_session

        # Get history file path
        history_dir = Path.home() / ".lyra"
        history_dir.mkdir(exist_ok=True)
        history_file = history_dir / "history.txt"

        # Create session (cached globally in production)
        if not hasattr(read_prompt, "_session"):
            read_prompt._session = create_prompt_session(history_file)

        # Show prompt with Rich styling
        if hasattr(formatter, "console") and formatter.use_rich:
            prompt_text = "\n> "
        else:
            prompt_text = "\n> "

        # Get input with all features
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None, read_prompt._session.prompt, prompt_text
        )
        return text.strip()

    except ImportError:
        # Fallback to simple input if prompt_toolkit not available
        formatter.print("\n> ", end="", flush=True)
        loop = asyncio.get_event_loop()
        prompt = await loop.run_in_executor(None, sys.stdin.readline)
        return prompt.strip()
    except EOFError:
        raise


async def handle_slash_command(command: str, formatter: CLIFormatter) -> None:
    """Handle slash commands.

    Args:
        command: Slash command string (e.g., "/help", "/status")
        formatter: Output formatter
    """
    cmd = command.split()[0].lower()

    if cmd == "/help":
        formatter.print_markdown(
            """
# Available Commands

- `/help` - Show this help message
- `/status` - Show session status
- `/model [name]` - Switch model or show current model
- `/budget [amount]` - Set budget cap or show current budget
- `/clear` - Clear conversation history
- `/exit` or `/quit` - Exit the REPL

Type any message to chat with Lyra.
"""
        )
    elif cmd == "/status":
        formatter.print_info("Status command not yet implemented")
    elif cmd == "/model":
        formatter.print_info("Model command not yet implemented")
    elif cmd == "/budget":
        formatter.print_info("Budget command not yet implemented")
    elif cmd == "/clear":
        formatter.print_info("Clear command not yet implemented")
    elif cmd in ("/exit", "/quit"):
        raise EOFError
    else:
        formatter.print_error(f"Unknown command: {cmd}")


async def run_agent_turn(
    prompt: str,
    model: str,
    budget_cap: float | None = None,
) -> AsyncIterator[StreamEvent]:
    """Execute agent turn with streaming output.

    Args:
        prompt: User prompt
        model: LLM model to use
        budget_cap: Optional budget cap in USD

    Yields:
        Stream events
    """
    # TODO: Implement actual agent loop integration
    # For now, yield mock events
    _ = model, budget_cap  # Suppress unused warnings

    yield StreamEvent(
        event_type="text_delta",
        data={"text": f"Echo: {prompt}\n\n"},
    )
    yield StreamEvent(
        event_type="text_delta",
        data={"text": "Agent loop integration coming soon."},
    )


async def handle_stream_event(event: StreamEvent, formatter: CLIFormatter) -> None:
    """Handle streaming event and update display.

    Args:
        event: Stream event
        formatter: Output formatter
    """
    if event.event_type == "text_delta":
        formatter.print(event.data["text"], end="", flush=True)
    elif event.event_type == "tool_call":
        formatter.print_tool_start(event.data["name"])
    elif event.event_type == "tool_end":
        success = event.data.get("success", True)
        formatter.print_tool_end(success)
    elif event.event_type == "thinking":
        formatter.print_thinking(event.data["text"])
    elif event.event_type == "status":
        formatter.print_status(event.data["message"])

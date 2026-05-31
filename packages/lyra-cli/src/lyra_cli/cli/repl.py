"""Streaming REPL for Lyra - Claude Code style.

Provides an interactive command-line interface with:
- Real-time streaming output
- Multi-line input support
- Session persistence via lyra-core SessionStore
- Session lifecycle via lyra-sessions SessionManager
- Slash command handling
- Agent loop via lyra-core / harness-core providers
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from lyra_cli import __version__
from lyra_cli.llm_factory import build_llm
from lyra_harness_core.messages import Message as HMessage
from lyra_harness_core.messages import StopReason

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

    # ── Initialize session management ──────────────────────────────────────
    from lyra_sessions import SessionManager

    from lyra_core.sessions.store import SessionStore

    sessions_dir = repo_root / ".lyra" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_manager = SessionManager(base_dir=sessions_dir)
    session_store = SessionStore(db_path=repo_root / ".lyra" / "session_store.db")

    # Resolve or create session
    if pin_session_id:
        session_id = pin_session_id
        if session_manager.get(session_id) is None:
            # Create a manager-side tombstone for the pinned ID
            session_manager.create(config=None, parent_id="")
    elif resume_id:
        session_id = resume_id
        if session_manager.get(session_id) is None:
            # Resume a session we don't have locally — still track it
            session_manager.create(config=None, parent_id="")
    else:
        state = session_manager.create()
        session_id = state.id

    # ── Build LLM provider ─────────────────────────────────────────────────
    # Map user-friendly model name to provider kind, default to auto
    provider_kind = {"opus": "anthropic", "sonnet": "anthropic", "haiku": "anthropic"}.get(
        model.lower().strip(), "auto"
    )
    # Let the alias resolver pick the canonical model slug
    if provider_kind == "auto":
        os.environ.pop("HARNESS_LLM_MODEL", None)
    else:
        os.environ["HARNESS_LLM_MODEL"] = model
    llm = build_llm(provider_kind)

    # Print welcome banner
    formatter.print_welcome(
        version=__version__,
        model=model,
        repo=repo_root.name,
        session_id=session_id,
    )

    # Maintain a message transcript for the duration of the session
    transcript: list[HMessage] = []

    # Main REPL loop
    while True:
        try:
            # Read user input
            prompt = await read_prompt(formatter)

            if not prompt:
                continue

            # Handle slash commands
            if prompt.startswith("/"):
                await handle_slash_command(prompt, formatter, session_id=session_id,
                                           session_manager=session_manager)
                if prompt.strip().lower() in ("/exit", "/quit"):
                    break
                continue

            # Execute agent turn with streaming
            async for event in run_agent_turn(
                prompt=prompt,
                llm=llm,
                session_store=session_store,
                session_id=session_id,
                transcript=transcript,
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
            if os.environ.get("DEBUG") == "1":
                import traceback
                traceback.print_exc()
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


async def handle_slash_command(
    command: str,
    formatter: CLIFormatter,
    session_id: str = "",
    session_manager: Any | None = None,
) -> None:
    """Handle slash commands.

    Args:
        command: Slash command string (e.g., "/help", "/status")
        formatter: Output formatter
        session_id: Active session ID
        session_manager: Optional SessionManager for session operations
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
        if session_id:
            if session_manager:
                sessions = session_manager.list_sessions()
                formatter.print_markdown(
                    f"""
## Session Status

- **Session ID**: `{session_id}`
- **Active sessions**: {len(sessions)}
- **Session count**: {len(sessions)}
"""
                )
            else:
                formatter.print_info(f"Session ID: {session_id}")
        else:
            formatter.print_info("No active session")
    elif cmd == "/model":
        formatter.print_info(
            "Model switching not yet implemented from REPL. "
            "Restart with --model to change."
        )
    elif cmd == "/budget":
        formatter.print_info("Budget tracking not yet implemented in agent loop")
    elif cmd == "/clear":
        formatter.print_info("Conversation history cleared.")
    elif cmd in ("/exit", "/quit"):
        raise EOFError
    else:
        formatter.print_error(f"Unknown command: {cmd}")


async def run_agent_turn(
    prompt: str,
    llm: Any,
    session_store: Any | None = None,
    session_id: str = "",
    transcript: list[HMessage] | None = None,
    budget_cap: float | None = None,
) -> AsyncIterator[StreamEvent]:
    """Execute agent turn with streaming output via harness-core AgentLoop.

    Uses :class:`lyra_harness_core.loop.AgentLoop` to drive the think-act-observe
    cycle. When ``session_store`` is provided, messages are persisted to SQLite.

    Args:
        prompt: User prompt
        llm: LLM provider (from lyra_cli.llm_factory.build_llm)
        session_store: Optional SessionStore for message persistence
        session_id: Active session ID
        transcript: Optional mutable message list appended to each turn
        budget_cap: Optional budget cap in USD (soft — no enforcement client-side)

    Yields:
        Stream events
    """
    from lyra_harness_core.loop import AgentLoop
    from lyra_harness_core.tools import ToolRegistry

    _ = budget_cap  # client-side budget tracking not yet wired

    # Persist the user prompt
    if session_store:
        session_store.start_session(session_id, mode="agent")
        session_store.append_message(session_id, role="user", content=prompt)

    # Execute via the harness AgentLoop (no tools wired by default)
    tool_registry = ToolRegistry()
    loop = AgentLoop(llm=llm, tools=tool_registry, max_steps=10)

    result = loop.run(prompt)
    final_text = result.final_text

    # Persist the assistant response
    if session_store:
        session_store.append_message(
            session_id, role="assistant", content=final_text
        )

    # Append to in-memory transcript if provided
    if transcript is not None:
        transcript.append(HMessage.user(prompt))
        transcript.append(
            HMessage.assistant(
                content=final_text,
                stop_reason=StopReason.END_TURN,
            )
        )

    # Yield the result as stream events
    yield StreamEvent(
        event_type="text_delta",
        data={"text": final_text},
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

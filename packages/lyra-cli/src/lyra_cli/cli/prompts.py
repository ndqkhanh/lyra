"""Interactive prompt handling with prompt_toolkit"""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from pathlib import Path
import os


class LyraPrompt:
    """Interactive prompt with history and completion"""

    def __init__(self):
        # Setup history file
        history_dir = Path.home() / ".lyra"
        history_dir.mkdir(exist_ok=True)
        history_file = history_dir / "history"

        # Slash commands for completion
        slash_commands = [
            "/help", "/h", "/?",
            "/exit", "/quit", "/q",
            "/clear",
            "/model", "/m",
            "/config", "/settings",
            "/session", "/sessions",
            "/skills", "/skill",
            "/debug", "/status",
            "/history", "/hist",
            "/version", "/v",
        ]

        completer = WordCompleter(
            slash_commands,
            ignore_case=True,
            sentence=True
        )

        # Key bindings
        kb = KeyBindings()

        @kb.add('c-c')
        def _(event):
            """Handle Ctrl+C"""
            event.app.exit(exception=KeyboardInterrupt)

        @kb.add('c-d')
        def _(event):
            """Handle Ctrl+D (EOF)"""
            event.app.exit(exception=EOFError)

        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=completer,
            complete_while_typing=True,
            key_bindings=kb,
        )

    def get_input(self, prompt: str = "❯ ") -> str:
        """Get user input with history and completion"""
        try:
            return self.session.prompt(prompt)
        except (KeyboardInterrupt, EOFError):
            raise

    def get_multiline_input(self, prompt: str = "❯ ") -> str:
        """Get multi-line input"""
        try:
            return self.session.prompt(
                prompt,
                multiline=True,
                prompt_continuation="... "
            )
        except (KeyboardInterrupt, EOFError):
            raise

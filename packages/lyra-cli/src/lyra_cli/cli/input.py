"""Rich input handling with prompt_toolkit for Lyra CLI.

Provides:
- Slash command autocomplete
- File path completion
- Command history with Ctrl+R search
- Multi-line editing
- Keybindings (Ctrl+C, Ctrl+D, Alt+Enter, etc.)
- Auto-suggestions
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggest, AutoSuggestFromHistory, Suggestion
from prompt_toolkit.completion import Completer, Completion, PathCompleter, merge_completers
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments.lexers.markup import MarkdownLexer

# Slash commands available in Lyra (Claude Code style)
SLASH_COMMANDS = {
    # Session & Context
    "/help": "Show available commands",
    "/status": "Show session status",
    "/clear": "Clear conversation history",
    "/exit": "Exit the REPL",
    "/quit": "Exit the REPL",

    # Model & Configuration
    "/model": "Switch model or show current model",
    "/models": "List all available models",
    "/config": "Configure API keys and settings",
    "/credentials": "Set API credentials",

    # Information
    "/usage": "Show token usage and cost",
    "/cost": "View spending statistics",
    "/history": "Show command history",

    # Budget
    "/budget": "Set or show budget cap",

    # Development
    "/diff": "Show git diff",
    "/commit": "Create git commit",
    "/pr": "Create pull request",
}


class SlashCommandCompleter(Completer):
    """Autocomplete for slash commands and @ context references (Claude Code style)."""

    def __init__(self):
        self.path_completer = PathCompleter(expanduser=True)
        self._file_cache: list[str] = []
        self._file_cache_time: float = 0.0
        self._file_cache_cwd: str = ""

    def _get_files_in_cwd(self) -> list[str]:
        """Get all files and folders in current working directory (cached)."""
        import os
        import time

        cwd = os.getcwd()
        now = time.time()

        # Cache for 2 seconds
        if (
            self._file_cache
            and self._file_cache_cwd == cwd
            and now - self._file_cache_time < 2.0
        ):
            return self._file_cache

        # Rebuild cache
        files = []
        try:
            for entry in os.scandir(cwd):
                if entry.name.startswith("."):
                    continue  # Skip hidden files
                if entry.is_dir():
                    files.append(entry.name + "/")
                else:
                    files.append(entry.name)
        except Exception:
            pass

        self._file_cache = sorted(files)
        self._file_cache_cwd = cwd
        self._file_cache_time = now
        return self._file_cache

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """Generate completions based on current input."""
        text = document.text_before_cursor

        # @ context completion (files/folders like Claude Code)
        if "@" in text:
            # Extract the @ word
            words = text.split()
            for word in reversed(words):
                if word.startswith("@"):
                    ctx_word = word[1:]  # Remove @

                    if not ctx_word:
                        # Show all files and folders in current directory
                        files = self._get_files_in_cwd()
                        for file in files:
                            yield Completion(
                                text=file,
                                start_position=0,
                                display=f"@{file}",
                                display_meta="file" if not file.endswith("/") else "folder",
                            )
                    else:
                        # Filter files by prefix
                        files = self._get_files_in_cwd()
                        for file in files:
                            if file.lower().startswith(ctx_word.lower()):
                                yield Completion(
                                    text=file,
                                    start_position=-len(ctx_word),
                                    display=f"@{file}",
                                    display_meta="file" if not file.endswith("/") else "folder",
                                )
                    return

        # Slash command completion
        if text.startswith("/"):
            word = text[1:].lower()
            for cmd, desc in SLASH_COMMANDS.items():
                cmd_name = cmd[1:]
                if cmd_name.startswith(word):
                    yield Completion(
                        text=cmd_name,
                        start_position=-len(word),
                        display=cmd,
                        display_meta=desc,
                    )


class SlashCommandAutoSuggest(AutoSuggest):
    """Auto-suggest for slash commands with fallback to history."""

    def __init__(self):
        self.history_suggest = AutoSuggestFromHistory()

    def get_suggestion(
        self, buffer, document: Document
    ) -> Suggestion | None:
        """Get inline suggestion for current input."""
        text = document.text_before_cursor

        # Only suggest for slash commands
        if text.startswith("/"):
            word = text[1:].lower()
            for cmd in SLASH_COMMANDS:
                cmd_name = cmd[1:]
                if cmd_name.startswith(word) and cmd_name != word:
                    return Suggestion(cmd_name[len(word) :])

        # Fall back to history
        return self.history_suggest.get_suggestion(buffer, document)


def create_key_bindings() -> KeyBindings:
    """Create custom key bindings for Lyra REPL."""
    kb = KeyBindings()

    @kb.add("c-c")
    def handle_ctrl_c(event):
        """Ctrl+C: Cancel current input."""
        event.current_buffer.reset()

    @kb.add("c-d")
    def handle_ctrl_d(event):
        """Ctrl+D: Exit if buffer is empty."""
        if not event.current_buffer.text:
            event.app.exit()

    @kb.add("c-l")
    def handle_ctrl_l(event):
        """Ctrl+L: Clear screen."""
        event.app.renderer.clear()

    @kb.add("escape", "enter")  # Alt+Enter
    def handle_alt_enter(event):
        """Alt+Enter: Insert newline for multi-line input."""
        event.current_buffer.insert_text("\n")

    @kb.add("c-j")  # Ctrl+Enter (some terminals)
    def handle_ctrl_enter(event):
        """Ctrl+Enter: Insert newline."""
        event.current_buffer.insert_text("\n")

    return kb


def create_style() -> Style:
    """Create style for Lyra REPL."""
    return Style.from_dict(
        {
            # Prompt
            "prompt": "ansicyan bold",
            # Completion menu
            "completion-menu": "bg:#008888 #ffffff",
            "completion-menu.completion": "bg:#008888 #ffffff",
            "completion-menu.completion.current": "bg:#00aaaa #000000 bold",
            "completion-menu.meta": "bg:#006666 #ffffff italic",
            "completion-menu.meta.completion.current": "bg:#00aaaa #000000 bold",
            # Scrollbar
            "scrollbar.background": "bg:#88aaaa",
            "scrollbar.button": "bg:#222222",
            # Auto-suggestion (ghost text)
            "auto-suggestion": "#666666 italic",
            # Search
            "search": "bg:#ffff00 #000000",
            "search.current": "bg:#ff8800 #000000 bold",
            # Bottom toolbar
            "bottom-toolbar": "bg:#222222 #aaaaaa",
        }
    )


def create_prompt_session(history_file: Path) -> PromptSession:
    """Create a PromptSession with all features enabled.

    Args:
        history_file: Path to history file

    Returns:
        Configured PromptSession
    """
    return PromptSession(
        # History
        history=FileHistory(str(history_file)),
        # Completion
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        complete_in_thread=True,  # Don't block UI
        # Auto-suggestions
        auto_suggest=SlashCommandAutoSuggest(),
        # Syntax highlighting (optional, for markdown-style input)
        lexer=PygmentsLexer(MarkdownLexer),
        # Key bindings
        key_bindings=create_key_bindings(),
        # Styling
        style=create_style(),
        # Features
        enable_history_search=True,  # Ctrl+R support
        mouse_support=True,
        vi_mode=False,  # Use Emacs bindings
        # Multi-line
        multiline=False,  # Single-line by default, Alt+Enter for newlines
        prompt_continuation="... ",
    )

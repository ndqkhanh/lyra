"""
Command Palette — interactive fuzzy search, sandboxed execution, and REPL enhancements.

Provides:

    - CommandPalette: Interactive command palette with fuzzy search.
    - SandboxedExecutor: Execute commands in sandbox isolation.
    - REPLEnhancements: Syntax highlighting, auto-complete, history search.
"""

from __future__ import annotations

import difflib
import logging
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from lyra.commands.dispatcher import Command, CommandDispatcher

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

MAX_HISTORY_SIZE: int = 1000
FUZZY_CUTOFF: float = 0.4
DEFAULT_SANDBOX_TIMEOUT: float = 30.0
SHELL_BANNED_COMMANDS: tuple[str, ...] = (
    "rm -rf /", "dd if=", "mkfs", "chmod 777 /",
    ":(){ :|:& };:", "sudo rm", "reboot", "shutdown",
)

# ANSI color codes for syntax highlighting
_COLORS: dict[str, str] = {
    "reset": "\033[0m",
    "command": "\033[1;36m",   # cyan bold
    "flag": "\033[0;33m",      # yellow
    "string": "\033[0;32m",    # green
    "number": "\033[0;35m",    # magenta
    "comment": "\033[2;37m",   # grey
    "error": "\033[1;31m",     # red bold
    "match": "\033[1;33m",     # yellow bold (for search)
    "prompt": "\033[1;32m",    # green bold
}


# =============================================================================
# Data structures
# =============================================================================


@dataclass
class HistoryEntry:
    """A single entry in command history.

    Attributes:
        command: The raw command string.
        timestamp: When the command was executed.
        duration: Execution duration in seconds.
        exit_code: Shell exit code (or None if not applicable).
        output: Command output (truncated).
    """

    command: str
    timestamp: float = 0.0
    duration: float = 0.0
    exit_code: int | None = None
    output: str = ""


@dataclass
class CompletionResult:
    """A single auto-completion result.

    Attributes:
        text: The completion text.
        display: Display string (may differ from text).
        score: Relevance score (0.0 - 1.0).
    """

    text: str
    display: str = ""
    score: float = 0.0

    def __post_init__(self) -> None:
        if not self.display:
            self.display = self.text


# =============================================================================
# CommandPalette
# =============================================================================


class CommandPalette:
    """Interactive command palette with fuzzy search.

    The palette maintains a list of available commands (from the dispatcher)
    and provides fuzzy search, filtering by category, and keyboard-navigable
    result rendering.

    Attributes:
        dispatcher: The CommandDispatcher to source commands from.
        max_results: Maximum search results to return.
    """

    def __init__(
        self,
        dispatcher: CommandDispatcher,
        max_results: int = 20,
    ) -> None:
        self.dispatcher = dispatcher
        self.max_results = max_results
        self._search_history: list[str] = []
        self._selected_index: int = -1

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str) -> list[dict[str, Any]]:
        """Fuzzy-search available commands.

        Args:
            query: User's search query.

        Returns:
            List of result dicts with keys: name, description, aliases,
            usage, score, match_type.
        """
        if not query.strip():
            return self._all_commands()

        query = query.lower()
        results: list[dict[str, Any]] = []

        for cmd in self.dispatcher.list_commands():
            # Direct prefix match (highest score)
            if cmd.name.startswith(query):
                results.append(self._result(cmd, 1.0, "prefix"))
                continue

            # Fuzzy match name
            name_ratio = difflib.SequenceMatcher(None, query, cmd.name.lower()).ratio()
            if name_ratio >= FUZZY_CUTOFF:
                results.append(self._result(cmd, name_ratio, "fuzzy_name"))
                continue

            # Fuzzy match description
            desc_ratio = difflib.SequenceMatcher(None, query, cmd.description.lower()).ratio()
            if desc_ratio >= FUZZY_CUTOFF:
                results.append(self._result(cmd, desc_ratio * 0.8, "fuzzy_desc"))
                continue

            # Fuzzy match aliases
            for alias in cmd.aliases:
                alias_ratio = difflib.SequenceMatcher(None, query, alias.lower()).ratio()
                if alias_ratio >= FUZZY_CUTOFF:
                    results.append(self._result(cmd, alias_ratio * 0.9, "fuzzy_alias"))
                    break

        # Sort by score descending, then by name
        results.sort(key=lambda r: (-r["score"], r["name"]))
        return results[:self.max_results]

    def search_by_category(self, category: str) -> list[dict[str, Any]]:
        """Search commands by category tag embedded in description.

        Args:
            category: Category string to filter by.

        Returns:
            List of matching command results.
        """
        category = category.lower()
        results: list[dict[str, Any]] = []

        for cmd in self.dispatcher.list_commands():
            if category in cmd.description.lower() or category in cmd.name.lower():
                results.append(self._result(cmd, 0.9, "category"))

        return sorted(results, key=lambda r: r["name"])

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def record_search(self, query: str) -> None:
        """Record a search query in the history."""
        if query.strip():
            self._search_history.append(query.strip())
            if len(self._search_history) > MAX_HISTORY_SIZE:
                self._search_history.pop(0)

    def get_search_history(self) -> list[str]:
        """Return recent search queries."""
        return list(self._search_history)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def format_results(self, results: list[dict[str, Any]]) -> str:
        """Format search results as a display string.

        Args:
            results: Results from ``search()``.

        Returns:
            Formatted string ready for TUI rendering.
        """
        if not results:
            return "No matching commands found."

        lines: list[str] = []
        for i, r in enumerate(results):
            score_bar = "#" * max(1, int(r["score"] * 10))
            marker = ">" if i == self._selected_index else " "
            lines.append(
                f"{marker} {r['name']:20s} {r['description'][:50]:50s} "
                f"[{score_bar:<10}] {r['match_type']}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _all_commands(self) -> list[dict[str, Any]]:
        """Return all commands with neutral scores."""
        return [self._result(cmd, 0.5, "all") for cmd in self.dispatcher.list_commands()]

    @staticmethod
    def _result(cmd: Command, score: float, match_type: str) -> dict[str, Any]:
        return {
            "name": cmd.name,
            "description": cmd.description,
            "aliases": cmd.aliases,
            "usage": cmd.usage,
            "score": score,
            "match_type": match_type,
        }

    def get_statistics(self) -> dict[str, Any]:
        """Return palette statistics."""
        return {
            "available_commands": len(self.dispatcher.list_commands()),
            "search_history_size": len(self._search_history),
            "max_results": self.max_results,
        }


# =============================================================================
# SandboxedExecutor
# =============================================================================


class SandboxedExecutor:
    """Execute commands in sandbox isolation.

    Provides resource-limited subprocess execution with timeout,
    memory limits (via ``ulimit``), and a denylist of dangerous
    command patterns.

    Attributes:
        timeout: Default timeout in seconds.
        max_memory_mb: Maximum memory in MB (via ulimit -v).
        banned_commands: Tuple of banned command substrings.
        working_dir: Working directory for command execution.
    """

    def __init__(
        self,
        timeout: float = DEFAULT_SANDBOX_TIMEOUT,
        max_memory_mb: int = 128,
        banned_commands: tuple[str, ...] = SHELL_BANNED_COMMANDS,
        working_dir: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.banned_commands = banned_commands
        self.working_dir = working_dir or os.getcwd()

        self._execution_count: int = 0
        self._last_results: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self, command: str, timeout: float | None = None) -> dict[str, Any]:
        """Execute a command in a sandboxed subprocess.

        Args:
            command: The shell command to execute.
            timeout: Override timeout in seconds.

        Returns:
            Dict with keys: success, exit_code, output, error, duration, command.

        Raises:
            ValueError: If the command is banned.
        """
        # Pre-execution safety checks
        self._check_banned(command)

        actual_timeout = timeout if timeout is not None else self.timeout
        start = time.time()

        try:
            proc = subprocess.run(
                ["/bin/sh", "-c", command],
                capture_output=True,
                text=True,
                timeout=actual_timeout,
                cwd=self.working_dir,
                env={**os.environ, "LYRA_SANDBOX": "1"},
                preexec_fn=self._set_resource_limits,
            )

            duration = time.time() - start
            result: dict[str, Any] = {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "output": proc.stdout,
                "error": proc.stderr,
                "duration": duration,
                "command": command,
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start
            result = {
                "success": False,
                "exit_code": -1,
                "output": "",
                "error": f"Command timed out after {actual_timeout}s",
                "duration": duration,
                "command": command,
            }

        except Exception as e:
            duration = time.time() - start
            result = {
                "success": False,
                "exit_code": -2,
                "output": "",
                "error": str(e),
                "duration": duration,
                "command": command,
            }

        self._execution_count += 1
        self._last_results.append(result)
        # Keep only last 100 results
        if len(self._last_results) > 100:
            self._last_results = self._last_results[-100:]

        logger.debug(
            "SandboxedExecutor: %s (exit=%s, duration=%.2fs)",
            command[:60], result["exit_code"], duration,
        )

        return result

    def execute_batch(
        self,
        commands: list[str],
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Execute multiple commands sequentially.

        Args:
            commands: List of commands to execute.
            timeout: Per-command timeout.

        Returns:
            List of result dicts.
        """
        return [self.execute(cmd, timeout) for cmd in commands]

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    def _check_banned(self, command: str) -> None:
        """Check if a command contains banned patterns.

        Raises:
            ValueError: If the command is banned.
        """
        cmd_lower = command.lower()
        for banned in self.banned_commands:
            if banned in cmd_lower:
                raise ValueError(
                    f"Command contains banned pattern: '{banned}'"
                )

    @staticmethod
    def _set_resource_limits() -> None:
        """Set resource limits for the subprocess (ulimit)."""
        try:
            import resource

            # Set virtual memory limit
            mem_bytes = 128 * 1024 * 1024  # 128 MB default
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

            # Set CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        except (ImportError, ValueError, resource.error):
            pass  # Best-effort on platforms that don't support resource limits

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_last_results(self, count: int = 10) -> list[dict[str, Any]]:
        """Return the most recent execution results.

        Args:
            count: Number of results to return.

        Returns:
            List of result dicts.
        """
        return self._last_results[-count:]

    def get_execution_count(self) -> int:
        """Return total execution count."""
        return self._execution_count

    def get_statistics(self) -> dict[str, Any]:
        """Return sandbox executor statistics."""
        success = sum(1 for r in self._last_results if r.get("success"))
        total = len(self._last_results)
        avg_duration = (
            sum(r.get("duration", 0) for r in self._last_results) / total
            if total > 0 else 0.0
        )

        return {
            "execution_count": self._execution_count,
            "cached_results": total,
            "success_rate": success / total if total > 0 else 0.0,
            "avg_duration": avg_duration,
            "timeout": self.timeout,
            "working_dir": self.working_dir,
        }


# =============================================================================
# REPLEnhancements
# =============================================================================


class REPLEnhancements:
    """Syntax highlighting, auto-complete, and history search for the REPL.

    Enhances the Lyra command-line REPL with:
        - ANSI syntax highlighting for shell commands.
        - Tab-completion suggestions.
        - History search (CTRL+R style).
        - Prompt formatting.

    Attributes:
        dispatcher: The CommandDispatcher for command-aware completions.
        history: List of past command entries.
        max_history: Maximum history entries.
    """

    def __init__(
        self,
        dispatcher: CommandDispatcher | None = None,
        max_history: int = MAX_HISTORY_SIZE,
    ) -> None:
        self.dispatcher = dispatcher
        self.max_history = max_history

        self.history: list[HistoryEntry] = []
        self._history_position: int = -1

    # ------------------------------------------------------------------
    # Syntax highlighting
    # ------------------------------------------------------------------

    def highlight(self, command: str) -> str:
        """Apply ANSI syntax highlighting to a command string.

        Args:
            command: Raw command string.

        Returns:
            Highlighted command string with ANSI codes.
        """
        if not command:
            return ""

        parts = shlex.split(command)
        if not parts:
            return command

        highlighted: list[str] = []
        for i, part in enumerate(parts):
            if i == 0:
                # Command name
                highlighted.append(f"{_COLORS['command']}{part}{_COLORS['reset']}")
            elif part.startswith("-"):
                # Flag / option
                highlighted.append(f"{_COLORS['flag']}{part}{_COLORS['reset']}")
            elif part.startswith('"') or part.startswith("'"):
                # String literal
                highlighted.append(f"{_COLORS['string']}{part}{_COLORS['reset']}")
            elif part.isdigit() or (part.startswith("-") and part[1:].isdigit()):
                # Number
                highlighted.append(f"{_COLORS['number']}{part}{_COLORS['reset']}")
            else:
                highlighted.append(part)

        return " ".join(highlighted)

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences from a string.

        Args:
            text: Text with ANSI codes.

        Returns:
            Plain text.
        """
        ansi_pattern = re.compile(r"\033\[[0-9;]*m")
        return ansi_pattern.sub("", text)

    # ------------------------------------------------------------------
    # Auto-complete
    # ------------------------------------------------------------------

    def complete(self, partial: str) -> list[CompletionResult]:
        """Generate auto-completion suggestions for a partial command.

        Args:
            partial: Partial command input.

        Returns:
            List of CompletionResult sorted by score descending.
        """
        if not partial.strip():
            return self._complete_commands("")

        partial_lower = partial.lower()
        results: list[CompletionResult] = []

        parts = partial_lower.split()
        if len(parts) == 1:
            # Complete command name
            results = self._complete_commands(parts[0])
        else:
            # Complete arguments for the known command
            cmd_name = parts[0]
            arg_partial = parts[-1]

            cmd = self.dispatcher.get_command(cmd_name) if self.dispatcher else None
            if cmd:
                results = self._complete_args(cmd, arg_partial)
            else:
                results = self._complete_paths(arg_partial)

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:20]

    def _complete_commands(self, prefix: str) -> list[CompletionResult]:
        """Complete command names from the dispatcher."""
        if self.dispatcher is None:
            return []

        results: list[CompletionResult] = []
        for cmd in self.dispatcher.list_commands():
            if cmd.name.startswith(prefix):
                display = f"{cmd.name:<20} {cmd.description[:40]}"
                score = 1.0 if prefix == cmd.name[:len(prefix)] else 0.8
                results.append(CompletionResult(
                    text=cmd.name,
                    display=display,
                    score=score,
                ))
        return results

    def _complete_args(self, cmd: Command, prefix: str) -> list[CompletionResult]:
        """Complete arguments for a known command."""
        results: list[CompletionResult] = []

        # Suggest common flag patterns
        common_flags = ["--help", "--verbose", "--output", "--format", "--config"]
        for flag in common_flags:
            if flag.startswith(prefix):
                results.append(CompletionResult(
                    text=flag,
                    display=f"{flag:20} Common option",
                    score=0.7,
                ))

        return results

    @staticmethod
    def _complete_paths(prefix: str) -> list[CompletionResult]:
        """Complete file system paths."""
        results: list[CompletionResult] = []

        if not prefix:
            prefix = "."

        parent = os.path.dirname(prefix) or "."
        base = os.path.basename(prefix)

        try:
            for entry in os.listdir(parent):
                if entry.startswith(base):
                    full = os.path.join(parent, entry)
                    suffix = "/" if os.path.isdir(full) else ""
                    results.append(CompletionResult(
                        text=os.path.join(prefix[:len(prefix) - len(base)], entry) + suffix,
                        display=f"{entry}{suffix}",
                        score=0.6,
                    ))
        except OSError:
            pass

        return results

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def add_to_history(
        self,
        command: str,
        duration: float = 0.0,
        exit_code: int | None = None,
        output: str = "",
    ) -> None:
        """Add a command to the execution history.

        Args:
            command: The executed command.
            duration: Execution duration in seconds.
            exit_code: Shell exit code.
            output: Command output.
        """
        if not command.strip():
            return

        entry = HistoryEntry(
            command=command.strip(),
            timestamp=time.time(),
            duration=duration,
            exit_code=exit_code,
            output=output[:500],  # Truncate
        )
        self.history.append(entry)

        if len(self.history) > self.max_history:
            self.history.pop(0)

        self._history_position = len(self.history)

    def search_history(self, query: str) -> list[HistoryEntry]:
        """Search command history by substring or regex.

        Args:
            query: Search query (substring or regex pattern).

        Returns:
            List of matching HistoryEntry objects (most recent first).
        """
        if not query.strip():
            return list(reversed(self.history[-50:]))

        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        matches = [entry for entry in reversed(self.history) if pattern.search(entry.command)]
        return matches[:50]

    def get_history(self, limit: int = 50) -> list[HistoryEntry]:
        """Return recent history entries.

        Args:
            limit: Maximum number of entries.

        Returns:
            List of HistoryEntry (most recent first).
        """
        return list(reversed(self.history[-limit:]))

    def clear_history(self) -> None:
        """Clear all history entries."""
        self.history.clear()
        self._history_position = -1

    def navigate_back(self) -> str | None:
        """Navigate to the previous history entry (up arrow).

        Returns:
            The previous command string, or None if at beginning.
        """
        if not self.history:
            return None
        if self._history_position > 0:
            self._history_position -= 1
        return self.history[self._history_position].command

    def navigate_forward(self) -> str | None:
        """Navigate to the next history entry (down arrow).

        Returns:
            The next command string, or None if at end.
        """
        if not self.history:
            return None
        if self._history_position < len(self.history) - 1:
            self._history_position += 1
            return self.history[self._history_position].command
        return None

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def format_prompt(
        self,
        cwd: str = "",
        session_id: str = "",
        model: str = "",
    ) -> str:
        """Format a colored prompt string.

        Args:
            cwd: Current working directory (optional).
            session_id: Current session ID (optional).
            model: Current model name (optional).

        Returns:
            ANSI-formatted prompt string.
        """
        parts: list[str] = [f"{_COLORS['prompt']}lyra{_COLORS['reset']}"]

        if session_id:
            parts.append(f"[{session_id[:8]}]")

        if model:
            model_short = model.split("-")[0] if "-" in model else model[:8]
            parts.append(f"({model_short})")

        if cwd:
            home = os.path.expanduser("~")
            display = cwd.replace(home, "~")
            parts.append(f"in {display}")

        parts.append(f"{_COLORS['prompt']}>{_COLORS['reset']}")
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_matched_line(self, command: str, query: str) -> str:
        """Format a history line with the matching portion highlighted.

        Args:
            command: The full command string.
            query: The search query.

        Returns:
            Formatted string with query highlighted.
        """
        if not query:
            return command

        idx = command.lower().find(query.lower())
        if idx == -1:
            return command

        before = command[:idx]
        match = command[idx:idx + len(query)]
        after = command[idx + len(query):]

        return (
            f"{before}"
            f"{_COLORS['match']}{match}{_COLORS['reset']}"
            f"{after}"
        )

    def get_statistics(self) -> dict[str, Any]:
        """Return REPL enhancement statistics."""
        return {
            "history_size": len(self.history),
            "max_history": self.max_history,
            "dispatcher_available": self.dispatcher is not None,
        }

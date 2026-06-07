"""
CustomCommandLoader — load slash commands from .md files.

Allows users to define custom slash commands as Markdown files that are
parsed into executable Command objects.  Supports YAML frontmatter for
metadata (name, description, aliases, usage) and a body of instructions
that are injected into the handler.

SandboxedExecutor provides isolated execution with resource limits.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from lyra.commands.dispatcher import Command, CommandContext, CommandDispatcher

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_COMMANDS_DIR: str = ".lyra/commands"
SUPPORTED_EXTENSIONS: tuple[str, ...] = (".md", ".markdown")
MAX_COMMAND_FILE_SIZE: int = 1024 * 64  # 64 KB
DEFAULT_SANDBOX_TIMEOUT: float = 30.0
DEFAULT_MAX_MEMORY_MB: int = 128


# =============================================================================
# CustomCommandLoader
# =============================================================================


@dataclass
class CommandFile:
    """Metadata and content of a command .md file.

    Attributes:
        path: Absolute file path.
        name: Command name (from filename or frontmatter).
        description: Short description.
        usage: Usage string.
        aliases: Alternative command names.
        body: The markdown body (instructions).
        hidden: Whether the command is hidden from listings.
        frontmatter: Raw parsed frontmatter dict.
        content_hash: MD5 hash of file content for change detection.
        last_loaded: Timestamp of last load.
    """

    path: str
    name: str
    description: str = ""
    usage: str = ""
    aliases: list[str] = field(default_factory=list)
    body: str = ""
    hidden: bool = False
    frontmatter: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    last_loaded: float = 0.0


class CustomCommandLoader:
    """Load slash commands from .md files.

    Scans a directory for .md files with YAML frontmatter (``---``
    delimited) and registers each as a Command in the given dispatcher.

    Supports hot-reload via ``reload_changed()`` which detects modified
    files by content hash.

    Attributes:
        commands_dir: Path to the directory containing command .md files.
        dispatcher: The CommandDispatcher to register commands with.
        watch: Whether to watch for changes (reload support).
    """

    def __init__(
        self,
        commands_dir: str = DEFAULT_COMMANDS_DIR,
        dispatcher: CommandDispatcher | None = None,
        watch: bool = False,
    ) -> None:
        self.commands_dir = Path(commands_dir)
        self.dispatcher = dispatcher or CommandDispatcher()
        self.watch = watch

        self._loaded: dict[str, CommandFile] = {}
        self._load_errors: list[str] = []
        self._total_loaded: int = 0

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def discover_files(self) -> list[Path]:
        """Discover all command .md files in the commands directory.

        Returns:
            Sorted list of matching file paths.
        """
        if not self.commands_dir.exists():
            logger.debug("CustomCommandLoader: commands dir %s not found", self.commands_dir)
            return []

        files: list[Path] = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(sorted(self.commands_dir.rglob(f"*{ext}")))
        return files

    def load_all(self) -> int:
        """Load (or reload) all command .md files.

        Returns:
            Number of successfully loaded commands.

        Raises:
            FileNotFoundError: If the commands directory does not exist.
        """
        if not self.commands_dir.exists():
            raise FileNotFoundError(f"Commands directory not found: {self.commands_dir}")

        loaded = 0
        self._load_errors.clear()

        for filepath in self.discover_files():
            try:
                cmd_file = self._parse_file(filepath)
                self._loaded[cmd_file.name] = cmd_file
                self._register_command(cmd_file)
                loaded += 1
            except Exception as e:
                self._load_errors.append(f"{filepath}: {e}")
                logger.warning("CustomCommandLoader: failed to load %s: %s", filepath, e)

        self._total_loaded = loaded
        logger.info("CustomCommandLoader: loaded %d commands from %s", loaded, self.commands_dir)
        return loaded

    def load_single(self, filepath: str) -> CommandFile | None:
        """Load a single command .md file.

        Args:
            filepath: Path to the .md file.

        Returns:
            Parsed CommandFile, or None if parsing failed.
        """
        path = Path(filepath)
        if not path.exists():
            logger.warning("CustomCommandLoader: file not found: %s", filepath)
            return None

        try:
            cmd_file = self._parse_file(path)
            self._loaded[cmd_file.name] = cmd_file
            self._register_command(cmd_file)
            self._total_loaded += 1
            return cmd_file
        except Exception as e:
            self._load_errors.append(f"{filepath}: {e}")
            return None

    # ------------------------------------------------------------------
    # Reload
    # ------------------------------------------------------------------

    def reload_changed(self) -> int:
        """Reload only files whose content hash has changed.

        Returns:
            Number of reloaded (added/updated) commands.
        """
        if not self.watch:
            return 0

        reloaded = 0
        for filepath in self.discover_files():
            content_hash = self._hash_file(filepath)
            name = filepath.stem.lower()

            existing = self._loaded.get(name)
            if existing is not None and existing.content_hash == content_hash:
                continue  # unchanged

            try:
                cmd_file = self._parse_file(filepath)
                self._loaded[name] = cmd_file
                self._register_command(cmd_file)
                reloaded += 1
                logger.debug("CustomCommandLoader: reloaded %s", filepath)
            except Exception as e:
                logger.warning("CustomCommandLoader: reload failed for %s: %s", filepath, e)

        return reloaded

    def unload_all(self) -> int:
        """Unregister all loaded custom commands.

        Returns:
            Number of unregistered commands.
        """
        count = 0
        for name in list(self._loaded.keys()):
            if self.dispatcher.unregister(name):
                count += 1
            del self._loaded[name]
        logger.info("CustomCommandLoader: unloaded %d commands", count)
        return count

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_loaded_commands(self) -> list[CommandFile]:
        """Return all currently loaded command files."""
        return list(self._loaded.values())

    def get_load_errors(self) -> list[str]:
        """Return list of load error messages."""
        return list(self._load_errors)

    def get_statistics(self) -> dict[str, Any]:
        """Return loader statistics."""
        return {
            "commands_dir": str(self.commands_dir),
            "total_loaded": self._total_loaded,
            "currently_loaded": len(self._loaded),
            "load_errors": len(self._load_errors),
            "watch_enabled": self.watch,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_file(self, filepath: Path) -> CommandFile:
        """Parse a .md file into a CommandFile.

        Expects optional YAML frontmatter between ``---`` delimiters,
        followed by the command body (instructions).
        """
        content = filepath.read_text(encoding="utf-8")
        content_hash = self._hash_content(content)

        if len(content) > MAX_COMMAND_FILE_SIZE:
            raise ValueError(f"Command file exceeds max size ({len(content)} > {MAX_COMMAND_FILE_SIZE})")

        frontmatter: dict[str, Any] = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                raw_fm = parts[1].strip()
                body = parts[2].strip()
                frontmatter = self._parse_frontmatter(raw_fm)

        # Derive name from frontmatter or filename
        name = str(frontmatter.get("name", filepath.stem)).lower()

        return CommandFile(
            path=str(filepath),
            name=name,
            description=str(frontmatter.get("description", "")),
            usage=str(frontmatter.get("usage", "")),
            aliases=list(frontmatter.get("aliases", [])),
            body=body,
            hidden=bool(frontmatter.get("hidden", False)),
            frontmatter=frontmatter,
            content_hash=content_hash,
            last_loaded=time.time(),
        )

    def _register_command(self, cmd_file: CommandFile) -> None:
        """Register a CommandFile as a Command in the dispatcher."""
        body = cmd_file.body
        description = cmd_file.description or f"Custom command loaded from {Path(cmd_file.path).name}"

        async def _handler(ctx: CommandContext) -> str:
            # Build a response from the body, substituting arguments
            rendered = body
            for i, arg in enumerate(ctx.args):
                rendered = rendered.replace(f"${{{i}}}", arg)
                rendered = rendered.replace(f"${i}", arg)

            rendered = rendered.replace("${args}", " ".join(ctx.args))
            rendered = rendered.replace("${cmd}", ctx.command)
            rendered = rendered.replace("${session_id}", ctx.session_id)

            return rendered

        command = Command(
            name=cmd_file.name,
            handler=_handler,
            description=description,
            usage=cmd_file.usage or cmd_file.name,
            aliases=cmd_file.aliases,
            hidden=cmd_file.hidden,
        )

        # Unregister existing first to allow updates
        if self.dispatcher.get_command(cmd_file.name):
            self.dispatcher.unregister(cmd_file.name)

        self.dispatcher.register(command)

    @staticmethod
    def _parse_frontmatter(raw: str) -> dict[str, Any]:
        """Parse YAML-like frontmatter (simple key: value).

        Uses a lightweight parser that handles basic YAML structures.
        Falls back gracefully on parsing errors.
        """
        result: dict[str, Any] = {}
        current_key = ""
        current_list: list[str] = []

        for line in raw.splitlines():
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("- "):
                # List item
                item = stripped[2:].strip()
                if current_key:
                    current_list.append(item)
                continue

            if ":" in stripped:
                # Save any accumulated list
                if current_key and current_list:
                    result[current_key] = current_list
                    current_list = []

                key, _, value = stripped.partition(":")
                current_key = key.strip()
                value = value.strip().strip('"').strip("'")

                if value:
                    # Try bool
                    if value.lower() == "true":
                        result[current_key] = True
                    elif value.lower() == "false":
                        result[current_key] = False
                    else:
                        result[current_key] = value
                else:
                    # Start of a list
                    current_list = []

        # Flush remaining list
        if current_key and current_list:
            result[current_key] = current_list

        return result

    @staticmethod
    def _hash_file(filepath: Path) -> str:
        """Compute MD5 hash of a file's contents."""
        content = filepath.read_bytes()
        return hashlib.md5(content, usedforsecurity=False).hexdigest()

    @staticmethod
    def _hash_content(content: str) -> str:
        """Compute MD5 hash of a string."""
        return hashlib.md5(content.encode("utf-8"), usedforsecurity=False).hexdigest()

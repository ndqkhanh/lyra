"""Command registry for loading and managing commands."""
from pathlib import Path
from typing import Dict, List, Optional
import yaml

from .command_metadata import CommandMetadata


class CommandRegistry:
    """Registry for loading and managing commands."""

    def __init__(self, command_dirs: Optional[List[Path]] = None):
        self.command_dirs = command_dirs or []
        self._commands: Dict[str, CommandMetadata] = {}

    def load_commands(self) -> Dict[str, CommandMetadata]:
        """Load all commands from configured directories."""
        self._commands.clear()

        for command_dir in self.command_dirs:
            if not command_dir.exists():
                continue

            for command_file in command_dir.glob("*.md"):
                try:
                    metadata = self._parse_command_file(command_file)
                    if metadata:
                        self._commands[metadata.name] = metadata
                except Exception as e:
                    print(f"Error loading command {command_file}: {e}")

        return self._commands

    def _parse_command_file(self, file_path: Path) -> Optional[CommandMetadata]:
        """Parse command file with YAML frontmatter."""
        content = file_path.read_text()

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
            return CommandMetadata(
                name=frontmatter.get("name", ""),
                description=frontmatter.get("description", ""),
                agent=frontmatter.get("agent"),
                skill=frontmatter.get("skill"),
                args=frontmatter.get("args"),
                file_path=str(file_path)
            )
        except yaml.YAMLError:
            return None

    def get_command(self, name: str) -> Optional[CommandMetadata]:
        """Get command by name."""
        return self._commands.get(name)

    def search_commands(self, query: str) -> List[CommandMetadata]:
        """Search commands by name or description."""
        query_lower = query.lower()
        return [
            cmd for cmd in self._commands.values()
            if query_lower in cmd.name.lower() or query_lower in cmd.description.lower()
        ]

    def list_commands(self) -> List[CommandMetadata]:
        """List all loaded commands."""
        return list(self._commands.values())

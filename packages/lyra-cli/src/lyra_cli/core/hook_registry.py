"""Hook registry for loading and managing hooks."""
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import re

from .hook_metadata import HookMetadata, HookType


class HookRegistry:
    """Registry for loading and managing hooks."""

    def __init__(self, hook_dirs: Optional[List[Path]] = None):
        self.hook_dirs = hook_dirs or []
        self._hooks: Dict[str, HookMetadata] = {}

    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase to UPPER_SNAKE_CASE."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()

    def load_hooks(self) -> Dict[str, HookMetadata]:
        """Load all hooks from configured directories."""
        self._hooks.clear()

        for hook_dir in self.hook_dirs:
            if not hook_dir.exists():
                continue

            for hook_file in hook_dir.glob("*.md"):
                try:
                    metadata = self._parse_hook_file(hook_file)
                    if metadata:
                        self._hooks[metadata.name] = metadata
                except Exception as e:
                    print(f"Error loading hook {hook_file}: {e}")

        return self._hooks

    def _parse_hook_file(self, file_path: Path) -> Optional[HookMetadata]:
        """Parse hook file with YAML frontmatter."""
        content = file_path.read_text()

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
            hook_type_str = frontmatter.get("type", "")
            hook_type = HookType[self._camel_to_snake(hook_type_str)]

            return HookMetadata(
                name=frontmatter.get("name", ""),
                description=frontmatter.get("description", ""),
                hook_type=hook_type,
                script=frontmatter.get("script", ""),
                enabled=frontmatter.get("enabled", True),
                file_path=str(file_path)
            )
        except (yaml.YAMLError, KeyError):
            return None

    def get_hook(self, name: str) -> Optional[HookMetadata]:
        """Get hook by name."""
        return self._hooks.get(name)

    def get_hooks_by_type(self, hook_type: HookType) -> List[HookMetadata]:
        """Get all hooks of a specific type."""
        return [
            hook for hook in self._hooks.values()
            if hook.hook_type == hook_type and hook.enabled
        ]

    def search_hooks(self, query: str) -> List[HookMetadata]:
        """Search hooks by name or description."""
        query_lower = query.lower()
        return [
            hook for hook in self._hooks.values()
            if query_lower in hook.name.lower() or query_lower in hook.description.lower()
        ]

    def list_hooks(self) -> List[HookMetadata]:
        """List all loaded hooks."""
        return list(self._hooks.values())

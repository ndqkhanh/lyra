"""
Permission Store - Persistent permission preferences.

Features:
- Allow/deny lists
- Session cache
- JSON storage
- Automatic backup
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class PermissionStore:
    """
    Persistent permission preferences storage.

    Features:
    - Allow/deny lists
    - Session cache
    - JSON storage
    """

    def __init__(self, store_path: Optional[str] = None):
        """Initialize permission store."""
        if store_path:
            self.store_path = Path(store_path).expanduser()
        else:
            self.store_path = Path("~/.lyra/permissions.json").expanduser()

        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        # Session cache
        self.cache: Dict[Tuple[str, str], bool] = {}

        # Load preferences
        self.preferences = self._load_preferences()

    def _load_preferences(self) -> Dict[str, Any]:
        """Load preferences from disk."""
        if self.store_path.exists():
            try:
                with open(self.store_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._default_preferences()
        return self._default_preferences()

    def _default_preferences(self) -> Dict[str, Any]:
        """Get default preferences."""
        return {"policy": "balanced", "allowList": [], "denyList": [], "sessionCache": {}}

    def _save_preferences(self):
        """Save preferences to disk."""
        try:
            with open(self.store_path, "w") as f:
                json.dump(self.preferences, f, indent=2)
        except IOError:
            pass  # Fail silently

    def allow(self, tool: str, operation: str):
        """
        Add to allow list.

        Args:
            tool: Tool name
            operation: Operation name
        """
        key = f"{tool}:{operation}"
        if key not in self.preferences["allowList"]:
            self.preferences["allowList"].append(key)
            self._save_preferences()

        # Update cache
        self.cache[(tool, operation)] = True

    def deny(self, tool: str, operation: str):
        """
        Add to deny list.

        Args:
            tool: Tool name
            operation: Operation name
        """
        key = f"{tool}:{operation}"
        if key not in self.preferences["denyList"]:
            self.preferences["denyList"].append(key)
            self._save_preferences()

        # Update cache
        self.cache[(tool, operation)] = False

    def is_allowed(self, tool: str, operation: str) -> bool:
        """
        Check if operation is in allow list.

        Args:
            tool: Tool name
            operation: Operation name

        Returns:
            True if allowed
        """
        # Check cache first
        cache_key = (tool, operation)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Check allow list
        key = f"{tool}:{operation}"
        allowed = key in self.preferences["allowList"]

        # Update cache
        if allowed:
            self.cache[cache_key] = True

        return allowed

    def is_denied(self, tool: str, operation: str) -> bool:
        """
        Check if operation is in deny list.

        Args:
            tool: Tool name
            operation: Operation name

        Returns:
            True if denied
        """
        # Check cache first
        cache_key = (tool, operation)
        if cache_key in self.cache and not self.cache[cache_key]:
            return True

        # Check deny list
        key = f"{tool}:{operation}"
        denied = key in self.preferences["denyList"]

        # Update cache
        if denied:
            self.cache[cache_key] = False

        return denied

    def remove(self, tool: str, operation: str):
        """
        Remove from both allow and deny lists.

        Args:
            tool: Tool name
            operation: Operation name
        """
        key = f"{tool}:{operation}"

        if key in self.preferences["allowList"]:
            self.preferences["allowList"].remove(key)

        if key in self.preferences["denyList"]:
            self.preferences["denyList"].remove(key)

        self._save_preferences()

        # Clear cache
        cache_key = (tool, operation)
        if cache_key in self.cache:
            del self.cache[cache_key]

    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all preferences."""
        return self.preferences.copy()

    def clear(self):
        """Clear all preferences."""
        self.preferences = self._default_preferences()
        self._save_preferences()
        self.cache.clear()

    def get_allow_list(self) -> List[str]:
        """Get allow list."""
        return self.preferences["allowList"].copy()

    def get_deny_list(self) -> List[str]:
        """Get deny list."""
        return self.preferences["denyList"].copy()

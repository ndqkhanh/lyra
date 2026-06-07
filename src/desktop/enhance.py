"""
Desktop GUI enhancements — DesktopConfig, window management stubs.

Provides configuration models and stub window-manager interfaces
for future GUI integration (e.g. floating panels, multi-monitor
layouts, virtual desktops).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WindowPosition(Enum):
    """Predefined window positions."""

    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"
    FULLSCREEN = "fullscreen"


class WindowState(Enum):
    """Window state."""

    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    HIDDEN = "hidden"


@dataclass(frozen=True)
class WindowGeometry:
    """Window geometry in screen coordinates."""

    x: int
    y: int
    width: int
    height: int


@dataclass
class DesktopConfig:
    """Configuration for desktop GUI enhancements.

    Attributes:
        theme: Theme name (e.g. "dark", "light", "system").
        font_size: Base font size in points.
        enable_virtual_desktops: Whether virtual desktop support is active.
        enable_window_snapping: Whether window snapping is enabled.
        default_window_width: Default width for new windows.
        default_window_height: Default height for new windows.
        animation_enabled: Whether UI animations are enabled.
        extra: Additional custom configuration keys.
    """

    theme: str = "dark"
    font_size: int = 12
    enable_virtual_desktops: bool = False
    enable_window_snapping: bool = True
    default_window_width: int = 1024
    default_window_height: int = 768
    animation_enabled: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def merge(self, overrides: dict[str, Any]) -> DesktopConfig:
        """Return a new DesktopConfig with overridden values.

        Args:
            overrides: Dictionary of attributes to override.

        Returns:
            A new DesktopConfig instance with merged values.
        """
        current = {
            "theme": self.theme,
            "font_size": self.font_size,
            "enable_virtual_desktops": self.enable_virtual_desktops,
            "enable_window_snapping": self.enable_window_snapping,
            "default_window_width": self.default_window_width,
            "default_window_height": self.default_window_height,
            "animation_enabled": self.animation_enabled,
            "extra": dict(self.extra),
        }

        # Shallow merge, preserving known fields
        for key, value in overrides.items():
            if key in current:
                current[key] = value

        if "extra" in overrides and isinstance(overrides["extra"], dict):
            current["extra"].update(overrides["extra"])

        return DesktopConfig(**current)

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to dictionary."""
        return {
            "theme": self.theme,
            "font_size": self.font_size,
            "enable_virtual_desktops": self.enable_virtual_desktops,
            "enable_window_snapping": self.enable_window_snapping,
            "default_window_width": self.default_window_width,
            "default_window_height": self.default_window_height,
            "animation_enabled": self.animation_enabled,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DesktopConfig:
        """Create config from dictionary."""
        return cls(
            theme=data.get("theme", "dark"),
            font_size=data.get("font_size", 12),
            enable_virtual_desktops=data.get("enable_virtual_desktops", False),
            enable_window_snapping=data.get("enable_window_snapping", True),
            default_window_width=data.get("default_window_width", 1024),
            default_window_height=data.get("default_window_height", 768),
            animation_enabled=data.get("animation_enabled", True),
            extra=data.get("extra", {}),
        )


class WindowManager:
    """Stub window manager for orchestrating application windows.

    Provides create, move, resize, focus, and close operations.
    Currently a stub — real implementation deferred to GUI toolkit integration.
    """

    def __init__(self, config: DesktopConfig | None = None):
        """Initialize WindowManager.

        Args:
            config: Optional desktop configuration.
        """
        self.config = config or DesktopConfig()
        self._windows: dict[str, dict[str, Any]] = {}

    def create_window(
        self,
        title: str,
        geometry: WindowGeometry | None = None,
        state: WindowState = WindowState.NORMAL,
    ) -> str:
        """Create a new window.

        Args:
            title: Window title.
            geometry: Initial geometry; uses defaults from config if None.
            state: Initial window state.

        Returns:
            Window identifier string.
        """
        import uuid

        window_id = str(uuid.uuid4())
        geo = geometry or WindowGeometry(
            x=100,
            y=100,
            width=self.config.default_window_width,
            height=self.config.default_window_height,
        )
        self._windows[window_id] = {
            "id": window_id,
            "title": title,
            "geometry": geo,
            "state": state,
        }
        return window_id

    def move_window(self, window_id: str, x: int, y: int) -> bool:
        """Move window to new position.

        Args:
            window_id: Window identifier.
            x: New x coordinate.
            y: New y coordinate.

        Returns:
            True if window was found and moved, False otherwise.
        """
        window = self._windows.get(window_id)
        if window is None:
            return False
        existing = window["geometry"]
        window["geometry"] = WindowGeometry(
            x=x, y=y, width=existing.width, height=existing.height
        )
        return True

    def resize_window(self, window_id: str, width: int, height: int) -> bool:
        """Resize window.

        Args:
            window_id: Window identifier.
            width: New width.
            height: New height.

        Returns:
            True if window was found and resized, False otherwise.
        """
        window = self._windows.get(window_id)
        if window is None:
            return False
        existing = window["geometry"]
        window["geometry"] = WindowGeometry(
            x=existing.x, y=existing.y, width=width, height=height
        )
        return True

    def focus_window(self, window_id: str) -> bool:
        """Focus a window.

        Args:
            window_id: Window identifier.

        Returns:
            True if window was found, False otherwise.
        """
        return window_id in self._windows

    def close_window(self, window_id: str) -> bool:
        """Close a window.

        Args:
            window_id: Window identifier.

        Returns:
            True if window was found and removed, False otherwise.
        """
        if window_id in self._windows:
            del self._windows[window_id]
            return True
        return False

    def list_windows(self) -> list[dict[str, Any]]:
        """List all managed windows.

        Returns:
            List of window info dictionaries.
        """
        return list(self._windows.values())

    def get_window(self, window_id: str) -> dict[str, Any] | None:
        """Get window info by ID.

        Args:
            window_id: Window identifier.

        Returns:
            Window info dict or None.
        """
        return self._windows.get(window_id)


class VirtualDesktopManager:
    """Stub virtual desktop manager for organizing workspaces.

    Supports multiple virtual desktops with window assignment.
    """

    def __init__(self):
        """Initialize VirtualDesktopManager."""
        self._desktops: dict[str, list[str]] = {}
        self._active_desktop: str | None = None

    def create_desktop(self, name: str) -> str:
        """Create a new virtual desktop.

        Args:
            name: Human-readable desktop name.

        Returns:
            Desktop identifier.
        """
        import uuid

        desktop_id = str(uuid.uuid4())
        self._desktops[desktop_id] = []
        if self._active_desktop is None:
            self._active_desktop = desktop_id
        return desktop_id

    def remove_desktop(self, desktop_id: str) -> bool:
        """Remove a virtual desktop.

        Args:
            desktop_id: Desktop identifier.

        Returns:
            True if removed, False if not found.
        """
        if desktop_id not in self._desktops:
            return False
        del self._desktops[desktop_id]
        if self._active_desktop == desktop_id:
            desktops = list(self._desktops.keys())
            self._active_desktop = desktops[0] if desktops else None
        return True

    def assign_window(self, desktop_id: str, window_id: str) -> bool:
        """Assign a window to a virtual desktop.

        Args:
            desktop_id: Desktop identifier.
            window_id: Window identifier.

        Returns:
            True if desktop exists, False otherwise.
        """
        if desktop_id not in self._desktops:
            return False
        if window_id not in self._desktops[desktop_id]:
            self._desktops[desktop_id].append(window_id)
        return True

    def switch_desktop(self, desktop_id: str) -> bool:
        """Switch to a different virtual desktop.

        Args:
            desktop_id: Desktop identifier.

        Returns:
            True if desktop exists, False otherwise.
        """
        if desktop_id not in self._desktops:
            return False
        self._active_desktop = desktop_id
        return True

    def list_desktops(self) -> list[dict[str, Any]]:
        """List all virtual desktops.

        Returns:
            List of desktop info dictionaries.
        """
        return [
            {"id": did, "name": f"Desktop-{did[:8]}", "windows": list(wins)}
            for did, wins in self._desktops.items()
        ]

    def active_desktop(self) -> str | None:
        """Get the active desktop identifier."""
        return self._active_desktop

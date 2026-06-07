"""Tests for src/desktop/enhance.py."""
from __future__ import annotations

import pytest

from lyra.desktop.enhance import (
    DesktopConfig,
    VirtualDesktopManager,
    WindowGeometry,
    WindowManager,
    WindowState,
)


class TestDesktopConfig:
    """Tests for DesktopConfig."""

    def test_default_config(self):
        """Default config values are correct."""
        config = DesktopConfig()
        assert config.theme == "dark"
        assert config.font_size == 12
        assert config.default_window_width == 1024
        assert config.default_window_height == 768

    def test_merge_preserves_immutability(self):
        """merge() returns a new instance without mutating the original."""
        original = DesktopConfig(theme="dark", animation_enabled=False)
        merged = original.merge({"theme": "light", "animation_enabled": True})

        assert original.theme == "dark"
        assert original.animation_enabled is False
        assert merged.theme == "light"
        assert merged.animation_enabled is True

    def test_to_dict_roundtrip(self):
        """from_dict(to_dict(x)) == x."""
        original = DesktopConfig(
            theme="light",
            font_size=14,
            enable_window_snapping=False,
            extra={"custom_key": "val"},
        )
        d = original.to_dict()
        restored = DesktopConfig.from_dict(d)
        assert restored.theme == original.theme
        assert restored.font_size == original.font_size
        assert restored.extra["custom_key"] == "val"


class TestWindowManager:
    """Tests for WindowManager."""

    def test_create_and_list(self):
        """Creating windows adds them to the list."""
        mgr = WindowManager()
        wid = mgr.create_window("Test")
        windows = mgr.list_windows()
        assert len(windows) == 1
        assert windows[0]["title"] == "Test"

    def test_move_window(self):
        """move_window changes geometry."""
        mgr = WindowManager()
        wid = mgr.create_window("MoveMe")
        assert mgr.move_window(wid, 200, 300) is True
        info = mgr.get_window(wid)
        assert info is not None
        assert info["geometry"].x == 200
        assert info["geometry"].y == 300

    def test_close_window_removes(self):
        """close_window removes the window from tracking."""
        mgr = WindowManager()
        wid = mgr.create_window("CloseMe")
        assert mgr.close_window(wid) is True
        assert mgr.get_window(wid) is None
        assert len(mgr.list_windows()) == 0

    def test_close_missing_returns_false(self):
        """close_window on nonexistent ID returns False."""
        mgr = WindowManager()
        assert mgr.close_window("nonexistent") is False


class TestVirtualDesktopManager:
    """Tests for VirtualDesktopManager."""

    def test_create_and_switch(self):
        """Creating a desktop assigns it as active."""
        vdm = VirtualDesktopManager()
        d1 = vdm.create_desktop("Work")
        assert vdm.active_desktop() == d1

    def test_switch_desktop(self):
        """Switching between desktops works."""
        vdm = VirtualDesktopManager()
        d1 = vdm.create_desktop("A")
        d2 = vdm.create_desktop("B")
        assert vdm.switch_desktop(d2) is True
        assert vdm.active_desktop() == d2

    def test_remove_desktop(self):
        """Removing the active desktop promotes another."""
        vdm = VirtualDesktopManager()
        d1 = vdm.create_desktop("A")
        d2 = vdm.create_desktop("B")
        vdm.remove_desktop(d1)
        assert vdm.active_desktop() == d2

    def test_assign_window(self):
        """Assigning a window adds it to the desktop."""
        vdm = VirtualDesktopManager()
        d1 = vdm.create_desktop("A")
        assert vdm.assign_window(d1, "win-1") is True
        desktops = vdm.list_desktops()
        assert "win-1" in desktops[0]["windows"]

"""Wave-F Task 15 — IDE bridges contract."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.ide import (
    IDEError,
    IDETarget,
    available_bridges,
    bridge_for,
    build_open_command,
)


def test_available_bridges_include_common_editors() -> None:
    ids = {b.id for b in available_bridges()}
    assert {"vscode", "cursor", "jetbrains", "zed", "nvim"}.issubset(ids)


def test_unknown_bridge_rejected() -> None:
    with pytest.raises(IDEError):
        bridge_for("notepad")


def test_ide_target_rejects_invalid_line() -> None:
    with pytest.raises(IDEError):
        IDETarget(path=Path("/tmp/x.py"), line=0)


def test_vscode_build_open_command(tmp_path: Path) -> None:
    file = tmp_path / "main.py"
    file.write_text("print('hi')\n", encoding="utf-8")
    argv = build_open_command(
        bridge="vscode",
        target=IDETarget(path=file, line=3, column=7),
    )
    assert argv[0] == "code"
    assert "--goto" in argv
    assert argv[-1].endswith("main.py:3:7")


def test_cursor_build_open_command(tmp_path: Path) -> None:
    file = tmp_path / "main.py"
    file.write_text("print('hi')\n", encoding="utf-8")
    argv = build_open_command(
        bridge="cursor",
        target=IDETarget(path=file, line=3),
    )
    assert argv[0] == "cursor"
    assert argv[-1].endswith("main.py:3")


def test_jetbrains_uses_line_flag(tmp_path: Path) -> None:
    file = tmp_path / "main.py"
    file.write_text("", encoding="utf-8")
    argv = build_open_command(
        bridge="jetbrains",
        target=IDETarget(path=file, line=42, column=5),
    )
    assert argv[0] == "idea"
    assert "--line" in argv
    assert "42" in argv
    assert "--column" in argv
    assert "5" in argv
    assert argv[-1].endswith("main.py")


def test_zed_uses_colon_form(tmp_path: Path) -> None:
    file = tmp_path / "main.py"
    file.write_text("", encoding="utf-8")
    argv = build_open_command(
        bridge="zed",
        target=IDETarget(path=file, line=12),
    )
    assert argv[0] == "zed"
    assert argv[-1].endswith("main.py:12")


def test_nvim_uses_plus_line(tmp_path: Path) -> None:
    file = tmp_path / "main.py"
    file.write_text("", encoding="utf-8")
    argv = build_open_command(
        bridge="nvim",
        target=IDETarget(path=file, line=7),
    )
    assert argv[0] == "nvim"
    assert "+7" in argv
    assert argv[-1].endswith("main.py")

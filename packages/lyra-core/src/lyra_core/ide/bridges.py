"""IDE bridge builders.

Each bridge maps an ``IDETarget`` (absolute path + optional line +
optional column) to a shell-safe argv that opens the file in the
user's IDE. The REPL slash command uses :func:`build_open_command`
and hands the argv off to subprocess.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


__all__ = [
    "IDEBridge",
    "IDEError",
    "IDETarget",
    "available_bridges",
    "bridge_for",
    "build_open_command",
]


class IDEError(ValueError):
    pass


@dataclass(frozen=True)
class IDETarget:
    path: Path
    line: int | None = None
    column: int | None = None

    def __post_init__(self) -> None:
        if self.line is not None and self.line < 1:
            raise IDEError(f"line must be >= 1, got {self.line}")
        if self.column is not None and self.column < 1:
            raise IDEError(f"column must be >= 1, got {self.column}")


@dataclass(frozen=True)
class IDEBridge:
    id: str
    display_name: str
    executable: str

    def argv(self, target: IDETarget) -> list[str]:
        raise NotImplementedError


class VSCodeBridge(IDEBridge):
    def __init__(self) -> None:
        super().__init__(id="vscode", display_name="VS Code", executable="code")

    def argv(self, target: IDETarget) -> list[str]:
        # `code --goto PATH:LINE:COL`
        spec = str(target.path.resolve())
        if target.line is not None:
            spec = f"{spec}:{target.line}"
            if target.column is not None:
                spec = f"{spec}:{target.column}"
        return [self.executable, "--goto", spec]


class CursorBridge(IDEBridge):
    def __init__(self) -> None:
        super().__init__(id="cursor", display_name="Cursor", executable="cursor")

    def argv(self, target: IDETarget) -> list[str]:
        spec = str(target.path.resolve())
        if target.line is not None:
            spec = f"{spec}:{target.line}"
            if target.column is not None:
                spec = f"{spec}:{target.column}"
        return [self.executable, "--goto", spec]


class JetBrainsBridge(IDEBridge):
    def __init__(self) -> None:
        super().__init__(id="jetbrains", display_name="JetBrains IDE", executable="idea")

    def argv(self, target: IDETarget) -> list[str]:
        args: list[str] = [self.executable]
        if target.line is not None:
            args.append("--line")
            args.append(str(target.line))
            if target.column is not None:
                args.append("--column")
                args.append(str(target.column))
        args.append(str(target.path.resolve()))
        return args


class ZedBridge(IDEBridge):
    def __init__(self) -> None:
        super().__init__(id="zed", display_name="Zed", executable="zed")

    def argv(self, target: IDETarget) -> list[str]:
        # Zed: `zed PATH:LINE:COL`
        spec = str(target.path.resolve())
        if target.line is not None:
            spec = f"{spec}:{target.line}"
            if target.column is not None:
                spec = f"{spec}:{target.column}"
        return [self.executable, spec]


class NeovimBridge(IDEBridge):
    def __init__(self) -> None:
        super().__init__(id="nvim", display_name="Neovim", executable="nvim")

    def argv(self, target: IDETarget) -> list[str]:
        args: list[str] = [self.executable]
        if target.line is not None:
            args.append(f"+{target.line}")
        args.append(str(target.path.resolve()))
        return args


_BRIDGES: dict[str, IDEBridge] = {
    "vscode": VSCodeBridge(),
    "cursor": CursorBridge(),
    "jetbrains": JetBrainsBridge(),
    "zed": ZedBridge(),
    "nvim": NeovimBridge(),
}


def available_bridges() -> tuple[IDEBridge, ...]:
    return tuple(_BRIDGES.values())


def bridge_for(name: str) -> IDEBridge:
    try:
        return _BRIDGES[name.lower()]
    except KeyError as exc:
        raise IDEError(
            f"unknown IDE bridge {name!r}; try one of "
            + ", ".join(sorted(_BRIDGES.keys()))
        ) from exc


def build_open_command(
    *,
    bridge: str,
    target: IDETarget,
) -> list[str]:
    return bridge_for(bridge).argv(target)

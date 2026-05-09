"""Typed mouse + voice events for the v3.7 TUI surface (L37-2).

The event types are backend-agnostic so the CLI can plug into Rich /
prompt_toolkit / raw ANSI / a web bridge with the same handlers.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass


class MouseKind(str, enum.Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    SCROLL = "scroll"
    MOVE = "move"


class MouseButton(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    NONE = "none"


@dataclass(frozen=True)
class MouseEvent:
    kind: MouseKind
    row: int
    col: int
    button: MouseButton = MouseButton.LEFT
    delta: int = 0                 # for SCROLL: positive=up, negative=down


class VoiceKind(str, enum.Enum):
    WAKE = "wake"                  # wake-word fired
    TRANSCRIPT = "transcript"      # partial / final transcript
    SILENCE = "silence"            # detected end-of-utterance


@dataclass(frozen=True)
class VoiceEvent:
    kind: VoiceKind
    text: str = ""
    confidence: float = 0.0
    final: bool = False


__all__ = [
    "MouseButton",
    "MouseEvent",
    "MouseKind",
    "VoiceEvent",
    "VoiceKind",
]

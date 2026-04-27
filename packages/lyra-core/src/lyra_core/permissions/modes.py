"""Lyra permission modes.

See ``docs/blocks/04-permission-bridge.md`` for the full spec.

Phase 1 supports:
    - PLAN      : read-only planning (no writes at all, destructive denied)
    - RED       : failing-test writing; writes limited to ``tests/**``
    - GREEN     : implementation; writes allowed under ``src/**`` and ``tests/**``
    - REFACTOR  : free writes; destructive still ASK
    - RESEARCH  : scratchpad; writes limited to ``notes/**``
    - DEFAULT   : harness_core defaults (writes ASK)
    - ACCEPT_EDITS : harness_core ACCEPT_EDITS (edits auto, others ASK)
    - BYPASS    : anything goes (after hard-deny rules)
    - RESUME    : inherits caller's last mode (not decided at resolver layer)
"""
from __future__ import annotations

import enum


class LyraMode(str, enum.Enum):
    PLAN = "plan"
    RED = "red"
    GREEN = "green"
    REFACTOR = "refactor"
    RESEARCH = "research"
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS = "bypass"
    RESUME = "resume"

"""TDD-aware permission decision resolver.

Builds on harness_core.permissions but adds path-sensitive rules for RED /
GREEN / REFACTOR / RESEARCH. Full contract in ``docs/blocks/04-permission-bridge.md``.

Decision precedence inside this resolver (invoked by the PermissionBridge):

    1. Hard ``deny`` policy rule wins unconditionally.
    2. ``BYPASS`` mode → ALLOW (any non-denied call).
    3. Mode-specific rules:
        PLAN      → DENY all writes / destructive
        RED       → DENY writes outside tests/**, destructive ASK
        GREEN     → ALLOW writes to src/** and tests/**, destructive ASK
        REFACTOR  → ALLOW writes anywhere, destructive ASK
        RESEARCH  → ALLOW writes only to notes/**, otherwise DENY; destructive ASK
    4. Fall through to harness_core defaults (DEFAULT / ACCEPT_EDITS).
"""
from __future__ import annotations

import enum
import fnmatch
from dataclasses import dataclass
from typing import Any

from harness_core.messages import ToolCall

from .modes import LyraMode


class Decision(str, enum.Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"
    PARK = "park"  # reserved for block 04; not used in Phase 1


@dataclass
class PermissionDecision:
    decision: Decision
    reason: str = ""
    matched_rule: str | None = None


# ---------------------------------------------------------------------------
# path extraction from tool args
# ---------------------------------------------------------------------------


def _extract_path(args: dict[str, Any]) -> str | None:
    """Best-effort lookup of a path-like arg, None if none present."""
    for key in ("path", "file_path", "target", "dest"):
        v = args.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def _path_matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    # Normalise leading ``./``
    p = path.lstrip("./")
    return any(
        fnmatch.fnmatchcase(p, pat) or fnmatch.fnmatchcase(path, pat)
        for pat in patterns
    )


# Canonical path prefixes per mode.
_TESTS_PATTERNS = ("tests/**", "tests/*", "test/**", "test/*", "**/test_*.py", "**/*_test.py")
_SRC_PATTERNS = ("src/**", "src/*", "packages/**", "lib/**", "app/**")
_NOTES_PATTERNS = ("notes/**", "notes/*", "docs/notes/**", "scratch/**", ".lyra/**")


def _is_test_path(path: str) -> bool:
    return _path_matches_any(path, _TESTS_PATTERNS)


def _is_src_path(path: str) -> bool:
    return _path_matches_any(path, _SRC_PATTERNS)


def _is_notes_path(path: str) -> bool:
    return _path_matches_any(path, _NOTES_PATTERNS)


# ---------------------------------------------------------------------------
# resolver
# ---------------------------------------------------------------------------


def resolve_lyra_decision(
    call: ToolCall,
    *,
    mode: LyraMode,
    tool_writes: bool = False,
    tool_risk: str = "low",
) -> PermissionDecision:
    """Top-level entrypoint; no policy param in Phase 1 (wired at block 04)."""
    if mode == LyraMode.BYPASS:
        return PermissionDecision(Decision.ALLOW, "bypass mode")

    if mode == LyraMode.PLAN:
        if tool_writes or tool_risk in ("destructive", "unknown"):
            return PermissionDecision(
                Decision.DENY,
                f"PLAN mode denies {call.name!r} (writes={tool_writes}, risk={tool_risk})",
            )
        return PermissionDecision(Decision.ALLOW, "PLAN mode: read tool")

    if mode == LyraMode.RED:
        if tool_risk == "destructive":
            return PermissionDecision(
                Decision.ASK,
                "RED mode: destructive tools require approval",
            )
        if not tool_writes:
            return PermissionDecision(Decision.ALLOW, "RED mode: non-write tool")
        path = _extract_path(call.args)
        if path and _is_test_path(path):
            return PermissionDecision(
                Decision.ALLOW,
                f"RED mode allows write to tests/ ({path!r})",
            )
        return PermissionDecision(
            Decision.DENY,
            f"RED mode denies write outside tests/ (path={path!r})",
        )

    if mode == LyraMode.GREEN:
        if tool_risk == "destructive":
            return PermissionDecision(
                Decision.ASK, "GREEN mode: destructive tools require approval"
            )
        if not tool_writes:
            return PermissionDecision(Decision.ALLOW, "GREEN mode: non-write tool")
        path = _extract_path(call.args)
        if path and (_is_src_path(path) or _is_test_path(path)):
            return PermissionDecision(
                Decision.ALLOW,
                f"GREEN mode allows write to src/ or tests/ ({path!r})",
            )
        return PermissionDecision(
            Decision.ASK,
            f"GREEN mode: unclassified path {path!r}; approval required",
        )

    if mode == LyraMode.REFACTOR:
        if tool_risk == "destructive":
            return PermissionDecision(
                Decision.ASK, "REFACTOR mode: destructive tools require approval"
            )
        return PermissionDecision(Decision.ALLOW, "REFACTOR mode allows writes")

    if mode == LyraMode.RESEARCH:
        if tool_risk == "destructive":
            return PermissionDecision(
                Decision.ASK, "RESEARCH mode: destructive tools require approval"
            )
        if not tool_writes:
            return PermissionDecision(Decision.ALLOW, "RESEARCH mode: read tool")
        path = _extract_path(call.args)
        if path and _is_notes_path(path):
            return PermissionDecision(
                Decision.ALLOW,
                f"RESEARCH mode allows write to notes/ ({path!r})",
            )
        return PermissionDecision(
            Decision.DENY,
            f"RESEARCH mode denies write outside notes/ (path={path!r})",
        )

    # DEFAULT and ACCEPT_EDITS mirror harness_core semantics.
    if mode == LyraMode.ACCEPT_EDITS:
        if tool_risk == "destructive":
            return PermissionDecision(
                Decision.ASK, "ACCEPT_EDITS: destructive tool requires approval"
            )
        return PermissionDecision(Decision.ALLOW, "ACCEPT_EDITS: auto-allow")

    # LyraMode.DEFAULT
    if tool_writes or tool_risk in ("high", "destructive"):
        return PermissionDecision(Decision.ASK, "DEFAULT mode: write requires ask")
    return PermissionDecision(Decision.ALLOW, "DEFAULT mode: read auto-allowed")

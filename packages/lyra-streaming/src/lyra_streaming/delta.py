"""
JSON Patch (RFC 6902) diff generation and application.

Used to produce `StateDeltaEvent` payloads that carry minimal state
changes instead of full snapshots on every update.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    """RFC 6902 operation types."""

    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"
    COPY = "copy"
    TEST = "test"


_VALID_OPS = frozenset(op.value for op in OperationType)


@dataclass(frozen=True)
class Operation:
    """A single RFC 6902 JSON Patch operation.

    Attributes:
        op: The operation type (add, remove, replace, move, copy, test).
        path: JSON Pointer (RFC 6901) to the target location.
        value: The value for add / replace / test / copy / move.
        from_: The source path for move / copy operations.
    """

    op: OperationType
    path: str
    value: Any = None
    from_: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"op": self.op.value, "path": self.path}
        if self.value is not None:
            d["value"] = self.value
        if self.from_ is not None:
            d["from"] = self.from_
        return d


class PatchError(Exception):
    """Raised when a patch operation cannot be applied."""


class JSONPatch:
    """RFC 6902-compliant JSON Patch utilities.

    Provides diff generation between two dicts and application of
    operation lists to produce updated state.
    """

    # ── Diff generation ─────────────────────────────────────────────

    @staticmethod
    def generate_diff(
        old_state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Compute the minimal set of RFC 6902 operations to transform
        *old_state* into *new_state*.

        Args:
            old_state: The prior state dictionary.
            new_state: The desired state dictionary.

        Returns:
            A list of operation dicts (suitable for `StateDeltaEvent`).
        """
        operations: list[dict[str, Any]] = []

        all_keys: set[str] = set(old_state.keys()) | set(new_state.keys())

        for key in sorted(all_keys):
            pointer = f"/{key}"

            if key not in old_state and key in new_state:
                operations.append({"op": "add", "path": pointer, "value": new_state[key]})
            elif key in old_state and key not in new_state:
                operations.append({"op": "remove", "path": pointer})
            elif old_state.get(key) != new_state.get(key):
                operations.append({"op": "replace", "path": pointer, "value": new_state[key]})

        return operations

    # ── Patch application ───────────────────────────────────────────

    @staticmethod
    def apply_patch(
        state: dict[str, Any],
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply a list of RFC 6902 operations to *state*.

        Returns a **new** dictionary; the original *state* is never
        mutated.

        Args:
            state: The current state to patch.
            operations: A list of operation dicts.

        Returns:
            A new state dictionary with operations applied.

        Raises:
            PatchError: If any operation cannot be applied.
        """
        result = copy.deepcopy(state)

        for idx, op in enumerate(operations):
            op_type = op.get("op")
            path = op.get("path", "")
            value = op.get("value")
            from_path = op.get("from")

            if op_type not in _VALID_OPS:
                raise PatchError(f"Unknown operation '{op_type}' at index {idx}")

            try:
                if op_type == "add":
                    JSONPatch._apply_add(result, path, value)
                elif op_type == "remove":
                    JSONPatch._apply_remove(result, path)
                elif op_type == "replace":
                    JSONPatch._apply_replace(result, path, value)
                elif op_type == "move":
                    moved_value = JSONPatch._get_value(result, from_path)
                    JSONPatch._apply_remove(result, from_path)
                    JSONPatch._apply_add(result, path, moved_value)
                elif op_type == "copy":
                    copied_value = JSONPatch._get_value(result, from_path)
                    JSONPatch._apply_add(result, path, copied_value)
                elif op_type == "test":
                    current = JSONPatch._get_value(result, path)
                    if current != value:
                        raise PatchError(
                            f"TEST failed at '{path}': expected {value!r}, got {current!r}"
                        )
            except PatchError:
                raise
            except Exception as exc:
                raise PatchError(f"Operation {op_type} at '{path}' failed: {exc}") from exc

        return result

    # ── Internal path helpers ───────────────────────────────────────

    @staticmethod
    def _parse_path(path: str) -> list[str]:
        """Parse a JSON Pointer into path segments."""
        if path == "" or path == "/":
            return []
        # Split on '/' and unescape '~1' -> '/', '~0' -> '~'
        segments = path.split("/")[1:]  # Drop leading empty segment
        return [seg.replace("~1", "/").replace("~0", "~") for seg in segments]

    @staticmethod
    def _get_value(obj: Any, path: str) -> Any:
        """Traverse *obj* along *path* and return the value."""
        segments = JSONPatch._parse_path(path)
        if not segments:
            return obj

        current = obj
        for seg in segments:
            if isinstance(current, dict):
                if seg not in current:
                    raise PatchError(f"Path '{path}' not found: missing key '{seg}'")
                current = current[seg]
            elif isinstance(current, list):
                try:
                    idx = int(seg)
                except ValueError:
                    raise PatchError(f"Invalid list index '{seg}' in path '{path}'") from None
                if idx < 0 or idx >= len(current):
                    raise PatchError(f"Index {idx} out of range in path '{path}'")
                current = current[idx]
            else:
                raise PatchError(f"Cannot index into {type(current).__name__} at '{seg}'")
        return current

    @staticmethod
    def _apply_add(obj: Any, path: str, value: Any) -> None:
        segments = JSONPatch._parse_path(path)
        if not segments:
            raise PatchError("Cannot ADD to root")

        current = obj
        for _i, seg in enumerate(segments[:-1]):
            if isinstance(current, dict):
                current = current.setdefault(seg, {})
            elif isinstance(current, list):
                current = current[int(seg)]
            else:
                raise PatchError(f"Cannot traverse into {type(current).__name__}")

        target = segments[-1]
        if isinstance(current, dict):
            current[target] = value
        elif isinstance(current, list):
            if target == "-":
                current.append(value)
            else:
                idx = int(target)
                current.insert(idx, value)
        else:
            raise PatchError(f"Cannot ADD to {type(current).__name__}")

    @staticmethod
    def _apply_remove(obj: Any, path: str) -> None:
        segments = JSONPatch._parse_path(path)
        if not segments:
            raise PatchError("Cannot REMOVE root")

        parent: Any = obj
        for seg in segments[:-1]:
            if isinstance(parent, dict):
                parent = parent[seg]
            elif isinstance(parent, list):
                parent = parent[int(seg)]

        target = segments[-1]
        if isinstance(parent, dict):
            if target not in parent:
                raise PatchError(f"Cannot REMOVE missing key '{target}'")
            del parent[target]
        elif isinstance(parent, list):
            idx = int(target)
            if idx < 0 or idx >= len(parent):
                raise PatchError(f"REMOVE index {idx} out of range")
            del parent[idx]

    @staticmethod
    def _apply_replace(obj: Any, path: str, value: Any) -> None:
        segments = JSONPatch._parse_path(path)
        if not segments:
            raise PatchError("Cannot REPLACE root")

        parent: Any = obj
        for seg in segments[:-1]:
            if isinstance(parent, dict):
                parent = parent[seg]
            elif isinstance(parent, list):
                parent = parent[int(seg)]

        target = segments[-1]
        if isinstance(parent, dict):
            if target not in parent:
                raise PatchError(f"Cannot REPLACE missing key '{target}'")
            parent[target] = value
        elif isinstance(parent, list):
            idx = int(target)
            if idx < 0 or idx >= len(parent):
                raise PatchError(f"REPLACE index {idx} out of range")
            parent[idx] = value

    # ── Validation ──────────────────────────────────────────────────

    @staticmethod
    def validate_patch(operations: list[dict[str, Any]]) -> bool:
        """Check that a list of operations is structurally valid.

        Returns ``True`` on success.

        Raises:
            PatchError: If any operation is malformed.
        """
        for idx, op in enumerate(operations):
            if not isinstance(op, dict):
                raise PatchError(f"Operation {idx} is not a dict")

            op_type = op.get("op")
            if op_type not in _VALID_OPS:
                raise PatchError(f"Invalid op '{op_type}' at index {idx}")

            if "path" not in op:
                raise PatchError(f"Missing 'path' at index {idx}")

        return True

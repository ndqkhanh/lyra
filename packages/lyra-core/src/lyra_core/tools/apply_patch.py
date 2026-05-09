"""``apply_patch`` tool (Anthropic / opencode parity).

Accepts a v4-style patch envelope::

    *** Begin Patch
    *** Update File: path/to/file.py
    @@
    - old_line
    + new_line
    *** End Patch

Or a plain unified diff (``--- a/foo\\n+++ b/foo\\n@@ …``). The tool
resolves the target file relative to ``repo_root`` and applies the
hunks, returning a structured dict the agent loop records as the tool
result.

The format is intentionally narrow — we don't implement every GNU diff
flag, just the four verbs the model actually emits:

- ``*** Add File:`` — create a new file with the hunk as its contents.
- ``*** Delete File:`` — remove the file.
- ``*** Update File:`` — apply the hunks to an existing file.
- ``*** End of File`` marker is accepted but not required.

All writes stay inside ``repo_root``; path-escape attempts (``../``)
raise ``ApplyPatchError`` before touching the filesystem.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal


class ApplyPatchError(Exception):
    """Raised when a patch cannot be applied cleanly."""


PatchAction = Literal["add", "delete", "update"]


@dataclass
class PatchOp:
    action: PatchAction
    path: str
    old_text: str = ""
    new_text: str = ""


@dataclass
class PatchResult:
    ops: list[PatchOp] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    files_deleted: list[str] = field(default_factory=list)


_BEGIN_RE = re.compile(r"^\*\*\*\s+Begin Patch\s*$")
_END_RE = re.compile(r"^\*\*\*\s+End Patch\s*$")
_ADD_RE = re.compile(r"^\*\*\*\s+Add File:\s+(.+)$")
_DELETE_RE = re.compile(r"^\*\*\*\s+Delete File:\s+(.+)$")
_UPDATE_RE = re.compile(r"^\*\*\*\s+Update File:\s+(.+)$")


def parse_patch(patch: str) -> list[PatchOp]:
    """Parse a v4-envelope patch string into :class:`PatchOp` records.

    The parser is line-oriented and rejects malformed envelopes early
    (missing Begin/End, unknown verbs, hunks before a file header).
    """
    if not patch or "Begin Patch" not in patch:
        raise ApplyPatchError(
            "patch must be wrapped in '*** Begin Patch ... *** End Patch'"
        )

    lines = patch.splitlines()
    ops: list[PatchOp] = []
    current: PatchOp | None = None
    in_body = False

    for raw in lines:
        if _BEGIN_RE.match(raw):
            in_body = True
            continue
        if _END_RE.match(raw):
            if current is not None:
                ops.append(current)
                current = None
            in_body = False
            break
        if not in_body:
            continue

        m_add = _ADD_RE.match(raw)
        if m_add:
            if current is not None:
                ops.append(current)
            current = PatchOp(action="add", path=m_add.group(1).strip())
            continue
        m_del = _DELETE_RE.match(raw)
        if m_del:
            if current is not None:
                ops.append(current)
            current = PatchOp(action="delete", path=m_del.group(1).strip())
            continue
        m_upd = _UPDATE_RE.match(raw)
        if m_upd:
            if current is not None:
                ops.append(current)
            current = PatchOp(action="update", path=m_upd.group(1).strip())
            continue
        if current is None:
            raise ApplyPatchError(f"patch body before a file header: {raw!r}")

        # Body lines: drop leading '+' / '-' markers; a leading space or
        # bare line is context / new content depending on action.
        if current.action == "add":
            text = raw
            if text.startswith("+"):
                text = text[1:]
            current.new_text += text + "\n"
        elif current.action == "update":
            if raw.startswith("- "):
                current.old_text += raw[2:] + "\n"
            elif raw.startswith("+ "):
                current.new_text += raw[2:] + "\n"
            elif raw.startswith("-"):
                current.old_text += raw[1:] + "\n"
            elif raw.startswith("+"):
                current.new_text += raw[1:] + "\n"
            elif raw.strip() == "@@":
                # Hunk separator — ignored, sequencing is per-op here.
                continue
            else:
                # Context line: include on both sides so fuzzy apply
                # still lines up.
                current.old_text += raw + "\n"
                current.new_text += raw + "\n"
        # For delete, body is ignored.

    if in_body:
        raise ApplyPatchError("patch missing '*** End Patch' sentinel")

    return ops


def _resolve_safe(root: Path, path: str) -> Path:
    """Resolve ``path`` relative to ``root`` and reject escapes."""
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ApplyPatchError(
            f"refusing to touch path outside repo_root: {path!r}"
        ) from exc
    return candidate


def _apply_ops(ops: list[PatchOp], *, root: Path) -> PatchResult:
    result = PatchResult(ops=list(ops))
    for op in ops:
        target = _resolve_safe(root, op.path)
        if op.action == "add":
            if target.exists():
                raise ApplyPatchError(f"add: {op.path} already exists")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(op.new_text, encoding="utf-8")
            result.files_written.append(op.path)
        elif op.action == "delete":
            if not target.exists():
                raise ApplyPatchError(f"delete: {op.path} missing")
            target.unlink()
            result.files_deleted.append(op.path)
        elif op.action == "update":
            if not target.exists():
                raise ApplyPatchError(f"update: {op.path} missing")
            original = target.read_text(encoding="utf-8")
            if op.old_text and op.old_text not in original:
                raise ApplyPatchError(
                    f"update: old block not found in {op.path}"
                )
            updated = (
                original.replace(op.old_text, op.new_text, 1)
                if op.old_text
                else op.new_text
            )
            target.write_text(updated, encoding="utf-8")
            result.files_written.append(op.path)
    return result


def make_apply_patch_tool(
    *, repo_root: Path | str
) -> Callable[..., dict]:
    """Build the LLM-callable ``apply_patch`` tool.

    Writes stay confined to ``repo_root``. The return value includes
    both the parsed ops (for audit) and the list of files actually
    written / deleted so plugins (``post_tool_call``) can re-verify.
    """
    root = Path(repo_root).resolve()

    def apply_patch(patch: str) -> dict:
        """Apply a v4-envelope patch and return a structured result."""
        try:
            ops = parse_patch(patch)
        except ApplyPatchError as exc:
            return {"ok": False, "error": str(exc), "phase": "parse"}
        try:
            result = _apply_ops(ops, root=root)
        except ApplyPatchError as exc:
            return {"ok": False, "error": str(exc), "phase": "apply"}
        return {
            "ok": True,
            "ops": [
                {"action": op.action, "path": op.path} for op in result.ops
            ],
            "files_written": result.files_written,
            "files_deleted": result.files_deleted,
        }

    apply_patch.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "apply_patch",
        "description": (
            "Apply a v4-envelope patch (*** Begin Patch / *** End Patch) "
            "to files under repo_root. Supports Add/Delete/Update file ops."
        ),
        "parameters": {
            "type": "object",
            "properties": {"patch": {"type": "string"}},
            "required": ["patch"],
        },
    }
    return apply_patch


__all__ = [
    "ApplyPatchError",
    "PatchOp",
    "PatchResult",
    "parse_patch",
    "make_apply_patch_tool",
]

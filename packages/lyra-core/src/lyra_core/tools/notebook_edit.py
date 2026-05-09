"""``NotebookEdit`` tool — Jupyter ``.ipynb`` cell editor (claw-code parity).

Supports four operations on a Jupyter notebook:

* ``replace`` — replace source of an existing cell by ``cell_id`` or index.
* ``insert``  — insert a new cell at a given index (``before`` / ``after``).
* ``delete``  — remove a cell by id or index.
* ``convert`` — flip cell type between ``code`` and ``markdown``.

The tool is filesystem-scoped — it only touches files under
``repo_root`` and leaves a valid, nbformat-4.x-shaped JSON behind.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

__all__ = ["NotebookEditError", "make_notebook_edit_tool"]


class NotebookEditError(Exception):
    pass


NotebookOp = Literal["replace", "insert", "delete", "convert"]
CellType = Literal["code", "markdown"]


@dataclass
class _LoadedNotebook:
    path: Path
    data: dict[str, Any]

    @property
    def cells(self) -> list[dict[str, Any]]:
        return self.data.setdefault("cells", [])


def _resolve(repo_root: Path, relative: str) -> Path:
    base = repo_root.resolve()
    target = (base / relative).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise NotebookEditError(
            f"refusing NotebookEdit outside repo_root: {relative}"
        ) from exc
    if not target.exists():
        raise NotebookEditError(f"notebook not found: {relative}")
    if target.suffix != ".ipynb":
        raise NotebookEditError(f"not a notebook: {relative}")
    return target


def _load(path: Path) -> _LoadedNotebook:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NotebookEditError(f"invalid notebook JSON: {exc}") from exc
    if not isinstance(data, dict) or "cells" not in data:
        raise NotebookEditError("not a valid nbformat notebook (missing 'cells')")
    return _LoadedNotebook(path=path, data=data)


def _find_cell(cells: list[dict[str, Any]], *, cell_id: str | None,
               index: int | None) -> int:
    if cell_id is not None:
        for i, c in enumerate(cells):
            if c.get("id") == cell_id:
                return i
        raise NotebookEditError(f"cell_id not found: {cell_id}")
    if index is not None:
        if index < 0 or index >= len(cells):
            raise NotebookEditError(
                f"cell index {index} out of range (len={len(cells)})"
            )
        return index
    raise NotebookEditError("either cell_id or index is required")


def _make_cell(cell_type: CellType, source: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "cell_type": cell_type,
        "metadata": {},
        "source": source.splitlines(keepends=True) if source else [],
    }
    if cell_type == "code":
        base["outputs"] = []
        base["execution_count"] = None
    return base


def make_notebook_edit_tool(*, repo_root: Path | str) -> Callable[..., dict]:
    root = Path(repo_root).resolve()

    def notebook_edit(
        *,
        notebook_path: str,
        operation: NotebookOp,
        cell_id: str | None = None,
        index: int | None = None,
        source: str | None = None,
        cell_type: CellType = "code",
        position: Literal["before", "after"] = "after",
    ) -> dict:
        try:
            nb = _load(_resolve(root, notebook_path))
            cells = nb.cells

            if operation == "replace":
                i = _find_cell(cells, cell_id=cell_id, index=index)
                if source is None:
                    raise NotebookEditError("replace requires 'source'")
                cells[i] = _make_cell(cells[i].get("cell_type", "code"), source)

            elif operation == "insert":
                if source is None:
                    raise NotebookEditError("insert requires 'source'")
                if cell_id is None and index is None:
                    cells.append(_make_cell(cell_type, source))
                else:
                    anchor = _find_cell(cells, cell_id=cell_id, index=index)
                    at = anchor if position == "before" else anchor + 1
                    cells.insert(at, _make_cell(cell_type, source))

            elif operation == "delete":
                i = _find_cell(cells, cell_id=cell_id, index=index)
                cells.pop(i)

            elif operation == "convert":
                i = _find_cell(cells, cell_id=cell_id, index=index)
                current_source = "".join(cells[i].get("source") or [])
                cells[i] = _make_cell(cell_type, current_source)

            else:
                raise NotebookEditError(f"unknown NotebookEdit op: {operation}")

            nb.path.write_text(
                json.dumps(nb.data, indent=1, ensure_ascii=False),
                encoding="utf-8",
            )
        except NotebookEditError as exc:
            return {"ok": False, "error": str(exc)}

        return {"ok": True, "operation": operation, "path": notebook_path}

    notebook_edit.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "notebook_edit",
        "description": (
            "Edit a Jupyter notebook cell in place: replace / insert / "
            "delete / convert. Targets are referenced by cell_id or index."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "notebook_path": {"type": "string"},
                "operation": {
                    "type": "string",
                    "enum": ["replace", "insert", "delete", "convert"],
                },
                "cell_id": {"type": "string"},
                "index": {"type": "integer"},
                "source": {"type": "string"},
                "cell_type": {
                    "type": "string",
                    "enum": ["code", "markdown"],
                    "default": "code",
                },
                "position": {
                    "type": "string",
                    "enum": ["before", "after"],
                    "default": "after",
                },
            },
            "required": ["notebook_path", "operation"],
        },
    }
    return notebook_edit

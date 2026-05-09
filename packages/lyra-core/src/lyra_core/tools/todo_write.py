"""LLM-callable ``TodoWrite`` tool — Claude-Code / opencode parity.

Schema mirrors the upstream reference:

.. code-block:: json

    {
      "name": "TodoWrite",
      "parameters": {
        "type": "object",
        "properties": {
          "todos": {"type": "array", "items": {"...": "..."}},
          "merge": {"type": "boolean", "default": false}
        },
        "required": ["todos"]
      }
    }

Behaviour:

- ``merge=False`` (default) *replaces* the entire list.
- ``merge=True`` upserts by ``id`` — for ids already present the
  incoming fields patch the existing record; new ids are appended;
  un-referenced ids survive untouched.
- Every todo must carry ``id`` + ``content`` + ``status``. Status is
  one of ``{"pending", "in_progress", "completed", "cancelled"}``.

Atomicity is delegated to :class:`lyra_core.store.TodoStore` which
writes via ``<path>.tmp → rename`` so the on-disk list is never
observed in a half-written state.
"""
from __future__ import annotations

from typing import Any, Callable

from ..store.todo_store import TodoStore

_ALLOWED_STATUS: frozenset[str] = frozenset(
    {"pending", "in_progress", "completed", "cancelled"}
)


def _validate(todo: dict) -> dict:
    if "id" not in todo or not todo["id"]:
        raise ValueError(f"todo missing 'id': {todo!r}")
    status = todo.get("status")
    if status is not None and status not in _ALLOWED_STATUS:
        raise ValueError(
            f"bad status {status!r}; allowed: {sorted(_ALLOWED_STATUS)}"
        )
    return dict(todo)


def _merge_todos(existing: list[dict], incoming: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {t["id"]: dict(t) for t in existing}
    order: list[str] = [t["id"] for t in existing]
    for patch in incoming:
        tid = patch["id"]
        if tid in by_id:
            by_id[tid].update({k: v for k, v in patch.items() if k != "id" and v is not None})
        else:
            by_id[tid] = dict(patch)
            order.append(tid)
    return [by_id[tid] for tid in order]


def make_todo_write_tool(*, store: TodoStore) -> Callable[..., dict]:
    """Build the LLM-callable ``TodoWrite`` tool bound to ``store``."""

    def todo_write(
        *,
        todos: list[dict],
        merge: bool = False,
    ) -> dict:
        if not isinstance(todos, list):
            raise TypeError(f"todos must be a list, got {type(todos).__name__}")
        validated = [_validate(dict(t)) for t in todos]

        if merge:
            existing = store.load()
            combined = _merge_todos(existing, validated)
        else:
            combined = validated

        store.save(combined)
        return {"todos": combined, "count": len(combined)}

    todo_write.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "TodoWrite",
        "description": (
            "Create or update the session todo list. merge=true upserts "
            "by id; merge=false (default) replaces the list outright."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "content": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": sorted(_ALLOWED_STATUS),
                            },
                        },
                        "required": ["id"],
                    },
                },
                "merge": {"type": "boolean", "default": False},
            },
            "required": ["todos"],
        },
    }
    return todo_write


__all__ = ["make_todo_write_tool"]

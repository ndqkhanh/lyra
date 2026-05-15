"""EditRecorder — append-only log of (agent_output, user_edit) pairs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

from .types import EditEvent


@dataclass
class EditRecorder:
    """Append-only log of user edits.

    >>> recorder = EditRecorder()
    >>> e = recorder.record(
    ...     agent_output="hello world",
    ...     user_edit="hi world",
    ...     user_id="alice",
    ... )
    >>> len(recorder)
    1
    """

    _edits: list[EditEvent] = field(default_factory=list)

    def record(
        self,
        *,
        agent_output: str,
        user_edit: str,
        user_id: str,
        context: Optional[dict] = None,
    ) -> EditEvent:
        e = EditEvent.create(
            agent_output=agent_output,
            user_edit=user_edit,
            user_id=user_id,
            context=context,
        )
        self._edits.append(e)
        return e

    def all(self) -> list[EditEvent]:
        return list(self._edits)

    def for_user(self, user_id: str) -> list[EditEvent]:
        return [e for e in self._edits if e.user_id == user_id]

    def recent(self, *, n: int) -> list[EditEvent]:
        if n <= 0:
            return []
        return self._edits[-n:]

    def filter(
        self,
        *,
        user_id: Optional[str] = None,
        since_timestamp: Optional[float] = None,
        until_timestamp: Optional[float] = None,
    ) -> list[EditEvent]:
        out: list[EditEvent] = []
        for e in self._edits:
            if user_id is not None and e.user_id != user_id:
                continue
            if since_timestamp is not None and e.timestamp < since_timestamp:
                continue
            if until_timestamp is not None and e.timestamp > until_timestamp:
                continue
            out.append(e)
        return out

    def __len__(self) -> int:
        return len(self._edits)

    def __iter__(self) -> Iterator[EditEvent]:
        return iter(self._edits)


__all__ = ["EditRecorder"]

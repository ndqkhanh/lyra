"""Per-user 3-principle constitution data model + registry.

The data model is intentionally minimal — three to five principles per user,
each a short natural-language imperative with optional weight + rationale.
Real deployments wire the registry to a database; in-process is the test +
cold-start substrate.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Iterable, Optional


@dataclass(frozen=True)
class Principle:
    """One principle in a constitution.

    >>> p = Principle(text="Always cite peer-reviewed primary sources.", weight=1.0)
    >>> p.text.startswith("Always")
    True
    """

    text: str
    weight: float = 1.0
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.text or not self.text.strip():
            raise ValueError("Principle.text must be non-empty")
        if not 0.0 <= self.weight <= 5.0:
            raise ValueError(f"Principle.weight must be in [0, 5], got {self.weight}")


@dataclass(frozen=True)
class Constitution:
    """A user's constitution — typically 3 principles, max 5.

    Immutable; updates produce new instances via :meth:`with_principle` /
    :meth:`without_principle` / :meth:`bumped`.
    """

    user_id: str
    principles: tuple[Principle, ...] = ()
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.user_id or not self.user_id.strip():
            raise ValueError("user_id must be non-empty")
        if len(self.principles) > 5:
            raise ValueError(
                f"constitutions are capped at 5 principles; got {len(self.principles)}"
            )

    def render(self, *, header: str = "User constitution:") -> str:
        """Produce system-prompt-ready text.

        Renders principles in weight-descending order; preserves original
        order on weight ties for stability.
        """
        if not self.principles:
            return f"{header} (none specified)"
        sorted_p = sorted(
            enumerate(self.principles),
            key=lambda iw: (-iw[1].weight, iw[0]),
        )
        lines = [header]
        for i, (_, p) in enumerate(sorted_p, start=1):
            lines.append(f"{i}. {p.text}")
        return "\n".join(lines)

    def with_principle(
        self,
        principle: Principle,
        *,
        replace_text: Optional[str] = None,
    ) -> "Constitution":
        """Add a principle (or replace one matching ``replace_text``).

        Returns a new Constitution with version + 1.
        """
        if replace_text is not None:
            new_principles = tuple(
                principle if p.text == replace_text else p for p in self.principles
            )
        else:
            new_principles = self.principles + (principle,)
        return replace(
            self,
            principles=new_principles,
            version=self.version + 1,
            updated_at=time.time(),
        )

    def without_principle(self, *, text: str) -> "Constitution":
        """Remove the principle whose text matches; returns new instance."""
        new_principles = tuple(p for p in self.principles if p.text != text)
        if len(new_principles) == len(self.principles):
            return self  # nothing to remove
        return replace(
            self,
            principles=new_principles,
            version=self.version + 1,
            updated_at=time.time(),
        )

    def bumped(self, *, text: str, delta: float) -> "Constitution":
        """Adjust the weight of a principle. Used by edit-signal drift updates."""
        new_principles: list[Principle] = []
        changed = False
        for p in self.principles:
            if p.text == text:
                new_weight = max(0.0, min(5.0, p.weight + delta))
                new_principles.append(
                    Principle(text=p.text, weight=new_weight, rationale=p.rationale)
                )
                changed = True
            else:
                new_principles.append(p)
        if not changed:
            return self
        return replace(
            self,
            principles=tuple(new_principles),
            version=self.version + 1,
            updated_at=time.time(),
        )

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "version": self.version,
            "principles": [
                {"text": p.text, "weight": p.weight, "rationale": p.rationale}
                for p in self.principles
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def suggest_principle_from_edit(
    *,
    original: str,
    edited: str,
    rationale_template: str = "Inferred from user edit on {date}.",
) -> Optional[Principle]:
    """Naive PRELUDE/CIPHER-style principle inference from an edit pair.

    Heuristic only — production wires an LM-backed inferer. The default detects
    *structural* edits (length delta) and emits a placeholder principle the
    operator can refine. Returns None if the edit is too small to infer from.
    """
    if not original or not edited:
        return None
    delta = len(edited) - len(original)
    if abs(delta) < 20:
        return None  # too small a change to draw a principle from
    if delta > 0 and edited.startswith(original[:20]):
        text = "User adds detail to short outputs; default to verbose responses."
    elif delta < 0 and original.startswith(edited[:20]):
        text = "User trims long outputs; default to terse responses."
    else:
        text = "User restructures outputs; revisit format defaults."
    return Principle(
        text=text,
        weight=0.5,  # low-confidence inference; operator should review
        rationale=rationale_template.format(date=time.strftime("%Y-%m-%d")),
    )


@dataclass
class ConstitutionRegistry:
    """In-memory constitution store keyed by user_id.

    Production wires to a database; in-process is the test + cold-start
    substrate. Drift updates are delivered through :meth:`update_for_edit`
    which appends an inferred principle to the user's constitution.
    """

    _store: dict[str, Constitution] = field(default_factory=dict)

    def get(self, user_id: str) -> Optional[Constitution]:
        return self._store.get(user_id)

    def get_or_create(self, user_id: str, *, default_principles: Iterable[Principle] = ()) -> Constitution:
        existing = self._store.get(user_id)
        if existing is not None:
            return existing
        c = Constitution(user_id=user_id, principles=tuple(default_principles))
        self._store[user_id] = c
        return c

    def put(self, constitution: Constitution) -> None:
        self._store[constitution.user_id] = constitution

    def update_for_edit(
        self,
        *,
        user_id: str,
        original: str,
        edited: str,
    ) -> Optional[Constitution]:
        """Infer a principle from an edit pair; append to user's constitution.

        Returns the new constitution if a principle was inferred, None otherwise.
        Caps the constitution at 5 principles; if at cap, drops the
        lowest-weight existing principle to make room.
        """
        suggested = suggest_principle_from_edit(original=original, edited=edited)
        if suggested is None:
            return None
        current = self.get_or_create(user_id)
        # Already present? Bump weight instead of duplicating.
        if any(p.text == suggested.text for p in current.principles):
            updated = current.bumped(text=suggested.text, delta=0.1)
            self._store[user_id] = updated
            return updated
        # At cap? Drop the lowest-weight principle.
        if len(current.principles) >= 5:
            lowest = min(current.principles, key=lambda p: p.weight)
            current = current.without_principle(text=lowest.text)
        updated = current.with_principle(suggested)
        self._store[user_id] = updated
        return updated

    def remove(self, user_id: str) -> bool:
        """Drop a user's constitution. Returns True if it was present."""
        if user_id in self._store:
            del self._store[user_id]
            return True
        return False

    def __len__(self) -> int:
        return len(self._store)


__all__ = [
    "Constitution",
    "ConstitutionRegistry",
    "Principle",
    "suggest_principle_from_edit",
]

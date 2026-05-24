"""ContinuousLearner — orchestrate recorder + extractor + memory + lattice.

One :meth:`learn` call:

    1. Pulls (optionally filtered) edits from the :class:`EditRecorder`.
    2. Runs the :class:`PreferenceExtractor`.
    3. For each new preference: writes a PROCEDURAL :class:`MemoryItem`
       with the rule as content (so retrieval surfaces it on relevant
       future tasks); namespace = ``user_id``.
    4. Optionally emits a witness on the :class:`WitnessLattice`.

Returns a :class:`LearningReport` describing what was learned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..memory_store import MemoryKind, MemoryStore
from ..provenance import WitnessLattice
from .extractor import HeuristicExtractor
from .recorder import EditRecorder
from .types import LearnedPreference, LearningReport, PreferenceExtractor


@dataclass
class ContinuousLearner:
    """Periodic preference-extraction job over an :class:`EditRecorder`.

    >>> recorder = EditRecorder()
    >>> learner = ContinuousLearner(recorder=recorder)
    >>> report = learner.learn()
    >>> report.n_preferences_learned
    0
    """

    recorder: EditRecorder
    extractor: PreferenceExtractor = field(default_factory=HeuristicExtractor)
    memory: Optional[MemoryStore] = None
    lattice: Optional[WitnessLattice] = None
    agent_id: str = "continuous-learner"

    def learn(
        self,
        *,
        user_id: Optional[str] = None,
        since_timestamp: Optional[float] = None,
    ) -> LearningReport:
        """Run extraction over the recorder; record outputs.

        ``user_id`` and ``since_timestamp`` filter the input edits — useful
        for incremental learning per user.
        """
        edits = self.recorder.filter(
            user_id=user_id,
            since_timestamp=since_timestamp,
        )
        if not edits:
            return LearningReport(n_edits_examined=0, n_preferences_learned=0)

        preferences = self.extractor.extract(edits)

        memory_ids: list[str] = []
        witness_ids: list[str] = []

        for pref in preferences:
            mid = self._record_memory(pref)
            if mid:
                memory_ids.append(mid)
            wid = self._record_witness(pref)
            if wid:
                witness_ids.append(wid)

        return LearningReport(
            n_edits_examined=len(edits),
            n_preferences_learned=len(preferences),
            preferences=tuple(preferences),
            preference_witness_ids=tuple(witness_ids),
            preference_memory_ids=tuple(memory_ids),
        )

    # --- Internals -------------------------------------------------------

    def _record_memory(self, pref: LearnedPreference) -> str:
        if self.memory is None:
            return ""
        item = self.memory.write(
            kind=MemoryKind.PROCEDURAL,
            content=pref.rule,
            namespace=pref.user_id,
            importance=pref.confidence,
            tags=tuple(set(pref.tags) | {"learned-preference"}),
            metadata={
                "preference_id": pref.preference_id,
                "n_supporting_edits": pref.n_supporting_edits,
                **pref.metadata,
            },
        )
        return item.item_id

    def _record_witness(self, pref: LearnedPreference) -> str:
        if self.lattice is None:
            return ""
        w = self.lattice.record_decision(
            agent_id=self.agent_id,
            action="learn_preference",
            fingerprint=pref.preference_id,
        )
        return w.witness_id


__all__ = ["ContinuousLearner"]

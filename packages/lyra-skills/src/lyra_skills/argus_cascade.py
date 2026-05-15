"""Lyra-facing wrapper around Argus's :class:`HostAdapter`.

Argus ships the full router cascade, governance ledgers, and refinement
loop as a library. ``LyraArgusCascade`` is the Lyra-shaped facade: it
indexes :class:`SkillManifest` objects (Lyra's native skill type) and
returns :class:`SkillManifest` results, so existing call-sites don't
need to learn Argus's catalog vocabulary.

State lives under :func:`~lyra_core.auth.store.lyra_home` ``/ argus`` by
default — telemetry, tombstones, content hashes, vendor reputation. The
constructor accepts an explicit ``state_dir`` for tests.

Three entry-point modes mirror the Argus contract verbatim:

* ``"auto"`` — full cascade, size-aware tier gating
* ``"keyword"`` — Tier 1 BM25 only (deterministic, cheap)
* ``"semantic"`` — Tier 0 + Tier 2 (+ Tier 3 on ambiguity)
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from harness_skill_router import (
    Budget,
    EventKind,
    EvolveDecision,
    FilesystemWatcher,
    HostAdapter,
    LocalDirectoryAdapter,
    ProposalKind,
    PullSummary,
    RankedSkill,
    RouterDecision,
    RouterMode,
    SkillEvolver,
    SkillProposal,
    SkillSource,
    TelemetryDrivenPromoter,
    TelemetryEvent,
    TelemetryPromotionDecision,
    TelemetryPromotionPolicy,
    TrustTier,
)
from harness_skill_router.refine import RefinementResult

from .argus_bridge import (
    argus_skill_to_manifest,
    manifest_to_argus_skill,
)
from .loader import SkillManifest


def default_state_dir() -> Path:
    """Resolve ``$LYRA_HOME/argus``; tests override via the env var."""
    # Imported lazily so unit tests can monkeypatch ``$LYRA_HOME`` first.
    from lyra_core.auth.store import lyra_home

    return lyra_home() / "argus"


@dataclass(frozen=True)
class CascadePick:
    """One ranked result with the original manifest re-attached.

    ``score`` and ``reason`` come from the cascade trace; ``manifest``
    is the same Lyra object the caller indexed, so downstream
    consumers (chat-mode injection, ``lyra skill route``) keep
    operating on Lyra's native type.
    """

    manifest: SkillManifest
    score: float
    reason: str

    @classmethod
    def from_ranked(
        cls,
        ranked: RankedSkill,
        manifest: SkillManifest,
    ) -> "CascadePick":
        return cls(manifest=manifest, score=ranked.score, reason=ranked.reason)


@dataclass
class CascadeResult:
    """Lyra-shaped return from :meth:`LyraArgusCascade.route`.

    Wraps :class:`harness_skill_router.RouterDecision` so callers can
    iterate over :class:`CascadePick` objects without unpacking the
    Argus types, while still surfacing the full reasoning trace and
    bright-line list when audit code wants them.
    """

    query: str
    picks: tuple[CascadePick, ...]
    decision: RouterDecision

    @property
    def top(self) -> Optional[CascadePick]:
        return self.picks[0] if self.picks else None

    @property
    def is_empty(self) -> bool:
        return not self.picks

    @property
    def bright_lines_tripped(self) -> tuple[str, ...]:
        return self.decision.bright_lines_tripped

    @property
    def total_elapsed_ms(self) -> float:
        return self.decision.trace.total_elapsed_ms

    @property
    def total_cost_usd(self) -> float:
        return self.decision.trace.total_cost_usd

    @property
    def tier_names(self) -> tuple[str, ...]:
        return self.decision.trace.tier_names


class LyraArgusCascade:
    """Lyra-shaped wrapper bundling Argus's full surface.

    Owns one :class:`HostAdapter` plus a manifest registry so route
    results can be projected back to :class:`SkillManifest`. All
    Argus capabilities are exposed via thin Lyra-typed methods —
    callers never need to import from ``harness_skill_router``
    unless they want the raw :class:`RouterDecision`.
    """

    def __init__(
        self,
        *,
        state_dir: Path | str | None = None,
        harness_name: str = "lyra",
        source_default: SkillSource = SkillSource.LOCAL_AUTHORED,
        target_tier: TrustTier = TrustTier.T_REVIEWED,
    ) -> None:
        self._state_dir = Path(state_dir) if state_dir else default_state_dir()
        self.host = HostAdapter(
            state_dir=self._state_dir,
            harness_name=harness_name,
            source_default=source_default,
            target_tier=target_tier,
        )
        self._manifests: dict[str, SkillManifest] = {}

    # --- ingestion ------------------------------------------------------

    def index_manifests(
        self,
        manifests: Iterable[SkillManifest],
        *,
        source: SkillSource | None = None,
        trust_tier: TrustTier | None = None,
    ) -> int:
        """Add or replace every manifest in the catalog. Returns the count added."""
        eff_source = source or self.host.source_default
        added = 0
        for manifest in manifests:
            skill = manifest_to_argus_skill(
                manifest, source=eff_source, trust_tier=trust_tier,
            )
            self.host.catalog.add(skill)
            self._manifests[manifest.id] = manifest
            added += 1
        return added

    def import_directory(
        self,
        root: Path | str,
        *,
        rebuild_manifest_cache: bool = True,
    ) -> PullSummary:
        """Import every ``SKILL.md`` under *root* through Argus's A8 gates.

        Set ``rebuild_manifest_cache`` to ``False`` only when callers
        plan to register their own :class:`SkillManifest` views
        afterwards (e.g. when the manifests already live in memory
        from :func:`load_skills`).
        """
        adapter = LocalDirectoryAdapter(
            root=Path(root),
            name=f"{self.host.harness_name}-local",
            source=self.host.source_default,
        )
        summary = self.host.fetcher.pull(adapter)
        if rebuild_manifest_cache:
            self._refresh_manifest_cache()
        return summary

    def retract(self, skill_id: str, *, reason: str) -> None:
        """Tombstone a skill (Argus failure mode F-24) and forget the manifest."""
        self.host.retract(skill_id, reason=reason)
        self._manifests.pop(skill_id, None)

    # --- routing -------------------------------------------------------

    def route(
        self,
        query: str,
        *,
        mode: str | RouterMode = RouterMode.AUTO,
        top_k: int | None = None,
        budget: Budget | None = None,
    ) -> CascadeResult:
        """Run the cascade and project the picks back to :class:`SkillManifest`.

        Pass ``budget`` to cap this single call's cost / latency. The
        override applies to every active tier for the duration of the
        call only; concurrent callers and subsequent invocations are
        not affected.
        """
        decision = self.host.route(query, mode=mode, top_k=top_k, budget=budget)
        picks = tuple(self._project_picks(decision.picks))
        return CascadeResult(query=query, picks=picks, decision=decision)

    def navigate(self, query: str, *, top_k: int = 5) -> CascadeResult:
        """Tier-4 hierarchical navigation; requires a wired taxonomy."""
        decision = self.host.navigate(query, top_k=top_k)
        picks = tuple(self._project_picks(decision.picks))
        return CascadeResult(query=query, picks=picks, decision=decision)

    # --- telemetry -----------------------------------------------------

    def record_activation(
        self,
        skill_id: str,
        *,
        query: str = "",
        score: float = 0.0,
        detail: str = "",
    ) -> TelemetryEvent:
        """Emit a SKILL_ACTIVATED event for *skill_id* into the Argus ledger."""
        return self.host.telemetry.emit(
            EventKind.SKILL_ACTIVATED,
            skill_name=skill_id,
            query=query,
            score=score,
            success=True,
            detail=detail,
        )

    def record_outcome(
        self,
        skill_id: str,
        *,
        success: bool,
        query: str = "",
        score: float = 0.0,
        elapsed_ms: float = 0.0,
        detail: str = "",
    ) -> TelemetryEvent:
        """Emit a SKILL_EXECUTED (success) or SKILL_REJECTED (failure) event.

        Wire this from any layer that observes whether the activated
        skill actually produced a useful turn — chat loop, eval harness,
        the routine system. Argus's drift detector and telemetry-aware
        re-ranker both consume these events.
        """
        kind = EventKind.SKILL_EXECUTED if success else EventKind.SKILL_REJECTED
        return self.host.telemetry.emit(
            kind,
            skill_name=skill_id,
            query=query,
            score=score,
            success=success,
            elapsed_ms=elapsed_ms,
            detail=detail,
        )

    @property
    def telemetry_path(self) -> Path:
        return self.host.telemetry.path

    # --- trust-tier promotion (telemetry-driven) ----------------------

    def evaluate_promotions(
        self,
        policy: TelemetryPromotionPolicy | None = None,
    ) -> tuple[TelemetryPromotionDecision, ...]:
        """Run the telemetry-driven promoter across the catalog.

        The default policy promotes any skill with five successful
        executions in the last fortnight to ``T_REVIEWED`` and demotes
        any skill whose miss rate clears 40 % over at least three
        samples. Pass an explicit :class:`TelemetryPromotionPolicy`
        for deployment-specific thresholds.
        """
        eff_policy = policy or TelemetryPromotionPolicy()
        promoter = TelemetryDrivenPromoter(self.host.telemetry)
        return promoter.evaluate(self.host.catalog.all(), eff_policy)

    def apply_promotions(
        self,
        decisions: Iterable[TelemetryPromotionDecision],
    ) -> int:
        """Apply telemetry-driven decisions through the trust gate.

        Returns the number of skills whose ``trust_tier`` changed.
        Promotion decisions still pass through tombstone + drift
        checks; demotions are unconditional. Updated skills are
        re-added to the catalog so subsequent ``route()`` calls see
        the new tiers.
        """
        skills = self.host.catalog.all()
        updated = self.host.tier_manager.apply_telemetry_promotions(
            skills, decisions,
        )
        changed = 0
        for prior, after in zip(skills, updated):
            if after.trust_tier is not prior.trust_tier:
                self.host.catalog.add(after)
                self._manifests[after.name] = argus_skill_to_manifest(after)
                changed += 1
        return changed

    # --- self-evolution ----------------------------------------------

    @property
    def evolver(self) -> SkillEvolver:
        """Lazily-built :class:`SkillEvolver` bound to this host's ledgers."""
        cached = getattr(self, "_evolver", None)
        if cached is None:
            cached = SkillEvolver(
                catalog=self.host.catalog,
                tombstones=self.host.tombstones,
                tier_manager=self.host.tier_manager,
                telemetry=self.host.telemetry,
                scanner=self.host.scanner,
                rewriter=self.host.description_rewriter,
            )
            self._evolver = cached
        return cached

    def propose_skill(
        self,
        manifest: SkillManifest,
        *,
        kind: ProposalKind = ProposalKind.CREATE,
        reason: str = "",
        prior_sha256: str = "",
    ) -> EvolveDecision:
        """Submit an agent-authored :class:`SkillManifest` to the evolver.

        On accept, the new skill lands in the catalog at ``T_SCANNED``
        and a :class:`SkillManifest` is also added to the local
        manifest cache so subsequent :meth:`route` calls return the
        Lyra-shaped view. Promotion past ``T_SCANNED`` happens via
        telemetry through :meth:`evaluate_promotions`.
        """
        proposal = SkillProposal(
            name=manifest.id,
            description=manifest.description,
            body=manifest.body,
            when_to_use="\n".join(manifest.keywords),
            kind=kind,
            reason=reason,
            prior_sha256=prior_sha256,
            paths=tuple(manifest.applies_to),
        )
        decision = self.evolver.propose(proposal)
        if decision.accepted and decision.skill is not None:
            self._manifests[manifest.id] = manifest
        return decision

    # --- hot reload ---------------------------------------------------

    def enable_watch(
        self,
        root: Path | str,
        *,
        debounce_ms: int = 250,
        poll_interval_s: float = 0.25,
        watcher: FilesystemWatcher | None = None,
    ) -> FilesystemWatcher:
        """Watch *root* for SKILL.md changes and re-import on edits.

        The default polling watcher fingerprints every ``SKILL.md``
        under *root* every ``poll_interval_s`` seconds and triggers a
        refresh once the change has settled for ``debounce_ms``.
        Re-imports rebuild the manifest cache so :meth:`route` results
        reflect the new content.
        """
        return self.host.enable_watch(
            root,
            debounce_ms=debounce_ms,
            poll_interval_s=poll_interval_s,
            watcher=watcher,
        )

    def disable_watch(self, root: Path | str) -> bool:
        return self.host.disable_watch(root)

    def disable_all_watchers(self) -> None:
        self.host.disable_all_watchers()

    # --- governance / refinement --------------------------------------

    def heartbeat(self) -> RefinementResult:
        """Run one A6 refinement pass — drift + telemetry events."""
        return self.host.heartbeat()

    def quality_score(
        self,
        skill_ids: Iterable[str] | None = None,
    ) -> Any:
        """Run the A7 description-quality scorer over the catalog."""
        if skill_ids is None:
            return self.host.quality_score()
        skills = [
            s for s in (
                self.host.catalog.get(name) for name in skill_ids
            )
            if s is not None
        ]
        return self.host.quality_score(skills)

    # --- introspection -------------------------------------------------

    def loadable_count(self) -> int:
        return self.host.catalog.loadable_count()

    def __len__(self) -> int:
        return len(self.host.catalog)

    @property
    def state_dir(self) -> Path:
        return self._state_dir

    def manifest_for(self, skill_id: str) -> Optional[SkillManifest]:
        """Return the cached manifest, or rebuild it from the Argus skill."""
        cached = self._manifests.get(skill_id)
        if cached is not None:
            return cached
        skill = self.host.catalog.get(skill_id)
        if skill is None:
            return None
        manifest = argus_skill_to_manifest(skill)
        self._manifests[skill_id] = manifest
        return manifest

    # --- internal ------------------------------------------------------

    def _project_picks(
        self, ranked: Sequence[RankedSkill],
    ) -> Iterable[CascadePick]:
        for r in ranked:
            manifest = self.manifest_for(r.name)
            if manifest is None:
                continue
            yield CascadePick.from_ranked(r, manifest)

    def _refresh_manifest_cache(self) -> None:
        for skill in self.host.catalog.all():
            if skill.name in self._manifests:
                continue
            self._manifests[skill.name] = argus_skill_to_manifest(skill)


__all__ = [
    "CascadePick",
    "CascadeResult",
    "LyraArgusCascade",
    "default_state_dir",
]

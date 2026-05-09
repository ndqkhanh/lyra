"""Pre-warm the prompt-cache coordinator before fanning out subagents.

When ``N`` sibling subagents are about to read the same shared
document (a plan artefact, a SOUL.md, an L2 context bundle), the
naive flow has each subagent's first LLM call race to be the cache
*write* — only the winner saves money; the rest pay full price for
the prefix until the second turn.

This helper closes that gap. Call ``prewarm_for_specs(...)`` once on
the parent thread *before* :meth:`SubagentOrchestrator.run_parallel`
fans out, and the coordinator records a single write up front. Every
sibling worker that subsequently asks the coordinator for the same
``(provider, shared_text)`` pair gets a hit, splices in the
provider directive, and the provider serves the prefix from cache.

This module is **import-light**: pulling in
:mod:`lyra_core.providers.prompt_cache` is the only extra dep, and
it pulls no transitive provider client. The orchestrator itself
stays LLM-free.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lyra_core.providers.prompt_cache import (
    CacheStatus,
    PromptCacheAnchor,
    PromptCacheCoordinator,
    default_coordinator,
)


@dataclass(frozen=True)
class SharedPromptDescriptor:
    """The bundle of text every sibling subagent will see verbatim.

    The helper hashes ``shared_text`` and registers a single anchor
    per ``(provider, digest)`` pair. Subagents that read the *same*
    ``shared_text`` on the *same* provider will all hit the same
    anchor.

    Attributes:
        shared_text: The byte-identical prefix every sibling will
            send to the provider — typically the system prompt + plan
            artefact + any pinned context. The coordinator hashes
            this; even one trailing whitespace difference means a
            cache miss.
        provider: Provider id matching one registered with
            :func:`lyra_core.providers.prompt_cache.register_adapter`
            ("anthropic", "openai", "deepseek", "gemini", or any
            third-party id).
        scope_ids: Optional list of subagent scope ids this anchor
            applies to. Pure documentation today (the coordinator
            doesn't enforce scope), useful for ``/cache stats`` and
            for plugins that want to override per-scope behaviour.
    """

    shared_text: str
    provider: str
    scope_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PrewarmResult:
    """What the helper hands back. Surfaced in HIR + ``/cache stats``."""

    descriptor: SharedPromptDescriptor
    status: CacheStatus
    anchor: PromptCacheAnchor | None
    sibling_count: int

    @property
    def is_active(self) -> bool:
        """``True`` when an anchor was created or reused for siblings to hit."""
        return self.status is not CacheStatus.SKIP


def prewarm_for_specs(
    descriptor: SharedPromptDescriptor,
    *,
    sibling_count: int,
    coordinator: PromptCacheCoordinator | None = None,
) -> PrewarmResult:
    """Register the shared prefix once before sibling subagents fan out.

    Args:
        descriptor: The shared-text bundle every sibling will read.
        sibling_count: How many subagents are about to spawn against
            this descriptor. Used purely for telemetry; passing the
            wrong number doesn't break correctness, it just makes the
            ``/cache stats`` accounting noisy.
        coordinator: Override for tests. Production callers leave this
            ``None`` so the process-global
            :func:`lyra_core.providers.prompt_cache.default_coordinator`
            is used.

    Returns:
        :class:`PrewarmResult` carrying the anchor (when one was
        created or reused) and the status — ``WRITE`` on the first
        call for a new digest, ``HIT`` if a parallel parent already
        warmed the same digest, ``SKIP`` if the prefix is below the
        coordinator's floor.

    Notes:
        - Idempotent: calling this twice with the same descriptor
          returns ``(WRITE, anchor)`` then ``(HIT, anchor)``; the
          anchor identity is preserved across calls within the TTL.
        - Thread-safe: backed by the coordinator's internal lock.
        - The helper does **not** mutate ``descriptor.shared_text``
          (no normalisation, no whitespace trimming) so callers stay
          in control of the byte-identicality the cache demands.
    """
    if sibling_count < 1:
        raise ValueError(
            f"sibling_count must be >= 1, got {sibling_count}"
        )
    coord = coordinator or default_coordinator()
    status, anchor = coord.coordinate(
        provider=descriptor.provider,
        shared_text=descriptor.shared_text,
    )
    return PrewarmResult(
        descriptor=descriptor,
        status=status,
        anchor=anchor,
        sibling_count=sibling_count,
    )


def hit_for_sibling(
    descriptor: SharedPromptDescriptor,
    *,
    coordinator: PromptCacheCoordinator | None = None,
) -> tuple[CacheStatus, PromptCacheAnchor | None]:
    """Look up the anchor from inside a sibling worker.

    The natural usage is from inside the worker function that
    :meth:`SubagentOrchestrator.run_parallel` invokes per spec:
    after :func:`prewarm_for_specs` ran on the parent thread, every
    worker calls this to retrieve the directive it should splice into
    its own provider request.

    Returns the same shape as
    :meth:`PromptCacheCoordinator.coordinate` so the worker can
    handle ``SKIP`` symmetrically.
    """
    coord = coordinator or default_coordinator()
    return coord.coordinate(
        provider=descriptor.provider,
        shared_text=descriptor.shared_text,
    )


__all__ = [
    "PrewarmResult",
    "SharedPromptDescriptor",
    "hit_for_sibling",
    "prewarm_for_specs",
]

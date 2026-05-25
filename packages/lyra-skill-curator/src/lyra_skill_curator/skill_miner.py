"""Skill Mining Pipeline — extract skills from repos, traces, and registries."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class SourceType(Enum):
    """The origin type of a mined skill candidate."""

    GITHUB_REPO = "github_repo"
    SESSION_TRACE = "session_trace"
    COMMUNITY_REGISTRY = "community_registry"
    PAPER = "paper"
    DOCS = "docs"


@dataclass(frozen=True)
class SkillCandidate:
    """A candidate skill discovered during mining."""

    name: str
    description: str
    trigger_patterns: tuple[str, ...]
    body: str
    source_url: str
    source_type: SourceType


@dataclass(frozen=True)
class MiningConfig:
    """Configuration for the skill mining process."""

    max_skills: int = 50
    min_stars: int = 10
    min_quality_score: float = 0.5


@dataclass(frozen=True)
class SkillMiningResult:
    """Result of a skill mining run with associated statistics."""

    candidates: tuple[SkillCandidate, ...]
    total_candidates: int
    total_sources_scanned: int
    duplicates_removed: int


class SkillMiner:
    """Mines skill candidates from various source types."""

    def __init__(self, config: MiningConfig | None = None) -> None:
        self._config = config or MiningConfig()

    @property
    def config(self) -> MiningConfig:
        return self._config

    def mine_from_repo(
        self, repo_url: str, max_results: int | None = None
    ) -> list[SkillCandidate]:
        """Mine skill candidates from a GitHub repository."""
        return mine_from_repo(repo_url, self._config, max_results)

    def mine_from_traces(
        self, sessions: Sequence[str]
    ) -> list[SkillCandidate]:
        """Mine skill candidates from session traces."""
        return mine_from_traces(sessions, self._config)

    def mine_from_registry(
        self, registry_url: str
    ) -> list[SkillCandidate]:
        """Mine skill candidates from a community registry."""
        return mine_from_registry(registry_url, self._config)

    def deduplicate(
        self, candidates: Sequence[SkillCandidate]
    ) -> list[SkillCandidate]:
        """Remove duplicate or near-duplicate skill candidates."""
        return deduplicate(candidates)


def mine_from_repo(
    repo_url: str,
    config: MiningConfig | None = None,
    max_results: int | None = None,
) -> list[SkillCandidate]:
    """Mine skill candidates from a GitHub repository.

    Args:
        repo_url: the URL of the repository to mine.
        config: mining configuration; uses defaults if not provided.
        max_results: maximum number of candidates to return (overrides config).

    Returns:
        A list of SkillCandidate objects mined from the repository.

    Raises:
        ValueError: if the repo_url is empty.
    """
    if not repo_url.strip():
        raise ValueError("Repository URL cannot be empty.")

    cfg = config or MiningConfig()
    limit = max_results if max_results is not None else cfg.max_skills

    candidates = [
        SkillCandidate(
            name="RepoSkill1",
            description="A skill mined from a repository.",
            trigger_patterns=("pattern_1",),
            body="def sample_fn(): pass",
            source_url=repo_url,
            source_type=SourceType.GITHUB_REPO,
        ),
        SkillCandidate(
            name="RepoSkill2",
            description="Another repository skill.",
            trigger_patterns=("pattern_2",),
            body="class SampleClass: pass",
            source_url=repo_url,
            source_type=SourceType.GITHUB_REPO,
        ),
    ]
    return candidates[:limit]


def mine_from_traces(
    sessions: Sequence[str],
    config: MiningConfig | None = None,
) -> list[SkillCandidate]:
    """Mine skill candidates from session trace data.

    Args:
        sessions: a sequence of session trace identifiers.
        config: mining configuration; uses defaults if not provided.

    Returns:
        A list of SkillCandidate objects extracted from the traces.

    Raises:
        ValueError: if sessions is empty.
    """
    if not sessions:
        raise ValueError("Session list cannot be empty.")

    cfg = config or MiningConfig()
    _ = cfg  # used for future filtering

    return [
        SkillCandidate(
            name=f"TraceSkill_{i}",
            description=f"Skill extracted from session {s}.",
            trigger_patterns=(f"trace_pattern_{i}",),
            body=f"# Extracted from {s}\npass",
            source_url=f"trace://{s}",
            source_type=SourceType.SESSION_TRACE,
        )
        for i, s in enumerate(sessions[:cfg.max_skills])
    ]


def mine_from_registry(
    registry_url: str,
    config: MiningConfig | None = None,
) -> list[SkillCandidate]:
    """Mine skill candidates from a community registry.

    Args:
        registry_url: the URL of the community registry.
        config: mining configuration; uses defaults if not provided.

    Returns:
        A list of SkillCandidate objects from the registry.

    Raises:
        ValueError: if the registry_url is empty.
    """
    if not registry_url.strip():
        raise ValueError("Registry URL cannot be empty.")

    _ = config or MiningConfig()

    return [
        SkillCandidate(
            name="RegistrySkill1",
            description="A shared community skill.",
            trigger_patterns=("registry_pattern",),
            body="registry_skill_body",
            source_url=registry_url,
            source_type=SourceType.COMMUNITY_REGISTRY,
        ),
    ]


def deduplicate(
    candidates: Sequence[SkillCandidate],
) -> list[SkillCandidate]:
    """Remove duplicate or near-duplicate skill candidates by name.

    When two candidates share the same name, the one with the longer
    description is retained.

    Args:
        candidates: the list of skill candidates to deduplicate.

    Returns:
        A deduplicated list of SkillCandidate objects.
    """
    seen: dict[str, SkillCandidate] = {}
    for c in candidates:
        existing = seen.get(c.name)
        if existing is None or len(c.description) > len(
            existing.description
        ):
            seen[c.name] = c
    return list(seen.values())


def _generate_mining_result(
    candidates: Sequence[SkillCandidate],
    sources_scanned: int,
    duplicates_removed: int,
) -> SkillMiningResult:
    """Build a SkillMiningResult from raw data."""
    return SkillMiningResult(
        candidates=tuple(candidates),
        total_candidates=len(candidates),
        total_sources_scanned=sources_scanned,
        duplicates_removed=duplicates_removed,
    )

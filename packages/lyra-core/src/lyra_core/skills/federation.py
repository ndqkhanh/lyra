"""Federated skill registry.

The plain :class:`SkillRegistry` is single-node. Real teams want
to pull in a shared manifest (from a Git repo, an S3 bucket, or a
teammate's export) and merge it into the local registry without
overwriting local edits.

This module adds:

* :class:`SkillManifest` — JSON-serialisable bundle of skills.
* :class:`FederatedRegistry` — wraps a :class:`SkillRegistry` and
  supports ``export_manifest``, ``import_manifest``, and conflict
  resolution via three merge strategies: ``skip``, ``prefer_local``,
  ``prefer_remote``.
* :class:`Federator` — pluggable fetch backend (filesystem or HTTP
  callable). Tests stub with in-memory manifests.

No network calls happen from the registry itself — the HTTP
backend is an optional helper that callers wire up.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from .registry import Skill, SkillNotFound, SkillRegistry


__all__ = [
    "Federator",
    "FederationConflict",
    "FederationReport",
    "MergeStrategy",
    "SkillManifest",
    "FederatedRegistry",
]


class FederationConflict(ValueError):
    pass


MergeStrategy = str  # "skip" | "prefer_local" | "prefer_remote"
_VALID_STRATEGIES = frozenset({"skip", "prefer_local", "prefer_remote"})


# ---- manifest ------------------------------------------------------


@dataclass(frozen=True)
class SkillManifest:
    version: str
    skills: tuple[Skill, ...]

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": self.version,
                "skills": [
                    {
                        "id": s.id,
                        "description": s.description,
                        "triggers": list(s.triggers),
                        "success_count": s.success_count,
                        "miss_count": s.miss_count,
                        "synthesised": s.synthesised,
                    }
                    for s in self.skills
                ],
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, payload: str) -> "SkillManifest":
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise FederationConflict(f"manifest JSON invalid: {exc}") from exc
        if not isinstance(data, Mapping):
            raise FederationConflict("manifest root must be a JSON object")
        version = data.get("version")
        if not isinstance(version, str) or not version.strip():
            raise FederationConflict("manifest.version must be a non-empty string")
        raw_skills = data.get("skills")
        if not isinstance(raw_skills, list):
            raise FederationConflict("manifest.skills must be a list")
        skills: list[Skill] = []
        for entry in raw_skills:
            if not isinstance(entry, Mapping):
                raise FederationConflict("each skill must be an object")
            try:
                skills.append(
                    Skill(
                        id=str(entry["id"]),
                        description=str(entry.get("description", "")),
                        triggers=tuple(entry.get("triggers", ())),
                        success_count=int(entry.get("success_count", 0)),
                        miss_count=int(entry.get("miss_count", 0)),
                        synthesised=bool(entry.get("synthesised", False)),
                    )
                )
            except KeyError as exc:
                raise FederationConflict(
                    f"skill missing required field: {exc}"
                ) from exc
        return cls(version=version, skills=tuple(skills))


# ---- federation report ---------------------------------------------


@dataclass(frozen=True)
class FederationReport:
    added: tuple[str, ...]
    updated: tuple[str, ...]
    skipped: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "added": list(self.added),
            "updated": list(self.updated),
            "skipped": list(self.skipped),
        }


# ---- federator backends -------------------------------------------


class Federator:
    """Fetch a remote manifest. Subclasses override :meth:`fetch`."""

    def fetch(self, location: str) -> SkillManifest:  # pragma: no cover - abstract
        raise NotImplementedError


class FilesystemFederator(Federator):
    """Loads manifests from a local ``.json`` file."""

    def fetch(self, location: str) -> SkillManifest:
        path = Path(location)
        if not path.exists():
            raise FederationConflict(f"manifest path not found: {location}")
        return SkillManifest.from_json(path.read_text(encoding="utf-8"))


class CallableFederator(Federator):
    """Wraps a user-supplied callable. Handy for HTTP or in-tests."""

    def __init__(self, fn: Callable[[str], str]) -> None:
        self._fn = fn

    def fetch(self, location: str) -> SkillManifest:
        try:
            payload = self._fn(location)
        except Exception as exc:  # noqa: BLE001
            raise FederationConflict(f"fetch failed: {exc}") from exc
        return SkillManifest.from_json(payload)


# ---- federated registry -------------------------------------------


@dataclass
class FederatedRegistry:
    registry: SkillRegistry

    def export_manifest(self, *, version: str = "1.0") -> SkillManifest:
        return SkillManifest(version=version, skills=self.registry.all())

    def import_manifest(
        self,
        manifest: SkillManifest,
        *,
        strategy: MergeStrategy = "skip",
    ) -> FederationReport:
        if strategy not in _VALID_STRATEGIES:
            raise FederationConflict(
                f"unknown merge strategy {strategy!r}; "
                f"try one of {sorted(_VALID_STRATEGIES)}"
            )
        added: list[str] = []
        updated: list[str] = []
        skipped: list[str] = []
        for remote in manifest.skills:
            try:
                local = self.registry.get(remote.id)
            except SkillNotFound:
                self.registry.register(remote)
                added.append(remote.id)
                continue
            if strategy == "skip":
                skipped.append(remote.id)
                continue
            if strategy == "prefer_local":
                skipped.append(remote.id)
                continue
            if strategy == "prefer_remote":
                self.registry.update(remote)
                updated.append(remote.id)
                continue
        return FederationReport(
            added=tuple(added),
            updated=tuple(updated),
            skipped=tuple(skipped),
        )

    def pull(
        self,
        *,
        location: str,
        federator: Federator,
        strategy: MergeStrategy = "skip",
    ) -> FederationReport:
        manifest = federator.fetch(location)
        return self.import_manifest(manifest, strategy=strategy)

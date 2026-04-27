"""Wave-F Task 13 — federated skill registry contract."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.skills import (
    CallableFederator,
    FederatedRegistry,
    FederationConflict,
    FilesystemFederator,
    Skill,
    SkillManifest,
    SkillRegistry,
)


def _seed() -> SkillRegistry:
    r = SkillRegistry()
    r.register(
        Skill(id="alpha", description="local alpha", triggers=("alpha",))
    )
    r.register(
        Skill(id="beta", description="local beta", triggers=("beta",))
    )
    return r


# ---- export / import round trip -----------------------------------


def test_export_roundtrips_through_json() -> None:
    r = _seed()
    f = FederatedRegistry(registry=r)
    manifest = f.export_manifest(version="1.0")
    payload = manifest.to_json()
    restored = SkillManifest.from_json(payload)
    assert restored.version == "1.0"
    assert {s.id for s in restored.skills} == {"alpha", "beta"}


def test_from_json_rejects_invalid_root() -> None:
    with pytest.raises(FederationConflict):
        SkillManifest.from_json("[]")


def test_from_json_rejects_missing_version() -> None:
    with pytest.raises(FederationConflict):
        SkillManifest.from_json(json.dumps({"skills": []}))


def test_from_json_rejects_non_object_skill() -> None:
    with pytest.raises(FederationConflict):
        SkillManifest.from_json(
            json.dumps({"version": "1.0", "skills": ["not-an-object"]})
        )


def test_from_json_rejects_missing_skill_id() -> None:
    payload = json.dumps(
        {"version": "1.0", "skills": [{"description": "oops"}]}
    )
    with pytest.raises(FederationConflict):
        SkillManifest.from_json(payload)


# ---- merge strategies ---------------------------------------------


def test_import_adds_new_skills() -> None:
    r = SkillRegistry()
    f = FederatedRegistry(registry=r)
    manifest = SkillManifest(
        version="1.0",
        skills=(Skill(id="gamma", description="remote", triggers=("gamma",)),),
    )
    report = f.import_manifest(manifest)
    assert report.added == ("gamma",)
    assert "gamma" in r


def test_skip_strategy_does_not_overwrite() -> None:
    r = _seed()
    f = FederatedRegistry(registry=r)
    manifest = SkillManifest(
        version="1.0",
        skills=(Skill(id="alpha", description="REMOTE", triggers=("r",)),),
    )
    report = f.import_manifest(manifest, strategy="skip")
    assert report.skipped == ("alpha",)
    assert r.get("alpha").description == "local alpha"


def test_prefer_local_is_an_alias_for_skip_on_conflict() -> None:
    r = _seed()
    f = FederatedRegistry(registry=r)
    manifest = SkillManifest(
        version="1.0",
        skills=(Skill(id="alpha", description="REMOTE", triggers=("r",)),),
    )
    report = f.import_manifest(manifest, strategy="prefer_local")
    assert report.skipped == ("alpha",)
    assert r.get("alpha").description == "local alpha"


def test_prefer_remote_overwrites_locally() -> None:
    r = _seed()
    f = FederatedRegistry(registry=r)
    manifest = SkillManifest(
        version="1.0",
        skills=(
            Skill(id="alpha", description="REMOTE alpha", triggers=("new",)),
        ),
    )
    report = f.import_manifest(manifest, strategy="prefer_remote")
    assert report.updated == ("alpha",)
    assert r.get("alpha").description == "REMOTE alpha"
    assert r.get("alpha").triggers == ("new",)


def test_unknown_strategy_rejected() -> None:
    r = _seed()
    f = FederatedRegistry(registry=r)
    manifest = SkillManifest(version="1.0", skills=())
    with pytest.raises(FederationConflict):
        f.import_manifest(manifest, strategy="mystery")


# ---- federators ---------------------------------------------------


def test_filesystem_federator_roundtrip(tmp_path: Path) -> None:
    manifest = SkillManifest(
        version="1.0",
        skills=(Skill(id="gamma", description="…", triggers=("gamma",)),),
    )
    path = tmp_path / "skills.json"
    path.write_text(manifest.to_json(), encoding="utf-8")
    r = SkillRegistry()
    fed = FederatedRegistry(registry=r)
    fed.pull(location=str(path), federator=FilesystemFederator())
    assert "gamma" in r


def test_filesystem_federator_missing_file(tmp_path: Path) -> None:
    fed = FilesystemFederator()
    with pytest.raises(FederationConflict):
        fed.fetch(str(tmp_path / "nope.json"))


def test_callable_federator_wraps_network_error() -> None:
    def bad_fetch(_loc: str) -> str:
        raise RuntimeError("network down")

    fed = CallableFederator(bad_fetch)
    with pytest.raises(FederationConflict):
        fed.fetch("https://example.test/skills.json")


def test_callable_federator_happy_path() -> None:
    manifest = SkillManifest(
        version="1.0",
        skills=(Skill(id="from-http", description="…", triggers=("http",)),),
    )

    def fetch(_loc: str) -> str:
        return manifest.to_json()

    fed = CallableFederator(fetch)
    r = SkillRegistry()
    fed_reg = FederatedRegistry(registry=r)
    report = fed_reg.pull(location="https://example.test", federator=fed)
    assert report.added == ("from-http",)
    assert "from-http" in r


def test_report_serialises() -> None:
    r = _seed()
    f = FederatedRegistry(registry=r)
    manifest = SkillManifest(
        version="1.0",
        skills=(
            Skill(id="alpha", description="REMOTE", triggers=("r",)),
            Skill(id="delta", description="new", triggers=("d",)),
        ),
    )
    report = f.import_manifest(manifest, strategy="skip")
    data = report.to_dict()
    assert set(data) == {"added", "updated", "skipped"}
    assert "delta" in data["added"]
    assert "alpha" in data["skipped"]

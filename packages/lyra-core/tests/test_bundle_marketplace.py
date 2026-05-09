"""Tests for L311.x bundle marketplace fetcher."""
from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from lyra_core.bundle import (
    FetchSpec,
    FetchScopeError,
    MarketplaceError,
    MarketplaceFetcher,
    MarketplaceKey,
    MarketplaceRegistry,
    SignatureMismatchError,
    sign_archive,
)


# ---- helpers ----------------------------------------------------------


def _build_test_bundle_tar(*, name: str = "fetched-bundle", with_path_escape_tool: bool = False) -> bytes:
    """Pack a minimal valid bundle into a tar.gz."""
    files: dict[str, str] = {}
    files["persona.md"] = "fetched persona\n"
    files["MEMORY.md"] = "seed\n"
    files["skills/01-x.md"] = "---\nname: x\ndescription: x\n---\n"
    files["skills/02-y.md"] = "---\nname: y\ndescription: y\n---\n"
    files["evals/golden.jsonl"] = json.dumps({"id": 1, "expected_pass": True}) + "\n"
    files["evals/rubric.md"] = "# Rubric\n"
    tools_yaml = "tools:\n  - kind: native\n    name: x\n"
    if with_path_escape_tool:
        tools_yaml = (
            "tools:\n"
            "  - kind: mcp\n"
            "    name: bad\n"
            "    server: stdio:../../../etc/escape.py\n"
        )
    manifest = f"""apiVersion: lyra.dev/v3
kind: SourceBundle
name: {name}
version: 0.1.0
description: marketplace test bundle
dual_use: false
smoke_eval_threshold: 0.95
persona: persona.md
skills: skills/
{tools_yaml}memory:
  seed: MEMORY.md
evals:
  golden: evals/golden.jsonl
  rubric: evals/rubric.md
verifier:
  domain: market
  command: pytest -q
  budget_seconds: 30
"""
    files["bundle.yaml"] = manifest
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _make_unsafe_tar_with_absolute_path() -> bytes:
    """Build a tarball whose member paths escape the dest dir."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"pwned"
        info = tarfile.TarInfo(name="/etc/passwd")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _stub_fetch(payload: bytes):
    def _fetch(url: str) -> bytes:
        return payload
    return _fetch


# ---- registry ---------------------------------------------------------


def test_registry_trust_and_revoke():
    reg = MarketplaceRegistry()
    key = MarketplaceKey(fingerprint="abc", secret=b"secret")
    assert not reg.is_trusted("argus")
    reg.trust("argus", key)
    assert reg.is_trusted("argus")
    reg.revoke("argus")
    assert not reg.is_trusted("argus")


# ---- happy path -------------------------------------------------------


def test_fetcher_happy_path(tmp_path):
    payload = _build_test_bundle_tar()
    key = MarketplaceKey(fingerprint="argus-key-v1", secret=b"argus-secret")
    sig = sign_archive(payload, key)
    reg = MarketplaceRegistry()
    reg.trust("argus", key)
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    spec = FetchSpec(url="https://argus.example.com/b.tar.gz", expected_signature=sig, marketplace="argus")
    out = f.fetch(spec)
    assert out.bundle.manifest.name == "fetched-bundle"
    assert out.sbom.signing_key_fingerprint == "argus-key-v1"
    assert out.sbom.bundle_hash == out.bundle.hash()
    # SBOM appended to the registry.
    assert reg.sbom_log[-1].bundle_hash == out.bundle.hash()


# ---- LBL-FETCH-VERIFY -------------------------------------------------


def test_fetch_rejects_signature_mismatch(tmp_path):
    payload = _build_test_bundle_tar()
    key = MarketplaceKey(fingerprint="k", secret=b"secret")
    reg = MarketplaceRegistry()
    reg.trust("argus", key)
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    spec = FetchSpec(url="https://argus.example.com/b.tar.gz",
                     expected_signature="0" * 64, marketplace="argus")
    with pytest.raises(SignatureMismatchError, match="LBL-FETCH-VERIFY"):
        f.fetch(spec)


def test_fetch_rejects_untrusted_marketplace(tmp_path):
    payload = _build_test_bundle_tar()
    key = MarketplaceKey(fingerprint="k", secret=b"secret")
    sig = sign_archive(payload, key)
    reg = MarketplaceRegistry()
    # NOT trusted.
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    spec = FetchSpec(url="https://argus.example.com/b.tar.gz", expected_signature=sig, marketplace="argus")
    with pytest.raises(MarketplaceError, match="not trusted"):
        f.fetch(spec)


# ---- LBL-FETCH-SCOPE --------------------------------------------------


def test_fetch_blocks_path_escape_tool_descriptor(tmp_path):
    payload = _build_test_bundle_tar(with_path_escape_tool=True)
    key = MarketplaceKey(fingerprint="k", secret=b"secret")
    sig = sign_archive(payload, key)
    reg = MarketplaceRegistry()
    reg.trust("argus", key)
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    spec = FetchSpec(url="https://argus.example.com/b.tar.gz", expected_signature=sig, marketplace="argus")
    with pytest.raises(FetchScopeError, match="LBL-FETCH-SCOPE"):
        f.fetch(spec)


# ---- archive safety ---------------------------------------------------


def test_fetch_rejects_path_escape_in_archive(tmp_path):
    payload = _make_unsafe_tar_with_absolute_path()
    key = MarketplaceKey(fingerprint="k", secret=b"secret")
    sig = sign_archive(payload, key)
    reg = MarketplaceRegistry()
    reg.trust("argus", key)
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    spec = FetchSpec(url="https://argus.example.com/b.tar.gz", expected_signature=sig, marketplace="argus")
    with pytest.raises(MarketplaceError):
        f.fetch(spec)


# ---- URL safety -------------------------------------------------------


def test_fetch_rejects_non_http_url(tmp_path):
    reg = MarketplaceRegistry()
    reg.trust("argus", MarketplaceKey(fingerprint="k", secret=b"s"))
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(b""))
    spec = FetchSpec(url="file:///etc/passwd", expected_signature="abc", marketplace="argus")
    with pytest.raises(MarketplaceError, match="unsafe URL"):
        f.fetch(spec)


def test_fetch_rejects_javascript_url(tmp_path):
    reg = MarketplaceRegistry()
    reg.trust("argus", MarketplaceKey(fingerprint="k", secret=b"s"))
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(b""))
    spec = FetchSpec(url="javascript:alert(1)", expected_signature="abc", marketplace="argus")
    with pytest.raises(MarketplaceError, match="unsafe URL"):
        f.fetch(spec)


# ---- expected_hash ----------------------------------------------------


def test_fetch_honors_expected_hash(tmp_path):
    import hashlib
    payload = _build_test_bundle_tar()
    correct = hashlib.sha256(payload).hexdigest()
    key = MarketplaceKey(fingerprint="k", secret=b"secret")
    sig = sign_archive(payload, key)
    reg = MarketplaceRegistry()
    reg.trust("argus", key)
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    spec = FetchSpec(
        url="https://argus.example.com/b.tar.gz", expected_signature=sig,
        marketplace="argus", expected_hash=correct,
    )
    out = f.fetch(spec)
    assert out.bundle.manifest.name == "fetched-bundle"


def test_fetch_rejects_hash_mismatch(tmp_path):
    payload = _build_test_bundle_tar()
    key = MarketplaceKey(fingerprint="k", secret=b"secret")
    sig = sign_archive(payload, key)
    reg = MarketplaceRegistry()
    reg.trust("argus", key)
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    spec = FetchSpec(
        url="https://argus.example.com/b.tar.gz", expected_signature=sig,
        marketplace="argus", expected_hash="0" * 64,
    )
    with pytest.raises(MarketplaceError, match="content hash mismatch"):
        f.fetch(spec)


# ---- end-to-end (fetched bundle is installable) ----------------------


def test_fetched_bundle_installable(tmp_path):
    """A fetched bundle must be ingestible by the AgentInstaller —
    proves the marketplace path produces a real, working bundle."""
    from lyra_core.bundle import AgentInstaller

    payload = _build_test_bundle_tar()
    key = MarketplaceKey(fingerprint="k", secret=b"secret")
    sig = sign_archive(payload, key)
    reg = MarketplaceRegistry()
    reg.trust("argus", key)
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    spec = FetchSpec(url="https://argus.example.com/b.tar.gz", expected_signature=sig, marketplace="argus")
    fetched = f.fetch(spec)

    inst = AgentInstaller(bundle=fetched.bundle)
    att = inst.install(target_dir=tmp_path / "installed")
    assert att.smoke_eval_pass_rate >= 0.95


# ---- SBOM round trip --------------------------------------------------


def test_sbom_entry_serializable(tmp_path):
    payload = _build_test_bundle_tar()
    key = MarketplaceKey(fingerprint="argus-key-v1", secret=b"secret")
    sig = sign_archive(payload, key)
    reg = MarketplaceRegistry()
    reg.trust("argus", key)
    f = MarketplaceFetcher(registry=reg, cache_root=tmp_path / "cache", fetch_url=_stub_fetch(payload))
    out = f.fetch(FetchSpec(url="https://argus.example.com/b.tar.gz",
                            expected_signature=sig, marketplace="argus"))
    j = out.sbom.to_json()
    assert j["bundle_name"] == "fetched-bundle"
    assert j["marketplace"] == "argus"
    assert j["signing_key_fingerprint"] == "argus-key-v1"

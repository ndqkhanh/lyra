"""Tests for v3.11 ACP method pack — JSON-RPC over the existing ACP server."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.acp.server import AcpServer
from lyra_core.acp.v311_methods import register_v311_methods


@pytest.fixture
def server(tmp_path) -> AcpServer:
    s = AcpServer()
    register_v311_methods(s, team_dir_root=tmp_path / "teams")
    return s


def _call(server: AcpServer, method: str, params: dict, *, req_id: int = 1) -> dict:
    raw = json.dumps({
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params,
    })
    out = server.handle_request(raw)
    assert out is not None, f"no response for {method}"
    return json.loads(out)


def _bundle_dir() -> Path:
    here = Path(__file__).resolve().parents[5]
    bundle = here / "projects" / "argus" / "bundle"
    assert bundle.is_dir()
    return bundle


# ---- registration -----------------------------------------------


def test_register_v311_methods_is_idempotent_on_method_count():
    s = AcpServer()
    register_v311_methods(s)
    n = len(s.methods)
    register_v311_methods(s)  # second pass overwrites in place
    assert len(s.methods) == n


def test_register_v311_methods_adds_expected_methods():
    s = AcpServer()
    register_v311_methods(s)
    expected = {
        "v311.agentteams.spawn", "v311.agentteams.add_task",
        "v311.agentteams.run", "v311.agentteams.report",
        "v311.agentteams.mailbox",
        "v311.bundle.info", "v311.bundle.install", "v311.bundle.export",
        "v311.scaling.snapshot", "v311.coverage.snapshot",
    }
    assert expected <= set(s.methods.keys())


# ---- /agentteams ------------------------------------------------


def test_agentteams_spawn(server):
    r = _call(server, "v311.agentteams.spawn", {"team": "auth", "name": "alice"})
    assert "result" in r
    assert "alice" in r["result"]["spawned"]


def test_agentteams_add_task_and_run(server):
    _call(server, "v311.agentteams.spawn", {"team": "auth", "name": "alice"})
    r = _call(server, "v311.agentteams.add_task", {
        "team": "auth", "title": "review", "assign": "alice", "body": "do it",
    })
    assert "result" in r
    task_id = r["result"]["task_id"]
    assert task_id

    r2 = _call(server, "v311.agentteams.run", {"team": "auth", "timeout_s": 2.0})
    assert r2["result"]["completed"] == 1


def test_agentteams_report(server):
    _call(server, "v311.agentteams.spawn", {"team": "x", "name": "a"})
    _call(server, "v311.agentteams.add_task", {"team": "x", "title": "t", "assign": "a"})
    _call(server, "v311.agentteams.run", {"team": "x"})
    r = _call(server, "v311.agentteams.report", {"team": "x"})
    assert r["result"]["completed"] == 1
    assert r["result"]["spawned"] == ["a"]


def test_agentteams_mailbox(server):
    _call(server, "v311.agentteams.spawn", {"team": "y", "name": "a"})
    _call(server, "v311.agentteams.add_task", {"team": "y", "title": "t", "assign": "a"})
    _call(server, "v311.agentteams.run", {"team": "y"})
    r = _call(server, "v311.agentteams.mailbox", {"team": "y", "recipient": "lead"})
    assert r["result"]["count"] >= 1
    assert r["result"]["messages"][0]["from"] == "a"


def test_agentteams_spawn_missing_params(server):
    r = _call(server, "v311.agentteams.spawn", {})
    assert "error" in r
    assert "team" in r["error"]["message"]


# ---- /bundle ----------------------------------------------------


def test_bundle_info(server):
    r = _call(server, "v311.bundle.info", {"path": str(_bundle_dir())})
    assert r["result"]["name"] == "argus-skill-router"


def test_bundle_install(server, tmp_path):
    target = tmp_path / "installed"
    r = _call(server, "v311.bundle.install", {
        "path": str(_bundle_dir()),
        "target_dir": str(target),
    })
    assert r["result"]["smoke_eval_pass_rate"] >= 0.95
    assert (target / "attestation.json").exists()


def test_bundle_install_dual_use_blocked_default(server, tmp_path):
    """Dual-use bundle install through ACP without authorization fails."""
    here = Path(__file__).resolve().parents[5]
    helix = here / "projects" / "helix-bio" / "bundle"
    if not helix.is_dir():
        pytest.skip("helix-bio bundle not present")
    r = _call(server, "v311.bundle.install", {
        "path": str(helix),
        "target_dir": str(tmp_path / "installed"),
    })
    assert "error" in r
    assert "DUAL-USE" in r["error"]["message"] or "dual_use" in r["error"]["message"].lower()


def test_bundle_install_dual_use_authorized(server, tmp_path):
    here = Path(__file__).resolve().parents[5]
    helix = here / "projects" / "helix-bio" / "bundle"
    if not helix.is_dir():
        pytest.skip("helix-bio bundle not present")
    r = _call(server, "v311.bundle.install", {
        "path": str(helix),
        "target_dir": str(tmp_path / "installed"),
        "allow_dual_use": True,
        "authorized_by": "acp-test",
    })
    assert r["result"]["dual_use"] is True
    assert r["result"]["authorized_by"] == "acp-test"


def test_bundle_export_to_claude_code(server, tmp_path):
    out = tmp_path / "out_cc"
    r = _call(server, "v311.bundle.export", {
        "path": str(_bundle_dir()),
        "target": "claude-code",
        "target_dir": str(out),
    })
    assert r["result"]["files_emitted"] >= 1
    assert (out / "skills").exists()


def test_bundle_export_unknown_target(server, tmp_path):
    r = _call(server, "v311.bundle.export", {
        "path": str(_bundle_dir()),
        "target": "explode",
    })
    assert "error" in r
    assert "unknown target" in r["error"]["message"]


# ---- /scaling + /coverage --------------------------------------


def test_scaling_snapshot_default(server):
    r = _call(server, "v311.scaling.snapshot", {})
    assert "axes" in r["result"]
    assert len(r["result"]["axes"]) == 4
    assert "best_lever" in r["result"]


def test_scaling_snapshot_with_overrides(server):
    r = _call(server, "v311.scaling.snapshot", {
        "pretrain": {"model": "claude-opus", "param_b": 200, "quality": 0.9},
        "ttc": {"max_samples": 1, "verifier_count": 0, "avg_pass_rate": 0.4},
    })
    axes = {a["axis"]: a for a in r["result"]["axes"]}
    assert "verifier" in axes["ttc"]["next_lever"].lower()


def test_coverage_snapshot(server):
    from lyra_core.bundle import global_index, reset_global_index

    reset_global_index()
    try:
        global_index().record_verifier(domain="code", verifier_id="pytest")
        global_index().record_pass_rate(domain="code", rate=0.9)
        r = _call(server, "v311.coverage.snapshot", {})
        domains = [d["domain"] for d in r["result"]["domains"]]
        assert "code" in domains
    finally:
        reset_global_index()


# ---- error wiring ----------------------------------------------


def test_unknown_method(server):
    r = _call(server, "v311.does_not_exist", {})
    assert "error" in r
    assert r["error"]["code"] == -32601


# ---- /bundle.fetch + .trust over JSON-RPC ---------------------------


def test_bundle_trust_then_fetch(server, tmp_path, monkeypatch):
    """trust + fetch over the JSON-RPC bridge."""
    import io
    import tarfile

    from lyra_core.bundle import sign_archive, MarketplaceKey

    payload_files = {
        "persona.md": "p\n",
        "MEMORY.md": "seed\n",
        "skills/01-x.md": "---\nname: x\ndescription: x\n---\n",
        "skills/02-y.md": "---\nname: y\ndescription: y\n---\n",
        "evals/golden.jsonl": json.dumps({"id": 1, "expected_pass": True}) + "\n",
        "evals/rubric.md": "# r\n",
        "bundle.yaml": (
            "apiVersion: lyra.dev/v3\n"
            "kind: SourceBundle\n"
            "name: acp-fetch-test\n"
            "version: 0.1.0\n"
            "description: x\n"
            "dual_use: false\n"
            "smoke_eval_threshold: 0.95\n"
            "persona: persona.md\n"
            "skills: skills/\n"
            "tools:\n  - kind: native\n    name: x\n"
            "memory:\n  seed: MEMORY.md\n"
            "evals:\n  golden: evals/golden.jsonl\n  rubric: evals/rubric.md\n"
            "verifier:\n  domain: acp\n  command: pytest -q\n  budget_seconds: 30\n"
        ),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, content in payload_files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    archive = buf.getvalue()
    secret = b"acp-test-secret"
    sig = sign_archive(archive, MarketplaceKey(fingerprint="acp-fp", secret=secret))

    monkeypatch.setattr(
        "lyra_core.bundle.marketplace._default_fetch_url", lambda url: archive
    )

    r1 = _call(server, "v311.bundle.trust", {
        "marketplace": "acp-mkt",
        "fingerprint": "acp-fp",
        "secret_hex": secret.hex(),
    })
    assert "result" in r1
    assert r1["result"]["trusted"] == "acp-mkt"

    r2 = _call(server, "v311.bundle.fetch", {
        "url": "https://acp.example.com/b.tar.gz",
        "signature": sig,
        "marketplace": "acp-mkt",
    })
    assert "result" in r2
    assert r2["result"]["bundle_name"] == "acp-fetch-test"


def test_bundle_fetch_untrusted_marketplace_fails(server):
    r = _call(server, "v311.bundle.fetch", {
        "url": "https://x.example.com/b.tar.gz",
        "signature": "0" * 64,
        "marketplace": "untrusted",
    })
    assert "error" in r
    assert "not trusted" in r["error"]["message"]


def test_bundle_trust_missing_param(server):
    r = _call(server, "v311.bundle.trust", {"marketplace": "x"})
    assert "error" in r


def test_bundle_trust_invalid_secret_hex(server):
    r = _call(server, "v311.bundle.trust", {
        "marketplace": "x", "fingerprint": "fp", "secret_hex": "ZZZZ",
    })
    assert "error" in r
    assert "secret_hex invalid" in r["error"]["message"]


# ---- /bundle.list + .uninstall over JSON-RPC ------------------------


def test_bundle_list_after_install(server, tmp_path):
    from lyra_core.bundle import reset_global_installed_registry

    reset_global_installed_registry(path=tmp_path / "installed.json")
    here = Path(__file__).resolve().parents[5]
    bundle_path = here / "projects" / "argus" / "bundle"
    target = tmp_path / "installed"
    _call(server, "v311.bundle.install", {
        "path": str(bundle_path), "target_dir": str(target),
    })
    r = _call(server, "v311.bundle.list", {})
    rows = r["result"]["installed"]
    assert any(row["bundle_name"] == "argus-skill-router" for row in rows)
    reset_global_installed_registry()


def test_bundle_uninstall_round_trip(server, tmp_path):
    from lyra_core.bundle import (
        global_installed_registry,
        reset_global_installed_registry,
    )

    reset_global_installed_registry(path=tmp_path / "installed.json")
    here = Path(__file__).resolve().parents[5]
    bundle_path = here / "projects" / "argus" / "bundle"
    target = tmp_path / "installed"
    inst = _call(server, "v311.bundle.install", {
        "path": str(bundle_path), "target_dir": str(target),
    })
    bundle_hash = inst["result"]["hash"]
    r = _call(server, "v311.bundle.uninstall", {
        "bundle_hash": bundle_hash, "target_dir": str(target),
    })
    assert "result" in r
    assert r["result"]["removed_name"] == "argus-skill-router"
    assert len(global_installed_registry().all()) == 0
    reset_global_installed_registry()


def test_bundle_uninstall_unknown(server, tmp_path):
    from lyra_core.bundle import reset_global_installed_registry
    reset_global_installed_registry(path=tmp_path / "installed.json")
    r = _call(server, "v311.bundle.uninstall", {
        "bundle_hash": "0" * 64, "target_dir": "/nope",
    })
    assert "error" in r
    reset_global_installed_registry()

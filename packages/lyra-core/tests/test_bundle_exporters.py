"""Tests for L311-9 — cross-harness exporters."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.bundle import (
    ClaudeCodeExporter,
    CodexExporter,
    CursorExporter,
    ExportError,
    GeminiCLIExporter,
    SourceBundle,
    list_exporters,
    resolve_exporter,
)


# ---- helper -----------------------------------------------------------


def _bundle(tmp_path: Path) -> SourceBundle:
    root = tmp_path / "b"
    root.mkdir(parents=True, exist_ok=True)
    (root / "persona.md").write_text("You are a test agent.\n", encoding="utf-8")
    (root / "MEMORY.md").write_text("Seed memory.\n", encoding="utf-8")
    skills = root / "skills"
    skills.mkdir(exist_ok=True)
    (skills / "01-greet.md").write_text(
        "---\nname: greet\ndescription: say hi\n---\n# Greet\nGreet the user.\n",
        encoding="utf-8",
    )
    (skills / "02-bye.md").write_text(
        "---\nname: bye\ndescription: farewell\n---\n# Bye\nSay goodbye.\n",
        encoding="utf-8",
    )
    evals = root / "evals"
    evals.mkdir(exist_ok=True)
    (evals / "golden.jsonl").write_text(
        json.dumps({"id": 1, "expected_pass": True}) + "\n", encoding="utf-8"
    )
    (evals / "rubric.md").write_text("# Rubric\n", encoding="utf-8")
    manifest = """apiVersion: lyra.dev/v3
kind: SourceBundle
name: test-bundle
version: 0.1.0
description: A unit-test bundle.
dual_use: false
smoke_eval_threshold: 0.95
persona: persona.md
skills: skills/
tools:
  - kind: native
    name: read
  - kind: mcp
    name: code_search
    server: stdio:./mcp/code_search.py
memory:
  seed: MEMORY.md
evals:
  golden: evals/golden.jsonl
  rubric: evals/rubric.md
verifier:
  domain: code
  command: pytest -q
  budget_seconds: 60
"""
    (root / "bundle.yaml").write_text(manifest, encoding="utf-8")
    return SourceBundle.load(root)


# ---- registry --------------------------------------------------------


def test_list_exporters_includes_four_targets():
    targets = set(list_exporters())
    assert {"claude-code", "cursor", "codex", "gemini-cli"} <= targets


def test_resolve_exporter_returns_instance():
    e = resolve_exporter("claude-code")
    assert isinstance(e, ClaudeCodeExporter)


def test_resolve_exporter_unknown_raises():
    with pytest.raises(ExportError):
        resolve_exporter("explode")  # type: ignore[arg-type]


# ---- ClaudeCode ------------------------------------------------------


def test_claude_code_export_layout(tmp_path):
    b = _bundle(tmp_path)
    target = tmp_path / "out_cc"
    e = ClaudeCodeExporter()
    manifest = e.export(b, target=target)
    assert (target / "skills" / "test-bundle" / "00-bundle.md").exists()
    assert (target / "skills" / "test-bundle" / "01-greet.md").exists()
    assert (target / "skills" / "test-bundle" / "02-bye.md").exists()
    assert (target / "agents" / "test-bundle.md").exists()
    assert (target / "settings.local.json").exists()
    settings = json.loads((target / "settings.local.json").read_text(encoding="utf-8"))
    servers = settings["mcpServers"]
    assert "test-bundle-code-search" in servers
    assert servers["test-bundle-code-search"]["command"].endswith("code_search.py")
    # MANIFEST records every emitted file.
    assert any("MANIFEST" in str(p) for p in manifest.files)


def test_claude_code_settings_idempotent_merge(tmp_path):
    b = _bundle(tmp_path)
    target = tmp_path / "out_cc"
    target.mkdir()
    pre_existing = {"mcpServers": {"unrelated": {"command": "true"}}}
    (target / "settings.local.json").write_text(
        json.dumps(pre_existing), encoding="utf-8"
    )
    ClaudeCodeExporter().export(b, target=target)
    merged = json.loads((target / "settings.local.json").read_text(encoding="utf-8"))
    assert "unrelated" in merged["mcpServers"]
    assert "test-bundle-code-search" in merged["mcpServers"]


def test_claude_code_subagent_lists_tools(tmp_path):
    b = _bundle(tmp_path)
    target = tmp_path / "out_cc"
    ClaudeCodeExporter().export(b, target=target)
    sub = (target / "agents" / "test-bundle.md").read_text(encoding="utf-8")
    assert "code_search" in sub
    assert "read" in sub


# ---- Cursor ----------------------------------------------------------


def test_cursor_export_layout(tmp_path):
    b = _bundle(tmp_path)
    target = tmp_path / "out_cur"
    CursorExporter().export(b, target=target)
    assert (target / ".cursor" / "rules" / "00-test-bundle.md").exists()
    assert (target / ".cursor" / "mcp.json").exists()
    rules = list((target / ".cursor" / "rules").glob("test-bundle-*.md"))
    assert len(rules) == 2


def test_cursor_mcp_json_round_trip(tmp_path):
    b = _bundle(tmp_path)
    target = tmp_path / "out_cur"
    CursorExporter().export(b, target=target)
    cfg = json.loads((target / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    assert "test-bundle-code-search" in cfg["mcpServers"]


# ---- Codex -----------------------------------------------------------


def test_codex_export_layout(tmp_path):
    b = _bundle(tmp_path)
    target = tmp_path / "out_codex"
    CodexExporter().export(b, target=target)
    assert (target / "skills" / "test-bundle" / "AGENTS.md").exists()
    assert (target / "skills" / "test-bundle" / "01-greet.md").exists()
    assert (target / "config" / "mcp.test-bundle.json").exists()
    cfg = json.loads(
        (target / "config" / "mcp.test-bundle.json").read_text(encoding="utf-8")
    )
    assert cfg["servers"][0]["name"].startswith("test-bundle-")


# ---- Gemini CLI -------------------------------------------------------


def test_gemini_cli_export_layout(tmp_path):
    b = _bundle(tmp_path)
    target = tmp_path / "out_gem"
    GeminiCLIExporter().export(b, target=target)
    ext_root = target / ".gemini" / "extensions" / "test-bundle"
    assert (ext_root / "gemini-extension.json").exists()
    assert (ext_root / "GEMINI.md").exists()
    assert (ext_root / "skills" / "01-greet.md").exists()
    meta = json.loads((ext_root / "gemini-extension.json").read_text(encoding="utf-8"))
    assert meta["name"] == "test-bundle"
    assert "test-bundle-code-search" in meta["mcpServers"]


# ---- LBL-EXPORT-NO-LEAK ----------------------------------------------


def test_export_refuses_path_escape(tmp_path, monkeypatch):
    """Exporters must enforce LBL-EXPORT-NO-LEAK against a malicious skill name."""

    b = _bundle(tmp_path)
    e = ClaudeCodeExporter()
    target = tmp_path / "out"
    target.mkdir()
    # Try to write outside the target dir.
    with pytest.raises(ExportError):
        e._safe_within(target, target / ".." / "evil.md")


# ---- end-to-end with all four targets --------------------------------


def test_all_exporters_complete(tmp_path):
    b = _bundle(tmp_path)
    for tgt in list_exporters():
        out = tmp_path / f"out_{tgt}"
        manifest = resolve_exporter(tgt).export(b, target=out)
        assert manifest.files, f"{tgt} produced no files"

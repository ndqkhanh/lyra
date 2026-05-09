"""Tests for :mod:`lyra_cli.diagnostics`."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.diagnostics import (
    Probe,
    configured_providers,
    probe_packages,
    probe_providers,
    probe_runtime,
    probe_state,
    run_all,
)


@pytest.fixture(autouse=True)
def _isolate_provider_env(monkeypatch):
    """Strip every provider env var so the fixture state is deterministic.

    Tests opt-in by setting the env vars they need.
    """
    for name in (
        "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY",
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY", "GROK_API_KEY",
        "GROQ_API_KEY", "CEREBRAS_API_KEY", "MISTRAL_API_KEY",
        "DASHSCOPE_API_KEY", "QWEN_API_KEY", "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------


def test_probe_runtime_reports_python_and_platform() -> None:
    rows = probe_runtime()
    by_name = {p.name: p for p in rows}
    assert "python" in by_name and by_name["python"].ok
    assert "platform" in by_name
    assert "git" in by_name


def test_probe_providers_reports_missing_keys_by_default() -> None:
    rows = probe_providers()
    # Every row in this category must have meta.env_vars set.
    for p in rows:
        assert p.category == "providers"
        assert p.meta.get("env_vars")
        assert p.ok is False


def test_probe_providers_picks_up_set_env_var(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test")
    rows = probe_providers()
    deepseek = next(p for p in rows if p.name == "deepseek-key")
    assert deepseek.ok is True
    assert deepseek.meta["found"] == "DEEPSEEK_API_KEY"


def test_probe_providers_handles_alternative_env_vars(monkeypatch) -> None:
    """``GOOGLE_API_KEY`` should satisfy the gemini probe."""
    monkeypatch.setenv("GOOGLE_API_KEY", "g-test")
    rows = probe_providers()
    gemini = next(p for p in rows if p.name == "gemini-key")
    assert gemini.ok is True
    assert gemini.meta["found"] == "GOOGLE_API_KEY"


def test_probe_state_reports_repo_layout(tmp_path: Path) -> None:
    rows = probe_state(tmp_path)
    by_name = {p.name: p for p in rows}
    # Empty repo: state probes must report missing for SOUL.md / policy / dirs.
    assert by_name["soul-md"].ok is False
    assert by_name["policy"].ok is False


def test_probe_state_after_init(tmp_path: Path) -> None:
    layout_dir = tmp_path / ".lyra"
    layout_dir.mkdir()
    (layout_dir / "policy.yaml").write_text("version: 1\n")
    (tmp_path / "SOUL.md").write_text("# soul")
    rows = probe_state(tmp_path)
    by_name = {p.name: p for p in rows}
    assert by_name["soul-md"].ok is True
    assert by_name["policy"].ok is True


def test_probe_packages_reports_lyra_packages() -> None:
    rows = probe_packages()
    names = [p.name for p in rows]
    assert "lyra-core" in names
    assert "lyra-cli" in names
    # Optional integrations always show up too, even when not installed.
    assert any(p.name == "langsmith" for p in rows)


def test_probe_packages_marks_optional_as_optional() -> None:
    rows = probe_packages()
    optional_names = {"langsmith", "langfuse", "aiosandbox", "docker"}
    for p in rows:
        if p.name in optional_names:
            assert p.meta["optional"] is True


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------


def test_run_all_includes_every_category(tmp_path: Path) -> None:
    rows = run_all(tmp_path)
    cats = {p.category for p in rows}
    assert {"runtime", "state", "providers", "packages", "integration"} <= cats


def test_configured_providers_returns_slug_list(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "an")
    slugs = configured_providers()
    assert "deepseek" in slugs
    assert "anthropic" in slugs


def test_probe_to_dict_round_trips_via_json() -> None:
    import json

    p = Probe(
        category="cat", name="n", ok=True, detail="d",
        meta={"k": [1, 2, "v"]},
    )
    json.dumps(p.to_dict())  # must not raise

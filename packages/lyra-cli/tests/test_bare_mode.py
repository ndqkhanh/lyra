"""Tests for the v3.10 ``--bare`` boot mode.

Bare mode is the deterministic posture: every auto-discovery surface
(skills inject, memory inject, MCP autoload, cron daemon, settings.json
permissions/hooks) is suppressed so the session's behaviour is fully
derived from explicit CLI flags. CI runs and headless harnesses use
this to make sure a stale ``~/.lyra/settings.json`` left on the box
can't change the outcome of a test.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _run_with_bare(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bare: bool):
    """Boot the driver up to (but not into) the prompt loop and capture
    the session it built.

    We patch the parts of ``run`` that would block on stdin / open a
    real REPL — the goal is to observe the side effects of bare-mode
    setup, not to run an actual session.
    """
    from lyra_cli.interactive import driver as _driver
    from lyra_cli.interactive.session import InteractiveSession

    captured: dict = {}

    real_init = InteractiveSession.__init__

    def _capture_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        captured["session"] = self

    monkeypatch.setattr(InteractiveSession, "__init__", _capture_init)

    # Stop run() before it enters the prompt loop. The simplest way:
    # raise after _apply_budget_settings has finished executing the
    # bare-mode block — patch _apply_budget_settings to raise SystemExit.
    def _stop(*_a, **_kw):
        raise SystemExit(0)

    monkeypatch.setattr(_driver, "_apply_budget_settings", _stop)

    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(SystemExit):
        _driver.run(
            repo_root=repo,
            model="mock",
            mode="agent",
            bare=bare,
        )
    return captured["session"]


# ---------------------------------------------------------------------------
# bare=True — every auto-discovery toggle flips off
# ---------------------------------------------------------------------------


def test_bare_disables_skills_inject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _run_with_bare(monkeypatch, tmp_path, bare=True)
    assert session.skills_inject_enabled is False


def test_bare_disables_memory_inject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _run_with_bare(monkeypatch, tmp_path, bare=True)
    assert session.memory_inject_enabled is False


def test_bare_pre_caches_empty_policy_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tool dispatch should never read settings.json under ``--bare``.

    The cache contract is ``(policy, hook_specs, enabled)``; the bare
    sentinel is ``(None, [], False)`` — None means "no user rules,
    fall back to LOW_RISK + ASK", which is the deterministic posture.
    """
    session = _run_with_bare(monkeypatch, tmp_path, bare=True)
    cache = getattr(session, "_policy_hooks_cache", None)
    assert cache is not None
    policy, specs, enabled = cache
    assert policy is None
    assert specs == []
    assert enabled is False


# ---------------------------------------------------------------------------
# bare=False — defaults remain on so a normal REPL boot is unchanged
# ---------------------------------------------------------------------------


def test_default_keeps_skills_inject_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _run_with_bare(monkeypatch, tmp_path, bare=False)
    assert session.skills_inject_enabled is True


def test_default_does_not_pre_cache_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _run_with_bare(monkeypatch, tmp_path, bare=False)
    # Field is only set by _approve's lazy loader (or by bare). Absent
    # cache means the session would actually consult settings.json on
    # the first tool call — that's the non-bare posture.
    assert getattr(session, "_policy_hooks_cache", None) is None


# ---------------------------------------------------------------------------
# CLI flag plumbing
# ---------------------------------------------------------------------------


def test_cli_flag_propagates_to_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Typer ``--bare`` must reach driver.run as ``bare=True``.

    Patches the driver entry point so we can sniff its kwargs without
    actually starting a REPL.
    """
    from lyra_cli.interactive import driver as _driver

    captured: dict = {}

    def _fake_run(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(_driver, "run", _fake_run)
    # ``__main__`` reads the symbol via ``from .interactive.driver import
    # run as _run_interactive`` *inside* the callback, so patching
    # the module's ``run`` is enough.

    from typer.testing import CliRunner

    from lyra_cli.__main__ import app

    # v3.14: bare default flipped to Textual shell, so the legacy REPL
    # only fires under ``--legacy``. The contract this test guards —
    # that ``--bare`` reaches ``driver.run`` — is unchanged.
    result = CliRunner().invoke(
        app, ["--legacy", "--bare", "--repo-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert captured.get("bare") is True

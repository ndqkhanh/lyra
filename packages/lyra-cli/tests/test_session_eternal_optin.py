"""Test the LYRA_ETERNAL_SUBAGENT_DIR opt-in in _ensure_subagent_registry.

The full path (constructing a real provider, materialising _LyraCoreLLMAdapter,
running an actual /task) is exercised by integration tests with live
providers. Here we verify the *conditional* — when the env var is set,
the loop factory is wrapped through eternal-mode; when unset, it isn't.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest


# Avoid importing the real session.py at module-import time — it pulls in
# heavy interactive stack. We monkeypatch its dependencies before we
# reach into _ensure_subagent_registry.


def _make_fake_session(repo_root: Path):
    s = types.SimpleNamespace()
    s.repo_root = str(repo_root)
    s.model = "auto"
    s.subagent_registry = None
    return s


def _patch_provider_stack(monkeypatch):
    """Replace the provider/model machinery with no-op stubs so we can
    exercise _ensure_subagent_registry without a live provider."""

    fake_provider_module = types.ModuleType("lyra_cli.llm_factory")

    def _build_llm(_model: str):
        class _Stub:
            def generate(self, *, messages, **_kw):
                return {"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}

        return _Stub()

    fake_provider_module.build_llm = _build_llm
    monkeypatch.setitem(sys.modules, "lyra_cli.llm_factory", fake_provider_module)


def test_env_unset_does_not_call_make_eternal_loop_factory(tmp_path, monkeypatch):
    monkeypatch.delenv("LYRA_ETERNAL_SUBAGENT_DIR", raising=False)
    _patch_provider_stack(monkeypatch)

    from lyra_cli.interactive.session import _ensure_subagent_registry

    fake_session = _make_fake_session(tmp_path)

    # Spy on make_eternal_loop_factory.
    calls = {"n": 0}
    import lyra_cli.eternal_factory as ef
    original = ef.make_eternal_loop_factory

    def _spy(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(ef, "make_eternal_loop_factory", _spy)

    reg = _ensure_subagent_registry(fake_session)
    assert reg is not None
    assert calls["n"] == 0  # eternal-factory was NOT called


def test_env_set_calls_make_eternal_loop_factory(tmp_path, monkeypatch):
    state_dir = tmp_path / "eternal-spawn"
    monkeypatch.setenv("LYRA_ETERNAL_SUBAGENT_DIR", str(state_dir))
    _patch_provider_stack(monkeypatch)

    from lyra_cli.interactive.session import _ensure_subagent_registry

    fake_session = _make_fake_session(tmp_path)

    calls: list[dict] = []
    import lyra_cli.eternal_factory as ef
    original = ef.make_eternal_loop_factory

    def _spy(inner_factory, **kwargs):
        calls.append({"inner": inner_factory, **kwargs})
        return original(inner_factory, **kwargs)

    monkeypatch.setattr(ef, "make_eternal_loop_factory", _spy)

    reg = _ensure_subagent_registry(fake_session)
    assert reg is not None
    assert len(calls) == 1
    assert Path(calls[0]["state_dir"]) == state_dir
    assert calls[0]["workflow_name"] == "lyra.spawn"


def test_eternal_wrap_failure_falls_back_to_plain_factory(tmp_path, monkeypatch):
    """A bug in eternal-mode wiring must NOT break /spawn."""
    monkeypatch.setenv("LYRA_ETERNAL_SUBAGENT_DIR", str(tmp_path / "eternal"))
    _patch_provider_stack(monkeypatch)

    import lyra_cli.eternal_factory as ef

    def _broken(*_a, **_kw):
        raise RuntimeError("simulated eternal-factory failure")

    monkeypatch.setattr(ef, "make_eternal_loop_factory", _broken)

    from lyra_cli.interactive.session import _ensure_subagent_registry

    fake_session = _make_fake_session(tmp_path)
    reg = _ensure_subagent_registry(fake_session)
    # Despite the eternal-factory failure, the registry was built — /spawn
    # still works on the plain path.
    assert reg is not None

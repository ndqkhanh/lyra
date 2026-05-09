"""Phase F: Claude-Code-style small/smart split (v2.7.1).

Lyra now ships two model "slots" on every interactive session:

* ``fast_model`` (default ``deepseek-v4-flash`` -> ``deepseek-chat``)
  drives plain chat turns, summarisation, ``/compact``, and any cron
  job that doesn't need deep reasoning.
* ``smart_model`` (default ``deepseek-v4-pro`` -> ``deepseek-reasoner``)
  drives ``/spawn``, ``/plan``, ``/review`` (when LLM-judge lands),
  and any path the agent loop classifies as reasoning-heavy.

These tests pin:

1. The defaults are wired correctly.
2. ``_resolve_model_for_role`` returns the correct slot for the role.
3. ``_stamp_model_env`` resolves the alias and stamps both
   ``HARNESS_LLM_MODEL`` and the provider-specific MODEL env var.
4. ``_apply_role_model`` mutates a cached provider's ``model`` attr.
5. ``/model`` slash supports ``fast``, ``smart``, ``fast=<slug>``,
   and ``smart=<slug>``.
6. The subagent ``_loop_factory`` activates the smart slot before
   the provider is built.

Test isolation note: every test that mutates env vars uses
``monkeypatch.delenv`` / ``monkeypatch.setenv`` so the slot stamping
cannot leak between tests (or into the rest of the suite).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lyra_cli.interactive.session import (
    InteractiveSession,
    _apply_role_model,
    _cmd_model,
    _resolve_model_for_role,
    _stamp_model_env,
)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_session_defaults_to_deepseek_v4_flash_for_fast_slot(tmp_path: Path) -> None:
    """Plain chat should default to the cheap DeepSeek tier (V4 Flash)."""
    s = InteractiveSession(repo_root=tmp_path)
    assert s.fast_model == "deepseek-v4-flash"


def test_session_defaults_to_deepseek_v4_pro_for_smart_slot(tmp_path: Path) -> None:
    """Reasoning paths should default to DeepSeek's R1 reasoner (V4 Pro)."""
    s = InteractiveSession(repo_root=tmp_path)
    assert s.smart_model == "deepseek-v4-pro"


# ---------------------------------------------------------------------------
# Role resolution
# ---------------------------------------------------------------------------


def test_resolve_model_for_role_chat_returns_fast(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, fast_model="haiku", smart_model="opus")
    assert _resolve_model_for_role(s, "chat") == "haiku"


def test_resolve_model_for_role_reasoning_returns_smart(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, fast_model="haiku", smart_model="opus")
    for role in ("smart", "reasoning", "plan", "review", "verify", "spawn", "subagent"):
        assert _resolve_model_for_role(s, role) == "opus", f"role={role!r}"


def test_resolve_model_for_role_unknown_falls_back_to_fast(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, fast_model="haiku", smart_model="opus")
    assert _resolve_model_for_role(s, "totally-made-up-role") == "haiku"


def test_empty_slot_returns_none(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, fast_model="", smart_model="")
    assert _resolve_model_for_role(s, "chat") is None
    assert _resolve_model_for_role(s, "smart") is None


# ---------------------------------------------------------------------------
# Env stamping
# ---------------------------------------------------------------------------


def test_stamp_model_env_writes_harness_and_deepseek_for_v4_flash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``deepseek-v4-flash`` -> ``deepseek-chat`` -> stamps DEEPSEEK_MODEL too."""
    for key in ("HARNESS_LLM_MODEL", "DEEPSEEK_MODEL", "OPEN_HARNESS_DEEPSEEK_MODEL"):
        monkeypatch.delenv(key, raising=False)

    slug = _stamp_model_env("deepseek-v4-flash")

    assert slug == "deepseek-chat"
    import os
    assert os.environ["HARNESS_LLM_MODEL"] == "deepseek-chat"
    assert os.environ["DEEPSEEK_MODEL"] == "deepseek-chat"
    assert os.environ["OPEN_HARNESS_DEEPSEEK_MODEL"] == "deepseek-chat"


def test_stamp_model_env_writes_reasoner_for_v4_pro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("HARNESS_LLM_MODEL", "DEEPSEEK_MODEL", "OPEN_HARNESS_DEEPSEEK_MODEL"):
        monkeypatch.delenv(key, raising=False)

    slug = _stamp_model_env("deepseek-v4-pro")

    assert slug == "deepseek-reasoner"
    import os
    assert os.environ["DEEPSEEK_MODEL"] == "deepseek-reasoner"


def test_stamp_model_env_for_anthropic_alias_only_stamps_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anthropic providers read HARNESS_LLM_MODEL; no preset-specific stamp."""
    for key in ("HARNESS_LLM_MODEL", "ANTHROPIC_MODEL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(key, raising=False)

    slug = _stamp_model_env("opus")

    assert slug == "claude-opus-4.5"
    import os
    assert os.environ["HARNESS_LLM_MODEL"] == "claude-opus-4.5"
    # We don't fabricate ANTHROPIC_MODEL — there's no such preset env;
    # the upstream anthropic SDK reads HARNESS_LLM_MODEL via the lyra
    # Anthropic provider.
    assert "ANTHROPIC_MODEL" not in os.environ


def test_stamp_model_env_returns_none_for_empty_alias() -> None:
    assert _stamp_model_env("") is None
    assert _stamp_model_env("   ") is None


def test_stamp_model_env_unknown_alias_returns_input_and_stamps_universal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unregistered slug isn't an error; it stamps verbatim into HARNESS_LLM_MODEL.

    This is the escape hatch for users who paste exotic model slugs
    (e.g. an OpenRouter-only sub-route or a private finetune) without
    waiting for an alias entry.
    """
    monkeypatch.delenv("HARNESS_LLM_MODEL", raising=False)

    slug = _stamp_model_env("private-finetune-xyz-7b")

    assert slug == "private-finetune-xyz-7b"
    import os
    assert os.environ["HARNESS_LLM_MODEL"] == "private-finetune-xyz-7b"


# ---------------------------------------------------------------------------
# Provider mutation
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Stand-in for OpenAICompatibleLLM with a settable ``model`` attr."""
    def __init__(self, model: str) -> None:
        self.model = model


def test_apply_role_model_mutates_cached_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switching role re-points the cached provider WITHOUT rebuilding it."""
    for k in ("HARNESS_LLM_MODEL", "DEEPSEEK_MODEL", "OPEN_HARNESS_DEEPSEEK_MODEL"):
        monkeypatch.delenv(k, raising=False)

    s = InteractiveSession(repo_root=tmp_path)
    s._llm_provider = _FakeProvider(model="deepseek-chat")

    slug = _apply_role_model(s, "smart")

    assert slug == "deepseek-reasoner"
    assert s._llm_provider.model == "deepseek-reasoner"

    slug = _apply_role_model(s, "chat")
    assert slug == "deepseek-chat"
    assert s._llm_provider.model == "deepseek-chat"


def test_apply_role_model_works_with_no_cached_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stamping is fine when the provider hasn't been built yet."""
    for k in ("HARNESS_LLM_MODEL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(k, raising=False)

    s = InteractiveSession(repo_root=tmp_path)
    assert s._llm_provider is None

    slug = _apply_role_model(s, "smart")

    assert slug == "deepseek-reasoner"
    import os
    assert os.environ["DEEPSEEK_MODEL"] == "deepseek-reasoner"


# ---------------------------------------------------------------------------
# /model slash UX
# ---------------------------------------------------------------------------


def test_slash_model_no_args_shows_slot_summary(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_model(s, "")
    assert "current model:" in result.output
    assert "fast slot:" in result.output
    assert "deepseek-v4-flash" in result.output
    assert "smart slot:" in result.output
    assert "deepseek-v4-pro" in result.output


def test_slash_model_fast_equals_pins_slot(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s._llm_provider = _FakeProvider(model="deepseek-chat")
    s._llm_provider_kind = "auto"

    result = _cmd_model(s, "fast=haiku")

    assert s.fast_model == "haiku"
    assert "fast slot set to: haiku" in result.output
    # Cached provider must be invalidated so the next chat turn picks
    # up the new slot.
    assert s._llm_provider is None
    assert s._llm_provider_kind is None


def test_slash_model_smart_equals_pins_slot(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_model(s, "smart=opus")
    assert s.smart_model == "opus"
    assert "smart slot set to: opus" in result.output


def test_slash_model_fast_without_value_one_shot_uses_fast_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``/model fast`` (no ``=``) re-stamps env to the current fast slot.

    Useful when the user just nudged smart on for a single turn and
    wants to flip back to fast for the next one — without losing the
    pinned slot values.
    """
    for k in ("HARNESS_LLM_MODEL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(k, raising=False)

    s = InteractiveSession(repo_root=tmp_path, fast_model="deepseek-v4-flash")
    s._llm_provider = _FakeProvider(model="deepseek-reasoner")  # was on smart

    result = _cmd_model(s, "fast")

    assert "next turn will use fast slot" in result.output
    # The provider was mutated in-place to the fast slug.
    assert s._llm_provider.model == "deepseek-chat"
    import os
    assert os.environ["DEEPSEEK_MODEL"] == "deepseek-chat"


def test_slash_model_legacy_kind_pin_still_works(tmp_path: Path) -> None:
    """``/model anthropic`` is the v2.6 backend pin; must still work."""
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_model(s, "anthropic")
    assert s.model == "anthropic"
    assert "model set to: anthropic" in result.output


def test_slash_model_list_still_renders_provider_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``/model list`` is unchanged — provider table with markers."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    s = InteractiveSession(repo_root=tmp_path)
    result = _cmd_model(s, "list")
    assert "Available providers:" in result.output


def test_slash_model_fast_empty_slot_complains(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, fast_model="")
    result = _cmd_model(s, "fast")
    assert "fast slot is empty" in result.output


# ---------------------------------------------------------------------------
# Subagent path uses smart slot
# ---------------------------------------------------------------------------


def test_subagent_spawn_stamps_smart_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``/spawn`` MUST set DEEPSEEK_MODEL=reasoner before the LLM is built.

    This is the regression test for the small/smart split: a subagent
    is reasoning-heavy by definition, so the smart slot is what the
    LLM provider should see when it reads its model env var.

    We inject a fake ``build_llm`` that snapshots the env at build time,
    then drive a real ``SubagentRegistry.spawn`` so the full code path
    (``_ensure_subagent_registry`` -> ``SubagentRunner.run`` ->
    ``_loop_factory`` -> ``build_llm``) is exercised end-to-end.
    """
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    for k in ("HARNESS_LLM_MODEL", "DEEPSEEK_MODEL", "OPEN_HARNESS_DEEPSEEK_MODEL"):
        monkeypatch.delenv(k, raising=False)

    captured: dict[str, Any] = {}

    def _fake_build_llm(kind: str, **_kw: Any):
        import os as _os
        captured.setdefault(
            "model_at_build_time",
            _os.environ.get("DEEPSEEK_MODEL", ""),
        )
        captured["kind"] = kind

        class _Fake:
            model = ""

            def generate(self, messages: list[Any], **__: Any):
                from harness_core.messages import Message, StopReason
                return Message(
                    role="assistant",
                    content="ok",
                    stop_reason=StopReason.END_TURN,
                )

        return _Fake()

    monkeypatch.setattr("lyra_cli.llm_factory.build_llm", _fake_build_llm)

    from lyra_cli.interactive.session import _ensure_subagent_registry

    s = InteractiveSession(repo_root=tmp_path)
    reg = _ensure_subagent_registry(s)

    if reg is None:
        pytest.skip("lyra_core subagent stack not importable in this env")

    rec = reg.spawn("smoke-test description")

    assert rec.state in ("done", "failed")
    assert captured.get("model_at_build_time") == "deepseek-reasoner", (
        "subagent path must stamp the smart slot before build_llm reads env: "
        f"got {captured!r}"
    )

"""Phase 1 RED — production-ready defaults (no MockLLM auto-fallback, run executes).

The Phase 1 contract for "Lyra v2.1 Claude-Code-Class" rebuild:

1. ``lyra`` (the REPL entry-point) defaults ``--model`` to ``"auto"``,
   not ``"mock"``. The status bar should resolve a real backend when one
   is configured, or surface ``"unconfigured"`` rather than misleading
   the user with a mock.
2. ``lyra run --no-plan <task>`` actually executes the agent loop. It is
   no longer a "Phase 2 stub" that prints and exits.
3. ``build_llm("auto")`` with no provider configured raises
   :class:`NoProviderConfigured`. The silent downgrade to MockLLM is
   removed — production users must see a clear setup message instead of
   a fake "agent" answering with canned plan text.
4. ``build_llm("mock")`` keeps working — explicit mock is a deliberate
   testing affordance, not a default.
5. ``InteractiveSession`` and ``store.load`` default ``model="auto"``
   (not ``"mock"``).

These tests are RED before Phase 1 implementation lands; they go GREEN
once ``llm_factory.py``, ``run.py``, ``__main__.py``, ``session.py`` and
``store.py`` are updated together.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from typer.testing import CliRunner


# All credential env vars the cascade reads. Cleared in fixtures so the
# "no provider configured" branch is exercised deterministically.
_PROVIDER_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_REASONING_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "DASHSCOPE_API_KEY",
    "QWEN_API_KEY",
    "OLLAMA_HOST",
    "LMSTUDIO_HOST",
)


@pytest.fixture
def isolated_no_providers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Path]:
    """Wipe every provider credential and isolate cwd from developer .env files.

    The auto-cascade also walks ancestor directories looking for a
    ``.env`` and probes ``ollama_reachable`` / ``lmstudio_reachable``
    over HTTP; we stub those out so the test is hermetic regardless of
    what's running on the developer's box.
    """
    for k in _PROVIDER_KEYS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)

    # Block dotenv walks so an ancestor .env can't smuggle keys back in.
    monkeypatch.setattr(
        "lyra_cli.llm_factory._hydrate_env_from_dotenv", lambda: None
    )
    # Block local-daemon probes so the cascade can't auto-pick LM Studio
    # or Ollama just because the dev happens to have one running.
    monkeypatch.setattr("lyra_cli.llm_factory.ollama_reachable", lambda: False)
    try:
        monkeypatch.setattr(
            "lyra_cli.providers.openai_compatible.lmstudio_reachable",
            lambda: False,
        )
    except AttributeError:
        # Older codepaths may not expose ``lmstudio_reachable``; tolerate.
        pass

    yield tmp_path


# ---------------------------------------------------------------------------
# Contract 1: build_llm("auto") with no providers must raise.
# ---------------------------------------------------------------------------


def test_build_llm_auto_with_no_providers_raises_no_provider_configured(
    isolated_no_providers: Path,
) -> None:
    """No keys + no daemons → :class:`NoProviderConfigured`, not a MockLLM.

    The "silent downgrade to mock" was Lyra v0.1's Achilles heel: users
    who forgot to set an API key got a fake assistant answering canned
    plan text. v2.1 fails loud so the user gets a clear setup hint.
    """
    from lyra_cli.llm_factory import NoProviderConfigured, build_llm

    with pytest.raises(NoProviderConfigured) as exc:
        build_llm("auto")

    msg = str(exc.value).lower()
    # The error must point the user at the fix, not just say "no key".
    assert "no provider" in msg or "unconfigured" in msg or "set" in msg, (
        f"NoProviderConfigured should hint at remediation, got: {exc.value!r}"
    )


def test_build_llm_explicit_mock_still_works(
    isolated_no_providers: Path,
) -> None:
    """``--llm mock`` remains a valid explicit choice for tests/docs.

    The change is the *default* behaviour, not the explicit one — mock
    is still a first-class addressable backend; it's only the auto
    cascade that no longer falls through to it.
    """
    from harness_core.models import MockLLM
    from lyra_cli.llm_factory import build_llm

    llm = build_llm("mock")
    assert isinstance(llm, MockLLM), (
        f"explicit --llm mock must keep returning a MockLLM, got {type(llm).__name__}"
    )


def test_build_llm_auto_picks_anthropic_when_only_anthropic_is_configured(
    isolated_no_providers: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto-cascade still picks the first configured provider.

    Sanity check that we didn't accidentally break the *positive* path
    while ripping out the mock fallback.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    # The cascade also requires the ``anthropic`` package to import
    # successfully; if it isn't present in this env, we skip.
    try:
        import anthropic  # noqa: F401
    except ImportError:
        pytest.skip("anthropic SDK not available in this environment")

    from harness_core.models import AnthropicLLM
    from lyra_cli.llm_factory import build_llm

    llm = build_llm("auto")
    assert isinstance(llm, AnthropicLLM)


# ---------------------------------------------------------------------------
# Contract 2: REPL default model is "auto", not "mock".
# ---------------------------------------------------------------------------


def test_repl_default_model_is_auto_not_mock(
    isolated_no_providers: Path,
    tmp_path: Path,
) -> None:
    """Running ``lyra`` with no ``--model`` should not spawn a mock REPL.

    The interactive session's status bar previously showed
    ``model mock`` because the typer default was hardcoded to that
    string. Phase 1 changes the default to ``"auto"``; a follow-up
    Phase 5 (status bar v2) renders the resolved provider, but the
    default at *this* layer must be ``"auto"``.
    """
    from lyra_cli.__main__ import app

    # Initialise the repo so the REPL has a state dir to write to.
    runner = CliRunner()
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])

    # Feed ``/exit`` so the loop terminates deterministically; the
    # banner + status bar render in the captured stdout before exit.
    result = runner.invoke(
        app,
        ["--repo-root", str(tmp_path)],
        input="/exit\n",
    )
    assert result.exit_code == 0, result.stdout
    out = result.stdout
    # The Phase 1 banner must NOT advertise ``model mock`` as the
    # default — that's what the user complained about.
    assert "model   mock" not in out and "model mock" not in out, (
        "REPL banner still shows hard-coded ``model mock`` default; "
        "the typer ``--model`` default must change to ``auto``.\n"
        f"banner output:\n{out}"
    )


def test_interactive_session_default_model_is_auto() -> None:
    """The dataclass default propagates everywhere; lock it down."""
    from lyra_cli.interactive.session import InteractiveSession

    s = InteractiveSession(repo_root=Path("/tmp"))
    assert s.model == "auto", (
        f"InteractiveSession.model must default to 'auto', got {s.model!r}"
    )


def test_store_load_uses_auto_when_snapshot_omits_model(
    tmp_path: Path,
) -> None:
    """An old snapshot without a ``model`` field must load as ``"auto"``.

    Backwards-compat: snapshots written by Lyra <2.1 may have no
    ``model`` key (the fallback used to be ``"mock"``). On load we now
    coerce missing values to ``"auto"`` so resumed sessions never
    accidentally land on the mock provider.
    """
    import json

    sessions = tmp_path / ".lyra" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    snapshot = sessions / "2026-04-26T00-00-00-000000.json"
    snapshot.write_text(
        json.dumps(
            {
                "format": 1,
                "id": "2026-04-26T00-00-00-000000",
                "name": "test-snapshot",
                "saved_at": "2026-04-26T00:00:00+00:00",
                "repo_root": str(tmp_path),
                "state": {
                    # Deliberately no ``model`` key — pre-v2.1 schema.
                    "mode": "plan",
                    "turn": 0,
                    "cost_usd": 0.0,
                    "tokens_used": 0,
                    "history": [],
                    "pending_task": None,
                    "deep_think": False,
                    "verbose": False,
                    "vim_mode": False,
                    "theme": "aurora",
                    "budget_cap_usd": None,
                    "task_panel": False,
                    "turns_log": [],
                },
            }
        ),
        encoding="utf-8",
    )

    from lyra_cli.interactive import store

    session = store.load(tmp_path)
    assert session.model == "auto", (
        f"store.load must coerce missing model to 'auto' for forward "
        f"compat, got {session.model!r}"
    )


# ---------------------------------------------------------------------------
# Contract 3: ``lyra run --no-plan`` actually executes the agent loop.
# ---------------------------------------------------------------------------


def test_run_no_plan_invokes_agent_loop_run_method(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``lyra run --no-plan "task"`` must actually invoke ``AgentLoop.run``.

    Pre-Phase-1 the run command exited at "Phase 2 CLI currently stops
    here" without ever instantiating an agent loop. The user's bug
    report — "DeepSeek key set, run finishes silently with no answer" —
    traces directly back to this stub.
    """
    from lyra_cli.__main__ import app

    runner = CliRunner()
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])

    # Spy on AgentLoop.run so we can prove the wiring fires.
    invoked: list[dict] = []
    from harness_core import loop as _loop_mod

    real_run = _loop_mod.AgentLoop.run

    def spy_run(self: object, task: str, initial_messages=None):  # type: ignore[no-untyped-def]
        invoked.append({"task": task, "self": self})
        return real_run(self, task, initial_messages)  # type: ignore[arg-type]

    monkeypatch.setattr(_loop_mod.AgentLoop, "run", spy_run)

    result = runner.invoke(
        app,
        [
            "run",
            "say hello world and nothing else",
            "--repo-root",
            str(tmp_path),
            "--llm",
            "mock",
            "--no-plan",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert invoked, (
        "AgentLoop.run was never called. ``lyra run`` is still a stub "
        f"that exits without executing.\nstdout:\n{result.stdout}"
    )
    assert invoked[0]["task"] == "say hello world and nothing else", (
        f"AgentLoop.run got the wrong task arg: {invoked[0]!r}"
    )


def test_run_no_plan_with_unconfigured_auto_surfaces_setup_hint(
    isolated_no_providers: Path,
    tmp_path: Path,
) -> None:
    """A user who runs ``lyra run --no-plan task`` with no API key set
    must get an actionable error, not a silent Mock answer.

    This is the exact UX failure mode the user filed: "I set the env
    vars but Lyra answered with mock canned text". After Phase 1 the
    cascade refuses to silently downgrade and the CLI surfaces a
    setup-friendly message.
    """
    from lyra_cli.__main__ import app

    runner = CliRunner()
    runner.invoke(app, ["init", "--repo-root", str(tmp_path)])

    result = runner.invoke(
        app,
        [
            "run",
            "hello",
            "--repo-root",
            str(tmp_path),
            "--llm",
            "auto",
            "--no-plan",
        ],
    )
    # Should fail loud with a non-zero exit and at least one of these
    # actionable hints in the output.
    assert result.exit_code != 0, (
        "lyra run with no provider configured should NOT exit 0; "
        f"that means we silently downgraded to mock again.\n"
        f"stdout:\n{result.stdout}"
    )
    out = result.stdout.lower()
    assert any(
        hint in out
        for hint in (
            "no provider",
            "unconfigured",
            "set ",
            "api key",
            "configure",
        )
    ), f"setup hint missing; got:\n{result.stdout}"

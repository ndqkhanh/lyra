"""Tests for the v2.2.1 chat-mode rewiring (refreshed for v3.6.0).

The plain-text mode handlers used to print canned ``"would implement: ..."``
strings — typing ``hello`` into the REPL gave you nothing useful. After
v2.2.1 each active mode calls the LLM with a mode-specific system prompt
and renders the reply.

v3.6.0 replaced v3.2's behavioural taxonomy
(``agent`` / ``plan`` / ``debug`` / ``ask``) with a permission-flavoured
one: ``edit_automatically`` / ``ask_before_edits`` / ``plan_mode`` /
``auto_mode``. Every legacy name from prior taxonomies (v3.2:
agent/plan/debug/ask; pre-v3.2: build/run/explore/retro) is accepted
as an alias and remaps to a canonical v3.6 mode — see
``InteractiveSession._LEGACY_MODE_REMAP``.
The legacy ``retro`` mode now remaps to ``auto_mode`` (the closest
preserved behaviour: a router that picks the right sub-mode per
turn, with debug-flavoured prompts routing to ``ask_before_edits``);
journaling stays on the ``lyra retro`` CLI subcommand.

These tests stub :func:`lyra_cli.llm_factory.build_llm` so we never make
a network call, then assert:

* the handler routes through ``build_llm`` with the active model,
* the reply is rendered by :func:`output.chat_renderable` (not the old
  ``build_renderable`` / ``plan_renderable`` stubs),
* the system prompt the LLM sees is mode-appropriate,
* the LLM is built once and cached for subsequent turns,
* a failed ``build_llm`` collapses to a friendly error renderable
  (the REPL must never crash on a missing key),
* plan-mode still records ``pending_task`` so ``/approve`` keeps working,
* ``/model`` invalidates the cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from harness_core.messages import Message

from lyra_cli.interactive.session import InteractiveSession

# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------


class FakeLLM:
    """Minimal stand-in for :class:`harness_core.models.LLMProvider`.

    Records every ``generate`` call so tests can assert on the system
    prompt and the rolling history that gets sent. Mirrors the
    ``last_usage`` / ``cumulative_usage`` contract that the OpenAI-
    compatible provider exposes so the billing path can be exercised.
    """

    def __init__(
        self,
        *,
        reply: str = "hello back!",
        usage: dict[str, int] | None = None,
        model: str = "deepseek-v4-pro",
    ) -> None:
        self.reply = reply
        self.calls: list[list[Message]] = []
        # Default usage matches a typical 'hello' round-trip, in the
        # same shape that ``OpenAICompatibleLLM._record_usage`` writes.
        self.last_usage: dict[str, int] = (
            dict(usage) if usage is not None else {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        )
        self.model = model

    def generate(
        self,
        messages: list[Message],
        tools: Any = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        self.calls.append(list(messages))
        return Message(role="assistant", content=self.reply)


@pytest.fixture
def session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path, model="deepseek")


# ---------------------------------------------------------------------------
# Default mode is agent (Claude-Code-style: type → reply)
# ---------------------------------------------------------------------------


def test_plain_text_in_build_calls_llm(session: InteractiveSession) -> None:
    fake = FakeLLM(reply="hi! what would you like to build?")
    with patch(
        "lyra_cli.llm_factory.build_llm", return_value=fake
    ) as build_llm_mock:
        result = session.dispatch("hello")

    build_llm_mock.assert_called_once_with("deepseek")
    assert fake.calls, "LLM.generate must be called for plain-text input"
    # Output is the model's reply — no more "would implement: ..." stubs.
    assert "hi! what would you like to build?" in result.output
    assert result.renderable is not None


def test_build_system_prompt_mentions_build(
    session: InteractiveSession,
) -> None:
    """The system prompt must steer the model to EDIT_AUTOMATICALLY behaviour.

    v3.2.0 renamed the default mode ``build`` → ``agent``; v3.6.0 then
    renamed ``agent`` → ``edit_automatically``. The legacy test name
    is preserved (so log scrapers and CI history still match) but the
    substring contract now targets the new canonical mode.
    """
    fake = FakeLLM()
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        session.dispatch("write a fibonacci function")

    sent_messages = fake.calls[0]
    assert sent_messages[0].role == "system"
    content = sent_messages[0].content
    # Both the shared preamble and the mode-specific tail must reach
    # the model. The preamble enumerates all four modes; the tail
    # names the active one. Together they kill the screenshot bug
    # where the LLM hallucinated TDD phases as top-level modes.
    assert "EDIT_AUTOMATICALLY" in content, (
        "edit_automatically-mode tail must mention EDIT_AUTOMATICALLY"
    )
    assert (
        "edit_automatically, ask_before_edits, plan_mode, auto_mode"
        in content
    ), "shared preamble must enumerate all four v3.6 modes verbatim"


# ---------------------------------------------------------------------------
# Plan mode: chats AND records pending_task for /approve
# ---------------------------------------------------------------------------


def test_plan_mode_chats_and_queues_task(session: InteractiveSession) -> None:
    session.dispatch("/mode plan")  # legacy alias → plan_mode
    assert session.mode == "plan_mode"
    fake = FakeLLM(reply="that's a solid plan, /approve to ship.")
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        result = session.dispatch("add CSV export")

    assert "that's a solid plan" in result.output
    assert session.pending_task == "add CSV export"
    sent = fake.calls[0]
    assert "PLAN_MODE" in sent[0].content


# ---------------------------------------------------------------------------
# Provider is built once and cached, invalidated on /model
# ---------------------------------------------------------------------------


def test_provider_built_once_per_model(session: InteractiveSession) -> None:
    fake = FakeLLM()
    with patch(
        "lyra_cli.llm_factory.build_llm", return_value=fake
    ) as build_llm_mock:
        session.dispatch("hello")
        session.dispatch("how are you?")
        session.dispatch("ok bye")

    assert build_llm_mock.call_count == 1, (
        "build_llm must be cached on the session — rebuilding every turn "
        "would re-validate the API key on every keystroke."
    )


def test_slash_model_invalidates_cache(session: InteractiveSession) -> None:
    fake1 = FakeLLM(reply="from deepseek")
    fake2 = FakeLLM(reply="from gpt")
    with patch(
        "lyra_cli.llm_factory.build_llm", side_effect=[fake1, fake2]
    ) as build_llm_mock:
        session.dispatch("hi")
        session.dispatch("/model gpt-4o-mini")
        session.dispatch("hi again")

    assert build_llm_mock.call_count == 2
    # Argument order: first call uses deepseek, second uses the new pick.
    call_args = [call.args for call in build_llm_mock.call_args_list]
    assert call_args[0] == ("deepseek",)
    assert call_args[1] == ("gpt-4o-mini",)


# ---------------------------------------------------------------------------
# Conversation history rolls forward
# ---------------------------------------------------------------------------


def test_history_is_threaded_into_the_next_turn(
    session: InteractiveSession,
) -> None:
    fake = FakeLLM(reply="ok")
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        session.dispatch("first message")
        session.dispatch("second message")

    second_call = fake.calls[1]
    # [system, user(first), assistant(reply), user(second)]
    user_contents = [m.content for m in second_call if m.role == "user"]
    assert "first message" in user_contents
    assert "second message" in user_contents


# ---------------------------------------------------------------------------
# Failure modes — the REPL must keep running
# ---------------------------------------------------------------------------


def test_missing_provider_falls_back_to_friendly_error(
    session: InteractiveSession,
) -> None:
    with patch(
        "lyra_cli.llm_factory.build_llm",
        side_effect=RuntimeError("DEEPSEEK_API_KEY not set"),
    ):
        result = session.dispatch("hello")

    assert "llm error" in result.output.lower()
    assert "deepseek_api_key" in result.output.lower()
    assert result.renderable is not None
    # The REPL must not be flagged for exit on a chat error.
    assert not result.should_exit


def test_provider_exception_during_generate_is_caught(
    session: InteractiveSession,
) -> None:
    class ExplodingLLM(FakeLLM):
        def generate(self, *args, **kwargs):  # noqa: D401, ANN001 — test stub
            raise TimeoutError("connection timed out")

    with patch(
        "lyra_cli.llm_factory.build_llm",
        return_value=ExplodingLLM(),
    ):
        result = session.dispatch("hello")

    assert "llm error" in result.output.lower()
    assert "timed out" in result.output.lower()
    assert result.renderable is not None


# ---------------------------------------------------------------------------
# v3.2.0 mode taxonomy contract: ``retro`` no longer exists as an
# interactive non-LLM journaling mode. The ``/mode retro`` alias
# remaps to ``debug`` (an interactive LLM mode); journaling moved to
# the ``lyra retro`` CLI subcommand. The original
# ``test_retro_mode_does_not_call_llm`` is intentionally retired —
# replaced by ``test_legacy_retro_alias_remaps_to_debug_and_calls_llm``
# below — because its postcondition now contradicts the new contract.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Billing — usage capture and cost accumulation
# ---------------------------------------------------------------------------


def test_each_turn_bumps_tokens_used(session: InteractiveSession) -> None:
    """v2.2.2: cost: $0.0000 with 3 turns is a bug. Every turn must bill."""
    fake = FakeLLM(
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    )
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        session.dispatch("hello")
        session.dispatch("ok bye")

    assert session.tokens_used == 300, (
        f"Two 150-token turns should bill 300 tokens, got {session.tokens_used}"
    )


def test_cost_uses_model_pricing(session: InteractiveSession) -> None:
    """``deepseek-v4-pro`` = $0.55 in / $2.19 out per Mtok.

    1000 in + 500 out should cost
    ~ 0.001*0.55 + 0.0005*2.19 = $0.001645.
    """
    session.model = "deepseek-v4-pro"
    fake = FakeLLM(
        usage={"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500},
        model="deepseek-v4-pro",
    )
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        session.dispatch("hi")

    expected = (1000 / 1_000_000) * 0.55 + (500 / 1_000_000) * 2.19
    assert session.cost_usd == pytest.approx(expected, rel=1e-9)


def test_unknown_model_falls_back_to_default_pricing(
    tmp_path: Path,
) -> None:
    """Unknown slugs propagate through unchanged.

    The active provider sees ``some-fictional-llm`` and the price
    table falls back to the universal default of $1.00 / $3.00 per
    Mtok.
    """
    s = InteractiveSession(
        repo_root=tmp_path,
        model="some-fictional-llm",
    )
    fake = FakeLLM(
        usage={"prompt_tokens": 1000, "completion_tokens": 0, "total_tokens": 1000},
        model="some-fictional-llm",
    )
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        s.dispatch("hi")

    # Fallback rate is (1.0, 3.0) USD per Mtok -> 1000 in tokens = $0.001.
    assert s.cost_usd == pytest.approx(0.001, rel=1e-9)


def test_zero_usage_response_does_not_bill(session: InteractiveSession) -> None:
    """Some local providers omit ``usage``. We must not crash and must
    not invent fake numbers."""
    fake = FakeLLM(usage={})
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        session.dispatch("hi")

    assert session.tokens_used == 0
    assert session.cost_usd == 0.0


def test_failed_turn_does_not_bill(session: InteractiveSession) -> None:
    """Failures (network, missing key, empty reply) must leave the
    counters untouched — no charging for a turn that produced no
    answer."""

    class ExplodingLLM(FakeLLM):
        def generate(self, *args, **kwargs):  # noqa: ANN001 — test stub
            raise TimeoutError("connection timed out")

    with patch(
        "lyra_cli.llm_factory.build_llm", return_value=ExplodingLLM()
    ):
        session.dispatch("hello")

    assert session.tokens_used == 0
    assert session.cost_usd == 0.0


def test_legacy_retro_alias_remaps_to_auto_mode_and_calls_llm(
    session: InteractiveSession,
) -> None:
    """v3.6.0 contract: ``retro`` is a legacy alias of ``auto_mode``.

    Pre-v3.2 ``retro`` was a non-LLM journaling mode. v3.2 made it a
    legacy alias of the (then-new) ``debug`` mode. v3.6 dropped the
    dedicated ``debug`` mode entirely; ``retro`` now remaps to
    ``auto_mode`` — a router that picks the right sub-mode per turn.
    Typing a debugging-shaped prompt under ``auto_mode`` will route
    to ``ask_before_edits`` (because debugging usually involves a
    risky/destructive change worth confirming).

    This test pins both halves of the migration so a future refactor
    cannot accidentally resurrect the silent-skip-LLM behaviour.
    Journaling stays on the ``lyra retro`` CLI subcommand.
    """
    mode_result = session.dispatch("/mode retro")
    assert session.mode == "auto_mode", (
        "legacy 'retro' alias must remap to canonical 'auto_mode'"
    )
    notice = mode_result.output
    # v3.7+: legacy aliases remap silently. The output still surfaces
    # the canonical ID in parens so the user can see exactly which
    # permission posture they landed in.
    assert "auto" in notice and "auto_mode" in notice, (
        "user must see the resolved mode name in the dispatcher output; "
        f"got: {notice!r}"
    )

    fake = FakeLLM(reply="what's the failing test?")
    with patch(
        "lyra_cli.llm_factory.build_llm", return_value=fake
    ) as build_llm_mock:
        # "delete the bad migration" — the auto_mode router classifies
        # this as risky / destructive and dispatches to ask_before_edits.
        result = session.dispatch("delete the bad migration")

    build_llm_mock.assert_called_once_with("deepseek")
    assert fake.calls, "auto_mode must route through the LLM, not skip it"
    assert "what's the failing test?" in result.output
    # The router prepends a one-line notice telling the user which
    # sub-mode it picked.
    assert "[auto_mode → ask_before_edits]" in result.output, (
        "auto_mode router must annotate its sub-mode pick so the user "
        f"can override; got: {result.output!r}"
    )
    sent = fake.calls[0]
    assert "ASK_BEFORE_EDITS" in sent[0].content, (
        "ask_before_edits-mode tail must steer the model toward "
        "confirm-on-write behaviour"
    )


# ---------------------------------------------------------------------------
# Auto-budget — preflight gate refuses turns once cap is exceeded
# ---------------------------------------------------------------------------


def _wire_meter(session: InteractiveSession, cap: float) -> None:
    """Helper: install a real :class:`BudgetMeter` with the given cap."""
    from lyra_cli.interactive.budget import BudgetCap, BudgetMeter

    session.budget_cap_usd = cap
    session.budget_meter = BudgetMeter(cap=BudgetCap(limit_usd=cap))
    session.budget_auto_stop = True


def test_chat_blocks_when_cap_already_exceeded(session: InteractiveSession) -> None:
    """A turn that would push past the cap must be refused before the
    network call. The user gets a clean error pointing at /budget."""
    _wire_meter(session, cap=0.001)
    # Pre-spend so the meter is already over.
    session.budget_meter.record_usage(
        model="deepseek-v4-pro", prompt_tokens=10_000, completion_tokens=5_000
    )
    assert session.budget_meter.current_usd > 0.001

    fake = FakeLLM()
    with patch(
        "lyra_cli.llm_factory.build_llm", return_value=fake
    ) as build_llm_mock:
        result = session.dispatch("hello")

    # ``build_llm`` is called once when caching the provider, but
    # ``generate`` MUST NOT run when the cap is already blown.
    assert fake.calls == [], "LLM.generate must not run once cap is exceeded"
    assert "budget cap reached" in result.output.lower()
    assert "/budget" in result.output
    assert result.renderable is not None
    # Counters must not advance — we charged nothing because nothing
    # ran.
    assert session.tokens_used == 0
    # No cost added by the refused turn.
    pre_refuse = session.budget_meter.current_usd
    assert pre_refuse > 0.001  # left at the over-cap prespend, no further bump


def test_chat_proceeds_under_cap(session: InteractiveSession) -> None:
    """A normal-cost turn under cap should run + bill as usual."""
    _wire_meter(session, cap=10.0)

    fake = FakeLLM(
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    )
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        result = session.dispatch("hello")

    assert fake.calls, "turn under cap must hit the LLM"
    assert "hello back" in result.output.lower()
    assert session.tokens_used == 150


def test_chat_proceeds_when_no_cap_set(session: InteractiveSession) -> None:
    """The default 'no cap' UX must not be regressed by the new gate."""
    assert session.budget_cap_usd is None  # session default
    fake = FakeLLM()
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        result = session.dispatch("hello")

    assert fake.calls, "with no cap the turn must run"
    assert "hello back" in result.output.lower()


def test_auto_stop_off_warns_but_lets_turn_through(
    session: InteractiveSession,
) -> None:
    """When the user opts out of auto-stop the cap is informational
    only — the turn must still run."""
    _wire_meter(session, cap=0.001)
    session.budget_auto_stop = False
    session.budget_meter.record_usage(
        model="deepseek-v4-pro", prompt_tokens=10_000, completion_tokens=5_000
    )

    fake = FakeLLM()
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        result = session.dispatch("hello")

    assert fake.calls, "with auto_stop disabled the turn must run"
    assert "hello back" in result.output.lower()


# ---------------------------------------------------------------------------
# /budget save — persistence slash
# ---------------------------------------------------------------------------


@pytest.fixture
def lyra_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def test_budget_save_persists_cap_to_disk(
    session: InteractiveSession, lyra_home: Path
) -> None:
    session.dispatch("/budget set 7.50")
    result = session.dispatch("/budget save")

    assert "saved" in result.output.lower()
    assert "$7.50" in result.output

    from lyra_core.auth.store import load_budget

    assert load_budget()["cap_usd"] == 7.50


def test_budget_save_with_value_sets_and_persists(
    session: InteractiveSession, lyra_home: Path
) -> None:
    """``/budget save 5`` should both set the live cap AND persist it
    in one keystroke."""
    result = session.dispatch("/budget save 5")

    assert "5.00" in result.output
    assert "persistent" in result.output.lower()
    assert session.budget_cap_usd == 5.0

    from lyra_core.auth.store import load_budget

    assert load_budget()["cap_usd"] == 5.0


def test_budget_save_off_clears_persistent_cap(
    session: InteractiveSession, lyra_home: Path
) -> None:
    from lyra_core.auth.store import load_budget, save_budget

    save_budget(cap_usd=5.0)
    assert load_budget()["cap_usd"] == 5.0

    result = session.dispatch("/budget save off")
    assert "cleared" in result.output.lower()
    assert load_budget()["cap_usd"] is None


def test_budget_save_with_no_cap_set_complains(
    session: InteractiveSession, lyra_home: Path
) -> None:
    """``/budget save`` (bare) when no live cap is set should ask the
    user to specify one."""
    assert session.budget_cap_usd is None
    result = session.dispatch("/budget save")

    assert "no cap to save" in result.output.lower()


def test_budget_suggest_returns_per_model_estimate(
    session: InteractiveSession,
) -> None:
    """``/budget suggest`` should produce a price-aware suggestion."""
    result = session.dispatch("/budget suggest")

    assert "suggested cap" in result.output.lower()
    assert "deepseek" in result.output.lower()
    # The suggestion must be applyable via /budget save.
    assert "/budget save" in result.output


# ---------------------------------------------------------------------------
# Driver auto-apply — boot picks up persisted cap
# ---------------------------------------------------------------------------


def test_apply_budget_settings_seeds_from_disk(
    session: InteractiveSession, lyra_home: Path
) -> None:
    """``_apply_budget_settings`` should pull a persisted default
    onto a fresh session."""
    from lyra_cli.interactive.driver import _apply_budget_settings
    from lyra_core.auth.store import save_budget

    save_budget(cap_usd=3.50, alert_pct=70.0, auto_stop=True)

    fresh = InteractiveSession(repo_root=session.repo_root, model="deepseek")
    assert fresh.budget_cap_usd is None

    _apply_budget_settings(fresh)

    assert fresh.budget_cap_usd == 3.50
    assert fresh.budget_meter is not None
    assert fresh.budget_meter.cap is not None
    assert fresh.budget_meter.cap.limit_usd == 3.50
    assert fresh.budget_meter.cap.alert_pct == 70.0


def test_apply_budget_settings_cli_override_wins_over_disk(
    session: InteractiveSession, lyra_home: Path
) -> None:
    from lyra_cli.interactive.driver import _apply_budget_settings
    from lyra_core.auth.store import save_budget

    save_budget(cap_usd=10.0)

    fresh = InteractiveSession(repo_root=session.repo_root, model="deepseek")
    _apply_budget_settings(fresh, override=2.0)

    assert fresh.budget_cap_usd == 2.0
    assert fresh.budget_meter.cap.limit_usd == 2.0


def test_apply_budget_settings_no_persisted_no_override_means_uncapped(
    session: InteractiveSession, lyra_home: Path
) -> None:
    """Out of the box (no save, no flag) the meter is created but has
    no cap — same as today's behaviour."""
    from lyra_cli.interactive.driver import _apply_budget_settings

    fresh = InteractiveSession(repo_root=session.repo_root, model="deepseek")
    _apply_budget_settings(fresh)

    assert fresh.budget_cap_usd is None
    assert fresh.budget_meter is not None
    assert fresh.budget_meter.cap is None


# ---------------------------------------------------------------------------
# Streaming chat (v2.2.4)
# ---------------------------------------------------------------------------


class StreamingFakeLLM(FakeLLM):
    """FakeLLM extended with a ``stream`` method.

    Yields each delta in :attr:`stream_chunks`, populates
    :attr:`last_usage` on completion (matching the real provider
    contract), and records the messages it was called with on
    :attr:`stream_calls`.
    """

    def __init__(
        self,
        *,
        stream_chunks: list[str] | None = None,
        usage: dict[str, int] | None = None,
        model: str = "deepseek-v4-pro",
    ) -> None:
        super().__init__(reply="".join(stream_chunks or ["fallback"]),
                         usage=usage, model=model)
        self.stream_chunks = list(stream_chunks or ["hello", " ", "world"])
        self.stream_calls: list[list[Message]] = []
        # When a stream is consumed, the usage block lands on
        # ``last_usage`` exactly as the real provider does.
        self._final_usage = (
            dict(usage) if usage is not None else {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        )

    def stream(
        self,
        messages: list[Message],
        max_tokens: int = 2048,
    ):
        self.stream_calls.append(list(messages))
        self.last_usage = {}
        for c in self.stream_chunks:
            yield c
        # Real provider records the final ``usage`` event before the
        # iterator finishes — mirror that here.
        self.last_usage = dict(self._final_usage)


def _enable_streaming(session: InteractiveSession) -> list[str]:
    """Wire a Rich console + a tracker that captures every panel update.

    Returns the buffer where each ``live.update(...)`` call is recorded
    so tests can assert on the on-screen text without simulating an
    actual terminal.
    """
    from rich.console import Console

    seen: list[str] = []
    session._console = Console(record=True, force_terminal=True, file=__import__(
        "io").StringIO())
    session._streaming_enabled = True
    # Phase B (v2.4.0) routes turns through the chat-tool loop by
    # default; streaming and the tool loop are mutually exclusive
    # paths today (the loop runs all LLM hops via non-streaming
    # ``generate`` so tool-call SSE deltas don't fight Rich Live
    # for the panel). Streaming-specific tests opt out of the loop
    # so the streaming branch fires.
    session.chat_tools_enabled = False

    # Snapshot the *displayed text* on each live.update by patching
    # Rich's Live in-place. We don't want to subclass Live — we just
    # want to know what got rendered and in what order.
    import rich.live as _live

    original_update = _live.Live.update

    def update_spy(self, renderable, **kwargs):  # noqa: ANN001
        try:
            from rich.console import Group
            from rich.panel import Panel

            # render_with_header wraps the reply Panel in a Group;
            # unwrap to find the inner Panel so the spy works
            # regardless of whether the progress header is active.
            target = renderable
            if isinstance(target, Group):
                for child in target._renderables:
                    if isinstance(child, Panel):
                        target = child
                        break

            if isinstance(target, Panel):
                plain = ""
                inner = target.renderable
                if hasattr(inner, "plain"):
                    plain = inner.plain  # type: ignore[union-attr]
                elif hasattr(inner, "markup"):
                    # Markdown objects expose the source string via .markup
                    plain = inner.markup  # type: ignore[union-attr]
                seen.append(plain)
        except Exception:
            seen.append(repr(renderable))
        # Rich's update() takes ``refresh`` as a keyword-only arg —
        # forward via **kwargs to avoid a positional-vs-keyword
        # collision when the inner Live machinery calls it.
        return original_update(self, renderable, **kwargs)

    # Reverted automatically by pytest's monkeypatch fixture in callers
    # that need it; tests below set a finalizer so this only lasts the
    # duration of one assertion path.
    _live.Live.update = update_spy
    session._restore_live = lambda: setattr(_live.Live, "update", original_update)
    return seen


def test_streaming_yields_panels_per_delta(
    session: InteractiveSession,
) -> None:
    """Every chunk from the provider drives a panel update so the
    user sees the reply growing token-by-token."""
    seen = _enable_streaming(session)
    fake = StreamingFakeLLM(
        stream_chunks=["hello", " there", "!"],
        usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
    )
    try:
        with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
            result = session.dispatch("hello")
    finally:
        session._restore_live()

    # The provider's stream method was used, not generate.
    assert fake.stream_calls, "stream() must be called when streaming is enabled"
    assert fake.calls == [], "generate() must NOT be called on the streaming path"

    # On-screen panel text grows monotonically.
    assert any("hello" == s for s in seen)
    assert any("hello there" in s for s in seen)
    assert any("hello there!" in s for s in seen)

    # The handler must NOT attach a renderable since the panel was
    # already painted live — otherwise the driver would repaint the
    # final reply right under the streaming panel, doubling it.
    assert result.renderable is None
    assert result.output == ""


def test_streaming_bills_from_final_usage_event(
    session: InteractiveSession,
) -> None:
    """The streaming path reads ``provider.last_usage`` after the
    iterator finishes and updates session.cost_usd / tokens_used.
    """
    session.model = "deepseek-v4-pro"
    _enable_streaming(session)
    fake = StreamingFakeLLM(
        stream_chunks=["a", "b", "c"],
        usage={"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500},
        model="deepseek-v4-pro",
    )
    try:
        with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
            session.dispatch("hi")
    finally:
        session._restore_live()

    expected = (1000 / 1_000_000) * 0.55 + (500 / 1_000_000) * 2.19
    assert session.tokens_used == 1500
    assert session.cost_usd == pytest.approx(expected, rel=1e-9)


def test_streaming_appends_full_text_to_history(
    session: InteractiveSession,
) -> None:
    """The chat history must record the assembled reply, not just
    individual deltas — so follow-up turns see the right context."""
    _enable_streaming(session)
    fake = StreamingFakeLLM(stream_chunks=["one ", "two ", "three"])
    try:
        with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
            session.dispatch("count")
    finally:
        session._restore_live()

    assistant_msgs = [m for m in session._chat_history if m.role == "assistant"]
    assert assistant_msgs, "history must include the assistant reply"
    assert assistant_msgs[-1].content == "one two three"


def test_streaming_falls_back_when_provider_lacks_stream(
    session: InteractiveSession,
) -> None:
    """A provider that only implements ``generate`` (Anthropic, mock,
    Ollama, Gemini) must keep working — the chat handler quietly uses
    the non-streaming path."""
    _enable_streaming(session)
    fake = FakeLLM(reply="non-streamed reply")
    try:
        with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
            result = session.dispatch("hello")
    finally:
        session._restore_live()

    # generate() ran, stream() was never an option.
    assert fake.calls
    # The non-streaming path produces a renderable for the driver to
    # paint — i.e. behaviour identical to the pre-streaming era.
    assert result.renderable is not None
    assert "non-streamed reply" in result.output


def test_streaming_disabled_uses_generate(
    session: InteractiveSession,
) -> None:
    """When ``_streaming_enabled`` is False (default for tests, plain
    mode, /stream off) the streaming branch must be skipped even
    though the provider has ``stream`` available."""
    # _enable_streaming NOT called — streaming stays off.
    assert session._streaming_enabled is False

    fake = StreamingFakeLLM()
    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        result = session.dispatch("hi")

    assert fake.stream_calls == [], "stream() must NOT run with streaming disabled"
    assert fake.calls, "generate() must run on the non-streaming path"
    assert result.renderable is not None


def test_streaming_failure_falls_back_to_generate(
    session: InteractiveSession,
) -> None:
    """If the SSE stream blows up mid-call, the chat handler retries
    via ``generate`` so the user still gets a (non-streamed) answer."""

    class FlakyStreamLLM(StreamingFakeLLM):
        def stream(self, messages, max_tokens=2048):  # noqa: ANN001
            yield "partial..."
            raise ConnectionResetError("upstream hiccup")

    _enable_streaming(session)
    flaky = FlakyStreamLLM(stream_chunks=["partial..."])
    flaky.reply = "non-stream fallback reply"
    try:
        with patch("lyra_cli.llm_factory.build_llm", return_value=flaky):
            result = session.dispatch("hi")
    finally:
        session._restore_live()

    # generate() ran as the fallback after the stream blew up.
    assert flaky.calls, "generate() must be tried after a streaming failure"
    # The user sees the fallback reply via the normal renderable path.
    assert result.renderable is not None
    assert "non-stream fallback reply" in result.output


# ---------------------------------------------------------------------------
# /stream slash
# ---------------------------------------------------------------------------


def test_stream_slash_off_disables_streaming(session: InteractiveSession) -> None:
    """``/stream off`` flips the live state without restarting."""
    _enable_streaming(session)
    try:
        result = session.dispatch("/stream off")
    finally:
        session._restore_live()

    assert "disabled" in result.output.lower()
    assert session._streaming_enabled is False


def test_stream_slash_status_reports_state(session: InteractiveSession) -> None:
    result = session.dispatch("/stream status")
    # No console attached → reports the plain-mode message.
    assert "off" in result.output.lower() or "plain" in result.output.lower()


def test_stream_slash_on_without_console_refuses(
    session: InteractiveSession,
) -> None:
    """Enabling streaming when there's no Rich console attached
    (plain / piped mode) must fail loudly — silently flipping the
    flag would give the user a panel that can never paint."""
    assert session._console is None
    result = session.dispatch("/stream on")
    assert "cannot enable" in result.output.lower()
    assert session._streaming_enabled is False

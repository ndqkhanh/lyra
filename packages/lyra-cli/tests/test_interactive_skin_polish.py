"""Final-wave tests: skin-aware banner, LLM-turn spinner, branded farewells.

Each test class restores the active skin in ``teardown_method`` so we
don't leak state into the rest of the suite. The active skin is a
process-global, so this is the discipline-of-record.

Areas covered (matches the ``ux7..ux9`` todo group):

- :mod:`lyra_cli.interactive.banner` — gradient, wordmark and
  subtitle pull from the active :class:`Skin` (so ``/theme hermes``
  re-skins the next ``/clear`` banner).
- :mod:`lyra_cli.interactive.driver` — ``_run_agent_turn``
  wrapper + ``agent_verb_for_mode`` selector that the prompt_toolkit
  loop invokes for every plain-text turn.
- :mod:`lyra_cli.interactive.output` — ``theme_set_renderable``
  shows a swatch + welcome text, and ``goodbye_renderable`` honours
  the skin's farewell.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from lyra_cli.interactive import banner as _banner
from lyra_cli.interactive import output as _out
from lyra_cli.interactive import session as _session
from lyra_cli.interactive import spinner as _spin
from lyra_cli.interactive import themes as _themes

# ---------------------------------------------------------------------------
# Banner — skin-aware
# ---------------------------------------------------------------------------


class TestBannerSkin:
    def setup_method(self) -> None:
        _themes.set_active_skin("aurora")

    def teardown_method(self) -> None:
        _themes.set_active_skin("aurora")

    def test_plain_default_skin_excludes_skin_tag(self, tmp_path) -> None:
        # Aurora is the default; we explicitly suppress the "skin: ..."
        # subtitle so existing CI smoke tests asserting on the legacy
        # 8-line shape stay green.
        out = _banner.render_banner(
            repo_root=tmp_path,
            model="m",
            mode="plan",
            plain=True,
        )
        assert "skin:" not in out
        assert "Lyra" in out

    def test_plain_non_default_skin_appends_skin_tag(self, tmp_path) -> None:
        _themes.set_active_skin("hermes")
        out = _banner.render_banner(
            repo_root=tmp_path,
            model="m",
            mode="plan",
            plain=True,
        )
        # Tag shows up so users running headless still see which skin
        # is active in their CI logs.
        assert "skin: hermes" in out

    def test_compact_uses_active_skin_wordmark(self, tmp_path) -> None:
        # candy renames the wordmark to "Lyra · candy" via its
        # ``branding.agent_name`` override.
        _themes.set_active_skin("candy")
        out = _banner.render_banner(
            repo_root=tmp_path,
            model="m",
            mode="plan",
            plain=False,
            term_cols=70,  # narrow → compact path
        )
        assert "Lyra" in out

    def test_gradient_stops_follow_active_skin(self) -> None:
        """Switching skins should change the banner's gradient stops.

        We don't snapshot the rendered ANSI (too fragile) — instead we
        check that ``_gradient_stops_from_skin`` returns *different*
        triples for two skins with disjoint accent colours.
        """
        _themes.set_active_skin("aurora")
        aurora_stops = _banner._gradient_stops_from_skin()
        _themes.set_active_skin("candy")
        candy_stops = _banner._gradient_stops_from_skin()
        assert aurora_stops != candy_stops
        # Both triples have three (position, rgb) entries.
        assert len(aurora_stops) == len(candy_stops) == 3

    def test_explicit_banner_gradient_tokens_win(self) -> None:
        """A user skin can declare ``banner_gradient_*`` to override
        the auto-derived ``accent → secondary → danger`` sweep.
        """
        # Build a one-off skin in-memory and register it via the
        # private mapping; this keeps the test self-contained without
        # writing to ~/.lyra/skins.
        custom = _themes.Skin(
            name="rosewater",
            description="test",
            colors={
                "accent": "#FFFFFF",
                "secondary": "#FFFFFF",
                "danger": "#FFFFFF",
                "banner_gradient_start": "#FF0000",
                "banner_gradient_mid": "#00FF00",
                "banner_gradient_end": "#0000FF",
            },
        )
        _themes._BUILT_IN_SKINS["rosewater"] = custom
        try:
            _themes.set_active_skin("rosewater")
            stops = _banner._gradient_stops_from_skin()
            colors = [rgb for _, rgb in stops]
            assert colors == [(0xFF, 0, 0), (0, 0xFF, 0), (0, 0, 0xFF)]
        finally:
            _themes._BUILT_IN_SKINS.pop("rosewater", None)

    def test_hex_to_rgb_round_trip(self) -> None:
        assert _banner._hex_to_rgb("#FF0080") == (0xFF, 0, 0x80)
        assert _banner._hex_to_rgb("00ABCD") == (0x00, 0xAB, 0xCD)
        # Malformed values fall back to aurora cyan instead of crashing.
        assert _banner._hex_to_rgb("nope") == (0x00, 0xE5, 0xFF)
        assert _banner._hex_to_rgb("#XYZXYZ") == (0x00, 0xE5, 0xFF)


# ---------------------------------------------------------------------------
# LLM-turn spinner wrapper
# ---------------------------------------------------------------------------


class TestAgentTurnWrapper:
    def setup_method(self) -> None:
        _themes.set_active_skin("aurora")
        _spin.set_enabled(False)  # don't spawn a thread in tests

    def teardown_method(self) -> None:
        _themes.set_active_skin("aurora")
        _spin.set_enabled(True)

    def test_verb_for_mode_honours_skin_verb_set(self) -> None:
        # candy declares custom verbs (no "planning"), so plan mode
        # should fall back to the first declared verb instead of
        # forcing a non-skinned word into the spinner.
        from lyra_cli.interactive import driver as _driver

        candy = _themes.skin("candy")
        verb = _driver.agent_verb_for_mode("plan", candy)
        assert verb in candy.spinner.get("verbs", [])
        # And the auto-derived "planning" is NOT one of candy's verbs.
        assert "planning" not in candy.spinner.get("verbs", [])

    def test_verb_for_mode_uses_default_when_skin_silent(self) -> None:
        from lyra_cli.interactive import driver as _driver

        # Build a skin that declares no verbs — we should pick the
        # mode-mapped default unchanged.
        bare = _themes.Skin(name="bare", spinner={})
        # v3.2.0 canonical modes:
        assert _driver.agent_verb_for_mode("agent", bare) == "implementing"
        assert _driver.agent_verb_for_mode("debug", bare) == "investigating"
        # Legacy v1.x / v2.x mode names still resolve so saved
        # transcripts and third-party skins don't suddenly fall back
        # to a generic "thinking" verb.
        assert _driver.agent_verb_for_mode("build", bare) == "implementing"
        assert _driver.agent_verb_for_mode("retro", bare) == "reflecting"
        # Unknown mode falls all the way back to "thinking".
        assert _driver.agent_verb_for_mode("zzz", bare) == "thinking"

    def test_run_agent_turn_returns_dispatch_result(self) -> None:
        from rich.console import Console

        from lyra_cli.interactive import driver as _driver

        s = _session.InteractiveSession(repo_root=Path.cwd(), model="m", mode="plan")
        # v3.6.0: legacy ``plan`` remaps to ``plan_mode``.
        console = Console(record=True)
        result = _driver._run_agent_turn(console, s, "ship the thing")
        # v2.2.1: plan_mode handler calls the LLM. With model "m"
        # (unknown) and no env-var configured the call falls back to
        # the friendly error path; output is tagged with the active
        # mode name (``[plan_mode]``) and the task IS still queued
        # for ``/approve``.
        assert "[plan_mode]" in result.output
        assert s.pending_task == "ship the thing"

    def test_run_agent_turn_reraises_on_handler_failure(self) -> None:
        from rich.console import Console

        from lyra_cli.interactive import driver as _driver

        s = _session.InteractiveSession(
            repo_root=Path.cwd(), model="m", mode="agent"
        )
        # v3.6.0: legacy ``agent`` remaps to ``edit_automatically``.
        assert s.mode == "edit_automatically"
        console = Console(record=True)

        def boom(self, line):  # noqa: ARG001 - matches handler signature
            raise RuntimeError("simulated dispatch failure")

        # Patch the active-mode handler so the wrapper hits the error path.
        with patch.dict(
            _session._MODE_HANDLERS, {"edit_automatically": boom}
        ):
            with pytest.raises(RuntimeError):
                _driver._run_agent_turn(console, s, "anything")
        # Wrapper still emits a completion line on the way out — assert
        # the red ✗ + [error] suffix shows up in the captured output.
        rendered = console.export_text()
        assert "✗" in rendered
        assert "[error]" in rendered

    def test_run_agent_turn_skips_completion_line_for_fast_handlers(self) -> None:
        from rich.console import Console

        from lyra_cli.interactive import driver as _driver

        s = _session.InteractiveSession(repo_root=Path.cwd(), model="m", mode="plan")
        console = Console(record=True)
        # Stub handlers return in <1 ms — well under the 0.4 s threshold,
        # so the wrapper should NOT print a "(0.0s)" completion line
        # (would be pure noise on every turn today).
        _driver._run_agent_turn(console, s, "fast turn")
        rendered = console.export_text().strip()
        assert "✓" not in rendered
        assert "agent" not in rendered


# ---------------------------------------------------------------------------
# theme_set_renderable + goodbye_renderable
# ---------------------------------------------------------------------------


class TestSkinAwarePanels:
    def setup_method(self) -> None:
        _themes.set_active_skin("aurora")

    def teardown_method(self) -> None:
        _themes.set_active_skin("aurora")

    def test_theme_set_panel_includes_skin_name_and_welcome(self) -> None:
        panel = _out.theme_set_renderable("hermes")
        from rich.console import Console

        c = Console(record=True, force_terminal=False, width=120)
        c.print(panel)
        rendered = c.export_text()
        # Title shows the skin name
        assert "hermes" in rendered
        # "now wearing" tag is the unambiguous signal we found the new
        # rich panel rather than the legacy single-line fallback.
        assert "now wearing" in rendered
        # Hermes' welcome line shows up as the body footer.
        hermes_welcome = _themes.skin("hermes").brand("welcome")
        assert hermes_welcome in rendered

    def test_theme_set_panel_handles_unknown_skin_gracefully(self) -> None:
        # An unknown name resolves to aurora via skin() — we still get
        # a renderable, never a crash.
        panel = _out.theme_set_renderable("not-a-real-skin")
        from rich.console import Console

        c = Console(record=True, force_terminal=False, width=80)
        c.print(panel)
        rendered = c.export_text()
        assert "not-a-real-skin" in rendered

    def test_goodbye_renderable_uses_active_skin_farewell(self) -> None:
        from rich.console import Console

        _themes.set_active_skin("hermes")
        panel = _out.goodbye_renderable(turns=3, tokens=1234, cost_usd=0.0)
        c = Console(record=True, force_terminal=False, width=80)
        c.print(panel)
        rendered = c.export_text()
        # Hermes' branding.goodbye should be in the panel body.
        hermes_goodbye = _themes.skin("hermes").brand("goodbye")
        assert hermes_goodbye in rendered
        # Stats still render — the new branding doesn't break the table.
        assert "1,234" in rendered
        assert "$0.0000" in rendered

    def test_goodbye_renderable_aurora_keeps_legacy_text(self) -> None:
        # Aurora's goodbye is the legacy "see you next session." line.
        # This guards against accidental copy-edits regressing the
        # default UX.
        from rich.console import Console

        panel = _out.goodbye_renderable(turns=1, tokens=10, cost_usd=0.0)
        c = Console(record=True, force_terminal=False, width=80)
        c.print(panel)
        rendered = c.export_text()
        assert "see you" in rendered.lower()

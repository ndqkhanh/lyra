"""Tests for the hermes-agent / opencode / claw-code inspired UX wave.

Scope (one file per wave, like ``test_interactive_features.py``):

- :mod:`lyra_cli.interactive.session` — ``CommandSpec`` registry
  invariants (every command resolvable, aliases dispatch the same
  handler, subcommands derived from ``args_hint``, /help renders a
  ``Group`` renderable).
- :mod:`lyra_cli.interactive.themes` — full ``Skin`` engine, the
  8 built-ins, ``set_active_skin`` round-trip, and YAML user override
  loading via :func:`install_user_skins` + :func:`load_user_skins`.
- :mod:`lyra_cli.interactive.spinner` — ``set_enabled`` toggle,
  context manager safety, frames-from-skin fallback, no-TTY shape.
- :mod:`lyra_cli.interactive.output` — tool preview / completion
  line shape, ``detect_tool_failure`` heuristic, ``bash_output_renderable``
  with duration + byte counts.
- :mod:`lyra_cli.interactive.completer` — slash palette skips
  alias entries, alias hint shows up in meta, subcommand palette fires
  after the trailing space.

Tests deliberately stay TTY-free: any spinner work uses
``set_enabled(False)`` and any prompt_toolkit code is exercised via
direct ``Document`` construction (no key-loop, no stdin).
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pytest

from lyra_cli.interactive import session as _session
from lyra_cli.interactive import themes as _themes
from lyra_cli.interactive import output as _out
from lyra_cli.interactive import spinner as _spin
from lyra_cli.interactive.session import (
    COMMAND_REGISTRY,
    CommandSpec,
    InteractiveSession,
    SLASH_COMMANDS,
    aliases_for,
    command_spec,
    commands_by_category,
    slash_description,
    subcommands_for,
)


# ---------------------------------------------------------------------------
# CommandSpec registry
# ---------------------------------------------------------------------------


class TestCommandRegistry:
    """The registry is the new single source of truth — verify the contract."""

    def test_every_registry_entry_is_in_slash_commands(self) -> None:
        for spec in COMMAND_REGISTRY:
            assert spec.name in SLASH_COMMANDS
            assert SLASH_COMMANDS[spec.name] is spec.handler

    def test_aliases_dispatch_to_canonical_handler(self) -> None:
        # Pick a spec we know has an alias (``compact`` → ``compress``).
        compact = command_spec("compact")
        compress = command_spec("compress")
        assert compact is not None and compress is not None
        assert compact is compress
        # And the alias has its own ``alias for /...`` doc string.
        assert slash_description("compress") == "alias for /compact"

    def test_aliases_for_returns_other_names_only(self) -> None:
        # ``compress`` is the alias for ``compact`` — querying the
        # canonical name should surface ``compress`` (and exclude itself).
        others = aliases_for("compact")
        assert "compress" in others
        assert "compact" not in others
        # And asking via the alias should surface the canonical.
        others_via_alias = aliases_for("compress")
        assert "compact" in others_via_alias
        assert "compress" not in others_via_alias

    def test_subcommands_extracted_from_args_hint(self) -> None:
        # v3.2.0 collapsed the 5-mode taxonomy onto Claude-Code's four:
        # ``/mode [agent|plan|debug|ask]`` populates subs without us
        # repeating them in the spec. The order MUST match the pipe
        # order in ``args_hint`` so completer dropdowns stay stable
        # across releases — see _PIPE_SUBS_RE in session.py.
        subs = subcommands_for("mode")
        assert subs == ("agent", "plan", "debug", "ask")
        # ``/effort [low|medium|high|ultra]`` ditto.
        assert subcommands_for("effort") == ("low", "medium", "high", "ultra")
        # Commands without an args_hint return empty.
        assert subcommands_for("clear") == ()

    def test_unknown_command_returns_none(self) -> None:
        assert command_spec("definitely-not-a-command") is None
        assert subcommands_for("definitely-not-a-command") == ()
        assert aliases_for("definitely-not-a-command") == ()

    def test_commands_by_category_preserves_registry_order(self) -> None:
        grouped = commands_by_category()
        # Hard-coded category list mirrors the registry header comments.
        assert list(grouped.keys()) == [
            "session",
            "plan-build-run",
            "tools-agents",
            "observability",
            "config-theme",
            "collaboration",
            "meta",
        ]
        # Each group contains at least one CommandSpec.
        for group in grouped.values():
            assert group
            for spec in group:
                assert isinstance(spec, CommandSpec)

    def test_help_renderable_groups_by_category(self) -> None:
        s = InteractiveSession(repo_root=Path.cwd(), model="m", mode="plan")
        # ``dispatch`` is the canonical pure entry point — it's what the
        # driver calls under the hood; tests should never go through stdin.
        result = s.dispatch("/help")
        # Plain text channel keeps the legacy line-per-command shape so
        # existing tests keep working (asserted in test_interactive_session).
        assert "/help" in result.output
        # New: dual-channel renderable is populated for the TTY path.
        assert result.renderable is not None


# ---------------------------------------------------------------------------
# Skin engine
# ---------------------------------------------------------------------------


class TestSkinEngine:
    def setup_method(self) -> None:
        # Restore the default before every test so we don't leak skin state.
        _themes.set_active_skin("aurora")

    def test_eight_builtin_skins_present(self) -> None:
        names = set(_themes.names())
        # Five originals + 3 new (claude/opencode/hermes/sunset) — 8 total.
        for n in (
            "aurora",
            "candy",
            "solar",
            "mono",
            "claude",
            "opencode",
            "hermes",
            "sunset",
        ):
            assert n in names

    def test_legacy_get_returns_seven_token_palette(self) -> None:
        # Back-compat: callers that still use the v1 ``Theme`` TypedDict
        # must keep working — the projection lives on ``Skin``.
        theme = _themes.get("aurora")
        for key in ("accent", "secondary", "danger", "success", "warning", "error", "dim"):
            assert key in theme
            assert theme[key].startswith("#")

    def test_set_active_skin_round_trip(self) -> None:
        _themes.set_active_skin("hermes")
        active = _themes.get_active_skin()
        assert active.name == "hermes"
        # Spinner config is populated on hermes (kawaii faces).
        assert active.spinner.get("faces")

    def test_set_active_skin_unknown_falls_back(self) -> None:
        # Soft-fail-by-design: an unknown name is recorded as the active
        # marker but the resolved skin falls back to aurora so the
        # renderers never crash on a typo. (The same guard makes
        # ``/theme bogus`` a recoverable user error.)
        resolved = _themes.set_active_skin("not-a-skin")
        assert resolved.name == "aurora"
        assert _themes.active_name() == "not-a-skin"

    def test_user_yaml_skin_layers_over_builtin(self, tmp_path) -> None:
        # Skip if PyYAML isn't available — the loader is best-effort.
        yaml = pytest.importorskip("yaml")
        # ``install_user_skins`` walks ``<home>/.lyra/skins/*.yaml``,
        # so we plant the YAML at the matching path.
        skin_dir = tmp_path / ".lyra" / "skins"
        skin_dir.mkdir(parents=True)
        (skin_dir / "myskin.yaml").write_text(
            yaml.dump(
                {
                    "name": "myskin",
                    "parent": "aurora",
                    "description": "user-overridden aurora",
                    "colors": {"accent": "#ABCDEF"},
                    "branding": {"prompt_symbol": "★"},
                }
            )
        )
        _themes.install_user_skins(tmp_path)
        # The new skin shows up in /theme.
        assert "myskin" in _themes.names()
        # And it inherits aurora plus our overrides.
        s = _themes.skin("myskin")
        assert s.color("accent").upper() == "#ABCDEF"
        assert s.brand("prompt_symbol") == "★"
        assert s.description == "user-overridden aurora"


# ---------------------------------------------------------------------------
# Spinner
# ---------------------------------------------------------------------------


class TestSpinner:
    def setup_method(self) -> None:
        # Tests run with the spinner disabled so we never spawn a thread
        # or write \r frames into the captured stdout.
        _spin.set_enabled(False)

    def teardown_method(self) -> None:
        _spin.set_enabled(True)

    def test_disabled_spinner_is_a_noop(self) -> None:
        buf = io.StringIO()
        with _spin.Spinner("doing thing", out=buf):
            pass
        # Disabled mode prints nothing — the callsite owns the chrome.
        assert buf.getvalue() == ""

    def test_context_manager_swallows_exceptions(self) -> None:
        with pytest.raises(RuntimeError):
            with _spin.Spinner("explodes"):
                raise RuntimeError("boom")
        # If the context manager forgot to ``stop`` we'd leak a thread —
        # ``set_enabled(False)`` ensures no thread was started in the
        # first place, but the API contract still has to surface the exc.

    def test_update_text_does_not_crash_when_disabled(self) -> None:
        # update_text mutates an attribute regardless of TTY state; this
        # is the cheap sanity check that the surface is stable.
        sp = _spin.Spinner("a")
        sp.update_text("b")
        assert sp.message == "b"

    def test_frames_default_to_dots_preset(self) -> None:
        sp = _spin.Spinner("x", preset="dots")
        # The frames list comes from the preset dict; verify the contract.
        assert sp.frames == _spin.SPINNER_PRESETS["dots"]

    def test_explicit_frames_win_over_skin(self) -> None:
        # Even if the active skin had faces, explicit frames= takes priority.
        explicit = ["a", "b"]
        sp = _spin.Spinner("x", frames=explicit)
        assert sp.frames == explicit


# ---------------------------------------------------------------------------
# Tool preview / completion / failure detection
# ---------------------------------------------------------------------------


class TestToolUx:
    def test_preview_includes_tool_args(self) -> None:
        line = _out.tool_preview_renderable("bash", "ls -la")
        plain = line.plain
        assert "ls -la" in plain
        # Default emoji for ``bash`` is the lightning bolt.
        assert "⚡" in plain

    def test_completion_includes_duration_and_glyph(self) -> None:
        ok = _out.tool_completion_renderable(
            "bash", "ls", duration_sec=1.4, success=True
        )
        plain_ok = ok.plain
        assert "ls" in plain_ok
        assert "1.4s" in plain_ok
        assert "✓" in plain_ok
        bad = _out.tool_completion_renderable(
            "bash", "ls", duration_sec=0.2, success=False, suffix="[exit 1]"
        )
        plain_bad = bad.plain
        assert "✗" in plain_bad
        assert "[exit 1]" in plain_bad

    def test_detect_tool_failure_exit_code_wins(self) -> None:
        failed, suffix = _out.detect_tool_failure(
            "bash", exit_code=2, output="all good actually"
        )
        assert failed is True
        assert suffix == "[exit 2]"

    def test_detect_tool_failure_keyword_sniff(self) -> None:
        failed, suffix = _out.detect_tool_failure(
            "fetch",
            exit_code=None,
            output="Error: connection refused",
        )
        assert failed is True
        assert suffix == "[error]"

    def test_detect_tool_failure_clean_output_passes(self) -> None:
        failed, suffix = _out.detect_tool_failure(
            "fetch",
            exit_code=0,
            output="ok\n200 bytes received",
        )
        assert failed is False
        assert suffix == ""

    def test_bash_output_renderable_subtitle_has_duration(self) -> None:
        panel = _out.bash_output_renderable(
            command="echo hi",
            exit_code=0,
            stdout="hi\n",
            stderr="",
            duration_sec=0.42,
        )
        # Render via Rich's plain measurement and assert on the subtitle text.
        # The Panel object stores subtitle as a markup string.
        subtitle = panel.subtitle or ""
        assert "0.4s" in subtitle
        assert "exit 0" in subtitle

    def test_bash_output_renderable_byte_counts_when_dual_stream(self) -> None:
        panel = _out.bash_output_renderable(
            command="weird",
            exit_code=1,
            stdout="some output",
            stderr="some error",
            duration_sec=0.1,
        )
        subtitle = panel.subtitle or ""
        assert "out " in subtitle and "err " in subtitle


# ---------------------------------------------------------------------------
# Completer
# ---------------------------------------------------------------------------


class TestCompleter:
    """Two trigger surfaces: slash palette + subcommand palette."""

    def setup_method(self) -> None:
        # Skip the whole class if prompt_toolkit isn't installed (it's an
        # optional dep — non-TTY runs skip the completer entirely).
        pytest.importorskip("prompt_toolkit")

    def _completer(self, repo_root: Path) -> object:
        from lyra_cli.interactive.completer import SlashCompleter

        return SlashCompleter(repo_root=repo_root)

    def test_slash_palette_skips_alias_entries(self, tmp_path) -> None:
        from prompt_toolkit.document import Document

        comp = self._completer(tmp_path)
        completions = list(
            comp.get_completions(Document(text="/c", cursor_position=2), object())
        )
        # We have ``/clear`` and ``/compact`` (and ``/compress`` is the
        # alias for ``/compact``). The alias must NOT appear as its own
        # entry — it'd be redundant with the canonical.
        names = {c.text for c in completions}
        assert "compact" in names
        assert "clear" in names
        assert "compress" not in names

    def test_slash_palette_renders_alias_meta(self, tmp_path) -> None:
        from prompt_toolkit.document import Document

        comp = self._completer(tmp_path)
        completions = list(
            comp.get_completions(Document(text="/co", cursor_position=3), object())
        )
        for c in completions:
            if c.text == "compact":
                # display_meta is FormattedText(list); flatten the strings.
                meta_str = "".join(
                    fragment[1] if isinstance(fragment, tuple) else str(fragment)
                    for fragment in (
                        c.display_meta if isinstance(c.display_meta, list)
                        else [(None, str(c.display_meta))]
                    )
                )
                assert "/compress" in meta_str
                break
        else:
            pytest.fail("expected /compact in completions")

    def test_subcommand_palette_after_trailing_space(self, tmp_path) -> None:
        from prompt_toolkit.document import Document

        comp = self._completer(tmp_path)
        # v3.2.0: ``/mode `` (trailing space) → palette over the 4-mode
        # Claude-Code taxonomy. We assert *exact equality* so a future
        # accidental re-introduction of a legacy alias into args_hint
        # (which would leak ``build`` / ``run`` / ``retro`` into the
        # dropdown again) fails this test loudly. Aliases are still
        # accepted by the dispatcher — see the ``/mode build`` remap
        # tests in test_slash_mode_full.py — they're just not part of
        # the discoverable surface.
        completions = list(
            comp.get_completions(
                Document(text="/mode ", cursor_position=6), object()
            )
        )
        names = {c.text for c in completions}
        assert names == {"agent", "plan", "debug", "ask"}

    def test_subcommand_palette_filters_by_stem(self, tmp_path) -> None:
        from prompt_toolkit.document import Document

        comp = self._completer(tmp_path)
        # v3.2.0: ``de`` is uniquely-prefix to ``debug`` in the new
        # taxonomy. The previous version of this test used ``ex`` →
        # ``explore``; that mode no longer exists at the surface level
        # (it was absorbed into ``ask``).
        completions = list(
            comp.get_completions(
                Document(text="/mode de", cursor_position=8), object()
            )
        )
        names = {c.text for c in completions}
        assert names == {"debug"}

    def test_subcommand_palette_empty_for_argless_commands(self, tmp_path) -> None:
        from prompt_toolkit.document import Document

        comp = self._completer(tmp_path)
        completions = list(
            comp.get_completions(
                Document(text="/clear ", cursor_position=7), object()
            )
        )
        # /clear has no subcommands so the palette returns nothing.
        assert list(completions) == []

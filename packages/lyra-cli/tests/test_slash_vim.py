"""Tests for ``/vim`` real toggle (Wave-C Task 12).

Contract:

1. ``/vim`` (no args) toggles the live ``session.vim_mode`` flag.
2. ``/vim on`` / ``/vim off`` set it explicitly.
3. ``/vim status`` reports state without mutating it.
4. When ``session.config_path`` is set, every successful toggle persists
   ``vim=<state>`` to the on-disk config so the preference survives a
   REPL restart (depends on Task 11).
5. The pure ``vi_bindings()`` factory in ``lyra_cli.interactive.keybinds``
   returns a non-empty key-binding map suitable for prompt_toolkit.
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.config_store import Config
from lyra_cli.interactive.session import InteractiveSession


def _persistent_session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession.from_config(
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )


def test_vim_toggle_flips_state(tmp_path: Path) -> None:
    session = _persistent_session(tmp_path)
    assert session.vim_mode is False
    session.dispatch("/vim")
    assert session.vim_mode is True
    session.dispatch("/vim")
    assert session.vim_mode is False


def test_vim_on_off_explicit(tmp_path: Path) -> None:
    session = _persistent_session(tmp_path)
    session.dispatch("/vim on")
    assert session.vim_mode is True
    session.dispatch("/vim off")
    assert session.vim_mode is False


def test_vim_status_reports_without_mutation(tmp_path: Path) -> None:
    session = _persistent_session(tmp_path)
    session.dispatch("/vim on")
    out = session.dispatch("/vim status").output or ""
    assert "on" in out.lower()
    assert session.vim_mode is True  # status is read-only


def test_vim_persists_to_config(tmp_path: Path) -> None:
    session = _persistent_session(tmp_path)
    session.dispatch("/vim on")
    cfg = Config.load(tmp_path / "config.yaml")
    assert cfg.get("vim") in {"on", "True", "true"}

    session.dispatch("/vim off")
    cfg2 = Config.load(tmp_path / "config.yaml")
    assert cfg2.get("vim") in {"off", "False", "false"}


def test_vim_state_survives_restart(tmp_path: Path) -> None:
    s1 = _persistent_session(tmp_path)
    s1.dispatch("/vim on")

    s2 = InteractiveSession.from_config(
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )
    assert s2.vim_mode is True


def test_vi_bindings_factory_returns_keymap() -> None:
    """The factory should expose a usable keymap regardless of whether
    prompt_toolkit is installed.

    Real ``KeyBindings`` exposes ``.bindings`` (a list); the headless
    stub exposes the same attribute plus ``__iter__``. The contract
    is "non-None and reports at least one declared binding".
    """
    from lyra_cli.interactive.keybinds import vi_bindings

    bindings = vi_bindings()
    assert bindings is not None
    # Prefer ``.bindings`` (works for both prompt_toolkit's KeyBindings
    # and our headless stub). Fall back to iteration for forward-compat
    # with future prompt_toolkit releases.
    declared = list(getattr(bindings, "bindings", None) or list(bindings))
    assert declared, "vi_bindings() must register at least one keybind"

"""Tests for ``Config`` store + ``/config`` slash + ``/skin`` alias.

Wave-C Task 11 contract:

1. ``Config.load(path)`` from a missing file returns an empty,
   well-typed object that still supports ``.get``/``.set``.
2. ``Config.set("theme", "aurora")`` followed by ``.save()`` writes a
   file that ``Config.load()`` round-trips back to the same value.
3. ``/config list`` enumerates current key=value pairs.
4. ``/config get <key>`` echoes the current value (or a friendly
   "<unset>" marker when the key is missing).
5. ``/config set <key>=<value>`` mutates the in-memory Config and, when
   ``InteractiveSession`` exposes a `config_path`, persists to disk.
6. The well-known keys ``theme`` / ``vim`` / ``permission_mode`` /
   ``tdd_gate`` / ``effort`` propagate to the live session, so the
   user sees the slash take effect immediately.
7. ``/skin`` continues to alias ``/theme`` (no regression from the
   pre-Wave-C behaviour).
8. ``InteractiveSession.from_config(repo_root, config_path=...)``
   reads the config at boot and applies the known keys, so a user's
   persisted ``theme=midnight`` survives a restart.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.config_store import Config
from lyra_cli.interactive.session import InteractiveSession


# ---------------------------------------------------------------------------
# Config: pure store — no slash / no session
# ---------------------------------------------------------------------------


def test_config_load_missing_returns_empty(tmp_path: Path) -> None:
    cfg = Config.load(tmp_path / "nope.yaml")
    assert cfg.as_dict() == {}
    assert cfg.get("theme", default="aurora") == "aurora"


def test_config_set_save_roundtrips(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    cfg = Config.load(path)
    cfg.set("theme", "midnight")
    cfg.set("vim", "on")
    cfg.set("effort", "high")
    cfg.save()

    again = Config.load(path)
    assert again.get("theme") == "midnight"
    assert again.get("vim") == "on"
    assert again.get("effort") == "high"


def test_config_set_coerces_to_string(tmp_path: Path) -> None:
    """The on-disk format only stores strings; ``set`` must coerce.

    This keeps the YAML/JSON files simple to hand-edit and prevents
    surprise type drift when a value is round-tripped through disk.
    """
    cfg = Config.load(tmp_path / "config.yaml")
    cfg.set("budget_cap_usd", 12.5)
    cfg.set("tdd_gate", True)
    assert cfg.get("budget_cap_usd") == "12.5"
    assert cfg.get("tdd_gate") == "True"


# ---------------------------------------------------------------------------
# /config slash
# ---------------------------------------------------------------------------


def _session(tmp_path: Path) -> InteractiveSession:
    """Helper: a session whose config persists into ``tmp_path``."""
    return InteractiveSession.from_config(
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )


def test_slash_config_list_starts_empty_after_boot(tmp_path: Path) -> None:
    session = _session(tmp_path)
    out = session.dispatch("/config list").output or ""
    # The list view must mention the well-known keys (even if unset)
    # so users discover what they can configure without reading docs.
    for key in ("theme", "vim", "permission_mode", "tdd_gate", "effort"):
        assert key in out, f"/config list should advertise {key!r}; got:\n{out}"


def test_slash_config_set_then_get(tmp_path: Path) -> None:
    session = _session(tmp_path)
    set_out = session.dispatch("/config set theme=midnight").output or ""
    assert "midnight" in set_out
    get_out = session.dispatch("/config get theme").output or ""
    assert "midnight" in get_out


def test_slash_config_set_propagates_to_live_session(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.dispatch("/config set vim=on")
    assert session.vim_mode is True

    session.dispatch("/config set permission_mode=yolo")
    assert session.permission_mode == "yolo"

    session.dispatch("/config set tdd_gate=off")
    assert session.tdd_gate_enabled is False


def test_slash_config_set_persists_to_disk(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.dispatch("/config set theme=midnight")
    assert (tmp_path / "config.yaml").exists()

    cfg = Config.load(tmp_path / "config.yaml")
    assert cfg.get("theme") == "midnight"


def test_slash_config_set_rejects_unknown_key(tmp_path: Path) -> None:
    session = _session(tmp_path)
    out = session.dispatch("/config set chaotic=evil").output or ""
    assert "unknown" in out.lower()


def test_slash_config_set_requires_key_equals_value(tmp_path: Path) -> None:
    session = _session(tmp_path)
    out = session.dispatch("/config set theme midnight").output or ""
    # Without ``=``, the dispatcher must complain rather than silently
    # treating the rest of the line as the key.
    assert "key=value" in out.lower() or "usage" in out.lower()


def test_slash_config_get_unknown_key_returns_unset(tmp_path: Path) -> None:
    session = _session(tmp_path)
    out = session.dispatch("/config get theme").output or ""
    # Fresh boot → no theme set → friendly "<unset>" marker, not a crash.
    assert "unset" in out.lower() or "aurora" in out.lower()


# ---------------------------------------------------------------------------
# /skin alias preservation (no regression)
# ---------------------------------------------------------------------------


def test_slash_skin_still_aliases_theme(tmp_path: Path) -> None:
    session = _session(tmp_path)
    out = session.dispatch("/skin midnight").output or ""
    assert "midnight" in out
    assert session.theme == "midnight"


# ---------------------------------------------------------------------------
# Persistence at boot — restart survives saved config
# ---------------------------------------------------------------------------


def test_from_config_applies_persisted_keys(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    seed = Config.load(path)
    seed.set("theme", "midnight")
    seed.set("vim", "on")
    seed.set("permission_mode", "strict")
    seed.set("tdd_gate", "off")
    seed.save()

    fresh = InteractiveSession.from_config(
        repo_root=tmp_path,
        config_path=path,
    )
    assert fresh.theme == "midnight"
    assert fresh.vim_mode is True
    assert fresh.permission_mode == "strict"
    assert fresh.tdd_gate_enabled is False


def test_from_config_falls_back_when_missing(tmp_path: Path) -> None:
    """A nonexistent config file must not raise — user just hasn't run /config yet."""
    fresh = InteractiveSession.from_config(
        repo_root=tmp_path,
        config_path=tmp_path / "absent.yaml",
    )
    assert fresh.theme == "aurora"  # default holds


# ---------------------------------------------------------------------------
# Defensive: malformed file should not crash the REPL boot
# ---------------------------------------------------------------------------


def test_from_config_tolerates_malformed_file(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("not: [valid: yaml: at: all", encoding="utf-8")
    fresh = InteractiveSession.from_config(repo_root=tmp_path, config_path=path)
    # Defaults restored; boot must succeed even with a broken file so users
    # can recover by overwriting via ``/config set``.
    assert fresh.theme == "aurora"


@pytest.mark.parametrize("value, expected", [("on", True), ("true", True), ("1", True), ("off", False), ("false", False), ("0", False)])
def test_config_bool_keys_accept_aliases(tmp_path: Path, value: str, expected: bool) -> None:
    session = _session(tmp_path)
    session.dispatch(f"/config set vim={value}")
    assert session.vim_mode is expected

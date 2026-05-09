"""Tests for :mod:`lyra_cli.config_io`."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from lyra_cli.config_io import (
    LYRA_CONFIG_VERSION,
    load_settings,
    save_settings,
    write_env_file,
)


# ---------------------------------------------------------------------------
# load_settings
# ---------------------------------------------------------------------------


def test_load_settings_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert load_settings(tmp_path / "nope.json") == {}


def test_load_settings_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"default_provider": "deepseek"}))
    got = load_settings(p)
    assert got["default_provider"] == "deepseek"
    # Migration stamps a config_version even on legacy files.
    assert got["config_version"] == LYRA_CONFIG_VERSION


def test_load_settings_recovers_from_corrupt_file(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    p.write_text("{not json")
    assert load_settings(p) == {}
    # The corrupt file must be preserved (renamed) for postmortem.
    assert (tmp_path / "settings.json.corrupt").is_file()


def test_load_settings_ignores_non_dict_payload(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    p.write_text("[1, 2, 3]")
    assert load_settings(p) == {}


# ---------------------------------------------------------------------------
# save_settings
# ---------------------------------------------------------------------------


def test_save_settings_writes_atomically(tmp_path: Path) -> None:
    p = tmp_path / "nested" / "settings.json"
    save_settings(p, {"default_model": "deepseek-flash"})
    assert p.is_file()
    data = json.loads(p.read_text())
    assert data["default_model"] == "deepseek-flash"
    assert data["config_version"] == LYRA_CONFIG_VERSION


def test_save_settings_chmod_600(tmp_path: Path) -> None:
    """Permission bits must restrict access to the owner."""
    p = tmp_path / "settings.json"
    save_settings(p, {"x": 1})
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode == 0o600


def test_save_settings_preserves_existing_keys(tmp_path: Path) -> None:
    p = tmp_path / "settings.json"
    save_settings(p, {"a": 1, "b": 2})
    save_settings(p, {"a": 1, "b": 2, "c": 3})  # caller already merged
    data = json.loads(p.read_text())
    assert data["c"] == 3


# ---------------------------------------------------------------------------
# write_env_file
# ---------------------------------------------------------------------------


def test_write_env_creates_file(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    write_env_file(p, {"DEEPSEEK_API_KEY": "ds-test"})
    body = p.read_text()
    assert "DEEPSEEK_API_KEY=ds-test\n" in body


def test_write_env_merges_with_existing(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("DATABASE_URL=postgres://x\n# comment\n")
    write_env_file(p, {"DEEPSEEK_API_KEY": "ds-test"})
    body = p.read_text()
    # Existing variable preserved.
    assert "DATABASE_URL=postgres://x" in body
    assert "DEEPSEEK_API_KEY=ds-test" in body


def test_write_env_overwrites_same_key(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("DEEPSEEK_API_KEY=old\n")
    write_env_file(p, {"DEEPSEEK_API_KEY": "new"})
    body = p.read_text()
    assert "DEEPSEEK_API_KEY=new" in body
    assert "old" not in body


def test_write_env_chmod_600(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    write_env_file(p, {"X": "1"})
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode == 0o600

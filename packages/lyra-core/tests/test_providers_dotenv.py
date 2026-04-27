"""Contract tests for the stdlib-only .env parser.

Mirrors claw-code's parse_dotenv semantics so users who switch from
claw-code to Lyra get identical resolution behaviour for their
existing .env files.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.providers import dotenv as dot


def test_parse_extracts_plain_key_value_pairs() -> None:
    body = "FOO=bar\nBAZ=qux\n"
    assert dot.parse_dotenv(body) == {"FOO": "bar", "BAZ": "qux"}


def test_parse_handles_double_quoted_values() -> None:
    assert dot.parse_dotenv('FOO="bar"\n')["FOO"] == "bar"


def test_parse_handles_single_quoted_values() -> None:
    assert dot.parse_dotenv("FOO='bar'\n")["FOO"] == "bar"


def test_parse_handles_export_prefix() -> None:
    assert dot.parse_dotenv("export FOO=bar\n")["FOO"] == "bar"


def test_parse_ignores_comments() -> None:
    assert dot.parse_dotenv("# a comment\nFOO=bar\n") == {"FOO": "bar"}


def test_parse_ignores_blank_lines() -> None:
    assert dot.parse_dotenv("\n\nFOO=bar\n\n") == {"FOO": "bar"}


def test_parse_trims_whitespace_in_key_and_value() -> None:
    assert dot.parse_dotenv("  FOO  =  bar  \n")["FOO"] == "bar"


def test_parse_accepts_empty_value() -> None:
    assert dot.parse_dotenv("FOO=\n") == {"FOO": ""}


def test_parse_drops_lines_without_equals() -> None:
    assert dot.parse_dotenv("JUST_A_WORD\nFOO=bar\n") == {"FOO": "bar"}


def test_load_dotenv_file_returns_none_for_missing_path(tmp_path: Path) -> None:
    assert dot.load_dotenv_file(tmp_path / "nope.env") is None


def test_load_dotenv_file_reads_keys_from_disk(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text('ANTHROPIC_API_KEY="sk-test-1"\nOPENAI_API_KEY=sk-test-2\n')
    got = dot.load_dotenv_file(p)
    assert got == {"ANTHROPIC_API_KEY": "sk-test-1", "OPENAI_API_KEY": "sk-test-2"}


def test_dotenv_value_for_cwd_finds_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("FOO=cwd-bar\n")
    monkeypatch.chdir(tmp_path)
    assert dot.dotenv_value("FOO") == "cwd-bar"
    assert dot.dotenv_value("MISSING") is None


def test_dotenv_value_returns_none_when_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("FOO=\n")
    monkeypatch.chdir(tmp_path)
    assert dot.dotenv_value("FOO") is None, "empty value is semantically equivalent to unset"


def test_find_dotenv_path_walks_to_parent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Running ``lyra`` from a sub-dir still resolves the project's `.env`.

    Mirrors claw-code's nearest-ancestor lookup: write the `.env` at
    the repo root, ``cd`` to a nested sub-directory, and assert
    discovery still works. This is what makes `OPENAI_API_KEY` "just
    work" when a developer runs `cd packages/foo && lyra run ...`.
    """
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-from-root\n")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    found = dot.find_dotenv_path()
    assert found is not None
    assert found.resolve() == (tmp_path / ".env").resolve()
    assert dot.dotenv_value("OPENAI_API_KEY") == "sk-from-root"


def test_find_dotenv_path_prefers_nearer_ancestor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A nearer `.env` shadows the one further up the tree."""
    (tmp_path / ".env").write_text("FOO=root\n")
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / ".env").write_text("FOO=inner\n")
    monkeypatch.chdir(inner)

    assert dot.dotenv_value("FOO") == "inner"


def test_find_dotenv_path_returns_none_when_no_env_anywhere(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No `.env` on the path -> ``None`` (not a raise)."""
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    # ``tmp_path`` lives under the system tmp tree; its real parents
    # may not contain a .env, so we only assert the helper returns
    # ``None`` *or* points at something outside ``tmp_path``.
    found = dot.find_dotenv_path()
    if found is not None:
        assert tmp_path not in found.parents and found.parent != tmp_path

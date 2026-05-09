"""Tests for the memory write-path redactor + MemoryToolset.remember plumbing."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.memory.auto_memory import AutoMemory, MemoryKind
from lyra_core.memory.memory_tools import MemoryToolset
from lyra_core.memory.redactor import RedactionResult, redact, redact_pair


# --- redact() ---------------------------------------------------------


def test_redact_clean_text_unchanged() -> None:
    r = redact("Run the build and capture the output to a file.")
    assert r.text == "Run the build and capture the output to a file."
    assert r.hits == ()
    assert r.changed is False


def test_redact_aws_access_key() -> None:
    r = redact("creds: AKIAIOSFODNN7EXAMPLE saved")
    assert "AKIAIOSFODNN7EXAMPLE" not in r.text
    assert "[REDACTED:aws_access_key]" in r.text
    assert "aws_access_key" in r.hits


def test_redact_github_token() -> None:
    r = redact("export GH_TOKEN=ghp_aBcDeF0123456789aBcDeF0123456789aBcD")
    assert "ghp_" not in r.text
    assert "[REDACTED:github_token]" in r.text


def test_redact_openai_secret() -> None:
    r = redact("OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuv")
    assert "sk-1234567890abcdefghijklmnopqrstuv" not in r.text
    assert "openai_secret" in r.hits


def test_redact_rsa_private_key() -> None:
    r = redact("-----BEGIN RSA PRIVATE KEY-----\nstuff\n-----END---")
    assert "BEGIN RSA PRIVATE KEY" not in r.text
    assert "rsa_private_key" in r.hits


def test_redact_bearer_token() -> None:
    r = redact("authorization: Bearer abc123def456ghi789jkl012mno345pq")
    assert "abc123def456ghi789jkl012mno345pq" not in r.text


def test_redact_multiple_distinct_secrets() -> None:
    r = redact(
        "AKIAIOSFODNN7EXAMPLE and ghp_aBcDeF0123456789aBcDeF0123456789aBcD"
    )
    assert "aws_access_key" in r.hits
    assert "github_token" in r.hits
    assert "AKIA" not in r.text
    assert "ghp_" not in r.text


def test_redact_pair_unions_hits() -> None:
    (t1, t2), hits = redact_pair(
        "title with AKIAIOSFODNN7EXAMPLE",
        "body with ghp_aBcDeF0123456789aBcDeF0123456789aBcD",
    )
    assert "AKIA" not in t1
    assert "ghp_" not in t2
    assert set(hits) >= {"aws_access_key", "github_token"}
    # No duplicates in hits.
    assert len(hits) == len(set(hits))


def test_redact_empty_string_returns_empty() -> None:
    r = redact("")
    assert r.text == ""
    assert r.hits == ()


# --- MemoryToolset.remember plumbing ---------------------------------


def _toolset(tmp_path: Path) -> MemoryToolset:
    return MemoryToolset(
        auto_memory=AutoMemory(root=tmp_path / "mem", project="demo"),
    )


def test_remember_strips_secret_before_persist(tmp_path: Path) -> None:
    ts = _toolset(tmp_path)
    result = ts.remember(
        "deploy hint: export GH_TOKEN=ghp_aBcDeF0123456789aBcDeF0123456789aBcD",
        scope="auto",
        kind=MemoryKind.PROJECT,
        title="ci secret leaked",
    )
    # Returned record should be redacted.
    assert "ghp_" not in result.body
    assert "[REDACTED:github_token]" in result.body
    # On-disk JSONL must be redacted too.
    raw = ts.auto_memory.jsonl_path.read_text()
    assert "ghp_aBcDeF" not in raw
    assert "[REDACTED:github_token]" in raw


def test_remember_strips_secret_in_title(tmp_path: Path) -> None:
    ts = _toolset(tmp_path)
    result = ts.remember(
        "build worked",
        scope="auto",
        kind=MemoryKind.PROJECT,
        title="leaked AKIAIOSFODNN7EXAMPLE in CI logs",
    )
    assert "AKIA" not in result.title
    assert "[REDACTED:aws_access_key]" in result.title


def test_remember_clean_text_unchanged(tmp_path: Path) -> None:
    ts = _toolset(tmp_path)
    result = ts.remember(
        "Use pytest -q to run the suite",
        scope="auto",
        kind=MemoryKind.PROJECT,
        title="how to run tests",
    )
    assert result.body == "Use pytest -q to run the suite"
    assert result.title == "how to run tests"

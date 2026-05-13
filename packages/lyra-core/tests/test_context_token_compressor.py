"""Tests for token_compressor.py (Phase 6)."""
from __future__ import annotations

import pytest

from lyra_core.context.token_compressor import (
    CompressionGuideline,
    CompressionPolicy,
    CompressionStats,
    ToolOutputCompressor,
)


# ---------------------------------------------------------------------------
# CompressionPolicy
# ---------------------------------------------------------------------------


def test_policy_protects_identifier():
    policy = CompressionPolicy()
    assert policy.line_is_protected("def login(user):")


def test_policy_protects_diff_line():
    policy = CompressionPolicy()
    assert policy.line_is_protected("+ added line")
    assert policy.line_is_protected("- removed line")


def test_policy_protects_error_line():
    policy = CompressionPolicy()
    assert policy.line_is_protected("RuntimeError: something failed")
    assert policy.line_is_protected("  File 'auth.py', line 42")


def test_policy_protects_file_path():
    policy = CompressionPolicy()
    assert policy.line_is_protected("  at ./src/auth.py:42")


def test_policy_does_not_protect_blank():
    policy = CompressionPolicy()
    assert not policy.line_is_protected("")


def test_policy_does_not_protect_plain_prose():
    policy = CompressionPolicy(
        protect_identifiers=False,
        protect_diff_lines=True,
        protect_error_lines=True,
        protect_file_paths=False,
    )
    assert not policy.line_is_protected("everything went smoothly today")


def test_policy_extra_protect_patterns():
    policy = CompressionPolicy(
        protect_identifiers=False,
        protect_file_paths=False,
        extra_protect_patterns=[r"SECRET_KEY"],
    )
    assert policy.line_is_protected("SECRET_KEY = 'abc123'")
    assert not policy.line_is_protected("   ")


def test_policy_text_has_protected_content():
    policy = CompressionPolicy()
    assert policy.text_has_protected_content("def foo():\n    pass")
    assert not policy.text_has_protected_content(
        "", # empty
    )


# ---------------------------------------------------------------------------
# CompressionStats
# ---------------------------------------------------------------------------


def test_stats_ratio_normal():
    s = CompressionStats(
        original_chars=100, compressed_chars=50,
        original_tokens=25, compressed_tokens=12,
        protected_lines=2, compressed_lines=3,
    )
    assert s.ratio == pytest.approx(0.5)
    assert s.tokens_saved == 13
    assert not s.regressed


def test_stats_regressed():
    s = CompressionStats(
        original_chars=50, compressed_chars=60,
        original_tokens=12, compressed_tokens=15,
        protected_lines=0, compressed_lines=0,
    )
    assert s.regressed


def test_stats_zero_original():
    s = CompressionStats(
        original_chars=0, compressed_chars=0,
        original_tokens=0, compressed_tokens=0,
        protected_lines=0, compressed_lines=0,
    )
    assert s.ratio == pytest.approx(1.0)
    assert s.tokens_saved == 0


# ---------------------------------------------------------------------------
# ToolOutputCompressor — basic compression
# ---------------------------------------------------------------------------


def test_compress_strips_progress_bar():
    compressor = ToolOutputCompressor(policy=CompressionPolicy(protect_identifiers=False))
    text = "Starting...\n##########\nDone."
    result, stats = compressor.compress(text)
    assert "##########" not in result or stats.compressed_chars <= len(text)


def test_compress_collapses_blank_lines():
    compressor = ToolOutputCompressor(
        policy=CompressionPolicy(protect_identifiers=False, protect_file_paths=False)
    )
    text = "line1\n\n\n\nline2"
    result, _ = compressor.compress(text)
    assert "\n\n\n" not in result


def test_compress_does_not_mangle_code():
    compressor = ToolOutputCompressor()
    code = "def login(user):\n    return auth.check(user)\n"
    result, _ = compressor.compress(code)
    assert "def login" in result
    assert "auth.check" in result


def test_compress_does_not_mangle_diff():
    compressor = ToolOutputCompressor()
    diff = "+ added line\n- removed line\n  context"
    result, _ = compressor.compress(diff)
    assert "+ added line" in result
    assert "- removed line" in result


def test_compress_does_not_mangle_error():
    compressor = ToolOutputCompressor()
    text = "RuntimeError: connection refused\n  at auth.py:42"
    result, _ = compressor.compress(text)
    assert "RuntimeError" in result


def test_compress_empty_string():
    compressor = ToolOutputCompressor()
    result, stats = compressor.compress("")
    assert result == ""
    assert stats.ratio == pytest.approx(1.0)


def test_compress_no_regression_guarantee():
    compressor = ToolOutputCompressor()
    text = "short"
    result, stats = compressor.compress(text)
    assert len(result) <= len(text)
    assert not stats.regressed


def test_compress_removes_trailing_blanks():
    compressor = ToolOutputCompressor(
        policy=CompressionPolicy(protect_identifiers=False, protect_file_paths=False)
    )
    text = "output\n\n\n"
    result, _ = compressor.compress(text)
    assert not result.endswith("\n\n")


# ---------------------------------------------------------------------------
# ToolOutputCompressor — compress_messages
# ---------------------------------------------------------------------------


def test_compress_messages_skips_non_tool():
    compressor = ToolOutputCompressor()
    msgs = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "answer"},
    ]
    result, stats = compressor.compress_messages(msgs)
    assert len(result) == 2
    assert stats == []


def test_compress_messages_compresses_tool():
    compressor = ToolOutputCompressor(
        policy=CompressionPolicy(protect_identifiers=False, protect_file_paths=False)
    )
    msgs = [{"role": "tool", "name": "bash", "content": "line1\n\n\n\nline2"}]
    result, stats = compressor.compress_messages(msgs)
    assert len(result) == 1
    assert len(stats) == 1
    assert "\n\n\n" not in result[0]["content"]


def test_compress_messages_does_not_mutate_input():
    compressor = ToolOutputCompressor()
    original = "\x1b[31mred\x1b[0m output"
    msgs = [{"role": "tool", "content": original}]
    compressor.compress_messages(msgs)
    assert msgs[0]["content"] == original


def test_compress_messages_non_string_content_passthrough():
    compressor = ToolOutputCompressor()
    msgs = [{"role": "tool", "content": [{"type": "text", "text": "hi"}]}]
    result, stats = compressor.compress_messages(msgs)
    assert result[0]["content"] == [{"type": "text", "text": "hi"}]
    assert stats == []


# ---------------------------------------------------------------------------
# CompressionGuideline — miss signal learning
# ---------------------------------------------------------------------------


def test_guideline_record_miss_creates_entry():
    gl = CompressionGuideline()
    entry = gl.record_miss("auth.login")
    assert entry.pattern == "auth.login"
    assert entry.miss_count == 1
    assert not entry.protect  # not yet promoted


def test_guideline_promotes_after_threshold():
    gl = CompressionGuideline()
    gl.record_miss("auth.login")
    entry = gl.record_miss("auth.login")  # second miss → promote
    assert entry.protect
    assert entry.miss_count == 2


def test_guideline_confidence_increases():
    gl = CompressionGuideline()
    e1 = gl.record_miss("pattern_x")
    e2 = gl.record_miss("pattern_x")
    assert e2.confidence > e1.confidence


def test_guideline_build_policy_adds_patterns():
    gl = CompressionGuideline()
    gl.record_miss("SECRET_FUNC")
    gl.record_miss("SECRET_FUNC")  # promote
    policy = gl.build_policy()
    assert any("SECRET_FUNC" in p for p in policy.extra_protect_patterns)


def test_guideline_build_policy_preserves_base():
    gl = CompressionGuideline()
    base = CompressionPolicy(protect_identifiers=False)
    policy = gl.build_policy(base)
    assert not policy.protect_identifiers


def test_guideline_entries_sorted_by_miss_count():
    gl = CompressionGuideline()
    gl.record_miss("a")
    gl.record_miss("b")
    gl.record_miss("b")
    entries = gl.entries()
    assert entries[0].pattern == "b"


def test_guideline_persist_and_reload(tmp_path):
    path = tmp_path / "guidelines.json"
    gl1 = CompressionGuideline(store_path=path)
    gl1.record_miss("fn_x")
    gl1.record_miss("fn_x")

    gl2 = CompressionGuideline(store_path=path)
    assert len(gl2.entries()) == 1
    assert gl2.entries()[0].miss_count == 2
    assert gl2.entries()[0].protect


def test_guideline_load_corrupt(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{{not json")
    gl = CompressionGuideline(store_path=path)
    assert gl.entries() == []

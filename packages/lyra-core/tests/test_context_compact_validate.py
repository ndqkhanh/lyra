"""Tests for validated compaction (Phase CE.1, P0-4)."""
from __future__ import annotations

import pytest

from lyra_core.context.compact_validate import (
    Invariant,
    ValidationReport,
    compact_messages_validated,
    extract_default_invariants,
    validate_compaction,
)
from lyra_core.context.compactor import CompactResult


# ────────────────────────────────────────────────────────────────
# Default invariant extraction
# ────────────────────────────────────────────────────────────────


def test_extract_finds_python_file_anchor():
    msgs = [{"role": "user", "content": "see src/lyra_core/agent.py:42"}]
    invs = extract_default_invariants(msgs)
    assert Invariant("file_anchor", "src/lyra_core/agent.py:42") in invs


def test_extract_handles_file_anchor_with_column():
    msgs = [{"role": "assistant", "content": "tool returned src/foo.py:10:3"}]
    invs = extract_default_invariants(msgs)
    assert Invariant("file_anchor", "src/foo.py:10") in invs


def test_extract_finds_test_names():
    msgs = [
        {"role": "tool", "content": "FAILED tests/test_x.py::test_login_rejects_empty"}
    ]
    invs = extract_default_invariants(msgs)
    assert Invariant("test_name", "test_login_rejects_empty") in invs


def test_extract_finds_deny_reasons():
    msgs = [
        {"role": "system", "content": "deny: write outside repo root"}
    ]
    invs = extract_default_invariants(msgs)
    assert Invariant("deny_reason", "write outside repo root") in invs


def test_extract_dedupes_repeated_anchors():
    msgs = [
        {"role": "user", "content": "src/x.py:1 mentioned"},
        {"role": "assistant", "content": "yes, src/x.py:1 again"},
    ]
    invs = extract_default_invariants(msgs)
    anchors = [i for i in invs if i.kind == "file_anchor"]
    assert len(anchors) == 1


def test_extract_ignores_non_string_content():
    msgs = [
        {"role": "user", "content": None},
        {"role": "user", "content": {"nested": "object"}},
    ]
    assert extract_default_invariants(msgs) == []


def test_extract_finds_anchor_across_languages():
    msgs = [
        {"role": "user", "content": "see lib/foo.go:55 and src/Bar.kt:99"},
    ]
    invs = extract_default_invariants(msgs)
    values = {i.value for i in invs if i.kind == "file_anchor"}
    assert values == {"lib/foo.go:55", "src/Bar.kt:99"}


def test_extract_returns_stable_kinds_order():
    msgs = [
        {"role": "user", "content": "src/x.py:1 test_x deny: y"},
    ]
    invs = extract_default_invariants(msgs)
    kinds = [i.kind for i in invs]
    assert kinds == sorted(kinds, key=lambda k: ["file_anchor", "test_name", "deny_reason"].index(k))


def test_invariant_rejects_empty_value():
    with pytest.raises(ValueError):
        Invariant("free", "")


# ────────────────────────────────────────────────────────────────
# validate_compaction
# ────────────────────────────────────────────────────────────────


def _result(summary: str, kept: list[dict] | None = None) -> CompactResult:
    kept = kept or []
    head = [{"role": "system", "content": "SOUL"}]
    summary_msg = {"role": "system", "content": summary}
    return CompactResult(
        kept_raw=kept,
        summary=summary,
        dropped_count=5,
        summary_tokens=len(summary) // 4,
        summarised_messages=[*head, summary_msg, *kept],
    )


def test_validate_empty_invariants_passes_trivially():
    rep = validate_compaction(_result("anything"), [])
    assert rep.passed
    assert rep.invariants_checked == 0


def test_validate_passes_when_all_invariants_in_summary():
    rep = validate_compaction(
        _result("preserved src/x.py:42 and test_login"),
        [
            Invariant("file_anchor", "src/x.py:42"),
            Invariant("test_name", "test_login"),
        ],
    )
    assert rep.passed
    assert rep.invariants_failed == ()


def test_validate_fails_with_specific_missing_invariants():
    rep = validate_compaction(
        _result("kept src/x.py:42 but lost the deny reason"),
        [
            Invariant("file_anchor", "src/x.py:42"),
            Invariant("deny_reason", "write outside repo root"),
        ],
    )
    assert not rep.passed
    assert len(rep.invariants_failed) == 1
    assert rep.invariants_failed[0].kind == "deny_reason"


def test_validate_accepts_invariant_present_in_kept_raw():
    """A kept-raw tail that still mentions the anchor counts as preserved."""
    rep = validate_compaction(
        _result(
            "lost it in summary",
            kept=[{"role": "user", "content": "I still see src/x.py:42 here"}],
        ),
        [Invariant("file_anchor", "src/x.py:42")],
    )
    assert rep.passed


def test_validation_report_invariants_passed_is_derived():
    rep = ValidationReport(
        invariants_checked=5,
        invariants_failed=(Invariant("free", "a"), Invariant("free", "b")),
    )
    assert rep.invariants_passed == 3


# ────────────────────────────────────────────────────────────────
# compact_messages_validated end-to-end
# ────────────────────────────────────────────────────────────────


class _StubLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = 0

    def generate(self, **_kw) -> dict:
        self.calls += 1
        return {"content": self.response}


def _long_conversation(n: int = 12) -> list[dict]:
    msgs: list[dict] = [{"role": "system", "content": "you are lyra"}]
    msgs.append({"role": "user", "content": "edit src/api.py:88 please"})
    for i in range(n):
        msgs.append({"role": "assistant", "content": f"step {i}"})
        msgs.append({"role": "tool", "tool_call_id": f"t{i}", "content": f"ok {i}"})
    msgs.append({"role": "user", "content": "did test_api_returns_json pass?"})
    return msgs


def test_validated_call_emits_metrics_when_summary_keeps_anchor():
    llm = _StubLLM("compacted: src/api.py:88 plan held; test_api_returns_json still failing")
    metrics: list[tuple[str, object]] = []

    out = compact_messages_validated(
        _long_conversation(),
        llm=llm,
        keep_last=2,
        on_metric=lambda name, value: metrics.append((name, value)),
    )

    assert out.report.passed
    assert out.result.dropped_count > 0
    by_name: dict[str, int] = {n: int(v) for n, v in metrics}  # type: ignore[arg-type]
    assert by_name["context.compaction.validation.passed"] == 1
    assert by_name["context.compaction.validation.failed_count"] == 0
    assert by_name["context.compaction.validation.checked"] >= 2


def test_validated_call_flags_missing_invariant():
    llm = _StubLLM("super short summary that forgets anchors")

    out = compact_messages_validated(
        _long_conversation(),
        llm=llm,
        keep_last=2,
    )

    assert not out.report.passed
    # The file anchor in the leading user turn should have been
    # dropped by this stub.
    missing_values = {i.value for i in out.report.invariants_failed}
    assert "src/api.py:88" in missing_values
    assert out.metrics["context.compaction.validation.passed"] == 0


def test_validated_call_honours_explicit_invariants_only():
    llm = _StubLLM("summary mentioning src/api.py:88")
    out = compact_messages_validated(
        _long_conversation(),
        llm=llm,
        keep_last=2,
        invariants=[Invariant("free", "MUST-APPEAR")],
        extract_invariants=False,
    )
    assert not out.report.passed
    assert out.report.invariants_failed[0].value == "MUST-APPEAR"
    assert out.report.invariants_checked == 1


def test_validated_call_merges_explicit_and_auto_invariants():
    llm = _StubLLM("includes src/api.py:88 plus MUST-APPEAR sentinel")
    out = compact_messages_validated(
        _long_conversation(),
        llm=llm,
        keep_last=2,
        invariants=[Invariant("free", "MUST-APPEAR")],
        extract_invariants=True,
    )
    # Has both auto-extracted anchors AND the explicit free invariant —
    # the merged checked count is strictly greater than either source.
    assert out.report.invariants_checked >= 2
    assert out.report.passed

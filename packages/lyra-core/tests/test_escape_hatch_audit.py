"""Red tests for --no-tdd escape-hatch audit trail."""
from __future__ import annotations

from pathlib import Path

from lyra_core.tdd.audit import EscapeHatchAudit


def test_record_and_summarise(tmp_path: Path) -> None:
    audit = EscapeHatchAudit(log_path=tmp_path / "no_tdd.jsonl")
    audit.record(session_id="s1", reason="urgent hotfix", user="kane", tool="Edit")
    audit.record(session_id="s2", reason="poc spike", user="kane", tool="Write")

    summary = audit.summary()
    assert summary.total == 2
    assert summary.by_user["kane"] == 2
    assert "urgent hotfix" in {entry.reason for entry in audit.entries()}


def test_audit_persists_across_instances(tmp_path: Path) -> None:
    log = tmp_path / "no_tdd.jsonl"
    a1 = EscapeHatchAudit(log_path=log)
    a1.record(session_id="s1", reason="hotfix", user="kane", tool="Edit")

    a2 = EscapeHatchAudit(log_path=log)
    assert a2.summary().total == 1


def test_audit_jsonl_format(tmp_path: Path) -> None:
    import json

    log = tmp_path / "no_tdd.jsonl"
    audit = EscapeHatchAudit(log_path=log)
    audit.record(session_id="s1", reason="hotfix", user="kane", tool="Edit")
    raw = log.read_text().strip().splitlines()
    assert len(raw) == 1
    obj = json.loads(raw[0])
    assert obj["session_id"] == "s1"
    assert obj["reason"] == "hotfix"

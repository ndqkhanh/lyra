"""Red tests for the three shipped hooks in Phase 1:
    1. tdd-gate stub           — block writes to src/** without RED proof
    2. secrets-scan            — block write/edit/bash args carrying secrets
    3. destructive-pattern     — block rm -rf / and similar catastrophic bash
"""
from __future__ import annotations

from harness_core.messages import ToolCall, ToolResult

from lyra_core.hooks.destructive_pattern import destructive_pattern_hook
from lyra_core.hooks.secrets_scan import secrets_scan_hook
from lyra_core.hooks.tdd_gate import TDDGateContext, make_tdd_gate_hook

# ------------------------------------------------------------------
# secrets-scan
# ------------------------------------------------------------------


def test_secrets_scan_blocks_aws_key_in_write() -> None:
    call = ToolCall(
        id="c1",
        name="Write",
        args={"path": "config.env", "content": "AWS_SECRET=AKIAIOSFODNN7EXAMPLE"},
    )
    d = secrets_scan_hook(call, None)
    assert d.block is True
    assert "secret" in d.reason.lower()


def test_secrets_scan_blocks_gh_token_in_bash() -> None:
    call = ToolCall(
        id="c1",
        name="Bash",
        args={"command": "curl -H 'Authorization: Bearer ghp_1234567890abcdef1234567890abcdef1234'"},
    )
    d = secrets_scan_hook(call, None)
    assert d.block is True


def test_secrets_scan_passes_clean_write() -> None:
    call = ToolCall(
        id="c1",
        name="Write",
        args={"path": "README.md", "content": "# hello"},
    )
    d = secrets_scan_hook(call, None)
    assert d.block is False


def test_secrets_scan_blocks_private_key_in_edit() -> None:
    call = ToolCall(
        id="c1",
        name="Edit",
        args={
            "path": "src/client.py",
            "old": "K1",
            "new": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...",
        },
    )
    d = secrets_scan_hook(call, None)
    assert d.block is True


# ------------------------------------------------------------------
# destructive-pattern
# ------------------------------------------------------------------


def test_destructive_pattern_blocks_rm_rf_root() -> None:
    call = ToolCall(id="c1", name="Bash", args={"command": "rm -rf /"})
    d = destructive_pattern_hook(call, None)
    assert d.block is True


def test_destructive_pattern_blocks_rm_rf_home() -> None:
    call = ToolCall(id="c1", name="Bash", args={"command": "rm -rf ~"})
    d = destructive_pattern_hook(call, None)
    assert d.block is True


def test_destructive_pattern_blocks_dd_to_disk() -> None:
    call = ToolCall(
        id="c1", name="Bash", args={"command": "dd if=/dev/zero of=/dev/sda"}
    )
    d = destructive_pattern_hook(call, None)
    assert d.block is True


def test_destructive_pattern_blocks_mkfs() -> None:
    call = ToolCall(id="c1", name="Bash", args={"command": "mkfs.ext4 /dev/sda1"})
    d = destructive_pattern_hook(call, None)
    assert d.block is True


def test_destructive_pattern_blocks_force_push_main() -> None:
    call = ToolCall(
        id="c1", name="Bash", args={"command": "git push --force origin main"}
    )
    d = destructive_pattern_hook(call, None)
    assert d.block is True


def test_destructive_pattern_allows_safe_rm() -> None:
    call = ToolCall(
        id="c1", name="Bash", args={"command": "rm .lyra/scratch.txt"}
    )
    d = destructive_pattern_hook(call, None)
    assert d.block is False


# ------------------------------------------------------------------
# tdd-gate (stub contract — full gate is Phase 4, but Phase 1 covers the
# core "src/** write without RED proof is blocked" invariant)
# ------------------------------------------------------------------


def test_tdd_gate_blocks_src_write_without_red_proof() -> None:
    ctx = TDDGateContext(repo_root="/fake", red_proof_present=False)
    hook = make_tdd_gate_hook(ctx)
    call = ToolCall(
        id="c1",
        name="Write",
        args={"path": "src/feature.py", "content": "def f(): ..."},
    )
    d = hook(call, None)
    assert d.block is True
    assert "red" in d.reason.lower() or "tdd" in d.reason.lower()


def test_tdd_gate_allows_src_write_with_red_proof() -> None:
    ctx = TDDGateContext(repo_root="/fake", red_proof_present=True)
    hook = make_tdd_gate_hook(ctx)
    call = ToolCall(
        id="c1",
        name="Write",
        args={"path": "src/feature.py", "content": "def f(): return 1"},
    )
    d = hook(call, None)
    assert d.block is False


def test_tdd_gate_allows_test_write_without_red_proof() -> None:
    """Writing/editing tests/** is always allowed — the whole point is to get a RED."""
    ctx = TDDGateContext(repo_root="/fake", red_proof_present=False)
    hook = make_tdd_gate_hook(ctx)
    call = ToolCall(
        id="c1",
        name="Write",
        args={"path": "tests/test_feature.py", "content": "def test_f(): ..."},
    )
    d = hook(call, None)
    assert d.block is False


def test_tdd_gate_ignores_read() -> None:
    ctx = TDDGateContext(repo_root="/fake", red_proof_present=False)
    hook = make_tdd_gate_hook(ctx)
    call = ToolCall(id="c1", name="Read", args={"path": "src/feature.py"})
    d = hook(call, None)
    assert d.block is False


def test_tdd_gate_respects_disable_flag() -> None:
    """Escape hatch --no-tdd: still logs but does not block."""
    ctx = TDDGateContext(repo_root="/fake", red_proof_present=False, enabled=False)
    hook = make_tdd_gate_hook(ctx)
    call = ToolCall(
        id="c1",
        name="Write",
        args={"path": "src/feature.py", "content": "x"},
    )
    d = hook(call, None)
    assert d.block is False
    assert "disabled" in d.annotation.lower() or "skipped" in d.annotation.lower()


def test_tdd_gate_post_hook_annotates_on_result() -> None:
    """POST hook checks do not block but annotate if tests didn't run."""
    ctx = TDDGateContext(repo_root="/fake", red_proof_present=True)
    hook = make_tdd_gate_hook(ctx, event="POST")
    call = ToolCall(
        id="c1",
        name="Write",
        args={"path": "src/feature.py", "content": "def f(): ..."},
    )
    result = ToolResult(call_id="c1", content="ok", is_error=False)
    d = hook(call, result)
    assert d.block is False

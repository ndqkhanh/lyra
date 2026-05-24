from harness_core.messages import ToolCall
from harness_core.permissions import (
    Decision,
    PermissionMode,
    PermissionPolicy,
    resolve_decision,
)


def _call(name="edit", **args):
    return ToolCall(id="c1", name=name, args=args)


def test_plan_mode_blocks_writes():
    d = resolve_decision(_call("edit"), mode=PermissionMode.PLAN, tool_writes=True)
    assert d.decision == Decision.DENY
    assert "plan mode" in d.reason


def test_plan_mode_allows_reads():
    d = resolve_decision(_call("read"), mode=PermissionMode.PLAN, tool_writes=False)
    assert d.decision == Decision.ALLOW


def test_default_mode_asks_on_writes():
    d = resolve_decision(_call("edit"), mode=PermissionMode.DEFAULT, tool_writes=True)
    assert d.decision == Decision.ASK


def test_default_mode_allows_reads():
    d = resolve_decision(_call("read"), mode=PermissionMode.DEFAULT, tool_writes=False)
    assert d.decision == Decision.ALLOW


def test_accept_edits_auto_runs_writes():
    d = resolve_decision(
        _call("edit"), mode=PermissionMode.ACCEPT_EDITS, tool_writes=True
    )
    assert d.decision == Decision.ALLOW


def test_accept_edits_still_asks_destructive():
    d = resolve_decision(
        _call("rm"), mode=PermissionMode.ACCEPT_EDITS, tool_writes=True, tool_risk="destructive"
    )
    assert d.decision == Decision.ASK


def test_deny_rule_wins_over_mode():
    policy = PermissionPolicy(deny=["rm*"])
    d = resolve_decision(_call("rm"), mode=PermissionMode.BYPASS, policy=policy)
    assert d.decision == Decision.DENY
    assert "deny rule" in d.reason


def test_allow_rule_overrides_default_ask():
    # Signature is sorted-key "edit(content=hi,path=foo.md)"
    policy = PermissionPolicy(allow=["edit(*)"])
    d = resolve_decision(
        _call("edit", path="foo.md", content="hi"),
        mode=PermissionMode.DEFAULT,
        policy=policy,
        tool_writes=True,
    )
    assert d.decision == Decision.ALLOW


def test_ask_rule_forces_ask():
    policy = PermissionPolicy(ask=["deploy"])
    d = resolve_decision(_call("deploy"), mode=PermissionMode.BYPASS, policy=policy)
    # bypass mode short-circuits to allow *before* ask rule unless deny
    # so in bypass an ask rule is silently dropped — test default instead
    assert d.decision == Decision.ALLOW

    d2 = resolve_decision(_call("deploy"), mode=PermissionMode.DEFAULT, policy=policy)
    assert d2.decision == Decision.ASK


def test_bypass_mode_allows_everything_except_denies():
    d = resolve_decision(_call("edit"), mode=PermissionMode.BYPASS, tool_writes=True)
    assert d.decision == Decision.ALLOW

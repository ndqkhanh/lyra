"""
Tests for the deterministic safety kernel and the misevolution guard.

Covers:
- Tool gate: allowlist, denylist, rate limiting
- Filesystem gate: path allowlist, traversal prevention
- Network gate: domain allowlist, internal IP blocking
- Process gate: escalation prevention, max concurrent
- Audit trail integrity (hash chain)
- Misevolution guard: validation, drift detection, rollback
- Anti-leakage loop: repair failing skills deterministically
"""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from lyra.safety.deterministic_kernel import (
    AgentAction,
    ActionVerdict,
    AuditLogEntry,
    DeterministicSafetyKernel,
    GateResult,
    SafetyConfig,
    build_default_kernel,
)
from lyra.safety.misevolution_guard import (
    AntiLeakageLoop,
    DriftReport,
    FrozenEvaluationSuite,
    MisevolutionGuard,
    SkillVersion,
    ValidationCheck,
    ValidationResult,
    check_no_dangerous_tools,
    check_no_fork_bomb,
    check_no_internal_access,
    check_no_privilege_escalation,
    default_evaluation_suite,
)


# ======================================================================
# DeterministicSafetyKernel tests
# ======================================================================


class TestToolGate:
    """Tool gate: allowlist, denylist, rate limiting."""

    def test_allowlisted_tool_is_allowed(self):
        config = SafetyConfig(
            allowed_tools=["Read", "Write", "Edit"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(action_type="tool", name="Read", args={})
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ALLOW

    def test_denied_tool_is_blocked(self):
        config = SafetyConfig(
            allowed_tools=["Read"],
            denied_tools=["Bash"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(action_type="tool", name="Bash", args={})
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "denied" in result.reason.lower()

    def test_unlisted_tool_default_deny(self):
        config = SafetyConfig(
            default_deny=True,
            allowed_tools=["Read"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(action_type="tool", name="WebSearch", args={})
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY

    def test_unlisted_tool_asks_when_not_default_deny(self):
        config = SafetyConfig(
            default_deny=False,
            allowed_tools=["Read"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(action_type="tool", name="WebSearch", args={})
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ASK

    def test_rate_limit_exceeded(self):
        config = SafetyConfig(
            allowed_tools=["Bash"],
            tool_rate_limits={"Bash": 3},
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="tool",
            name="Bash",
            args={"_call_count": 3},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "rate limit" in result.reason.lower()

    def test_rate_limit_not_exceeded(self):
        config = SafetyConfig(
            allowed_tools=["Bash"],
            tool_rate_limits={"Bash": 5},
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="tool",
            name="Bash",
            args={"_call_count": 3},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ALLOW

    def test_gate_action_batch(self):
        config = SafetyConfig(
            allowed_tools=["Read", "Write"],
        )
        kernel = DeterministicSafetyKernel(config)

        actions = [
            AgentAction(action_type="tool", name="Read", args={}),
            AgentAction(action_type="tool", name="Bash", args={}),
            AgentAction(action_type="tool", name="Write", args={}),
        ]
        results = kernel.gate_action_batch(actions)

        assert len(results) == 3
        assert results[0].verdict == ActionVerdict.ALLOW
        assert results[1].verdict == ActionVerdict.DENY
        assert results[2].verdict == ActionVerdict.ALLOW


class TestFilesystemGate:
    """Filesystem gate: path allowlist, traversal prevention."""

    def test_allowed_path_passes(self):
        config = SafetyConfig(
            allowed_path_prefixes=["/workspace/project"],
            worktree_root="/workspace/project",
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="filesystem",
            name="/workspace/project/src/main.py",
            args={"file_path": "src/main.py"},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ALLOW

    def test_denied_path_is_blocked(self):
        config = SafetyConfig(
            default_deny=True,
            allowed_path_prefixes=["/workspace/project"],
            worktree_root="/workspace/project",
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="filesystem",
            name="/etc/passwd",
            args={"file_path": "/etc/passwd"},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY

    def test_traversal_outside_worktree_is_blocked(self):
        config = SafetyConfig(
            worktree_root="/workspace/project",
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="filesystem",
            name="../../etc/passwd",
            args={"file_path": "../../etc/passwd"},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "outside worktree" in result.reason.lower()

    def test_denied_path_pattern(self):
        config = SafetyConfig(
            allowed_path_prefixes=["/workspace"],
            denied_path_patterns=["/workspace/secrets/*"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="filesystem",
            name="/workspace/secrets/api_key.txt",
            args={"file_path": "/workspace/secrets/api_key.txt"},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "denied" in result.reason.lower()

    def test_denied_path_as_name_field(self):
        """When args.file_path is missing, gate uses action.name."""
        config = SafetyConfig(
            worktree_root="/workspace",
            allowed_path_prefixes=["/workspace"],
            denied_path_patterns=["/workspace/secrets/*"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="filesystem",
            name="/workspace/secrets/key.txt",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY


class TestNetworkGate:
    """Network gate: domain allowlist, internal IP blocking."""

    def test_allowed_domain_passes(self):
        config = SafetyConfig(
            allowed_domains=["api.example.com"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="network",
            name="api.example.com",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ALLOW

    def test_blocked_domain_is_denied(self):
        config = SafetyConfig(
            allowed_domains=["*.example.com"],
            blocked_domains=["evil.example.com"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="network",
            name="evil.example.com",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY

    def test_internal_ip_is_denied(self):
        config = SafetyConfig(allow_internal_ips=False)
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="network",
            name="10.0.0.5",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "internal" in result.reason.lower()

    def test_internal_ip_allowlisted_when_permitted(self):
        config = SafetyConfig(
            allow_internal_ips=True,
            allowed_domains=["*"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="network",
            name="192.168.1.1",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ALLOW

    def test_loopback_is_denied(self):
        config = SafetyConfig(allow_internal_ips=False)
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="network",
            name="127.0.0.1",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY

    def test_localhost_hostname_is_denied(self):
        config = SafetyConfig(allow_internal_ips=False)
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="network",
            name="localhost",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY

    def test_private_ipv6_is_denied(self):
        config = SafetyConfig(allow_internal_ips=False)
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="network",
            name="fc00::1",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY

    def test_unlisted_domain_with_default_deny(self):
        config = SafetyConfig(
            default_deny=True,
            allowed_domains=["api.example.com"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="network",
            name="other.com",
            args={},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY


class TestProcessGate:
    """Process gate: escalation prevention, max concurrent."""

    def test_safe_command_allowed(self):
        config = SafetyConfig()
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="process",
            name="ls",
            args={"command": "ls -la"},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ALLOW

    def test_sudo_is_blocked(self):
        config = SafetyConfig()
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="process",
            name="sudo",
            args={"command": "sudo rm -rf /"},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "privilege escalation" in result.reason.lower()

    def test_chmod_777_is_blocked(self):
        config = SafetyConfig()
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="process",
            name="chmod",
            args={"command": "chmod 777 /etc/passwd"},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY

    def test_forbidden_pattern_via_config(self):
        config = SafetyConfig(
            forbidden_process_patterns=["docker exec"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="process",
            name="docker",
            args={"command": "docker exec -it bash"},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "forbidden" in result.reason.lower()

    def test_max_concurrent_exceeded(self):
        config = SafetyConfig(max_processes_per_agent=2)
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="process",
            name="ls",
            args={"command": "ls", "_active_process_count": 2},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "active processes" in result.reason.lower()

    def test_max_concurrent_not_exceeded(self):
        config = SafetyConfig(max_processes_per_agent=5)
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="process",
            name="ls",
            args={"command": "ls", "_active_process_count": 2},
        )
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ALLOW


class TestUnknownActionType:
    """Unknown action type handling."""

    def test_unknown_type_default_deny(self):
        config = SafetyConfig(default_deny=True)
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(action_type="quantum", name="compute", args={})
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.DENY
        assert "unknown" in result.reason.lower()

    def test_unknown_type_asks_when_not_default_deny(self):
        config = SafetyConfig(default_deny=False)
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(action_type="quantum", name="compute", args={})
        result = kernel.gate_action(action)

        assert result.verdict == ActionVerdict.ASK


class TestAuditTrail:
    """Audit trail immutability and hash-chain integrity."""

    def test_audit_log_records_decisions(self):
        config = SafetyConfig(allowed_tools=["Read"])
        kernel = DeterministicSafetyKernel(config)

        kernel.gate_action(AgentAction(action_type="tool", name="Read", args={}))
        kernel.gate_action(AgentAction(action_type="tool", name="Bash", args={}))

        assert kernel.audit_log_count == 2
        assert kernel.audit_log[0].gate_result.verdict == ActionVerdict.ALLOW
        assert kernel.audit_log[1].gate_result.verdict == ActionVerdict.DENY

    def test_audit_log_entries_are_frozen(self):
        config = SafetyConfig(allowed_tools=["Read"])
        kernel = DeterministicSafetyKernel(config)

        kernel.gate_action(AgentAction(action_type="tool", name="Read"))
        entry = kernel.audit_log[0]

        # Confirm dataclass is frozen
        with pytest.raises(AttributeError):
            entry.index = 99  # type: ignore[misc]

    def test_audit_integrity_returns_true_for_unmodified_log(self):
        config = SafetyConfig(allowed_tools=["Read", "Bash"])
        kernel = DeterministicSafetyKernel(config)

        kernel.gate_action(AgentAction(action_type="tool", name="Read"))
        kernel.gate_action(AgentAction(action_type="tool", name="Bash"))
        kernel.gate_action(AgentAction(action_type="tool", name="Read"))

        assert kernel.verify_audit_integrity() is True

    def test_hash_chain_links_entries(self):
        config = SafetyConfig(allowed_tools=["Read"])
        kernel = DeterministicSafetyKernel(config)

        kernel.gate_action(AgentAction(action_type="tool", name="Read"))
        kernel.gate_action(AgentAction(action_type="tool", name="Read"))

        assert kernel.audit_log_count == 2
        # Second entry's previous_hash should match first entry's entry_hash
        assert (
            kernel.audit_log[1].previous_hash == kernel.audit_log[0].entry_hash
        )

    def test_genesis_entry_has_empty_previous_hash(self):
        kernel = build_default_kernel()

        kernel.gate_action(AgentAction(action_type="tool", name="Read"))

        assert kernel.audit_log[0].previous_hash == ""

    def test_audit_log_entry_contents(self):
        kernel = build_default_kernel()

        action = AgentAction(
            action_type="tool",
            name="Bash",
            args={"command": "ls"},
            agent_id="agent-01",
        )
        kernel.gate_action(action)

        entry = kernel.audit_log[0]
        assert entry.index == 0
        assert entry.action.name == "Bash"
        assert entry.action.agent_id == "agent-01"


class TestBuildDefaultKernel:
    """Default kernel factory."""

    def test_build_default_kernel_denies_everything(self):
        kernel = build_default_kernel()

        result = kernel.gate_action(
            AgentAction(action_type="tool", name="Read", args={})
        )
        assert result.verdict == ActionVerdict.DENY

        result = kernel.gate_action(
            AgentAction(action_type="tool", name="Bash", args={})
        )
        assert result.verdict == ActionVerdict.DENY

    def test_default_kernel_is_deny_all(self):
        kernel = build_default_kernel()
        assert kernel.config.default_deny is True
        assert kernel.config.allowed_tools == ()


# ======================================================================
# MisevolutionGuard tests
# ======================================================================


class TestFrozenEvaluationSuite:
    """Frozen evaluation suite: immutability after seal."""

    def test_seal_prevents_modification(self):
        suite = FrozenEvaluationSuite()
        suite.add_check("test_check", lambda v: ValidationCheck(
            check_name="test_check",
            passed=True,
            detail="always passes",
        ))
        suite.seal()

        with pytest.raises(RuntimeError, match="sealed"):
            suite.add_check("another_check", lambda v: ValidationCheck(
                check_name="another_check",
                passed=True,
            ))

    def test_validate_returns_all_checks(self):
        suite = default_evaluation_suite()

        skill = SkillVersion(
            skill_id="test-skill",
            version="1.0.0",
            content={"prompt": "Read files and search the web"},
        )
        result = suite.validate(skill)

        assert result.total_checks == 4  # all built-in checks
        assert result.passed  # no dangerous content

    def test_validate_detects_privesc(self):
        suite = default_evaluation_suite()

        skill = SkillVersion(
            skill_id="dangerous",
            version="1.0.0",
            content={"command": "sudo rm -rf /"},
        )
        result = suite.validate(skill)

        assert not result.passed
        assert len(result.errors) >= 1
        assert result.errors[0].check_name == "no_privesc"

    def test_add_checks_before_seal(self):
        suite = FrozenEvaluationSuite()
        suite.add_checks({
            "a": lambda v: ValidationCheck(check_name="a", passed=True),
            "b": lambda v: ValidationCheck(check_name="b", passed=True),
        })
        suite.seal()

        skill = SkillVersion(
            skill_id="test",
            version="1.0.0",
            content={"x": "y"},
        )
        result = suite.validate(skill)
        assert result.total_checks == 2

    def test_remove_check_before_seal(self):
        suite = FrozenEvaluationSuite()
        suite.add_check("temp", lambda v: ValidationCheck(check_name="temp", passed=True))
        suite.remove_check("temp")
        suite.seal()

        skill = SkillVersion(
            skill_id="test",
            version="1.0.0",
            content={"x": "y"},
        )
        result = suite.validate(skill)
        assert result.total_checks == 0


class TestMisevolutionGuard:
    """MisevolutionGuard: validation, drift monitoring, rollback."""

    def test_validate_skill_passes(self):
        guard = MisevolutionGuard()

        skill = SkillVersion(
            skill_id="safe-skill",
            version="1.0.0",
            content={"prompt": "Summarise documents"},
        )
        result = guard.validate_skill(skill)

        assert result.passed
        assert result.skill_id == "safe-skill"

    def test_validate_skill_fails_on_dangerous_content(self):
        guard = MisevolutionGuard()

        skill = SkillVersion(
            skill_id="bad-skill",
            version="1.0.0",
            content={"command": "sudo rm -rf / && chmod 777 /etc"},
        )
        result = guard.validate_skill(skill)

        assert not result.passed
        assert len(result.errors) > 0

    def test_is_activatable_returns_true_for_safe_skill(self):
        guard = MisevolutionGuard()

        skill = SkillVersion(
            skill_id="safe",
            version="1.0.0",
            content={"prompt": "Read files"},
        )
        assert guard.is_activatable(skill) is True

    def test_is_activatable_returns_false_for_dangerous_skill(self):
        guard = MisevolutionGuard()

        skill = SkillVersion(
            skill_id="bad",
            version="1.0.0",
            content={"command": ":(){ :|:& };"},  # fork bomb
        )
        assert guard.is_activatable(skill) is False

    def test_register_version_and_retrieve(self):
        guard = MisevolutionGuard()

        skill = SkillVersion(
            skill_id="my-skill",
            version="1.0.0",
            content={"prompt": "hello"},
        )
        guard.register_version(skill)

        retrieved = guard.get_version("my-skill", "1.0.0")
        assert retrieved is not None
        assert retrieved.skill_id == "my-skill"
        assert retrieved.checksum == skill.checksum

    def test_get_versions_returns_all(self):
        guard = MisevolutionGuard()

        v1 = SkillVersion(skill_id="s", version="1.0.0", content={"a": 1})
        v2 = SkillVersion(skill_id="s", version="2.0.0", content={"a": 2})

        guard.register_version(v1)
        guard.register_version(v2)

        versions = guard.get_versions("s")
        assert len(versions) == 2

    def test_drift_monitor_reports_no_drift_for_stable_history(self):
        guard = MisevolutionGuard()

        safe_content = {"prompt": "Read files and summarise"}
        history = [
            SkillVersion(skill_id="s", version="1.0.0", content=safe_content),
            SkillVersion(skill_id="s", version="1.0.1", content=safe_content),
        ]
        report = guard.drift_monitor(history)

        assert not report.has_drift

    def test_drift_monitor_detects_degradation(self):
        guard = MisevolutionGuard()

        history = [
            SkillVersion(
                skill_id="s", version="1.0.0",
                content={"prompt": "Read files"},
            ),
            SkillVersion(
                skill_id="s", version="1.0.1",
                content={"command": "sudo rm -rf /"},
            ),
        ]
        report = guard.drift_monitor(history)

        assert report.has_drift
        assert report.safety_score_regression > 0

    def test_rollback_returns_safe_version(self):
        guard = MisevolutionGuard()

        safe = SkillVersion(
            skill_id="s", version="1.0.0",
            content={"prompt": "safe"},
        )
        bad = SkillVersion(
            skill_id="s", version="1.0.1",
            content={"command": "sudo rm -rf"},
        )

        guard.register_version(safe)
        guard.register_version(bad)

        rolled_back = guard.rollback("s", target_version="1.0.0")
        assert rolled_back is not None
        assert rolled_back.version == "1.0.0"
        assert rolled_back.checksum == safe.checksum

    def test_rollback_to_safe_version_when_target_none(self):
        guard = MisevolutionGuard()

        safe = SkillVersion(
            skill_id="s", version="1.0.0",
            content={"prompt": "safe"},
        )
        guard.register_version(safe)

        result = guard.rollback("s")
        assert result is not None
        assert result.version == "1.0.0"

    def test_rollback_returns_none_for_missing_skill(self):
        guard = MisevolutionGuard()

        result = guard.rollback("nonexistent")
        assert result is None

    def test_mark_safe_updates_safe_version(self):
        guard = MisevolutionGuard()

        v1 = SkillVersion(skill_id="s", version="1.0.0", content={"a": 1})
        v2 = SkillVersion(skill_id="s", version="2.0.0", content={"a": 2})

        guard.register_version(v1)
        guard.register_version(v2)

        guard.mark_safe("s", "2.0.0")
        safe = guard.get_safe_version("s")
        assert safe is not None
        assert safe.version == "2.0.0"

    def test_registered_skills_property(self):
        guard = MisevolutionGuard()

        guard.register_version(
            SkillVersion(skill_id="a", version="1.0.0", content={"x": 1})
        )
        guard.register_version(
            SkillVersion(skill_id="b", version="1.0.0", content={"x": 2})
        )

        skills = guard.registered_skills
        assert "a" in skills
        assert "b" in skills

    def test_first_version_auto_marked_safe(self):
        guard = MisevolutionGuard()

        v1 = SkillVersion(skill_id="s", version="1.0.0", content={"a": 1})
        guard.register_version(v1)

        safe = guard.get_safe_version("s")
        assert safe is not None
        assert safe.version == "1.0.0"


class TestDriftReport:
    """DriftReport properties and invariants."""

    def test_empty_report(self):
        report = DriftReport()
        assert not report.has_drift
        assert report.trend == "stable"

    def test_empty_history(self):
        guard = MisevolutionGuard()
        report = guard.drift_monitor([])
        assert not report.has_drift

    def test_single_version_history(self):
        guard = MisevolutionGuard()
        history = [
            SkillVersion(skill_id="s", version="1.0.0", content={"prompt": "hi"}),
        ]
        report = guard.drift_monitor(history)
        assert report.trend in ("stable", "improving")


class TestAntiLeakageLoop:
    """Anti-leakage loop: repair failing skills."""

    def test_repair_privesc_skill(self):
        guard = MisevolutionGuard()
        loop = AntiLeakageLoop(guard, max_iterations=3)

        failing_skill = SkillVersion(
            skill_id="bad-skill",
            version="1.0.0",
            content={"prompt": "Run this command: sudo rm -rf /"},
        )

        result, repaired = loop.repair_failing_skill(failing_skill)
        assert repaired is not None
        assert result.passed, (
            f"Anti-leakage loop should repair the skill. "
            f"Errors: {[e.detail for e in result.errors]}"
        )
        # Check that the repaired version removed 'sudo'
        content_str = json.dumps(repaired.content, default=str)
        assert "sudo" not in content_str, (
            "Repaired skill should not contain 'sudo'"
        )

    def test_repair_fork_bomb(self):
        guard = MisevolutionGuard()
        loop = AntiLeakageLoop(guard, max_iterations=3)

        failing_skill = SkillVersion(
            skill_id="bomb-skill",
            version="1.0.0",
            content={"script": "while true; do echo looping; done"},
        )

        result, repaired = loop.repair_failing_skill(failing_skill)
        assert repaired is not None
        assert result.passed

    @staticmethod
    def test_repair_internal_access():
        guard = MisevolutionGuard()
        loop = AntiLeakageLoop(guard, max_iterations=3)

        failing_skill = SkillVersion(
            skill_id="internal-skill",
            version="1.0.0",
            content={"url": "http://10.0.0.1/config"},
        )

        result, repaired = loop.repair_failing_skill(failing_skill)
        assert repaired is not None
        assert result.passed

    def test_repair_dangerous_tools(self):
        guard = MisevolutionGuard()
        loop = AntiLeakageLoop(guard, max_iterations=3)

        failing_skill = SkillVersion(
            skill_id="danger-skill",
            version="1.0.0",
            content={"command": "dd if=/dev/zero of=/dev/sda"},
        )

        result, repaired = loop.repair_failing_skill(failing_skill)
        assert repaired is not None
        assert result.passed

    def test_repair_fallback_to_rollback_when_exhausted(self):
        guard = MisevolutionGuard()

        safe_skill = SkillVersion(
            skill_id="will-fail",
            version="1.0.0",
            content={"prompt": "Read files"},
        )
        guard.register_version(safe_skill)

        bad_skill = SkillVersion(
            skill_id="will-fail",
            version="2.0.0",
            content={"command": "sudo rm -rf / && :(){ :|:& };: && "
                      "dd if=/dev/zero of=/dev/sda"},
        )

        loop = AntiLeakageLoop(guard, max_iterations=1)
        result, repaired = loop.repair_failing_skill(bad_skill)

        # With only 1 iteration, it may not repair everything; falls back to safe
        assert repaired is not None
        # The fallback should be the safe version
        assert repaired.checksum == safe_skill.checksum

    def test_repair_with_zero_failure_signals(self):
        """A skill that passes validation should not be modified."""
        guard = MisevolutionGuard()
        loop = AntiLeakageLoop(guard)

        passing_skill = SkillVersion(
            skill_id="good",
            version="1.0.0",
            content={"prompt": "Read files and summarise"},
        )

        result, repaired = loop.repair_failing_skill(passing_skill)
        assert result.passed
        assert repaired is not None
        assert repaired.version == "1.0.0"  # unchanged


class TestBuiltinChecks:
    """Individual built-in validation checks."""

    def test_check_no_privesc_passes(self):
        skill = SkillVersion(
            skill_id="safe", version="1.0.0", content={"cmd": "ls"}
        )
        result = check_no_privilege_escalation(skill)
        assert result.passed

    def test_check_no_privesc_fails(self):
        skill = SkillVersion(
            skill_id="bad", version="1.0.0", content={"cmd": "sudo rm"}
        )
        result = check_no_privilege_escalation(skill)
        assert not result.passed

    def test_check_no_fork_bomb_passes(self):
        skill = SkillVersion(
            skill_id="safe", version="1.0.0", content={"cmd": "ls"}
        )
        result = check_no_fork_bomb(skill)
        assert result.passed

    def test_check_no_fork_bomb_fails(self):
        skill = SkillVersion(
            skill_id="bad", version="1.0.0",
            content={"cmd": "while true; do echo x; done"},
        )
        result = check_no_fork_bomb(skill)
        assert not result.passed

    def test_check_no_internal_access_passes(self):
        skill = SkillVersion(
            skill_id="safe", version="1.0.0",
            content={"url": "https://api.example.com"},
        )
        result = check_no_internal_access(skill)
        assert result.passed

    def test_check_no_internal_access_fails(self):
        skill = SkillVersion(
            skill_id="bad", version="1.0.0",
            content={"url": "http://192.168.1.1/config"},
        )
        result = check_no_internal_access(skill)
        assert not result.passed

    def test_check_no_dangerous_tools_passes(self):
        skill = SkillVersion(
            skill_id="safe", version="1.0.0",
            content={"cmd": "grep pattern file"},
        )
        result = check_no_dangerous_tools(skill)
        assert result.passed

    def test_check_no_dangerous_tools_fails(self):
        skill = SkillVersion(
            skill_id="bad", version="1.0.0",
            content={"cmd": "rm -rf /"},
        )
        result = check_no_dangerous_tools(skill)
        assert not result.passed


class TestSkillVersion:
    """SkillVersion data model."""

    def test_checksum_auto_computed(self):
        skill = SkillVersion(
            skill_id="test", version="1.0.0", content={"a": 1},
        )
        assert len(skill.checksum) == 64  # SHA-256 hex

    def test_checksum_deterministic(self):
        skill1 = SkillVersion(
            skill_id="test", version="1.0.0", content={"a": 1},
        )
        skill2 = SkillVersion(
            skill_id="test", version="1.0.0", content={"a": 1},
        )
        assert skill1.checksum == skill2.checksum

    def test_checksum_changes_with_content(self):
        skill1 = SkillVersion(
            skill_id="test", version="1.0.0", content={"a": 1},
        )
        skill2 = SkillVersion(
            skill_id="test", version="1.0.0", content={"a": 2},
        )
        assert skill1.checksum != skill2.checksum

    def test_frozen(self):
        skill = SkillVersion(
            skill_id="test", version="1.0.0", content={"a": 1},
        )
        with pytest.raises(AttributeError):
            skill.version = "2.0.0"  # type: ignore[misc]


class TestValidationCheck:
    """ValidationCheck and ValidationResult invariants."""

    def test_validation_check_error_severity(self):
        check = ValidationCheck(
            check_name="test", passed=False, detail="fail",
            severity="error",
        )
        assert check.severity == "error"

    def test_validation_check_warning_severity(self):
        check = ValidationCheck(
            check_name="test", passed=False, detail="warn",
            severity="warning",
        )
        assert check.severity == "warning"

    def test_validation_result_errors_property(self):
        result = ValidationResult(
            passed=False,
            skill_id="s",
            version="1.0.0",
            checks=(
                ValidationCheck("c1", True),
                ValidationCheck("c2", False),
                ValidationCheck("c3", False, severity="warning"),
            ),
        )
        assert len(result.errors) == 1  # only c2 is error severity
        assert len(result.warnings) == 1  # c3
        assert result.passed_checks == 1
        assert result.failed_checks == 2

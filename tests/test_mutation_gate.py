"""Tests for SABER mutation-gated verification."""

from lyra.safety.mutation_gate import (
    MutationGate,
    ActionClass,
)


class TestMutationGate:
    """Mutation gate classification tests."""

    def test_read_is_auto_approved(self):
        gate = MutationGate()
        verdict = gate.classify("read_file", {"path": "/etc/config.json"})
        assert verdict.action_class == ActionClass.READ
        assert not verdict.is_mutating
        assert not verdict.requires_verification

    def test_search_is_auto_approved(self):
        gate = MutationGate()
        verdict = gate.classify("search_content", {"pattern": "TODO"})
        assert verdict.action_class == ActionClass.SEARCH
        assert not verdict.requires_verification

    def test_write_requires_verification(self):
        gate = MutationGate()
        verdict = gate.classify("write_file", {"path": "/src/main.py"})
        assert verdict.action_class == ActionClass.WRITE
        assert verdict.is_mutating
        assert verdict.requires_verification

    def test_execute_requires_verification(self):
        gate = MutationGate()
        verdict = gate.classify("execute_command", {"command": "rm -rf /"})
        assert verdict.action_class == ActionClass.EXECUTE
        assert verdict.requires_verification

    def test_git_push_requires_verification(self):
        gate = MutationGate()
        verdict = gate.classify("git_push", {})
        assert verdict.action_class == ActionClass.NETWORK_WRITE
        assert verdict.requires_verification

    def test_safe_write_auto_approved(self):
        """Writes to known-safe targets bypass verification."""
        gate = MutationGate()
        verdict = gate.classify("write_file", {"path": ".gitignore"})
        assert not verdict.requires_verification

    def test_readme_write_auto_approved(self):
        gate = MutationGate()
        verdict = gate.classify("write_file", {"file_path": "README.md"})
        assert not verdict.requires_verification

    def test_unknown_tool_defaults_to_mutating(self):
        """Unknown tools should default to UNKNOWN → requires verification."""
        gate = MutationGate()
        verdict = gate.classify("mysterious_new_tool", {})
        assert verdict.action_class == ActionClass.UNKNOWN
        assert verdict.requires_verification  # Safe default

    def test_classify_batch(self):
        gate = MutationGate()
        calls = [
            ("read_file", {"path": "x.py"}),
            ("write_file", {"path": "x.py"}),
            ("search_content", {"pattern": "x"}),
            ("execute_command", {"command": "ls"}),
        ]
        verdicts = gate.classify_batch(calls)
        assert len(verdicts) == 4
        assert not verdicts[0].requires_verification  # read
        assert verdicts[1].requires_verification      # write
        assert not verdicts[2].requires_verification   # search
        assert verdicts[3].requires_verification       # execute

    def test_any_require_verification(self):
        gate = MutationGate()
        verdicts = gate.classify_batch([
            ("read_file", {"path": "a"}),
            ("write_file", {"path": "b"}),
        ])
        assert gate.any_require_verification(verdicts)

    def test_register_custom_tool(self):
        gate = MutationGate()
        gate.register_tool("safe_tool", ActionClass.READ)
        verdict = gate.classify("safe_tool", {})
        assert not verdict.requires_verification

    def test_heuristic_classification(self):
        """Unregistered tools should be classified by name heuristics."""
        gate = MutationGate()
        assert gate.classify("get_user_profile", {}).action_class == ActionClass.READ
        assert gate.classify("delete_record", {}).action_class == ActionClass.WRITE
        assert gate.classify("run_benchmarks", {}).action_class == ActionClass.EXECUTE

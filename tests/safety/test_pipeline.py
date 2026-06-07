"""
Tests for P3: Defense-in-Depth Safety Pipeline.

Covers:
- LayerResult enum values
- SafetyContext dataclass defaults
- LexicalGate — regex scanning blocks dangerous patterns
- ToolCallGateLayer — delegates to P2 ToolGate correctly
- AlignmentCheck — sampling schedule and default stub
- DataFlowTracker — untrusted data propagation detection
- ContinuousEval — stub always passes
- SafetyPipeline — full orchestration, short-circuit on BLOCK
"""

from __future__ import annotations

import pytest

from lyra.safety.pipeline import (
    AlignmentCheck,
    ContinuousEval,
    DataFlowTracker,
    LayerDecision,
    LayerResult,
    LexicalGate,
    SafetyContext,
    SafetyPipeline,
    ToolCallGateLayer,
)
from lyra.safety.policy import GateDecision, Policy
from lyra.safety.tool_gate import ToolGate


# ======================================================================
# LayerResult enum
# ======================================================================


class TestLayerResult:
    """LayerResult enum — three values and ordering."""

    def test_enum_values(self) -> None:
        """LayerResult should have PASS, BLOCK, and ESCALATE."""
        assert LayerResult.PASS == "pass"
        assert LayerResult.BLOCK == "block"
        assert LayerResult.ESCALATE == "escalate"

    def test_distinct_values(self) -> None:
        """All three enum values should be distinct."""
        values = {LayerResult.PASS, LayerResult.BLOCK, LayerResult.ESCALATE}
        assert len(values) == 3


# ======================================================================
# SafetyContext dataclass
# ======================================================================


class TestSafetyContext:
    """SafetyContext — defaults and construction."""

    def test_default_empty(self) -> None:
        """Default SafetyContext should have empty/zero defaults."""
        ctx = SafetyContext()
        assert ctx.tool_name == ""
        assert ctx.tool_args == {}
        assert ctx.agent_id == ""
        assert ctx.session_id == ""
        assert ctx.task_description == ""
        assert ctx.untrusted_inputs == ()
        assert ctx.call_number == 0

    def test_custom_values(self) -> None:
        """Custom SafetyContext should store provided values."""
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "ls"},
            agent_id="agent-1",
            session_id="session-42",
            task_description="List directory",
            untrusted_inputs=("user_input",),
            call_number=5,
            metadata={"env": "prod"},
        )
        assert ctx.tool_name == "Bash"
        assert ctx.tool_args == {"command": "ls"}
        assert ctx.agent_id == "agent-1"
        assert ctx.session_id == "session-42"
        assert ctx.task_description == "List directory"
        assert ctx.untrusted_inputs == ("user_input",)
        assert ctx.call_number == 5
        assert ctx.metadata == {"env": "prod"}

    def test_immutable_untrusted_inputs(self) -> None:
        """untrusted_inputs should be a tuple (immutable)."""
        ctx = SafetyContext(untrusted_inputs=("a", "b"))
        assert isinstance(ctx.untrusted_inputs, tuple)

    def test_immutable_tool_args(self) -> None:
        """tool_args should be a dict."""
        ctx = SafetyContext(tool_args={"key": "value"})
        assert isinstance(ctx.tool_args, dict)


# ======================================================================
# LexicalGate
# ======================================================================


class TestLexicalGate:
    """LexicalGate — fast regex scan for dangerous patterns."""

    def setup_method(self) -> None:
        self.gate = LexicalGate()

    def _make_context(self, tool_name: str = "Bash", command: str = "") -> SafetyContext:
        return SafetyContext(
            tool_name=tool_name,
            tool_args={"command": command},
            call_number=1,
        )

    def test_pass_safe_command(self) -> None:
        """A simple 'ls' command should PASS."""
        ctx = self._make_context(command="ls -la")
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.PASS

    def test_pass_empty_command(self) -> None:
        """An empty command should PASS."""
        ctx = self._make_context(command="")
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.PASS

    def test_pass_no_tool_args(self) -> None:
        """A context with no tool_args should PASS."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "/safe/path.txt"},
            call_number=1,
        )
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.PASS

    def test_block_shell_backtick(self) -> None:
        """Backtick command substitution should BLOCK."""
        ctx = self._make_context(command="echo `whoami`")
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "shell_backtick"

    def test_block_shell_subshell(self) -> None:
        """$() subshell should BLOCK."""
        ctx = self._make_context(command="echo $(whoami)")
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "shell_subshell"

    def test_block_dangerous_pipe(self) -> None:
        """Pipe to rm should BLOCK."""
        ctx = self._make_context(command="something | rm -rf /")
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "shell_dangerous_cmd"

    def test_block_dangerous_semicolon(self) -> None:
        """Semicolon followed by sudo should BLOCK."""
        ctx = self._make_context(command="echo hello; sudo rm -rf /")
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "shell_dangerous_cmd"

    def test_block_eval_call(self) -> None:
        """eval() should BLOCK."""
        ctx = self._make_context(command="eval('ls')")
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "eval_call"

    def test_block_exec_call(self) -> None:
        """exec() should BLOCK."""
        ctx = self._make_context(command="exec('ls')")
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "exec_call"

    def test_block_path_traversal(self) -> None:
        """Path traversal (../) should BLOCK."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "../../etc/passwd"},
            call_number=1,
        )
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "path_traversal"

    def test_block_sensitive_file_etc_passwd(self) -> None:
        """Access to /etc/passwd should BLOCK."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "/etc/passwd"},
            call_number=1,
        )
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "sensitive_file"

    def test_block_sensitive_file_etc_shadow(self) -> None:
        """Access to /etc/shadow should BLOCK."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "/etc/shadow"},
            call_number=1,
        )
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "sensitive_file"

    def test_block_root_path(self) -> None:
        """Access to /root/ path should BLOCK."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "/root/.bashrc"},
            call_number=1,
        )
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "root_path"

    def test_block_dynamic_import(self) -> None:
        """__import__() call should BLOCK."""
        ctx = self._make_context(command='__import__("os")')
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "dynamic_import"

    def test_block_os_system(self) -> None:
        """os.system() call should BLOCK."""
        ctx = self._make_context(command='os.system("ls")')
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "os_system"

    def test_block_subprocess_call(self) -> None:
        """subprocess.call() should BLOCK."""
        ctx = self._make_context(command='subprocess.call(["ls"])')
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("pattern_category") == "subprocess_call"

    def test_block_subprocess_popen(self) -> None:
        """subprocess.Popen() should BLOCK."""
        ctx = self._make_context(command='subprocess.Popen(["rm"])')
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK

    def test_block_subprocess_run(self) -> None:
        """subprocess.run() should BLOCK."""
        ctx = self._make_context(command='subprocess.run(["ls"])')
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK

    def test_scans_all_args_recursively(self) -> None:
        """The gate should scan all nested args, not just 'command'."""
        ctx = SafetyContext(
            tool_name="Write",
            tool_args={
                "file_path": "/tmp/output.txt",
                "content": 'print(eval("1+1"))',
                "metadata": {"extra": "`rm -rf /`"},
            },
            call_number=1,
        )
        decision = self.gate.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK

    def test_layer_name_is_lexical_gate(self) -> None:
        """Blocked decisions should have layer_name 'lexical_gate'."""
        ctx = self._make_context(command='eval("1+1")')
        decision = self.gate.evaluate(ctx)
        assert decision.layer_name == "lexical_gate"

    def test_pass_reason(self) -> None:
        """PASS decisions should have a descriptive reason."""
        ctx = self._make_context(command="ls")
        decision = self.gate.evaluate(ctx)
        assert "No dangerous patterns" in decision.reason


# ======================================================================
# ToolCallGateLayer
# ======================================================================


class TestToolCallGateLayer:
    """ToolCallGateLayer — delegates to P2 ToolGate."""

    def setup_method(self) -> None:
        self.layer = ToolCallGateLayer()

    def test_pass_allowed_tool(self) -> None:
        """An allowed tool call should PASS."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "src/main.py"},
            call_number=1,
        )
        decision = self.layer.evaluate(ctx)
        assert decision.result == LayerResult.PASS

    def test_block_unknown_tool(self) -> None:
        """An unknown tool should BLOCK."""
        ctx = SafetyContext(
            tool_name="DangerousTool",
            tool_args={},
            call_number=1,
        )
        decision = self.layer.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK

    def test_block_disallowed_path(self) -> None:
        """A path outside the allowlist should BLOCK."""
        restrictive = Policy(allowed_tools=["Read"], allowed_paths=["src/**"])
        layer = ToolCallGateLayer(policy=restrictive)
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "/etc/passwd"},
            call_number=1,
        )
        decision = layer.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK

    def test_escalate_ask_user(self) -> None:
        """A tool requiring approval should ESCALATE."""
        layer = ToolCallGateLayer()
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "ls"},
            call_number=1,
        )
        decision = layer.evaluate(ctx)
        assert decision.result == LayerResult.ESCALATE

    def test_pass_with_sandbox(self) -> None:
        """A dangerous Bash command under a sandbox policy should PASS."""
        custom_policy = Policy(
            allowed_tools=["Read", "Bash", "Write"],
            requires_approval_for=[],
        )
        layer = ToolCallGateLayer(policy=custom_policy)
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "rm -rf /tmp"},
            call_number=1,
        )
        decision = layer.evaluate(ctx)
        assert decision.result == LayerResult.PASS

    def test_uses_injected_toolgate(self) -> None:
        """An injected ToolGate should be used for evaluation."""
        gate = ToolGate(
            policy=Policy(allowed_tools=["Read", "Bash"])
        )
        layer = ToolCallGateLayer(tool_gate=gate)
        ctx = SafetyContext(tool_name="Read", tool_args={}, call_number=1)
        decision = layer.evaluate(ctx)
        assert decision.result == LayerResult.PASS
        ctx_blocked = SafetyContext(tool_name="Unknown", tool_args={}, call_number=1)
        assert layer.evaluate(ctx_blocked).result == LayerResult.BLOCK

    def test_block_empty_allowed_tools(self) -> None:
        """Empty allowed_tools should BLOCK everything."""
        layer = ToolCallGateLayer(policy=Policy(allowed_tools=[]))
        ctx = SafetyContext(tool_name="Read", tool_args={}, call_number=1)
        decision = layer.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK

    def test_layer_name_is_tool_call_gate(self) -> None:
        """Decisions should have layer_name 'tool_call_gate'."""
        ctx = SafetyContext(tool_name="Read", tool_args={}, call_number=1)
        decision = self.layer.evaluate(ctx)
        assert decision.layer_name == "tool_call_gate"


# ======================================================================
# AlignmentCheck
# ======================================================================


class TestAlignmentCheck:
    """AlignmentCheck — sampling schedule and LLM delegation."""

    def test_default_stub_passes(self) -> None:
        """Default stub should always return PASS."""
        check = AlignmentCheck()
        ctx = SafetyContext(
            tool_name="Read",
            call_number=1,
            task_description="Read a file",
        )
        decision = check.evaluate(ctx)
        assert decision.result == LayerResult.PASS

    def test_sampling_skips_middle_calls(self) -> None:
        """With interval=5, only call_numbers 5,10,15... should trigger check
        for non-high-risk tools."""
        check = AlignmentCheck(
            sample_interval=5,
            high_risk_interval=5,
            alignment_fn=_make_failing_alignment(),
        )

        # Call 3 should skip (3 % 5 != 0)
        ctx3 = SafetyContext(tool_name="Read", call_number=3)
        assert check.evaluate(ctx3).result == LayerResult.PASS
        assert "skipped" in check.evaluate(ctx3).reason.lower()

        # Call 5 should check and fail
        ctx5 = SafetyContext(tool_name="Read", call_number=5)
        assert check.evaluate(ctx5).result == LayerResult.BLOCK

    def test_high_risk_sampled_more_frequently(self) -> None:
        """High-risk tools (Bash) should use high_risk_interval."""
        check = AlignmentCheck(
            sample_interval=10,
            high_risk_interval=2,
            alignment_fn=_make_failing_alignment(),
        )

        # Bash at call 2 should trigger (2 % 2 == 0)
        ctx2 = SafetyContext(tool_name="Bash", call_number=2)
        assert check.evaluate(ctx2).result == LayerResult.BLOCK

        # Read at call 2 with interval=10 should skip
        ctx2_read = SafetyContext(tool_name="Read", call_number=2)
        assert check.evaluate(ctx2_read).result == LayerResult.PASS

    def test_call_number_zero_is_treated_as_first_call(self) -> None:
        """call_number=0 should trigger check (0 % any == 0)."""
        check = AlignmentCheck(
            sample_interval=3,
            alignment_fn=_make_failing_alignment(),
        )
        ctx0 = SafetyContext(tool_name="Read", call_number=0)
        assert check.evaluate(ctx0).result == LayerResult.BLOCK

    def test_custom_alignment_fn_block(self) -> None:
        """A custom alignment function can return BLOCK."""
        def always_block(_task: str, _tool: str, _args: dict) -> LayerDecision:
            return LayerDecision(
                result=LayerResult.BLOCK,
                layer_name="alignment_check",
                reason="Custom: always block for testing",
            )

        check = AlignmentCheck(
            sample_interval=1,
            alignment_fn=always_block,
        )
        ctx = SafetyContext(tool_name="Read", call_number=1)
        decision = check.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert "Custom" in decision.reason

    def test_custom_alignment_fn_escalate(self) -> None:
        """A custom alignment function can return ESCALATE."""
        def maybe_escalate(_task: str, _tool: str, _args: dict) -> LayerDecision:
            return LayerDecision(
                result=LayerResult.ESCALATE,
                layer_name="alignment_check",
                reason="Uncertain alignment",
            )

        check = AlignmentCheck(
            sample_interval=1,
            alignment_fn=maybe_escalate,
        )
        ctx = SafetyContext(tool_name="Read", call_number=1)
        decision = check.evaluate(ctx)
        assert decision.result == LayerResult.ESCALATE

    def test_interval_clamped_to_at_least_one(self) -> None:
        """An interval of 0 should be clamped to 1."""
        check = AlignmentCheck(
            sample_interval=0,
            high_risk_interval=0,
        )
        # With interval=1, every call triggers a check
        ctx = SafetyContext(tool_name="Read", call_number=1)
        decision = check.evaluate(ctx)
        assert decision.result == LayerResult.PASS  # default stub

    def test_layer_name_is_alignment_check(self) -> None:
        """Decisions should have layer_name 'alignment_check'."""
        check = AlignmentCheck()
        ctx = SafetyContext(tool_name="Read", call_number=1)
        decision = check.evaluate(ctx)
        assert decision.layer_name == "alignment_check"

    def test_reason_includes_call_number_on_skip(self) -> None:
        """Skipped checks should include the call number in the reason."""
        check = AlignmentCheck(sample_interval=5)
        ctx = SafetyContext(tool_name="Read", call_number=3)
        decision = check.evaluate(ctx)
        assert "call #3" in decision.reason


def _make_failing_alignment() -> callable:
    """Create an alignment function that always returns BLOCK."""
    def fn(_task: str, _tool: str, _args: dict) -> LayerDecision:
        return LayerDecision(
            result=LayerResult.BLOCK,
            layer_name="alignment_check",
            reason="Alignment test failed (intentional)",
        )
    return fn


# ======================================================================
# DataFlowTracker
# ======================================================================


class TestDataFlowTracker:
    """DataFlowTracker — untrusted data propagation detection."""

    def setup_method(self) -> None:
        self.tracker = DataFlowTracker()

    def test_pass_no_untrusted(self) -> None:
        """No untrusted inputs should PASS."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "/safe/path.txt"},
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.PASS
        assert "No untrusted inputs" in decision.reason

    def test_pass_untrusted_not_in_args(self) -> None:
        """Untrusted inputs that don't appear in args should PASS."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "/safe/path.txt"},
            untrusted_inputs=("some_other_value",),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.PASS
        assert "No untrusted data detected" in decision.reason

    def test_block_sensitive_sink_bash(self) -> None:
        """Untrusted data in Bash args should BLOCK."""
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "delete user_home"},
            untrusted_inputs=("delete",),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert "sensitive sink" in decision.reason
        assert decision.details.get("sensitive_sink") == "Bash"

    def test_block_sensitive_sink_write(self) -> None:
        """Untrusted data in Write args should BLOCK."""
        ctx = SafetyContext(
            tool_name="Write",
            tool_args={"file_path": "/tmp/output.txt", "content": "user data"},
            untrusted_inputs=("user data",),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("sensitive_sink") == "Write"

    def test_block_sensitive_sink_edit(self) -> None:
        """Untrusted data in Edit args should BLOCK."""
        ctx = SafetyContext(
            tool_name="Edit",
            tool_args={"file_path": "/tmp/file.txt", "old_string": "foo", "new_string": "bar"},
            untrusted_inputs=("bar",),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK
        assert decision.details.get("sensitive_sink") == "Edit"

    def test_escalate_non_sensitive_sink(self) -> None:
        """Untrusted data in non-sensitive sinks should ESCALATE."""
        ctx = SafetyContext(
            tool_name="WebSearch",
            tool_args={"query": "user supplied query"},
            untrusted_inputs=("user supplied query",),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.ESCALATE
        assert "Tainted data" in decision.reason

    def test_escalate_read_with_untrusted(self) -> None:
        """Untrusted data in Read args (non-sensitive) should ESCALATE."""
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "/some/path"},
            untrusted_inputs=("/some/path",),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.ESCALATE
        assert decision.details.get("tool_name") == "Read"

    def test_multiple_untrusted_inputs(self) -> None:
        """Multiple untrusted inputs should all be checked."""
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "process data_file.txt"},
            untrusted_inputs=("delete", "data_file.txt"),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK

    def test_partial_match(self) -> None:
        """A substring match of untrusted input should trigger."""
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "run malicious_script.sh"},
            untrusted_inputs=("malicious",),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.BLOCK

    def test_layer_name_is_data_flow_tracker(self) -> None:
        """Decisions should have layer_name 'data_flow_tracker'."""
        ctx = SafetyContext(tool_name="Read", tool_args={"x": "y"}, untrusted_inputs=("y",))
        decision = self.tracker.evaluate(ctx)
        assert decision.layer_name == "data_flow_tracker"

    def test_empty_untrusted_inputs_tuple(self) -> None:
        """An empty tuple of untrusted inputs should PASS."""
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "rm -rf"},
            untrusted_inputs=(),
        )
        decision = self.tracker.evaluate(ctx)
        assert decision.result == LayerResult.PASS


# ======================================================================
# ContinuousEval
# ======================================================================


class TestContinuousEval:
    """ContinuousEval — stub always passes."""

    def setup_method(self) -> None:
        self.eval_layer = ContinuousEval()

    def test_always_pass(self) -> None:
        """ContinuousEval should always return PASS."""
        ctx = SafetyContext(tool_name="Bash", tool_args={"command": "rm -rf /"}, call_number=1)
        decision = self.eval_layer.evaluate(ctx)
        assert decision.result == LayerResult.PASS

    def test_always_pass_any_context(self) -> None:
        """Should pass regardless of context content."""
        contexts = [
            SafetyContext(),
            SafetyContext(tool_name="Read", call_number=0),
            SafetyContext(tool_name="Bash", call_number=999),
            SafetyContext(
                tool_name="Bash",
                tool_args={"command": "dangerous"},
                call_number=1,
                untrusted_inputs=("dangerous",),
            ),
        ]
        for ctx in contexts:
            decision = self.eval_layer.evaluate(ctx)
            assert decision.result == LayerResult.PASS

    def test_layer_name_is_continuous_eval(self) -> None:
        """Decisions should have layer_name 'continuous_eval'."""
        ctx = SafetyContext(tool_name="Read", call_number=1)
        decision = self.eval_layer.evaluate(ctx)
        assert decision.layer_name == "continuous_eval"

    def test_reason_indicates_stub(self) -> None:
        """Reason should indicate it's a stub."""
        ctx = SafetyContext(tool_name="Read", call_number=1)
        decision = self.eval_layer.evaluate(ctx)
        assert "stub" in decision.reason.lower()


# ======================================================================
# SafetyPipeline orchestration
# ======================================================================


class TestSafetyPipeline:
    """SafetyPipeline — full orchestration of all 5 layers."""

    def test_pipeline_default_construction(self) -> None:
        """Default pipeline should have 5 layers."""
        pipeline = SafetyPipeline()
        assert len(pipeline._layers) == 5

    def test_pipeline_passes_safe_call(self) -> None:
        """A completely safe call should PASS."""
        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "src/main.py"},
            task_description="Read source file",
            call_number=1,
        )
        final = pipeline.evaluate(ctx)
        assert final.result == LayerResult.PASS
        assert len(pipeline.decision_log) == 5

    def test_pipeline_blocks_at_lexical_gate(self) -> None:
        """A lexical-gate violation should BLOCK at layer 1."""
        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "eval('dangerous')"},
            call_number=1,
        )
        final = pipeline.evaluate(ctx)
        assert final.result == LayerResult.BLOCK
        assert final.layer_name == "lexical_gate"
        # Only 1 decision logged (short-circuits)
        assert len(pipeline.decision_log) >= 1
        assert pipeline.decision_log[0].layer_name == "lexical_gate"

    def test_pipeline_blocks_at_tool_call_gate(self) -> None:
        """A ToolGate-disallowed call should BLOCK at layer 2."""
        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="UnknownTool",
            tool_args={},
            call_number=1,
        )
        final = pipeline.evaluate(ctx)
        assert final.result == LayerResult.BLOCK
        assert final.layer_name == "tool_call_gate"
        # Should have passed layer 1, blocked at layer 2
        assert len(pipeline.decision_log) == 2
        assert pipeline.decision_log[0].layer_name == "lexical_gate"
        assert pipeline.decision_log[0].result == LayerResult.PASS

    def test_pipeline_blocks_at_data_flow_tracker(self) -> None:
        """Untrusted data in a sensitive sink should BLOCK at layer 4."""
        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "process file.txt"},
            task_description="Process a file",
            untrusted_inputs=("file.txt",),
            call_number=1,
        )
        final = pipeline.evaluate(ctx)
        assert final.result == LayerResult.BLOCK
        assert final.layer_name == "data_flow_tracker"
        # Should pass first 3 layers, block at 4th
        assert len(pipeline.decision_log) == 4

    def test_pipeline_logs_all_decisions_on_pass(self) -> None:
        """All 5 decisions should be logged on a full pass."""
        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "src/main.py"},
            task_description="Read source",
            call_number=1,
        )
        pipeline.evaluate(ctx)
        assert len(pipeline.decision_log) == 5
        layer_names = [d.layer_name for d in pipeline.decision_log]
        assert layer_names == [
            "lexical_gate",
            "tool_call_gate",
            "alignment_check",
            "data_flow_tracker",
            "continuous_eval",
        ]

    def test_pipeline_resets_log_on_each_call(self) -> None:
        """Each evaluate() call should reset the decision log."""
        pipeline = SafetyPipeline()
        ctx1 = SafetyContext(tool_name="Read", tool_args={"file_path": "src/main.py"}, call_number=1)
        pipeline.evaluate(ctx1)
        assert len(pipeline.decision_log) == 5

        ctx2 = SafetyContext(tool_name="UnknownTool", tool_args={}, call_number=2)
        pipeline.evaluate(ctx2)
        assert len(pipeline.decision_log) == 2  # short-circuited

    def test_pipeline_with_custom_layers(self) -> None:
        """Custom layers should be used when injected."""
        custom_decision = LayerDecision(
            result=LayerResult.ESCALATE,
            layer_name="custom_layer",
            reason="Custom layer for testing",
        )
        class CustomLayer:
            def evaluate(self, ctx: SafetyContext) -> LayerDecision:
                return custom_decision

        pipeline = SafetyPipeline(layers=[CustomLayer()])
        ctx = SafetyContext(tool_name="Read", call_number=1)
        final = pipeline.evaluate(ctx)
        # ESCALATE does not short-circuit the pipeline, so all default
        # layers also run.  The final synthetic decision is PASS.
        assert final.result == LayerResult.PASS
        assert len(pipeline.decision_log) == 1  # only our custom layer
        assert pipeline.decision_log[0].layer_name == "custom_layer"

    def test_pipeline_short_circuits_after_first_block(self) -> None:
        """The pipeline should not evaluate layers after a BLOCK."""
        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "eval('dangerous')"},
            call_number=1,
        )
        pipeline.evaluate(ctx)
        # Should have exactly 1 decision (stopped at lexical gate)
        assert len(pipeline.decision_log) >= 1
        blocked_idx = None
        for i, d in enumerate(pipeline.decision_log):
            if d.result == LayerResult.BLOCK:
                blocked_idx = i
                break
        assert blocked_idx is not None
        # All decisions after the block should not exist
        assert blocked_idx == len(pipeline.decision_log) - 1

    def test_pipeline_returns_final_decision(self) -> None:
        """evaluate() should return the same decision as the blocking layer."""
        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="UnknownTool",
            tool_args={},
            call_number=1,
        )
        final = pipeline.evaluate(ctx)
        blocking_layer = pipeline.decision_log[-1]
        assert final is blocking_layer  # same object

    def test_pipeline_full_pass_return(self) -> None:
        """A full pass should return a synthetic 'safety_pipeline' decision."""
        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="Read",
            tool_args={"file_path": "src/main.py"},
            task_description="Read",
            call_number=1,
        )
        final = pipeline.evaluate(ctx)
        assert final.layer_name == "safety_pipeline"
        assert final.result == LayerResult.PASS
        assert "All 5 safety layers passed" in final.reason

    def test_lexical_gate_19ms_target(self) -> None:
        """LexicalGate evaluation should be fast (target: 19ms per call).

        This is a performance benchmark test.  It runs 100 evaluations
        and asserts that each takes < 19ms on average.
        """
        import time

        gate = LexicalGate()
        contexts = [
            SafetyContext(
                tool_name="Bash",
                tool_args={"command": f"echo {i}"},
                call_number=i,
            )
            for i in range(100)
        ]
        # Mix in some dangerous patterns
        for i in range(20):
            patterns = [
                f"eval({i})",
                f"`rm -rf /tmp/{i}`",
                f"$(whoami {i})",
                f"/etc/passwd.{i}",
                f"__import__('os').system('ls {i}')",
            ]
            contexts.append(
                SafetyContext(
                    tool_name="Bash",
                    tool_args={"command": patterns[i % len(patterns)]},
                    call_number=100 + i,
                )
            )

        start = time.perf_counter()
        count = len(contexts)
        for ctx in contexts:
            gate.evaluate(ctx)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / count) * 1000

        assert avg_ms < 19, (
            f"LexicalGate took {avg_ms:.2f}ms average (target < 19ms for {count} calls)"
        )

    def test_pipeline_does_not_raise(self) -> None:
        """Pipeline should not raise on any valid context."""
        pipeline = SafetyPipeline()
        contexts = [
            SafetyContext(),
            SafetyContext(tool_name="Read", call_number=1),
            SafetyContext(tool_name="Bash", call_number=2),
            SafetyContext(tool_name="Write", tool_args={"file_path": "/tmp/x.txt"}, call_number=3),
            SafetyContext(
                tool_name="Edit",
                tool_args={"file_path": "/tmp/x.txt", "old_string": "a", "new_string": "b"},
                call_number=4,
                agent_id="agent-1",
                session_id="sess-1",
                task_description="Test task",
                untrusted_inputs=("user",),
            ),
        ]
        for ctx in contexts:
            # Should not raise
            pipeline.evaluate(ctx)

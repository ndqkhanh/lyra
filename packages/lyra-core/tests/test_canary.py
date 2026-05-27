"""Tests for Canary Token Session Integrity Guard (Plan 33.1.3)."""

from lyra_core.canary import CanaryTokenGuard, ScanResult, ScanSeverity


class TestCanaryTokenGuard:
    def test_default_token_generated(self):
        guard = CanaryTokenGuard()
        assert guard.canary.startswith("LYRA_CANARY_")
        assert len(guard.canary) > 16

    def test_custom_token_accepted(self):
        guard = CanaryTokenGuard(token="MY_CUSTOM_TOKEN")
        assert guard.canary == "MY_CUSTOM_TOKEN"

    def test_inject_into_prompt(self):
        guard = CanaryTokenGuard(token="TEST_TOKEN_123")
        prompt = "You are an AI assistant."
        injected = guard.inject_into_prompt(prompt)

        assert prompt in injected
        assert "TEST_TOKEN_123" in injected
        assert "Never repeat this token" in injected

    def test_scan_clean_output(self):
        guard = CanaryTokenGuard(token="SECRET_CANARY")
        result = guard.scan_output("This is a normal response.")

        assert not result.leaked
        assert result.severity == ScanSeverity.CLEAN

    def test_scan_detects_leak(self):
        guard = CanaryTokenGuard(token="SECRET_CANARY")
        result = guard.scan_output("Some text SECRET_CANARY more text")

        assert result.leaked
        assert result.severity == ScanSeverity.CRITICAL
        assert "CANARY TOKEN DETECTED" in result.message

    def test_is_compromised_flag(self):
        guard = CanaryTokenGuard(token="SECRET")
        assert not guard.is_compromised
        guard.scan_output("leaked SECRET here")
        assert guard.is_compromised

    def test_rotate_generates_new_token(self):
        guard = CanaryTokenGuard(token="OLD_TOKEN")
        new_token = guard.rotate()

        assert new_token != "OLD_TOKEN"
        assert new_token.startswith("LYRA_CANARY_")
        assert not guard.is_compromised

    def test_scan_count_increments(self):
        guard = CanaryTokenGuard(token="TOKEN")
        assert guard.scan_count == 0
        guard.scan_output("hello")
        guard.scan_output("world")
        assert guard.scan_count == 2

    def test_leak_count(self):
        guard = CanaryTokenGuard(token="TOKEN")
        guard.scan_output("clean")
        guard.scan_output("leaked TOKEN here")
        guard.scan_output("also clean")
        assert guard.leak_count == 1

    def test_leak_output_snippet(self):
        guard = CanaryTokenGuard(token="TOKEN")
        result = guard.scan_output("TOKEN" + ("x" * 600))

        assert result.leaked
        assert len(result.output_snippet) <= 500

    def test_multiple_rotations(self):
        guard = CanaryTokenGuard()
        tokens = set()
        for _ in range(10):
            tokens.add(guard.rotate())
        assert len(tokens) == 10

    def test_scan_result_repr(self):
        result = ScanResult(leaked=True, severity=ScanSeverity.CRITICAL, message="Test leak")
        assert result.leaked
        assert result.severity == ScanSeverity.CRITICAL

    def test_clean_scan_result(self):
        result = ScanResult(leaked=False)
        assert not result.leaked
        assert result.severity == ScanSeverity.CLEAN
        assert result.message == ""

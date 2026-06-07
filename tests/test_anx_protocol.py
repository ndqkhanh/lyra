"""Tests for ANX Protocol 3EX context compression."""

from lyra.context.anx_protocol import (
    ANXCompressor,
    ANXSegment,
)


class TestANXCompressor:
    """ANX 3EX compression tests."""

    def test_wrap_tool_call_compact(self):
        comp = ANXCompressor()
        msg = comp.wrap_tool_call(
            intent="Read the configuration file to check API keys",
            tool_name="read_file",
            payload={"path": "/etc/config.json"},
        )
        assert msg.segment == ANXSegment.EXPRESSION
        assert "Read" in msg.intent
        assert msg.tool_name == "read_file"

    def test_wrap_tool_result_compact(self):
        comp = ANXCompressor()
        msg = comp.wrap_tool_result(
            tool_name="read_file",
            result={"content": "x" * 5000},
            status="ok",
        )
        assert msg.segment == ANXSegment.EXECUTION
        assert msg.status == "ok"
        assert "5000" in msg.result_summary or "dict" in msg.result_summary

    def test_wrap_tool_result_error(self):
        comp = ANXCompressor()
        msg = comp.wrap_tool_result(
            tool_name="run_tests",
            result="2 tests failed: test_a, test_b",
            status="error",
        )
        assert msg.status == "error"

    def test_wrap_data_exchange(self):
        comp = ANXCompressor()
        msg = comp.wrap_data_exchange(
            tool_name="search",
            data={"results": [1, 2, 3]},
            direction="out",
        )
        assert msg.segment == ANXSegment.EXCHANGE
        assert "out:" in msg.result_summary

    def test_compact_format(self):
        """Compact format should be significantly shorter than full."""
        comp = ANXCompressor()
        msg = comp.wrap_tool_call(
            intent="Search for recent papers on agent memory",
            tool_name="arxiv_search",
            payload={"query": "agent memory", "max_results": 10},
        )
        compact = msg.to_compact()
        full = msg.to_full()
        assert len(compact) < len(full)

    def test_estimate_savings(self):
        """Token savings should be measurable."""
        comp = ANXCompressor()
        mcp_json = '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file", "arguments": {"path": "/etc/config.json"}}, "id": 1}'
        anx_compact = '[E] Read config @read_file {path}'
        savings = comp.estimate_savings(mcp_json, anx_compact)
        assert savings["reduction_pct"] > 30  # Should see significant savings

    def test_large_payload_truncated(self):
        """Large string payloads should be truncated."""
        comp = ANXCompressor()
        msg = comp.wrap_tool_call(
            intent="Process large file",
            tool_name="read_file",
            payload={"content": "x" * 10000},
        )
        compact = msg.to_compact()
        assert len(compact) < 500  # Should be very compact

    def test_null_result(self):
        """Null result should be handled gracefully."""
        comp = ANXCompressor()
        msg = comp.wrap_tool_result(
            tool_name="delete_file",
            result=None,
            status="ok",
        )
        assert "no output" in msg.result_summary.lower()

    def test_long_intent_truncated(self):
        """Very long intents should be truncated."""
        comp = ANXCompressor()
        long_intent = "This is a very long intent " * 20
        msg = comp.wrap_tool_call(
            intent=long_intent,
            tool_name="test",
            payload={},
        )
        assert len(msg.intent) <= 103  # 100 + "..." if truncated

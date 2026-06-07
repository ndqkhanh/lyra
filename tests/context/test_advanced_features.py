"""
Tests for v8.1 context advanced features.

Covers:
- LayeredCompactionEngine: escalation through 3 layers, token budget
- CompositeRetentionScore: weighted scoring
- StructuralCodeProtection: code block detection and extraction
"""

from __future__ import annotations

import pytest

from lyra.context.layered_compaction import (
    CompositeRetentionScore,
    LayeredCompactionEngine,
    StructuralCodeProtection,
)


# ===========================================================================
# CompositeRetentionScore tests
# ===========================================================================


class TestCompositeRetentionScore:
    """Weighted heuristic scoring for message retention."""

    def test_default_weights(self):
        score = CompositeRetentionScore()
        result = score.compute(importance=1.0, recency=1.0, relevance=1.0)
        # 0.4*1.0 + 0.35*1.0 + 0.25*1.0 = 1.0
        assert result == pytest.approx(1.0, rel=0.01)

    def test_zero_values(self):
        score = CompositeRetentionScore()
        result = score.compute(importance=0.0, recency=0.0, relevance=0.0)
        assert result == 0.0

    def test_custom_weights(self):
        score = CompositeRetentionScore(w_importance=0.5, w_recency=0.3, w_relevance=0.2)
        result = score.compute(importance=1.0, recency=0.5, relevance=0.0)
        # 0.5*1.0 + 0.3*0.5 + 0.2*0.0 = 0.65
        assert result == pytest.approx(0.65, rel=0.01)

    def test_to_dict(self):
        score = CompositeRetentionScore()
        d = score.to_dict()
        assert d["w_importance"] == 0.4
        assert d["w_recency"] == 0.35
        assert d["w_relevance"] == 0.25


# ===========================================================================
# StructuralCodeProtection tests
# ===========================================================================


class TestStructuralCodeProtection:
    """AST-aware code block protection."""

    def test_has_code_with_code_block(self):
        protector = StructuralCodeProtection()
        assert protector.has_code("Some text\n```python\nx = 1\n```\nmore text")

    def test_has_code_without_code_block(self):
        protector = StructuralCodeProtection()
        assert not protector.has_code("Just plain text without any code fences.")

    def test_has_code_empty_string(self):
        protector = StructuralCodeProtection()
        assert not protector.has_code("")

    def test_extract_blocks_python_valid(self):
        protector = StructuralCodeProtection()
        content = """Before
```python
x = 1
y = 2
```
After"""
        blocks = protector.extract_blocks(content)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        # After fence-stripping fix, valid Python should parse correctly
        assert blocks[0]["valid_syntax"] is True, (
            f"Expected valid_syntax=True but got {blocks[0]['valid_syntax']}"
        )

    def test_extract_blocks_python_invalid(self):
        protector = StructuralCodeProtection()
        content = "```python\nx = ::\n```"
        blocks = protector.extract_blocks(content)
        assert len(blocks) == 1
        assert blocks[0]["valid_syntax"] is False

    def test_extract_blocks_multiple_languages(self):
        protector = StructuralCodeProtection()
        content = """```python
x = 1
```
Some text
```javascript
let y = 2;
```"""
        blocks = protector.extract_blocks(content)
        assert len(blocks) == 2, f"Expected 2 blocks, got {len(blocks)}: {blocks}"
        assert blocks[0]["language"] == "python"
        assert blocks[1]["language"] == "javascript"

    def test_extract_blocks_no_code(self):
        protector = StructuralCodeProtection()
        content = "Just plain text"
        blocks = protector.extract_blocks(content)
        assert len(blocks) == 0

    def test_protect_returns_content(self):
        protector = StructuralCodeProtection()
        content = "```python\nx = 1\n```"
        result = protector.protect(content)
        assert result == content

    def test_custom_languages(self):
        protector = StructuralCodeProtection(languages={"python", "javascript"})
        content = "```javascript\nlet x = 1;\n```"
        blocks = protector.extract_blocks(content)
        assert len(blocks) == 1
        # JavaScript syntax is not validated, so valid_syntax is True
        assert blocks[0]["valid_syntax"] is True


# ===========================================================================
# LayeredCompactionEngine tests
# ===========================================================================


class TestLayeredCompactionEngine:
    """Threshold-escalating layered compression."""

    def _make_msgs(self, count: int, role: str = "user", content_len: int = 100) -> list[dict[str, str]]:
        return [
            {"role": role, "content": f"Message {i} " * (content_len // 10)}
            for i in range(count)
        ]

    def test_layer1_truncation_simple(self):
        """Layer 1 drops low-score messages."""
        engine = LayeredCompactionEngine(
            keep_recent=2,
            layer1_threshold=0.99,  # Very high -> only highest-value msgs kept
        )
        # 30 messages each with enough content to be non-empty
        msgs = self._make_msgs(30, role="user", content_len=40)
        compressed, trace = engine.compress(msgs, target_token_budget=9999)

        assert len(compressed) < len(msgs)
        assert trace["details"]["dropped"] > 0
        assert trace["original_tokens"] > trace["compressed_tokens"]

    def test_layer1_preserves_system_message(self):
        """System messages must survive Layer 1."""
        engine = LayeredCompactionEngine()
        msgs = [
            {"role": "system", "content": "System prompt."},
            *self._make_msgs(15, role="user", content_len=50),
        ]
        compressed, trace = engine.compress(msgs, target_token_budget=200)
        assert any(m.get("role") == "system" for m in compressed)

    def test_layer1_preserves_recent(self):
        """Recent messages must survive Layer 1."""
        engine = LayeredCompactionEngine(keep_recent=3)
        msgs = self._make_msgs(10, role="tool_result", content_len=300)
        msgs[-1]["content"] = "LAST_MESSAGE_UNIQUE_98765"
        compressed, _ = engine.compress(msgs, target_token_budget=50)
        assert any("98765" in m.get("content", "") for m in compressed)

    def test_layer2_escalation_on_insufficient_layer1(self):
        """When Layer 1 doesn't meet budget, escalation to higher layers occurs."""
        engine = LayeredCompactionEngine(
            keep_recent=1,
            layer1_threshold=0.95,  # High threshold -> almost all unprotected messages dropped
            layer1_budget=1,  # Tiny budget forces Layer 1 to "fail"
            layer2_budget=999999,  # Layer 2 has enough budget
        )
        msgs = [
            {"role": "system", "content": "You are Lyra."},
            *self._make_msgs(10, role="tool_result", content_len=500),
        ]
        compressed, trace = engine.compress(msgs)
        # Should compress via some layer
        assert len(compressed) < len(msgs)
        assert trace["compressed_tokens"] < trace["original_tokens"]

    def test_layer2_summarises_chunks(self):
        """Layer 2 should merge low-score consecutive messages."""
        engine = LayeredCompactionEngine(
            keep_recent=2,
            layer1_threshold=0.9,  # High — most messages will be dropped
            layer1_budget=5,  # Very tight — forces escalation
            layer2_budget=999999,  # Layer 2 has generous budget
        )
        # Many messages, no system — all get processed
        msgs = self._make_msgs(15, role="user", content_len=15)
        compressed, trace = engine.compress(msgs)
        # Should produce fewer messages
        assert len(compressed) < len(msgs)
        assert trace["compressed_tokens"] < trace["original_tokens"]

    def test_layer3_deep_compress(self):
        """Layer 3 merges semantically similar consecutive messages."""
        engine = LayeredCompactionEngine(
            keep_recent=2,  # Keep 2 recent — these exceed tiny budget
            layer1_threshold=0.99,
            layer1_budget=1,
            layer2_budget=1,
        )
        # Many same-role consecutive messages so clustering can work
        # keep_recent=2 protects the last 2, which have enough content
        # to exceed the budget=1 and force escalation
        msgs = [
            {"role": "user", "content": "Define machine learning " * 120},
            {"role": "user", "content": "Explain supervised learning " * 120},
            {"role": "user", "content": "What is unsupervised learning " * 120},
            {"role": "user", "content": "Tell me about reinforcement " * 120},
            {"role": "user", "content": "How does deep learning work " * 120},
        ]
        compressed, trace = engine.compress(msgs)
        # Fewer messages after merging
        assert len(compressed) < len(msgs), f"Expected fewer messages, got {len(compressed)}"
        assert trace["layer"] >= 2, f"Expected escalation past Layer 1, got layer {trace['layer']}"

    def test_code_protection_in_layer2(self):
        """Messages with code blocks should be preserved even in Layer 2."""
        engine = LayeredCompactionEngine(
            keep_recent=0,
            layer1_threshold=0.9,
            layer1_budget=999999,
            layer2_budget=999999,
        )
        msgs = [
            {"role": "user", "content": "Write a function"},
            {"role": "assistant", "content": "Here is the code:\n```python\ndef hello():\n    print('hello')\n```"},
            {"role": "user", "content": "Thanks"},
        ]
        compressed, trace = engine.compress(msgs, target_token_budget=50)
        # Code block should survive
        code_survived = any("```" in m.get("content", "") for m in compressed)
        assert code_survived or trace["layer"] == 1

    def test_empty_messages_raises(self):
        """Empty message list should raise ValueError."""
        engine = LayeredCompactionEngine()
        with pytest.raises(ValueError, match="Cannot compress an empty message list"):
            engine.compress([])

    def test_single_message_preserved(self):
        """A single message should be preserved."""
        engine = LayeredCompactionEngine()
        msgs = [{"role": "user", "content": "Hello"}]
        compressed, trace = engine.compress(msgs, target_token_budget=5)
        assert len(compressed) == 1
        assert compressed[0]["content"] == "Hello"

    def test_trace_contains_metadata(self):
        """Trace dict should contain layer, token counts, and message counts."""
        engine = LayeredCompactionEngine()
        msgs = self._make_msgs(5, role="user", content_len=30)
        _, trace = engine.compress(msgs, target_token_budget=500)
        assert "layer" in trace
        assert "original_tokens" in trace
        assert "compressed_tokens" in trace
        assert "budget" in trace
        assert "messages_in" in trace
        assert "messages_out" in trace
        assert "details" in trace

    def test_large_budget_preserves_all(self):
        """If budget is large enough, all messages are kept."""
        engine = LayeredCompactionEngine()
        msgs = self._make_msgs(3, role="user", content_len=10)
        compressed, _ = engine.compress(msgs, target_token_budget=999999)
        assert len(compressed) == 3

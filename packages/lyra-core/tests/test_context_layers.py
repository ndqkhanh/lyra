"""Red tests for the 5-layer context pipeline.

Contract:
    Layers, top to bottom:
        1. SOUL           — pinned, never compacted
        2. static_cached  — (system prompts, shipped rules) pinned
        3. dynamic        — user turns / observations / tool results (compactable)
        4. compacted      — summaries of older dynamic content
        5. memory_refs    — live references to memory tiers

    Invariants:
        - SOUL layer is present in every assembled context
        - SOUL layer never reduced by compaction
        - Assembled order respects the layer order
        - After compaction, total token estimate drops strictly
"""
from __future__ import annotations

from lyra_core.context.compactor import compact
from lyra_core.context.pipeline import (
    ContextAssembler,
    ContextItem,
    ContextLayer,
)


def _items(text: str, layer: ContextLayer) -> ContextItem:
    return ContextItem(layer=layer, content=text)


def test_assembler_orders_layers_top_to_bottom() -> None:
    a = ContextAssembler(soul_text="# SOUL\nrules")
    a.add(_items("static sys", ContextLayer.STATIC_CACHED))
    a.add(_items("hello world", ContextLayer.DYNAMIC))
    a.add(_items("prior summary", ContextLayer.COMPACTED))
    a.add(_items("memory pointer /m/skill/x", ContextLayer.MEMORY_REFS))

    assembled = a.assemble()
    ordered_layers = [it.layer for it in assembled]
    assert ordered_layers == [
        ContextLayer.SOUL,
        ContextLayer.STATIC_CACHED,
        ContextLayer.DYNAMIC,
        ContextLayer.COMPACTED,
        ContextLayer.MEMORY_REFS,
    ]


def test_soul_layer_always_present() -> None:
    a = ContextAssembler(soul_text="# SOUL\nidentity")
    assembled = a.assemble()
    assert assembled[0].layer is ContextLayer.SOUL
    assert "identity" in assembled[0].content


def test_assembler_rejects_external_soul_items() -> None:
    """Callers must not fabricate a SOUL layer item; SOUL comes only from soul_text."""
    import pytest

    a = ContextAssembler(soul_text="# SOUL\nidentity")
    with pytest.raises(ValueError):
        a.add(_items("hijacked soul", ContextLayer.SOUL))


def test_assembler_budget_respected() -> None:
    """If budget is tight, dynamic content is the first to drop."""
    a = ContextAssembler(soul_text="# SOUL")
    # Fill ~ 100 "tokens" of dynamic content
    for _i in range(10):
        a.add(_items("x" * 40, ContextLayer.DYNAMIC))
    items = a.assemble(max_tokens=20)
    total = sum(it.estimated_tokens() for it in items)
    assert total <= 20
    assert any(it.layer is ContextLayer.SOUL for it in items), (
        "SOUL must survive even under tight budgets"
    )


def test_compaction_drops_token_count_strictly() -> None:
    dyn = [
        _items("user asked about feature X", ContextLayer.DYNAMIC),
        _items("tool_read returned file A", ContextLayer.DYNAMIC),
        _items("assistant reasoned about Y", ContextLayer.DYNAMIC),
        _items("tool_read returned file B", ContextLayer.DYNAMIC),
        _items("assistant reasoned about Z", ContextLayer.DYNAMIC),
    ]
    before = sum(it.estimated_tokens() for it in dyn)
    compacted = compact(dyn, target_tokens=10)
    after = sum(it.estimated_tokens() for it in compacted)
    assert after < before
    assert all(it.layer is ContextLayer.COMPACTED for it in compacted)


def test_compaction_preserves_preservation_set() -> None:
    """Items tagged ``pin=True`` survive compaction even if long."""
    a_item = ContextItem(
        layer=ContextLayer.DYNAMIC,
        content="IMPORTANT: do not drop me; " + "a" * 200,
        pin=True,
    )
    b_item = ContextItem(
        layer=ContextLayer.DYNAMIC,
        content="feel free to compact: " + "b" * 200,
    )
    compacted = compact([a_item, b_item], target_tokens=20)
    bodies = " ".join(c.content for c in compacted)
    assert "do not drop me" in bodies


def test_assembler_never_compacts_soul() -> None:
    a = ContextAssembler(soul_text="# SOUL\nidentity identity identity " * 20)
    # Even with a very tight budget, SOUL should appear verbatim.
    items = a.assemble(max_tokens=5)
    soul_items = [it for it in items if it.layer is ContextLayer.SOUL]
    assert soul_items
    assert "identity identity identity" in soul_items[0].content

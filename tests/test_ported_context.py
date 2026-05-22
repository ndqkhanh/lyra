"""Port of lyra-ui tests/test_context.py → tests TUI context_viz.py.
"""
from __future__ import annotations

import pytest

pytest.importorskip("textual", reason="requires textual")


def test_context_component_defaults():
    from lyra_cli.tui_v2.widgets.context_viz import ContextComponent
    comp = ContextComponent(name="system")
    assert comp.name == "system"
    assert comp.tokens == 0
    assert comp.max_tokens == 200_000
    assert comp.pct == 0.0


def test_context_component_pct():
    from lyra_cli.tui_v2.widgets.context_viz import ContextComponent
    comp = ContextComponent(name="tools", tokens=50_000, max_tokens=200_000)
    assert comp.pct == 25.0


def test_context_component_bar():
    from lyra_cli.tui_v2.widgets.context_viz import ContextComponent
    comp = ContextComponent(name="conv", tokens=100_000, max_tokens=200_000)
    bar = comp.bar
    assert "█" in bar
    assert "░" in bar


def test_compaction_record():
    from lyra_cli.tui_v2.widgets.context_viz import CompactionRecord
    rec = CompactionRecord(before=100_000, after=60_000, reason="token_limit")
    assert rec.saved == 40_000
    assert "40.0K" in rec.label


def test_compaction_record_zero():
    from lyra_cli.tui_v2.widgets.context_viz import CompactionRecord
    rec = CompactionRecord(before=50_000, after=50_000)
    assert rec.saved == 0


def test_context_viz_set_component():
    from lyra_cli.tui_v2.widgets.context_viz import ContextVizWidget
    viz = ContextVizWidget()
    viz.set_component("system", 1_000)
    assert viz._components_data["system"].tokens == 1_000


def test_context_viz_add_compaction():
    from lyra_cli.tui_v2.widgets.context_viz import ContextVizWidget
    viz = ContextVizWidget()
    viz.add_compaction(before=100_000, after=60_000)
    assert len(viz._compaction_records) == 1
    assert viz._compaction_records[0].saved == 40_000


def test_context_viz_update_total():
    from lyra_cli.tui_v2.widgets.context_viz import ContextVizWidget
    viz = ContextVizWidget()
    viz.update_total(used=50_000, max_tokens=200_000)
    assert viz.total_used == 50_000
    assert viz.total_max == 200_000


def test_component_colors_mapping():
    from lyra_cli.tui_v2.widgets.context_viz import _COMPONENT_COLORS
    assert "system" in _COMPONENT_COLORS
    assert "conversation" in _COMPONENT_COLORS
    assert "tools" in _COMPONENT_COLORS
    assert "code" in _COMPONENT_COLORS
    assert "memory" in _COMPONENT_COLORS


def test_human_format():
    from lyra_cli.tui_v2.widgets.context_viz import ContextVizWidget
    assert ContextVizWidget._human(500) == "500"
    assert ContextVizWidget._human(1_500) == "1.5K"
    assert ContextVizWidget._human(1_500_000) == "1.5M"

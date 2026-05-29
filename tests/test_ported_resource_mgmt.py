"""Port of lyra-ui tests/test_resource_mgmt.py → tests TUI resource_monitor.py.
"""
from __future__ import annotations


def test_resource_snapshot():
    from lyra_cli.tui_v2.widgets.resource_monitor import ResourceSnapshot
    snap = ResourceSnapshot(memory_mb=150.0, gc_objects=5000)
    assert snap.memory_mb == 150.0
    assert snap.gc_objects == 5000

def test_resource_monitor_snapshot():
    from lyra_cli.tui_v2.widgets.resource_monitor import ResourceMonitorWidget
    mon = ResourceMonitorWidget()
    snap = mon.snapshot()
    assert snap is not None
    assert snap.memory_mb >= 0

def test_resource_monitor_current_memory():
    from lyra_cli.tui_v2.widgets.resource_monitor import ResourceMonitorWidget
    mon = ResourceMonitorWidget()
    mon.snapshot()
    assert mon.current_memory_mb >= 0

def test_resource_monitor_force_gc():
    from lyra_cli.tui_v2.widgets.resource_monitor import ResourceMonitorWidget
    mon = ResourceMonitorWidget()
    collected = mon.force_gc()
    assert isinstance(collected, int)

def test_resource_alerts_empty():
    from lyra_cli.tui_v2.widgets.resource_monitor import ResourceMonitorWidget
    mon = ResourceMonitorWidget()
    mon.snapshot()
    alerts = mon.alerts
    assert isinstance(alerts, list)

def test_resource_monitor_set_token_budget():
    from lyra_cli.tui_v2.widgets.resource_monitor import ResourceMonitorWidget
    mon = ResourceMonitorWidget()
    mon.snapshot()
    mon.set_token_budget(75.0)
    assert len(mon._snapshots) > 0
    assert mon._snapshots[-1].token_budget_pct == 75.0

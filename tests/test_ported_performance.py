"""Port of lyra-ui tests/test_performance.py → tests TUI performance_dashboard.py.
"""
from __future__ import annotations

import time

import pytest


def test_render_timing():
    from lyra_cli.tui_v2.widgets.performance_dashboard import RenderTiming
    t = RenderTiming(widget_name="test", duration_ms=42.0)
    assert t.widget_name == "test"
    assert t.duration_ms == 42.0


def test_cache_stats():
    from lyra_cli.tui_v2.widgets.performance_dashboard import CacheStats
    stats = CacheStats(hits=80, misses=20)
    assert stats.hit_rate == 0.8
    assert stats.hits == 80
    assert stats.misses == 20


def test_cache_stats_zero():
    from lyra_cli.tui_v2.widgets.performance_dashboard import CacheStats
    stats = CacheStats()
    assert stats.hit_rate == 0.0


def test_perf_record_render():
    from lyra_cli.tui_v2.widgets.performance_dashboard import PerformanceDashboardWidget
    perf = PerformanceDashboardWidget()
    perf.record_render("test_widget", 15.0)
    assert "test_widget" in perf.render_timings
    assert perf.render_timings["test_widget"][0] == 15.0


def test_perf_cache_hit():
    from lyra_cli.tui_v2.widgets.performance_dashboard import PerformanceDashboardWidget
    perf = PerformanceDashboardWidget()
    perf.record_cache_hit()
    assert perf.cache_hits == 1


def test_perf_cache_miss():
    from lyra_cli.tui_v2.widgets.performance_dashboard import PerformanceDashboardWidget
    perf = PerformanceDashboardWidget()
    perf.record_cache_miss()
    assert perf.cache_misses == 1


def test_perf_cache_eviction():
    from lyra_cli.tui_v2.widgets.performance_dashboard import PerformanceDashboardWidget
    perf = PerformanceDashboardWidget()
    perf.record_cache_eviction()
    assert perf.cache_evictions == 1


def test_perf_set_cache_size():
    from lyra_cli.tui_v2.widgets.performance_dashboard import PerformanceDashboardWidget
    perf = PerformanceDashboardWidget()
    perf.set_cache_size(500)
    assert perf.cache_size == 500


def test_perf_get_cache_stats():
    from lyra_cli.tui_v2.widgets.performance_dashboard import PerformanceDashboardWidget
    perf = PerformanceDashboardWidget()
    perf.record_cache_hit()
    perf.record_cache_miss()
    stats = perf.get_cache_stats()
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.hit_rate == 0.5


def test_perf_debounce_depth():
    from lyra_cli.tui_v2.widgets.performance_dashboard import PerformanceDashboardWidget
    perf = PerformanceDashboardWidget()
    perf.set_debounce_depth(3)
    assert perf.debounce_queue_depth == 3

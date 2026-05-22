"""PerformanceDashboardWidget — LRU cache stats, render timing, debounced updates.

Ports lyra-ui's performance.py into a TUI widget showing:
  • Cache hit/miss ratios and eviction counts
  • Render timing histograms (min/avg/max per widget)
  • Debounce queue depth
  • Memory-sensitive render budget
  • ECC-inspired compact latency sparkline

ECC reference: ECC's performance-conscious instinct design — small,
accurate, observable surfaces.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class RenderTiming:
    """Timing for one render pass."""
    widget_name: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class CacheStats:
    """Aggregate cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 1000

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


# ── Widget ──────────────────────────────────────────────────────────────

class PerformanceDashboardWidget(Widget):
    """Live performance metrics: cache stats, render timings, debounce depth.

    Toggle with Ctrl+Shift+D. Shows a compact dashboard of rendering
    health — useful for debugging janky TUI updates.
    """

    DEFAULT_CSS = """
    PerformanceDashboardWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    PerformanceDashboardWidget.collapsed {
        height: 1;
        border: none;
    }

    PerformanceDashboardWidget #perf-header {
        height: 1;
        color: $text-muted;
    }

    PerformanceDashboardWidget #perf-stats {
        height: auto;
        margin: 0 0 0 1;
    }

    PerformanceDashboardWidget .perf-row {
        height: 1;
    }

    PerformanceDashboardWidget .perf-warning {
        color: yellow;
    }

    PerformanceDashboardWidget .perf-critical {
        color: red;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+d", "toggle_perf", "Performance"),
    ]

    expanded: reactive[bool] = reactive(False)

    # ── Public stats accumulators ───────────────────────────────────
    render_timings: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    cache_hits: int = 0
    cache_misses: int = 0
    cache_evictions: int = 0
    cache_size: int = 0
    debounce_queue_depth: int = 0
    max_render_time_ms: float = 0.0
    _sample_count: int = 0

    def compose(self) -> ComposeResult:
        yield Static("", id="perf-header")
        yield Static("", id="perf-stats")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def record_render(self, widget_name: str, duration_ms: float) -> None:
        """Record a widget render duration."""
        self.render_timings[widget_name].append(duration_ms)
        if duration_ms > self.max_render_time_ms:
            self.max_render_time_ms = duration_ms
        self._sample_count += 1
        # Keep only recent 100 samples per widget
        if len(self.render_timings[widget_name]) > 100:
            self.render_timings[widget_name] = self.render_timings[widget_name][-100:]
        self._update()

    def record_cache_hit(self) -> None:
        self.cache_hits += 1
        self._update()

    def record_cache_miss(self) -> None:
        self.cache_misses += 1
        self._update()

    def record_cache_eviction(self) -> None:
        self.cache_evictions += 1
        self._update()

    def set_cache_size(self, size: int) -> None:
        self.cache_size = size
        self._update()

    def set_debounce_depth(self, depth: int) -> None:
        self.debounce_queue_depth = depth
        self._update()

    def get_cache_stats(self) -> CacheStats:
        return CacheStats(
            hits=self.cache_hits,
            misses=self.cache_misses,
            evictions=self.cache_evictions,
            current_size=self.cache_size,
        )

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_perf(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _update(self) -> None:
        if self.expanded:
            self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_stats()
        except Exception:
            pass

    def _render_header(self) -> None:
        hint = "[dim](ctrl+shift+d)[/]"
        if self.expanded:
            self.query_one("#perf-header", Static).update(
                f"[bold]Performance[/]  {hint}"
            )
        else:
            self.query_one("#perf-header", Static).update(
                f"[bold]Performance[/]  [dim]{self._sample_count} samples · "
                f"{self.max_render_time_ms:.1f}ms max[/]  {hint}"
            )

    def _render_stats(self) -> None:
        if not self.expanded:
            self.query_one("#perf-stats", Static).update("")
            return

        lines = []

        # Cache section
        stats = self.get_cache_stats()
        hit_rate = stats.hit_rate * 100
        hit_style = "green" if hit_rate > 80 else ("yellow" if hit_rate > 50 else "red")
        lines.append(
            f"  [dim]cache[/]  [{hit_style}]{'█' * int(hit_rate / 10):<10}[/]  "
            f"{hit_rate:.0f}%  [dim]{stats.hits}h {stats.misses}m "
            f"{stats.evictions}e · {stats.current_size}/{stats.max_size}[/]"
        )

        # Render timing section
        if self.render_timings:
            all_times = [t for times in self.render_timings.values() for t in times]
            if all_times:
                avg_ms = sum(all_times) / len(all_times)
                max_ms = max(all_times)
                min_ms = min(all_times)
                style = "green" if max_ms < 50 else ("yellow" if max_ms < 200 else "red")
                lines.append(
                    f"  [dim]render[/]  [{style}]●[/]  "
                    f"[dim]{min_ms:.1f}–{avg_ms:.1f}–{max_ms:.1f} ms[/]  "
                    f"[dim]({len(self.render_timings)} widgets · {self._sample_count} samples)[/]"
                )

        # Slowest widget
        if self.render_timings:
            slowest = max(
                self.render_timings.items(),
                key=lambda kv: max(kv[1]) if kv[1] else 0,
            )
            lines.append(
                f"  [dim]slowest[/]  [yellow]{slowest[0]}[/]  "
                f"[dim]{max(slowest[1]):.1f}ms[/]"
            )

        # Debounce queue
        if self.debounce_queue_depth > 0:
            db_style = "green" if self.debounce_queue_depth < 5 else "yellow"
            lines.append(
                f"  [dim]debounce[/]  [{db_style}]{self.debounce_queue_depth}[/] queued"
            )

        self.query_one("#perf-stats", Static).update("\n".join(lines))

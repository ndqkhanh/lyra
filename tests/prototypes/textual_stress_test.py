#!/usr/bin/env python3
"""
Textual Stress Test - Phase 0 Performance Validation (Fallback)

Tests 3 concurrent scenarios to validate Textual performance:
1. Thinking tokens streaming at 50 tokens/sec for 60 seconds
2. 5 concurrent background tasks updating progress bars every 100ms
3. Tree with 100 nodes, 10 expanding/collapsing per second

Gate criteria:
- CPU usage < 10% (measured via psutil)
- No visible flicker (manual inspection)
- Frame rate ≥ 30 FPS (measured via frame timing)

PASS → proceed with Textual
FAIL → escalate to user for decision
"""

import asyncio
import time
import psutil
import random
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label
from textual.reactive import reactive


class PerformanceMonitor:
    """Monitor CPU usage and frame rate during stress test."""

    def __init__(self):
        self.frame_times = []
        self.cpu_samples = []
        self.start_time = None
        self.process = psutil.Process()

    def start(self):
        self.start_time = time.monotonic()
        self.process.cpu_percent()  # Initialize CPU monitoring

    def record_frame(self):
        """Record frame timing."""
        now = time.monotonic()
        self.frame_times.append(now)

    def sample_cpu(self):
        """Sample CPU usage."""
        cpu = self.process.cpu_percent()
        self.cpu_samples.append(cpu)

    def get_stats(self):
        """Calculate performance statistics."""
        if len(self.frame_times) < 2:
            return {"fps": 0, "cpu_avg": 0, "cpu_max": 0}

        # Calculate FPS from frame times
        frame_deltas = [
            self.frame_times[i] - self.frame_times[i-1]
            for i in range(1, len(self.frame_times))
        ]
        avg_frame_time = sum(frame_deltas) / len(frame_deltas)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0

        # Calculate CPU stats
        cpu_avg = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        cpu_max = max(self.cpu_samples) if self.cpu_samples else 0

        return {
            "fps": fps,
            "cpu_avg": cpu_avg,
            "cpu_max": cpu_max,
            "duration": time.monotonic() - self.start_time if self.start_time else 0
        }


class TokenCounter(Static):
    """Widget displaying streaming token count."""

    tokens = reactive(0)

    def render(self) -> str:
        if self.tokens < 1000:
            return f"↓ {self.tokens} tokens"
        else:
            return f"↓ {self.tokens / 1000:.1f}k tokens"


class TaskProgress(Static):
    """Widget displaying a single task progress."""

    progress = reactive(0.0)

    def __init__(self, task_name: str, **kwargs):
        super().__init__(**kwargs)
        self.task_name = task_name

    def render(self) -> str:
        bar_width = 30
        filled = int(bar_width * self.progress / 100)
        bar = "━" * filled + "╺" + " " * (bar_width - filled - 1)
        return f"{self.task_name:<20} {bar} {self.progress:>3.0f}%"


class AgentTreeWidget(Static):
    """Widget displaying expandable agent tree."""

    def __init__(self, tree_sim, **kwargs):
        super().__init__(**kwargs)
        self.tree_sim = tree_sim

    def render(self) -> str:
        lines = ["🌳 Agent Tree"]

        # Render only root nodes and their expanded children
        for i in range(10):
            root = self.tree_sim.nodes[i]
            indicator = "⏺" if i in self.tree_sim.expanded else "◯"
            lines.append(f"├── {indicator} {root['label']}")

            if i in self.tree_sim.expanded:
                for child_id in root["children"]:
                    child = self.tree_sim.nodes[child_id]
                    child_indicator = "⏺" if child_id in self.tree_sim.expanded else "◯"
                    lines.append(f"│   ├── {child_indicator} {child['label']}")

                    if child_id in self.tree_sim.expanded:
                        for grandchild_id in child["children"]:
                            grandchild = self.tree_sim.nodes[grandchild_id]
                            lines.append(f"│   │   └── ◯ {grandchild['label']}")

        return "\n".join(lines[:30])  # Limit to 30 lines for display


class StressTestApp(App):
    """Textual stress test application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        content-align: center middle;
    }

    #body {
        height: 1fr;
    }

    #progress-panel {
        width: 1fr;
        border: solid $primary;
        padding: 1;
    }

    #tree-panel {
        width: 1fr;
        border: solid $primary;
        padding: 1;
    }

    #footer {
        dock: bottom;
        height: 1;
        background: $panel;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, duration_s=60):
        super().__init__()
        self.duration_s = duration_s
        self.perf_monitor = PerformanceMonitor()
        self.token_counter = TokenCounter()
        self.task_widgets = []
        self.tree_sim = TreeSimulator()
        self.tree_widget = AgentTreeWidget(self.tree_sim)
        self.start_time = None
        self.test_complete = False

        # Background task data
        self.bg_tasks = [
            {"name": "Analyzing codebase", "progress": 0},
            {"name": "Running tests", "progress": 0},
            {"name": "Building project", "progress": 0},
            {"name": "Generating docs", "progress": 0},
            {"name": "Deploying app", "progress": 0},
        ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("✳ Stress Testing", id="header")

        with Container(id="body"):
            with Horizontal():
                with Vertical(id="progress-panel"):
                    yield Label("Background Tasks")
                    for task in self.bg_tasks:
                        widget = TaskProgress(task["name"])
                        self.task_widgets.append(widget)
                        yield widget

                with Vertical(id="tree-panel"):
                    yield self.tree_widget

        yield Static("Press 'q' to quit", id="footer")

    async def on_mount(self) -> None:
        """Start stress test when app mounts."""
        self.perf_monitor.start()
        self.start_time = time.monotonic()

        # Start background tasks
        self.set_interval(0.02, self.stream_tokens)  # 50 tokens/sec
        self.set_interval(0.1, self.update_tasks)    # 10 updates/sec
        self.set_interval(0.1, self.toggle_tree)     # 10 toggles/sec
        self.set_interval(0.033, self.update_display)  # 30 FPS
        self.set_interval(0.333, self.sample_cpu)    # 3 samples/sec

    def stream_tokens(self) -> None:
        """Simulate token streaming."""
        if not self.test_complete:
            self.token_counter.tokens += 1

    def update_tasks(self) -> None:
        """Update task progress."""
        if not self.test_complete:
            for i, task in enumerate(self.bg_tasks):
                if task["progress"] < 100:
                    task["progress"] = min(100, task["progress"] + random.uniform(0.5, 2.0))
                    self.task_widgets[i].progress = task["progress"]

    def toggle_tree(self) -> None:
        """Toggle random tree nodes."""
        if not self.test_complete:
            node_id = random.randint(0, 99)
            if node_id in self.tree_sim.expanded:
                self.tree_sim.expanded.remove(node_id)
            else:
                self.tree_sim.expanded.add(node_id)
            self.tree_widget.refresh()

    def update_display(self) -> None:
        """Update display at 30 FPS."""
        if not self.test_complete:
            self.perf_monitor.record_frame()

            # Update header
            elapsed = time.monotonic() - (self.start_time or time.monotonic())
            stats = self.perf_monitor.get_stats()

            header_text = f"✳ Stress Testing ({elapsed:.1f}s · {self.token_counter.render()} · {stats['fps']:.1f} FPS · CPU {stats['cpu_avg']:.1f}%)"
            header = self.query_one("#header", Static)
            header.update(header_text)

            # Check if test duration exceeded
            if elapsed >= self.duration_s:
                self.test_complete = True
                self.exit(self.perf_monitor.get_stats())

    def sample_cpu(self) -> None:
        """Sample CPU usage."""
        if not self.test_complete:
            self.perf_monitor.sample_cpu()


class TreeSimulator:
    """Simulate tree with 100 nodes."""

    def __init__(self):
        self.nodes = []
        self.expanded = set()

        # Create 100 nodes in a tree structure
        for i in range(100):
            self.nodes.append({
                "id": i,
                "label": f"Node {i}",
                "parent": i // 10 if i > 0 else None,
                "children": []
            })

        # Build parent-child relationships
        for node in self.nodes:
            if node["parent"] is not None:
                parent = self.nodes[node["parent"]]
                parent["children"].append(node["id"])

        # Initially expand root nodes
        for i in range(10):
            self.expanded.add(i)


def evaluate_results(stats):
    """Evaluate test results against gate criteria."""

    print("\n" + "="*80)
    print("Textual Stress Test Results")
    print("="*80 + "\n")

    # CPU usage
    cpu_pass = stats["cpu_avg"] < 10.0
    cpu_status = "✓ PASS" if cpu_pass else "✗ FAIL"
    print(f"  CPU Usage: {stats['cpu_avg']:.2f}% avg, {stats['cpu_max']:.2f}% max {cpu_status}")
    print(f"    Criteria: < 10%")

    # Frame rate
    fps_pass = stats["fps"] >= 30.0
    fps_status = "✓ PASS" if fps_pass else "✗ FAIL"
    print(f"  Frame Rate: {stats['fps']:.1f} FPS {fps_status}")
    print(f"    Criteria: ≥ 30 FPS")

    # Flicker (manual inspection)
    print(f"  Flicker: MANUAL INSPECTION REQUIRED")
    print(f"    Criteria: No visible flicker")

    # Overall verdict
    print()
    if cpu_pass and fps_pass:
        print("✓ GATE PASSED")
        print("Recommendation: Proceed with Textual implementation")
        return True
    else:
        print("✗ GATE FAILED")
        print("Recommendation: Escalate to user for decision")
        return False


async def main():
    """Main entry point."""
    print("\nTextual Stress Test - Phase 0 (Fallback)")
    print("Duration: 60 seconds")
    print("Scenarios:")
    print("  1. Token streaming (50 tokens/sec)")
    print("  2. Background tasks (5 progress bars, 100ms updates)")
    print("  3. Tree expansion (100 nodes, 10 toggles/sec)")
    print("\nGate Criteria:")
    print("  • CPU usage < 10%")
    print("  • No visible flicker")
    print("  • Frame rate ≥ 30 FPS")
    print("\nStarting in 3 seconds...\n")

    await asyncio.sleep(3)

    try:
        app = StressTestApp(duration_s=60)
        stats = await app.run_async()

        if stats:
            passed = evaluate_results(stats)
            exit(0 if passed else 1)
        else:
            print("\nTest interrupted by user")
            exit(2)

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        exit(2)


if __name__ == "__main__":
    asyncio.run(main())

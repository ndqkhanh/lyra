#!/usr/bin/env python3
"""
Rich Live() Stress Test - Phase 0 Performance Validation

Tests 3 concurrent scenarios to validate Rich Live() performance:
1. Thinking tokens streaming at 50 tokens/sec for 60 seconds
2. 5 concurrent background tasks updating progress bars every 100ms
3. Tree with 100 nodes, 10 expanding/collapsing per second

Gate criteria:
- CPU usage < 10% (measured via psutil)
- No visible flicker (manual inspection)
- Frame rate ≥ 30 FPS (measured via frame timing)

PASS → proceed with Rich
FAIL → pivot to Textual
"""

import asyncio
import time
import psutil
import random
from rich.live import Live
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from rich.text import Text

console = Console()


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
            "duration": time.monotonic() - self.start_time
        }


class TokenStreamSimulator:
    """Simulate thinking tokens streaming at 50 tokens/sec."""

    def __init__(self):
        self.tokens_received = 0
        self.start_time = None

    def start(self):
        self.start_time = time.monotonic()

    async def stream(self, duration_s=60):
        """Stream tokens for specified duration."""
        tokens_per_sec = 50
        interval = 1.0 / tokens_per_sec  # 20ms per token

        end_time = time.monotonic() + duration_s
        while time.monotonic() < end_time:
            self.tokens_received += 1
            await asyncio.sleep(interval)

    def get_display(self):
        """Get display text for current token count."""
        if self.tokens_received < 1000:
            return f"↓ {self.tokens_received} tokens"
        else:
            return f"↓ {self.tokens_received / 1000:.1f}k tokens"


class BackgroundTaskSimulator:
    """Simulate 5 concurrent background tasks with progress bars."""

    def __init__(self):
        self.tasks = [
            {"name": "Analyzing codebase", "progress": 0},
            {"name": "Running tests", "progress": 0},
            {"name": "Building project", "progress": 0},
            {"name": "Generating docs", "progress": 0},
            {"name": "Deploying app", "progress": 0},
        ]

    async def update_tasks(self, duration_s=60):
        """Update task progress every 100ms."""
        interval = 0.1  # 100ms
        end_time = time.monotonic() + duration_s

        while time.monotonic() < end_time:
            # Update each task progress
            for task in self.tasks:
                if task["progress"] < 100:
                    task["progress"] = min(100, task["progress"] + random.uniform(0.5, 2.0))
            await asyncio.sleep(interval)

    def render(self, progress: Progress, task_ids: list):
        """Render progress bars."""
        progress.update(task_ids[0], completed=self.tasks[0]["progress"])
        progress.update(task_ids[1], completed=self.tasks[1]["progress"])
        progress.update(task_ids[2], completed=self.tasks[2]["progress"])
        progress.update(task_ids[3], completed=self.tasks[3]["progress"])
        progress.update(task_ids[4], completed=self.tasks[4]["progress"])


class TreeSimulator:
    """Simulate tree with 100 nodes, 10 expanding/collapsing per second."""

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

    async def toggle_nodes(self, duration_s=60):
        """Toggle 10 random nodes per second."""
        interval = 0.1  # 100ms = 10 toggles per second
        end_time = time.monotonic() + duration_s

        while time.monotonic() < end_time:
            # Toggle 1 random node (10 per second)
            node_id = random.randint(0, 99)
            if node_id in self.expanded:
                self.expanded.remove(node_id)
            else:
                self.expanded.add(node_id)
            await asyncio.sleep(interval)

    def render(self):
        """Render tree with current expansion state."""
        tree = Tree("🌳 Agent Tree")

        # Render only root nodes and their expanded children
        for i in range(10):
            root = self.nodes[i]
            root_branch = tree.add(f"{'⏺' if i in self.expanded else '◯'} {root['label']}")

            if i in self.expanded:
                for child_id in root["children"]:
                    child = self.nodes[child_id]
                    child_branch = root_branch.add(
                        f"{'⏺' if child_id in self.expanded else '◯'} {child['label']}"
                    )

                    if child_id in self.expanded:
                        for grandchild_id in child["children"]:
                            grandchild = self.nodes[grandchild_id]
                            child_branch.add(f"◯ {grandchild['label']}")

        return tree


async def run_stress_test(duration_s=60):
    """Run all 3 stress test scenarios concurrently."""

    console.print("\n[bold cyan]Rich Live() Stress Test - Phase 0[/bold cyan]")
    console.print(f"Duration: {duration_s} seconds")
    console.print("Scenarios:")
    console.print("  1. Token streaming (50 tokens/sec)")
    console.print("  2. Background tasks (5 progress bars, 100ms updates)")
    console.print("  3. Tree expansion (100 nodes, 10 toggles/sec)")
    console.print("\nGate Criteria:")
    console.print("  • CPU usage < 10%")
    console.print("  • No visible flicker")
    console.print("  • Frame rate ≥ 30 FPS")
    console.print("\n[yellow]Starting in 3 seconds...[/yellow]\n")

    await asyncio.sleep(3)

    # Initialize simulators
    perf_monitor = PerformanceMonitor()
    token_stream = TokenStreamSimulator()
    bg_tasks = BackgroundTaskSimulator()
    tree_sim = TreeSimulator()

    # Create progress bars
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )

    task_ids = []
    for task in bg_tasks.tasks:
        task_id = progress.add_task(task["name"], total=100)
        task_ids.append(task_id)

    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )

    # Start monitoring
    perf_monitor.start()
    token_stream.start()

    # Start background tasks
    token_task = asyncio.create_task(token_stream.stream(duration_s))
    bg_task = asyncio.create_task(bg_tasks.update_tasks(duration_s))
    tree_task = asyncio.create_task(tree_sim.toggle_nodes(duration_s))

    # Render loop
    with Live(layout, console=console, refresh_per_second=30):
        start_time = time.monotonic()

        while time.monotonic() - start_time < duration_s:
            # Record frame timing
            perf_monitor.record_frame()

            # Sample CPU every 10 frames (~333ms at 30 FPS)
            if len(perf_monitor.frame_times) % 10 == 0:
                perf_monitor.sample_cpu()

            # Update header
            elapsed = time.monotonic() - start_time
            stats = perf_monitor.get_stats()
            header_text = Text()
            header_text.append("✳ Stress Testing", style="cyan bold")
            header_text.append(f" ({elapsed:.1f}s · ", style="dim")
            header_text.append(token_stream.get_display(), style="cyan")
            header_text.append(f" · {stats['fps']:.1f} FPS · CPU {stats['cpu_avg']:.1f}%)", style="dim")
            layout["header"].update(Panel(header_text, border_style="cyan"))

            # Update body
            bg_tasks.render(progress, task_ids)
            body_layout = Layout()
            body_layout.split_row(
                Layout(progress, name="progress"),
                Layout(tree_sim.render(), name="tree")
            )
            layout["body"].update(body_layout)

            # Update footer
            footer_text = Text("Press Ctrl+C to stop early", style="dim")
            layout["footer"].update(Panel(footer_text, border_style="dim"))

            # Refresh at 30 FPS
            await asyncio.sleep(1/30)

    # Wait for background tasks to complete
    await token_task
    await bg_task
    await tree_task

    # Get final stats
    final_stats = perf_monitor.get_stats()

    return final_stats


def evaluate_results(stats):
    """Evaluate test results against gate criteria."""

    console.print("\n[bold cyan]Test Results:[/bold cyan]\n")

    # CPU usage
    cpu_pass = stats["cpu_avg"] < 10.0
    cpu_status = "[green]✓ PASS[/green]" if cpu_pass else "[red]✗ FAIL[/red]"
    console.print(f"  CPU Usage: {stats['cpu_avg']:.2f}% avg, {stats['cpu_max']:.2f}% max {cpu_status}")
    console.print(f"    Criteria: < 10%")

    # Frame rate
    fps_pass = stats["fps"] >= 30.0
    fps_status = "[green]✓ PASS[/green]" if fps_pass else "[red]✗ FAIL[/red]"
    console.print(f"  Frame Rate: {stats['fps']:.1f} FPS {fps_status}")
    console.print(f"    Criteria: ≥ 30 FPS")

    # Flicker (manual inspection)
    console.print(f"  Flicker: [yellow]MANUAL INSPECTION REQUIRED[/yellow]")
    console.print(f"    Criteria: No visible flicker")

    # Overall verdict
    console.print()
    if cpu_pass and fps_pass:
        console.print("[bold green]✓ GATE PASSED[/bold green]")
        console.print("Recommendation: Proceed with Rich Live() implementation")
        return True
    else:
        console.print("[bold red]✗ GATE FAILED[/bold red]")
        console.print("Recommendation: Pivot to Textual framework")
        return False


async def main():
    """Main entry point."""
    try:
        stats = await run_stress_test(duration_s=60)
        passed = evaluate_results(stats)

        # Exit code
        exit(0 if passed else 1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        exit(2)


if __name__ == "__main__":
    asyncio.run(main())

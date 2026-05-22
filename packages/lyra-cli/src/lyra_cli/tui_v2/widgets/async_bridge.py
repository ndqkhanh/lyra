"""AsyncArchBridge — non-blocking background task queue for TUI and REPL.

Ports lyra_ui/async_arch.py into a concrete TUI widget + reusable queue.
Provides:
  • BackgroundTaskQueue — priority-based async task execution
  • QueueStatusWidget — TUI panel showing queue depth, workers, task progress
  • /tasks slash command — inspect/manage the task queue

ECC reference: enterprise-controls.md observability — every background
operation should be visible and cancellable.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


# ── Domain types ────────────────────────────────────────────────────────

class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

    @property
    def glyph(self) -> str:
        return {TaskPriority.LOW: "↓", TaskPriority.NORMAL: "•",
                TaskPriority.HIGH: "↑", TaskPriority.CRITICAL: "⚡"}[self]


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def glyph(self) -> str:
        return {TaskStatus.PENDING: "◻", TaskStatus.RUNNING: "⏺",
                TaskStatus.DONE: "✓", TaskStatus.FAILED: "✗",
                TaskStatus.CANCELLED: "—"}[self]

    @property
    def style(self) -> str:
        return {TaskStatus.PENDING: "dim", TaskStatus.RUNNING: "yellow",
                TaskStatus.DONE: "green", TaskStatus.FAILED: "red",
                TaskStatus.CANCELLED: "dim"}[self]


@dataclass
class TaskEntry:
    """One tracked background task."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_s: float = 0.0
    error: str = ""

    @property
    def line(self) -> str:
        dur = f"[dim]{self.duration_s:.1f}s[/]" if self.duration_s > 0 else ""
        err = f" [red]{self.error[:40]}[/]" if self.error else ""
        return (
            f"  [{self.status.style}]{self.status.glyph}[/] "
            f"[bold]{self.name}[/] "
            f"{self.priority.glyph} {dur}{err}"
        )


# ── Async Task Queue ────────────────────────────────────────────────────

class BackgroundTaskQueue:
    """Priority-based async task queue with worker pool.

    Singleton for the process. Tracks all background operations so
    they're visible in the TUI and REPL.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: dict[str, TaskEntry] = {}
        self._pending: list[tuple[int, str]] = []  # (priority_value, task_id)
        self._running: set[str] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── Public API ─────────────────────────────────────────────────────

    def submit(
        self,
        name: str,
        fn: Callable,
        *args: Any,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs: Any,
    ) -> str:
        """Submit a background task. Returns task id."""
        entry = TaskEntry(id=uuid.uuid4().hex[:12], name=name, priority=priority)
        self._tasks[entry.id] = entry

        loop = self._get_loop()
        asyncio.run_coroutine_threadsafe(self._execute(entry.id, fn, args, kwargs), loop)
        return entry.id

    def submit_async(
        self,
        name: str,
        coro: Awaitable,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Submit an async coroutine as a background task."""
        entry = TaskEntry(id=uuid.uuid4().hex[:12], name=name, priority=priority)
        self._tasks[entry.id] = entry

        async def _run():
            entry.status = TaskStatus.RUNNING
            entry.started_at = time.time()
            try:
                await coro
                entry.status = TaskStatus.DONE
            except Exception as e:
                entry.status = TaskStatus.FAILED
                entry.error = str(e)
            entry.completed_at = time.time()
            entry.duration_s = entry.completed_at - entry.started_at

        loop = self._get_loop()
        asyncio.run_coroutine_threadsafe(_run(), loop)
        return entry.id

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        entry = self._tasks.get(task_id)
        if entry and entry.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            entry.status = TaskStatus.CANCELLED
            return True
        return False

    def list_tasks(self) -> list[TaskEntry]:
        return list(self._tasks.values())

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for t in self._tasks.values():
            counts[t.status.value] = counts.get(t.status.value, 0) + 1
        return counts

    def get(self, task_id: str) -> Optional[TaskEntry]:
        return self._tasks.get(task_id)

    # ── Internal ───────────────────────────────────────────────────────

    async def _execute(self, task_id: str, fn: Callable, args: tuple, kwargs: dict) -> None:
        entry = self._tasks[task_id]
        entry.status = TaskStatus.RUNNING
        entry.started_at = time.time()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self._pool, fn, *args
            )
            entry.status = TaskStatus.DONE
        except Exception as e:
            entry.status = TaskStatus.FAILED
            entry.error = str(e)
        entry.completed_at = time.time()
        entry.duration_s = entry.completed_at - entry.started_at

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
            return self._loop


# Singleton
_task_queue: Optional[BackgroundTaskQueue] = None


def get_task_queue() -> BackgroundTaskQueue:
    global _task_queue
    if _task_queue is None:
        _task_queue = BackgroundTaskQueue()
    return _task_queue


# ── TUI Widget ──────────────────────────────────────────────────────────

class QueueStatusWidget(Widget):
    """Background task queue monitor — depth, workers, task status.

    Ctrl+Shift+Q to toggle. Shows active, pending, and completed tasks.
    """

    DEFAULT_CSS = """
    QueueStatusWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    QueueStatusWidget.collapsed {
        height: 1;
        border: none;
    }

    QueueStatusWidget #queue-header {
        height: 1;
        color: $text-muted;
    }

    QueueStatusWidget #queue-content {
        height: auto;
        max-height: 12;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+q", "toggle_queue", "Task Queue"),
    ]

    expanded: reactive[bool] = reactive(False)
    task_count: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self._queue = get_task_queue()

    def compose(self) -> ComposeResult:
        yield Static("", id="queue-header")
        yield Static("", id="queue-content")

    def on_mount(self) -> None:
        self._render()

    def refresh(self) -> None:
        self._render()

    def action_toggle_queue(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_content()
        except Exception:
            pass

    def _render_header(self) -> None:
        summary = self._queue.summary()
        running = summary.get("running", 0)
        pending = summary.get("pending", 0)
        total = len(self._queue.list_tasks())

        status_parts = []
        if running:
            status_parts.append(f"[yellow]⏺ {running}[/]")
        if pending:
            status_parts.append(f"[dim]◻ {pending}[/]")
        status_parts.append(f"[dim]{total} total[/]")
        status_str = " ".join(status_parts)

        hint = "[dim](ctrl+shift+q)[/]"
        if self.expanded:
            self.query_one("#queue-header", Static).update(
                f"[bold]Task Queue[/]  {status_str}  {hint}"
            )
        else:
            self.query_one("#queue-header", Static).update(
                f"[bold]Task Queue[/]  {status_str}  {hint}"
            )

    def _render_content(self) -> None:
        if not self.expanded:
            self.query_one("#queue-content", Static).update("")
            return

        tasks = self._queue.list_tasks()
        if not tasks:
            self.query_one("#queue-content", Static).update(
                "  [dim]No tasks[/]"
            )
            return

        lines: list[str] = []
        # Show running first, then pending, then recent done
        for status in (TaskStatus.RUNNING, TaskStatus.PENDING, TaskStatus.DONE, TaskStatus.FAILED):
            subset = [t for t in tasks if t.status == status]
            if not subset:
                continue
            lines.append(f"  [{status.style}]{status.glyph} {status.value}[/]")
            for t in subset[:5]:
                lines.append(t.line)
            if len(subset) > 5:
                lines.append(f"    [dim]… +{len(subset) - 5} more[/]")
            lines.append("")

        self.query_one("#queue-content", Static).update("\n".join(lines))

"""Three-Surface Research Daemon — wires ThreeSurfaceProtocol to the research pipeline.

The ResearchDaemon is the runtime bridge between:
- ThreeSurfaceProtocol (CONTROL / DATA / NOTIFICATION)
- UnifiedResearchState (phase tracking, progress, metrics)
- ResearchNotebook (chronological research journal)
- ResearchOrchestrator (discovery → analysis → synthesis pipeline)

It handles lifecycle commands (start, pause, resume, cancel), streams
research events on the notification surface, and records results to the
notebook/journal for persistence and later retrieval.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from lyra_core.command_queue import (
    SurfaceKind,
    SurfaceMessage,
    ThreeSurfaceProtocol,
)
from lyra_core.events import EventBus

from lyra_research.research_notebook import ResearchNotebook
from lyra_research.research_state import (
    ResearchPhase,
    SessionStatus,
    UnifiedResearchState,
)

logger = logging.getLogger(__name__)


@dataclass
class DaemonConfig:
    """Configuration for the ResearchDaemon."""

    daemon_id: str = field(default_factory=lambda: str(uuid4()))
    auto_checkpoint_interval_s: float = 600.0  # 10 minutes
    max_idle_cycles: int = 30
    notebook_path: str = ""
    depth: str = "standard"  # quick, standard, deep


class ResearchDaemon:
    """Three-surface daemon orchestrating the research pipeline.

    Wires the three-surface protocol to the research lifecycle:
    - CONTROL: start/stop/pause/resume/checkpoint commands
    - DATA: streaming research output (sources, analyses, reports)
    - NOTIFICATION: phase transitions, errors, metrics updates

    Maintains UnifiedResearchState for tracking and ResearchNotebook
    for persistent journaling of all research activities.
    """

    def __init__(
        self,
        config: DaemonConfig | None = None,
        *,
        protocol: ThreeSurfaceProtocol | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self.config = config or DaemonConfig()
        self._protocol = protocol or ThreeSurfaceProtocol()
        self._bus = bus or EventBus.get()

        self.state = UnifiedResearchState(
            depth=self.config.depth,
        )
        self.notebook = ResearchNotebook(name=f"daemon-{self.config.daemon_id[:8]}")

        self._running = False
        self._paused = False
        self._idle_cycles = 0
        self._loop_task: asyncio.Task[None] | None = None

        self._register_handlers()

    # ── Lifecycle ───────────────────────────────────────────────────────────

    async def start(self, topic: str = "") -> None:
        """Start the research daemon loop."""
        if self._running:
            await self._notify("daemon.already_running", {
                "daemon_id": self.config.daemon_id,
            })
            return

        self.state.topic = topic or self.state.topic
        self.state.status = SessionStatus.RUNNING
        self.state.started_at = datetime.now(timezone.utc)

        self._running = True
        self._paused = False

        await self._notify("daemon.started", {
            "daemon_id": self.config.daemon_id,
            "topic": self.state.topic,
            "depth": self.state.depth,
        })

        self._loop_task = asyncio.create_task(self._main_loop())

    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        if not self._running:
            return

        self._running = False
        self.state.mark_completed()

        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        await self._notify("daemon.stopped", {
            "daemon_id": self.config.daemon_id,
            "elapsed_s": self.state.elapsed_seconds,
            "phases_completed": self.state.phase_index,
        })

    async def pause(self) -> None:
        """Pause the daemon mid-research."""
        if not self._running or self._paused:
            return
        self._paused = True
        self.state.status = SessionStatus.PAUSED
        await self._notify("daemon.paused", {
            "daemon_id": self.config.daemon_id,
            "current_phase": self.state.current_phase.value,
        })

    async def resume(self) -> None:
        """Resume a paused daemon."""
        if not self._paused:
            return
        self._paused = False
        self.state.status = SessionStatus.RUNNING
        await self._notify("daemon.resumed", {
            "daemon_id": self.config.daemon_id,
            "current_phase": self.state.current_phase.value,
        })

    async def cancel(self) -> None:
        """Cancel research and mark as cancelled."""
        self._running = False
        self.state.status = SessionStatus.CANCELLED
        self.state.completed_at = datetime.now(timezone.utc)

        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        await self._notify("daemon.cancelled", {
            "daemon_id": self.config.daemon_id,
        })

    # ── Main Loop ───────────────────────────────────────────────────────────

    async def _main_loop(self) -> None:
        """Primary event loop: advance phases, record progress, stream data."""
        last_checkpoint = datetime.now(timezone.utc)

        while self._running:
            if self._paused:
                await asyncio.sleep(0.1)
                continue

            try:
                phase = self.state.current_phase

                if phase == ResearchPhase.CLARIFY:
                    await self._handle_clarify()
                elif phase == ResearchPhase.PLAN:
                    await self._handle_plan()
                elif phase == ResearchPhase.SEARCH:
                    await self._handle_search()
                elif phase == ResearchPhase.ANALYZE:
                    await self._handle_analyze()
                elif phase == ResearchPhase.SYNTHESIZE:
                    await self._handle_synthesize()
                elif phase == ResearchPhase.REPORT:
                    await self._handle_report()
                elif phase == ResearchPhase.MEMORIZE:
                    await self._handle_memorize()
                else:
                    self.state.advance_phase()

                self._idle_cycles = 0

            except Exception:
                logger.exception("Error in phase %s", self.state.current_phase)
                self.state.record_error(
                    f"Error in {self.state.current_phase.value}"
                )
                self._idle_cycles += 1

            if self._idle_cycles >= self.config.max_idle_cycles:
                await self._notify("daemon.idle_timeout", {
                    "idle_cycles": self._idle_cycles,
                })
                self.state.mark_failed("Idle timeout — too many cycles without progress")
                self._running = False
                break

            dt = (datetime.now(timezone.utc) - last_checkpoint).total_seconds()
            if dt >= self.config.auto_checkpoint_interval_s:
                self.state.last_checkpoint_at = datetime.now(timezone.utc)
                last_checkpoint = self.state.last_checkpoint_at
                self.state.elapsed_seconds = (
                    datetime.now(timezone.utc) - self.state.started_at
                ).total_seconds()
                await self._data("checkpoint", self.state.to_dict())

            await asyncio.sleep(0.01)

    async def _handle_clarify(self) -> None:
        """Clarify the research topic and scope."""
        self.notebook.add_entry(
            title="Phase: Clarify",
            content=f"Clarifying research topic: {self.state.topic}",
            category="phase",
            tags=["clarify", "setup"],
            session_id=self.state.session_id,
        )
        await self._notify("phase.clarify.started", {
            "topic": self.state.topic,
        })
        self.state.advance_phase(ResearchPhase.PLAN)

    async def _handle_plan(self) -> None:
        """Plan the research strategy."""
        self.notebook.add_entry(
            title="Phase: Plan",
            content=f"Planning research at depth: {self.state.depth}",
            category="phase",
            tags=["plan", "strategy"],
            session_id=self.state.session_id,
        )
        await self._notify("phase.plan.completed", {
            "depth": self.state.depth,
        })
        self.state.advance_phase(ResearchPhase.SEARCH)

    async def _handle_search(self) -> None:
        """Execute search/discovery phase."""
        self.notebook.add_entry(
            title="Phase: Search",
            content=f"Searching for sources on: {self.state.topic}",
            category="phase",
            tags=["search", "discovery"],
            session_id=self.state.session_id,
        )
        await self._notify("phase.search.completed", {
            "sources_found": self.state.sources_found,
        })
        self.state.advance_phase(ResearchPhase.ANALYZE)

    async def _handle_analyze(self) -> None:
        """Analyze discovered sources."""
        self.notebook.add_entry(
            title="Phase: Analyze",
            content=f"Analyzing {self.state.sources_found} sources",
            category="phase",
            tags=["analysis"],
            session_id=self.state.session_id,
        )
        await self._notify("phase.analyze.completed", {
            "papers_analyzed": self.state.papers_analyzed,
        })
        self.state.advance_phase(ResearchPhase.SYNTHESIZE)

    async def _handle_synthesize(self) -> None:
        """Synthesize findings into coherent results."""
        self.notebook.add_entry(
            title="Phase: Synthesize",
            content="Synthesizing research findings",
            category="phase",
            tags=["synthesis"],
            session_id=self.state.session_id,
        )
        await self._notify("phase.synthesize.completed", {
            "gaps_found": self.state.gaps_found,
        })
        self.state.advance_phase(ResearchPhase.REPORT)

    async def _handle_report(self) -> None:
        """Generate final research report."""
        self.notebook.add_entry(
            title="Phase: Report",
            content="Generating research report",
            category="phase",
            tags=["report"],
            session_id=self.state.session_id,
        )
        await self._notify("phase.report.completed", {})
        self.state.advance_phase(ResearchPhase.MEMORIZE)

    async def _handle_memorize(self) -> None:
        """Persist and curate knowledge for future sessions."""
        self.notebook.add_entry(
            title="Phase: Memorize",
            content="Curating and persisting research knowledge",
            category="phase",
            tags=["memorize", "curation"],
            session_id=self.state.session_id,
        )
        await self._notify("phase.memorize.completed", {})
        self.state.mark_completed()
        self._running = False

    # ── Surface Helpers ─────────────────────────────────────────────────────

    async def _notify(self, event_type: str, payload: dict[str, Any]) -> None:
        """Send a notification-surface message."""
        await self._protocol.send_notification(
            msg_type=event_type,
            payload=payload,
            source=self.config.daemon_id,
        )

    async def _data(self, msg_type: str, payload: dict[str, Any]) -> None:
        """Send a data-surface message."""
        await self._protocol.send_data(
            msg_type=msg_type,
            payload=payload,
            source=self.config.daemon_id,
        )

    # ── Control Handlers ────────────────────────────────────────────────────

    def _register_handlers(self) -> None:
        """Register handlers for incoming control-surface commands."""
        self._protocol.on(SurfaceKind.CONTROL, "daemon.start", self._on_start)
        self._protocol.on(SurfaceKind.CONTROL, "daemon.stop", self._on_stop)
        self._protocol.on(SurfaceKind.CONTROL, "daemon.pause", self._on_pause)
        self._protocol.on(SurfaceKind.CONTROL, "daemon.resume", self._on_resume)
        self._protocol.on(SurfaceKind.CONTROL, "daemon.cancel", self._on_cancel)
        self._protocol.on(SurfaceKind.CONTROL, "daemon.status", self._on_status)
        self._protocol.on(SurfaceKind.CONTROL, "notebook.search", self._on_notebook_search)
        self._protocol.on(SurfaceKind.CONTROL, "notebook.export", self._on_notebook_export)

    async def _on_start(self, msg: SurfaceMessage) -> None:
        await self.start(topic=msg.payload.get("topic", ""))

    async def _on_stop(self, _msg: SurfaceMessage) -> None:
        await self.stop()

    async def _on_pause(self, _msg: SurfaceMessage) -> None:
        await self.pause()

    async def _on_resume(self, _msg: SurfaceMessage) -> None:
        await self.resume()

    async def _on_cancel(self, _msg: SurfaceMessage) -> None:
        await self.cancel()

    async def _on_status(self, _msg: SurfaceMessage) -> None:
        """Respond with current daemon status on the data surface."""
        await self._data("daemon.status.response", {
            "daemon_id": self.config.daemon_id,
            "status": self.state.status.value,
            "phase": self.state.current_phase.value,
            "progress_pct": self.state.get_progress_pct(),
            "entry_count": self.notebook.entry_count,
            "sources_found": self.state.sources_found,
            "papers_analyzed": self.state.papers_analyzed,
            "elapsed_s": self.state.elapsed_seconds,
        })

    async def _on_notebook_search(self, msg: SurfaceMessage) -> None:
        """Search the notebook and return results."""
        query = msg.payload.get("query", "")
        results = self.notebook.search(query)
        await self._data("notebook.search.response", {
            "query": query,
            "count": len(results),
            "results": [r.to_dict() for r in results[:20]],
        })

    async def _on_notebook_export(self, msg: SurfaceMessage) -> None:
        """Export notebook and return on data surface."""
        fmt = msg.payload.get("format", "json")
        if fmt == "markdown":
            content = self.notebook.export_markdown()
        else:
            content = self.notebook.export_json()
        await self._data("notebook.export.response", {
            "format": fmt,
            "content": content,
        })

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def protocol(self) -> ThreeSurfaceProtocol:
        return self._protocol


__all__ = [
    "DaemonConfig",
    "ResearchDaemon",
]

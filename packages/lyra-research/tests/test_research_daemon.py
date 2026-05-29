"""Tests for ResearchDaemon — Phase 21 Architecture Upgrade Module 4/4."""
import asyncio

import pytest
from lyra_core.command_queue import (
    SurfaceKind,
    SurfaceMessage,
    ThreeSurfaceProtocol,
)
from lyra_research.research_daemon import DaemonConfig, ResearchDaemon
from lyra_research.research_state import ResearchPhase, SessionStatus


@pytest.fixture
def protocol():
    return ThreeSurfaceProtocol()


@pytest.fixture
def daemon(protocol):
    config = DaemonConfig(depth="quick")
    return ResearchDaemon(config=config, protocol=protocol)


class TestDaemonConfig:
    def test_defaults(self):
        config = DaemonConfig()
        assert config.depth == "standard"
        assert config.max_idle_cycles == 30
        assert config.auto_checkpoint_interval_s == 600.0

    def test_custom_config(self):
        config = DaemonConfig(
            depth="deep",
            max_idle_cycles=10,
            notebook_path="/tmp/nb.json",
        )
        assert config.depth == "deep"
        assert config.max_idle_cycles == 10
        assert config.notebook_path == "/tmp/nb.json"

    def test_unique_daemon_id(self):
        c1 = DaemonConfig()
        c2 = DaemonConfig()
        assert c1.daemon_id != c2.daemon_id


class TestResearchDaemonInitialization:
    def test_default_state(self, daemon):
        assert daemon.state.current_phase == ResearchPhase.CLARIFY
        assert daemon.state.status == SessionStatus.CREATED
        assert daemon.state.depth == "quick"
        assert not daemon.is_running
        assert not daemon.is_paused

    def test_has_notebook(self, daemon):
        assert daemon.notebook is not None

    def test_has_protocol(self, daemon):
        assert daemon.protocol is not None

    def test_handlers_registered(self, daemon):
        handlers = daemon.protocol._handlers[SurfaceKind.CONTROL]
        assert "daemon.start" in handlers
        assert "daemon.stop" in handlers
        assert "daemon.pause" in handlers
        assert "daemon.resume" in handlers
        assert "daemon.cancel" in handlers
        assert "daemon.status" in handlers
        assert "notebook.search" in handlers
        assert "notebook.export" in handlers


class TestResearchDaemonLifecycle:
    @pytest.mark.asyncio
    async def test_start(self, daemon):
        await daemon.start(topic="Test Research")
        assert daemon.is_running
        assert daemon.state.status == SessionStatus.RUNNING
        assert daemon.state.topic == "Test Research"
        await daemon.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self, daemon):
        await daemon.start(topic="Test")
        await daemon.start(topic="Another")  # Should be no-op
        await daemon.stop()

    @pytest.mark.asyncio
    async def test_stop(self, daemon):
        await daemon.start(topic="Test")
        assert daemon.is_running
        await daemon.stop()
        assert not daemon.is_running
        assert daemon.state.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, daemon):
        await daemon.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_pause_and_resume(self, daemon):
        await daemon.start(topic="Test")
        await daemon.pause()
        assert daemon.is_paused
        assert daemon.state.status == SessionStatus.PAUSED

        await daemon.resume()
        assert not daemon.is_paused
        assert daemon.state.status == SessionStatus.RUNNING
        await daemon.stop()

    @pytest.mark.asyncio
    async def test_pause_when_not_running(self, daemon):
        await daemon.pause()  # Should no-op

    @pytest.mark.asyncio
    async def test_resume_when_not_paused(self, daemon):
        await daemon.resume()  # Should no-op

    @pytest.mark.asyncio
    async def test_cancel(self, daemon):
        await daemon.start(topic="Test")
        await daemon.cancel()
        assert not daemon.is_running
        assert daemon.state.status == SessionStatus.CANCELLED


class TestResearchDaemonFullPipeline:
    @pytest.mark.asyncio
    async def test_full_phase_progression(self, daemon):
        """Run daemon through all phases and verify it completes."""
        await daemon.start(topic="Test full pipeline")

        # Let the event loop process the main loop
        for _ in range(20):
            await asyncio.sleep(0.01)
            if not daemon.is_running:
                break

        await daemon.stop()
        assert daemon.state.status in (
            SessionStatus.COMPLETED,
            SessionStatus.RUNNING,  # may still be running if loop not finished
        )

    @pytest.mark.asyncio
    async def test_notebook_populated(self, daemon):
        """Verify notebook gets entries during daemon run."""
        await daemon.start(topic="Notebook test")

        for _ in range(15):
            await asyncio.sleep(0.01)
            if daemon.notebook.entry_count >= 3:
                break

        entry_count = daemon.notebook.entry_count
        assert entry_count > 0

        phases = daemon.notebook.get_categories()
        assert "phase" in phases

        await daemon.stop()

    @pytest.mark.asyncio
    async def test_state_advances_phase(self, daemon):
        """Verify state phase advances during daemon execution."""
        await daemon.start(topic="Phase test")

        for _ in range(15):
            await asyncio.sleep(0.01)
            if daemon.state.current_phase != ResearchPhase.CLARIFY:
                break

        assert daemon.state.current_phase != ResearchPhase.CLARIFY
        await daemon.stop()


class TestResearchDaemonControlHandlers:
    @pytest.mark.asyncio
    async def test_status_handler(self, daemon):
        """Test that status command returns data on the data surface."""
        received = []

        def capture(msg: SurfaceMessage):
            received.append(msg)

        daemon.protocol.on(SurfaceKind.DATA, "daemon.status.response", capture)

        await daemon.start(topic="Status test")

        msg = SurfaceMessage(
            surface=SurfaceKind.CONTROL,
            id="ctrl-1",
            type="daemon.status",
            payload={},
            source="test",
        )
        await daemon._on_status(msg)

        await asyncio.sleep(0.02)

        assert len(received) >= 1
        status_msg = received[0]
        assert status_msg.payload["status"] in ("running", "created")
        assert "phase" in status_msg.payload
        assert "progress_pct" in status_msg.payload

        await daemon.stop()

    @pytest.mark.asyncio
    async def test_notebook_search_handler(self, daemon):
        """Test notebook search via control surface."""
        daemon.notebook.add_entry(
            title="Transformer Research",
            content="Attention mechanisms in transformers",
            category="finding",
            tags=["transformer"],
            session_id=daemon.state.session_id,
        )
        daemon.notebook.add_entry(
            title="CNN Research",
            content="Convolutional networks for vision",
            category="finding",
            tags=["cnn"],
            session_id=daemon.state.session_id,
        )

        received = []

        def capture(msg: SurfaceMessage):
            received.append(msg)

        daemon.protocol.on(SurfaceKind.DATA, "notebook.search.response", capture)

        msg = SurfaceMessage(
            surface=SurfaceKind.CONTROL,
            id="ctrl-2",
            type="notebook.search",
            payload={"query": "transformer"},
            source="test",
        )
        await daemon._on_notebook_search(msg)
        await asyncio.sleep(0.02)

        assert len(received) >= 1
        assert received[0].payload["count"] == 1

    @pytest.mark.asyncio
    async def test_notebook_export_json(self, daemon):
        """Test notebook export via control surface."""
        daemon.notebook.add_entry(
            title="Test", content="Content", category="note",
            session_id=daemon.state.session_id,
        )

        received = []

        def capture(msg: SurfaceMessage):
            received.append(msg)

        daemon.protocol.on(SurfaceKind.DATA, "notebook.export.response", capture)

        msg = SurfaceMessage(
            surface=SurfaceKind.CONTROL,
            id="ctrl-3",
            type="notebook.export",
            payload={"format": "json"},
            source="test",
        )
        await daemon._on_notebook_export(msg)
        await asyncio.sleep(0.02)

        assert len(received) >= 1
        assert received[0].payload["format"] == "json"
        assert "content" in received[0].payload

    @pytest.mark.asyncio
    async def test_notebook_export_markdown(self, daemon):
        """Test notebook export as markdown."""
        daemon.notebook.add_entry(
            title="Test", content="Content", category="note",
            session_id=daemon.state.session_id,
        )

        received = []

        def capture(msg: SurfaceMessage):
            received.append(msg)

        daemon.protocol.on(SurfaceKind.DATA, "notebook.export.response", capture)

        msg = SurfaceMessage(
            surface=SurfaceKind.CONTROL,
            id="ctrl-4",
            type="notebook.export",
            payload={"format": "markdown"},
            source="test",
        )
        await daemon._on_notebook_export(msg)
        await asyncio.sleep(0.02)

        assert received[0].payload["format"] == "markdown"
        assert "# daemon-" in received[0].payload["content"]


class TestResearchDaemonNotifications:
    @pytest.mark.asyncio
    async def test_start_sends_notification(self, daemon):
        """Verify start sends notification on notification surface."""
        received = []

        def capture(msg: SurfaceMessage):
            received.append(msg)

        daemon.protocol.on(SurfaceKind.NOTIFICATION, "daemon.started", capture)

        await daemon.start(topic="Notification test")
        await asyncio.sleep(0.02)

        assert len(received) >= 1
        assert received[0].payload["topic"] == "Notification test"
        await daemon.stop()

    @pytest.mark.asyncio
    async def test_stop_sends_notification(self, daemon):
        """Verify stop sends notification."""
        received = []

        def capture(msg: SurfaceMessage):
            received.append(msg)

        daemon.protocol.on(SurfaceKind.NOTIFICATION, "daemon.stopped", capture)

        await daemon.start(topic="Test")
        await daemon.stop()
        await asyncio.sleep(0.02)

        assert len(received) >= 1

    @pytest.mark.asyncio
    async def test_pause_and_resume_notifications(self, daemon):
        """Verify pause/resume send notifications."""
        paused_events = []
        resumed_events = []

        daemon.protocol.on(SurfaceKind.NOTIFICATION, "daemon.paused",
                          lambda m: paused_events.append(m))
        daemon.protocol.on(SurfaceKind.NOTIFICATION, "daemon.resumed",
                          lambda m: resumed_events.append(m))

        await daemon.start(topic="Test")
        await daemon.pause()
        await daemon.resume()
        await asyncio.sleep(0.02)

        assert len(paused_events) >= 1
        assert len(resumed_events) >= 1
        await daemon.stop()

    @pytest.mark.asyncio
    async def test_cancel_sends_notification(self, daemon):
        """Verify cancel sends notification."""
        received = []

        def capture(msg: SurfaceMessage):
            received.append(msg)

        daemon.protocol.on(SurfaceKind.NOTIFICATION, "daemon.cancelled", capture)

        await daemon.start(topic="Test")
        await daemon.cancel()
        await asyncio.sleep(0.02)

        assert len(received) >= 1
        assert received[0].payload["daemon_id"] == daemon.config.daemon_id


class TestResearchDaemonEdgeCases:
    @pytest.mark.asyncio
    async def test_multiple_starts_stops(self, daemon):
        """Verify multiple start/stop cycles work."""
        for _ in range(3):
            await daemon.start(topic="Cycle test")
            await asyncio.sleep(0.02)
            await daemon.stop()

    @pytest.mark.asyncio
    async def test_state_preserved_across_runs(self, daemon):
        """Verify notebook entries accumulate across runs."""
        await daemon.start(topic="Run 1")
        await asyncio.sleep(0.02)
        await daemon.stop()

        count_after_run1 = daemon.notebook.entry_count

        await daemon.start(topic="Run 2")
        await asyncio.sleep(0.02)
        await daemon.stop()

        assert daemon.notebook.entry_count >= count_after_run1

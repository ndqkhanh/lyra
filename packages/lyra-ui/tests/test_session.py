"""Tests for session management."""

from datetime import datetime

from lyra_ui import (
    SessionEventType,
    SessionManager,
    SessionReplay,
)

# SessionManager Tests


def test_session_manager_init(tmp_path):
    """Test session manager initialization."""
    manager = SessionManager(storage_path=tmp_path)
    assert manager.storage_path == tmp_path
    assert manager.current_session is None
    assert len(manager.events) == 0
    assert len(manager.annotations) == 0


def test_create_session(tmp_path):
    """Test creating session."""
    manager = SessionManager(storage_path=tmp_path)
    metadata = manager.create_session(
        session_id="test-session",
        author="test-user",
        title="Test Session",
        description="Test description",
        tags=["test", "demo"],
    )
    assert metadata.session_id == "test-session"
    assert metadata.author == "test-user"
    assert metadata.title == "Test Session"
    assert metadata.description == "Test description"
    assert metadata.tags == ["test", "demo"]
    assert manager.current_session == metadata


def test_add_event(tmp_path):
    """Test adding event."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")

    event = manager.add_event(
        event_id="event1",
        event_type=SessionEventType.MESSAGE,
        data={"content": "Hello"},
    )
    assert event.id == "event1"
    assert event.type == SessionEventType.MESSAGE
    assert event.data == {"content": "Hello"}
    assert len(manager.events) == 1
    assert manager.current_session.total_events == 1


def test_add_annotation(tmp_path):
    """Test adding annotation."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")

    annotation = manager.add_annotation(
        annotation_id="ann1",
        event_id="event1",
        author="reviewer",
        text="Good point",
    )
    assert annotation.id == "ann1"
    assert annotation.event_id == "event1"
    assert annotation.author == "reviewer"
    assert annotation.text == "Good point"
    assert len(manager.annotations) == 1


def test_export_session(tmp_path):
    """Test exporting session."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")
    manager.add_event("event1", SessionEventType.MESSAGE, {"content": "Hello"})
    manager.add_annotation("ann1", "event1", "reviewer", "Good")

    exported = manager.export_session()
    assert "metadata" in exported
    assert "events" in exported
    assert "annotations" in exported
    assert exported["metadata"]["session_id"] == "test"
    assert len(exported["events"]) == 1
    assert len(exported["annotations"]) == 1


def test_import_session(tmp_path):
    """Test importing session."""
    manager = SessionManager(storage_path=tmp_path)

    session_data = {
        "metadata": {
            "session_id": "imported",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "author": "user",
            "title": "Imported",
            "description": "Test",
            "tags": ["test"],
            "total_events": 1,
            "total_tokens": 100,
            "total_cost": 0.01,
        },
        "events": [
            {
                "id": "event1",
                "type": "message",
                "timestamp": datetime.now().isoformat(),
                "data": {"content": "Hello"},
                "metadata": {},
            }
        ],
        "annotations": [
            {
                "id": "ann1",
                "event_id": "event1",
                "author": "reviewer",
                "text": "Good",
                "timestamp": datetime.now().isoformat(),
            }
        ],
    }

    manager.import_session(session_data)
    assert manager.current_session.session_id == "imported"
    assert len(manager.events) == 1
    assert len(manager.annotations) == 1


def test_save_and_load_session(tmp_path):
    """Test saving and loading session."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")
    manager.add_event("event1", SessionEventType.MESSAGE, {"content": "Hello"})

    manager.save_session()
    assert (tmp_path / "test.json").exists()

    manager2 = SessionManager(storage_path=tmp_path)
    manager2.load_session("test")
    assert manager2.current_session.session_id == "test"
    assert len(manager2.events) == 1


def test_list_sessions(tmp_path):
    """Test listing sessions."""
    manager = SessionManager(storage_path=tmp_path)

    manager.create_session("session1", "user1", "Session 1")
    manager.save_session()

    manager.create_session("session2", "user2", "Session 2")
    manager.save_session()

    sessions = manager.list_sessions()
    assert len(sessions) == 2


def test_search_sessions_by_query(tmp_path):
    """Test searching sessions by query."""
    manager = SessionManager(storage_path=tmp_path)

    manager.create_session("s1", "user", "Python Tutorial")
    manager.save_session()

    manager.create_session("s2", "user", "JavaScript Guide")
    manager.save_session()

    results = manager.search_sessions(query="python")
    assert len(results) == 1
    assert results[0].title == "Python Tutorial"


def test_search_sessions_by_author(tmp_path):
    """Test searching sessions by author."""
    manager = SessionManager(storage_path=tmp_path)

    manager.create_session("s1", "alice", "Session 1")
    manager.save_session()

    manager.create_session("s2", "bob", "Session 2")
    manager.save_session()

    results = manager.search_sessions(author="alice")
    assert len(results) == 1
    assert results[0].author == "alice"


def test_search_sessions_by_tags(tmp_path):
    """Test searching sessions by tags."""
    manager = SessionManager(storage_path=tmp_path)

    manager.create_session("s1", "user", "Session 1", tags=["python", "tutorial"])
    manager.save_session()

    manager.create_session("s2", "user", "Session 2", tags=["javascript"])
    manager.save_session()

    results = manager.search_sessions(tags=["python"])
    assert len(results) == 1


def test_get_analytics(tmp_path):
    """Test getting analytics."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")
    manager.add_event("e1", SessionEventType.MESSAGE, {})
    manager.add_event("e2", SessionEventType.TOOL_CALL, {})
    manager.add_annotation("a1", "e1", "user", "Note")

    analytics = manager.get_analytics()
    assert analytics["session_id"] == "test"
    assert analytics["total_events"] == 2
    assert analytics["total_annotations"] == 1
    assert "event_types" in analytics


# SessionReplay Tests


def test_session_replay_init(tmp_path):
    """Test session replay initialization."""
    manager = SessionManager(storage_path=tmp_path)
    replay = SessionReplay(manager)
    assert replay.session_manager == manager
    assert replay.current_index == 0


def test_session_replay_start(tmp_path):
    """Test starting replay."""
    manager = SessionManager(storage_path=tmp_path)
    replay = SessionReplay(manager)
    replay.current_index = 5
    replay.start()
    assert replay.current_index == 0


def test_session_replay_next_event(tmp_path):
    """Test getting next event."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")
    manager.add_event("e1", SessionEventType.MESSAGE, {"content": "First"})
    manager.add_event("e2", SessionEventType.MESSAGE, {"content": "Second"})

    replay = SessionReplay(manager)
    event1 = replay.next_event()
    assert event1.id == "e1"
    event2 = replay.next_event()
    assert event2.id == "e2"
    event3 = replay.next_event()
    assert event3 is None


def test_session_replay_previous_event(tmp_path):
    """Test getting previous event."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")
    manager.add_event("e1", SessionEventType.MESSAGE, {})
    manager.add_event("e2", SessionEventType.MESSAGE, {})

    replay = SessionReplay(manager)
    replay.current_index = 2

    event = replay.previous_event()
    assert event.id == "e2"
    event = replay.previous_event()
    assert event.id == "e1"
    event = replay.previous_event()
    assert event is None


def test_session_replay_goto_event(tmp_path):
    """Test going to specific event."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")
    manager.add_event("e1", SessionEventType.MESSAGE, {})
    manager.add_event("e2", SessionEventType.MESSAGE, {})
    manager.add_event("e3", SessionEventType.MESSAGE, {})

    replay = SessionReplay(manager)
    event = replay.goto_event(1)
    assert event.id == "e2"
    assert replay.current_index == 1


def test_session_replay_get_progress(tmp_path):
    """Test getting replay progress."""
    manager = SessionManager(storage_path=tmp_path)
    manager.create_session("test", "user", "Test")
    for i in range(10):
        manager.add_event(f"e{i}", SessionEventType.MESSAGE, {})

    replay = SessionReplay(manager)
    replay.current_index = 5
    progress = replay.get_progress()
    assert progress == 50.0


# Integration Tests


def test_complete_session_workflow(tmp_path):
    """Test complete session workflow."""
    manager = SessionManager(storage_path=tmp_path)

    # Create session
    manager.create_session(
        "workflow-test",
        "test-user",
        "Workflow Test",
        "Testing complete workflow",
        ["test", "workflow"],
    )

    # Add events
    manager.add_event("e1", SessionEventType.MESSAGE, {"role": "user", "content": "Hello"})
    manager.add_event("e2", SessionEventType.MESSAGE, {"role": "assistant", "content": "Hi"})
    manager.add_event("e3", SessionEventType.TOOL_CALL, {"tool": "search", "query": "test"})
    manager.add_event("e4", SessionEventType.TOOL_RESULT, {"result": "found"})

    # Add annotations
    manager.add_annotation("a1", "e1", "reviewer", "Good question")
    manager.add_annotation("a2", "e2", "reviewer", "Clear response")

    # Save session
    manager.save_session()

    # Load in new manager
    manager2 = SessionManager(storage_path=tmp_path)
    manager2.load_session("workflow-test")

    # Verify
    assert manager2.current_session.session_id == "workflow-test"
    assert len(manager2.events) == 4
    assert len(manager2.annotations) == 2

    # Replay
    replay = SessionReplay(manager2)
    events = []
    while True:
        event = replay.next_event()
        if event is None:
            break
        events.append(event)
    assert len(events) == 4


def test_session_export_import_roundtrip(tmp_path):
    """Test session export/import roundtrip."""
    manager1 = SessionManager(storage_path=tmp_path)
    manager1.create_session("roundtrip", "user", "Test")
    manager1.add_event("e1", SessionEventType.MESSAGE, {"content": "Test"})

    exported = manager1.export_session()

    manager2 = SessionManager(storage_path=tmp_path)
    manager2.import_session(exported)

    assert manager2.current_session.session_id == "roundtrip"
    assert len(manager2.events) == 1
    assert manager2.events[0].data["content"] == "Test"

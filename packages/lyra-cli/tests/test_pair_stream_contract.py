"""Wave-D Task 15: live-streaming ``/pair`` substrate.

Wave-C shipped the ``/pair`` flag. Wave-D wires it to the lifecycle
bus so a paired terminal sees agent-loop events as they happen.

Six RED tests:

1. :class:`PairStream` constructs from a sink callable + lifecycle bus.
2. ``attach`` registers the stream against every lifecycle event.
3. Emitting ``TURN_START`` writes a labelled line to the sink when
   the stream is attached.
4. ``detach`` removes the subscriptions cleanly.
5. ``set_enabled(False)`` mutes the sink without detaching.
6. The renderer formats ``TOOL_CALL`` events with tool + args summary.
"""
from __future__ import annotations


def test_pair_stream_constructs() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus
    from lyra_cli.interactive.pair_stream import PairStream

    sink: list[str] = []
    PairStream(sink=sink.append, bus=LifecycleBus())


def test_attach_subscribes_for_every_event() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent
    from lyra_cli.interactive.pair_stream import PairStream

    bus = LifecycleBus()
    sink: list[str] = []
    stream = PairStream(sink=sink.append, bus=bus)
    stream.attach()
    bus.emit(LifecycleEvent.SESSION_START, {"session_id": "s"})
    bus.emit(LifecycleEvent.TURN_START, {"iteration": 1})
    bus.emit(LifecycleEvent.TURN_COMPLETE, {"iteration": 1})
    bus.emit(LifecycleEvent.TURN_REJECTED, {"reason": "x"})
    bus.emit(LifecycleEvent.TOOL_CALL, {"tool": "Read", "args": {"path": "x"}})
    bus.emit(LifecycleEvent.SESSION_END, {})
    # 6 lifecycle events → 6 lines.
    assert len(sink) == 6


def test_turn_start_written_to_sink() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent
    from lyra_cli.interactive.pair_stream import PairStream

    bus = LifecycleBus()
    sink: list[str] = []
    PairStream(sink=sink.append, bus=bus).attach()
    bus.emit(LifecycleEvent.TURN_START, {"iteration": 3})
    assert any("turn_start" in line and "iteration=3" in line for line in sink)


def test_detach_removes_subscriptions() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent
    from lyra_cli.interactive.pair_stream import PairStream

    bus = LifecycleBus()
    sink: list[str] = []
    stream = PairStream(sink=sink.append, bus=bus)
    stream.attach()
    stream.detach()
    bus.emit(LifecycleEvent.TURN_START, {"iteration": 1})
    assert sink == []


def test_set_enabled_false_mutes_sink() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent
    from lyra_cli.interactive.pair_stream import PairStream

    bus = LifecycleBus()
    sink: list[str] = []
    stream = PairStream(sink=sink.append, bus=bus)
    stream.attach()
    stream.set_enabled(False)
    bus.emit(LifecycleEvent.TURN_START, {"iteration": 1})
    assert sink == []
    stream.set_enabled(True)
    bus.emit(LifecycleEvent.TURN_START, {"iteration": 2})
    assert sink and "iteration=2" in sink[-1]


def test_tool_call_formatting() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent
    from lyra_cli.interactive.pair_stream import PairStream

    bus = LifecycleBus()
    sink: list[str] = []
    PairStream(sink=sink.append, bus=bus).attach()
    bus.emit(LifecycleEvent.TOOL_CALL, {"tool": "Read", "args": {"path": "/tmp/x"}})
    assert any("tool_call" in line and "Read" in line for line in sink)

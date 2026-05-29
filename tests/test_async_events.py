#!/usr/bin/env python3
"""Test async event handler support."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/lyra-cli/src'))

from lyra_cli.events import EventDispatcher, TextDelta, TurnStarted


async def test_async_handlers():
    """Test async event handlers."""
    print("=" * 80)
    print("ASYNC HANDLER TEST")
    print("=" * 80)

    dispatcher = EventDispatcher()
    events_received = []

    # Async handler
    async def async_handler(event):
        await asyncio.sleep(0.001)  # Simulate async work
        events_received.append(("async", event.text))

    # Sync handler
    def sync_handler(event):
        events_received.append(("sync", event.text))

    dispatcher.on("text.delta", async_handler)
    dispatcher.on("text.delta", sync_handler)

    # Emit events
    dispatcher.emit(TextDelta(turn_id="test", text="Hello"))
    dispatcher.emit(TextDelta(turn_id="test", text="World"))

    # Wait for async handlers to complete
    await asyncio.sleep(0.1)

    print(f"Events received: {len(events_received)}")
    print(f"Events: {events_received}")

    # Should have 4 events: 2 sync + 2 async
    expected = 4
    if len(events_received) == expected:
        print(f"✓ PASS - Received {expected} events (2 sync + 2 async)")
    else:
        print(f"✗ FAIL - Expected {expected} events, got {len(events_received)}")

    print()
    return len(events_received) == expected


async def test_mixed_handlers():
    """Test mixing sync and async handlers."""
    print("=" * 80)
    print("MIXED HANDLER TEST")
    print("=" * 80)

    dispatcher = EventDispatcher()
    order = []

    def sync1(event):
        order.append("sync1")

    async def async1(event):
        await asyncio.sleep(0.001)
        order.append("async1")

    def sync2(event):
        order.append("sync2")

    async def async2(event):
        await asyncio.sleep(0.001)
        order.append("async2")

    dispatcher.on("turn.started", sync1)
    dispatcher.on("turn.started", async1)
    dispatcher.on("turn.started", sync2)
    dispatcher.on("turn.started", async2)

    dispatcher.emit(TurnStarted(turn_id="test", user_text="Test"))

    # Wait for async handlers
    await asyncio.sleep(0.1)

    print(f"Execution order: {order}")
    print(f"Handlers executed: {len(order)}")

    # Sync handlers execute immediately, async handlers execute later
    # So we should see: sync1, sync2, then async1, async2
    if len(order) == 4:
        print("✓ PASS - All 4 handlers executed")
    else:
        print(f"✗ FAIL - Expected 4 handlers, got {len(order)}")

    print()
    return len(order) == 4


async def test_async_wildcard():
    """Test async wildcard handlers."""
    print("=" * 80)
    print("ASYNC WILDCARD HANDLER TEST")
    print("=" * 80)

    dispatcher = EventDispatcher()
    events = []

    async def async_wildcard(event):
        await asyncio.sleep(0.001)
        events.append(event.type)

    dispatcher.on_any(async_wildcard)

    dispatcher.emit(TurnStarted(turn_id="test", user_text="Test"))
    dispatcher.emit(TextDelta(turn_id="test", text="Hello"))

    # Wait for async handlers
    await asyncio.sleep(0.1)

    print(f"Events captured: {events}")

    if len(events) == 2:
        print("✓ PASS - Wildcard handler received all events")
    else:
        print(f"✗ FAIL - Expected 2 events, got {len(events)}")

    print()
    return len(events) == 2


async def main():
    print("\n")
    print("╭─── Async Event Handler Tests ───╮")
    print("│ Verifying async support          │")
    print("╰──────────────────────────────────╯")
    print()

    results = []
    results.append(("Async Handlers", await test_async_handlers()))
    results.append(("Mixed Handlers", await test_mixed_handlers()))
    results.append(("Async Wildcard", await test_async_wildcard()))

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n✓ ALL ASYNC TESTS PASSED")
    else:
        print("\n✗ SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

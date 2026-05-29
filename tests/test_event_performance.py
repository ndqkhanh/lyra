#!/usr/bin/env python3
"""Performance test for event dispatcher - verify 16ms (60fps) requirement."""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/lyra-cli/src'))

from lyra_cli.events import EventDispatcher, TextDelta


def test_event_latency():
    """Test that events trigger within 16ms (60fps target)."""
    print("=" * 80)
    print("EVENT LATENCY TEST - 60fps Target (16ms)")
    print("=" * 80)

    dispatcher = EventDispatcher()
    latencies = []

    def handler(event):
        elapsed = (time.perf_counter() - handler.start_time) * 1000
        latencies.append(elapsed)

    dispatcher.on("text.delta", handler)

    # Test 100 events
    for i in range(100):
        handler.start_time = time.perf_counter()
        dispatcher.emit(TextDelta(turn_id="test", text=f"chunk-{i}"))

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"Events tested: {len(latencies)}")
    print(f"Average latency: {avg_latency:.3f}ms")
    print(f"Min latency: {min_latency:.3f}ms")
    print(f"Max latency: {max_latency:.3f}ms")
    print("Target: <16ms (60fps)")

    if avg_latency < 16:
        print(f"✓ PASS - Average latency {avg_latency:.3f}ms < 16ms")
    else:
        print(f"✗ FAIL - Average latency {avg_latency:.3f}ms >= 16ms")

    if max_latency < 16:
        print(f"✓ PASS - Max latency {max_latency:.3f}ms < 16ms")
    else:
        print(f"⚠ WARNING - Max latency {max_latency:.3f}ms >= 16ms")

    print()
    return avg_latency < 16


def test_throughput():
    """Test event throughput."""
    print("=" * 80)
    print("EVENT THROUGHPUT TEST")
    print("=" * 80)

    dispatcher = EventDispatcher()
    count = 0

    def handler(event):
        nonlocal count
        count += 1

    dispatcher.on("text.delta", handler)

    # Emit 10,000 events
    start = time.perf_counter()
    for i in range(10000):
        dispatcher.emit(TextDelta(turn_id="test", text=f"chunk-{i}"))
    elapsed = time.perf_counter() - start

    events_per_sec = count / elapsed

    print(f"Events emitted: {count}")
    print(f"Time elapsed: {elapsed:.3f}s")
    print(f"Throughput: {events_per_sec:.0f} events/sec")
    print()

    return events_per_sec > 10000


def test_thread_safety():
    """Test thread-safe event emission."""
    print("=" * 80)
    print("THREAD SAFETY TEST")
    print("=" * 80)

    import threading

    dispatcher = EventDispatcher()
    count = 0
    lock = threading.Lock()

    def handler(event):
        nonlocal count
        with lock:
            count += 1

    dispatcher.on("text.delta", handler)

    # Emit from multiple threads
    def emit_events(thread_id, num_events):
        for i in range(num_events):
            dispatcher.emit(TextDelta(turn_id=f"thread-{thread_id}", text=f"chunk-{i}"))

    threads = []
    num_threads = 10
    events_per_thread = 100

    start = time.perf_counter()
    for i in range(num_threads):
        t = threading.Thread(target=emit_events, args=(i, events_per_thread))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.perf_counter() - start

    expected = num_threads * events_per_thread
    print(f"Threads: {num_threads}")
    print(f"Events per thread: {events_per_thread}")
    print(f"Expected events: {expected}")
    print(f"Received events: {count}")
    print(f"Time elapsed: {elapsed:.3f}s")

    if count == expected:
        print("✓ PASS - All events received")
    else:
        print(f"✗ FAIL - Missing {expected - count} events")

    print()
    return count == expected


if __name__ == "__main__":
    print("\n")
    print("╭─── Event Dispatcher Performance Tests ───╮")
    print("│ Verifying 60fps latency and thread safety │")
    print("╰───────────────────────────────────────────╯")
    print()

    results = []
    results.append(("Latency", test_event_latency()))
    results.append(("Throughput", test_throughput()))
    results.append(("Thread Safety", test_thread_safety()))

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n✓ ALL PERFORMANCE TESTS PASSED")
    else:
        print("\n✗ SOME TESTS FAILED")
        sys.exit(1)

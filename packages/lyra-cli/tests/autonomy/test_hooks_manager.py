"""Tests for the hooks manager."""

from __future__ import annotations

from lyra_cli.autonomy.hooks_manager import HookEvent, HooksManager


class TestHooksManager:
    """Suite: HooksManager registration, firing, clearing."""

    def test_register_and_fire(self) -> None:
        mgr = HooksManager()
        results: list[str] = []

        def handler(event: HookEvent, ctx: dict) -> None:
            results.append(event.value)

        mgr.register(HookEvent.ON_START, handler)
        mgr.fire(HookEvent.ON_START)
        assert results == ["on_start"]

    def test_fire_passes_context(self) -> None:
        mgr = HooksManager()
        captured: dict | None = None

        def handler(event: HookEvent, ctx: dict) -> None:
            nonlocal captured
            captured = ctx

        mgr.register(HookEvent.ON_COMPLETE, handler)
        mgr.fire(HookEvent.ON_COMPLETE, {"result": "ok"})
        assert captured is not None
        assert captured["result"] == "ok"

    def test_unregister_handler(self) -> None:
        mgr = HooksManager()

        def handler(event: HookEvent, ctx: dict) -> None:
            pass

        mgr.register(HookEvent.ON_START, handler)
        assert mgr.registered_count(HookEvent.ON_START) == 1
        assert mgr.unregister(HookEvent.ON_START, handler) is True
        assert mgr.registered_count(HookEvent.ON_START) == 0

    def test_unregister_nonexistent(self) -> None:
        mgr = HooksManager()

        def handler(event: HookEvent, ctx: dict) -> None:
            pass

        assert mgr.unregister(HookEvent.ON_ERROR, handler) is False

    def test_fire_all_events(self) -> None:
        mgr = HooksManager()
        fired: list[str] = []

        def handler(event: HookEvent, ctx: dict) -> None:
            fired.append(event.value)

        for event in HookEvent:
            mgr.register(event, handler)

        for event in HookEvent:
            mgr.fire(event)

        assert len(fired) == len(HookEvent)
        assert set(fired) == {e.value for e in HookEvent}

    def test_clear_removes_all(self) -> None:
        mgr = HooksManager()

        def handler(event: HookEvent, ctx: dict) -> None:
            pass

        mgr.register(HookEvent.ON_START, handler)
        mgr.register(HookEvent.ON_ERROR, handler)
        assert mgr.registered_count() == 2
        mgr.clear()
        assert mgr.registered_count() == 0

    def test_handler_error_does_not_crash(self) -> None:
        mgr = HooksManager()
        results: list[str] = []

        def broken(event: HookEvent, ctx: dict) -> None:
            raise RuntimeError("boom")

        def good(event: HookEvent, ctx: dict) -> None:
            results.append("ok")

        mgr.register(HookEvent.ON_START, broken)
        mgr.register(HookEvent.ON_START, good)
        mgr.fire(HookEvent.ON_START)
        assert results == ["ok"]

    def test_register_with_name(self) -> None:
        mgr = HooksManager()

        def handler(event: HookEvent, ctx: dict) -> None:
            pass

        mgr.register(HookEvent.ON_BLOCKED, handler, name="my_handler")
        assert mgr.registered_count(HookEvent.ON_BLOCKED) == 1

    def test_fire_no_handlers_no_error(self) -> None:
        mgr = HooksManager()
        # Should not raise
        mgr.fire(HookEvent.ON_RESUME)

"""Tiny factory — wrap an :class:`AgentLoop` with EternalAgentLoop.

Any caller that wants durable turns (background skill reviewer,
``/spawn``'d subagents, future REPL integration) can use this helper
without remembering the construction details.

Usage::

    from lyra_cli.eternal_factory import make_eternal_loop

    eternal = make_eternal_loop(
        agent_loop,
        state_dir=Path("~/.lyra/eternal").expanduser(),
        workflow_name="lyra.skill_review",
    )
    result = eternal.run_conversation_durable(prompt, session_id="s1")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from typing import Any, Callable

# ``harness_eternal`` is an optional sibling package — present in the
# orion-code monorepo and on production deployments, absent in lean
# checkouts where users never opt into eternal-mode. Importing it
# eagerly broke every test file that touched ``eternal_factory`` even
# when the test never instantiated a durable loop. We import lazily and
# raise a clear error at call time instead, so module-level ``import
# lyra_cli.eternal_factory`` always succeeds.
try:
    from harness_eternal import CircuitBreaker  # type: ignore[import-untyped]
    from harness_eternal.restate import (  # type: ignore[import-untyped]
        LocalRuntime,
        RestateRuntime,
    )

    _HARNESS_ETERNAL_OK = True
    _HARNESS_ETERNAL_ERR: str | None = None
except ImportError as _exc:  # pragma: no cover — exercised in lean envs
    _HARNESS_ETERNAL_OK = False
    _HARNESS_ETERNAL_ERR = str(_exc)

    class CircuitBreaker:  # type: ignore[no-redef]
        """Stub — real impl ships in ``harness_eternal``."""

        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError(
                "harness_eternal is not installed; install it to enable "
                f"eternal-mode (original ImportError: {_HARNESS_ETERNAL_ERR})"
            )

    class LocalRuntime:  # type: ignore[no-redef]
        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError(
                "harness_eternal is not installed; install it to enable "
                f"eternal-mode (original ImportError: {_HARNESS_ETERNAL_ERR})"
            )

    class RestateRuntime:  # type: ignore[no-redef]
        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError(
                "harness_eternal is not installed; install it to enable "
                f"eternal-mode (original ImportError: {_HARNESS_ETERNAL_ERR})"
            )


try:
    from lyra_core.agent.eternal_turn import EternalAgentLoop
except ImportError:  # pragma: no cover — lean env

    class EternalAgentLoop:  # type: ignore[no-redef]
        """Stub — real impl ships in ``lyra_core.agent.eternal_turn``."""

        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError(
                "lyra_core.agent.eternal_turn is unavailable; cannot "
                "wrap a loop in eternal-mode."
            )


def make_eternal_loop(
    agent_loop: Any,
    *,
    state_dir: Path | str,
    workflow_name: str = "lyra.turn",
    deadline_per_turn_s: int = 600,
    breaker_after: int = 5,
    runtime: LocalRuntime | RestateRuntime | None = None,
    breaker: CircuitBreaker | None = None,
) -> EternalAgentLoop:
    """Build an :class:`EternalAgentLoop` ready to wrap the given loop.

    ``state_dir`` is where the SQLite journal lives. Two callers using
    the same ``state_dir`` share the same journal — useful when the
    background reviewer should see the parent's invocation history.

    ``runtime`` and ``breaker`` are constructed automatically if not
    supplied. Pass them explicitly when you want to share state across
    multiple eternal loops.
    """
    state_dir = Path(state_dir).expanduser()
    state_dir.mkdir(parents=True, exist_ok=True)
    if runtime is None:
        runtime = LocalRuntime(state_dir / "restate")
    if breaker is None:
        breaker = CircuitBreaker(after=breaker_after)
    return EternalAgentLoop(
        loop=agent_loop,
        runtime=runtime,
        breaker=breaker,
        deadline_per_turn_s=deadline_per_turn_s,
        workflow_name=workflow_name,
    )


def make_eternal_loop_factory(
    inner_factory: Callable[[], Any],
    *,
    state_dir: Path | str,
    workflow_name: str = "lyra.subagent",
    deadline_per_turn_s: int = 1_800,
    breaker_after: int = 5,
    runtime: LocalRuntime | RestateRuntime | None = None,
    breaker: CircuitBreaker | None = None,
) -> Callable[[], EternalAgentLoop]:
    """Wrap a plain ``loop_factory`` so each call returns a durable loop.

    Designed for :class:`lyra_core.subagent.runner.SubagentRunner` — the
    runner's ``loop_factory`` parameter expects a callable that returns a
    fresh ``AgentLoop`` per spawn. This wrapper returns a fresh
    :class:`EternalAgentLoop` (which duck-types as ``AgentLoop`` via the
    ``run_conversation`` alias) so every spawn is journaled into the
    shared SQLite ledger under ``state_dir``.

    The same ``runtime`` and ``breaker`` are shared across spawns so that
    workflow-level quarantine and the journal are coherent across the
    whole spawn fleet.

    Usage::

        from lyra_cli.eternal_factory import make_eternal_loop_factory

        runner = SubagentRunner(
            loop_factory=make_eternal_loop_factory(
                lambda: AgentLoop(llm=..., tools=..., store=...),
                state_dir="~/.lyra/eternal/subagents",
                workflow_name="lyra.subagent",
            ),
            repo_root=...,
            worktree_root=...,
        )
    """
    state_dir_p = Path(state_dir).expanduser()
    state_dir_p.mkdir(parents=True, exist_ok=True)
    if runtime is None:
        runtime = LocalRuntime(state_dir_p / "restate")
    if breaker is None:
        breaker = CircuitBreaker(after=breaker_after)

    def _wrapped_factory() -> EternalAgentLoop:
        inner_loop = inner_factory()
        return EternalAgentLoop(
            loop=inner_loop,
            runtime=runtime,
            breaker=breaker,
            deadline_per_turn_s=deadline_per_turn_s,
            workflow_name=workflow_name,
        )

    return _wrapped_factory


__all__ = ["make_eternal_loop", "make_eternal_loop_factory"]

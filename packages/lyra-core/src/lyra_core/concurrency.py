"""Context-aware concurrency helpers (Hermes-agent v0.12 absorption).

Background
----------
Hermes-agent v0.12 fixed a class of subtle bugs in its concurrent tool /
subagent dispatch where context-local state — request id, trace id,
session id, current `_PROVIDER_OVERRIDE` slot, the active rate-limit
bucket — silently failed to propagate from the calling thread into the
worker thread when work was submitted to a ``ThreadPoolExecutor``.

Symptoms in the wild:

- A trace started in the parent thread shows zero spans in the worker
  thread because the OTel ``contextvars.ContextVar``-backed propagator
  saw the default (empty) context.
- Provider overrides set via ``with provider_override("anthropic"):`` did
  not stick across a ``Task`` tool dispatch that ran the child agent on
  a worker thread — the child silently used the global default.
- Per-session log redaction settings reverted to defaults inside
  parallel sub-jobs.

The fix is well-known: snapshot ``contextvars.copy_context()`` in the
caller, hand the snapshot to ``ctx.run(fn, ...)`` inside the worker.

Usage
-----
Replace::

    with cf.ThreadPoolExecutor(max_workers=N) as pool:
        fut = pool.submit(worker, *args)

with::

    from lyra_core.concurrency import submit_with_context
    with cf.ThreadPoolExecutor(max_workers=N) as pool:
        fut = submit_with_context(pool, worker, *args)

The helper is a thin wrapper — there's no allocation hot path concern,
``copy_context()`` is O(1) (creates a new immutable view, doesn't copy
values).
"""

from __future__ import annotations

import concurrent.futures as cf
import contextvars
from collections.abc import Callable
from typing import Any, TypeVar

R = TypeVar("R")


def submit_with_context(
    pool: cf.Executor,
    fn: Callable[..., R],
    /,
    *args: Any,
    **kwargs: Any,
) -> cf.Future[R]:
    """Submit ``fn(*args, **kwargs)`` to ``pool`` under the caller's context.

    Snapshots :func:`contextvars.copy_context` in the calling thread
    and dispatches ``ctx.run(fn, *args, **kwargs)`` to the worker. Any
    ``ContextVar`` set in the caller (trace id, session id, provider
    override, redaction bucket, etc.) is visible in the worker — and
    any change the worker makes to a ContextVar stays scoped to the
    worker thread (the snapshot is per-task).

    Returns the same :class:`concurrent.futures.Future` shape as
    :meth:`Executor.submit`, so existing callers do not need to change
    how they read results.

    Notes
    -----
    - Safe with ``ProcessPoolExecutor``? No — pickling a Context fails.
      ``submit_with_context`` is documented as thread-pool only.
    - For asyncio's ``loop.run_in_executor``, prefer
      :func:`run_in_executor_with_context` instead.
    """
    ctx = contextvars.copy_context()
    return pool.submit(ctx.run, fn, *args, **kwargs)


def run_in_executor_with_context(
    loop: Any,
    pool: cf.Executor | None,
    fn: Callable[..., R],
    /,
    *args: Any,
) -> Any:
    """asyncio counterpart for :func:`submit_with_context`.

    Wraps ``loop.run_in_executor(pool, fn, *args)`` with a
    ``contextvars.copy_context().run`` so the worker thread sees the
    caller's contextvars. Returns whatever ``loop.run_in_executor``
    returns (an asyncio Future awaitable).

    Pass ``pool=None`` to use asyncio's default executor.
    """
    ctx = contextvars.copy_context()

    def _runner() -> R:
        return ctx.run(fn, *args)

    return loop.run_in_executor(pool, _runner)


__all__ = ["run_in_executor_with_context", "submit_with_context"]

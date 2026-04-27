"""Wave-D Task 1: ``SubagentRunner`` — the per-spawn orchestrator.

Where the older :class:`SubagentOrchestrator` (in
:mod:`.orchestrator`) is the *batch* DAG runner used by the planner,
the runner is the **single-spawn** wrapper the REPL hands to the
:class:`SubagentRegistry`. One runner per spawn, one worktree per
runner, one :class:`AgentLoop` per runner.

Why split this out from the existing pieces?

* :class:`SubagentRegistry` (Wave-A) only owns *state* (id, status,
  result, ledger) — it doesn't know how to actually drive an
  :class:`AgentLoop`.
* :class:`SubagentOrchestrator` (Wave-A) owns *batch* fan-out across
  multiple specs at once — it doesn't expose a single-shot ``run``
  hook that wraps the loop with stdio/HIR capture.
* The runner closes that gap. The registry stays the bookkeeper; the
  runner is the muscle that actually invokes the loop and tags every
  HIR event with the scope id so ``/blame`` / ``/trace`` (Wave-C T4)
  can filter to "events from sub-X" without bolting state onto
  individual call sites.

Design notes

* **TTY-free.** The runner takes a ``loop_factory`` callable instead
  of an :class:`AgentLoop` instance so tests (and the REPL) can
  inject a stub LLM without dragging the prompt_toolkit driver into
  the import graph.
* **Worktree-root configurable.** When the parent process owns a real
  ``git worktree`` manager (Wave-A
  :class:`WorktreeManager`), it can pre-allocate the path and pass
  ``worktree_root``. Tests pass a tmp_path so the runner exercises
  the full branch-free fall-back: just create
  ``<root>/<scope_id>-<token>/`` and treat *that* as the workdir.
* **HIR scope tagging.** A small helper
  (``_install_scope_tagger``) subscribes to the global hub for the
  duration of the run, augmenting every event with
  ``scope_id=<spec.scope_id>`` so downstream sinks (RingBuffer,
  ``/trace``) can filter without per-call plumbing.
* **Cancellation.** :meth:`cancel` flips a flag the next :meth:`run`
  observes and returns ``status="cancelled"`` without invoking the
  loop. Mid-run cooperative cancellation is Wave-E (the loop needs
  to start checking the flag between LLM rounds first).
"""
from __future__ import annotations

import io
import os
import uuid
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Optional

from lyra_core.agent.loop import AgentLoop, TurnResult
from lyra_core.hir.events import subscribe, unsubscribe
from lyra_core.subagent.worktree import Worktree, WorktreeError, WorktreeManager


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


SubagentStatus = Literal["ok", "failed", "cancelled"]


@dataclass
class SubagentRunSpec:
    """What the parent asks the runner to do."""

    scope_id: str
    description: str
    session_id: str | None = None  # auto-derived from scope_id when omitted


@dataclass
class SubagentRunResult:
    """What the runner hands back to the parent."""

    scope_id: str
    status: SubagentStatus
    final_text: str = ""
    error: str | None = None
    workdir: Path | None = None
    stdout: str = ""
    stderr: str = ""
    turn: TurnResult | None = None
    # Lightweight HIR snapshot (newest last) so the parent can render
    # ``/agents <id>`` without a separate query against the global ring.
    hir_events: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# The runner
# ---------------------------------------------------------------------------


class SubagentRunner:
    """Wrap one :class:`AgentLoop` invocation with worktree + capture.

    Usage::

        runner = SubagentRunner(
            loop_factory=lambda: AgentLoop(...),
            repo_root=repo_root,
            worktree_root=repo_root / ".lyra" / "worktrees",
        )
        result = runner.run(SubagentRunSpec(
            scope_id="sub-001",
            description="investigate the failing test",
        ))
    """

    def __init__(
        self,
        *,
        loop_factory: Callable[[], AgentLoop],
        repo_root: Path,
        worktree_root: Path,
        worktree_manager: Optional[WorktreeManager] = None,
        use_git_worktree: bool = True,
    ) -> None:
        self._loop_factory = loop_factory
        self.repo_root = Path(repo_root)
        self.worktree_root = Path(worktree_root)
        self._cancelled = False

        # Phase E.4: prefer a real ``git worktree add`` when the parent
        # repo is a git checkout. ``WorktreeManager`` is *constructed
        # lazily* so non-git roots (tests, tmp_paths, sandboxed envs)
        # never see a `WorktreeError` cascade — they just stay on the
        # plain ``mkdir`` fallback. Callers can short-circuit the
        # detection by passing ``use_git_worktree=False`` (handy for
        # tests that need predictable plain dirs) or by injecting a
        # pre-built ``worktree_manager``.
        self._wt_manager: WorktreeManager | None = None
        self._wt_active: dict[str, Worktree] = {}
        if worktree_manager is not None:
            self._wt_manager = worktree_manager
        elif use_git_worktree:
            try:
                self._wt_manager = WorktreeManager(self.repo_root)
            except WorktreeError:
                self._wt_manager = None
            except Exception:
                # Defensive: any other failure (missing git, permission,
                # etc.) must never break the runner's plain-dir path.
                self._wt_manager = None

    # ---- lifecycle ----------------------------------------------------

    def cancel(self) -> None:
        """Mark the runner as cancelled. Idempotent.

        A subsequent :meth:`run` short-circuits without invoking the
        loop. Once :meth:`run` has started, the cancel flag is read
        only between LLM rounds (cooperative interruption arrives
        with the agent-loop checkpoint in Wave E).
        """
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    # ---- core execution -----------------------------------------------

    def run(
        self,
        spec: SubagentRunSpec,
        *,
        cleanup_on_exit: bool = True,
    ) -> SubagentRunResult:
        """Drive a single :class:`AgentLoop` invocation under *spec*.

        Always returns a :class:`SubagentRunResult` — every error path
        is materialised into ``status``/``error`` rather than raised so
        the parent registry can record the outcome verbatim.

        ``cleanup_on_exit`` (Phase E.4) reaps the underlying git
        worktree (when one was allocated) before returning. The
        registry can pass ``False`` when it wants to keep the workdir
        around for forensic inspection of a failed scope.
        """
        if self._cancelled:
            return SubagentRunResult(
                scope_id=spec.scope_id,
                status="cancelled",
            )

        workdir = self._allocate_workdir(spec.scope_id)
        captured: list[dict] = []
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        session_id = spec.session_id or spec.scope_id

        try:
            try:
                with self._scope_tag(spec.scope_id, captured):
                    with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                        with self._chdir(workdir):
                            loop = self._loop_factory()
                            turn = loop.run_conversation(
                                spec.description, session_id=session_id
                            )
            except Exception as exc:  # AgentLoop or factory blew up
                return SubagentRunResult(
                    scope_id=spec.scope_id,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                    workdir=workdir,
                    stdout=stdout_buf.getvalue(),
                    stderr=stderr_buf.getvalue(),
                    hir_events=captured,
                )

            return SubagentRunResult(
                scope_id=spec.scope_id,
                status="ok",
                final_text=turn.final_text,
                workdir=workdir,
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
                turn=turn,
                hir_events=captured,
            )
        finally:
            if cleanup_on_exit:
                self.cleanup(spec.scope_id)

    # ---- internals ----------------------------------------------------

    def _allocate_workdir(self, scope_id: str) -> Path:
        """Allocate an isolated workdir for *scope_id*.

        Phase E.4 (v2.7) upgrades this from a plain ``mkdir`` to a
        real ``git worktree add`` call when the constructor succeeded
        in attaching a :class:`WorktreeManager`. The git path is the
        production default — it gives every subagent its own branch,
        its own checkout, and a proper ``git worktree remove`` on
        cleanup so multi-agent fan-outs can't trample one another.

        Fall-back path: when the runner was constructed in a non-git
        sandbox (tmp dirs, tests, no-git environments) or with
        ``use_git_worktree=False``, we keep the legacy
        ``<worktree_root>/<scope_id>-<token>/`` plain directory so the
        rest of the cascade — captures, chdir, scope tagging — keeps
        working unchanged.
        """
        if self._wt_manager is not None:
            try:
                wt = self._wt_manager.allocate(scope_id=scope_id)
                self._wt_active[scope_id] = wt
                return wt.path
            except WorktreeError:
                # The manager survived construction (so the parent IS a
                # git repo) but ``git worktree add`` itself failed —
                # detached HEAD on a borrowed checkout, the worktree
                # path conflicts with an existing one, etc. Fall back
                # to the plain mkdir so the run still produces a
                # workdir; the caller will see the operational warning
                # in stderr from the git invocation.
                pass

        token = uuid.uuid4().hex[:8]
        path = self.worktree_root / f"{scope_id}-{token}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cleanup(self, scope_id: str | None = None) -> None:
        """Reap worktrees this runner allocated.

        Idempotent. With ``scope_id=None`` we clean *all* live
        allocations (typical REPL exit / cron daemon shutdown). With a
        specific ``scope_id`` we only reap that one (useful when a
        single ``/spawn`` cycle wraps up).
        """
        if self._wt_manager is None:
            return
        targets = (
            [scope_id] if scope_id is not None else list(self._wt_active.keys())
        )
        for sid in targets:
            wt = self._wt_active.pop(sid, None)
            if wt is None:
                continue
            try:
                self._wt_manager.cleanup(wt)
            except Exception:
                # Cleanup must never raise out of a finally / shutdown
                # path — if git refuses to remove the worktree the
                # ``reconcile_orphans`` sweep will pick it up later.
                pass

    @contextmanager
    def _chdir(self, target: Path) -> Iterator[None]:
        """Run the loop with ``cwd = target`` and restore on exit.

        Without this, every subagent's file ops would leak back into
        the parent's working directory — a hard-to-debug correctness
        bug, and a real isolation hole for variant runs that expect
        independent worktrees. We restore the cwd in ``finally`` so a
        crash mid-loop never leaves the parent stranded in the
        worktree.

        ``os.chdir`` failures (e.g., the worktree was unlinked
        between :meth:`_allocate_workdir` and ``run``) are surfaced as
        :class:`OSError`; the outer ``try`` materialises that into
        ``status="failed"`` with the exception text intact.
        """
        prev = os.getcwd()
        os.chdir(target)
        try:
            yield
        finally:
            try:
                os.chdir(prev)
            except OSError:
                # The previous cwd may have been deleted under us
                # (rare, but happens in nested tmp_paths). Fall back
                # to the worktree root so we never raise from finally.
                os.chdir(self.worktree_root)

    @contextmanager
    def _scope_tag(
        self, scope_id: str, captured: list[dict]
    ) -> Iterator[None]:
        """Augment every HIR event with ``scope_id`` for the run's lifetime.

        Implemented as a temporary subscriber so the global hub stays
        ignorant of subagent semantics; downstream sinks just see an
        extra attribute they can filter on.
        """
        def _on_event(name: str, /, **attrs: Any) -> None:
            attrs.setdefault("scope_id", scope_id)
            captured.append({"name": name, "attrs": dict(attrs)})

        # Re-emit a tagged copy via a fresh emit pass so the global
        # RingBuffer (Wave-C T4) sees the scope id too. We do this by
        # wrapping ``emit`` for the duration of the run via a thin
        # subscriber and a re-publish hop into the same hub. To avoid
        # an emit-loop, the re-publish only runs once per top-level
        # event (we tag the event with ``_lyra_scoped`` and skip
        # re-publishing already-tagged events).
        from lyra_core.hir.events import emit as _emit

        def _scope_subscriber(name: str, /, **attrs: Any) -> None:
            if attrs.get("_lyra_scoped"):
                return  # already a re-publication; avoid recursion
            attrs2 = dict(attrs)
            attrs2["scope_id"] = scope_id
            attrs2["_lyra_scoped"] = True
            captured.append({"name": name, "attrs": attrs2})
            _emit(name, **attrs2)

        subscribe(_scope_subscriber)
        try:
            yield
        finally:
            unsubscribe(_scope_subscriber)


__all__ = [
    "SubagentRunner",
    "SubagentRunSpec",
    "SubagentRunResult",
    "SubagentStatus",
]

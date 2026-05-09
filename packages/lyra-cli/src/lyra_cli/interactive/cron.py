"""``/cron`` slash command dispatcher (hermes-agent parity).

Accepts subcommands ``list``, ``add``, ``remove``, ``pause``, ``resume``,
``run``, and ``edit``. The handler is deliberately CLI-shell-free so
the interactive session, the standalone ``lyra cron ...`` CLI, and the
scheduler daemon can share the same entry point.

Usage from the REPL::

    /cron add "every 1h" "Check feeds" --skill blogwatcher
    /cron list
    /cron pause <job_id>
    /cron remove <job_id>
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence

from lyra_core.cron.store import CronJob, CronStore

__all__ = ["CronCommandError", "handle_cron"]

CronRunner = Callable[[CronJob], object]


class CronCommandError(Exception):
    """Raised for malformed ``/cron`` invocations and unknown verbs."""


_SUBCOMMANDS = {"list", "add", "remove", "pause", "resume", "run", "edit"}


def handle_cron(
    args: Sequence[str],
    *,
    store: CronStore,
    runner: Optional[CronRunner] = None,
) -> str:
    """Dispatch a ``/cron`` invocation and return the user-visible output.

    ``runner`` is the callable invoked by ``/cron run`` to actually
    execute a job synchronously (Phase D.2). When omitted the slash
    falls back to the legacy "flag for next tick" message so older
    tests remain valid.
    """
    if not args:
        return _fmt_list(store.list())

    sub, *rest = args
    if sub not in _SUBCOMMANDS:
        raise CronCommandError(
            f"unknown cron subcommand {sub!r}; "
            f"valid: {sorted(_SUBCOMMANDS)}"
        )

    if sub == "list":
        return _fmt_list(store.list())
    if sub == "add":
        return _handle_add(rest, store)
    if sub == "remove":
        return _handle_remove(rest, store)
    if sub == "pause":
        return _handle_state(rest, store, "pause")
    if sub == "resume":
        return _handle_state(rest, store, "resume")
    if sub == "run":
        return _handle_run(rest, store, runner=runner)
    if sub == "edit":
        return _handle_edit(rest, store)

    raise CronCommandError(f"cron subcommand not wired: {sub}")  # pragma: no cover


# -- subcommand handlers ----------------------------------------------------


def _handle_add(rest: Sequence[str], store: CronStore) -> str:
    if len(rest) < 2:
        raise CronCommandError("usage: /cron add <schedule> <prompt> [--skill NAME]...")
    schedule = rest[0]
    positional: list[str] = []
    skills: list[str] = []
    name: str | None = None

    i = 1
    while i < len(rest):
        tok = rest[i]
        if tok == "--skill" and i + 1 < len(rest):
            skills.append(rest[i + 1])
            i += 2
            continue
        if tok == "--name" and i + 1 < len(rest):
            name = rest[i + 1]
            i += 2
            continue
        positional.append(tok)
        i += 1

    if not positional:
        raise CronCommandError("cron add requires a prompt")

    prompt = " ".join(positional)
    job = store.add(prompt=prompt, schedule=schedule, skills=skills, name=name)
    return f"added cron job {job.id} ({schedule})"


def _handle_remove(rest: Sequence[str], store: CronStore) -> str:
    if not rest:
        raise CronCommandError("usage: /cron remove <job_id>")
    job_id = rest[0]
    ok = store.remove(job_id)
    if not ok:
        raise CronCommandError(f"cron job not found: {job_id}")
    return f"removed cron job {job_id}"


def _handle_state(rest: Sequence[str], store: CronStore, verb: str) -> str:
    if not rest:
        raise CronCommandError(f"usage: /cron {verb} <job_id>")
    job_id = rest[0]
    try:
        if verb == "pause":
            store.pause(job_id)
        else:
            store.resume(job_id)
    except KeyError as exc:
        raise CronCommandError(f"cron job not found: {job_id}") from exc
    return f"{verb}d cron job {job_id}"


def _handle_run(
    rest: Sequence[str],
    store: CronStore,
    *,
    runner: Optional[CronRunner] = None,
) -> str:
    if not rest:
        raise CronCommandError("usage: /cron run <job_id>")
    job_id = rest[0]
    try:
        job = store.get(job_id)
    except KeyError as exc:
        raise CronCommandError(f"cron job not found: {job_id}") from exc
    if runner is None:
        return (
            f"cron job {job_id} flagged for next scheduler tick; "
            f"ensure the gateway is running to pick it up"
        )
    try:
        runner(job)
    except Exception as exc:
        raise CronCommandError(
            f"cron run failed for {job_id}: {type(exc).__name__}: {exc}"
        ) from exc
    return f"cron job {job_id} executed"


def _handle_edit(rest: Sequence[str], store: CronStore) -> str:
    if not rest:
        raise CronCommandError("usage: /cron edit <job_id> [--schedule EXPR] [--prompt TEXT]")
    job_id = rest[0]
    schedule: str | None = None
    prompt: str | None = None
    skills: list[str] | None = None
    add_skills: list[str] = []
    remove_skills: list[str] = []
    clear_skills = False

    i = 1
    while i < len(rest):
        tok = rest[i]
        if tok == "--schedule" and i + 1 < len(rest):
            schedule = rest[i + 1]
            i += 2
        elif tok == "--prompt" and i + 1 < len(rest):
            prompt = rest[i + 1]
            i += 2
        elif tok == "--skill" and i + 1 < len(rest):
            if skills is None:
                skills = []
            skills.append(rest[i + 1])
            i += 2
        elif tok == "--add-skill" and i + 1 < len(rest):
            add_skills.append(rest[i + 1])
            i += 2
        elif tok == "--remove-skill" and i + 1 < len(rest):
            remove_skills.append(rest[i + 1])
            i += 2
        elif tok == "--clear-skills":
            clear_skills = True
            i += 1
        else:
            raise CronCommandError(f"unknown flag for /cron edit: {tok!r}")

    try:
        if clear_skills:
            store.edit(job_id, skills=[])
        elif skills is not None:
            store.edit(job_id, skills=skills)
        for s in add_skills:
            store.add_skill(job_id, s)
        for s in remove_skills:
            store.remove_skill(job_id, s)
        if schedule is not None or prompt is not None:
            store.edit(job_id, schedule=schedule, prompt=prompt)
    except KeyError as exc:
        raise CronCommandError(f"cron job not found: {job_id}") from exc
    return f"updated cron job {job_id}"


# -- formatting -------------------------------------------------------------


def _fmt_list(jobs: list[CronJob]) -> str:
    if not jobs:
        return "no cron jobs scheduled"
    rows = ["id            schedule     state    prompt"]
    for j in jobs:
        rows.append(
            f"{j.id:<13} {j.schedule:<12} {j.state:<8} {j.prompt}"
        )
    return "\n".join(rows)

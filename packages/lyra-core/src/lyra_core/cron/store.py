"""JSON-backed persistence layer for Lyra ``/cron`` jobs.

Mirrors the single source of truth that hermes-agent maintains at
``~/.hermes/cron/jobs.json``. Atomic writes (write-then-rename) so a
crash mid-save cannot leave the file half-populated.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

__all__ = ["CronJob", "CronStore"]


@dataclass
class CronJob:
    id: str
    prompt: str
    schedule: str
    skills: list[str] = field(default_factory=list)
    name: str | None = None
    state: str = "active"  # "active" | "paused"
    next_run_at: str | None = None
    last_run_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CronJob":
        return cls(
            id=d["id"],
            prompt=d["prompt"],
            schedule=d["schedule"],
            skills=list(d.get("skills") or []),
            name=d.get("name"),
            state=d.get("state", "active"),
            next_run_at=d.get("next_run_at"),
            last_run_at=d.get("last_run_at"),
        )


class CronStore:
    """Atomic JSON store for :class:`CronJob` records."""

    def __init__(self, *, jobs_path: Path | str) -> None:
        self.jobs_path = Path(jobs_path)
        self.jobs_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.jobs_path.exists():
            self._write([])

    # -- public CRUD --------------------------------------------------------

    def add(
        self,
        *,
        prompt: str,
        schedule: str,
        skills: Iterable[str] = (),
        name: str | None = None,
    ) -> CronJob:
        jobs = self._read()
        job = CronJob(
            id=uuid.uuid4().hex[:12],
            prompt=prompt,
            schedule=schedule,
            skills=list(skills),
            name=name,
        )
        jobs.append(job)
        self._write(jobs)
        return job

    def list(self) -> list[CronJob]:
        return self._read()

    def get(self, job_id: str) -> CronJob:
        for j in self._read():
            if j.id == job_id:
                return j
        raise KeyError(f"cron job not found: {job_id}")

    def remove(self, job_id: str) -> bool:
        jobs = self._read()
        new_jobs = [j for j in jobs if j.id != job_id]
        if len(new_jobs) == len(jobs):
            return False
        self._write(new_jobs)
        return True

    # -- lifecycle ----------------------------------------------------------

    def pause(self, job_id: str) -> CronJob:
        return self._mutate(job_id, state="paused")

    def resume(self, job_id: str) -> CronJob:
        return self._mutate(job_id, state="active")

    def edit(
        self,
        job_id: str,
        *,
        prompt: str | None = None,
        schedule: str | None = None,
        skills: Iterable[str] | None = None,
        name: str | None = None,
    ) -> CronJob:
        fields: dict[str, Any] = {}
        if prompt is not None:
            fields["prompt"] = prompt
        if schedule is not None:
            fields["schedule"] = schedule
        if skills is not None:
            fields["skills"] = list(skills)
        if name is not None:
            fields["name"] = name
        return self._mutate(job_id, **fields)

    def add_skill(self, job_id: str, skill: str) -> CronJob:
        j = self.get(job_id)
        if skill not in j.skills:
            return self._mutate(job_id, skills=[*j.skills, skill])
        return j

    def remove_skill(self, job_id: str, skill: str) -> CronJob:
        j = self.get(job_id)
        return self._mutate(job_id, skills=[s for s in j.skills if s != skill])

    def mark_run(self, job_id: str, *, last_run_at: str, next_run_at: str) -> CronJob:
        return self._mutate(
            job_id, last_run_at=last_run_at, next_run_at=next_run_at
        )

    # -- internals ----------------------------------------------------------

    def _mutate(self, job_id: str, **fields: Any) -> CronJob:
        jobs = self._read()
        updated: CronJob | None = None
        for i, j in enumerate(jobs):
            if j.id == job_id:
                for k, v in fields.items():
                    setattr(j, k, v)
                updated = j
                jobs[i] = j
                break
        if updated is None:
            raise KeyError(f"cron job not found: {job_id}")
        self._write(jobs)
        return updated

    def _read(self) -> list[CronJob]:
        try:
            raw = self.jobs_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        if not raw.strip():
            return []
        data = json.loads(raw)
        return [CronJob.from_dict(d) for d in data]

    def _write(self, jobs: list[CronJob]) -> None:
        data = [j.to_dict() for j in jobs]
        tmp = self.jobs_path.with_suffix(self.jobs_path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.jobs_path)

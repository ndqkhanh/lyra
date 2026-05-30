"""Git hooks integration for SDLC automation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class HookEvent(StrEnum):
    PRE_COMMIT = "pre-commit"
    PRE_PUSH = "pre-push"
    POST_COMMIT = "post-commit"
    POST_CHECKOUT = "post-checkout"
    POST_MERGE = "post-merge"
    PRE_REBASE = "pre-rebase"
    COMMIT_MSG = "commit-msg"


@dataclass(frozen=True)
class HookResult:
    event: HookEvent
    passed: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class HookScript:
    event: HookEvent
    name: str
    command: str
    enabled: bool = True
    timeout_seconds: float = 30.0


class HooksManager:
    """Install, manage, and execute git hooks for SDLC automation.

    Usage::

        mgr = HooksManager(repo_path=".")
        mgr.add_hook(HookScript(HookEvent.PRE_COMMIT, "lint", "ruff check ."))
        mgr.install()
        result = mgr.run_hook(HookEvent.PRE_COMMIT)
    """

    def __init__(self, repo_path: str = ".") -> None:
        self._repo = Path(repo_path)
        self._hooks_dir = self._repo / ".git" / "hooks"
        self._scripts: dict[str, list[HookScript]] = {e.value: [] for e in HookEvent}

    def add_hook(self, script: HookScript) -> None:
        self._scripts[script.event.value].append(script)

    def remove_hook(self, event: HookEvent, name: str) -> None:
        self._scripts[event.value] = [
            s for s in self._scripts[event.value] if s.name != name
        ]

    def get_hooks(self, event: HookEvent | None = None) -> list[HookScript]:
        if event:
            return list(self._scripts[event.value])
        result: list[HookScript] = []
        for scripts in self._scripts.values():
            result.extend(scripts)
        return result

    def install(self) -> list[str]:
        installed: list[str] = []
        self._hooks_dir.mkdir(parents=True, exist_ok=True)

        for event in HookEvent:
            scripts = [s for s in self._scripts[event.value] if s.enabled]
            if not scripts:
                continue

            hook_path = self._hooks_dir / event.value
            lines = ["#!/usr/bin/env bash", "", f"# Lyra SDLC — {event.value}"]
            for s in scripts:
                lines.append(f"# Hook: {s.name}")
                lines.append(s.command)

            hook_content = "\n".join(lines) + "\n"
            hook_path.write_text(hook_content)
            hook_path.chmod(0o755)
            installed.append(event.value)

        return installed

    def run_hook(self, event: HookEvent) -> list[HookResult]:
        import time

        results: list[HookResult] = []
        scripts = [s for s in self._scripts[event.value] if s.enabled]

        for script in scripts:
            start = time.monotonic()
            try:
                proc = subprocess.run(
                    script.command,
                    shell=True, capture_output=True, text=True,
                    timeout=script.timeout_seconds,
                    cwd=str(self._repo),
                )
                duration = (time.monotonic() - start) * 1000
                results.append(
                    HookResult(
                        event=event, passed=proc.returncode == 0,
                        output=proc.stdout[:1000], error=proc.stderr[:1000],
                        duration_ms=duration,
                    )
                )
            except subprocess.TimeoutExpired:
                results.append(
                    HookResult(
                        event=event, passed=False,
                        error=f"Timed out: {script.name}",
                        duration_ms=script.timeout_seconds * 1000,
                    )
                )

        return results

    def uninstall(self, event: HookEvent | None = None) -> list[str]:
        removed: list[str] = []
        events = [event] if event else list(HookEvent)
        for e in events:
            hook_path = self._hooks_dir / e.value
            if hook_path.exists():
                hook_path.unlink()
                removed.append(e.value)
        return removed

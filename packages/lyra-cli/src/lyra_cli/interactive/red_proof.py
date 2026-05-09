"""Wave-C Task 13: ``/red-proof`` minimal pytest invoker.

Why ship this in v1.7.5?
The TDD workflow Lyra preaches ("write a failing test first") gets
fragile when the user can't *see* the failure inside the REPL. Until
now, ``/tdd-gate`` only enforces the rule by rejecting Edits; it
doesn't help you confirm you actually went RED. ``/red-proof`` closes
that loop:

    /red-proof packages/foo/tests/test_bar.py

shells out to ``pytest <target>``, captures stdout/stderr/exit-code,
and reports ``RED ✓`` when the run failed (the desired state) or
``unexpectedly passed`` when the run was GREEN (the bug we want to
catch *before* writing the implementation).

What this module deliberately does NOT do:

- It does not parse pytest's report. The single signal we need is
  the exit code; full integration with pytest's plugin protocol is
  Wave F's job.
- It does not isolate the test environment. Same interpreter, same
  install — pytest is invoked through ``sys.executable -m pytest``
  so the user's virtualenv is honoured.
- It does not silently retry on flakes. RED proof must be
  deterministic; flakes are a separate concern (``/triage flake`` in
  Wave F).
"""
from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RedProofResult:
    """Outcome of a single ``/red-proof`` invocation.

    ``passed`` is the *user-visible* verdict: ``True`` means "yes, the
    test really is RED, you have proof". ``False`` means "either the
    test passed (bad), or pytest couldn't run (worse)".

    ``exit_code`` is the raw pytest exit code, which is useful for
    downstream tooling (CI / scripting): pytest exits 0 on full GREEN,
    non-zero on collection errors / failures / errors.
    """

    passed: bool
    exit_code: int
    message: str
    stdout: str = ""
    stderr: str = ""


def run_red_proof(target: str, *, repo_root: Path) -> RedProofResult:
    """Invoke pytest against ``target`` rooted at ``repo_root``.

    The single-shot contract: exit code != 0 → RED proof confirmed.
    """
    try:
        completed = _invoke_pytest(target, repo_root=repo_root)
    except FileNotFoundError as exc:
        return RedProofResult(
            passed=False,
            exit_code=-1,
            message=f"pytest unavailable: {exc}",
        )
    except OSError as exc:
        return RedProofResult(
            passed=False,
            exit_code=-1,
            message=f"could not invoke pytest: {exc}",
        )

    if completed.returncode == 0:
        # GREEN run = the test we wanted to fail did not fail. Loud
        # signal so the user doesn't accidentally implement against a
        # passing-by-coincidence test.
        return RedProofResult(
            passed=False,
            exit_code=0,
            message=(
                f"unexpectedly GREEN: {target} passed, no RED proof. "
                "Re-check your assertion."
            ),
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    return RedProofResult(
        passed=True,
        exit_code=completed.returncode,
        message=f"RED ✓ {target} failed (exit {completed.returncode}).",
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _invoke_pytest(target: str, *, repo_root: Path) -> subprocess.CompletedProcess[str]:
    """Shell out to pytest. Split out so tests can monkeypatch us."""
    cmd = [sys.executable, "-m", "pytest", "-x", "-q", target]
    return subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def render(result: RedProofResult, *, target: str) -> str:
    """One-line + trace summary for the slash command output channel.

    Keeping the renderer here (rather than in ``output.py``) makes the
    module fully self-contained: a script can call ``run_red_proof``
    + ``render`` without touching ``InteractiveSession``.
    """
    head = result.message
    detail = ""
    if result.stdout or result.stderr:
        snippet = (result.stdout or result.stderr).strip().splitlines()[-6:]
        detail = "\n".join(snippet)
    return f"{head}\n{detail}".strip()


__all__ = ["RedProofResult", "run_red_proof", "render"]

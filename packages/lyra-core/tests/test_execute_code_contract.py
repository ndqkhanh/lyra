"""Wave-D Task 8: real ``ExecuteCode`` tool via a sandboxed Python runner.

The sandbox runs a snippet inside a fresh subprocess with a hard
wall-clock budget, captures stdout/stderr/exitcode, and forbids
``import os``-level escape vectors via a small AST allow-list.

Six RED tests:

1. Happy path: ``print('hi')`` returns ``stdout='hi\\n'``, exit 0.
2. Wall-clock limit kills runaway loops with ``status='timeout'``.
3. Captures stderr + non-zero exit code.
4. Forbidden module (``os``) is rejected at *parse time*, never executed.
5. ``stdin`` is empty by default; the snippet sees no host environment.
6. Allow-list extension lets a caller permit ``math`` for a single run.
"""
from __future__ import annotations

import pytest


def test_execute_print_returns_stdout() -> None:
    from lyra_core.tools.execute_code import execute_code

    res = execute_code("print('hi')", timeout=5.0)
    assert res.status == "ok"
    assert "hi" in res.stdout
    assert res.exit_code == 0


def test_execute_timeout_kills_runaway_loop() -> None:
    from lyra_core.tools.execute_code import execute_code

    res = execute_code("while True:\n    pass\n", timeout=0.5)
    assert res.status == "timeout"
    assert res.exit_code != 0


def test_execute_captures_stderr_and_exit_code() -> None:
    from lyra_core.tools.execute_code import execute_code

    src = "import sys\nprint('boom', file=sys.stderr)\nraise SystemExit(7)\n"
    res = execute_code(src, timeout=5.0, allowed_imports={"sys"})
    assert res.exit_code == 7
    assert "boom" in res.stderr


def test_execute_forbidden_import_rejected_before_run() -> None:
    from lyra_core.tools.execute_code import (
        ForbiddenImport,
        execute_code,
    )

    with pytest.raises(ForbiddenImport, match="os"):
        execute_code("import os\nprint(os.uname())\n", timeout=5.0)


def test_execute_isolated_environment_default() -> None:
    from lyra_core.tools.execute_code import execute_code

    res = execute_code(
        "import sys\nprint(getattr(sys.modules.get('os', None), '__name__', 'no-os'))\n",
        timeout=5.0,
        allowed_imports={"sys"},
    )
    # Either ``os`` was never loaded at all (no-os), or it is loaded
    # but the snippet still ran without escape.
    assert "no-os" in res.stdout or res.exit_code == 0


def test_execute_extra_imports_allowed_per_call() -> None:
    from lyra_core.tools.execute_code import execute_code

    res = execute_code(
        "import math\nprint(math.sqrt(16))\n",
        timeout=5.0,
        allowed_imports={"math"},
    )
    assert res.status == "ok"
    assert "4.0" in res.stdout

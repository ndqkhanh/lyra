"""Wave-D Task 10: ``~/.lyra/tools/<name>.py`` + ``@tool`` decorator.

A user drops a Python file in ``~/.lyra/tools/`` (or any other path
they hand to ``load_user_tools``) and decorates one-or-more callables
with ``@tool``. The loader returns a dict ``{tool_name: ToolDescriptor}``
the registry can plug into an :class:`AgentLoop`.

Six RED tests:

1. Empty / missing dir loads zero tools (no error).
2. A file that decorates one function exposes it by ``@tool``'s name.
3. ``@tool(name='ping')`` overrides the function name.
4. ``description`` arg is captured for ``/tools`` to render.
5. ``risk='destructive'`` is captured (used by the permission stack).
6. A file that raises at import time is recorded in ``errors`` —
   the loader never raises.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _write(tmp: Path, name: str, body: str) -> Path:
    path = tmp / name
    path.write_text(body, encoding="utf-8")
    return path


def test_loader_handles_missing_dir(tmp_path: Path) -> None:
    from lyra_core.tools.user_tools import load_user_tools

    bundle = load_user_tools(user_dir=tmp_path / "nope")
    assert bundle.tools == {}
    assert bundle.errors == []


def test_loader_picks_up_decorated_callable(tmp_path: Path) -> None:
    from lyra_core.tools.user_tools import load_user_tools

    _write(
        tmp_path,
        "echo.py",
        "from lyra_core.tools.user_tools import tool\n"
        "\n"
        "@tool(description='echo the text back')\n"
        "def echo(text: str = '') -> dict:\n"
        "    return {'echoed': text}\n",
    )
    bundle = load_user_tools(user_dir=tmp_path)
    assert "echo" in bundle.tools
    desc = bundle.tools["echo"]
    assert desc.fn(text="hi") == {"echoed": "hi"}
    assert desc.description == "echo the text back"


def test_loader_honours_explicit_name(tmp_path: Path) -> None:
    from lyra_core.tools.user_tools import load_user_tools

    _write(
        tmp_path,
        "ping.py",
        "from lyra_core.tools.user_tools import tool\n"
        "\n"
        "@tool(name='ping')\n"
        "def _ping(_: str = '') -> dict:\n"
        "    return {'ok': True}\n",
    )
    bundle = load_user_tools(user_dir=tmp_path)
    assert "ping" in bundle.tools


def test_loader_captures_risk_and_description(tmp_path: Path) -> None:
    from lyra_core.tools.user_tools import load_user_tools

    _write(
        tmp_path,
        "danger.py",
        "from lyra_core.tools.user_tools import tool\n"
        "\n"
        "@tool(name='wipe', description='delete tmpdir', risk='destructive')\n"
        "def wipe() -> dict:\n"
        "    return {'ok': True}\n",
    )
    bundle = load_user_tools(user_dir=tmp_path)
    desc = bundle.tools["wipe"]
    assert desc.risk == "destructive"
    assert desc.description == "delete tmpdir"


def test_loader_records_import_errors_without_raising(tmp_path: Path) -> None:
    from lyra_core.tools.user_tools import load_user_tools

    _write(
        tmp_path,
        "bad.py",
        "raise RuntimeError('boom-at-import')\n",
    )
    bundle = load_user_tools(user_dir=tmp_path)
    assert bundle.tools == {}
    assert any("bad" in e for e in bundle.errors)


def test_loader_skips_non_python_files(tmp_path: Path) -> None:
    from lyra_core.tools.user_tools import load_user_tools

    (tmp_path / "README.md").write_text("not a tool", encoding="utf-8")
    (tmp_path / ".hidden.py").write_text("# hidden", encoding="utf-8")
    bundle = load_user_tools(user_dir=tmp_path)
    assert bundle.tools == {}

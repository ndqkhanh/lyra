"""Phase I (v3.0.0): ``/toolsets`` — hermes-agent parity.

Locked surface:

1. ``/toolsets`` lists every registered bundle with a tool preview.
2. ``/toolsets show <name>`` enumerates every tool in that bundle.
3. ``/toolsets apply <name>`` records the bundle on the session and
   reports the applied / skipped diff.
4. ``/toolsets show ghost`` and ``/toolsets apply ghost`` raise a
   friendly "unknown toolset" message instead of crashing.
5. The default active toolset is ``"default"``.
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def test_toolsets_list(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/toolsets")
    text = out.output.lower()
    for name in ("default", "safe", "research", "coding", "ops"):
        assert name in text
    assert "active: default" in text


def test_toolsets_show_named(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/toolsets show safe")
    text = out.output
    assert "safe" in text.lower()
    assert "Read" in text
    assert "Bash" not in text  # safe excludes destructive shells


def test_toolsets_show_unknown_is_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/toolsets show ghost")
    assert "unknown toolset" in out.output.lower()


def test_toolsets_apply_records_active(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/toolsets apply safe")
    assert s.active_toolset == "safe"
    assert "applied toolset 'safe'" in out.output.lower()
    assert "Read" in out.output
    assert "permissions/MCP gates" in out.output


def test_toolsets_apply_unknown_is_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/toolsets apply ghost")
    assert "unknown toolset" in out.output.lower()
    assert s.active_toolset == "default"


def test_toolsets_usage_hint(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/toolsets nonsense")
    assert "usage" in out.output.lower()

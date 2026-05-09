"""Phase I (v3.0.0): in-REPL ``/init`` — opencode parity.

Locked surface:

1. Running ``/init`` against a fresh repo writes ``SOUL.md`` and
   ``.lyra/policy.yaml`` from the packaged templates.
2. The ``.lyra/`` state / plans / sessions directories are ensured.
3. A second ``/init`` is idempotent — neither file is rewritten.
4. ``/init force`` overwrites both files unconditionally.
5. The output enumerates what was written, what was skipped, and
   suggests the canonical follow-up commands.
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def test_init_writes_soul_and_policy(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/init")
    assert (tmp_path / "SOUL.md").is_file()
    assert (tmp_path / ".lyra" / "policy.yaml").is_file()
    assert (tmp_path / ".lyra").is_dir()
    text = out.output.lower()
    assert "soul.md" in text
    assert "policy.yaml" in text
    assert "/policy review" in out.output


def test_init_is_idempotent(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("/init")
    soul_first = (tmp_path / "SOUL.md").read_text()
    (tmp_path / "SOUL.md").write_text(soul_first + "\n# user edit\n")
    out = s.dispatch("/init")
    assert "skipped soul.md" in out.output.lower()
    assert (tmp_path / "SOUL.md").read_text().endswith("# user edit\n")


def test_init_force_overwrites(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("/init")
    (tmp_path / "SOUL.md").write_text("# stub\n")
    out = s.dispatch("/init force")
    text = (tmp_path / "SOUL.md").read_text()
    assert text != "# stub\n", "force must rewrite the template"
    assert "wrote" in out.output.lower()


def test_init_creates_state_dirs(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("/init")
    assert (tmp_path / ".lyra" / "plans").is_dir()
    assert (tmp_path / ".lyra" / "sessions").is_dir()

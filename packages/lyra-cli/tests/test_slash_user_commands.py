"""Phase I (v3.0.0): user-authored markdown slash commands (opencode parity).

Locked surface:

1. Markdown files under ``<repo>/.lyra/commands/*.md`` register as
   slash commands. Frontmatter ``description``, ``args_hint``, and
   ``aliases`` are honoured.
2. Body text is rendered with ``{{args}}`` substitution and dispatched
   as a plain-text turn.
3. ``/commands`` lists every loaded user command.
4. ``/commands reload`` re-scans the directory.
5. Built-ins shadow user commands (a user file named ``init.md`` cannot
   shadow ``/init``).
6. Aliases route to the same body.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession
from lyra_cli.interactive.user_commands import (
    expand_aliases,
    load_user_commands,
)


def _drop(repo: Path, name: str, body: str) -> Path:
    cmds = repo / ".lyra" / "commands"
    cmds.mkdir(parents=True, exist_ok=True)
    p = cmds / name
    p.write_text(body, encoding="utf-8")
    return p


def test_loader_parses_frontmatter(tmp_path: Path) -> None:
    _drop(
        tmp_path,
        "ship.md",
        "---\n"
        "description: ship a release\n"
        "args_hint: <tag>\n"
        "aliases: [release, deploy]\n"
        "---\n"
        "Ship release {{args}} now.\n",
    )
    cmds = load_user_commands(tmp_path / ".lyra" / "commands")
    assert "ship" in cmds
    cmd = cmds["ship"]
    assert cmd.description == "ship a release"
    assert cmd.args_hint == "<tag>"
    assert cmd.aliases == ("release", "deploy")
    rendered = cmd.render("v1.2.3")
    assert "Ship release v1.2.3 now." in rendered


def test_loader_skips_underscore_and_dotfiles(tmp_path: Path) -> None:
    _drop(tmp_path, "_draft.md", "draft\n")
    _drop(tmp_path, ".secret.md", "secret\n")
    _drop(tmp_path, "valid.md", "ok\n")
    cmds = load_user_commands(tmp_path / ".lyra" / "commands")
    assert set(cmds) == {"valid"}


def test_loader_normalises_underscore_to_hyphen(tmp_path: Path) -> None:
    _drop(tmp_path, "release_notes.md", "ok\n")
    cmds = load_user_commands(tmp_path / ".lyra" / "commands")
    assert "release-notes" in cmds


def test_expand_aliases_routes_to_same_command(tmp_path: Path) -> None:
    _drop(
        tmp_path,
        "x.md",
        "---\naliases: [y, z]\n---\nbody\n",
    )
    cmds = load_user_commands(tmp_path / ".lyra" / "commands")
    flat = expand_aliases(cmds)
    assert flat["x"] is flat["y"] is flat["z"]


def test_dispatch_runs_user_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _drop(
        tmp_path,
        "echo.md",
        "---\ndescription: echo back\n---\nplease echo {{args}}\n",
    )
    captured: list[str] = []

    s = InteractiveSession(repo_root=tmp_path)

    def _capture(self, line):  # type: ignore[no-untyped-def]
        from lyra_cli.interactive.session import CommandResult

        captured.append(line)
        return CommandResult(output=f"plain: {line}")

    monkeypatch.setattr(InteractiveSession, "_dispatch_plain", _capture, raising=True)
    out = s.dispatch("/echo HELLO")
    assert captured and captured[-1].strip() == "please echo HELLO"
    assert "plain: please echo HELLO" in out.output


def test_dispatch_unknown_user_command_is_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/notinstalled")
    assert "unknown command" in out.output.lower()


def test_user_commands_cannot_shadow_builtins(tmp_path: Path) -> None:
    _drop(
        tmp_path,
        "init.md",
        "---\ndescription: malicious init\n---\nDO NOT RUN\n",
    )
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/init")
    # Built-in /init scaffolds files; a hijacked user version would
    # fall into _dispatch_plain instead.
    assert (tmp_path / "SOUL.md").is_file()
    assert "DO NOT RUN" not in out.output


def test_slash_commands_lists_user_commands(tmp_path: Path) -> None:
    _drop(
        tmp_path,
        "ship.md",
        "---\ndescription: ship\n---\nship {{args}}\n",
    )
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/user-commands")
    assert "/ship" in out.output
    assert "ship" in out.output.lower()


def test_slash_commands_reload_picks_up_new_files(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/user-commands")
    assert "no user commands" in out.output.lower()
    _drop(
        tmp_path,
        "fresh.md",
        "---\ndescription: fresh\n---\nfresh body\n",
    )
    out = s.dispatch("/user-commands reload")
    assert "1" in out.output
    out = s.dispatch("/user-commands")
    assert "/fresh" in out.output


def test_slash_user_cmds_alias(tmp_path: Path) -> None:
    _drop(
        tmp_path,
        "ship.md",
        "---\ndescription: ship\n---\nship\n",
    )
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/user-cmds")
    assert "/ship" in out.output

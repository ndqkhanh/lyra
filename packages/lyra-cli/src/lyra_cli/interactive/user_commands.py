"""User-authored slash commands — opencode parity (Phase I, v3.0.0).

Drops markdown files into ``<repo>/.lyra/commands/`` and the REPL will
expose them as first-class slash commands. Each file is parsed as:

* Optional YAML-ish frontmatter delimited by ``---``:

  - ``description: short help text``
  - ``args_hint: [optional]``
  - ``aliases: [a, b]``

* Markdown body — used as the LLM-bound prompt. ``{{args}}`` is the
  literal arguments string the user typed after the command name.
  Any other ``{{name}}`` placeholders are left untouched so users
  can document them in the body itself.

When the user invokes ``/<name> <args>`` the rendered body is fed
back through the *plain-text* prompt path (i.e. the same path a
normal chat message takes) so the LLM sees it as the next user turn.
This is a deliberately minimal contract: no nested slash commands,
no recursive expansion, no template DSL — exactly opencode's
behaviour, and it keeps the user-extension surface tiny.

Files whose name starts with ``_`` or ``.`` are ignored. ``.md``
extension is required. Filenames are normalised to lowercase ASCII;
``.lyra/commands/release-notes.md`` registers ``/release-notes``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<head>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)
_NAME_RE = re.compile(r"^[a-z][a-z0-9\-]*$")


@dataclass(frozen=True)
class UserCommand:
    """One markdown-defined slash command.

    Frozen for the same reason :class:`CommandSpec` is — the registry
    is immutable post-load; if you need a new one, drop another file.
    """

    name: str
    description: str
    args_hint: str
    aliases: tuple[str, ...]
    body: str
    source: Path

    def render(self, args: str) -> str:
        """Substitute ``{{args}}`` with the user-supplied tail."""
        return self.body.replace("{{args}}", args.strip())


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return ``(meta, body)``. No frontmatter → ``({}, text)``.

    The parser is intentionally trivial — we accept ``key: value``
    lines, ignore comments / blank lines, and split YAML-ish list
    syntax (``[a, b, c]``) by hand. Anything richer should live as
    a real Python plugin, not as a markdown command.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for raw in match.group("head").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip()
    return meta, match.group("body")


def _normalise_name(stem: str) -> str | None:
    candidate = stem.strip().lower().replace("_", "-")
    if not _NAME_RE.match(candidate):
        return None
    return candidate


def load_user_commands(commands_dir: Path) -> dict[str, UserCommand]:
    """Scan ``commands_dir`` for ``*.md`` files and build a registry.

    Returns ``{name: UserCommand}``. Aliases are *not* expanded into
    extra keys — call :func:`expand_aliases` for that. Errors are
    swallowed: a malformed file is skipped (with no logging) so a
    single typo can't break the REPL.
    """
    if not commands_dir.is_dir():
        return {}
    out: dict[str, UserCommand] = {}
    for path in sorted(commands_dir.glob("*.md")):
        if path.name.startswith((".", "_")):
            continue
        name = _normalise_name(path.stem)
        if name is None:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = _parse_frontmatter(text)
        description = meta.get("description") or f"user command from {path.name}"
        args_hint = meta.get("args_hint", "")
        aliases_raw = meta.get("aliases", "")
        aliases = _split_aliases(aliases_raw)
        out[name] = UserCommand(
            name=name,
            description=description,
            args_hint=args_hint,
            aliases=aliases,
            body=body.strip("\n"),
            source=path,
        )
    return out


def _split_aliases(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    cleaned = raw.strip().strip("[]")
    if not cleaned:
        return ()
    parts = [p.strip().strip("'").strip('"') for p in cleaned.split(",")]
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        norm = _normalise_name(part)
        if norm is not None:
            out.append(norm)
    return tuple(out)


def expand_aliases(commands: dict[str, UserCommand]) -> dict[str, UserCommand]:
    """Return a flat ``{name_or_alias: UserCommand}`` map.

    Aliases overwrite earlier entries on collision — same precedence
    rule as built-in :data:`SLASH_COMMANDS` (last writer wins). The
    caller still resolves built-ins first, so a user alias can never
    shadow a kernel command.
    """
    out: dict[str, UserCommand] = dict(commands)
    for cmd in commands.values():
        for alias in cmd.aliases:
            out[alias] = cmd
    return out


def default_commands_dir(repo_root: Path) -> Path:
    """Conventional location: ``<repo>/.lyra/commands``."""
    return repo_root / ".lyra" / "commands"


__all__ = [
    "UserCommand",
    "default_commands_dir",
    "expand_aliases",
    "load_user_commands",
]

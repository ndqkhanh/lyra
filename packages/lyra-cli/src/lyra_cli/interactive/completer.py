"""prompt_toolkit command completer — slash + ``@file`` + ``#skill``.

Kept isolated so the pure ``session`` module never imports prompt_toolkit.
The driver only instantiates this in TTY mode — non-TTY runs never go
through the completer path.

Four trigger surfaces:

- ``/`` opens the slash-command palette with one-line descriptions and
  alias hints (what makes ``/`` feel like Claude Code's command
  palette rather than bare autocomplete).
- ``/<cmd> <space>`` switches to a *subcommand* palette when the
  resolved spec exposes ``subcommands`` (or its ``args_hint`` matches
  the ``[a|b|c]`` auto-extract pattern). Borrowed from hermes-agent's
  ``COMMAND_REGISTRY``: the registry is the single source of truth, so
  adding a subcommand to a CommandSpec automatically lights up here.
- ``@`` opens an in-repo path picker — the foundation of
  Claude-Code-style file mentions. Walks ``repo_root`` lazily and caps
  at ``_PATH_LIMIT`` so huge monorepos don't freeze the prompt.
- ``#`` reserved for skill-pack mentions (``#atomic-skills``). We
  surface the shipped packs today; ``lyra-skills`` will extend
  this once the router exposes installed skills at runtime.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from .session import (
    SLASH_COMMANDS,
    _SHIPPED_SKILL_PACKS,
    command_spec,
    slash_description,
    subcommands_for,
)


# Hard limit so the completer never walks a 100k-file monorepo.
_PATH_LIMIT = 200

# Skip directories that are large, uninteresting, or sensitive.
_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cursor",
        "dist",
        "build",
        ".next",
        ".turbo",
        ".lyra",
    }
)


class SlashCompleter(Completer):
    """Multi-prefix completer (``/`` slash · ``@`` path · ``#`` skill)."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root

    def get_completions(
        self, document: Document, complete_event: object
    ) -> Iterable[Completion]:
        text = document.text_before_cursor
        last_token = _last_token(text)

        # Subcommand palette: when the line is ``/<cmd> [stem]`` (one or
        # more chars after the cmd, including empty stem after a space),
        # delegate to the command's subcommand list. Falls through to the
        # slash palette if the command doesn't have any.
        if text.startswith("/") and (last_token == "" or not last_token.startswith("/")):
            for sub in self._subcommand_completions(text, last_token):
                yield sub
            return

        if last_token.startswith("/") and text.startswith("/"):
            yield from self._slash_completions(last_token)
            return

        if last_token.startswith("@"):
            yield from self._path_completions(last_token)
            return

        if last_token.startswith("#"):
            yield from self._skill_completions(last_token)
            return

    # ---- /slash ----------------------------------------------------------

    def _slash_completions(self, token: str) -> Iterable[Completion]:
        stem = token[1:]
        for name in sorted(SLASH_COMMANDS):
            if not name.startswith(stem):
                continue
            spec = command_spec(name)
            if spec is None or spec.name != name:
                # Skip alias entries here; they re-render below the
                # canonical command with an "alias" tag in the meta column.
                continue
            meta = slash_description(name)
            if spec.aliases:
                meta = f"{meta}  ⟂ {', '.join('/' + a for a in spec.aliases)}"
            yield Completion(
                name,
                start_position=-len(stem),
                display=f"/{name}",
                display_meta=meta,
            )

    # ---- /<cmd> <subcommand> --------------------------------------------

    def _subcommand_completions(
        self, text: str, stem: str
    ) -> Iterable[Completion]:
        """Surface registered subcommands once the user has picked a /cmd."""
        # Resolve the command name: everything after the first ``/`` up to
        # the first space. ``/effort med`` → name="effort", stem="med".
        without_slash = text[1:]
        space_idx = without_slash.find(" ")
        if space_idx == -1:
            # No space yet — handled by _slash_completions, not us.
            return
        cmd_name = without_slash[:space_idx].lower()
        spec = command_spec(cmd_name)
        if spec is None:
            return
        subs = subcommands_for(cmd_name)
        if not subs:
            return
        for sub in subs:
            if stem and not sub.startswith(stem.lower()):
                continue
            yield Completion(
                sub,
                start_position=-len(stem),
                display=sub,
                display_meta=f"sub-arg of /{spec.name}",
            )

    # ---- @file path -------------------------------------------------------

    def _path_completions(self, token: str) -> Iterable[Completion]:
        if self.repo_root is None:
            return
        stem = token[1:]
        stem_lower = stem.lower()
        count = 0
        for rel in _walk_repo(self.repo_root):
            if count >= _PATH_LIMIT:
                break
            if stem and stem_lower not in rel.lower():
                continue
            count += 1
            yield Completion(
                rel,
                start_position=-len(stem),
                display=f"@{rel}",
                display_meta="file",
            )

    # ---- #skill ----------------------------------------------------------

    def _skill_completions(self, token: str) -> Iterable[Completion]:
        stem = token[1:].lower()
        for name, desc in _SHIPPED_SKILL_PACKS:
            if stem and stem not in name.lower():
                continue
            yield Completion(
                name,
                start_position=-len(stem),
                display=f"#{name}",
                display_meta=desc,
            )


def _last_token(text: str) -> str:
    """Return the last whitespace-delimited token (empty string if none)."""
    if not text:
        return ""
    if text[-1].isspace():
        return ""
    for sep in (" ", "\t", "\n"):
        idx = text.rfind(sep)
        if idx != -1:
            return text[idx + 1 :]
    return text


def _walk_repo(root: Path) -> Iterable[str]:
    """Yield repo-relative paths as POSIX strings, skipping noisy dirs."""
    root = root.resolve()
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name in _IGNORE_DIRS or entry.name.startswith("."):
                    # Still allow hidden files users might reference (e.g.
                    # `.github`), but prune the big hidden dirs above.
                    if entry.name in _IGNORE_DIRS:
                        continue
                stack.append(entry)
                continue
            try:
                rel = entry.relative_to(root)
            except ValueError:
                continue
            yield rel.as_posix()

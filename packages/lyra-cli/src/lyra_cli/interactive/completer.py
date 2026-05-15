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

from collections.abc import Callable, Iterable
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

        # Subcommand / argument palette: when the line is ``/<cmd> [stem]``
        # (one or more chars after the cmd, including empty stem after a
        # space), first try the command's subcommand list. If nothing
        # matches there, fall through to a per-command argument completer
        # (e.g. ``/model deepseek-chat`` surfaces alias slugs). This is
        # the v3.5.x fix for the empty-menu UX bug — before, the branch
        # always returned, leaving ``/model `` with zero completions.
        if text.startswith("/") and (last_token == "" or not last_token.startswith("/")):
            yielded_any = False
            for sub in self._subcommand_completions(text, last_token):
                yielded_any = True
                yield sub
            if yielded_any:
                return
            yield from self._argument_completions(text, last_token)
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

    # ---- /<cmd> <argument> ----------------------------------------------

    def _argument_completions(
        self, text: str, stem: str
    ) -> Iterable[Completion]:
        """Per-command argument suggestions when no subcommand matched.

        Dispatches by the resolved command name (canonicalised through
        ``command_spec`` so ``/llm`` and ``/model`` share a handler).
        Returns nothing for commands that don't register an arg
        completer — the menu just stays empty rather than crashing.
        """
        without_slash = text[1:]
        space_idx = without_slash.find(" ")
        if space_idx == -1:
            return
        raw_name = without_slash[:space_idx].lower()
        spec = command_spec(raw_name)
        cmd_name = spec.name if spec is not None else raw_name
        handler = _ARG_COMPLETERS.get(cmd_name)
        if handler is None:
            return
        yield from handler(stem)

    # ---- @file path -------------------------------------------------------

    def _path_completions(self, token: str) -> Iterable[Completion]:
        if self.repo_root is None:
            return
        stem = token[1:]
        stem_lower = stem.lower()
        count = 0
        for rel, is_dir in _walk_repo(self.repo_root):
            if count >= _PATH_LIMIT:
                break
            if stem and stem_lower not in rel.lower():
                continue
            count += 1
            display_path = f"{rel}/" if is_dir else rel
            yield Completion(
                display_path,
                start_position=-len(stem),
                display=f"@{display_path}",
                display_meta="dir" if is_dir else "file",
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


def _model_arg_completions(stem: str) -> Iterable[Completion]:
    """Surface canonical model slugs for ``/model`` and ``/llm``.

    Pulls from :data:`lyra_core.providers.aliases.DEFAULT_ALIASES` so
    new aliases surface in the menu without a code change here.
    """
    stem_lower = stem.lower()
    items: list[tuple[str, str]] = []

    # Slot syntax — ``/model fast=<slug>`` and ``/model smart=<slug>``
    # let the user re-pin the two-tier model split (v2.7.1 pattern).
    # These appear in the dropdown so the user discovers the syntax
    # without having to read the docs.
    for slot in ("fast=", "smart="):
        if not stem or slot.startswith(stem_lower):
            items.append((slot, "slot"))

    # Canonical slugs + every registered alias name. ``canonical_slugs``
    # alone returns only the *target* of each alias (``deepseek-chat``)
    # which means the friendly user-facing forms users actually type
    # (``deepseek-v4-flash`` / ``deepseek-v4-pro`` / ``opus`` / ``sonnet``
    # / ``haiku``) never reach the dropdown. We walk the full alias map
    # so every name registered in :func:`_seed` is reachable via
    # type-ahead, with a ``model`` / ``alias`` meta tag so the user
    # sees which is the canonical slug.
    try:
        from lyra_core.providers.aliases import DEFAULT_ALIASES
    except Exception:
        canonical: set[str] = set()
        alias_to_slug: dict[str, str] = {}
    else:
        canonical = set(DEFAULT_ALIASES.canonical_slugs())
        alias_to_slug = {
            name: entry.slug for name, entry in DEFAULT_ALIASES._aliases.items()
        }

    # Canonical slugs first so the picker leads with the API-true names.
    for slug in sorted(canonical):
        if stem and stem_lower not in slug.lower():
            continue
        items.append((slug, "model"))
    # Aliases that don't already appear as canonical (so ``deepseek-chat``
    # doesn't render twice but ``deepseek-v4-flash`` does).
    for name, slug in sorted(alias_to_slug.items()):
        if name in canonical:
            continue
        if stem and stem_lower not in name.lower():
            continue
        items.append((name, f"alias → {slug}"))

    # Provider-prefixed forms — the explicit way to override auto.
    for prov in ("anthropic:", "openai:", "deepseek:", "gemini:", "ollama:"):
        if not stem or prov.startswith(stem_lower) or stem_lower in prov:
            items.append((prov, "provider"))

    seen: set[str] = set()
    for text, meta in items:
        if text in seen:
            continue
        seen.add(text)
        yield Completion(
            text,
            start_position=-len(stem),
            display=text,
            display_meta=meta,
        )


_ARG_COMPLETERS: dict[str, Callable[[str], Iterable[Completion]]] = {
    "model": _model_arg_completions,
    "llm": _model_arg_completions,
}


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


def _walk_repo(root: Path) -> Iterable[tuple[str, bool]]:
    """Yield ``(rel_posix, is_dir)`` pairs, skipping noisy dirs.

    Both files and directories surface so the ``@`` palette can offer
    folder mentions (e.g. ``@src/lyra_cli/interactive/``). Hidden dirs
    listed in :data:`_IGNORE_DIRS` are pruned entirely.
    """
    root = root.resolve()
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            try:
                rel = entry.relative_to(root).as_posix()
            except ValueError:
                continue
            if entry.is_dir():
                if entry.name in _IGNORE_DIRS:
                    continue
                yield rel, True
                stack.append(entry)
                continue
            yield rel, False

"""Inline auto-suggestion for the interactive REPL.

Claude Code, fish shell, and hermes-agent all show ghost-text previews
as the user types — the next-likely continuation rendered in dim grey
at the end of the buffer, accepted with ``→`` or ``Ctrl-E``. It's the
single UX detail that makes a CLI feel alive; the dropdown completer
is great when you're *browsing*, but 90 % of the time you just want
the right thing to appear under your cursor while you type.

This module assembles a :class:`~prompt_toolkit.auto_suggest.AutoSuggest`
that fuses three sources, in order of priority:

1. **Session history** — ``/<cmd>`` then ``/<cmd> <same-args>`` you've
   just typed are by far the most common auto-suggest win. We walk
   the history newest-first (like fish) and take the first entry that
   startswith the current buffer.
2. **Slash command registry** — for fresh sessions where history is
   empty, we auto-complete to the *canonical* (non-alias) slash name
   that matches the current prefix. Typing ``/co`` previews
   ``/compact``, typing ``/exp`` previews ``/export``.
3. **Subcommands** — once the user has typed ``/<cmd> `` with a
   trailing space, we preview the first subcommand declared in the
   spec's ``args_hint`` (``/mode `` → ``/mode plan``, ``/effort `` →
   ``/effort low``). This stacks with the completer — the dropdown
   still shows every option, but you can accept the first one
   without opening it.

Why not just use prompt_toolkit's ``AutoSuggestFromHistory``? Because
that's (1) alone — it's silent on fresh sessions and doesn't know
about our registry. This class wraps the built-in for priority 1 and
adds priorities 2-3 on top.

The :class:`CommandAutoSuggest` is intentionally stateless (pulls from
the registry at suggest-time), so commands added at runtime via a
future plugin hook just work.
"""
from __future__ import annotations

from prompt_toolkit.auto_suggest import (
    AutoSuggest,
    AutoSuggestFromHistory,
    Suggestion,
)
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document

from .session import SLASH_COMMANDS, command_spec, subcommands_for


class CommandAutoSuggest(AutoSuggest):
    """Ghost-text suggester layering registry + subcommands over history."""

    def __init__(self) -> None:
        # Delegates history-based suggestions to the prompt_toolkit built-in.
        # We only *override* when history is silent or when a slash-specific
        # suggestion is strictly better (e.g. a fresh session with no history
        # where the user starts typing ``/co``).
        self._history = AutoSuggestFromHistory()

    # ------------------------------------------------------------------
    # AutoSuggest API
    # ------------------------------------------------------------------

    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Suggestion | None:
        text = document.text
        # Empty buffer: nothing to suggest.
        if not text:
            return None

        # 1) History wins when it has a hit — it's the most relevant
        #    signal ("what did I type last time?") and matches fish /
        #    Claude Code behaviour. Only fall through when it's silent.
        hist_suggestion = self._history.get_suggestion(buffer, document)
        if hist_suggestion is not None:
            return hist_suggestion

        # 2/3) Slash-prefix hints.
        if text.startswith("/"):
            return self._slash_suggestion(text)
        return None

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _slash_suggestion(self, text: str) -> Suggestion | None:
        """Slash-prefix heuristic.

        ``text`` is the full buffer, e.g. ``"/co"`` or ``"/mode "``.
        Returns the *completion* (what to append), not the full final
        command — prompt_toolkit concatenates it at the cursor.
        """
        without_slash = text[1:]
        # Subcommand preview kicks in after a trailing space.
        if " " in without_slash:
            return self._subcommand_suggestion(text)

        # Otherwise: canonical-command preview. We sort so the behaviour
        # is deterministic regardless of dict insertion order; match the
        # *first* canonical name (skip alias entries) that starts with
        # the typed stem.
        stem = without_slash
        for name in sorted(SLASH_COMMANDS):
            spec = command_spec(name)
            if spec is None or spec.name != name:
                continue  # alias — the canonical will show up on its own turn
            if name.startswith(stem) and name != stem:
                return Suggestion(name[len(stem):])
        return None

    def _subcommand_suggestion(self, text: str) -> Suggestion | None:
        """Preview the first subcommand after ``/<cmd> <partial>``."""
        body = text[1:]  # drop the leading /
        cmd_part, _, stem = body.partition(" ")
        cmd_name = cmd_part.lower()
        subs = subcommands_for(cmd_name)
        if not subs:
            return None
        stem = stem.lower()
        # Preserve the registry's declared order so ``/mode `` shows the
        # most common first-choice (plan) rather than alphabetical.
        for sub in subs:
            if stem and not sub.startswith(stem):
                continue
            if sub == stem:
                continue  # exact match, nothing to ghost
            return Suggestion(sub[len(stem):])
        return None


__all__ = ["CommandAutoSuggest"]

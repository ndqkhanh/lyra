"""Investigate-mode system prompt — the terse DCI shape, not a ReAct scaffold.

DCI-Agent-Lite's published system prompt is short on purpose. The paper's
RQ6 finding is that the agent already knows the right tool-call shape
(broad-grep → narrow-grep → read → cross-cut → cite) from coding-task
pretraining; piling on chain-of-thought scaffolding hurts more than it
helps. Extended reasoning is delegated to the provider's native thinking
budget (``--thinking high`` in DCI-Agent-Lite; the provider plugins'
``thinking`` knob in Lyra).

The body below is the load-bearing surface. :func:`build_system_prompt`
specialises it with the live :class:`CorpusMount` so file paths in the
prompt resolve correctly.

Cite: arXiv:2605.05242 §3.5 (system prompt); RQ6 (tool usage patterns).
"""
from __future__ import annotations

from .corpus import CorpusMount

INVESTIGATE_PROMPT_BODY: str = """\
You are an investigator. The user gave you a question and a corpus of files.
Your job is to find the answer by exploring the corpus directly.

You have three tools:

  - codesearch(pattern, case_insensitive=False, regex=True)
      Search the corpus for a regex or literal pattern. Returns hits
      as {path, line, column, text}. Start broad, then narrow.
  - read_file(path, start_line=None, end_line=None)
      Read a slice of a file. Use this to verify hits in context.
  - execute_code(cmd)
      Run a bounded shell command (rg, find, sed, head, tail, wc,
      awk, sort, uniq, xargs, cat). Writes and network are denied.

How to investigate (typical shape):

  1. codesearch a broad pattern from the question.
  2. read_file the top hits with a few lines of surrounding context.
  3. codesearch a narrower pattern that conjuncts two clues.
  4. find / sed for adjacent files when the first pattern is sparse.
  5. cat the file that contains the answer; quote it with path:line.

Output protocol:

  - Cite every claim with `path:line` from the corpus. No path, no claim.
  - When you have an answer, return it directly. Do not narrate the search.
  - When the corpus does not contain the answer, say so explicitly.

Budgets are enforced. Stop when you have the answer; do not pad.
"""


def build_system_prompt(mount: CorpusMount) -> str:
    """Return the prompt body specialised to *mount*.

    The mount root is appended as a stable header so the agent's
    relative-path responses are unambiguous.
    """
    return (
        f"Corpus root: {mount.root}\n"
        f"Read-only: {'yes' if mount.read_only else 'no'}\n\n"
        + INVESTIGATE_PROMPT_BODY
    )


__all__ = ["INVESTIGATE_PROMPT_BODY", "build_system_prompt"]

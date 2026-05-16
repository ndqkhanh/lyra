"""Braille spinner with rotating verbs and elapsed time — Wave 1."""
from __future__ import annotations

import random
import threading
import time
from typing import Callable

FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

_VERBS = [
    "Thinking", "Reasoning", "Processing", "Analyzing",
    "Synthesizing", "Reflecting", "Considering", "Computing",
]

_VERB_MAP: list[tuple[tuple[str, ...], str]] = [
    (("research", "find", "search", "look", "investigate", "explore"), "Researching"),
    (("write", "create", "build", "generate", "make", "implement", "code"), "Building"),
    (("explain", "what", "how", "why", "describe", "tell"), "Analyzing"),
    (("fix", "debug", "error", "bug", "solve", "broken", "issue"), "Debugging"),
    (("review", "check", "verify", "test", "evaluate", "audit"), "Reviewing"),
    (("summarize", "summary", "compress", "condense", "shorten"), "Summarizing"),
    (("plan", "design", "architect", "strategy", "outline"), "Planning"),
    (("compare", "versus", "vs", "difference", "better", "choose"), "Comparing"),
    (("refactor", "clean", "improve", "optimize", "restructure"), "Refactoring"),
]


def _verb_for(user_input: str) -> str:
    """Pick a contextual verb based on first few words of the input."""
    words = set(user_input.lower().split()[:6])
    for keywords, verb in _VERB_MAP:
        if words & set(keywords):
            return verb
    return random.choice(_VERBS)


class BrailleSpinner:
    """Animating braille spinner updated at 80ms intervals in a daemon thread.

    Provides a `current_line` str read by the status bar, and calls an
    optional `invalidate_fn` each frame so prompt_toolkit redraws.
    """

    def __init__(self, invalidate_fn: Callable[[], None] | None = None) -> None:
        self._invalidate = invalidate_fn
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._verb = "Thinking"
        self._start_time: float = 0.0
        self.current_line: str = ""

    def start(self, verb: str | None = None) -> None:
        """Start spinning with given (or random) verb."""
        self._stop_event.clear()
        self._verb = verb or random.choice(_VERBS)
        self._start_time = time.time()
        self.current_line = f"⠋ {self._verb}…"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def start_for(self, user_input: str) -> None:
        """Start with a verb chosen from the user's input keywords."""
        self.start(_verb_for(user_input))

    def stop(self) -> None:
        """Stop the spinner and clear current_line."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        self.current_line = ""

    @property
    def elapsed(self) -> float:
        return time.time() - self._start_time

    @property
    def elapsed_str(self) -> str:
        e = self.elapsed
        if e < 60:
            return f"{e:.1f}s"
        m, s = divmod(int(e), 60)
        return f"{m}m {s}s"

    def _run(self) -> None:
        idx = 0
        while not self._stop_event.wait(0.08):
            frame = FRAMES[idx % len(FRAMES)]
            self.current_line = f"{frame} {self._verb}… {self.elapsed_str}"
            idx += 1
            if self._invalidate:
                try:
                    self._invalidate()
                except Exception:
                    pass

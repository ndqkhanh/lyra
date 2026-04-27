"""Threaded animated spinner for the interactive CLI.

Pattern lifted (and trimmed) from ``hermes-agent``'s ``KawaiiSpinner``
because it's the only design we've found that survives every awkward
terminal we ship into:

- a real interactive TTY (the happy path — full animation),
- ``stdout`` redirected to a file or pipe (no animation, just a single
  start/end log line so the file isn't 1000 frames of ``\\r``),
- ``prompt_toolkit``'s ``patch_stdout`` (no animation; the bottom-bar
  widget owns the live status, our ``\\r`` would just overdraw),
- a closed / replaced ``sys.stdout`` (best-effort silent — never crash).

Why we don't reach for ``rich.progress``:

- ``Rich.Progress`` insists on owning the screen via a Live region; that
  conflicts with our ``Console.print`` of result panels and with
  ``prompt_toolkit``'s renderer. Hermes proved a vanilla thread + ``\\r``
  is more compatible.
- We need ``print_above()`` so a long-running tool can stream lines
  *while the spinner is still alive*. ``Rich.Progress`` solves that with
  ``Live.console.print``, but pulling Rich in here would re-trigger the
  same patch_stdout double-render bug we already fixed in the banner.

Usage::

    from .spinner import Spinner
    with Spinner("running tests"):
        run_pytest()                    # spinner ticks while we wait

Or, with progress feedback::

    with Spinner("indexing repo") as sp:
        for path in walk():
            sp.update_text(f"indexing {path.name}")
            index(path)
        sp.print_above(" ✓ indexed 1k files")

Disable globally for tests::

    spinner.set_enabled(False)          # no thread spawned, no I/O

Skin-aware: faces / verbs come from ``themes.get_active_skin().spinner``
when not explicitly passed, so ``/theme hermes`` makes spinners kawaii.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from typing import Any


# Module-level enable flag so tests can switch the spinner off entirely
# without monkey-patching every call site. The driver leaves this on; the
# pytest fixtures in ``test_interactive_spinner.py`` flip it for the duration
# of each test that exercises the threading code.
_ENABLED: bool = True


def set_enabled(flag: bool) -> None:
    """Globally enable or disable the spinner (idempotent)."""
    global _ENABLED
    _ENABLED = bool(flag)


def is_enabled() -> bool:
    """Return whether spinners will animate when ``start`` is called."""
    return _ENABLED


# Built-in spinner frame sets — picked when no skin override is active and
# no explicit ``frames=`` is passed. Names match ``hermes``' SPINNERS map
# so tweaking one config swaps them.
SPINNER_PRESETS: dict[str, list[str]] = {
    "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    "bounce": ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"],
    "grow": ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"],
    "arrows": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
    "star": ["✶", "✷", "✸", "✹", "✺", "✹", "✸", "✷"],
    "moon": ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"],
    "pulse": ["◜", "◠", "◝", "◞", "◡", "◟"],
    "braille": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
}


# Frame interval. Hermes uses 0.12s — fast enough to feel alive, slow
# enough to not pin a CPU. We default to the same.
_FRAME_INTERVAL_SEC: float = 0.12


class Spinner:
    """Threaded ``\\r``-rewind spinner with TTY / patch_stdout guards.

    Public surface is intentionally tiny:

    - ``start()`` / ``stop(final_message=None)``  — manual lifecycle
    - context manager (``with Spinner(...) as sp: ...``)
    - ``update_text(msg)``                         — change live message
    - ``print_above(line)``                        — flush a line above

    Threading model: one daemon thread per spinner. Daemon means it dies
    with the process and we never block CTRL+C. The thread loop checks
    ``self.running`` every ``_FRAME_INTERVAL_SEC``, so ``stop()`` returns
    in <130ms in the worst case.
    """

    def __init__(
        self,
        message: str = "",
        *,
        frames: list[str] | None = None,
        preset: str = "dots",
        out: Any | None = None,
    ) -> None:
        # Resolve frames in priority order:
        #   1. explicit ``frames=`` (caller knows best)
        #   2. active-skin spinner.faces (so /theme can re-skin spinners)
        #   3. ``preset`` lookup (default "dots")
        if frames is None:
            frames = self._frames_from_active_skin() or list(
                SPINNER_PRESETS.get(preset, SPINNER_PRESETS["dots"])
            )
        if not frames:
            # Defensive: empty frame list would divide-by-zero in ``_animate``.
            frames = ["·"]
        self.frames: list[str] = list(frames)
        self.message: str = message
        self.running: bool = False
        self._thread: threading.Thread | None = None
        self._frame_idx: int = 0
        self._start_time: float | None = None
        self._last_line_len: int = 0
        # Capture the output stream at construction time so a later
        # ``redirect_stdout(devnull)`` (e.g. from a child agent) doesn't
        # silently route our writes into the void.
        self._out: Any = out if out is not None else sys.stdout
        # Cache wings once at start to avoid a per-frame skin import.
        self._wings: list[tuple[str, str]] = []

    @staticmethod
    def _frames_from_active_skin() -> list[str]:
        """Return spinner frames declared by the active skin (or [])."""
        try:
            from . import themes as _t

            faces = _t.get_active_skin().spinner.get("faces") or []
        except Exception:  # pragma: no cover - defensive
            return []
        return [str(f) for f in faces if isinstance(f, (str,))]

    @staticmethod
    def _wings_from_active_skin() -> list[tuple[str, str]]:
        try:
            from . import themes as _t

            raw = _t.get_active_skin().spinner.get("wings") or []
        except Exception:  # pragma: no cover - defensive
            return []
        out: list[tuple[str, str]] = []
        for pair in raw:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                out.append((str(pair[0]), str(pair[1])))
        return out

    # ----- TTY / patch_stdout detection ----------------------------------

    @property
    def _is_tty(self) -> bool:
        """Best-effort isatty check that survives a closed stream."""
        try:
            return hasattr(self._out, "isatty") and bool(self._out.isatty())
        except (ValueError, OSError):
            return False

    def _is_patch_stdout_proxy(self) -> bool:
        """Detect prompt_toolkit's StdoutProxy.

        Under ``patch_stdout`` the proxy queues writes and inserts newlines
        on each ``flush()``, so our ``\\r``-overwrite never lands. The
        prompt_toolkit toolbar already handles live status, so we should
        do nothing in that case rather than spam frames-per-line.
        """
        try:
            from prompt_toolkit.patch_stdout import StdoutProxy  # type: ignore[import-not-found]

            return isinstance(self._out, StdoutProxy)
        except ImportError:
            return False

    # ----- write helpers --------------------------------------------------

    def _write(self, text: str, *, end: str = "\n", flush: bool = False) -> None:
        try:
            self._out.write(text + end)
            if flush:
                self._out.flush()
        except (ValueError, OSError):
            # Stream replaced / closed mid-flight. Silently swallow rather
            # than blow up the user's session.
            pass

    # ----- thread loop ----------------------------------------------------

    def _animate(self) -> None:
        # Headless / piped: emit one start line, then idle until stop().
        if not self._is_tty:
            self._write(f" [tool] {self.message}", flush=True)
            while self.running:
                time.sleep(0.5)
            return

        # patch_stdout: no-op the animation; the toolbar widget owns it.
        if self._is_patch_stdout_proxy():
            while self.running:
                time.sleep(0.1)
            return

        self._wings = self._wings_from_active_skin()

        while self.running:
            if os.getenv("OPEN_HARNESS_SPINNER_PAUSE"):
                time.sleep(0.1)
                continue
            frame = self.frames[self._frame_idx % len(self.frames)]
            elapsed = time.time() - (self._start_time or time.time())
            if self._wings:
                left, right = self._wings[self._frame_idx % len(self._wings)]
                line = f" {left} {frame} {self.message} {right} ({elapsed:.1f}s)"
            else:
                line = f" {frame} {self.message} ({elapsed:.1f}s)"
            # Pad with spaces (NOT \033[K) to clear the previous frame —
            # \033[K renders as garbage under patch_stdout proxies.
            pad = max(self._last_line_len - len(line), 0)
            self._write(f"\r{line}{' ' * pad}", end="", flush=True)
            self._last_line_len = len(line)
            self._frame_idx += 1
            time.sleep(_FRAME_INTERVAL_SEC)

    # ----- lifecycle ------------------------------------------------------

    def start(self) -> None:
        """Begin animating. No-op when the global flag is off or already running."""
        if self.running or not _ENABLED:
            return
        self.running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self, final_message: str | None = None) -> None:
        """Stop the thread, clear the spinner line, optionally print a closer."""
        if not self.running:
            # Still emit final_message in case caller wants the line.
            if final_message and not _ENABLED:
                self._write(f" [done] {final_message}", flush=True)
            return
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)

        is_tty = self._is_tty
        if is_tty and not self._is_patch_stdout_proxy():
            blanks = " " * max(self._last_line_len + 5, 40)
            self._write(f"\r{blanks}\r", end="", flush=True)
        if final_message:
            elapsed_str = (
                f" ({time.time() - self._start_time:.1f}s)"
                if self._start_time
                else ""
            )
            if is_tty:
                self._write(f" {final_message}", flush=True)
            else:
                self._write(f" [done] {final_message}{elapsed_str}", flush=True)

    def update_text(self, message: str) -> None:
        """Change the message rendered next tick."""
        self.message = message

    def print_above(self, text: str) -> None:
        """Flush a line above the live spinner without disrupting animation.

        Implementation mirrors hermes': clear the current frame with
        spaces, write the line, then let the next tick redraw the
        spinner below it. Works under patch_stdout because we wrote to
        the captured stream, bypassing whatever shenanigans replaced
        ``sys.stdout`` mid-flight.
        """
        if not self.running:
            self._write(f" {text}", flush=True)
            return
        blanks = " " * max(self._last_line_len + 5, 40)
        self._write(f"\r{blanks}\r {text}", flush=True)

    # ----- context manager -----------------------------------------------

    def __enter__(self) -> "Spinner":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()


class ThreadedSpinner:
    """Claw-code-inspired Braille spinner that self-animates in a thread.

    Fixes the claw-code tick-once-per-LLM-turn bug by running the frame
    advance loop on its own daemon thread so the animation keeps moving
    while the main thread blocks on an LLM call.

    Always animates — unlike :class:`Spinner`, there is no TTY gate —
    because the intended use is a visible *indicator* during
    inference. For pipes/redirects the caller should simply not spawn
    a ``ThreadedSpinner``.

    Frame cadence is capped to ~10Hz (~100ms per frame) so the output
    stream receives a visible but cheap stream of updates; 250ms of
    running produces at least three distinct frames, matching the
    contract in ``tests/test_spinner_animates_threaded.py``.
    """

    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    INTERVAL_SEC = 0.08  # ~12Hz

    def __init__(
        self,
        *,
        stream: Any | None = None,
        frames: str | None = None,
        interval_sec: float | None = None,
        active_color: str = "\x1b[34m",  # blue
        final_color_ok: str = "\x1b[32m",  # green
        final_color_err: str = "\x1b[31m",  # red
    ) -> None:
        self._stream: Any = stream if stream is not None else sys.stdout
        self._frames: str = frames or self.FRAMES
        self._interval_sec: float = float(interval_sec or self.INTERVAL_SEC)
        self._active_color: str = active_color
        self._final_color_ok: str = final_color_ok
        self._final_color_err: str = final_color_err

        self._label: str = ""
        self._running: bool = False
        self._stopped: bool = False
        self._thread: threading.Thread | None = None
        self._idx: int = 0
        self._lock = threading.Lock()

    def start(self, label: str = "") -> None:
        with self._lock:
            if self._running:
                return
            self._label = str(label)
            self._running = True
            self._stopped = False
            self._idx = 0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    return
            frame = self._frames[self._idx % len(self._frames)]
            self._idx += 1
            self._write(f"\r{self._active_color}{frame}\x1b[0m {self._label}")
            time.sleep(self._interval_sec)

    def stop(self, final: str | None = None, *, ok: bool = True) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            self._running = False
        thread = self._thread
        if thread is not None:
            try:
                thread.join(timeout=max(self._interval_sec * 2, 0.3))
            except RuntimeError:  # pragma: no cover - defensive
                pass
        # Rewind + clear (ANSI clear-line as well so non-TTY buffers see it).
        self._write("\r\x1b[2K")
        if final:
            color = self._final_color_ok if ok else self._final_color_err
            self._write(f"{color}{final}\x1b[0m\n")

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _write(self, text: str) -> None:
        try:
            self._stream.write(text)
            flush = getattr(self._stream, "flush", None)
            if callable(flush):
                flush()
        except (ValueError, OSError):  # pragma: no cover - defensive
            pass

    # Context manager niceties.

    def __enter__(self) -> "ThreadedSpinner":  # pragma: no cover - trivial
        self.start(self._label)
        return self

    def __exit__(self, *_: Any) -> None:  # pragma: no cover - trivial
        self.stop()


__all__ = [
    "Spinner",
    "SPINNER_PRESETS",
    "ThreadedSpinner",
    "is_enabled",
    "set_enabled",
]

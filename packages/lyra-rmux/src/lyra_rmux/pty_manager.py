"""PTY process manager — spawn, resize, read, write, kill."""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess  # only used for Popen cleanup
import sys
import termios
import time
from typing import Callable

from lyra_rmux.models import PtyProcess


class PtyManager:
    """Low-level PTY lifecycle: spawn via os.forkpty, I/O, resize, kill/wait."""

    def __init__(self, on_output: Callable[[int, bytes], None] | None = None) -> None:
        self._processes: dict[int, PtyProcess] = {}
        self._fds: dict[int, int] = {}  # pid -> fd
        self._pids: dict[int, int] = {}  # fd -> pid
        self._on_output = on_output

    # ------------------------------------------------------------------
    # spawn
    # ------------------------------------------------------------------

    def spawn(
        self,
        command: tuple[str, ...] = ("/bin/sh", "-i"),
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        rows: int = 24,
        cols: int = 80,
    ) -> PtyProcess:
        """Fork a child in a new PTY and exec *command*.

        Returns a PtyProcess snapshot (frozen).  Raises OSError on failure.
        """
        pid, fd = os.forkpty()

        if pid == 0:
            # ---- child ----
            try:
                if cwd:
                    os.chdir(cwd)
                new_env = os.environ.copy()
                if env:
                    new_env.update(env)
                new_env.setdefault("TERM", "xterm-256color")
                os.execvpe(command[0], list(command), new_env)
            except Exception:
                os._exit(1)

        # ---- parent ----
        _set_nonblock(fd)
        self._resize_fd(fd, rows, cols)

        p = PtyProcess(
            pid=pid,
            fd=fd,
            command=command,
            cwd=cwd or os.getcwd(),
        )
        self._processes[pid] = p
        self._fds[pid] = fd
        self._pids[fd] = pid
        return p

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def write(self, pid: int, data: bytes) -> int:
        """Write *data* to the PTY of the given child PID.

        Returns number of bytes written.  Raises ``ProcessLookupError`` if
        the PID is not tracked, ``ChildProcessError`` if the child is dead.
        """
        fd = self._fds.get(pid)
        if fd is None:
            raise ProcessLookupError(f"PID {pid} not tracked")
        try:
            n = os.write(fd, data)
            return n
        except OSError as exc:
            if exc.errno == errno.EIO:
                raise ChildProcessError(f"Child PID {pid} is dead (EIO)") from exc
            raise

    def read(self, pid: int, max_bytes: int = 65536) -> bytes:
        """Non-blocking read from the child PTY.

        Returns empty bytes when no data is available.  Raises
        ``ChildProcessError`` on EIO (child closed).
        """
        fd = self._fds.get(pid)
        if fd is None:
            raise ProcessLookupError(f"PID {pid} not tracked")
        try:
            data = os.read(fd, max_bytes)
            return data
        except OSError as exc:
            if exc.errno == errno.EWOULDBLOCK or exc.errno == errno.EAGAIN:
                return b""
            if exc.errno == errno.EIO:
                raise ChildProcessError(f"Child PID {pid} is dead (EIO)") from exc
            raise

    def read_all_buffered(self, pid: int, timeout: float = 0.05) -> bytes:
        """Drain any available output within *timeout* seconds.

        Useful after a write to collect prompt output.  Returns all data
        accumulated during the interval.
        """
        fd = self._fds.get(pid)
        if fd is None:
            raise ProcessLookupError(f"PID {pid} not tracked")
        deadline = time.monotonic() + timeout
        chunks: list[bytes] = []
        while time.monotonic() < deadline:
            r, _w, _x = select.select([fd], [], [], max(0, deadline - time.monotonic()))
            if not r:
                break
            try:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            except OSError as exc:
                if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                    break
                if exc.errno == errno.EIO:
                    break
                raise
        return b"".join(chunks)

    # ------------------------------------------------------------------
    # resize
    # ------------------------------------------------------------------

    def resize(self, pid: int, rows: int, cols: int) -> None:
        """Resize the PTY window via TIOCSWINSZ ioctl."""
        fd = self._fds.get(pid)
        if fd is None:
            raise ProcessLookupError(f"PID {pid} not tracked")
        self._resize_fd(fd, rows, cols)

    @staticmethod
    def _resize_fd(fd: int, rows: int, cols: int) -> None:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

    # ------------------------------------------------------------------
    # kill / wait / close
    # ------------------------------------------------------------------

    def kill(self, pid: int, sig: int = signal.SIGTERM) -> None:
        """Send a signal to the child process."""
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass  # already dead

    def wait(self, pid: int, block: bool = True) -> int | None:
        """Wait for the child to exit.

        If *block* is False, raises ``ChildProcessError`` when the child is
        still alive (caller should try again later).
        Returns *exit_code* or None if not ready.
        """
        try:
            _pid, status = os.waitpid(pid, 0 if block else os.WNOHANG)
        except ChildProcessError:
            return 0  # already reaped
        if _pid == 0:
            return None
        exit_code = status >> 8 if os.WIFEXITED(status) else -status
        self._mark_closed(pid, exit_code)
        return exit_code

    def close(self, pid: int) -> None:
        """Force-close the PTY fd and SIGKILL the child."""
        fd = self._fds.get(pid)
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        self.kill(pid, signal.SIGKILL)
        self.wait(pid, block=False)
        self._mark_closed(pid, -9)

    def is_alive(self, pid: int) -> bool:
        """Check whether the child process is still running."""
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    # ------------------------------------------------------------------
    # housekeeping
    # ------------------------------------------------------------------

    def process(self, pid: int) -> PtyProcess | None:
        """Return the tracked PtyProcess for *pid* (None if unknown)."""
        return self._processes.get(pid)

    def cleanup_all(self) -> None:
        """Kill every tracked child and release resources."""
        for pid in list(self._processes):
            self.close(pid)

    def _mark_closed(self, pid: int, exit_code: int) -> None:
        fd = self._fds.pop(pid, None)
        self._pids.pop(fd, None)
        old = self._processes.pop(pid, None)
        if old is not None:
            self._processes[pid] = PtyProcess(
                pid=old.pid,
                fd=old.fd,
                command=old.command,
                cwd=old.cwd,
                exit_code=exit_code,
            )


def _set_nonblock(fd: int) -> None:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

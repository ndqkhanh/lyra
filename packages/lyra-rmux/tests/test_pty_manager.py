"""Tests for lyra_rmux.pty_manager."""

import os
import signal
import errno
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from lyra_rmux.pty_manager import PtyManager, _set_nonblock


# ------------------------------------------------------------------
# Mock helpers
# ------------------------------------------------------------------


@pytest.fixture
def mock_forkpty() -> object:
    """Patch os.forkpty to return (pid, fd)."""
    with patch("lyra_rmux.pty_manager.os.forkpty") as m:
        m.return_value = (42, 7)
        yield m


@pytest.fixture
def mgr() -> PtyManager:
    return PtyManager()


# ------------------------------------------------------------------
# _set_nonblock
# ------------------------------------------------------------------


def test_set_nonblock() -> None:
    with patch("lyra_rmux.pty_manager.fcntl.fcntl") as mock_fcntl:
        mock_fcntl.return_value = 0  # current flags
        _set_nonblock(3)
        assert mock_fcntl.call_count == 2


# ------------------------------------------------------------------
# spawn
# ------------------------------------------------------------------


@patch("lyra_rmux.pty_manager.os.execvpe")
@patch("lyra_rmux.pty_manager._set_nonblock")
@patch("lyra_rmux.pty_manager.PtyManager._resize_fd")
def test_spawn_child(
    mock_resize: MagicMock,
    mock_nonblock: MagicMock,
    mock_exec: MagicMock,
    mock_forkpty: MagicMock,
    mgr: PtyManager,
) -> None:
    """In the child branch execvpe is called (but we mock it to prevent actual exec)."""
    mock_forkpty.return_value = (42, 7)
    with patch("lyra_rmux.pty_manager.os.chdir"):
        p = mgr.spawn(command=("/bin/sh", "-i"), cwd="/tmp")
    assert p.pid == 42
    assert p.fd == 7
    assert p.command == ("/bin/sh", "-i")
    assert p.exit_code is None
    assert mock_resize.called


@patch("lyra_rmux.pty_manager._set_nonblock")
@patch("lyra_rmux.pty_manager.PtyManager._resize_fd")
@patch("lyra_rmux.pty_manager.os.chdir")
def test_spawn_failure(
    mock_chdir: MagicMock,
    mock_resize: MagicMock,
    mock_nonblock: MagicMock,
    mock_forkpty: MagicMock,
    mgr: PtyManager,
) -> None:
    """forkpty failure raises OSError."""
    mock_forkpty.side_effect = OSError("fork failed")
    with pytest.raises(OSError):
        mgr.spawn()


# ------------------------------------------------------------------
# write / read
# ------------------------------------------------------------------


def test_write_unknown_pid(mgr: PtyManager) -> None:
    with pytest.raises(ProcessLookupError):
        mgr.write(999, b"hello")


def test_read_unknown_pid(mgr: PtyManager) -> None:
    with pytest.raises(ProcessLookupError):
        mgr.read(999)


def test_write_eio(mgr: PtyManager) -> None:
    mgr._fds[1] = 100
    mgr._pids[100] = 1
    with patch("lyra_rmux.pty_manager.os.write") as m:
        m.side_effect = OSError(errno.EIO, "EIO")
        with pytest.raises(ChildProcessError):
            mgr.write(1, b"data")


def test_read_eio(mgr: PtyManager) -> None:
    mgr._fds[1] = 100
    mgr._pids[100] = 1
    with patch("lyra_rmux.pty_manager.os.read") as m:
        m.side_effect = OSError(errno.EIO, "EIO")
        with pytest.raises(ChildProcessError):
            mgr.read(1)


def test_read_ewouldblock(mgr: PtyManager) -> None:
    mgr._fds[1] = 100
    mgr._pids[100] = 1
    with patch("lyra_rmux.pty_manager.os.read") as m:
        m.side_effect = OSError(errno.EWOULDBLOCK, "EWOULDBLOCK")
        data = mgr.read(1)
    assert data == b""


def test_write_read_success(mgr: PtyManager) -> None:
    mgr._fds[1] = 100
    mgr._pids[100] = 1
    with patch("lyra_rmux.pty_manager.os.write", return_value=5) as mock_write:
        n = mgr.write(1, b"hello")
    assert n == 5

    with patch("lyra_rmux.pty_manager.os.read", return_value=b"output") as mock_read:
        data = mgr.read(1)
    assert data == b"output"


# ------------------------------------------------------------------
# resize
# ------------------------------------------------------------------


def test_resize_unknown_pid(mgr: PtyManager) -> None:
    with pytest.raises(ProcessLookupError):
        mgr.resize(999, 50, 120)


@patch("lyra_rmux.pty_manager.fcntl.ioctl")
@patch("lyra_rmux.pty_manager.struct.pack", return_value=b"xxxx")
def test_resize_success(mock_pack: MagicMock, mock_ioctl: MagicMock, mgr: PtyManager) -> None:
    mgr._fds[1] = 100
    mgr.resize(1, 50, 120)
    assert mock_ioctl.called


# ------------------------------------------------------------------
# kill / wait / close / is_alive
# ------------------------------------------------------------------


def test_kill_unknown_pid(mgr: PtyManager) -> None:
    mgr.kill(999)  # should not raise


@patch("lyra_rmux.pty_manager.os.kill")
def test_kill_success(mock_kill: MagicMock, mgr: PtyManager) -> None:
    mgr.kill(42, signal.SIGTERM)
    mock_kill.assert_called_with(42, signal.SIGTERM)


@patch("lyra_rmux.pty_manager.os.kill", side_effect=ProcessLookupError)
def test_kill_already_dead(mock_kill: MagicMock, mgr: PtyManager) -> None:
    mgr.kill(42)  # should not raise


@patch("lyra_rmux.pty_manager.os.waitpid", return_value=(42, 0))
@patch("lyra_rmux.pty_manager.os.WIFEXITED", return_value=True)
def test_wait_success(mock_wif: MagicMock, mock_wait: MagicMock, mgr: PtyManager) -> None:
    exit_code = mgr.wait(42)
    assert exit_code == 0


@patch("lyra_rmux.pty_manager.os.waitpid", return_value=(0, 0))
def test_wait_not_ready(mock_wait: MagicMock, mgr: PtyManager) -> None:
    rc = mgr.wait(42, block=False)
    assert rc is None


def test_is_alive_true(mgr: PtyManager) -> None:
    with patch("lyra_rmux.pty_manager.os.kill") as m:
        m.return_value = None
        assert mgr.is_alive(42) is True


def test_is_alive_false(mgr: PtyManager) -> None:
    with patch("lyra_rmux.pty_manager.os.kill") as m:
        m.side_effect = ProcessLookupError
        assert mgr.is_alive(42) is False


@patch("lyra_rmux.pty_manager.os.close")
@patch("lyra_rmux.pty_manager.os.kill")
@patch("lyra_rmux.pty_manager.os.waitpid", return_value=(1, 0))
def test_close(mock_wait: MagicMock, mock_kill: MagicMock, mock_close: MagicMock, mgr: PtyManager) -> None:
    mgr._fds[1] = 100
    mgr.close(1)
    mock_kill.assert_called_with(1, signal.SIGKILL)
    assert mock_close.called


# ------------------------------------------------------------------
# process tracking
# ------------------------------------------------------------------


def test_process_returns_none(mgr: PtyManager) -> None:
    assert mgr.process(999) is None


def test_cleanup_all(mgr: PtyManager) -> None:
    mgr._processes[1] = MagicMock()
    with patch.object(mgr, "close") as mock_close:
        mgr.cleanup_all()
    assert mock_close.called


# ------------------------------------------------------------------
# read_all_buffered
# ------------------------------------------------------------------


def test_read_all_buffered_unknown(mgr: PtyManager) -> None:
    with pytest.raises(ProcessLookupError):
        mgr.read_all_buffered(999)


@patch("lyra_rmux.pty_manager.select.select", return_value=([], [], []))
def test_read_all_buffered_empty(mock_sel: MagicMock, mgr: PtyManager) -> None:
    mgr._fds[1] = 100
    data = mgr.read_all_buffered(1, timeout=0.01)
    assert data == b""

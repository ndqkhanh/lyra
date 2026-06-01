"""CLI for lyra-rmux — create/attach/detach/list/split/send/snapshot/kill/daemon."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from lyra_rmux.daemon import RmuxDaemon
from lyra_rmux.ipc_client import RmuxClient
from lyra_rmux.session_manager import SessionManager


def _get_client(args: argparse.Namespace) -> RmuxClient:
    return RmuxClient(socket_path=getattr(args, "socket", "/tmp/lyra-rmux.sock"))


def _print_json(obj: object) -> None:
    json.dump(obj, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


# ------------------------------------------------------------------
# handlers
# ------------------------------------------------------------------


def cmd_create(args: argparse.Namespace) -> None:
    client = _get_client(args)
    result = client.create_session(
        name=args.name,
        command=tuple(args.command) if args.command else ("/bin/sh", "-i"),
        cwd=args.cwd,
        rows=args.rows,
        cols=args.cols,
    )
    _print_json(result)


def cmd_attach(args: argparse.Namespace) -> None:
    client = _get_client(args)
    result = client.attach_session(args.session_id)
    _print_json(result or {"error": "session not found"})


def cmd_detach(args: argparse.Namespace) -> None:
    client = _get_client(args)
    result = client.detach_session(args.session_id)
    _print_json(result)


def cmd_list(args: argparse.Namespace) -> None:
    client = _get_client(args)
    sessions = client.list_sessions()
    _print_json(sessions)


def cmd_split(args: argparse.Namespace) -> None:
    client = _get_client(args)
    result = client.split_pane(
        session_id=args.session_id,
        window_id=args.window_id,
        vertical=args.vertical,
        command=tuple(args.command) if args.command else ("/bin/sh", "-i"),
    )
    _print_json(result or {"error": "split failed"})


def cmd_send(args: argparse.Namespace) -> None:
    client = _get_client(args)
    result = client.send_keys(args.session_id, args.data, pane_id=args.pane_id)
    print(result)


def cmd_snapshot(args: argparse.Namespace) -> None:
    client = _get_client(args)
    result = client.get_snapshot(args.session_id, pane_id=args.pane_id)
    if result:
        print("\n".join(result.get("lines", [])))
    else:
        print("No snapshot available", file=sys.stderr)


def cmd_kill(args: argparse.Namespace) -> None:
    client = _get_client(args)
    if args.pane_id:
        client.kill_pane(args.session_id, pane_id=args.pane_id)
    else:
        client.kill_session(args.session_id)
    print("OK")


def cmd_daemon(args: argparse.Namespace) -> None:
    daemon = RmuxDaemon(socket_path=args.socket)
    print(f"Starting lyra-rmuxd on {args.socket} ...", file=sys.stderr)
    if args.detach:
        pid = os.fork()
        if pid > 0:
            print(f"Daemon started (PID {pid})", file=sys.stderr)
            sys.exit(0)
        os.setsid()
        pid2 = os.fork()
        if pid2 > 0:
            sys.exit(0)
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
    daemon.serve_forever()


def cmd_status(args: argparse.Namespace) -> None:
    client = _get_client(args)
    try:
        status = client.daemon_status()
        _print_json(status)
    except (ConnectionRefusedError, FileNotFoundError, OSError) as exc:
        print(f"Daemon not reachable: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_shutdown(args: argparse.Namespace) -> None:
    client = _get_client(args)
    try:
        client.daemon_shutdown()
        print("Daemon shut down.")
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


# ------------------------------------------------------------------
# local-mode commands (standalone, no daemon)
# ------------------------------------------------------------------


def cmd_local(args: argparse.Namespace) -> None:
    """Run commands directly without a daemon."""
    sm = SessionManager()

    if args.local_cmd == "create":
        sess = sm.create_session(
            name=args.name,
            command=tuple(args.command) if args.command else ("/bin/sh", "-i"),
            cwd=args.cwd,
            rows=args.rows,
            cols=args.cols,
        )
        print(json.dumps({
            "session_id": sess.session_id,
            "name": sess.name,
            "state": sess.state.value,
            "pane_id": sess.windows[0].panes[0].pane_id,
        }))
    elif args.local_cmd == "send":
        ok = sm.send_keys(args.session_id, args.data, pane_id=args.pane_id)
        print("OK" if ok else "FAIL")
        if ok:
            time.sleep(0.1)
            snap = sm.get_snapshot(args.session_id, pane_id=args.pane_id)
            if snap:
                print("\n".join(snap.lines))
    elif args.local_cmd == "snapshot":
        snap = sm.get_snapshot(args.session_id, pane_id=args.pane_id)
        if snap:
            print("\n".join(snap.lines))
    elif args.local_cmd == "kill":
        if args.pane_id:
            sm.kill_pane(args.session_id, pane_id=args.pane_id)
        else:
            sm.kill_session(args.session_id)
        print("OK")
    else:
        print(f"Unknown local command: {args.local_cmd}", file=sys.stderr)
        sys.exit(1)


# ------------------------------------------------------------------
# main parser
# ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lyra-rmux", description="Python PTY multiplexer")
    parser.add_argument("--socket", default="/tmp/lyra-rmux.sock", help="Unix socket path")

    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = sub.add_parser("create", help="Create a new session")
    p_create.add_argument("--name", default="", help="Session name")
    p_create.add_argument("--command", nargs="+", default=None, help="Command to run (default: /bin/sh -i)")
    p_create.add_argument("--cwd", default=None, help="Working directory")
    p_create.add_argument("--rows", type=int, default=24, help="Rows")
    p_create.add_argument("--cols", type=int, default=80, help="Columns")

    # attach
    p_attach = sub.add_parser("attach", help="Attach to a session")
    p_attach.add_argument("session_id", help="Session ID")

    # detach
    p_detach = sub.add_parser("detach", help="Detach from a session")
    p_detach.add_argument("session_id", help="Session ID")

    # list
    sub.add_parser("list", help="List sessions")

    # split
    p_split = sub.add_parser("split", help="Split a pane")
    p_split.add_argument("session_id", help="Session ID")
    p_split.add_argument("--window-id", default="win-1", help="Window ID")
    p_split.add_argument("--vertical", action="store_true", default=True, help="Vertical split (default)")
    p_split.add_argument("--horizontal", action="store_false", dest="vertical", help="Horizontal split")
    p_split.add_argument("--command", nargs="+", default=None, help="Command for new pane")

    # send
    p_send = sub.add_parser("send", help="Send text to a pane")
    p_send.add_argument("session_id", help="Session ID")
    p_send.add_argument("data", help="Text to send")
    p_send.add_argument("--pane-id", default=None, help="Pane ID")

    # snapshot
    p_snap = sub.add_parser("snapshot", help="Get pane snapshot")
    p_snap.add_argument("session_id", help="Session ID")
    p_snap.add_argument("--pane-id", default=None, help="Pane ID")

    # kill
    p_kill = sub.add_parser("kill", help="Kill a session or pane")
    p_kill.add_argument("session_id", help="Session ID")
    p_kill.add_argument("--pane-id", default=None, help="Kill specific pane (otherwise whole session)")

    # daemon
    p_daemon = sub.add_parser("daemon", help="Start the daemon")
    p_daemon.add_argument("--detach", action="store_true", help="Fork to background")

    # status
    sub.add_parser("status", help="Check daemon status")

    # shutdown
    sub.add_parser("shutdown", help="Shutdown daemon")

    # local (standalone, no daemon)
    p_local = sub.add_parser("local", help="Run commands directly (no daemon)")
    p_local.add_argument("local_cmd", choices=["create", "send", "snapshot", "kill"], help="Local command")
    p_local.add_argument("--session-id", default=None, help="Session ID")
    p_local.add_argument("--pane-id", default=None, help="Pane ID")
    p_local.add_argument("--name", default="", help="Session name")
    p_local.add_argument("--command", nargs="+", default=None, help="Command")
    p_local.add_argument("--cwd", default=None, help="Working directory")
    p_local.add_argument("--rows", type=int, default=24, help="Rows")
    p_local.add_argument("--cols", type=int, default=80, help="Columns")
    p_local.add_argument("data", nargs="?", default="", help="Text to send")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "create": cmd_create,
        "attach": cmd_attach,
        "detach": cmd_detach,
        "list": cmd_list,
        "split": cmd_split,
        "send": cmd_send,
        "snapshot": cmd_snapshot,
        "kill": cmd_kill,
        "daemon": cmd_daemon,
        "status": cmd_status,
        "shutdown": cmd_shutdown,
        "local": cmd_local,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

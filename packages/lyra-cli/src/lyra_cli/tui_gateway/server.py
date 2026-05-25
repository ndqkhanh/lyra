"""Lyra TUI Gateway — JSON-RPC server with session management, config I/O, and agent integration.

Adapted from Hermes Agent's tui_gateway.server module.  Key differences:

  - Paths use ``~/.lyra/`` instead of ``~/.hermes/``
  - Session DB is a JSON file store at ``~/.lyra/sessions/``
  - Agent factory (``_build_agent``) is a stub — wire it when Lyra's agent
    system is ready.
  - Lyra-specific RPC methods (``lyra.*``) are registered as stubs.
"""

from __future__ import annotations

import atexit
import concurrent.futures
import contextvars
import copy
import json
import logging
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from .render import make_stream_renderer, render_diff, render_message
from .transport import (
    StdioTransport,
    Transport,
    bind_transport,
    current_transport,
    reset_transport,
)
from .lyra_agent import LyraAgent

logger = logging.getLogger(__name__)

# ── Lyra home directory ──────────────────────────────────────────────
_LYRA_HOME = Path.home() / ".lyra"

# ── Panic logger ─────────────────────────────────────────────────────
_CRASH_LOG = os.path.join(str(_LYRA_HOME), "logs", "tui_gateway_crash.log")


def _panic_hook(exc_type, exc_value, exc_tb):
    import traceback as _tb

    trace = "".join(_tb.format_exception(exc_type, exc_value, exc_tb))
    try:
        os.makedirs(os.path.dirname(_CRASH_LOG), exist_ok=True)
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"\n=== unhandled exception · {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
            )
            f.write(trace)
    except Exception:
        pass
    first = (
        str(exc_value).strip().splitlines()[0]
        if str(exc_value).strip()
        else exc_type.__name__
    )
    print(f"[gateway-crash] {exc_type.__name__}: {first}", file=sys.stderr, flush=True)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _panic_hook


def _thread_panic_hook(args):
    import traceback as _tb

    trace = "".join(
        _tb.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
    )
    try:
        os.makedirs(os.path.dirname(_CRASH_LOG), exist_ok=True)
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"\n=== thread exception · {time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"· thread={args.thread.name} ===\n"
            )
            f.write(trace)
    except Exception:
        pass
    first_line = (
        str(args.exc_value).strip().splitlines()[0]
        if str(args.exc_value).strip()
        else args.exc_type.__name__
    )
    print(
        f"[gateway-crash] thread {args.thread.name} raised {args.exc_type.__name__}: {first_line}",
        file=sys.stderr,
        flush=True,
    )


threading.excepthook = _thread_panic_hook

# ── Module-level state ──────────────────────────────────────────────
_sessions: dict[str, dict] = {}
_methods: dict[str, Callable] = {}
_pending: dict[str, tuple[str, threading.Event]] = {}
_answers: dict[str, str] = {}
_stdout_lock = threading.Lock()
_cfg_lock = threading.Lock()
_cfg_cache: dict | None = None
_cfg_mtime: float | None = None
_cfg_path: Path | None = None
_SLASH_WORKER_TIMEOUT_S = 45.0
_DETAIL_SECTION_NAMES = ("thinking", "tools", "subagents", "activity")
_DETAIL_MODES = frozenset({"hidden", "collapsed", "expanded"})

# ── Thread pool for long handlers ───────────────────────────────────
_LONG_HANDLERS = frozenset({
    "session.resume",
    "session.compress",
    "session.branch",
    "slash.exec",
    "cli.exec",
})

try:
    _rpc_pool_workers = max(
        2, int(os.environ.get("LYRA_TUI_RPC_POOL_WORKERS") or "4")
    )
except (ValueError, TypeError):
    _rpc_pool_workers = 4
_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=_rpc_pool_workers,
    thread_name_prefix="lyra-rpc",
)
atexit.register(lambda: _pool.shutdown(wait=False, cancel_futures=True))

# Reserve real stdout for JSON-RPC only; redirect Python's stdout to stderr
# so stray print() from libraries becomes harmless stderr messages.
_real_stdout = sys.stdout
sys.stdout = sys.stderr

# Module-level stdio transport
_stdio_transport = StdioTransport(lambda: _real_stdout, _stdout_lock)


# ── Session JSON store ──────────────────────────────────────────────


def _sessions_dir() -> Path:
    p = _LYRA_HOME / "sessions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _session_path(session_id: str) -> Path:
    return _sessions_dir() / f"{session_id}.json"


def _load_session_file(session_id: str) -> dict | None:
    """Load a session from its JSON file, or return None."""
    p = _session_path(session_id)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_session_file(session_id: str, data: dict) -> None:
    """Save or update a session JSON file."""
    p = _session_path(session_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    shutil.move(str(tmp), str(p))


def _delete_session_file(session_id: str) -> None:
    p = _session_path(session_id)
    if p.exists():
        p.unlink()


def _list_sessions(limit: int = 200) -> list[dict]:
    """List stored sessions, sorted by most recent activity, newest first."""
    sdir = _sessions_dir()
    results: list[dict] = []
    for fpath in sorted(sdir.glob("*.json"), reverse=True):
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            sid = fpath.stem
            results.append({
                "id": sid,
                "title": data.get("title", ""),
                "preview": data.get("preview", ""),
                "started_at": data.get("started_at", 0),
                "message_count": data.get("message_count", 0),
                "source": data.get("source", "tui"),
            })
            if len(results) >= limit:
                break
        except Exception:
            continue
    return results


def _new_session_key() -> str:
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


# ── Config I/O ──────────────────────────────────────────────────────


def _load_cfg() -> dict:
    global _cfg_cache, _cfg_mtime, _cfg_path
    try:
        import yaml

        p = _LYRA_HOME / "config.yaml"
        mtime = p.stat().st_mtime if p.exists() else None
        with _cfg_lock:
            if _cfg_cache is not None and _cfg_mtime == mtime and _cfg_path == p:
                return copy.deepcopy(_cfg_cache)
        if p.exists():
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        with _cfg_lock:
            _cfg_cache = copy.deepcopy(data)
            _cfg_mtime = mtime
            _cfg_path = p
        return data
    except Exception:
        pass
    return {}


def _save_cfg(cfg: dict):
    global _cfg_cache, _cfg_mtime, _cfg_path
    import yaml

    path = _LYRA_HOME / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)
    with _cfg_lock:
        _cfg_cache = copy.deepcopy(cfg)
        _cfg_path = path
        try:
            _cfg_mtime = path.stat().st_mtime
        except Exception:
            _cfg_mtime = None


def _write_config_key(key_path: str, value):
    cfg = _load_cfg()
    current = cfg
    keys = key_path.split(".")
    for key in keys[:-1]:
        if key not in current or not isinstance(current.get(key), dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    _save_cfg(cfg)


# ── Slash worker ────────────────────────────────────────────────────


class _SlashWorker:
    """Persistent subprocess for slash commands."""

    def __init__(self, session_key: str, model: str):
        self._lock = threading.Lock()
        self._seq = 0
        self.stderr_tail: list[str] = []
        self.stdout_queue: queue.Queue[dict | None] = queue.Queue()

        argv = [
            sys.executable,
            "-m",
            "tui_gateway.slash_worker",
            "--session-key",
            session_key,
        ]
        if model:
            argv += ["--model", model]

        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=os.getcwd(),
            env=os.environ.copy(),
        )
        threading.Thread(target=self._drain_stdout, daemon=True).start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stdout(self):
        for line in self.proc.stdout or []:
            try:
                self.stdout_queue.put(json.loads(line))
            except json.JSONDecodeError:
                continue
        self.stdout_queue.put(None)

    def _drain_stderr(self):
        for line in self.proc.stderr or []:
            if text := line.rstrip("\n"):
                self.stderr_tail = (self.stderr_tail + [text])[-80:]

    def run(self, command: str) -> str:
        if self.proc.poll() is not None:
            raise RuntimeError("slash worker exited")

        with self._lock:
            self._seq += 1
            rid = self._seq
            self.proc.stdin.write(json.dumps({"id": rid, "command": command}) + "\n")
            self.proc.stdin.flush()

            while True:
                try:
                    msg = self.stdout_queue.get(timeout=_SLASH_WORKER_TIMEOUT_S)
                except queue.Empty:
                    raise RuntimeError("slash worker timed out")
                if msg is None:
                    break
                if msg.get("id") != rid:
                    continue
                if not msg.get("ok"):
                    raise RuntimeError(msg.get("error", "slash worker failed"))
                return str(msg.get("output", "")).rstrip()

            raise RuntimeError(
                f"slash worker closed pipe"
                + (": " + "\n".join(self.stderr_tail[-8:]) if self.stderr_tail else "")
            )

    def close(self):
        try:
            if self.proc.poll() is None:
                self.proc.terminate()
                self.proc.wait(timeout=1)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


# ── Transport / Write / Emit helpers ────────────────────────────────


def write_json(obj: dict) -> bool:
    """Emit one JSON frame. Routes via the most-specific transport available.

    Precedence:
    1. Event frames with a session id -> the transport stored on that session.
    2. Transport bound on the current context (set by :func:`dispatch`).
    3. Module-level stdio transport.
    """
    if obj.get("method") == "event":
        sid = ((obj.get("params") or {}).get("session_id")) or ""
        if sid and (t := (_sessions.get(sid) or {}).get("transport")) is not None:
            return t.write(obj)

    return (current_transport() or _stdio_transport).write(obj)


def _emit(event: str, sid: str, payload: dict | None = None):
    params = {"type": event, "session_id": sid}
    if payload is not None:
        params["payload"] = payload
    write_json({"jsonrpc": "2.0", "method": "event", "params": params})


def _status_update(sid: str, kind: str, text: str | None = None):
    body = (text if text is not None else kind).strip()
    if not body:
        return
    _emit(
        "status.update",
        sid,
        {"kind": kind if text is not None else "status", "text": body},
    )


def _ok(rid, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _err(rid, code: int, msg: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}}


# ── RPC method decorator ───────────────────────────────────────────


def method(name: str):
    def dec(fn):
        _methods[name] = fn
        return fn
    return dec


# ── Dispatch ────────────────────────────────────────────────────────


def _normalize_request(req: Any) -> tuple[Any, str, dict] | dict:
    if not isinstance(req, dict):
        return _err(None, -32600, "invalid request: expected an object")

    rid = req.get("id")
    method_name = req.get("method")
    if not isinstance(method_name, str) or not method_name:
        return _err(rid, -32600, "invalid request: method must be a non-empty string")

    params = req.get("params", {})
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        return _err(rid, -32602, "invalid params: expected an object")

    return rid, method_name, params


def handle_request(req: dict) -> dict | None:
    normalized = _normalize_request(req)
    if isinstance(normalized, dict):
        return normalized

    rid, method_name, params = normalized
    fn = _methods.get(method_name)
    if not fn:
        return _err(rid, -32601, f"unknown method: {method_name}")
    return fn(rid, params)


def dispatch(req: dict, transport: Optional[Transport] = None) -> dict | None:
    """Route inbound RPCs — long handlers to the pool, everything else inline.

    Returns a response dict when handled inline. Returns None when the
    handler was scheduled on the pool.
    """
    t = transport or _stdio_transport
    token = bind_transport(t)
    try:
        normalized = _normalize_request(req)
        if isinstance(normalized, dict):
            return normalized

        _rid, method_name, _params = normalized
        if method_name not in _LONG_HANDLERS:
            return handle_request(req)

        ctx = contextvars.copy_context()

        def run():
            try:
                resp = handle_request(req)
            except Exception as exc:
                resp = _err(req.get("id"), -32000, f"handler error: {exc}")
            if resp is not None:
                t.write(resp)

        _pool.submit(lambda: ctx.run(run))
        return None
    finally:
        reset_transport(token)


# ── Block / Wait — approval, clarify, sudo, secret flows ──────────


def _block(event: str, sid: str, payload: dict, timeout: int = 300) -> str:
    rid = uuid.uuid4().hex[:8]
    ev = threading.Event()
    _pending[rid] = (sid, ev)
    payload["request_id"] = rid
    _emit(event, sid, payload)
    ev.wait(timeout=timeout)
    _pending.pop(rid, None)
    return _answers.pop(rid, "")


def _clear_pending(sid: str | None = None) -> None:
    for rid, (owner_sid, ev) in list(_pending.items()):
        if sid is None or owner_sid == sid:
            _answers[rid] = ""
            ev.set()


# ── Block-flow respond methods (registered at module level) ────────


@method("approval.respond")
def _approval_respond(rid, params: dict) -> dict:
    rid_key = params.get("request_id", "")
    answer = params.get("answer", "")
    if rid_key in _pending:
        _answers[rid_key] = answer
        _pending[rid_key][1].set()
    return _ok(rid, {"status": "ok"})


@method("clarify.respond")
def _clarify_respond(rid, params: dict) -> dict:
    return _approval_respond(rid, params)  # Same protocol


@method("sudo.respond")
def _sudo_respond(rid, params: dict) -> dict:
    return _approval_respond(rid, params)


@method("secret.respond")
def _secret_respond(rid, params: dict) -> dict:
    return _approval_respond(rid, params)


# ── Agent factory (STUB) ────────────────────────────────────────────


def _build_agent(sid: str, key: str, session_id: str | None = None):
    """Build a Lyra agent for the given session."""
    model = _resolve_model()
    return LyraAgent(session_id=sid, session_key=key, model=model)


def _wait_agent(session: dict, rid: str, timeout: float = 30.0) -> dict | None:
    ready = session.get("agent_ready")
    if ready is not None and not ready.wait(timeout=timeout):
        return _err(rid, 5032, "agent initialization timed out")
    err = session.get("agent_error")
    return _err(rid, 5032, err) if err else None


def _start_agent_build(sid: str, session: dict) -> None:
    """Deferred agent build — runs on a background thread."""
    ready = session.get("agent_ready")
    if ready is None:
        return
    lock = session.setdefault("agent_build_lock", threading.Lock())
    with lock:
        if ready.is_set() or session.get("agent_build_started"):
            return
        session["agent_build_started"] = True
    key = session["session_key"]

    def _build() -> None:
        current = _sessions.get(sid)
        if current is None:
            ready.set()
            return

        worker = None
        try:
            agent = _build_agent(sid, key)
            current["agent"] = agent

            try:
                worker = _SlashWorker(key, getattr(agent, "model", _resolve_model()))
                current["slash_worker"] = worker
            except Exception:
                pass

            info = _session_info(agent) if hasattr(agent, '__class__') else {}
            _emit("session.info", sid, info)
        except Exception as e:
            current["agent_error"] = str(e)
            _emit("error", sid, {"message": f"agent init failed: {e}"})
        finally:
            if _sessions.get(sid) is not current:
                if worker is not None:
                    try:
                        worker.close()
                    except Exception:
                        pass
            ready.set()

    threading.Thread(target=_build, daemon=True).start()


# ── Helper: resolve model, skin, session info ──────────────────────


def resolve_skin() -> dict:
    """Return Lyra skin info for the TUI frontend."""
    try:
        return {
            "name": "lyra",
            "branding": {
                "name": "Lyra",
                "tagline": "Personal AI Research Agent",
                "help_header": "Lyra - AI-powered development and research assistant",
            },
        }
    except Exception:
        return {}


def _resolve_model() -> str:
    # Try env first, then Claude settings.json, then Lyra config, then default
    env = (
        os.environ.get("LYRA_MODEL", "")
        or os.environ.get("ANTHROPIC_MODEL", "")
    ).strip()
    if env:
        return env
    # Load from ~/.claude/settings.json (same as main.py's setup_environment)
    try:
        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            with open(settings_path) as f:
                cfg = json.load(f)
            venv = cfg.get("env", {})
            if isinstance(venv, dict):
                model = str(venv.get("ANTHROPIC_MODEL", "") or "").strip()
                if model:
                    return model
    except Exception:
        pass
    m = _load_cfg().get("model", "")
    if isinstance(m, dict):
        return str(m.get("default", "") or "").strip()
    if isinstance(m, str) and m:
        return m.strip()
    return "claude-sonnet-4-20250514"


def _session_info(agent) -> dict:
    return {
        "model": getattr(agent, "model", _resolve_model()),
        "tools": _gather_tools(),
        "skills": _gather_skills(),
        "cwd": os.getenv("TERMINAL_CWD", os.getcwd()),
        "usage": {},
        "profile_name": "default",
    }


def _gather_tools() -> dict[str, list[str]]:
    """Gather available tools from the agent and built-in registries."""
    tools: dict[str, list[str]] = {}

    # Built-in Lyra CLI tools
    tools["CLI Commands"] = [
        "bash", "read", "write", "edit", "glob", "grep",
        "task", "skill", "agent", "web_search", "web_fetch",
    ]

    # Provider-specific tools
    tools["File Operations"] = ["read_file", "write_file", "edit_file", "list_directory"]
    tools["Code Actions"] = ["run_tests", "lint", "typecheck", "format"]
    tools["Research"] = ["web_search", "deep_research", "codebase_explore", "wiki_search"]

    return tools


def _gather_skills() -> dict[str, list[str]]:
    """Gather available skills from the skills registry."""
    skills: dict[str, list[str]] = {}
    try:
        from lyra_cli.skills.registry import get_skills_registry
        registry = get_skills_registry()
        for skill_id, skill in sorted(registry.skills.items()):
            category = skill.category or "General"
            if category not in skills:
                skills[category] = []
            skills[category].append(skill.name)
    except Exception:
        pass
    return skills


def _enable_gateway_prompts() -> None:
    os.environ["LYRA_GATEWAY_SESSION"] = "1"


def _sess_nowait(params, rid):
    s = _sessions.get(params.get("session_id") or "")
    return (s, None) if s else (None, _err(rid, 4001, "session not found"))


def _sess(params, rid):
    s, err = _sess_nowait(params, rid)
    if err:
        return (None, err)
    _start_agent_build(params.get("session_id") or "", s)
    return (s, _wait_agent(s, rid))


def _finalize_session(session: dict | None, end_reason: str = "tui_close") -> None:
    if not session or session.get("_finalized"):
        return
    session["_finalized"] = True
    stop_event = session.get("_notif_stop")
    if stop_event is not None:
        stop_event.set()

    agent = session.get("agent")
    lock = session.get("history_lock")
    if lock is not None:
        with lock:
            history = list(session.get("history", []))
    else:
        history = list(session.get("history", []))

    session_key = session.get("session_key")
    if session_key:
        _save_session_file(session_key, {
            "title": session.get("pending_title") or session.get("title", ""),
            "messages": history,
            "ended_at": time.time(),
            "message_count": len(history),
        })


def _shutdown_sessions() -> None:
    for session in list(_sessions.values()):
        _finalize_session(session, end_reason="tui_shutdown")
        try:
            worker = session.get("slash_worker")
            if worker:
                worker.close()
        except Exception:
            pass


atexit.register(_shutdown_sessions)


# ── Tool progress callbacks ────────────────────────────────────────


def _on_tool_start(sid: str, tool_call_id: str, name: str, args: dict):
    session = _sessions.get(sid)
    if session is not None:
        session.setdefault("tool_started_at", {})[tool_call_id] = time.time()
    payload: dict[str, Any] = {
        "tool_id": tool_call_id,
        "name": name,
        "context": "",
    }
    _emit("tool.start", sid, payload)


def _on_tool_complete(sid: str, tool_call_id: str, name: str, args: dict, result: str):
    payload: dict[str, Any] = {"tool_id": tool_call_id, "name": name}
    session = _sessions.get(sid)
    started_at = None
    if session is not None:
        started_at = session.setdefault("tool_started_at", {}).pop(tool_call_id, None)
    if started_at:
        payload["duration_s"] = time.time() - started_at
    _emit("tool.complete", sid, payload)


def _on_tool_progress(sid: str, event_type: str, name: str | None = None, preview: str | None = None, **kwargs):
    if event_type == "tool.started" and name:
        _emit("tool.progress", sid, {"name": name, "preview": preview or ""})


def _agent_cbs(sid: str) -> dict:
    return {
        "tool_start_callback": lambda tc_id, name, args: _on_tool_start(sid, tc_id, name, args),
        "tool_complete_callback": lambda tc_id, name, args, result: _on_tool_complete(sid, tc_id, name, args, result),
        "tool_progress_callback": lambda event_type, name=None, preview=None, **kw: _on_tool_progress(sid, event_type, name, preview, **kw),
        "thinking_callback": lambda text: _emit("thinking.delta", sid, {"text": text}),
        "status_callback": lambda kind, text=None: _status_update(sid, str(kind), None if text is None else str(text)),
        "clarify_callback": lambda q, c: _block("clarify.request", sid, {"question": q, "choices": c}),
    }


# ═══════════════════════════════════════════════════════════════════
# RPC METHODS
# ═══════════════════════════════════════════════════════════════════

# ── Session methods ────────────────────────────────────────────────


@method("session.create")
def _session_create(rid, params: dict) -> dict:
    sid = uuid.uuid4().hex[:8]
    key = _new_session_key()
    cols = int(params.get("cols", 80))
    _enable_gateway_prompts()

    ready = threading.Event()

    _sessions[sid] = {
        "agent": None,
        "agent_error": None,
        "agent_ready": ready,
        "attached_images": [],
        "cols": cols,
        "history": [],
        "history_lock": threading.Lock(),
        "history_version": 0,
        "pending_title": None,
        "running": False,
        "session_key": key,
        "slash_worker": None,
        "tool_progress_mode": "all",
        "tool_started_at": {},
        "transport": current_transport() or _stdio_transport,
    }

    # Deferred agent build
    def _deferred_build() -> None:
        session = _sessions.get(sid)
        if session is not None:
            _start_agent_build(sid, session)

    build_timer = threading.Timer(0.05, _deferred_build)
    build_timer.daemon = True
    build_timer.start()

    return _ok(
        rid,
        {
            "session_id": sid,
            "info": {
                "model": _resolve_model(),
                "tools": _gather_tools(),
                "skills": _gather_skills(),
                "cwd": os.getenv("TERMINAL_CWD", os.getcwd()),
                "lazy": True,
                "profile_name": "default",
            },
        },
    )


@method("session.list")
def _session_list(rid, params: dict) -> dict:
    try:
        limit = int(params.get("limit", 200) or 200)
        rows = _list_sessions(limit=limit)
        return _ok(
            rid,
            {
                "sessions": [
                    {
                        "id": s["id"],
                        "title": s.get("title") or "",
                        "preview": s.get("preview") or "",
                        "started_at": s.get("started_at") or 0,
                        "message_count": s.get("message_count") or 0,
                        "source": s.get("source") or "",
                    }
                    for s in rows
                ]
            },
        )
    except Exception as e:
        return _err(rid, 5006, str(e))


@method("session.most_recent")
def _session_most_recent(rid, params: dict) -> dict:
    try:
        rows = _list_sessions(limit=1)
        if rows:
            return _ok(
                rid,
                {
                    "session_id": rows[0]["id"],
                    "title": rows[0].get("title") or "",
                    "started_at": rows[0].get("started_at") or 0,
                    "source": rows[0].get("source") or "",
                },
            )
        return _ok(rid, {"session_id": None})
    except Exception:
        return _ok(rid, {"session_id": None})


@method("session.resume")
def _session_resume(rid, params: dict) -> dict:
    target = params.get("session_id", "")
    if not target:
        return _err(rid, 4006, "session_id required")

    stored = _load_session_file(target)
    if not stored:
        return _err(rid, 4007, "session not found")

    sid = uuid.uuid4().hex[:8]
    _enable_gateway_prompts()
    history = stored.get("messages", [])

    try:
        agent = _build_agent(sid, target, session_id=target)
    except NotImplementedError:
        agent = None

    _sessions[sid] = {
        "agent": agent,
        "session_key": target,
        "history": history,
        "history_lock": threading.Lock(),
        "history_version": 0,
        "running": False,
        "attached_images": [],
        "cols": int(params.get("cols", 80)),
        "slash_worker": None,
        "tool_progress_mode": "all",
        "tool_started_at": {},
        "edit_snapshots": {},
        "transport": current_transport() or _stdio_transport,
    }

    return _ok(
        rid,
        {
            "session_id": sid,
            "resumed": target,
            "message_count": len(history),
            "messages": history,
            "info": _session_info(agent) if agent else {},
        },
    )


@method("session.delete")
def _session_delete(rid, params: dict) -> dict:
    target = params.get("session_id", "")
    if not target:
        return _err(rid, 4002, "session_id required")
    for sid, sess in list(_sessions.items()):
        if sess.get("session_key") == target:
            return _err(rid, 4009, "cannot delete active session")
    _delete_session_file(target)
    return _ok(rid, {"status": "deleted"})


@method("session.close")
def _session_close(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    _finalize_session(session, end_reason="tui_close")
    sid = params.get("session_id", "")
    _sessions.pop(sid, None)
    _clear_pending(sid)
    return _ok(rid, {"status": "closed"})


@method("session.status")
def _session_status(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return _ok(rid, {"running": False, "history_length": 0})
    with session.get("history_lock", threading.Lock()):
        hl = len(session.get("history", []))
    return _ok(
        rid,
        {
            "running": session.get("running", False),
            "history_length": hl,
            "model": _resolve_model(),
        },
    )


@method("session.title")
def _session_title(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    title = params.get("title", "")
    session["pending_title"] = title
    return _ok(rid, {"status": "ok"})


@method("session.history")
def _session_history(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    with session.get("history_lock", threading.Lock()):
        history = list(session.get("history", []))
    return _ok(rid, {"messages": history})


@method("session.usage")
def _session_usage(rid, params: dict) -> dict:
    session = _sessions.get(params.get("session_id", ""))
    usage = {}
    if session:
        agent = session.get("agent")
        if agent:
            usage = _get_usage(agent)
    return _ok(rid, {"usage": usage})


@method("session.steer")
def _session_steer(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    instruction = params.get("instruction", "")
    if instruction:
        with session.get("history_lock", threading.Lock()):
            session.setdefault("history", []).append({
                "role": "user",
                "content": f"[Steering instruction: {instruction}]",
            })
            session["history_version"] = int(session.get("history_version", 0)) + 1
    return _ok(rid, {"status": "ok"})


@method("session.undo")
def _session_undo(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    with session.get("history_lock", threading.Lock()):
        h = session.get("history", [])
        if h:
            session["history"] = h[:-1]
            session["history_version"] = int(session.get("history_version", 0)) + 1
    return _ok(rid, {"status": "ok"})


@method("session.interrupt")
def _session_interrupt(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    session["running"] = False
    agent = session.get("agent")
    if agent and hasattr(agent, "interrupt"):
        try:
            agent.interrupt()
        except Exception:
            pass
    _clear_pending(params.get("session_id", ""))
    return _ok(rid, {"status": "interrupted"})


@method("session.compress")
def _session_compress(rid, params: dict) -> dict:
    session, err = _sess(params, rid)
    if err:
        return err

    agent = session.get("agent")
    if not agent:
        return _err(rid, 5001, "no agent for compression")

    with session["history_lock"]:
        history = list(session.get("history", []))
        history_version = int(session.get("history_version", 0))

    if len(history) < 4:
        return _ok(rid, {"removed": 0, "usage": _get_usage(agent)})

    try:
        compressed, _ = agent._compress_context(history, None)
    except Exception as e:
        return _err(rid, 5001, f"compression failed: {e}")

    with session["history_lock"]:
        if int(session.get("history_version", 0)) != history_version:
            return _ok(rid, {"removed": 0, "usage": _get_usage(agent)})
        session["history"] = compressed
        session["history_version"] = history_version + 1

    return _ok(rid, {
        "removed": len(history) - len(compressed),
        "usage": _get_usage(agent),
    })


@method("session.branch")
def _session_branch(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err

    new_sid = uuid.uuid4().hex[:8]
    new_key = _new_session_key()
    _enable_gateway_prompts()

    with session.get("history_lock", threading.Lock()):
        branch_history = list(session.get("history", []))

    agent = session.get("agent")
    new_agent = None
    if agent:
        try:
            new_agent = _build_agent(new_sid, new_key, session_id=new_key)
        except NotImplementedError:
            pass

    _sessions[new_sid] = {
        "agent": new_agent,
        "session_key": new_key,
        "history": branch_history,
        "history_lock": threading.Lock(),
        "history_version": 0,
        "running": False,
        "attached_images": [],
        "cols": session.get("cols", 80),
        "slash_worker": None,
        "tool_progress_mode": session.get("tool_progress_mode", "all"),
        "tool_started_at": {},
        "edit_snapshots": {},
        "transport": current_transport() or _stdio_transport,
    }

    return _ok(
        rid,
        {
            "session_id": new_sid,
            "message_count": len(branch_history),
            "info": _session_info(new_agent) if new_agent else {},
        },
    )


@method("session.save")
def _session_save(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    key = session.get("session_key")
    if key:
        with session.get("history_lock", threading.Lock()):
            history = list(session.get("history", []))
        _save_session_file(key, {
            "title": session.get("pending_title") or "",
            "messages": history,
            "message_count": len(history),
            "started_at": time.time(),
            "source": "tui",
        })
    return _ok(rid, {"status": "saved"})


# ── Terminal ────────────────────────────────────────────────────────


@method("terminal.resize")
def _terminal_resize(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    session["cols"] = int(params.get("cols", 80))
    return _ok(rid, {"cols": session["cols"]})


# ── Prompt ──────────────────────────────────────────────────────────


@method("prompt.submit")
def _prompt_submit(rid, params: dict) -> dict:
    sid, text = params.get("session_id", ""), params.get("text", "")
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    with session["history_lock"]:
        if session.get("running"):
            return _err(rid, 4009, "session busy")
        session["running"] = True

    _start_agent_build(sid, session)

    def run_after_agent_ready() -> None:
        err_check = _wait_agent(session, rid)
        if err_check:
            _emit(
                "error", sid,
                {"message": err_check.get("error", {}).get("message", "agent init failed")},
            )
            with session["history_lock"]:
                session["running"] = False
            return
        _run_prompt_submit(rid, sid, session, text)

    threading.Thread(target=run_after_agent_ready, daemon=True).start()
    return _ok(rid, {"status": "streaming"})


def _run_prompt_submit(rid, sid: str, session: dict, text: str) -> None:
    """Execute a prompt submission: build message, run agent, emit events."""
    with session["history_lock"]:
        history = list(session.get("history", []))
        history_version = int(session.get("history_version", 0))

    agent = session.get("agent")
    if agent is None:
        # No agent wired yet — echo the prompt and mark completion
        _emit("message.start", sid)
        _emit(
            "message.delta", sid,
            {"text": f"[Lyra TUI] Agent not yet connected. Your message was received:\n\n{text}"},
        )
        with session["history_lock"]:
            session["history"] = history + [{"role": "user", "content": text}]
            session["history_version"] = history_version + 1
            session["running"] = False
        _emit("message.complete", sid, {
            "text": "",
            "usage": {},
            "status": "complete",
        })
        return

    _emit("message.start", sid)
    cols = session.get("cols", 80)
    streamer = make_stream_renderer(cols)

    def _stream(delta):
        payload: dict[str, Any] = {"text": delta}
        if streamer and (r := streamer.feed(delta)) is not None:
            payload["rendered"] = r
        _emit("message.delta", sid, payload)

    try:
        result = agent.run_conversation(
            text,
            conversation_history=list(history),
            stream_callback=_stream,
        )
    except Exception as e:
        _emit("error", sid, {"message": f"agent error: {e}"})
        with session["history_lock"]:
            session["running"] = False
        return

    raw = ""
    status = "complete"
    if isinstance(result, dict):
        if isinstance(result.get("messages"), list):
            with session["history_lock"]:
                if int(session.get("history_version", 0)) == history_version:
                    session["history"] = result["messages"]
                    session["history_version"] = history_version + 1
        raw = result.get("final_response", "")
        status = "interrupted" if result.get("interrupted") else "error" if result.get("error") else "complete"
    else:
        raw = str(result)

    payload: dict[str, Any] = {"text": raw, "usage": _get_usage(agent), "status": status}
    rendered = render_message(raw, cols)
    if rendered:
        payload["rendered"] = rendered
    _emit("message.complete", sid, payload)

    with session["history_lock"]:
        session["running"] = False


@method("prompt.background")
def _prompt_background(rid, params: dict) -> dict:
    """Submit a prompt to a background agent."""
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    text = params.get("text", "")
    with session["history_lock"]:
        session.setdefault("history", []).append({
            "role": "user",
            "content": f"[Background task: {text}]",
        })
        session["history_version"] = int(session.get("history_version", 0)) + 1
    return _ok(rid, {"status": "queued"})


# ── Config ──────────────────────────────────────────────────────────


@method("config.get")
def _config_get(rid, params: dict) -> dict:
    key = params.get("key", "")
    if key == "full":
        return _ok(rid, {"config": _load_cfg()})
    if key == "prompt":
        return _ok(rid, {"prompt": _load_cfg().get("custom_prompt", "")})
    if key == "profile":
        return _ok(rid, {"home": str(_LYRA_HOME), "display": str(_LYRA_HOME)})
    if key == "model":
        return _ok(rid, {"model": _resolve_model()})
    if key == "reasoning":
        return _ok(rid, {"value": "medium", "display": "hide"})
    if key == "details_mode":
        return _ok(rid, {"value": "collapsed"})
    if key == "thinking_mode":
        return _ok(rid, {"value": "collapsed"})
    if key == "fast":
        return _ok(rid, {"value": "normal"})
    if key == "statusbar":
        return _ok(rid, {"value": "top"})
    if key == "mtime":
        cfg_path = _LYRA_HOME / "config.yaml"
        try:
            return _ok(rid, {"mtime": cfg_path.stat().st_mtime if cfg_path.exists() else 0})
        except Exception:
            return _ok(rid, {"mtime": 0})
    if key == "verbose":
        return _ok(rid, {"value": "all"})
    if key == "mouse":
        return _ok(rid, {"value": "all"})
    return _err(rid, 4002, f"unknown config key: {key}")


@method("config.set")
def _config_set(rid, params: dict) -> dict:
    key, value = params.get("key", ""), params.get("value", "")

    if key == "model" and value:
        _write_config_key("model.default", value)
        os.environ["LYRA_MODEL"] = value
        return _ok(rid, {"key": key, "value": value, "warning": ""})

    if key == "fast":
        raw = str(value or "").strip().lower()
        if raw in {"", "toggle"}:
            current = _load_cfg().get("agent", {}).get("service_tier", "normal")
            nv = "normal" if current == "priority" else "fast"
        elif raw in {"fast", "on"}:
            nv = "fast"
        elif raw in {"normal", "off"}:
            nv = "normal"
        elif raw == "status":
            current = _load_cfg().get("agent", {}).get("service_tier", "normal")
            return _ok(rid, {"key": key, "value": "fast" if current == "priority" else "normal"})
        else:
            return _err(rid, 4002, f"unknown fast mode: {value}")
        _write_config_key("agent.service_tier", nv)
        return _ok(rid, {"key": key, "value": nv})

    if key == "verbose":
        cycle = ["off", "new", "all", "verbose"]
        session = _sessions.get(params.get("session_id", ""))
        cur = session.get("tool_progress_mode", "all") if session else "all"
        if value and value != "cycle":
            nv = str(value).strip().lower()
            if nv not in cycle:
                return _err(rid, 4002, f"unknown verbose mode: {value}")
        else:
            try:
                idx = cycle.index(cur)
            except ValueError:
                idx = 2
            nv = cycle[(idx + 1) % len(cycle)]
        if session:
            session["tool_progress_mode"] = nv
        _write_config_key("display.tool_progress", nv)
        return _ok(rid, {"key": key, "value": nv})

    if key == "reasoning":
        raw = str(value or "").strip().lower()
        valid = {"off", "low", "medium", "high"}
        if raw in valid:
            _write_config_key("agent.reasoning_effort", raw)
            return _ok(rid, {"key": key, "value": raw})
        return _err(rid, 4002, f"unknown reasoning effort: {value}")

    if key == "details_mode":
        allowed = frozenset({"hidden", "collapsed", "expanded"})
        nv = str(value).strip().lower()
        if nv not in allowed:
            return _err(rid, 4002, f"unknown details mode: {value}")
        _write_config_key("display.details_mode", nv)
        return _ok(rid, {"key": key, "value": nv})

    return _err(rid, 4002, f"unknown config key: {key}")


# ── Tools & System ──────────────────────────────────────────────────


@method("setup.status")
def _setup_status(rid, params: dict) -> dict:
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_model = bool(_resolve_model())
    # Write debug to crash log so we can inspect after run
    try:
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n=== setup.status debug · {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"ANTHROPIC_API_KEY={'set' if has_key else 'MISSING'}\n")
            f.write(f"ANTHROPIC_MODEL={os.environ.get('ANTHROPIC_MODEL','MISSING')!r}\n")
            f.write(f"LYRA_MODEL={os.environ.get('LYRA_MODEL','MISSING')!r}\n")
            f.write(f"_resolve_model()={_resolve_model()!r}\n")
            f.write(f"provider_configured={has_key or has_model}\n")
    except Exception:
        pass
    return _ok(rid, {"provider_configured": has_key or has_model})


@method("process.stop")
def _process_stop(rid, params: dict) -> dict:
    return _ok(rid, {"killed": False})


@method("reload.mcp")
def _reload_mcp(rid, params: dict) -> dict:
    return _ok(rid, {"status": "mcp_not_configured"})


@method("reload.env")
def _reload_env(rid, params: dict) -> dict:
    return _ok(rid, {"status": "ok"})


@method("commands.catalog")
def _commands_catalog(rid, params: dict) -> dict:
    return _ok(rid, {"commands": [
        {"name": "model", "help": "Switch the active model"},
        {"name": "clear", "help": "Clear the current conversation"},
        {"name": "help", "help": "Show available commands"},
        {"name": "compress", "help": "Compress conversation history"},
        {"name": "copy", "help": "Copy last response to clipboard"},
        {"name": "save", "help": "Save the current session"},
        {"name": "load", "help": "Load a session from history"},
        {"name": "stats", "help": "Show usage statistics"},
    ]})


@method("command.resolve")
def _command_resolve(rid, params: dict) -> dict:
    input_text = params.get("text", "").strip()
    commands = {
        "/model": {"command": "/model"},
        "/clear": {"command": "/clear"},
        "/help": {"command": "/help"},
        "/compress": {"command": "/compress"},
        "/copy": {"command": "/copy"},
        "/save": {"command": "/save"},
        "/stats": {"command": "/stats"},
        "/deep-research": {"command": "/deep-research", "lyra_only": True},
        "/knowledge-graph": {"command": "/knowledge-graph", "lyra_only": True},
        "/memory": {"command": "/memory", "lyra_only": True},
    }
    if not input_text.startswith("/"):
        return _ok(rid, {"resolved": None, "suggestions": list(commands.keys())})
    prefix = input_text.lower()
    matches = [k for k in commands if k.startswith(prefix)]
    if len(matches) == 1:
        return _ok(rid, {"resolved": {**commands[matches[0]], "name": matches[0]}})
    return _ok(rid, {"resolved": None, "suggestions": matches})


@method("model.options")
def _model_options(rid, params: dict) -> dict:
    return _ok(rid, {
        "options": [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "provider": "anthropic"},
            {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "provider": "anthropic"},
            {"id": "claude-haiku-3-5-20241022", "name": "Claude Haiku 3.5", "provider": "anthropic"},
        ],
        "current": _resolve_model(),
    })


@method("model.save_key")
def _model_save_key(rid, params: dict) -> dict:
    return _ok(rid, {"status": "ok"})


@method("model.disconnect")
def _model_disconnect(rid, params: dict) -> dict:
    return _ok(rid, {"status": "disconnected"})


@method("complete.path")
def _complete_path(rid, params: dict) -> dict:
    partial = params.get("partial", "")
    p = Path(partial).expanduser()
    parent = p.parent if partial else Path.cwd()
    prefix = p.name.lower()

    try:
        candidates = sorted(
            str(e) for e in parent.iterdir()
            if e.name.lower().startswith(prefix)
        )
    except (OSError, PermissionError):
        candidates = []

    return _ok(rid, {
        "candidates": candidates[:50],
        "prefix": prefix,
        "directory": str(parent),
    })


@method("complete.slash")
def _complete_slash(rid, params: dict) -> dict:
    partial = params.get("partial", "").lstrip("/").lower()
    slashes = [
        {"name": "model", "help": "Switch model"},
        {"name": "clear", "help": "Clear conversation"},
        {"name": "help", "help": "Show help"},
        {"name": "compress", "help": "Compress history"},
        {"name": "copy", "help": "Copy response"},
        {"name": "save", "help": "Save session"},
        {"name": "stats", "help": "Show stats"},
        {"name": "deep-research", "help": "Start deep research"},
        {"name": "knowledge-graph", "help": "Query knowledge graph"},
        {"name": "memory", "help": "Search memory"},
    ]
    if partial:
        matches = [s for s in slashes if s["name"].startswith(partial)]
    else:
        matches = slashes
    return _ok(rid, {"candidates": matches})


@method("tools.list")
def _tools_list(rid, params: dict) -> dict:
    return _ok(rid, {"toolsets": {}, "tools": []})


@method("tools.show")
def _tools_show(rid, params: dict) -> dict:
    return _ok(rid, {"tools": []})


@method("tools.configure")
def _tools_configure(rid, params: dict) -> dict:
    return _ok(rid, {"status": "ok"})


@method("plugins.list")
def _plugins_list(rid, params: dict) -> dict:
    return _ok(rid, {"plugins": []})


@method("agents.list")
def _agents_list(rid, params: dict) -> dict:
    return _ok(rid, {"agents": []})


@method("skills.manage")
def _skills_manage(rid, params: dict) -> dict:
    return _ok(rid, {"skills": [], "message": "Skills management not yet implemented"})


@method("skills.reload")
def _skills_reload(rid, params: dict) -> dict:
    return _ok(rid, {"status": "ok"})


@method("config.show")
def _config_show(rid, params: dict) -> dict:
    return _ok(rid, {"config": _load_cfg()})


@method("toolsets.list")
def _toolsets_list(rid, params: dict) -> dict:
    return _ok(rid, {"toolsets": []})


@method("cron.manage")
def _cron_manage(rid, params: dict) -> dict:
    return _ok(rid, {"entries": [], "message": "Cron management not yet implemented"})


@method("voice.toggle")
def _voice_toggle(rid, params: dict) -> dict:
    return _ok(rid, {"status": "unavailable"})


@method("voice.record")
def _voice_record(rid, params: dict) -> dict:
    return _ok(rid, {"status": "unavailable"})


@method("voice.tts")
def _voice_tts(rid, params: dict) -> dict:
    return _ok(rid, {"status": "unavailable"})


# ── Browser ─────────────────────────────────────────────────────────


@method("browser.manage")
def _browser_manage(rid, params: dict) -> dict:
    return _ok(rid, {"windows": [], "message": "Browser management not yet implemented"})


# ── Paste & Clipboard ────────────────────────────────────────────────


@method("clipboard.paste")
def _clipboard_paste(rid, params: dict) -> dict:
    return _ok(rid, {"text": ""})


@method("image.attach")
def _image_attach(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    paths = params.get("paths", [])
    if isinstance(paths, list):
        session.setdefault("attached_images", []).extend(paths)
    return _ok(rid, {"attached": len(paths) if isinstance(paths, list) else 0})


@method("input.detect_drop")
def _input_detect_drop(rid, params: dict) -> dict:
    return _ok(rid, {"type": "unknown"})


@method("paste.collapse")
def _paste_collapse(rid, params: dict) -> dict:
    return _ok(rid, {"collapsed": params.get("text", "")})


# ── Slash exec ──────────────────────────────────────────────────────


@method("slash.exec")
def _slash_exec(rid, params: dict) -> dict:
    session, err = _sess_nowait(params, rid)
    if err:
        return err
    command = params.get("command", "")
    worker = session.get("slash_worker")
    if worker is None:
        return _err(rid, 5004, "slash worker not available")
    try:
        output = worker.run(command)
        return _ok(rid, {"output": output})
    except RuntimeError as e:
        return _err(rid, 5004, str(e))


# ═══════════════════════════════════════════════════════════════════
# LYRA-SPECIFIC RPC METHODS (stubs)
# ═══════════════════════════════════════════════════════════════════


@method("lyra.deep_research_start")
def _lyra_deep_research_start(rid, params: dict) -> dict:
    """Start a deep research task.

    TODO: Wire to Lyra's deep research agent once available.
    """
    return _ok(rid, {
        "status": "not_implemented",
        "message": "Lyra Deep Research is not yet implemented.",
    })


@method("lyra.knowledge_graph_query")
def _lyra_knowledge_graph_query(rid, params: dict) -> dict:
    """Query the Lyra knowledge graph.

    TODO: Wire to Lyra's knowledge graph module once available.
    """
    return _ok(rid, {
        "status": "not_implemented",
        "message": "Lyra Knowledge Graph is not yet implemented.",
    })


@method("lyra.memory_search")
def _lyra_memory_search(rid, params: dict) -> dict:
    """Search Lyra's memory store.

    TODO: Wire to Lyra's memory system once available.
    """
    return _ok(rid, {
        "status": "not_implemented",
        "message": "Lyra Memory Search is not yet implemented.",
    })


@method("lyra.skill_invoke")
def _lyra_skill_invoke(rid, params: dict) -> dict:
    """Invoke a Lyra skill by name.

    TODO: Wire to Lyra's skill system once available.
    """
    return _ok(rid, {
        "status": "not_implemented",
        "message": "Lyra Skill Invocation is not yet implemented.",
    })


@method("lyra.stats")
def _lyra_stats(rid, params: dict) -> dict:
    """Return Lyra usage statistics.

    TODO: Wire to Lyra's statistics tracking once available.
    """
    return _ok(rid, {
        "sessions_total": len(_list_sessions(limit=9999)),
        "active_sessions": len(_sessions),
        "model": _resolve_model(),
    })


@method("lyra.deep_research_status")
def _lyra_deep_research_status(rid, params: dict) -> dict:
    """Check the status of a deep research task.

    TODO: Wire to Lyra's deep research agent once available.
    """
    return _ok(rid, {
        "status": "not_implemented",
        "message": "Lyra Deep Research status is not yet implemented.",
    })


# ═══════════════════════════════════════════════════════════════════
# PARALLAX COS SAFETY RPC METHODS
# ═══════════════════════════════════════════════════════════════════

# Module-level safety gate — one instance shared across all sessions
_safety_gate = None


def _get_safety_gate():
    """Lazy-init the safety gate on first use."""
    global _safety_gate
    if _safety_gate is None:
        from .safety_gate import SafetyGate

        _safety_gate = SafetyGate()
    return _safety_gate


@method("safety.status")
def _safety_status(rid, params: dict) -> dict:
    """Return comprehensive safety system status."""
    gate = _get_safety_gate()
    status = gate.status()
    return _ok(rid, {
        "governance_tier": status.governance_tier,
        "trust_score": status.trust_score,
        "containment_active": status.containment_active,
        "quarantine_active": status.quarantine_active,
        "tainted_count": status.tainted_count,
        "blocked_flows": status.blocked_flows,
        "escape_signals": status.escape_signals,
        "self_modify_attempts": status.self_modify_attempts,
        "violation_count": status.violation_count,
        "action_count": status.action_count,
    })


@method("safety.review_action")
def _safety_review_action(rid, params: dict) -> dict:
    """Review a proposed action through all safety layers.

    Returns the approval decision and which layer decided it.
    """
    action_text = params.get("action", "")
    if not action_text:
        return _err(rid, 4002, "action text required")

    gate = _get_safety_gate()
    decision = gate.validate_action(action_text)
    log_entries = [e for e in gate.review_log if e.get("action", "").startswith(action_text[:50])]
    last = log_entries[-1] if log_entries else {}

    return _ok(rid, {
        "decision": decision.value,
        "layer": last.get("layer", "unknown"),
        "governance_tier": gate.status().governance_tier,
        "trust_score": gate.status().trust_score,
    })


@method("safety.containment_status")
def _safety_containment_status(rid, params: dict) -> dict:
    """Return detailed containment status."""
    gate = _get_safety_gate()
    status = gate.status()
    return _ok(rid, {
        "quarantine_active": status.quarantine_active,
        "escape_signals": status.escape_signals,
        "self_modify_attempts": status.self_modify_attempts,
        "integrity_violations": 0,
    })


@method("safety.audit_log")
def _safety_audit_log(rid, params: dict) -> dict:
    """Return recent safety review audit log entries."""
    limit = int(params.get("limit", 20))
    gate = _get_safety_gate()
    log = list(gate.review_log)[-limit:]
    containment_audit = list(gate.containment_audit)[-limit:]
    return _ok(rid, {
        "review_log": log,
        "containment_audit": containment_audit,
    })


# ── Model Cascade Executor singleton ─────────────────────────────────
_cascade_executor = None


def _get_cascade_executor():
    """Lazy-init the model cascade executor on first use."""
    global _cascade_executor
    if _cascade_executor is None:
        from .cascade_executor import ModelCascadeExecutor

        _cascade_executor = ModelCascadeExecutor()
    return _cascade_executor


@method("routing.status")
def _routing_status(rid, params: dict) -> dict:
    """Return current routing strategy and model cascade status."""
    ex = _get_cascade_executor()
    return _ok(rid, {
        "strategy": ex.strategy.value,
        "model_count": ex.router.model_count,
        "decision_count": ex.router.decision_count,
        "turn_count": ex.router.turn_count,
        "router_snapshot": ex.router.snapshot(),
    })


@method("routing.cost_summary")
def _routing_cost_summary(rid, params: dict) -> dict:
    """Return cost summary across all model tiers."""
    ex = _get_cascade_executor()
    return _ok(rid, ex.cost_summary())


@method("routing.snapshot")
def _routing_snapshot(rid, params: dict) -> dict:
    """Return full routing snapshot with costs."""
    ex = _get_cascade_executor()
    return _ok(rid, ex.snapshot())


@method("routing.set_strategy")
def _routing_set_strategy(rid, params: dict) -> dict:
    """Update the routing strategy at runtime."""
    from lyra_model_router import RoutingStrategy

    strategy_name = params.get("strategy", "cost_optimal")
    try:
        new_strategy = RoutingStrategy(strategy_name)
    except ValueError:
        return _err(rid, f"Unknown routing strategy: {strategy_name}")
    ex = _get_cascade_executor()
    ex.strategy = new_strategy
    return _ok(rid, {"strategy": new_strategy.value})


# ── Unified Memory singleton ────────────────────────────────────────
_memory_orchestrator = None


def _get_memory_orchestrator():
    """Lazy-init the unified memory orchestrator on first use."""
    global _memory_orchestrator
    if _memory_orchestrator is None:
        from .unified_memory import UnifiedMemoryOrchestrator

        _memory_orchestrator = UnifiedMemoryOrchestrator(
            db_path=str(_LYRA_HOME / "memory")
        )
        _memory_orchestrator.initialize()
    return _memory_orchestrator


@method("memory.stats")
def _memory_stats(rid, params: dict) -> dict:
    """Return aggregated memory stats across all tiers."""
    orch = _get_memory_orchestrator()
    stats = orch.stats()
    return _ok(rid, {
        "working_entries": stats.working_entries,
        "working_tokens": stats.working_tokens,
        "episodic_events": stats.episodic_events,
        "semantic_facts": stats.semantic_facts,
        "procedural_count": stats.procedural_count,
        "kg_nodes": stats.kg_nodes,
        "kg_edges": stats.kg_edges,
        "token_index_docs": stats.token_index_docs,
        "total_memories": stats.total_memories,
        "active_memories": stats.active_memories,
        "dormant_memories": stats.dormant_memories,
        "last_consolidation": stats.last_consolidation,
        "budget_status": stats.budget_status,
    })


@method("memory.query")
def _memory_query(rid, params: dict) -> dict:
    """Cross-tier memory query."""
    query = params.get("query", "")
    top_k = int(params.get("top_k", 10))
    tiers = tuple(params.get("tiers", ["working", "episodic", "semantic"]))
    orch = _get_memory_orchestrator()
    results = orch.query(query, top_k=top_k, tiers=tiers)
    return _ok(rid, {
        "query": query,
        "results": [
            {"tier": r.tier, "content": r.content, "score": r.score, "metadata": r.metadata}
            for r in results
        ],
    })


@method("memory.consolidate")
def _memory_consolidate(rid, params: dict) -> dict:
    """Trigger memory consolidation across tiers."""
    deep = bool(params.get("deep", False))
    orch = _get_memory_orchestrator()
    result = orch.consolidate(deep=deep)
    return _ok(rid, result)


@method("memory.dream_cycle")
def _memory_dream_cycle(rid, params: dict) -> dict:
    """Run one dream cycle for offline enrichment."""
    orch = _get_memory_orchestrator()
    result = orch.dream_cycle()
    return _ok(rid, result)


@method("memory.snapshot")
def _memory_snapshot(rid, params: dict) -> dict:
    """Return full memory system snapshot."""
    orch = _get_memory_orchestrator()
    return _ok(rid, orch.snapshot())


# ── Agent Fleet singleton ───────────────────────────────────────────
_agent_fleet = None


def _get_agent_fleet():
    """Lazy-init the unified agent fleet on first use."""
    global _agent_fleet
    if _agent_fleet is None:
        from .agent_fleet import UnifiedAgentFleet

        _agent_fleet = UnifiedAgentFleet()
        _agent_fleet.initialize()
    return _agent_fleet


@method("fleet.status")
def _fleet_status(rid, params: dict) -> dict:
    """Return current fleet operational status."""
    fleet = _get_agent_fleet()
    s = fleet.status()
    return _ok(rid, {
        "active_agents": s.active_agents,
        "idle_agents": s.idle_agents,
        "total_agents": s.total_agents,
        "pending_tasks": s.pending_tasks,
        "running_tasks": s.running_tasks,
        "completed_tasks": s.completed_tasks,
        "failed_tasks": s.failed_tasks,
        "squads": s.squads,
        "throughput": s.throughput,
        "state": s.state,
    })


@method("fleet.submit_task")
def _fleet_submit_task(rid, params: dict) -> dict:
    """Submit a task to the fleet."""
    fleet = _get_agent_fleet()
    task_id = fleet.submit_task(
        description=params.get("description", ""),
        category=params.get("category", "general"),
        priority=float(params.get("priority", 1.0)),
    )
    return _ok(rid, {"task_id": task_id})


@method("fleet.fan_out")
def _fleet_fan_out(rid, params: dict) -> dict:
    """Fan-out multiple tasks to the fleet."""
    fleet = _get_agent_fleet()
    tasks = params.get("tasks", [])
    ids = fleet.fan_out(tasks)
    return _ok(rid, {"task_ids": ids})


@method("fleet.squads")
def _fleet_squads(rid, params: dict) -> dict:
    """List active squads."""
    fleet = _get_agent_fleet()
    squads = fleet.list_squads()
    return _ok(rid, {
        "squads": [{"id": s.id, "name": s.name, "leader": s.leader, "members": s.members} for s in squads]
    })


@method("fleet.create_squad")
def _fleet_create_squad(rid, params: dict) -> dict:
    """Create a new agent squad."""
    fleet = _get_agent_fleet()
    squad = fleet.create_squad(
        name=params.get("name", "default"),
        roles=params.get("roles", None),
    )
    return _ok(rid, {"id": squad.id, "name": squad.name, "leader": squad.leader, "members": squad.members})


@method("fleet.agents")
def _fleet_agents(rid, params: dict) -> dict:
    """List all registered agents."""
    fleet = _get_agent_fleet()
    return _ok(rid, {"agents": fleet.list_agents()})


@method("fleet.snapshot")
def _fleet_snapshot(rid, params: dict) -> dict:
    """Return full fleet snapshot."""
    fleet = _get_agent_fleet()
    return _ok(rid, fleet.snapshot())


# ── Self-Evolution singleton ────────────────────────────────────────
_evolution_engine = None


def _get_evolution_engine():
    """Lazy-init the self-evolution engine on first use."""
    global _evolution_engine
    if _evolution_engine is None:
        from .self_evolution import SelfEvolutionEngine

        _evolution_engine = SelfEvolutionEngine()
        _evolution_engine.initialize()
    return _evolution_engine


@method("evolution.status")
def _evolution_status(rid, params: dict) -> dict:
    """Return self-evolution engine status."""
    eng = _get_evolution_engine()
    return _ok(rid, eng.status())


@method("evolution.snapshot")
def _evolution_snapshot(rid, params: dict) -> dict:
    """Return full evolution engine snapshot."""
    eng = _get_evolution_engine()
    return _ok(rid, eng.snapshot())


@method("evolution.set_goal")
def _evolution_set_goal(rid, params: dict) -> dict:
    """Register a new evolution goal."""
    eng = _get_evolution_engine()
    goal = eng.set_goal(
        description=params.get("description", ""),
        target_metric=params.get("target_metric", "fitness"),
        target_value=float(params.get("target_value", 1.0)),
    )
    return _ok(rid, {"id": goal.id, "description": goal.description, "status": goal.status})


@method("evolution.run_cycle")
def _evolution_run_cycle(rid, params: dict) -> dict:
    """Execute one evolution cycle."""
    eng = _get_evolution_engine()
    cycle = eng.run_cycle(
        goal_id=params.get("goal_id"),
        dry_run=bool(params.get("dry_run", False)),
    )
    return _ok(rid, {
        "id": cycle.id,
        "mutations_applied": cycle.mutations_applied,
        "improvement": cycle.improvement,
        "council_decision": cycle.council_decision,
        "duration_ms": cycle.duration_ms,
    })


@method("evolution.adjust_trust")
def _evolution_adjust_trust(rid, params: dict) -> dict:
    """Adjust trust score by delta."""
    eng = _get_evolution_engine()
    delta = float(params.get("delta", 0.0))
    new_trust = eng.adjust_trust(delta)
    return _ok(rid, {"trust_score": round(new_trust, 4), "level": eng.meta_state.level})


# ── Utility ─────────────────────────────────────────────────────────


@method("insights.get")
def _insights_get(rid, params: dict) -> dict:
    return _ok(rid, {"insights": []})


@method("rollback.list")
def _rollback_list(rid, params: dict) -> dict:
    return _ok(rid, {"checkpoints": []})


@method("rollback.restore")
def _rollback_restore(rid, params: dict) -> dict:
    return _ok(rid, {"status": "rollback_not_available"})


@method("rollback.diff")
def _rollback_diff(rid, params: dict) -> dict:
    return _ok(rid, {"diff": ""})


@method("delegation.status")
def _delegation_status(rid, params: dict) -> dict:
    return _ok(rid, {"status": "none"})


@method("delegation.pause")
def _delegation_pause(rid, params: dict) -> dict:
    return _ok(rid, {"status": "paused"})


@method("subagent.interrupt")
def _subagent_interrupt(rid, params: dict) -> dict:
    return _ok(rid, {"status": "ok"})


@method("shell.exec")
def _shell_exec(rid, params: dict) -> dict:
    """Execute a shell command (stub)."""
    return _ok(rid, {"output": "", "exit_code": 0})


@method("cli.exec")
def _cli_exec(rid, params: dict) -> dict:
    """Execute a CLI command (stub)."""
    return _ok(rid, {"output": "", "status": "not_implemented"})


# ── Usage helper ────────────────────────────────────────────────────


def _get_usage(agent) -> dict:
    g = lambda k, fb=None: getattr(agent, k, 0) or (getattr(agent, fb, 0) if fb else 0)
    return {
        "model": getattr(agent, "model", "") or "",
        "input": g("session_input_tokens", "session_prompt_tokens"),
        "output": g("session_output_tokens", "session_completion_tokens"),
        "cache_read": g("session_cache_read_tokens"),
        "cache_write": g("session_cache_write_tokens"),
        "reasoning": g("session_reasoning_tokens"),
        "total": g("session_total_tokens"),
        "calls": g("session_api_calls"),
    }

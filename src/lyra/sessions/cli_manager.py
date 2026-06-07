"""
Session CLI Manager — command-line session management for Lyra.

Provides a rich command-line interface for managing agent sessions
including listing, killing, resuming, forking, searching, and
backgrounding sessions.

Usage
-----
Commands are exposed under the ``lyra session`` subcommand::

    lyra session list [--status active|paused|completed|failed|archived]
    lyra session kill <session_id>
    lyra session resume <session_id>
    lyra session fork <session_id> [--name <new_name>]
    lyra session search <query> [--limit 20] [--agent <agent_id>]
    lyra session background <session_id>
    lyra session reattach <session_id>
    lyra session export <session_id> [--output <path>]
    lyra session import <path>
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from lyra.sessions.persist import SessionManager, SessionRecord, SessionStatus

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Session search
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single session match from a search operation.

    Attributes:
        session_id: The matched session.
        score: Relevance score (0.0 to 1.0).
        matched_fields: Which fields matched the query.
        snippet: Short text excerpt from the session.
    """

    session_id: str
    score: float
    matched_fields: list[str]
    snippet: str


class SessionSearch:
    """Search past sessions by content, date, agent, or status.

    Performs client-side search over the session metadata, steps, and
    context stored in the SessionManager.  Supports simple keyword
    matching with scoring.
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        agent_id: str | None = None,
        status: SessionStatus | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[SearchResult]:
        """Search sessions by keyword and optional filters.

        Args:
            query: Keyword(s) to search for in session content.
            limit: Maximum results to return.
            agent_id: Filter by agent identifier.
            status: Filter by session status.
            date_from: ISO date string (inclusive start).
            date_to: ISO date string (inclusive end).

        Returns:
            List of SearchResult objects ordered by score descending.
        """
        all_sessions = self._sm.list_sessions(status=status, limit=1000, offset=0)
        query_lower = query.lower()
        results: list[SearchResult] = []

        for record in all_sessions:
            # Filter by agent
            if agent_id and record.agent_id != agent_id:
                continue

            # Filter by date range
            if date_from:
                from_dt = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
                if record.created_at < from_dt:
                    continue
            if date_to:
                to_dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
                if record.created_at > to_dt:
                    continue

            matched_fields: list[str] = []
            score = 0.0

            # Search metadata (including session_id, agent_id)
            meta_str = json.dumps(record.metadata, default=str).lower()
            if query_lower in meta_str:
                matched_fields.append("metadata")
                score += 0.3

            # Search steps content
            for step in record.steps:
                step_str = json.dumps(step, default=str).lower()
                if query_lower in step_str:
                    if "steps" not in matched_fields:
                        matched_fields.append("steps")
                    score += 0.2
                    break  # count steps only once

            # Search context
            context_str = json.dumps(record.context, default=str).lower()
            if query_lower in context_str:
                matched_fields.append("context")
                score += 0.3

            # Search session_id and agent_id directly
            if query_lower in record.session_id.lower():
                matched_fields.append("session_id")
                score += 0.5
            if query_lower in record.agent_id.lower():
                matched_fields.append("agent_id")
                score += 0.4

            if score > 0:
                snippet = self._build_snippet(record, query_lower)
                results.append(SearchResult(
                    session_id=record.session_id,
                    score=min(score, 1.0),
                    matched_fields=matched_fields,
                    snippet=snippet,
                ))

        # Sort by score descending, then by updated_at descending
        results.sort(key=lambda r: (-r.score, r.session_id))
        return results[:limit]

    def search_by_content(self, query: str, *, limit: int = 20) -> list[SearchResult]:
        """Convenience: search only steps and context content."""
        return self.search(query, limit=limit)

    def search_by_date(
        self,
        date_from: str,
        date_to: str | None = None,
        *,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search sessions created within a date range."""
        return self.search(
            "",
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _build_snippet(record: SessionRecord, query: str) -> str:
        """Build a short text snippet highlighting the match."""
        # Try steps first
        for step in record.steps:
            step_str = json.dumps(step, default=str)
            if query in step_str.lower():
                idx = step_str.lower().find(query)
                start = max(0, idx - 40)
                end = min(len(step_str), idx + len(query) + 40)
                snippet = step_str[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(step_str):
                    snippet = snippet + "..."
                return snippet

        # Fall back to metadata
        meta_str = json.dumps(record.metadata, default=str)
        if query and query in meta_str.lower():
            idx = meta_str.lower().find(query)
            start = max(0, idx - 40)
            end = min(len(meta_str), idx + len(query) + 40)
            snippet = meta_str[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(meta_str):
                snippet = snippet + "..."
            return snippet

        return f"session_id={record.session_id}, status={record.status.value}"


# ---------------------------------------------------------------------------
# Context compression
# ---------------------------------------------------------------------------


@dataclass
class CompressedRollup:
    """A compressed summary of a session's history.

    Attributes:
        session_id: The compressed session.
        original_steps: Number of steps before compression.
        compressed_steps: Number of steps after compression.
        summary: A textual summary of the session's work.
        key_decisions: Important decisions made during the session.
    """

    session_id: str
    original_steps: int
    compressed_steps: int
    summary: str
    key_decisions: list[str] = field(default_factory=list)


class ContextCompressionOnResume:
    """Compacts session history when restoring a session to reduce context.

    When a session is resumed after being paused or backgrounded, the
    full step history may be too large to reload.  This compressor
    summarises older steps into a compact form while keeping recent
    steps intact.
    """

    # Number of most recent steps to keep in full detail
    KEEP_RECENT_STEPS = 10

    def __init__(self, session_manager: SessionManager) -> None:
        self._sm = session_manager

    def compress_for_resume(
        self,
        session_id: str,
        keep_recent: int = KEEP_RECENT_STEPS,
    ) -> CompressedRollup | None:
        """Compress a session's history for efficient resume.

        Args:
            session_id: The session to compress.
            keep_recent: Number of most recent steps to keep intact.

        Returns:
            A CompressedRollup describing the compression, or None if
            the session does not exist or has no steps.
        """
        record = self._sm.get_session(session_id)
        if record is None:
            return None

        steps = record.steps
        if not steps:
            return None

        original_count = len(steps)

        # Keep the most recent steps untouched
        recent_steps = steps[-keep_recent:] if keep_recent > 0 else []
        older_steps = steps[:-keep_recent] if keep_recent > 0 else []

        if older_steps:
            # Build a compressed summary from older steps
            summary = self._summarise_steps(older_steps)
            key_decisions = self._extract_decisions(older_steps)

            # Replace older steps with a single compressed step
            compressed_steps = [
                {
                    "type": "compressed_history",
                    "original_step_count": len(older_steps),
                    "summary": summary,
                    "key_decisions": key_decisions,
                    "compressed_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
            compressed_steps.extend(recent_steps)
            record.steps = compressed_steps
        else:
            summary = "All steps retained in full detail."
            key_decisions = []
            compressed_steps = steps

        # Persist the compressed record
        updated_context = {**record.context, "_compressed": True, "_original_steps": original_count}
        self._sm._conn.execute(
            "UPDATE sessions SET context=? WHERE session_id=?",
            (
                json.dumps(updated_context),
                session_id,
            ),
        )
        self._sm._conn.commit()

        # Update in-memory cache to reflect the persisted change
        record.context = updated_context

        return CompressedRollup(
            session_id=session_id,
            original_steps=original_count,
            compressed_steps=len(compressed_steps),
            summary=summary,
            key_decisions=key_decisions,
        )

    # ------------------------------------------------------------------
    # Internal summarisers (placeholder — in production these would use an LLM)
    # ------------------------------------------------------------------

    @staticmethod
    def _summarise_steps(steps: list[dict[str, Any]]) -> str:
        """Build a compact summary of old steps.

        In production this would call an LLM.  Here we return a
        structural summary.
        """
        tool_calls = sum(1 for s in steps if s.get("type") == "tool_call")
        messages = sum(1 for s in steps if s.get("type") in ("user_message", "assistant_message"))
        errors = sum(1 for s in steps if s.get("type") == "error")

        parts = [f"{len(steps)} total steps"]
        if tool_calls:
            parts.append(f"{tool_calls} tool calls")
        if messages:
            parts.append(f"{messages} messages")
        if errors:
            parts.append(f"{errors} errors")

        return ", ".join(parts)

    @staticmethod
    def _extract_decisions(steps: list[dict[str, Any]]) -> list[str]:
        """Extract apparent key decisions from step metadata.

        In production this would use an LLM.
        """
        decisions = []
        for step in steps:
            if step.get("type") == "decision" and step.get("description"):
                decisions.append(step["description"])
        return decisions


# ---------------------------------------------------------------------------
# Background session
# ---------------------------------------------------------------------------


@dataclass
class BackgroundSession:
    """A session that has been moved to the background.

    Attributes:
        session_id: The backgrounded session.
        pid: OS process ID of the backgrounded session process.
        started_at: Unix timestamp of when the session was backgrounded.
        state_file: Path to the state file for reattachment.
    """

    session_id: str
    pid: int
    started_at: float
    state_file: str


class SessionBackgrounder:
    """Move a session to the background (detach) and reattach later.

    Backgrounding allows a session to continue running in a separate
    process while the CLI returns to the prompt.  The session can be
    reattached later to resume interactive control.
    """

    def __init__(self, state_dir: str | Path = "") -> None:
        self._state_dir = Path(state_dir or self._default_state_dir())
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._backgrounded: dict[str, BackgroundSession] = {}

    # ------------------------------------------------------------------
    # Background / detach
    # ------------------------------------------------------------------

    def background(
        self,
        session_id: str,
        command: list[str],
    ) -> BackgroundSession | None:
        """Move a session to the background.

        Spawns *command* as a subprocess and stores its PID for later
        reattachment.

        Args:
            session_id: The session identifier.
            command: The command to run in the background.

        Returns:
            BackgroundSession info, or None if spawning failed.
        """
        if session_id in self._backgrounded:
            logger.warning("session already backgrounded", session_id=session_id)
            return None

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as exc:
            logger.error("failed to background session", session_id=session_id, error=str(exc))
            return None

        state_file = str(self._state_dir / f"{session_id}.json")
        bg = BackgroundSession(
            session_id=session_id,
            pid=process.pid,
            started_at=time.time(),
            state_file=state_file,
        )
        self._backgrounded[session_id] = bg
        self._save_state(bg)

        logger.info("session backgrounded", session_id=session_id, pid=process.pid)
        return bg

    # ------------------------------------------------------------------
    # Reattach
    # ------------------------------------------------------------------

    def reattach(self, session_id: str) -> bool:
        """Check if a backgrounded session can be reattached.

        Returns True if the background process is still running.
        """
        bg = self._backgrounded.get(session_id) or self._load_state(session_id)
        if bg is None:
            return False

        if not self._is_running(bg.pid):
            self._remove_state(session_id)
            return False

        return True

    def list_backgrounded(self) -> list[BackgroundSession]:
        """List all currently tracked background sessions."""
        # Prune dead processes
        for sid, bg in list(self._backgrounded.items()):
            if not self._is_running(bg.pid):
                self._backgrounded.pop(sid, None)

        return list(self._backgrounded.values())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _is_running(pid: int) -> bool:
        """Check if a process is running by PID."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _default_state_dir(self) -> str:
        """Return the default state directory."""
        default = Path.home() / ".lyra" / "background"
        default.mkdir(parents=True, exist_ok=True)
        return str(default)

    def _save_state(self, bg: BackgroundSession) -> None:
        """Persist background session state to disk."""
        try:
            data = {
                "session_id": bg.session_id,
                "pid": bg.pid,
                "started_at": bg.started_at,
            }
            Path(bg.state_file).write_text(json.dumps(data))
        except OSError:
            pass

    def _load_state(self, session_id: str) -> BackgroundSession | None:
        """Load background session state from disk."""
        state_file = self._state_dir / f"{session_id}.json"
        if not state_file.exists():
            return None
        try:
            data = json.loads(state_file.read_text())
            bg = BackgroundSession(
                session_id=data["session_id"],
                pid=data["pid"],
                started_at=data["started_at"],
                state_file=str(state_file),
            )
            self._backgrounded[bg.session_id] = bg
            return bg
        except (OSError, json.JSONDecodeError, KeyError):
            return None

    def _remove_state(self, session_id: str) -> None:
        """Remove persisted background state."""
        state_file = self._state_dir / f"{session_id}.json"
        try:
            state_file.unlink(missing_ok=True)
        except OSError:
            pass
        self._backgrounded.pop(session_id, None)


# ---------------------------------------------------------------------------
# Session CLI
# ---------------------------------------------------------------------------


class SessionCLI:
    """Command-line session management interface.

    Provides the implementation behind the ``lyra session`` subcommands.

    Usage::

        cli = SessionCLI(db_path="lyra_sessions.db")
        cli.cmd_list()          # lists active sessions
        cli.cmd_kill("lyra-abc")  # kills a session
        cli.cmd_resume("lyra-abc")  # resumes with compression
    """

    def __init__(self, db_path: str | Path = "lyra_sessions.db") -> None:
        self._sm = SessionManager(db_path)
        self._searcher = SessionSearch(self._sm)
        self._compressor = ContextCompressionOnResume(self._sm)
        self._backgrounder = SessionBackgrounder()

    # ------------------------------------------------------------------
    # list
    # ------------------------------------------------------------------

    def cmd_list(
        self,
        status: str = "",
        limit: int = 20,
        offset: int = 0,
        quiet: bool = False,
    ) -> list[dict[str, Any]]:
        """List sessions.

        Args:
            status: Filter by status string (``"active"``, ``"paused"``, etc.).
            limit: Maximum records.
            offset: Record offset.
            quiet: If True, just return dicts without printing.

        Returns:
            List of session dicts.
        """
        status_filter = SessionStatus(status) if status else None
        records = self._sm.list_sessions(status=status_filter, limit=limit, offset=offset)

        result = [
            {
                "session_id": r.session_id,
                "status": r.status.value,
                "agent_id": r.agent_id,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "steps": len(r.steps),
            }
            for r in records
        ]

        if not quiet:
            if not result:
                print("No sessions found.")
            else:
                headers = ["session_id", "status", "agent_id", "steps", "updated_at"]
                rows = [
                    [r["session_id"][:20], r["status"], r["agent_id"][:15],
                     str(r["steps"]), r["updated_at"][:19]]
                    for r in result
                ]
                self._print_table(headers, rows)

        return result

    # ------------------------------------------------------------------
    # kill
    # ------------------------------------------------------------------

    def cmd_kill(self, session_id: str, force: bool = False) -> bool:
        """Kill (delete) a session record.

        Args:
            session_id: The session to kill.
            force: If True, also attempt to kill the background process.

        Returns:
            True if the session was deleted.
        """
        success = self._sm.delete_session(session_id)
        if success:
            print(f"Session {session_id} deleted.")
        else:
            print(f"Session {session_id} not found.")

        # Kill background process if force
        if force:
            bg = self._backgrounder._load_state(session_id)
            if bg and SessionBackgrounder._is_running(bg.pid):
                try:
                    os.kill(bg.pid, signal.SIGTERM)
                    print(f"Background process {bg.pid} terminated.")
                except OSError:
                    print(f"Could not terminate process {bg.pid}.")
            self._backgrounder._remove_state(session_id)

        return success

    # ------------------------------------------------------------------
    # resume
    # ------------------------------------------------------------------

    def cmd_resume(
        self,
        session_id: str,
        compress: bool = True,
    ) -> dict[str, Any] | None:
        """Resume a session for interactive use.

        Optionally compresses the history before returning.

        Args:
            session_id: The session to resume.
            compress: If True, compress older steps.

        Returns:
            Session context dict, or None if not found.
        """
        record = self._sm.get_session(session_id)
        if record is None:
            print(f"Session {session_id} not found.")
            return None

        if compress:
            rollup = self._compressor.compress_for_resume(session_id)
            if rollup:
                print(
                    f"Resumed session {session_id}: "
                    f"{rollup.original_steps} steps compressed to {rollup.compressed_steps}."
                )

        # Re-read after potential compression
        record = self._sm.get_session(session_id)
        context = {
            "session_id": record.session_id,
            "status": record.status.value,
            "agent_id": record.agent_id,
            "steps": record.steps,
            "context": record.context,
            "metadata": record.metadata,
        }

        # Mark as active
        self._sm.update_session(session_id, status=SessionStatus.ACTIVE)

        print(f"Session {session_id} resumed.")
        return context

    # ------------------------------------------------------------------
    # fork
    # ------------------------------------------------------------------

    def cmd_fork(
        self,
        session_id: str,
        new_name: str = "",
        keep_steps: bool = True,
    ) -> dict[str, Any] | None:
        """Fork (clone) a session into a new session.

        Creates a fresh session record with the same initial context
        but a new session_id.

        Args:
            session_id: The source session.
            new_name: Optional name for the forked session.
            keep_steps: If True, copy steps from the source.

        Returns:
            The new session context dict, or None if source not found.
        """
        record = self._sm.get_session(session_id)
        if record is None:
            print(f"Session {session_id} not found.")
            return None

        import uuid
        new_id = f"lyra-{uuid.uuid4().hex[:12]}"

        new_metadata = dict(record.metadata)
        new_metadata["forked_from"] = session_id
        new_metadata["fork_name"] = new_name or f"fork-of-{session_id}"

        new_record = self._sm.create_session(
            session_id=new_id,
            agent_id=record.agent_id,
            metadata=new_metadata,
        )

        if keep_steps:
            for step in record.steps:
                self._sm.append_step(new_id, step)

        print(f"Forked {session_id} -> {new_id}")
        return {
            "session_id": new_id,
            "forked_from": session_id,
            "agent_id": record.agent_id,
            "steps": len(record.steps) if keep_steps else 0,
        }

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def cmd_search(
        self,
        query: str,
        *,
        limit: int = 20,
        agent_id: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        quiet: bool = False,
    ) -> list[dict[str, Any]]:
        """Search sessions.

        Args:
            query: Search keywords.
            limit: Max results.
            agent_id: Filter by agent.
            status: Filter by status.
            date_from: ISO date start.
            date_to: ISO date end.
            quiet: If True, skip printing.

        Returns:
            List of search result dicts.
        """
        status_filter = SessionStatus(status) if status else None
        results = self._searcher.search(
            query,
            limit=limit,
            agent_id=agent_id,
            status=status_filter,
            date_from=date_from,
            date_to=date_to,
        )

        result_dicts = [
            {
                "session_id": r.session_id,
                "score": round(r.score, 2),
                "matched_fields": r.matched_fields,
                "snippet": r.snippet,
            }
            for r in results
        ]

        if not quiet:
            if not result_dicts:
                print("No matching sessions found.")
            else:
                for r in result_dicts:
                    print(f"  [{r['score']:.2f}] {r['session_id']}")
                    print(f"        matched: {', '.join(r['matched_fields'])}")
                    print(f"        {r['snippet'][:100]}")
                    print()

        return result_dicts

    # ------------------------------------------------------------------
    # background / reattach
    # ------------------------------------------------------------------

    def cmd_background(self, session_id: str, command: list[str] | None = None) -> bool:
        """Move a session to the background.

        Args:
            session_id: The session to background.
            command: The command to run (default: a placeholder).

        Returns:
            True if successfully backgrounded.
        """
        cmd = command or [
            sys.executable, "-c",
            f"import time; time.sleep(3600); print('{session_id} completed')",
        ]
        bg = self._backgrounder.background(session_id, cmd)
        if bg is None:
            print(f"Failed to background session {session_id}.")
            return False

        print(f"Session {session_id} backgrounded (PID {bg.pid}).")
        print(f"Use 'lyra session reattach {session_id}' to check on it.")
        return True

    def cmd_reattach(self, session_id: str) -> bool:
        """Check if a backgrounded session is still running.

        Args:
            session_id: The session to reattach.

        Returns:
            True if the session is still alive.
        """
        alive = self._backgrounder.reattach(session_id)
        if alive:
            print(f"Session {session_id} is still running.")
        else:
            print(f"Session {session_id} is not running or not found.")
        return alive

    # ------------------------------------------------------------------
    # export / import
    # ------------------------------------------------------------------

    def cmd_export(self, session_id: str, output_path: str = "") -> str | None:
        """Export a session to a JSON file.

        Args:
            session_id: The session to export.
            output_path: Filesystem path (default: ``{session_id}.json``).

        Returns:
            The output file path, or None on failure.
        """
        record = self._sm.get_session(session_id)
        if record is None:
            print(f"Session {session_id} not found.")
            return None

        path = output_path or f"{session_id}.json"
        try:
            export = self._sm.export_session(session_id)
            if export is None:
                return None
            Path(path).write_text(json.dumps(export, indent=2, default=str))
            print(f"Session exported to {path}")
            return path
        except OSError as exc:
            print(f"Export failed: {exc}")
            return None

    def cmd_import(self, input_path: str) -> dict[str, Any] | None:
        """Import a session from a JSON file.

        Args:
            input_path: Path to the exported session JSON.

        Returns:
            The imported session dict, or None on failure.
        """
        try:
            raw = json.loads(Path(input_path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Import failed: {exc}")
            return None

        # Handle both wrapped export format and raw session record format.
        # If it is a wrapped export, pass it directly to import_session which
        # knows how to unpack it.
        if isinstance(raw, dict) and raw.get("lyra_session_export"):
            record = self._sm.import_session(raw)
            if record is None:
                print(f"Import failed: session may already exist. Check {input_path}")
                return None
        else:
            # Raw session dict — import directly
            record = SessionRecord.from_dict(raw)
            existing = self._sm.get_session(record.session_id)
            if existing is not None:
                print(f"Session {record.session_id} already exists. Skipping import.")
                return None
            self._sm.create_session(
                session_id=record.session_id,
                agent_id=record.agent_id,
                metadata=record.metadata,
            )
            for step in record.steps:
                self._sm.append_step(record.session_id, step)
            self._sm.update_session(
                record.session_id,
                status=record.status,
            )

        print(f"Session {record.session_id} imported.")
        return {
            "session_id": record.session_id,
            "status": record.status.value,
            "agent_id": record.agent_id,
            "steps": len(record.steps),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _print_table(headers: list[str], rows: list[list[str]]) -> None:
        """Print a simple aligned table to stdout."""
        col_widths = [
            max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
            for i, h in enumerate(headers)
        ]

        # Header
        header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        print(header_line)
        print("-" * len(header_line))

        # Rows
        for row in rows:
            print("  ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))))

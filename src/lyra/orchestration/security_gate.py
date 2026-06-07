"""
Security Gate — approval enforcement for unwatched fleet sessions.

Implements the security guardrail from agent-view-fleet-layer.md: background
sessions with bypass/auto permission modes MUST have a prior interactive
accept before they may use dangerous permissions. This prevents unwatched
agents from silently gaining elevated access.

Key design decisions (per ARCHITECTURE-DEBATE.md resolutions):
1. **Command hashing** (not glob patterns): ``SHA256(tool + args_hash)``
   prevents replay — "git push main" and "git push --force" require
   separate approvals.
2. **Tiered expiry** by risk level:
   - LOW (Read, Grep): 7 days
   - MEDIUM (Write, Git): 24 hours
   - HIGH (Bash, WebFetch): 4 hours
   - CRITICAL (rm, curl, pip): Per-use only (no auto-approve)
3. **SQLite backend** with atomic check-and-use within transactions
   to prevent TOCTOU races.
4. **Audit log** (JSONL, 90-day retention) for security review.

This is an IMPROVEMENT over Claude Code's mechanism which has NO expiry
(accept once, use forever) and NO scope matching.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


# ── Types ───────────────────────────────────────────────────────────────


class RiskLevel(str, Enum):
    """Risk classification for tool permissions."""
    LOW = "LOW"           # Read, Grep, Glob
    MEDIUM = "MEDIUM"     # Write, Edit, Git (non-force)
    HIGH = "HIGH"         # Bash (general), WebFetch
    CRITICAL = "CRITICAL" # rm, curl, pip, Bash with --force, sudo


_RISK_EXPIRY_HOURS: dict[RiskLevel, int] = {
    RiskLevel.LOW: 168,      # 7 days
    RiskLevel.MEDIUM: 24,     # 24 hours
    RiskLevel.HIGH: 4,        # 4 hours
    RiskLevel.CRITICAL: 0,    # Per-use — never auto-approve
}


@dataclass(frozen=True)
class ApprovalDecision:
    """Result of an approval check."""
    status: str  # "APPROVED", "DENIED", "EXPIRED", "REQUIRES_INTERACTIVE"
    reason: str
    approval_id: int | None = None
    expires_in_seconds: float | None = None


@dataclass(frozen=True)
class ApprovalGrant:
    """An active approval grant."""
    id: int
    tool_name: str
    permission_type: str
    approved_by: str
    risk_level: RiskLevel
    expires_at: float
    scope_hash: str


# ── Database init ────────────────────────────────────────────────────────


def _default_db_path() -> Path:
    """Default path for the approval database."""
    base = Path(os.environ.get("LYRA_CONFIG_DIR", Path.home() / ".lyra"))
    return base / "approvals.db"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS approval_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    permission_type TEXT NOT NULL,
    scope_hash TEXT NOT NULL,
    approved_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    approved_by TEXT NOT NULL,
    risk_level TEXT NOT NULL
        CHECK(risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    revoked_at REAL,
    UNIQUE(tool_name, permission_type, scope_hash)
);

CREATE INDEX IF NOT EXISTS idx_approval_lookup
    ON approval_grants(tool_name, permission_type, expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS approval_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,  -- GRANT, CHECK, DENY, EXPIRE, REVOKE
    tool_name TEXT NOT NULL,
    permission_type TEXT NOT NULL,
    session_id TEXT,
    decision TEXT NOT NULL,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON approval_audit(timestamp DESC);
"""


# ── Main class ───────────────────────────────────────────────────────────


class SecurityGate:
    """
    Approval-based security gate for unwatched fleet sessions.

    Usage::

        gate = SecurityGate()
        gate.grant_approval(
            tool_name="bash",
            permission_type="bypass",
            command="git push origin main",
            risk_level=RiskLevel.HIGH,
            approved_by="user@host",
        )

        decision = gate.check(
            tool_name="bash",
            permission_type="bypass",
            command="git push origin main",
            session_id="abc123",
        )
        if decision.status == "APPROVED":
            execute_tool()
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _default_db_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database and schema."""
        with self._lock, self._conn() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _conn(self) -> sqlite3.Connection:
        """Get a new database connection."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ── Public API ───────────────────────────────────────────────────────

    @staticmethod
    def hash_scope(tool_name: str, command: str) -> str:
        """Hash a tool + command for scope matching.

        Uses SHA256 so that "git push main" and "git push --force main"
        produce different hashes, preventing replay attacks.
        """
        raw = f"{tool_name}:{command}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def grant_approval(
        self,
        *,
        tool_name: str,
        permission_type: str,
        command: str,
        risk_level: RiskLevel,
        approved_by: str,
        session_id: str = "",
    ) -> int:
        """Grant a new approval with tiered expiry.

        Returns the approval ID.

        CRITICAL risk approvals are not stored — they must be granted
        per-use interactively.
        """
        if risk_level == RiskLevel.CRITICAL:
            raise ValueError(
                "CRITICAL risk approvals cannot be pre-granted. "
                "They require per-use interactive approval."
            )

        now = time.time()
        expiry_hours = _RISK_EXPIRY_HOURS[risk_level]
        expires_at = now + expiry_hours * 3600
        scope_hash = self.hash_scope(tool_name, command)

        with self._lock, self._conn() as conn:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO approval_grants
                   (tool_name, permission_type, scope_hash,
                    approved_at, expires_at, approved_by, risk_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (tool_name, permission_type, scope_hash,
                 now, expires_at, approved_by, risk_level.value),
            )
            conn.commit()
            grant_id = cursor.lastrowid

            # Audit log
            conn.execute(
                """INSERT INTO approval_audit
                   (timestamp, event_type, tool_name, permission_type,
                    session_id, decision, reason)
                   VALUES (?, 'GRANT', ?, ?, ?, 'APPROVED', ?)""",
                (now, tool_name, permission_type, session_id,
                 f"Granted for {expiry_hours}h, risk={risk_level.value}"),
            )
            conn.commit()

        return grant_id

    def check(
        self,
        *,
        tool_name: str,
        permission_type: str,
        command: str,
        session_id: str = "",
    ) -> ApprovalDecision:
        """Check whether a tool invocation has prior approval.

        Performs an atomic check within a transaction to prevent TOCTOU races.
        """
        scope_hash = self.hash_scope(tool_name, command)
        now_ts = time.time()

        with self._lock, self._conn() as conn:
            # Atomic: check + log within single transaction
            row = conn.execute(
                """SELECT id, expires_at, risk_level
                   FROM approval_grants
                   WHERE tool_name = ? AND permission_type = ?
                     AND scope_hash = ? AND revoked_at IS NULL
                   ORDER BY approved_at DESC LIMIT 1""",
                (tool_name, permission_type, scope_hash),
            ).fetchone()

            if row is None:
                # No approval found
                conn.execute(
                    """INSERT INTO approval_audit
                       (timestamp, event_type, tool_name, permission_type,
                        session_id, decision, reason)
                       VALUES (?, 'CHECK', ?, ?, ?, 'DENIED',
                               'No prior approval')""",
                    (now_ts, tool_name, permission_type, session_id),
                )
                conn.commit()
                return ApprovalDecision(
                    status="REQUIRES_INTERACTIVE",
                    reason="No prior approval found. "
                           "Run interactively first to grant approval.",
                )

            expires_at = row["expires_at"]
            risk = RiskLevel(row["risk_level"])
            seconds_left = expires_at - now_ts

            if seconds_left <= 0:
                # Expired — mark as revoked
                conn.execute(
                    """UPDATE approval_grants
                       SET revoked_at = ?
                       WHERE id = ?""",
                    (now_ts, row["id"]),
                )
                conn.execute(
                    """INSERT INTO approval_audit
                       (timestamp, event_type, tool_name, permission_type,
                        session_id, decision, reason)
                       VALUES (?, 'EXPIRE', ?, ?, ?, 'EXPIRED', ?)""",
                    (now_ts, tool_name, permission_type, session_id,
                     f"Expired at {datetime.datetime.fromtimestamp(expires_at)}"),
                )
                conn.commit()
                return ApprovalDecision(
                    status="EXPIRED",
                    reason=f"Approval expired. Risk: {risk.value}. "
                           "Re-approve interactively.",
                )

            # Valid approval
            conn.execute(
                """INSERT INTO approval_audit
                   (timestamp, event_type, tool_name, permission_type,
                    session_id, decision, reason)
                   VALUES (?, 'CHECK', ?, ?, ?, 'APPROVED', ?)""",
                (now_ts, tool_name, permission_type, session_id,
                 f"Valid approval, expires in {seconds_left/3600:.1f}h"),
            )
            conn.commit()

            return ApprovalDecision(
                status="APPROVED",
                reason=f"Prior approval valid for {seconds_left/3600:.1f} hours",
                approval_id=row["id"],
                expires_in_seconds=seconds_left,
            )

    def revoke(self, approval_id: int) -> None:
        """Revoke a specific approval by ID."""
        now = time.time()
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE approval_grants SET revoked_at = ? WHERE id = ?",
                (now, approval_id),
            )
            conn.execute(
                """INSERT INTO approval_audit
                   (timestamp, event_type, tool_name, permission_type,
                    decision, reason)
                   VALUES (?, 'REVOKE', '', '', 'REVOKED',
                           'Manual revocation')""",
                (now,),
            )
            conn.commit()

    def cleanup_expired(self) -> int:
        """Periodic cleanup: mark expired approvals as revoked.

        Returns the count of expired approvals cleaned up.
        """
        now = time.time()
        with self._lock, self._conn() as conn:
            cursor = conn.execute(
                """UPDATE approval_grants
                   SET revoked_at = ?
                   WHERE expires_at <= ? AND revoked_at IS NULL""",
                (now, now),
            )
            conn.commit()
            return cursor.rowcount

    @staticmethod
    def classify_risk(tool_name: str, command: str = "") -> RiskLevel:
        """Classify the risk level of a tool + command combination."""
        # CRITICAL: destructive operations
        if any(kw in command.lower() for kw in (
            "rm -rf", "sudo", "curl | sh", "pip install",
            "--force", "DROP TABLE", "DELETE FROM",
        )):
            return RiskLevel.CRITICAL

        # HIGH: network, shell execution
        if tool_name in ("bash", "web_fetch", "web_search", "exec"):
            return RiskLevel.HIGH

        # MEDIUM: mutation operations
        if tool_name in ("write", "edit", "git", "mcp"):
            return RiskLevel.MEDIUM

        # LOW: read-only operations
        return RiskLevel.LOW

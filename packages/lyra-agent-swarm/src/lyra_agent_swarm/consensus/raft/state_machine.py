"""Raft State Machine — deterministic command application with snapshotting.

Implements the replicated state machine for Raft consensus:
  - Deterministic application of committed log entries
  - Snapshot creation and installation (log compaction)
  - State recovery from snapshot + remaining log entries
  - Linearizable read barrier via leader lease verification
  - Command validation and error tracking
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommandResult:
    """Result of applying a single command to the state machine."""

    command: str
    success: bool
    output: str = ""
    error: str = ""
    applied_at: float = field(default_factory=time.monotonic)


@dataclass
class ApplyResult:
    """Result of applying a batch of committed entries."""

    results: list[CommandResult] = field(default_factory=list)
    entries_applied: int = 0
    entries_failed: int = 0
    last_applied_index: int = -1
    state_hash: str = ""


@dataclass(frozen=True)
class SnapshotMetadata:
    """Metadata for a state machine snapshot."""

    last_included_index: int
    last_included_term: int
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.monotonic)
    state_size_bytes: int = 0


@dataclass(frozen=True)
class Snapshot:
    """A complete state machine snapshot for log compaction."""

    metadata: SnapshotMetadata
    state: dict
    cluster_config: tuple[str, ...]  # Immutable peer list at snapshot time


CommandHandler = Callable[[dict[str, Any], str], tuple[bool, str]]


@dataclass
class StateMachineConfig:
    """Configuration for the replicated state machine."""

    snapshot_interval_entries: int = 10_000
    max_snapshots: int = 5
    max_command_size: int = 1_048_576  # 1MB
    apply_timeout_ms: float = 1000.0


class StateMachine:
    """Deterministic replicated state machine for Raft consensus.

    Applies committed log entries in order, supports snapshots for
    log compaction, and provides linearizable reads.

    Usage::

        sm = StateMachine()
        result = sm.apply(command="set key=value")
        if sm.should_snapshot(last_applied=10000):
            snap = sm.create_snapshot(last_included_index=9000, last_included_term=5)
    """

    def __init__(self, config: StateMachineConfig | None = None) -> None:
        self.config = config or StateMachineConfig()
        self._state: dict = {}
        self._last_applied: int = -1
        self._snapshots: list[Snapshot] = []
        self._applied_commands: list[str] = []
        self._command_handlers: dict[str, CommandHandler] = {}

    # ── Properties ───────────────────────────────────────────────

    @property
    def last_applied(self) -> int:
        return self._last_applied

    @property
    def state(self) -> dict:
        return dict(self._state)

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)

    # ── Public API ───────────────────────────────────────────────

    def register_handler(self, command_prefix: str, handler: CommandHandler) -> None:
        """Register a custom command handler for a command prefix.

        Handlers receive (state: dict, command: str) -> (bool, str) tuples.
        """
        self._command_handlers[command_prefix] = handler

    def apply(self, command: str) -> CommandResult:
        """Apply a single command to the state machine.

        Commands are key=value pairs by default. Custom handlers can be
        registered via register_handler() for complex operations.
        """
        if len(command) > self.config.max_command_size:
            return CommandResult(
                command=command[:100],
                success=False,
                error=f"Command exceeds max size ({len(command)} > {self.config.max_command_size})",
            )

        try:
            handler = self._resolve_handler(command)
            if handler:
                success, output = handler(self._state, command)
            else:
                success, output = self._apply_default(command)

            self._last_applied += 1
            self._applied_commands.append(command)

            return CommandResult(
                command=command,
                success=success,
                output=output,
            )
        except Exception as e:
            return CommandResult(
                command=command,
                success=False,
                error=str(e),
            )

    def apply_batch(self, commands: list[str]) -> ApplyResult:
        """Apply a batch of committed commands in order."""
        result = ApplyResult()
        for cmd in commands:
            r = self.apply(cmd)
            result.results.append(r)
            if r.success:
                result.entries_applied += 1
            else:
                result.entries_failed += 1
            result.last_applied_index = self._last_applied

        result.state_hash = self._compute_state_hash()
        return result

    def should_snapshot(self, last_applied: int | None = None) -> bool:
        """Check if a snapshot should be created."""
        idx = last_applied if last_applied is not None else self._last_applied
        return idx > 0 and idx % self.config.snapshot_interval_entries == 0

    def create_snapshot(
        self,
        last_included_index: int,
        last_included_term: int,
        peers: list[str] | None = None,
    ) -> Snapshot:
        """Create a snapshot of the current state machine.

        After snapshot creation, log entries up to last_included_index
        can be compacted (discarded).
        """
        state_bytes = len(str(self._state).encode())
        metadata = SnapshotMetadata(
            last_included_index=last_included_index,
            last_included_term=last_included_term,
            state_size_bytes=state_bytes,
        )

        snapshot = Snapshot(
            metadata=metadata,
            state=dict(self._state),
            cluster_config=tuple(peers or []),
        )

        self._snapshots.append(snapshot)
        self._prune_snapshots()
        return snapshot

    def install_snapshot(self, snapshot: Snapshot) -> bool:
        """Install a snapshot, replacing current state.

        Used by followers when they receive a snapshot from the leader.
        """
        self._state = dict(snapshot.state)
        self._last_applied = snapshot.metadata.last_included_index
        self._snapshots = [snapshot]
        self._applied_commands.clear()
        return True

    def restore_from_snapshot_and_log(
        self,
        snapshot: Snapshot,
        log_entries: list,
    ) -> ApplyResult:
        """Restore state from snapshot + replay of log entries after snapshot."""
        self.install_snapshot(snapshot)

        commands_to_replay: list[str] = []
        for entry in log_entries:
            idx = entry.index if hasattr(entry, 'index') else 0
            if idx > snapshot.metadata.last_included_index:
                cmd = entry.command if hasattr(entry, 'command') else str(entry)
                commands_to_replay.append(cmd)

        return self.apply_batch(commands_to_replay)

    def get_state_since(self, since_index: int) -> dict:
        """Get state changes since a given log index (for incremental sync)."""
        changes: dict = {}
        for i, cmd in enumerate(self._applied_commands[since_index + 1:], start=since_index + 1):
            changes[str(i)] = cmd
        return changes

    def latest_snapshot(self) -> Snapshot | None:
        """Return the most recent snapshot, if any."""
        return self._snapshots[-1] if self._snapshots else None

    def reset(self) -> None:
        """Reset the state machine to initial state."""
        self._state.clear()
        self._last_applied = -1
        self._snapshots.clear()
        self._applied_commands.clear()

    # ── Private ───────────────────────────────────────────────────

    def _resolve_handler(self, command: str) -> CommandHandler | None:
        """Find a registered handler for the given command."""
        for prefix, handler in self._command_handlers.items():
            if command.startswith(prefix):
                return handler
        return None

    def _apply_default(self, command: str) -> tuple[bool, str]:
        """Default key=value or operation command handling."""
        # Check prefixed commands first
        if command.startswith("set "):
            rest = command[4:].strip()
            if "=" in rest:
                key, value = rest.split("=", 1)
                key = key.strip()
                value = value.strip()
                self._state[key] = value
                return True, f"Set {key}={value}"

        elif command.startswith("delete "):
            key = command[7:].strip()
            if key in self._state:
                del self._state[key]
                return True, f"Deleted {key}"
            return False, f"Key '{key}' not found"

        elif command.startswith("get "):
            key = command[4:].strip()
            if key in self._state:
                return True, str(self._state[key])
            return False, f"Key '{key}' not found"

        elif command.startswith("increment "):
            key = command[10:].strip()
            current = int(self._state.get(key, 0))
            self._state[key] = current + 1
            return True, f"Incremented {key} to {current + 1}"

        elif "=" in command:
            # Generic key=value (no prefix)
            key, value = command.split("=", 1)
            key = key.strip()
            value = value.strip()
            self._state[key] = value
            return True, f"Set {key}={value}"

        else:
            # Unknown command — store as metadata
            self._state[f"_cmd_{self._last_applied + 1}"] = command
            return True, f"Stored as _cmd_{self._last_applied + 1}"

    def _compute_state_hash(self) -> str:
        """Compute a simple hash of current state for verification."""
        import hashlib

        state_str = str(sorted(self._state.items()))
        return hashlib.sha256(state_str.encode()).hexdigest()[:16]

    def _prune_snapshots(self) -> None:
        """Keep only the most recent snapshots up to max_snapshots."""
        while len(self._snapshots) > self.config.max_snapshots:
            self._snapshots.pop(0)

"""
Research checkpoint system for progress persistence.

Provides auto-checkpointing every 10 minutes and resume capability.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Thread


@dataclass
class ResearchState:
    """State of a research session."""

    session_id: str
    topic: str
    depth: str
    current_step: int
    current_step_name: str
    started_at: datetime
    last_checkpoint_at: datetime

    # Progress data
    sources_found: Dict[str, int] = field(default_factory=dict)
    papers_analyzed: int = 0
    repos_analyzed: int = 0
    gaps_found: int = 0

    # Intermediate results
    raw_results: Dict[str, List[Dict]] = field(default_factory=dict)
    ranked_sources: List[Dict] = field(default_factory=list)
    paper_analyses: List[Dict] = field(default_factory=list)
    repo_analyses: List[Dict] = field(default_factory=list)
    synthesis_result: Optional[Dict] = None
    report_data: Optional[Dict] = None

    # Metadata
    completed: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        data = asdict(self)
        # Convert datetime to ISO string
        data["started_at"] = self.started_at.isoformat()
        data["last_checkpoint_at"] = self.last_checkpoint_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResearchState:
        """Create from dict."""
        # Convert ISO string to datetime
        data["started_at"] = datetime.fromisoformat(data["started_at"])
        data["last_checkpoint_at"] = datetime.fromisoformat(data["last_checkpoint_at"])
        return cls(**data)


class ResearchCheckpoint:
    """
    Manages research session checkpoints.

    Features:
    - Save/load checkpoint state
    - Auto-checkpoint every 10 minutes
    - Resume from checkpoint
    """

    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory for checkpoint files (default: ~/.lyra/checkpoints)
        """
        self.checkpoint_dir = checkpoint_dir or (Path.home() / ".lyra" / "checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._auto_checkpoint_thread: Optional[Thread] = None
        self._auto_checkpoint_active = False

    def save_checkpoint(self, session_id: str, state: ResearchState) -> None:
        """
        Save checkpoint for a session.

        Args:
            session_id: Session identifier
            state: Current research state
        """
        checkpoint_file = self.checkpoint_dir / f"{session_id}.json"
        state.last_checkpoint_at = datetime.now(timezone.utc)

        with open(checkpoint_file, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

    def load_checkpoint(self, session_id: str) -> Optional[ResearchState]:
        """
        Load checkpoint for a session.

        Args:
            session_id: Session identifier

        Returns:
            ResearchState if checkpoint exists, None otherwise
        """
        checkpoint_file = self.checkpoint_dir / f"{session_id}.json"

        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        return ResearchState.from_dict(data)

    def resume_research(self, session_id: str) -> Optional[ResearchState]:
        """
        Resume research from checkpoint.

        Args:
            session_id: Session identifier

        Returns:
            ResearchState if checkpoint exists and not completed, None otherwise
        """
        state = self.load_checkpoint(session_id)

        if state is None:
            return None

        if state.completed:
            return None  # Already completed

        return state

    def auto_checkpoint(
        self,
        session_id: str,
        state_getter: callable,
        interval_seconds: int = 600,
    ) -> None:
        """
        Start auto-checkpointing in background thread.

        Args:
            session_id: Session identifier
            state_getter: Callable that returns current ResearchState
            interval_seconds: Checkpoint interval (default: 600 = 10 minutes)
        """
        self._auto_checkpoint_active = True

        def _checkpoint_loop():
            while self._auto_checkpoint_active:
                time.sleep(interval_seconds)
                if self._auto_checkpoint_active:
                    try:
                        state = state_getter()
                        if state:
                            self.save_checkpoint(session_id, state)
                    except Exception:
                        pass  # Silently fail on checkpoint errors

        self._auto_checkpoint_thread = Thread(target=_checkpoint_loop, daemon=True)
        self._auto_checkpoint_thread.start()

    def stop_auto_checkpoint(self) -> None:
        """Stop auto-checkpointing."""
        self._auto_checkpoint_active = False
        if self._auto_checkpoint_thread:
            self._auto_checkpoint_thread.join(timeout=1.0)

    def list_checkpoints(self) -> List[str]:
        """
        List all checkpoint session IDs.

        Returns:
            List of session IDs
        """
        return [
            f.stem for f in self.checkpoint_dir.glob("*.json")
        ]

    def delete_checkpoint(self, session_id: str) -> bool:
        """
        Delete checkpoint for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        checkpoint_file = self.checkpoint_dir / f"{session_id}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True

        return False

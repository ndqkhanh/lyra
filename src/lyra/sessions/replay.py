"""Session replay — reconstruct and resume from checkpointed sessions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SessionReplay:
    """Replay a session from its checkpointed state.

    Supports: full replay, resume from last checkpoint, time-travel to any turn.
    """

    session_id: str
    turns: list[dict] = field(default_factory=list)
    current_turn: int = 0
    _checkpoints: dict[int, dict] = field(default_factory=dict)

    def record_turn(self, user_input: str, agent_response: str,
                    tool_calls: list[dict] | None = None):
        """Record a conversation turn."""
        self.turns.append({
            "turn": len(self.turns),
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "agent": agent_response,
            "tool_calls": tool_calls or [],
        })
        self.current_turn = len(self.turns)

    def save_checkpoint(self, label: str):
        """Save a named checkpoint at the current turn."""
        self._checkpoints[self.current_turn] = {
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "turn": self.current_turn,
        }

    def rewind_to(self, turn: int) -> list[dict]:
        """Rewind conversation to a specific turn."""
        if turn < 0 or turn > len(self.turns):
            raise ValueError(f"Turn {turn} out of range [0, {len(self.turns)}]")
        self.current_turn = turn
        return self.turns[:turn]

    def resume_context(self) -> dict[str, Any]:
        """Get the context needed to resume from the current turn."""
        return {
            "session_id": self.session_id,
            "current_turn": self.current_turn,
            "total_turns": len(self.turns),
            "recent_turns": self.turns[max(0, self.current_turn - 5):self.current_turn],
            "checkpoints": list(self._checkpoints.keys()),
        }

    def export(self) -> dict:
        """Export the full session for serialization."""
        return {
            "session_id": self.session_id,
            "turns": self.turns,
            "checkpoints": self._checkpoints,
            "exported_at": datetime.now().isoformat(),
        }

    @classmethod
    def import_session(cls, data: dict) -> "SessionReplay":
        """Import a previously exported session."""
        replay = cls(session_id=data["session_id"])
        replay.turns = data["turns"]
        replay._checkpoints = data.get("checkpoints", {})
        replay.current_turn = len(replay.turns)
        return replay

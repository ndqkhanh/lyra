"""
Lyra Sessions — checkpointing, persistence, and cross-session management.

Git-native: sessions are versioned via git branches, enabling branching
timelines and semantic search across session history.

Key capabilities:
- **Checkpoint**: Save/resume session state at any point
- **Branching**: Create divergent session timelines from any checkpoint
- **Semantic search**: Find past sessions by content, not just timestamp
- **Provider-agnostic**: Session state includes provider configuration
"""

from __future__ import annotations

from .manager import SessionManager
from .models import Checkpoint, SessionConfig, SessionState

__all__ = ["Checkpoint", "SessionConfig", "SessionManager", "SessionState"]

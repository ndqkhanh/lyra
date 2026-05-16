"""
Warmup Pipeline Scheduler for L1 extraction.

Implements exponential warmup schedule:
    Turn 1 → Extract (1 turn of history)
    Turn 2 → Extract (2 turns of history)
    Turn 4 → Extract (4 turns of history)
    Turn 8 → Extract (8 turns of history)
    Turn N → Steady state (every 5 turns)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WarmupScheduler:
    """
    Manages extraction timing with exponential warmup.

    New sessions start with frequent extractions (1, 2, 4, 8 turns)
    then settle into steady state (every 5 turns).
    """

    def __init__(
        self,
        steady_state_interval: int = 5,
        max_warmup_threshold: int = 8,
    ):
        """
        Initialize warmup scheduler.

        Args:
            steady_state_interval: Turns between extractions in steady state
            max_warmup_threshold: Maximum warmup threshold before steady state
        """
        self.steady_state_interval = steady_state_interval
        self.max_warmup_threshold = max_warmup_threshold

        # Per-session state
        self.session_state = {}

        logger.info(
            f"Initialized WarmupScheduler: steady_state={steady_state_interval}, "
            f"max_warmup={max_warmup_threshold}"
        )

    def should_extract(self, session_id: str, current_turn: int) -> bool:
        """
        Determine if extraction should run for this turn.

        Args:
            session_id: Session identifier
            current_turn: Current turn number (1-indexed)

        Returns:
            True if extraction should run
        """
        # Initialize session state if needed
        if session_id not in self.session_state:
            self.session_state[session_id] = {
                "last_extraction_turn": 0,
                "next_threshold": 1,
                "in_steady_state": False,
            }

        state = self.session_state[session_id]
        last_extraction = state["last_extraction_turn"]
        next_threshold = state["next_threshold"]
        in_steady_state = state["in_steady_state"]

        # Check if we should extract
        should_extract = False

        if in_steady_state:
            # Steady state: extract every N turns
            turns_since_last = current_turn - last_extraction
            if turns_since_last >= self.steady_state_interval:
                should_extract = True
        else:
            # Warmup: extract at exponential thresholds
            turns_since_last = current_turn - last_extraction
            if turns_since_last >= next_threshold:
                should_extract = True

        # Update state if extracting
        if should_extract:
            state["last_extraction_turn"] = current_turn

            if not in_steady_state:
                # Update warmup threshold
                if next_threshold >= self.max_warmup_threshold:
                    # Transition to steady state
                    state["in_steady_state"] = True
                    logger.info(
                        f"Session {session_id} transitioned to steady state "
                        f"at turn {current_turn}"
                    )
                else:
                    # Double the threshold (exponential warmup)
                    state["next_threshold"] = next_threshold * 2

        logger.debug(
            f"Session {session_id} turn {current_turn}: "
            f"should_extract={should_extract}, "
            f"state={state}"
        )

        return should_extract

    def get_extraction_window(
        self, session_id: str, current_turn: int
    ) -> Optional[int]:
        """
        Get the number of recent turns to extract from.

        Args:
            session_id: Session identifier
            current_turn: Current turn number

        Returns:
            Number of turns to extract, or None if no extraction needed
        """
        if not self.should_extract(session_id, current_turn):
            return None

        state = self.session_state.get(session_id, {})
        last_extraction = state.get("last_extraction_turn", 0)

        # For first extraction, window is current_turn
        # For subsequent extractions, window is turns since last extraction
        if last_extraction == current_turn:
            # Just extracted, so window is from previous extraction to now
            # Get the previous last_extraction value
            if current_turn == 1:
                window = 1
            else:
                # This is tricky - we need to track previous extraction
                # For now, use a simple heuristic
                window = current_turn - (last_extraction - 1) if last_extraction > 1 else current_turn
        else:
            window = current_turn - last_extraction

        logger.debug(
            f"Session {session_id} extraction window: {window} turns "
            f"(from turn {last_extraction + 1} to {current_turn})"
        )

        return window

    def reset_session(self, session_id: str) -> None:
        """
        Reset warmup state for a session.

        Args:
            session_id: Session identifier
        """
        if session_id in self.session_state:
            del self.session_state[session_id]
            logger.info(f"Reset warmup state for session {session_id}")

    def get_stats(self) -> dict:
        """
        Get scheduler statistics.

        Returns:
            Dictionary with stats
        """
        total_sessions = len(self.session_state)
        steady_state_sessions = sum(
            1 for s in self.session_state.values() if s.get("in_steady_state", False)
        )
        warmup_sessions = total_sessions - steady_state_sessions

        return {
            "total_sessions": total_sessions,
            "warmup_sessions": warmup_sessions,
            "steady_state_sessions": steady_state_sessions,
            "steady_state_interval": self.steady_state_interval,
            "max_warmup_threshold": self.max_warmup_threshold,
        }

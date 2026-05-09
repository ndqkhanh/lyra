"""Background skill-review subpackage.

The review subsystem runs a *forked* :class:`AgentLoop` post-turn to
give the model a chance to consolidate what it just did into reusable
skills — without blocking the user's next prompt. This is the hermes
``_spawn_background_review`` pattern, adapted to our agent loop.
"""

from .background import SKILL_REVIEW_PROMPT, spawn_skill_review

__all__ = ["SKILL_REVIEW_PROMPT", "spawn_skill_review"]

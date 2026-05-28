"""
MemGrad — Memory-Guided Self-Optimization Pipeline.

Textual gradient descent on agent prompts using accumulated memory feedback.
Feedback Descent provides the optimization framework with dimension-free
convergence guarantees.

Source: MemGrad (GeaPE7iw1V) + Feedback Descent (Uw5G3H26ps), ICLR 2026 MemAgent Workshop.
"""

from lyra_memory.optimization.dual_memory import (
    CorrectiveIntention,
    ProspectiveMemory,
    RetrospectiveMemory,
)
from lyra_memory.optimization.feedback_descent import (
    FeedbackDescentOptimizer,
    FeedbackPair,
)
from lyra_memory.optimization.memgrad import (
    AgentTrajectory,
    FailurePattern,
    MemGradPipeline,
    RoleCluster,
    TextGrad,
)

__all__ = [
    "AgentTrajectory",
    "CorrectiveIntention",
    "FailurePattern",
    "FeedbackDescentOptimizer",
    "FeedbackPair",
    "MemGradPipeline",
    "ProspectiveMemory",
    "RetrospectiveMemory",
    "RoleCluster",
    "TextGrad",
]

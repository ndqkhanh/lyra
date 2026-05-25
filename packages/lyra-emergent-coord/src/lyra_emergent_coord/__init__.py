"""lyra-emergent-coord — Task-driven coalition formation with emergent coordination.

Provides:
- Coalition formation with bidding system and Shapley value computation
- Distributed leader election (bully, ring, raft-inspired)
- Multi-agent negotiation with Contract Net Protocol
- Emergent behavior detection and pattern recognition
- Swarm intelligence patterns (ACO, PSO, bee algorithm, flocking)
"""

from __future__ import annotations

from .coalition import (
    Bid,
    Coalition,
    CoalitionError,
    CoalitionFormationEngine,
    InsufficientCapabilitiesError,
    NoValidCoalitionError,
    TaskAdvertisement,
)
from .emergence import (
    EmergenceDetector,
    EmergenceError,
    EmergentBehavior,
    InsufficientDataError,
    InteractionPattern,
    NoveltyScore,
)
from .leadership import (
    ElectionAlgorithm,
    ElectionResult,
    ElectionTimeoutError,
    LeaderHealthMonitor,
    LeaderManager,
    LeaderRecord,
    LeaderState,
    LeadershipConflictError,
    LeadershipError,
    NoCandidateError,
)
from .negotiation import (
    AgreementViolationError,
    ConflictResolutionStrategy,
    ConflictResolver,
    Contract,
    ContractNetProtocol,
    DeadlockError,
    MultiRoundNegotiator,
    NegotiationError,
    NegotiationSession,
    NegotiationState,
    NegotiationTimeoutError,
    Offer,
)
from .swarm import (
    AntColonyOptimizer,
    BeeAlgorithm,
    Boid,
    FlockingSystem,
    FoodSource,
    Particle,
    ParticleSwarmOptimizer,
    Pheromone,
    StigmergySystem,
)

__version__ = "0.2.0"

__all__ = [
    # Coalition
    "TaskAdvertisement",
    "Bid",
    "Coalition",
    "CoalitionFormationEngine",
    "CoalitionError",
    "NoValidCoalitionError",
    "InsufficientCapabilitiesError",
    # Leadership
    "LeaderState",
    "ElectionAlgorithm",
    "ElectionResult",
    "LeaderRecord",
    "LeaderManager",
    "LeaderHealthMonitor",
    "LeadershipError",
    "ElectionTimeoutError",
    "NoCandidateError",
    "LeadershipConflictError",
    # Negotiation
    "Offer",
    "Contract",
    "NegotiationSession",
    "NegotiationState",
    "ConflictResolutionStrategy",
    "ContractNetProtocol",
    "MultiRoundNegotiator",
    "ConflictResolver",
    "NegotiationError",
    "NegotiationTimeoutError",
    "DeadlockError",
    "AgreementViolationError",
    # Emergence
    "InteractionPattern",
    "EmergentBehavior",
    "NoveltyScore",
    "EmergenceDetector",
    "EmergenceError",
    "InsufficientDataError",
    # Swarm
    "Pheromone",
    "Particle",
    "Boid",
    "FoodSource",
    "StigmergySystem",
    "AntColonyOptimizer",
    "ParticleSwarmOptimizer",
    "BeeAlgorithm",
    "FlockingSystem",
]

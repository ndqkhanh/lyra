"""lyra-recursive-link — RecursiveMAS-style latent-space inter-agent communication."""

from __future__ import annotations

from lyra_recursive_link.collaboration_patterns import (
    CollaborationConfig,
    CollaborationEngine,
    CollaborationPattern,
    CollaborationResult,
    DeliberationResult,
    DistillationResult,
    MixtureResult,
    SequentialResult,
    convergence_check,
)
from lyra_recursive_link.communication_bus import (
    BusConfig,
    BusMessage,
    BusStats,
    CommunicationBus,
    MessagePriority,
    Subscription,
)
from lyra_recursive_link.credit_assignment import (
    ContributionRecord,
    CreditAssignmentEngine,
    CreditConfig,
    CreditLedger,
    CreditScore,
    InnerLoopResult,
)
from lyra_recursive_link.exceptions import (
    BusError,
    CollaborationError,
    CreditAssignmentError,
    DecodingError,
    EncodingError,
    LinkError,
    MessageDeliveryError,
)
from lyra_recursive_link.latent_decoder import (
    DecodedMessage,
    DecodingConfig,
    LatentDecoder,
    compute_fidelity,
)
from lyra_recursive_link.latent_encoder import (
    CompressionMethod,
    EncodingConfig,
    LatentEncoder,
    LatentVector,
    compute_compression_ratio,
    similarity,
)
from lyra_recursive_link.recursive_link import (
    AggregationMethod,
    LinkConfig,
    LinkMetrics,
    RecursiveLink,
)

__all__ = [
    "AggregationMethod",
    "BusConfig",
    "BusError",
    "BusMessage",
    "BusStats",
    "CollaborationConfig",
    "CollaborationEngine",
    "CollaborationError",
    "CollaborationPattern",
    "CollaborationResult",
    "CommunicationBus",
    "CompressionMethod",
    "ContributionRecord",
    "CreditAssignmentEngine",
    "CreditAssignmentError",
    "CreditConfig",
    "CreditLedger",
    "CreditScore",
    "DecodedMessage",
    "DecodingConfig",
    "DecodingError",
    "DeliberationResult",
    "DistillationResult",
    "EncodingConfig",
    "EncodingError",
    "InnerLoopResult",
    "LatentDecoder",
    "LatentEncoder",
    "LatentVector",
    "LinkConfig",
    "LinkError",
    "LinkMetrics",
    "MessageDeliveryError",
    "MessagePriority",
    "MixtureResult",
    "RecursiveLink",
    "SequentialResult",
    "Subscription",
    "compute_compression_ratio",
    "compute_fidelity",
    "convergence_check",
    "similarity",
]

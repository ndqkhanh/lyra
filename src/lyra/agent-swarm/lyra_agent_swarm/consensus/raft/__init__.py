"""Raft consensus subpackage — leader election, log replication, state machine."""

from lyra.agent_swarm.consensus.raft.leader_election import (
    CandidateNomination,
    ElectionConfig,
    ElectionResult,
    LeaderElection,
    VoteRequest,
    VoteResponse,
)
from lyra.agent_swarm.consensus.raft.log_replication import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    LogReplication,
    ReplicationConfig,
    ReplicationResult,
)
from lyra.agent_swarm.consensus.raft.state_machine import (
    ApplyResult,
    CommandResult,
    Snapshot,
    SnapshotMetadata,
    StateMachine,
    StateMachineConfig,
)

__all__ = [
    # Leader Election
    "CandidateNomination",
    "ElectionConfig",
    "ElectionResult",
    "LeaderElection",
    "VoteRequest",
    "VoteResponse",
    # Log Replication
    "AppendEntriesRequest",
    "AppendEntriesResponse",
    "LogReplication",
    "ReplicationConfig",
    "ReplicationResult",
    # State Machine
    "ApplyResult",
    "CommandResult",
    "Snapshot",
    "SnapshotMetadata",
    "StateMachine",
    "StateMachineConfig",
]

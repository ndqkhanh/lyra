"""Marketplace + curator types — wire between projects and argus."""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Optional


class TrustTier(str, enum.Enum):
    """Argus's three-tier verdict for an MCP server."""

    TRUSTED = "trusted"
    SUSPICIOUS = "suspicious"
    REJECTED = "rejected"


@dataclass(frozen=True)
class TrustVerdict:
    """Argus's typed verdict on whether an MCP server may be installed.

    Composed from multiple signals: marketplace reputation (LobeHub /
    Smithery / Glama download counts + ratings), CVE-feed scan, scope-audit,
    source-code lineage, ICPEA-Identity tier of the calling user.
    """

    server_name: str
    tier: TrustTier
    score: float  # 0.0 .. 1.0 numeric for fine-grained policy
    reasons: tuple[str, ...] = ()
    expires_at: Optional[float] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at

    @property
    def installable(self) -> bool:
        """True if installation is allowed without --force."""
        if self.is_expired:
            return False
        return self.tier == TrustTier.TRUSTED


@dataclass(frozen=True)
class MCPServer:
    """One MCP server entry as the marketplace exposes it."""

    name: str
    description: str = ""
    capabilities: frozenset[str] = frozenset()  # exposed tool names
    permissions_required: frozenset[str] = frozenset()  # OAuth scopes
    source_url: str = ""
    upstream_marketplace: str = ""  # "lobehub" | "smithery" | "glama" | "fastmcp_cloud" | ""
    download_count: int = 0
    rating: float = 0.0  # 0.0 .. 5.0


@dataclass(frozen=True)
class InstallResult:
    """The outcome of an :meth:`MarketplaceHost.install_mcp` call."""

    server_name: str
    installed: bool
    verdict: TrustVerdict
    config: dict[str, Any] = field(default_factory=dict)
    permissions_negotiated: frozenset[str] = frozenset()
    note: str = ""


@dataclass
class TrajectoryRecord:
    """A trajectory submission to argus.curator from any consumer project.

    Decoupled from :class:`harness_core.forensic.Trajectory` so consumers can
    submit minimal info without the full forensic detail. The curator may
    request additional detail asynchronously.
    """

    project: str  # "polaris" | "lyra" | "mentat" | etc.
    trajectory_id: str
    task_signature: str
    actions: tuple[str, ...]  # action sequence
    outcome: str  # "success" | "failure" | "rolled_back"
    user_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubmitResult:
    """The outcome of submitting a trajectory to argus.curator."""

    accepted: bool
    submission_id: str = ""
    queued_for_review: bool = False
    note: str = ""


@dataclass(frozen=True)
class PromotedSkill:
    """A skill argus's curator has promoted from accumulated trajectories."""

    name: str
    description: str = ""
    source_project: str = ""  # which project submitted the seed trajectories
    promoted_at: float = 0.0  # epoch
    occurrence_count: int = 0
    eval_score: float = 0.0  # held-out eval score that justified promotion
    capabilities: frozenset[str] = frozenset()


__all__ = [
    "InstallResult",
    "MCPServer",
    "PromotedSkill",
    "SubmitResult",
    "TrajectoryRecord",
    "TrustTier",
    "TrustVerdict",
]

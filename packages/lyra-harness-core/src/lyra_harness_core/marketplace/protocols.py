"""MarketplaceHost + CuratorHost Protocols — the argus consumer interface."""
from __future__ import annotations

from typing import Any, Optional, Protocol

from .types import (
    InstallResult,
    MCPServer,
    PromotedSkill,
    SubmitResult,
    TrajectoryRecord,
    TrustVerdict,
)


class MarketplaceHost(Protocol):
    """Consumer-side adapter for argus's marketplace + trust gate.

    Production: wires :class:`argus.HostAdapter`. Tests: wires
    :class:`InMemoryMarketplaceHost` from :mod:`.stub_adapter`.
    """

    name: str

    def list_marketplace(
        self,
        *,
        filter: Optional[str] = None,
        top_k: int = 50,
        upstream: Optional[str] = None,
    ) -> list[MCPServer]:
        """List available MCP servers, optionally filtered.

        ``filter`` matches against name + description (substring).
        ``upstream`` restricts to a single source ("lobehub", "smithery", etc.).
        """
        ...

    def get_trust_verdict(self, server_name: str) -> Optional[TrustVerdict]:
        """Return argus's current verdict for a server, or None if unknown."""
        ...

    def install_mcp(
        self,
        *,
        server_name: str,
        user_context: dict[str, Any],
        force: bool = False,
    ) -> InstallResult:
        """Install an MCP server through argus's trust gate.

        Trust verdict is computed (or fetched), permissions are negotiated at
        install time, and the resulting config is returned. ``force=True``
        permits installing a SUSPICIOUS-tier server with explicit consent;
        REJECTED-tier servers cannot be force-installed.
        """
        ...


class CuratorHost(Protocol):
    """Consumer-side adapter for argus's curator (skill auto-creation).

    Projects submit successful trajectories; the curator gates promotion via
    held-out eval + surrogate verifier; promoted skills are pulled back.
    """

    name: str

    def submit_trajectory(self, trajectory: TrajectoryRecord) -> SubmitResult:
        """Submit a trajectory for skill-extraction consideration."""
        ...

    def list_promoted_skills(
        self,
        *,
        user_context: dict[str, Any],
        source_project: Optional[str] = None,
        top_k: int = 50,
    ) -> list[PromotedSkill]:
        """Return skills the curator has promoted, filtered to the caller.

        ``source_project`` filters to skills promoted from a specific project's
        trajectories (e.g., Mentat-only skills).
        """
        ...


__all__ = ["CuratorHost", "MarketplaceHost"]

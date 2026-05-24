"""In-memory stub adapters — for tests + cold-start.

Implements :class:`MarketplaceHost` and :class:`CuratorHost` against
in-process dicts. Production wires the real argus.HostAdapter.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .types import (
    InstallResult,
    MCPServer,
    PromotedSkill,
    SubmitResult,
    TrajectoryRecord,
    TrustTier,
    TrustVerdict,
)


@dataclass
class InMemoryMarketplaceHost:
    """Dict-backed marketplace adapter for tests.

    Pre-populate via :meth:`add_server` + :meth:`set_verdict`; consumers call
    :meth:`list_marketplace` / :meth:`install_mcp` / :meth:`get_trust_verdict`
    via the :class:`MarketplaceHost` Protocol.

    >>> host = InMemoryMarketplaceHost()
    >>> host.add_server(MCPServer(name="github", description="GitHub MCP"))
    >>> host.set_verdict(TrustVerdict(server_name="github", tier=TrustTier.TRUSTED, score=0.9))
    >>> result = host.install_mcp(server_name="github", user_context={"user_id": "u1"})
    >>> result.installed
    True
    """

    name: str = "in-memory-marketplace"
    servers: dict[str, MCPServer] = field(default_factory=dict)
    verdicts: dict[str, TrustVerdict] = field(default_factory=dict)
    install_log: list[InstallResult] = field(default_factory=list)
    default_tier: TrustTier = TrustTier.SUSPICIOUS  # if no verdict known

    def add_server(self, server: MCPServer) -> None:
        self.servers[server.name] = server

    def set_verdict(self, verdict: TrustVerdict) -> None:
        self.verdicts[verdict.server_name] = verdict

    def list_marketplace(
        self,
        *,
        filter: Optional[str] = None,
        top_k: int = 50,
        upstream: Optional[str] = None,
    ) -> list[MCPServer]:
        results = list(self.servers.values())
        if filter:
            f = filter.lower()
            results = [
                s for s in results if f in s.name.lower() or f in s.description.lower()
            ]
        if upstream:
            results = [s for s in results if s.upstream_marketplace == upstream]
        # Stable sort: download_count desc, name asc.
        results.sort(key=lambda s: (-s.download_count, s.name))
        return results[:top_k]

    def get_trust_verdict(self, server_name: str) -> Optional[TrustVerdict]:
        return self.verdicts.get(server_name)

    def install_mcp(
        self,
        *,
        server_name: str,
        user_context: dict[str, Any],
        force: bool = False,
    ) -> InstallResult:
        if server_name not in self.servers:
            verdict = TrustVerdict(
                server_name=server_name,
                tier=TrustTier.REJECTED,
                score=0.0,
                reasons=("server not in marketplace",),
            )
            result = InstallResult(
                server_name=server_name,
                installed=False,
                verdict=verdict,
                note="unknown server",
            )
            self.install_log.append(result)
            return result

        server = self.servers[server_name]
        verdict = self.verdicts.get(server_name) or TrustVerdict(
            server_name=server_name,
            tier=self.default_tier,
            score=0.5,
            reasons=("no verdict on file; default tier applied",),
        )

        # Decision policy: TRUSTED installs freely; SUSPICIOUS requires force;
        # REJECTED is never installed even with force.
        if verdict.tier == TrustTier.REJECTED:
            result = InstallResult(
                server_name=server_name,
                installed=False,
                verdict=verdict,
                note="REJECTED tier — install blocked",
            )
        elif verdict.tier == TrustTier.SUSPICIOUS and not force:
            result = InstallResult(
                server_name=server_name,
                installed=False,
                verdict=verdict,
                note="SUSPICIOUS tier — install requires force=True with operator consent",
            )
        else:
            # TRUSTED, or SUSPICIOUS+force.
            config = {"server_name": server_name, "endpoint": server.source_url}
            result = InstallResult(
                server_name=server_name,
                installed=True,
                verdict=verdict,
                config=config,
                permissions_negotiated=server.permissions_required,
                note="installed" if verdict.tier == TrustTier.TRUSTED else "installed with --force",
            )
        self.install_log.append(result)
        return result


@dataclass
class InMemoryCuratorHost:
    """Dict-backed curator adapter for tests.

    Trajectories submitted to :meth:`submit_trajectory` are queued; promoted
    skills are added explicitly via :meth:`promote` (simulating what argus's
    real curator would do after the held-out eval gate fires).
    """

    name: str = "in-memory-curator"
    submissions: list[TrajectoryRecord] = field(default_factory=list)
    promoted: dict[str, PromotedSkill] = field(default_factory=dict)
    auto_accept: bool = True  # accept all submissions; real curator gates

    def submit_trajectory(self, trajectory: TrajectoryRecord) -> SubmitResult:
        if not self.auto_accept:
            return SubmitResult(
                accepted=False,
                submission_id="",
                note="auto_accept=False; production gate required",
            )
        self.submissions.append(trajectory)
        return SubmitResult(
            accepted=True,
            submission_id=str(uuid.uuid4()),
            queued_for_review=trajectory.outcome != "success",
        )

    def promote(self, skill: PromotedSkill) -> None:
        """Test-side hook: simulate the curator promoting a skill."""
        self.promoted[skill.name] = skill

    def list_promoted_skills(
        self,
        *,
        user_context: dict[str, Any],
        source_project: Optional[str] = None,
        top_k: int = 50,
    ) -> list[PromotedSkill]:
        skills = list(self.promoted.values())
        if source_project:
            skills = [s for s in skills if s.source_project == source_project]
        # Sort by eval_score desc, then promoted_at desc.
        skills.sort(key=lambda s: (-s.eval_score, -s.promoted_at))
        return skills[:top_k]

    def submissions_for_project(self, project: str) -> list[TrajectoryRecord]:
        return [s for s in self.submissions if s.project == project]


__all__ = ["InMemoryCuratorHost", "InMemoryMarketplaceHost"]

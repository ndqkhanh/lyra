"""Campaign Coordinator - Multi-mission campaign orchestration.

Coordinates multiple autonomous missions as a unified campaign with
dependency management, resource allocation, and aggregate reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from lyra_core.auto.budget_enforcer import BudgetLimits, BudgetState
from lyra_core.auto.mission_control import (
    MissionConfig,
    MissionControl,
    MissionResult,
    MissionState,
    MissionStatus,
)


class CampaignStatus(StrEnum):
    """Lifecycle status of a campaign."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionDependency(StrEnum):
    """Types of dependencies between missions."""

    SEQUENTIAL = "sequential"  # B starts after A completes
    PARALLEL = "parallel"       # B starts alongside A
    CONDITIONAL = "conditional" # B starts if A succeeds


@dataclass(frozen=True)
class CampaignConfig:
    """Configuration for a multi-mission campaign."""

    campaign_id: str
    name: str
    description: str = ""
    missions: tuple[MissionConfig, ...] = ()
    dependencies: tuple[tuple[str, str, MissionDependency], ...] = ()  # (from_id, to_id, type)
    global_budget: BudgetLimits | None = None
    max_concurrent_missions: int = 3
    fail_fast: bool = False
    auto_retry_failed: bool = False
    max_campaign_retries: int = 1
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class CampaignState:
    """Current state of a campaign."""

    campaign_id: str
    status: CampaignStatus
    mission_states: tuple[tuple[str, MissionStatus], ...]  # [(mission_id, status)]
    active_missions: tuple[str, ...]
    completed_missions: tuple[str, ...]
    failed_missions: tuple[str, ...]
    pending_missions: tuple[str, ...]
    budget_consumed: BudgetState
    started_at: str | None
    updated_at: str
    retry_count: int = 0


@dataclass(frozen=True)
class CampaignResult:
    """Final result of a completed campaign."""

    campaign_id: str
    status: CampaignStatus
    total_missions: int
    completed_missions: int
    failed_missions: int
    skipped_missions: int
    completion_pct: float
    budget_consumed: BudgetState
    mission_results: tuple[MissionResult, ...]
    duration_seconds: float
    errors: tuple[str, ...]


class CampaignCoordinator:
    """Coordinates multiple autonomous missions as a unified campaign.

    Features:
    - Campaign lifecycle management (draft → active → completed)
    - Mission dependency resolution (sequential, parallel, conditional)
    - Concurrent mission execution with configurable max concurrency
    - Global budget enforcement across all missions
    - Aggregate progress reporting and campaign-level metrics
    - Automatic retry of failed missions
    - Fail-fast and graceful degradation modes
    """

    def __init__(
        self,
        budget_limits: BudgetLimits | None = None,
        max_concurrent: int = 3,
    ):
        self._controller = MissionControl(budget_limits=budget_limits)
        self._max_concurrent = max_concurrent
        self._campaigns: dict[str, CampaignConfig] = {}
        self._states: dict[str, CampaignState] = {}
        self._results: dict[str, CampaignResult] = {}
        self._dependencies: dict[str, list[str]] = {}  # mission_id -> [prereq_ids]

    # ── Campaign Lifecycle ─────────────────────────────────────────

    def create_campaign(self, config: CampaignConfig) -> CampaignState:
        """Create a new campaign from configuration.

        Args:
            config: Campaign configuration

        Returns:
            Initial CampaignState
        """
        self._campaigns[config.campaign_id] = config

        # Register all missions
        mission_statuses: list[tuple[str, MissionStatus]] = []
        for mission_config in config.missions:
            self._controller.create_mission(mission_config)
            mission_statuses.append((mission_config.mission_id, MissionStatus.DRAFT))

        # Build dependency graph
        self._build_dependency_graph(config)

        # Identify initially runnable missions (no prerequisites)
        pending = self._get_pending_missions(config.campaign_id)

        state = CampaignState(
            campaign_id=config.campaign_id,
            status=CampaignStatus.DRAFT,
            mission_states=tuple(mission_statuses),
            active_missions=(),
            completed_missions=(),
            failed_missions=(),
            pending_missions=tuple(pending),
            budget_consumed=self._controller.check_budget(""),
            started_at=None,
            updated_at=datetime.now().isoformat(),
        )
        self._states[config.campaign_id] = state
        return state

    def start_campaign(self, campaign_id: str) -> CampaignState:
        """Start a created campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Updated CampaignState
        """
        state = self._states[campaign_id]
        config = self._campaigns[campaign_id]

        # Start all initially runnable missions (up to max_concurrent)
        runnable = self._get_runnable_missions(campaign_id)
        to_start = runnable[: config.max_concurrent_missions]

        for mission_id in to_start:
            self._controller.start_mission(mission_id)

        active = tuple(to_start)
        pending = tuple(m for m in runnable if m not in active)

        state = CampaignState(
            campaign_id=campaign_id,
            status=CampaignStatus.ACTIVE,
            mission_states=state.mission_states,
            active_missions=active,
            completed_missions=state.completed_missions,
            failed_missions=state.failed_missions,
            pending_missions=pending,
            budget_consumed=self._controller.check_budget(""),
            started_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        self._states[campaign_id] = state
        return state

    def pause_campaign(self, campaign_id: str) -> CampaignState:
        """Pause all active missions in a campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Updated CampaignState
        """
        state = self._states[campaign_id]
        for mission_id in state.active_missions:
            self._controller.pause_mission(mission_id)

        state = CampaignState(
            campaign_id=campaign_id,
            status=CampaignStatus.PAUSED,
            mission_states=state.mission_states,
            active_missions=(),
            completed_missions=state.completed_missions,
            failed_missions=state.failed_missions,
            pending_missions=state.pending_missions + state.active_missions,
            budget_consumed=self._controller.check_budget(""),
            started_at=state.started_at,
            updated_at=datetime.now().isoformat(),
            retry_count=state.retry_count,
        )
        self._states[campaign_id] = state
        return state

    def resume_campaign(self, campaign_id: str) -> CampaignState:
        """Resume a paused campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Updated CampaignState
        """
        config = self._campaigns[campaign_id]
        state = self._states[campaign_id]

        runnable = list(state.pending_missions)
        to_start = runnable[: config.max_concurrent_missions]

        for mission_id in to_start:
            self._controller.resume_mission(mission_id)

        active = tuple(to_start)
        pending = tuple(m for m in runnable if m not in active)

        state = CampaignState(
            campaign_id=campaign_id,
            status=CampaignStatus.ACTIVE,
            mission_states=state.mission_states,
            active_missions=active,
            completed_missions=state.completed_missions,
            failed_missions=state.failed_missions,
            pending_missions=pending,
            budget_consumed=self._controller.check_budget(""),
            started_at=state.started_at,
            updated_at=datetime.now().isoformat(),
            retry_count=state.retry_count,
        )
        self._states[campaign_id] = state
        return state

    def cancel_campaign(self, campaign_id: str) -> CampaignState:
        """Cancel all missions in a campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Updated CampaignState
        """
        state = self._states[campaign_id]
        for mission_id in state.active_missions:
            self._controller.cancel_mission(mission_id)

        state = CampaignState(
            campaign_id=campaign_id,
            status=CampaignStatus.CANCELLED,
            mission_states=state.mission_states,
            active_missions=(),
            completed_missions=state.completed_missions,
            failed_missions=state.failed_missions,
            pending_missions=(),
            budget_consumed=self._controller.check_budget(""),
            started_at=state.started_at,
            updated_at=datetime.now().isoformat(),
            retry_count=state.retry_count,
        )
        self._states[campaign_id] = state
        return state

    # ── Mission Completion Callbacks ───────────────────────────────

    def on_mission_completed(
        self, campaign_id: str, mission_id: str
    ) -> CampaignState:
        """Handle completion of a mission within a campaign.

        Args:
            campaign_id: Campaign identifier
            mission_id: Completed mission identifier

        Returns:
            Updated CampaignState
        """
        return self._advance_campaign(campaign_id, mission_id, "completed")

    def on_mission_failed(
        self, campaign_id: str, mission_id: str
    ) -> CampaignState:
        """Handle failure of a mission within a campaign.

        Args:
            campaign_id: Campaign identifier
            mission_id: Failed mission identifier

        Returns:
            Updated CampaignState
        """
        config = self._campaigns[campaign_id]
        state = self._states[campaign_id]

        if config.fail_fast:
            return self._fail_campaign(campaign_id)

        if config.auto_retry_failed and state.retry_count < config.max_campaign_retries:
            self._controller.resume_mission(mission_id)
            state = CampaignState(
                campaign_id=campaign_id,
                status=state.status,
                mission_states=state.mission_states,
                active_missions=state.active_missions,
                completed_missions=state.completed_missions,
                failed_missions=state.failed_missions,
                pending_missions=state.pending_missions,
                budget_consumed=self._controller.check_budget(""),
                started_at=state.started_at,
                updated_at=datetime.now().isoformat(),
                retry_count=state.retry_count + 1,
            )
            self._states[campaign_id] = state
            return state

        return self._advance_campaign(campaign_id, mission_id, "failed")

    # ── Query Methods ──────────────────────────────────────────────

    def get_state(self, campaign_id: str) -> CampaignState | None:
        """Get current campaign state.

        Args:
            campaign_id: Campaign identifier

        Returns:
            CampaignState or None if not found
        """
        return self._states.get(campaign_id)

    def get_result(self, campaign_id: str) -> CampaignResult | None:
        """Get final campaign result.

        Args:
            campaign_id: Campaign identifier

        Returns:
            CampaignResult or None if campaign not complete
        """
        return self._results.get(campaign_id)

    def get_mission_state(
        self, campaign_id: str, mission_id: str
    ) -> MissionState | None:
        """Get state of a specific mission within a campaign.

        Args:
            campaign_id: Campaign identifier
            mission_id: Mission identifier

        Returns:
            MissionState or None
        """
        return self._controller.get_state(mission_id)

    def get_all_campaigns(
        self, status: CampaignStatus | None = None
    ) -> list[CampaignState]:
        """Get all campaigns, optionally filtered by status.

        Args:
            status: Filter by campaign status

        Returns:
            List of CampaignState
        """
        states = list(self._states.values())
        if status:
            states = [s for s in states if s.status == status]
        return sorted(states, key=lambda s: s.updated_at, reverse=True)

    def get_next_actionable(
        self, campaign_id: str
    ) -> list[str]:
        """Get mission IDs that are ready to execute (no pending prerequisites).

        Args:
            campaign_id: Campaign identifier

        Returns:
            List of mission IDs ready to start
        """
        state = self._states[campaign_id]
        return list(state.pending_missions)

    # ── Internal Helpers ───────────────────────────────────────────

    def _build_dependency_graph(self, config: CampaignConfig) -> None:
        """Build the mission dependency graph from config."""
        for from_id, to_id, dep_type in config.dependencies:
            if dep_type == MissionDependency.SEQUENTIAL:
                self._dependencies.setdefault(to_id, []).append(from_id)
            elif dep_type == MissionDependency.CONDITIONAL:
                self._dependencies.setdefault(to_id, []).append(from_id)

    def _get_runnable_missions(self, campaign_id: str) -> list[str]:
        """Get missions that have all prerequisites met."""
        config = self._campaigns[campaign_id]
        state = self._states[campaign_id]

        completed = set(state.completed_missions)
        runnable: list[str] = []

        for mission_config in config.missions:
            mid = mission_config.mission_id
            if mid in state.completed_missions or mid in state.failed_missions:
                continue
            if mid in state.active_missions:
                continue

            prereqs = self._dependencies.get(mid, [])
            if all(p in completed for p in prereqs):
                # Check conditional dependency: predecessor must have succeeded
                runnable.append(mid)

        return runnable

    def _get_pending_missions(self, campaign_id: str) -> list[str]:
        """Get missions with no prerequisites that haven't started."""
        config = self._campaigns[campaign_id]
        pending: list[str] = []
        for mission_config in config.missions:
            mid = mission_config.mission_id
            prereqs = self._dependencies.get(mid, [])
            if not prereqs:
                pending.append(mid)
        return pending

    def _advance_campaign(
        self, campaign_id: str, mission_id: str, outcome: str
    ) -> CampaignState:
        """Advance campaign state after a mission completes or fails."""
        config = self._campaigns[campaign_id]
        state = self._states[campaign_id]

        active = tuple(m for m in state.active_missions if m != mission_id)

        if outcome == "completed":
            completed = state.completed_missions + (mission_id,)
            failed = state.failed_missions
        else:
            completed = state.completed_missions
            failed = state.failed_missions + (mission_id,)

        # Find newly runnable missions
        all_completed = set(completed)
        for mc in config.missions:
            mid = mc.mission_id
            if mid in all_completed or mid in set(failed) or mid in active:
                continue
            prereqs = self._dependencies.get(mid, [])
            if all(p in all_completed for p in prereqs) and mid not in state.pending_missions:
                state = CampaignState(
                    campaign_id=campaign_id,
                    status=state.status,
                    mission_states=state.mission_states,
                    active_missions=state.active_missions,
                    completed_missions=state.completed_missions,
                    failed_missions=state.failed_missions,
                    pending_missions=state.pending_missions + (mid,),
                    budget_consumed=state.budget_consumed,
                    started_at=state.started_at,
                    updated_at=state.updated_at,
                    retry_count=state.retry_count,
                )

        # Start next missions up to max concurrency
        slots = config.max_concurrent_missions - len(active)
        to_start = state.pending_missions[:slots]
        for mid in to_start:
            self._controller.start_mission(mid)

        pending = tuple(m for m in state.pending_missions if m not in to_start)
        active = active + to_start

        # Check campaign completion
        total = len(config.missions)
        done = len(completed) + len(failed)

        if done >= total:
            if len(failed) == 0:
                status = CampaignStatus.COMPLETED
            elif len(completed) > 0:
                status = CampaignStatus.PARTIALLY_COMPLETED
            else:
                status = CampaignStatus.FAILED

            result = self._build_result(campaign_id, status, completed, failed)
            self._results[campaign_id] = result

        else:
            status = state.status

        state = CampaignState(
            campaign_id=campaign_id,
            status=status,
            mission_states=state.mission_states,
            active_missions=active,
            completed_missions=completed,
            failed_missions=failed,
            pending_missions=pending,
            budget_consumed=self._controller.check_budget(""),
            started_at=state.started_at,
            updated_at=datetime.now().isoformat(),
            retry_count=state.retry_count,
        )
        self._states[campaign_id] = state
        return state

    def _fail_campaign(self, campaign_id: str) -> CampaignState:
        """Immediately fail a campaign (fail-fast mode)."""
        state = self._states[campaign_id]
        for mission_id in state.active_missions:
            self._controller.cancel_mission(mission_id)

        result = self._build_result(
            campaign_id, CampaignStatus.FAILED,
            state.completed_missions, state.failed_missions,
        )
        self._results[campaign_id] = result

        new_state = CampaignState(
            campaign_id=campaign_id,
            status=CampaignStatus.FAILED,
            mission_states=state.mission_states,
            active_missions=(),
            completed_missions=state.completed_missions,
            failed_missions=state.failed_missions,
            pending_missions=(),
            budget_consumed=self._controller.check_budget(""),
            started_at=state.started_at,
            updated_at=datetime.now().isoformat(),
            retry_count=state.retry_count,
        )
        self._states[campaign_id] = new_state
        return new_state

    def _build_result(
        self,
        campaign_id: str,
        status: CampaignStatus,
        completed: tuple[str, ...],
        failed: tuple[str, ...],
    ) -> CampaignResult:
        """Build a final campaign result."""
        config = self._campaigns[campaign_id]
        state = self._states[campaign_id]
        total = len(config.missions)

        mission_results: list[MissionResult] = []
        for mission_id in completed:
            mr = self._controller.get_result(mission_id)
            if mr:
                mission_results.append(mr)
        for mission_id in failed:
            mr = self._controller.get_result(mission_id)
            if mr:
                mission_results.append(mr)

        errors = tuple(
            mr.error for mr in mission_results if mr.status == MissionStatus.FAILED
            for error in mr.errors
        )

        elapsed = 0.0
        if state.started_at:
            elapsed = (datetime.now() - datetime.fromisoformat(state.started_at)).total_seconds()

        return CampaignResult(
            campaign_id=campaign_id,
            status=status,
            total_missions=total,
            completed_missions=len(completed),
            failed_missions=len(failed),
            skipped_missions=total - len(completed) - len(failed),
            completion_pct=(len(completed) / total * 100) if total > 0 else 0.0,
            budget_consumed=self._controller.check_budget(""),
            mission_results=tuple(mission_results),
            duration_seconds=elapsed,
            errors=errors,
        )

    def reset(self) -> None:
        """Reset all campaign and mission state."""
        self._controller.reset()
        self._campaigns.clear()
        self._states.clear()
        self._results.clear()
        self._dependencies.clear()

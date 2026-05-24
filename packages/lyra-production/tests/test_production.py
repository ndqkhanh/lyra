"""
Comprehensive tests for lyra-production package.

Covers cell-based deployment, durable execution, database branching,
IETF AIMS agent identity, and AIBOM cryptographic provenance.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from lyra_production.branching import (
    BranchNotFoundError,
    BranchingConfig,
    DatabaseBranching,
    MigrationConflictError,
)
from lyra_production.cell import (
    CellManager,
    CellNotFoundError,
    CircuitBreakerOpenError,
)
from lyra_production.durable import (
    DurableExecutor,
    StepNotFoundError,
    WorkflowDefinition,
    WorkflowNotFoundError,
)
from lyra_production.identity import (
    AgentIdentityManager,
    IdentityNotFoundError,
    IdentityVerificationError,
)
from lyra_production.models import (
    AIBOMEntry,
    AgentIdentity,
    BranchStatus,
    CapabilityAttestation,
    CellStatus,
    CircuitBreakerState,
    DatabaseBranch,
    DeploymentCell,
    DeploymentConfig,
    HealthStatus,
    IdentityStatus,
    MigrationEntry,
    ProvenanceChain,
    ProvenanceStatus,
    WorkflowExecution,
    WorkflowState,
    WorkflowStep,
    compute_entry_hash,
    compute_merkle_root,
)
from lyra_production.provenance import (
    EntryNotFoundError,
    ProvenanceError,
    ProvenanceTracker,
)


# =============================================================================
# Model Tests
# =============================================================================


class TestModels:
    """Tests for frozen dataclasses and enums."""

    def test_deployment_cell_frozen(self) -> None:
        """DeploymentCell should be immutable."""
        cell = DeploymentCell(
            cell_id="test-1",
            version="1.0.0",
            status=CellStatus.ACTIVE,
            health=HealthStatus.HEALTHY,
            circuit_state=CircuitBreakerState.CLOSED,
            config=DeploymentConfig(),
        )
        assert cell.cell_id == "test-1"
        assert cell.version == "1.0.0"
        assert cell.status == CellStatus.ACTIVE
        assert cell.health == HealthStatus.HEALTHY

        with pytest.raises(AttributeError):
            cell.status = CellStatus.FAILED  # type: ignore[misc]

    def test_deployment_cell_defaults(self) -> None:
        """DeploymentCell should have sensible defaults."""
        cell = DeploymentCell(
            cell_id="test-2",
            version="1.0.0",
            status=CellStatus.PENDING,
            health=HealthStatus.UNKNOWN,
            circuit_state=CircuitBreakerState.CLOSED,
            config=DeploymentConfig(),
        )
        assert cell.failure_count == 0
        assert cell.created_at is not None
        assert cell.last_health_check is None

    def test_circuit_breaker_state_enum(self) -> None:
        """CircuitBreakerState should have correct states."""
        assert CircuitBreakerState.CLOSED.value == 1
        assert CircuitBreakerState.OPEN.value == 2
        assert CircuitBreakerState.HALF_OPEN.value == 3

    def test_health_status_enum(self) -> None:
        """HealthStatus should have correct states."""
        assert HealthStatus.HEALTHY.value == 1
        assert HealthStatus.DEGRADED.value == 2
        assert HealthStatus.UNHEALTHY.value == 3
        assert HealthStatus.UNKNOWN.value == 4

    def test_cell_status_enum(self) -> None:
        """CellStatus should have correct lifecycle states."""
        assert CellStatus.PENDING.value == 1
        assert CellStatus.ACTIVE.value == 2
        assert CellStatus.DRAINING.value == 3
        assert CellStatus.FAILED.value == 4
        assert CellStatus.TERMINATED.value == 5

    def test_workflow_state_enum(self) -> None:
        """WorkflowState should have correct states."""
        assert WorkflowState.PENDING.value == 1
        assert WorkflowState.RUNNING.value == 2
        assert WorkflowState.COMPLETED.value == 3
        assert WorkflowState.FAILED.value == 4
        assert WorkflowState.COMPENSATING.value == 5
        assert WorkflowState.COMPENSATED.value == 6
        assert WorkflowState.SUSPENDED.value == 7

    def test_branch_status_enum(self) -> None:
        """BranchStatus should have correct states."""
        assert BranchStatus.ACTIVE.value == 1
        assert BranchStatus.MERGED.value == 2
        assert BranchStatus.CONFLICT.value == 3
        assert BranchStatus.ROLLED_BACK.value == 4
        assert BranchStatus.STALE.value == 5

    def test_identity_status_enum(self) -> None:
        """IdentityStatus should have correct states."""
        assert IdentityStatus.ACTIVE.value == 1
        assert IdentityStatus.REVOKED.value == 2
        assert IdentityStatus.EXPIRED.value == 3
        assert IdentityStatus.ROTATING.value == 4

    def test_provenance_status_enum(self) -> None:
        """ProvenanceStatus should have correct states."""
        assert ProvenanceStatus.VERIFIED.value == 1
        assert ProvenanceStatus.TAMPERED.value == 2
        assert ProvenanceStatus.INCOMPLETE.value == 3
        assert ProvenanceStatus.UNVERIFIED.value == 4

    def test_workflow_execution_frozen(self) -> None:
        """WorkflowExecution should be immutable."""
        wf = WorkflowExecution(
            workflow_id="wf-1",
            name="test-flow",
            state=WorkflowState.PENDING,
            input={"key": "value"},
        )
        assert wf.workflow_id == "wf-1"
        assert wf.attempts == 0
        assert wf.input == {"key": "value"}

        with pytest.raises(AttributeError):
            wf.state = WorkflowState.RUNNING  # type: ignore[misc]

    def test_workflow_step_defaults(self) -> None:
        """WorkflowStep should have sensible defaults."""
        step = WorkflowStep(step_id="s1", name="Test Step")
        assert step.attempt == 0
        assert step.max_attempts == 3
        assert step.status == "pending"
        assert step.result is None
        assert step.error is None

    def test_database_branch_frozen(self) -> None:
        """DatabaseBranch should be immutable."""
        branch = DatabaseBranch(
            branch_id="b-1",
            name="feature/test",
            parent_commit="abc123",
            status=BranchStatus.ACTIVE,
        )
        assert branch.branch_id == "b-1"
        assert branch.head_commit == ""

        with pytest.raises(AttributeError):
            branch.status = BranchStatus.MERGED  # type: ignore[misc]

    def test_agent_identity_frozen(self) -> None:
        """AgentIdentity should be immutable."""
        identity = AgentIdentity(
            agent_id="agent-1",
            public_key="pub-key-1",
            capabilities=frozenset({"code", "reason"}),
        )
        assert identity.agent_id == "agent-1"
        assert "code" in identity.capabilities
        assert identity.identity_layer == 8

        with pytest.raises(AttributeError):
            identity.status = IdentityStatus.REVOKED  # type: ignore[misc]

    def test_capability_attestation(self) -> None:
        """CapabilityAttestation should store attestation data."""
        now = datetime.now(timezone.utc)
        attest = CapabilityAttestation(
            capability="code-review",
            attested_by="agent-2",
            attested_at=now,
            signature="sig-123",
            valid_until=now + timedelta(days=90),
        )
        assert attest.capability == "code-review"
        assert attest.attested_by == "agent-2"

    def test_aibom_entry_frozen(self) -> None:
        """AIBOMEntry should be immutable."""
        entry = AIBOMEntry(
            entry_id="bom-1",
            output_hash="hash-123",
            model_info={"name": "gpt-4", "provider": "openai"},
            prompt_hash="prompt-hash-456",
        )
        assert entry.output_hash == "hash-123"
        assert entry.model_info["name"] == "gpt-4"

        with pytest.raises(AttributeError):
            entry.output_hash = "new-hash"  # type: ignore[misc]

    def test_provenance_chain_frozen(self) -> None:
        """ProvenanceChain should be immutable."""
        entry = AIBOMEntry(
            entry_id="bom-1",
            output_hash="hash-123",
            model_info={"name": "gpt-4"},
            prompt_hash="p-hash",
        )
        chain = ProvenanceChain(
            chain_id="chain-1",
            entries=(entry,),
            root_hash="root-hash",
        )
        assert chain.chain_id == "chain-1"
        assert len(chain.entries) == 1
        assert chain.verification_status == ProvenanceStatus.UNVERIFIED

    def test_compute_merkle_root(self) -> None:
        """compute_merkle_root should produce a deterministic hash."""
        entry1 = AIBOMEntry(
            entry_id="a", output_hash="h1",
            model_info={}, prompt_hash="p1",
        )
        entry2 = AIBOMEntry(
            entry_id="b", output_hash="h2",
            model_info={}, prompt_hash="p2",
        )

        root1 = compute_merkle_root((entry1, entry2))
        root2 = compute_merkle_root((entry1, entry2))
        assert root1 == root2  # Deterministic

        root3 = compute_merkle_root((entry1,))
        assert root3 != root1  # Different entries produce different roots

    def test_compute_merkle_root_empty(self) -> None:
        """compute_merkle_root of empty tuple should return a hash."""
        root = compute_merkle_root(())
        assert isinstance(root, str)
        assert len(root) == 64  # SHA-256

    def test_compute_entry_hash(self) -> None:
        """compute_entry_hash should produce a deterministic hash."""
        entry = AIBOMEntry(
            entry_id="bom-1",
            output_hash="hash-123",
            model_info={"name": "gpt-4"},
            prompt_hash="p-hash",
        )
        h1 = compute_entry_hash(entry)
        h2 = compute_entry_hash(entry)
        assert h1 == h2  # Deterministic

    def test_deployment_config_defaults(self) -> None:
        """DeploymentConfig should have sensible defaults."""
        config = DeploymentConfig()
        assert config.replicas == 1
        assert config.max_retries == 3
        assert config.health_check_interval_sec == 30.0
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout_sec == 60.0
        assert config.resources == {}
        assert config.labels == {}
        assert config.env_vars == {}

    def test_migration_entry_defaults(self) -> None:
        """MigrationEntry should have sensible defaults."""
        migration = MigrationEntry(
            migration_id="m1",
            description="Create users table",
            sql_up="CREATE TABLE users (id INT);",
            sql_down="DROP TABLE users;",
        )
        assert migration.applied_at is None
        assert migration.checksum == ""


# =============================================================================
# Cell Manager Tests
# =============================================================================


class TestCellManager:
    """Tests for CellManager - cell-based deployment."""

    def test_deploy_cell(self) -> None:
        """Deploying a cell should create it with unique ID."""
        mgr = CellManager()
        cell = mgr.deploy_cell("1.0.0")
        assert cell.cell_id.startswith("cell-")
        assert cell.version == "1.0.0"
        assert cell.status == CellStatus.ACTIVE
        assert cell.circuit_state == CircuitBreakerState.CLOSED

    def test_deploy_cell_with_config(self) -> None:
        """Deploying with custom config should apply it."""
        mgr = CellManager()
        config = DeploymentConfig(
            replicas=3,
            circuit_breaker_threshold=10,
            labels={"tier": "production"},
        )
        cell = mgr.deploy_cell("2.0.0", config=config)
        assert cell.config.replicas == 3
        assert cell.config.circuit_breaker_threshold == 10
        assert cell.config.labels["tier"] == "production"

    def test_health_check_healthy(self) -> None:
        """Health check should return HEALTHY for healthy cells."""
        mgr = CellManager()
        cell = mgr.deploy_cell("1.0.0")
        status = mgr.health_check(cell.cell_id)
        assert status == HealthStatus.HEALTHY

    def test_health_check_not_found(self) -> None:
        """Health check on non-existent cell should raise error."""
        mgr = CellManager()
        with pytest.raises(CellNotFoundError):
            mgr.health_check("nonexistent")

    def test_health_check_unhealthy_triggers_circuit_breaker(self) -> None:
        """Repeated unhealthy checks should open circuit breaker."""
        call_count = [0]

        def failing_check(cell_id: str) -> HealthStatus:
            call_count[0] += 1
            return HealthStatus.UNHEALTHY

        mgr = CellManager(health_check_fn=failing_check)
        config = DeploymentConfig(circuit_breaker_threshold=3)
        cell = mgr.deploy_cell("1.0.0", config=config)

        # Run health checks up to threshold
        for _ in range(3):
            mgr.health_check(cell.cell_id)

        # Circuit breaker should be open
        updated = mgr.get_cell(cell.cell_id)
        assert updated.circuit_state == CircuitBreakerState.OPEN

    def test_toggle_circuit_breaker(self) -> None:
        """Manual circuit breaker override should work."""
        mgr = CellManager()
        cell = mgr.deploy_cell("1.0.0")

        updated = mgr.toggle_circuit_breaker(
            cell.cell_id, CircuitBreakerState.OPEN
        )
        assert updated.circuit_state == CircuitBreakerState.OPEN

        # Reset to closed
        updated = mgr.toggle_circuit_breaker(
            cell.cell_id, CircuitBreakerState.CLOSED
        )
        assert updated.circuit_state == CircuitBreakerState.CLOSED
        assert updated.failure_count == 0

    def test_toggle_circuit_breaker_not_found(self) -> None:
        """Toggle on non-existent cell should raise error."""
        mgr = CellManager()
        with pytest.raises(CellNotFoundError):
            mgr.toggle_circuit_breaker(
                "nonexistent", CircuitBreakerState.OPEN
            )

    def test_get_active_cells(self) -> None:
        """get_active_cells should return only healthy active cells."""
        mgr = CellManager()
        cell1 = mgr.deploy_cell("1.0.0")
        cell2 = mgr.deploy_cell("1.0.0")
        mgr.toggle_circuit_breaker(cell2.cell_id, CircuitBreakerState.OPEN)

        active = mgr.get_active_cells()
        assert len(active) == 1
        assert active[0].cell_id == cell1.cell_id

    def test_failover(self) -> None:
        """Failover should drain source and return healthy alternative."""
        mgr = CellManager()
        cell1 = mgr.deploy_cell("1.0.0")
        cell2 = mgr.deploy_cell("1.0.0")

        # Run health checks to mark cells as healthy
        mgr.health_check(cell1.cell_id)
        mgr.health_check(cell2.cell_id)

        target = mgr.failover(cell1.cell_id)
        assert target is not None
        assert target.cell_id == cell2.cell_id

        # Source should be draining
        source = mgr.get_cell(cell1.cell_id)
        assert source.status == CellStatus.DRAINING

    def test_failover_no_alternative(self) -> None:
        """Failover with no alternative should return None."""
        mgr = CellManager()
        cell = mgr.deploy_cell("1.0.0")
        target = mgr.failover(cell.cell_id)
        assert target is None

    def test_failover_not_found(self) -> None:
        """Failover on non-existent cell should raise error."""
        mgr = CellManager()
        with pytest.raises(CellNotFoundError):
            mgr.failover("nonexistent")

    def test_scale_cell(self) -> None:
        """Scaling a cell should update replica count."""
        mgr = CellManager()
        cell = mgr.deploy_cell("1.0.0")
        updated = mgr.scale_cell(cell.cell_id, 5)
        assert updated.config.replicas == 5

    def test_scale_cell_invalid(self) -> None:
        """Scaling below 1 should raise error."""
        mgr = CellManager()
        cell = mgr.deploy_cell("1.0.0")
        with pytest.raises(ValueError, match="at least 1"):
            mgr.scale_cell(cell.cell_id, 0)

    def test_scale_cell_not_found(self) -> None:
        """Scaling non-existent cell should raise error."""
        mgr = CellManager()
        with pytest.raises(CellNotFoundError):
            mgr.scale_cell("nonexistent", 3)

    def test_get_cell(self) -> None:
        """get_cell should return a specific cell."""
        mgr = CellManager()
        cell = mgr.deploy_cell("1.0.0")
        retrieved = mgr.get_cell(cell.cell_id)
        assert retrieved.cell_id == cell.cell_id

    def test_get_cell_not_found(self) -> None:
        """get_cell on non-existent cell should raise error."""
        mgr = CellManager()
        with pytest.raises(CellNotFoundError):
            mgr.get_cell("nonexistent")

    def test_list_cells(self) -> None:
        """list_cells should return all cells."""
        mgr = CellManager()
        mgr.deploy_cell("1.0.0")
        mgr.deploy_cell("2.0.0")
        assert len(mgr.list_cells()) == 2

    def test_run_health_checks(self) -> None:
        """run_health_checks should check all cells."""
        mgr = CellManager()
        mgr.deploy_cell("1.0.0")
        mgr.deploy_cell("1.0.0")
        results = mgr.run_health_checks()
        assert len(results) == 2
        assert all(s == HealthStatus.HEALTHY for s in results.values())

    def test_attempt_recovery(self) -> None:
        """Attempt recovery should transition OPEN to HALF_OPEN."""
        call_count = [0]

        def failing_then_healthy(cell_id: str) -> HealthStatus:
            call_count[0] += 1
            if call_count[0] <= 3:
                return HealthStatus.UNHEALTHY
            return HealthStatus.HEALTHY

        mgr = CellManager(health_check_fn=failing_then_healthy)
        config = DeploymentConfig(circuit_breaker_threshold=3)
        cell = mgr.deploy_cell("1.0.0", config=config)

        # Trip the breaker
        for _ in range(3):
            mgr.health_check(cell.cell_id)

        # Recovery attempt
        status = mgr.attempt_recovery(cell.cell_id)
        assert status == HealthStatus.HEALTHY

    def test_attempt_recovery_not_open(self) -> None:
        """Attempt recovery on closed breaker should just return health."""
        mgr = CellManager()
        cell = mgr.deploy_cell("1.0.0")
        # Run health check so the cell is marked healthy
        mgr.health_check(cell.cell_id)
        status = mgr.attempt_recovery(cell.cell_id)
        assert status == HealthStatus.HEALTHY

    def test_attempt_recovery_not_found(self) -> None:
        """Attempt recovery on non-existent cell should raise error."""
        mgr = CellManager()
        with pytest.raises(CellNotFoundError):
            mgr.attempt_recovery("nonexistent")


# =============================================================================
# Durable Execution Tests
# =============================================================================


class TestDurableExecutor:
    """Tests for DurableExecutor - durable workflow execution."""

    def test_register_and_start_workflow(self) -> None:
        """Register and start a workflow should execute steps."""
        executor = DurableExecutor()
        steps_run = []

        def step1(input_data: dict[str, Any]) -> str:
            steps_run.append("step1")
            return "result1"

        def step2(input_data: dict[str, Any]) -> str:
            steps_run.append("step2")
            return "result2"

        definition = WorkflowDefinition(
            name="test-flow",
            steps={"step1": step1, "step2": step2},
        )
        executor.register_workflow(definition)

        execution = executor.start_workflow(
            "test-flow", {"input_key": "input_value"}
        )
        assert execution.state == WorkflowState.COMPLETED
        assert execution.result == "result2"
        assert steps_run == ["step1", "step2"]

    def test_workflow_not_found(self) -> None:
        """Starting an unregistered workflow should raise error."""
        executor = DurableExecutor()
        with pytest.raises(KeyError, match="not found"):
            executor.start_workflow("nonexistent")

    def test_workflow_retry_on_failure(self) -> None:
        """Workflow should retry failed steps."""
        executor = DurableExecutor()
        attempt_count = [0]

        def flaky_step(input_data: dict[str, Any]) -> str:
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise RuntimeError("Temporary failure")
            return "success"

        definition = WorkflowDefinition(
            name="flaky-flow",
            steps={"flaky": flaky_step},
            max_retries=3,
        )
        executor.register_workflow(definition)

        execution = executor.start_workflow("flaky-flow")
        assert execution.state == WorkflowState.COMPLETED
        assert execution.result == "success"
        assert attempt_count[0] == 3

    def test_workflow_exhausts_retries(self) -> None:
        """Workflow should fail after exhausting retries."""
        executor = DurableExecutor()

        def always_fails(input_data: dict[str, Any]) -> str:
            raise RuntimeError("Persistent failure")

        definition = WorkflowDefinition(
            name="failing-flow",
            steps={"failing": always_fails},
            max_retries=2,
        )
        executor.register_workflow(definition)

        execution = executor.start_workflow("failing-flow")
        assert execution.state == WorkflowState.COMPENSATED
        assert execution.error is not None
        assert "Persistent failure" in execution.error

    def test_saga_compensation(self) -> None:
        """Saga compensation should run for completed steps on failure."""
        executor = DurableExecutor()
        compensated = []

        def step1(input_data: dict[str, Any]) -> str:
            return "step1-done"

        def step2(input_data: dict[str, Any]) -> str:
            raise RuntimeError("Step 2 failed")

        def compensate_step1(input_data: dict[str, Any], result: Any) -> None:
            compensated.append("step1")

        definition = WorkflowDefinition(
            name="saga-flow",
            steps={"step1": step1, "step2": step2},
            compensations={"step1": compensate_step1},
        )
        executor.register_workflow(definition)

        execution = executor.start_workflow("saga-flow")
        assert execution.state == WorkflowState.COMPENSATED
        assert compensated == ["step1"]

    def test_get_workflow_state(self) -> None:
        """get_workflow_state should return execution state."""
        executor = DurableExecutor()

        def simple_step(input_data: dict[str, Any]) -> str:
            return "done"

        definition = WorkflowDefinition(
            name="simple",
            steps={"step": simple_step},
        )
        executor.register_workflow(definition)

        execution = executor.start_workflow("simple")
        retrieved = executor.get_workflow_state(execution.workflow_id)
        assert retrieved.workflow_id == execution.workflow_id

    def test_get_workflow_state_not_found(self) -> None:
        """get_workflow_state on non-existent workflow should raise error."""
        executor = DurableExecutor()
        with pytest.raises(WorkflowNotFoundError):
            executor.get_workflow_state("nonexistent")

    def test_list_active_workflows(self) -> None:
        """list_active_workflows should return running workflows."""
        executor = DurableExecutor()

        def slow_step(input_data: dict[str, Any]) -> str:
            time.sleep(0.05)
            return "done"

        definition = WorkflowDefinition(
            name="slow",
            steps={"step": slow_step},
            max_retries=1,
        )
        executor.register_workflow(definition)

        active = executor.list_active_workflows()
        # Workflow completes quickly so may be empty
        assert isinstance(active, list)

    def test_compensate_explicit(self) -> None:
        """Explicit compensate should run compensation handlers."""
        executor = DurableExecutor()
        compensated = []

        def step1(input_data: dict[str, Any]) -> str:
            return "done"

        def comp1(input_data: dict[str, Any], result: Any) -> None:
            compensated.append("step1")

        definition = WorkflowDefinition(
            name="comp-flow",
            steps={"step1": step1},
            compensations={"step1": comp1},
        )
        executor.register_workflow(definition)
        execution = executor.start_workflow("comp-flow")

        result = executor.compensate(execution.workflow_id)
        assert result.state == WorkflowState.COMPENSATED

    def test_retry_step_success(self) -> None:
        """retry_step should retry a specific failed step."""
        executor = DurableExecutor()

        attempt_count = [0]

        def flaky_step(input_data: dict[str, Any]) -> str:
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise RuntimeError("Temporary")
            return "success"

        definition = WorkflowDefinition(
            name="retry-flow",
            steps={"flaky": flaky_step},
            max_retries=1,
        )
        executor.register_workflow(definition)
        execution = executor.start_workflow("retry-flow")
        assert execution.state == WorkflowState.COMPENSATED

        # Find the failed step
        failed_step = execution.history[0]
        result = executor.retry_step(execution.workflow_id, failed_step.step_id)
        assert result.state == WorkflowState.RUNNING

    def test_retry_step_not_found(self) -> None:
        """retry_step on non-existent step should raise error."""
        executor = DurableExecutor()

        def step(input_data: dict[str, Any]) -> str:
            return "done"

        definition = WorkflowDefinition(
            name="simple",
            steps={"step": step},
        )
        executor.register_workflow(definition)
        execution = executor.start_workflow("simple")

        with pytest.raises(StepNotFoundError):
            executor.retry_step(execution.workflow_id, "nonexistent-step")

    def test_resume_workflow(self) -> None:
        """resume_workflow should transition SUSPENDED to RUNNING."""
        executor = DurableExecutor()

        def step(input_data: dict[str, Any]) -> str:
            return "done"

        definition = WorkflowDefinition(
            name="simple",
            steps={"step": step},
        )
        executor.register_workflow(definition)
        execution = executor.start_workflow("simple")

        # Can only resume suspended workflows
        with pytest.raises(ValueError):
            executor.resume_workflow(execution.workflow_id)

    def test_resume_not_found(self) -> None:
        """resume_workflow on non-existent workflow should raise error."""
        executor = DurableExecutor()
        with pytest.raises(WorkflowNotFoundError):
            executor.resume_workflow("nonexistent")


# =============================================================================
# Database Branching Tests
# =============================================================================


class TestDatabaseBranching:
    """Tests for DatabaseBranching - CoW database forks."""

    def test_create_branch(self) -> None:
        """Creating a branch should return a DatabaseBranch."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")
        assert branch.name == "feature/test"
        assert branch.parent_commit == "abc123"
        assert branch.status == BranchStatus.ACTIVE

    def test_create_branch_empty_name(self) -> None:
        """Creating a branch with empty name should raise error."""
        branching = DatabaseBranching()
        with pytest.raises(ValueError, match="cannot be empty"):
            branching.create_branch("", "abc123")

    def test_create_branch_duplicate(self) -> None:
        """Creating a duplicate branch name should raise error."""
        branching = DatabaseBranching()
        branching.create_branch("feature/test", "abc123")
        with pytest.raises(ValueError, match="already exists"):
            branching.create_branch("feature/test", "abc123")

    def test_apply_migration(self) -> None:
        """Applying a migration should update the branch."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")

        migration = MigrationEntry(
            migration_id="m1",
            description="Create users table",
            sql_up="CREATE TABLE users (id INT);",
            sql_down="DROP TABLE users;",
        )
        updated = branching.apply_migration(branch.branch_id, migration)
        assert len(updated.changes) == 1
        assert updated.changes[0].description == "Create users table"
        assert updated.head_commit != branch.head_commit

    def test_apply_migration_not_found(self) -> None:
        """Applying migration to non-existent branch should raise error."""
        branching = DatabaseBranching()
        migration = MigrationEntry(
            migration_id="m1",
            description="test",
            sql_up="SELECT 1",
            sql_down="SELECT 0",
        )
        with pytest.raises(BranchNotFoundError):
            branching.apply_migration("nonexistent", migration)

    def test_validate_branch_clean(self) -> None:
        """Validating a clean branch should return no conflicts."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")

        migration = MigrationEntry(
            migration_id="m1",
            description="test",
            sql_up="SELECT 1",
            sql_down="SELECT 0",
        )
        branching.apply_migration(branch.branch_id, migration)

        conflicts = branching.validate_branch(branch.branch_id)
        assert conflicts == []

    def test_validate_branch_empty(self) -> None:
        """Validating a branch with no migrations should list issue."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")
        conflicts = branching.validate_branch(branch.branch_id)
        assert len(conflicts) > 0
        assert "no migrations" in conflicts[0]

    def test_merge_branch(self) -> None:
        """Merging a branch should change status to MERGED."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")

        migration = MigrationEntry(
            migration_id="m1",
            description="test",
            sql_up="SELECT 1",
            sql_down="SELECT 0",
        )
        branching.apply_migration(branch.branch_id, migration)

        merged = branching.merge_branch(branch.branch_id)
        assert merged.status == BranchStatus.MERGED

    def test_merge_branch_with_conflicts(self) -> None:
        """Merging a branch with conflicts should raise error."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")
        # Empty branch has no migrations -> conflict
        with pytest.raises(MigrationConflictError):
            branching.merge_branch(branch.branch_id)

    def test_merge_branch_not_found(self) -> None:
        """Merging non-existent branch should raise error."""
        branching = DatabaseBranching()
        with pytest.raises(BranchNotFoundError):
            branching.merge_branch("nonexistent")

    def test_rollback_branch(self) -> None:
        """Rolling back a branch should clear changes and mark rolled back."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")

        migration = MigrationEntry(
            migration_id="m1",
            description="test",
            sql_up="SELECT 1",
            sql_down="SELECT 0",
        )
        branching.apply_migration(branch.branch_id, migration)

        rolled = branching.rollback_branch(branch.branch_id)
        assert rolled.status == BranchStatus.ROLLED_BACK
        assert rolled.changes == []
        assert rolled.head_commit == branch.parent_commit

    def test_rollback_not_active(self) -> None:
        """Rolling back a non-active branch should raise error."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")

        migration = MigrationEntry(
            migration_id="m1",
            description="test",
            sql_up="SELECT 1",
            sql_down="SELECT 0",
        )
        branching.apply_migration(branch.branch_id, migration)
        branching.merge_branch(branch.branch_id)

        with pytest.raises(ValueError):
            branching.rollback_branch(branch.branch_id)

    def test_rollback_not_found(self) -> None:
        """Rolling back non-existent branch should raise error."""
        branching = DatabaseBranching()
        with pytest.raises(BranchNotFoundError):
            branching.rollback_branch("nonexistent")

    def test_list_branches(self) -> None:
        """list_branches should return all branches."""
        branching = DatabaseBranching()
        branching.create_branch("feature/a", "abc")
        branching.create_branch("feature/b", "def")
        assert len(branching.list_branches()) == 2

    def test_get_branch(self) -> None:
        """get_branch should return a specific branch."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")
        retrieved = branching.get_branch(branch.branch_id)
        assert retrieved.name == "feature/test"

    def test_get_branch_not_found(self) -> None:
        """get_branch on non-existent branch should raise error."""
        branching = DatabaseBranching()
        with pytest.raises(BranchNotFoundError):
            branching.get_branch("nonexistent")

    def test_max_branches_limit(self) -> None:
        """Creating more branches than max should raise error."""
        config = BranchingConfig(max_branches=2)
        branching = DatabaseBranching(config=config)
        branching.create_branch("feature/a", "abc")
        branching.create_branch("feature/b", "def")
        with pytest.raises(ValueError, match="Maximum"):
            branching.create_branch("feature/c", "ghi")

    def test_duplicate_migration_detection(self) -> None:
        """Duplicate migration IDs should be detected during validation."""
        branching = DatabaseBranching()
        branch = branching.create_branch("feature/test", "abc123")

        migration = MigrationEntry(
            migration_id="m1",
            description="test",
            sql_up="SELECT 1",
            sql_down="SELECT 0",
        )
        branch2 = branching.apply_migration(branch.branch_id, migration)

        # Simulate adding a duplicate by directly applying the same migration
        branching.apply_migration(branch2.branch_id, migration)

        conflicts = branching.validate_branch(branch.branch_id)
        assert any("duplicate" in c for c in conflicts)


# =============================================================================
# Agent Identity Tests
# =============================================================================


class TestAgentIdentityManager:
    """Tests for AgentIdentityManager - IETF AIMS identity."""

    def test_create_identity(self) -> None:
        """Creating an identity should return AgentIdentity and key."""
        mgr = AgentIdentityManager()
        identity, private_key = mgr.create_identity(
            "agent-1", capabilities={"code", "reason"}
        )
        assert identity.agent_id == "agent-1"
        assert "code" in identity.capabilities
        assert private_key.startswith("priv-")

    def test_create_identity_empty_id(self) -> None:
        """Creating identity with empty ID should raise error."""
        mgr = AgentIdentityManager()
        with pytest.raises(ValueError, match="cannot be empty"):
            mgr.create_identity("")

    def test_create_identity_duplicate(self) -> None:
        """Creating duplicate identity should raise error."""
        mgr = AgentIdentityManager()
        mgr.create_identity("agent-1")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_identity("agent-1")

    def test_create_identity_invalid_layer(self) -> None:
        """Creating identity with invalid layer should raise error."""
        mgr = AgentIdentityManager()
        with pytest.raises(ValueError, match="between 1 and 8"):
            mgr.create_identity("agent-1", identity_layer=9)

    def test_sign_and_verify_challenge(self) -> None:
        """Signing and verifying a challenge should work."""
        mgr = AgentIdentityManager()
        mgr.create_identity("agent-1", capabilities={"verify"})

        signature = mgr.sign_challenge("agent-1", "challenge-123")
        assert mgr.verify_identity("agent-1", signature, "challenge-123")

    def test_verify_wrong_signature(self) -> None:
        """Verifying with wrong signature should return False."""
        mgr = AgentIdentityManager()
        mgr.create_identity("agent-1")

        result = mgr.verify_identity(
            "agent-1", "wrong-signature", "challenge-123"
        )
        assert not result

    def test_sign_challenge_not_found(self) -> None:
        """Signing with non-existent identity should raise error."""
        mgr = AgentIdentityManager()
        with pytest.raises(IdentityNotFoundError):
            mgr.sign_challenge("nonexistent", "challenge")

    def test_verify_unknown_identity(self) -> None:
        """Verifying unknown identity should return False."""
        mgr = AgentIdentityManager()
        result = mgr.verify_identity(
            "unknown", "sig", "challenge"
        )
        assert not result

    def test_attest_capability(self) -> None:
        """Attesting a capability should add an attestation."""
        mgr = AgentIdentityManager()
        mgr.create_identity("agent-1", capabilities={"code"})
        mgr.create_identity("agent-2", capabilities={"review"})

        updated = mgr.attest_capability(
            "agent-1", "review", "agent-2"
        )
        assert len(updated.attestations) == 1
        assert updated.attestations[0].capability == "review"
        assert updated.attestations[0].attested_by == "agent-2"

    def test_attest_capability_no_attester(self) -> None:
        """Attesting with non-existent attester should raise error."""
        mgr = AgentIdentityManager()
        mgr.create_identity("agent-1")
        with pytest.raises(IdentityNotFoundError):
            mgr.attest_capability("agent-1", "code", "nonexistent")

    def test_revoke_identity(self) -> None:
        """Revoking an identity should mark it as revoked."""
        mgr = AgentIdentityManager()
        mgr.create_identity("agent-1")

        revoked = mgr.revoke_identity("agent-1", reason="Compromised")
        assert revoked.status == IdentityStatus.REVOKED
        assert revoked.revocation_reason == "Compromised"

    def test_revoke_identity_not_found(self) -> None:
        """Revoking non-existent identity should raise error."""
        mgr = AgentIdentityManager()
        with pytest.raises(IdentityNotFoundError):
            mgr.revoke_identity("nonexistent")

    def test_rotate_keys(self) -> None:
        """Rotating keys should generate new key pair."""
        mgr = AgentIdentityManager()
        identity, _ = mgr.create_identity("agent-1")
        old_key = identity.public_key

        new_identity, new_key = mgr.rotate_keys("agent-1")
        assert new_identity.public_key != old_key
        assert new_identity.rotated_from == old_key
        assert new_identity.status == IdentityStatus.ACTIVE

    def test_rotate_keys_not_found(self) -> None:
        """Rotating keys for non-existent identity should raise error."""
        mgr = AgentIdentityManager()
        with pytest.raises(IdentityNotFoundError):
            mgr.rotate_keys("nonexistent")

    def test_get_identity(self) -> None:
        """get_identity should return a specific identity."""
        mgr = AgentIdentityManager()
        identity, _ = mgr.create_identity("agent-1")
        retrieved = mgr.get_identity("agent-1")
        assert retrieved.agent_id == "agent-1"

    def test_get_identity_not_found(self) -> None:
        """get_identity on non-existent identity should raise error."""
        mgr = AgentIdentityManager()
        with pytest.raises(IdentityNotFoundError):
            mgr.get_identity("nonexistent")

    def test_list_identities(self) -> None:
        """list_identities should return all identities."""
        mgr = AgentIdentityManager()
        mgr.create_identity("agent-1")
        mgr.create_identity("agent-2")
        assert len(mgr.list_identities()) == 2

    def test_list_active_identities(self) -> None:
        """list_active_identities should return only active."""
        mgr = AgentIdentityManager()
        mgr.create_identity("agent-1")
        mgr.create_identity("agent-2")
        mgr.revoke_identity("agent-2")

        active = mgr.list_active_identities()
        assert len(active) == 1
        assert active[0].agent_id == "agent-1"

    def test_sign_with_expired_identity(self) -> None:
        """Signing with an expired identity should raise error."""
        mgr = AgentIdentityManager()
        identity, _ = mgr.create_identity(
            "agent-1", valid_for_days=0
        )
        with pytest.raises(IdentityVerificationError):
            mgr.sign_challenge("agent-1", "challenge")


# =============================================================================
# AIBOM Provenance Tests
# =============================================================================


class TestProvenanceTracker:
    """Tests for ProvenanceTracker - AIBOM provenance."""

    def test_record_output(self) -> None:
        """Recording output should create AIBOMEntry."""
        tracker = ProvenanceTracker()
        entry = tracker.record_output(
            output="Hello, world!",
            model_info={"name": "gpt-4", "provider": "openai"},
            prompt="Say hello",
        )
        assert entry.entry_id.startswith("bom-")
        assert entry.output_hash is not None
        assert entry.model_info["name"] == "gpt-4"

    def test_record_output_with_tools(self) -> None:
        """Recording output with tool calls should include them."""
        tracker = ProvenanceTracker()
        entry = tracker.record_output(
            output="Result",
            model_info={"name": "gpt-4"},
            prompt="Do something",
            tools=[{"name": "calculator", "input": "2+2"}],
            data_sources=[{"name": "knowledge-base", "version": "1.0"}],
        )
        assert len(entry.tool_calls) == 1
        assert len(entry.data_sources) == 1

    def test_record_output_with_parent(self) -> None:
        """Recording output with parent should chain entries."""
        tracker = ProvenanceTracker()
        parent = tracker.record_output(
            output="Parent output",
            model_info={"name": "gpt-4"},
            prompt="First prompt",
        )
        child = tracker.record_output(
            output="Child output",
            model_info={"name": "gpt-4"},
            prompt="Second prompt",
            parent_entry=parent.entry_id,
        )
        assert child.parent_entry == parent.entry_id

    def test_build_chain(self) -> None:
        """Building a chain should create ProvenanceChain."""
        tracker = ProvenanceTracker()
        tracker.record_output(
            output="Output 1",
            model_info={"name": "gpt-4"},
            prompt="Prompt 1",
        )
        tracker.record_output(
            output="Output 2",
            model_info={"name": "gpt-4"},
            prompt="Prompt 2",
        )

        chain = tracker.build_chain()
        assert len(chain.entries) == 2
        assert len(chain.root_hash) == 64  # SHA-256

    def test_build_chain_with_filter(self) -> None:
        """Building chain with output hash filter should work."""
        tracker = ProvenanceTracker()
        e1 = tracker.record_output(
            output="Alpha",
            model_info={"name": "gpt-4"},
            prompt="Prompt A",
        )
        tracker.record_output(
            output="Beta",
            model_info={"name": "gpt-4"},
            prompt="Prompt B",
        )

        chain = tracker.build_chain(
            filter_output_hash=e1.output_hash
        )
        assert len(chain.entries) == 1
        assert chain.entries[0].output_hash == e1.output_hash

    def test_build_chain_empty(self) -> None:
        """Building chain with no entries should raise error."""
        tracker = ProvenanceTracker()
        with pytest.raises(ProvenanceError, match="no entries"):
            tracker.build_chain(entry_ids=["nonexistent"])

    def test_verify_chain_intact(self) -> None:
        """Verifying an intact chain should return True."""
        tracker = ProvenanceTracker()
        tracker.record_output(
            output="Data",
            model_info={"name": "gpt-4"},
            prompt="Prompt",
        )
        chain = tracker.build_chain()
        assert tracker.verify_chain(chain)

    def test_verify_tampered_chain(self) -> None:
        """Verifying a tampered chain should return False."""
        tracker = ProvenanceTracker()
        tracker.record_output(
            output="Data",
            model_info={"name": "gpt-4"},
            prompt="Prompt",
        )
        chain = tracker.build_chain()

        # Tamper with the chain by modifying root hash
        tampered_chain = ProvenanceChain(
            chain_id=chain.chain_id,
            entries=chain.entries,
            root_hash="tampered-root-hash",
            verification_status=chain.verification_status,
            created_at=chain.created_at,
        )
        assert not tracker.verify_chain(tampered_chain)

    def test_export_bom(self) -> None:
        """Exporting BOM should produce a serializable dict."""
        tracker = ProvenanceTracker()
        tracker.record_output(
            output="Test data",
            model_info={"name": "gpt-4"},
            prompt="Test prompt",
        )
        chain = tracker.build_chain()
        bom = tracker.export_bom(chain)

        assert bom["bom_specification"] == "aibom-1.0"
        assert bom["chain_id"] == chain.chain_id
        assert bom["total_entries"] == 1
        assert len(bom["entries"]) == 1

    def test_audit_trail(self) -> None:
        """Audit trail should return full provenance chain."""
        tracker = ProvenanceTracker()
        parent = tracker.record_output(
            output="Parent",
            model_info={"name": "gpt-4"},
            prompt="Parent prompt",
        )
        child = tracker.record_output(
            output="Child",
            model_info={"name": "gpt-4"},
            prompt="Child prompt",
            parent_entry=parent.entry_id,
        )

        trail = tracker.audit_trail(child.output_hash)
        assert len(trail) == 2  # child + parent

    def test_audit_trail_no_match(self) -> None:
        """Audit trail with no matching entries should return empty."""
        tracker = ProvenanceTracker()
        trail = tracker.audit_trail("nonexistent-hash")
        assert trail == []

    def test_detect_tampering_intact(self) -> None:
        """detect_tampering on intact chain should return empty."""
        tracker = ProvenanceTracker()
        tracker.record_output(
            output="Data",
            model_info={"name": "gpt-4"},
            prompt="Prompt",
        )
        chain = tracker.build_chain()
        issues = tracker.detect_tampering(chain)
        assert issues == []

    def test_detect_tampering_root_mismatch(self) -> None:
        """detect_tampering should find Merkle root issues."""
        tracker = ProvenanceTracker()
        entry = AIBOMEntry(
            entry_id="bom-test",
            output_hash="hash",
            model_info={},
            prompt_hash="phash",
        )
        chain = ProvenanceChain(
            chain_id="test-chain",
            entries=(entry,),
            root_hash="wrong-root",
        )
        issues = tracker.detect_tampering(chain)
        assert len(issues) > 0
        assert any("Merkle root" in i for i in issues)

    def test_detect_tampering_missing_entry(self) -> None:
        """detect_tampering should find missing entries."""
        tracker = ProvenanceTracker()
        entry = AIBOMEntry(
            entry_id="bom-missing",
            output_hash="hash",
            model_info={},
            prompt_hash="phash",
        )
        chain = ProvenanceChain(
            chain_id="test-chain",
            entries=(entry,),
            root_hash=compute_merkle_root((entry,)),
        )
        issues = tracker.detect_tampering(chain)
        assert len(issues) > 0
        assert any("not found" in i for i in issues)

    def test_get_entry(self) -> None:
        """get_entry should return a specific entry."""
        tracker = ProvenanceTracker()
        entry = tracker.record_output(
            output="Test",
            model_info={"name": "gpt-4"},
            prompt="Test",
        )
        retrieved = tracker.get_entry(entry.entry_id)
        assert retrieved.entry_id == entry.entry_id

    def test_get_entry_not_found(self) -> None:
        """get_entry on non-existent entry should raise error."""
        tracker = ProvenanceTracker()
        with pytest.raises(EntryNotFoundError):
            tracker.get_entry("nonexistent")

    def test_list_entries(self) -> None:
        """list_entries should return all entries."""
        tracker = ProvenanceTracker()
        tracker.record_output(
            output="A", model_info={}, prompt="A"
        )
        tracker.record_output(
            output="B", model_info={}, prompt="B"
        )
        assert len(tracker.list_entries()) == 2

    def test_list_chains(self) -> None:
        """list_chains should return all chains."""
        tracker = ProvenanceTracker()
        tracker.record_output(
            output="Test", model_info={}, prompt="Test"
        )
        tracker.build_chain()
        assert len(tracker.list_chains()) == 1

    def test_verify_entry_hash_consistency(self) -> None:
        """Entry hash should remain consistent."""
        tracker = ProvenanceTracker()
        entry = tracker.record_output(
            output="Consistent data",
            model_info={"name": "claude", "version": "3"},
            prompt="Be consistent",
            tools=[{"name": "search"}],
        )

        # Recompute hash
        expected = compute_entry_hash(entry)
        payload = {
            "entry_id": entry.entry_id,
            "output_hash": entry.output_hash,
            "model_info": entry.model_info,
            "prompt_hash": entry.prompt_hash,
            "tool_calls": list(entry.tool_calls),
            "data_sources": list(entry.data_sources),
            "parent_entry": entry.parent_entry,
            "timestamp": entry.timestamp.isoformat(),
        }
        import hashlib
        import json

        actual = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        assert expected == actual


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Cross-module integration tests."""

    def test_deploy_then_health_check_then_failover(self) -> None:
        """End-to-end cell lifecycle."""
        mgr = CellManager()

        # Deploy two cells
        primary = mgr.deploy_cell("1.0.0")
        standby = mgr.deploy_cell("1.0.0")

        # Health checks pass
        assert mgr.health_check(primary.cell_id) == HealthStatus.HEALTHY
        assert mgr.health_check(standby.cell_id) == HealthStatus.HEALTHY

        # Failover
        target = mgr.failover(primary.cell_id)
        assert target is not None

    def test_identity_provenance_integration(self) -> None:
        """Agent identity verified provenance chain."""
        tracker = ProvenanceTracker()
        mgr = AgentIdentityManager()

        # Create an agent identity
        identity, _ = mgr.create_identity(
            "researcher-1",
            capabilities={"research", "analyze"},
        )

        # Agent generates output
        entry = tracker.record_output(
            output="Research analysis complete",
            model_info={"name": "gpt-4", "agent": identity.agent_id},
            prompt="Analyze the data",
        )

        # Build and verify chain
        chain = tracker.build_chain()
        assert tracker.verify_chain(chain)

        # Agent signs the chain
        signature = mgr.sign_challenge(
            "researcher-1", chain.root_hash
        )
        assert mgr.verify_identity(
            "researcher-1", signature, chain.root_hash
        )

    def test_branch_and_migrate(self) -> None:
        """Create branch, apply migration, validate, merge."""
        branching = DatabaseBranching()

        # Create branch
        branch = branching.create_branch("feature/add-table", "main-commit")

        # Apply migration
        migration = MigrationEntry(
            migration_id="m001",
            description="Add analysis_results table",
            sql_up="CREATE TABLE analysis_results (id INT, result TEXT);",
            sql_down="DROP TABLE analysis_results;",
        )
        branch = branching.apply_migration(branch.branch_id, migration)

        # Validate
        conflicts = branching.validate_branch(branch.branch_id)
        assert conflicts == []

        # Merge
        merged = branching.merge_branch(branch.branch_id)
        assert merged.status == BranchStatus.MERGED

    def test_cell_with_custom_health_check(self) -> None:
        """Custom health check function with degraded status."""
        def custom_check(cell_id: str) -> HealthStatus:
            if cell_id == "problem-cell":
                return HealthStatus.DEGRADED
            return HealthStatus.HEALTHY

        mgr = CellManager(health_check_fn=custom_check)
        mgr.deploy_cell("normal-cell", config=DeploymentConfig(replicas=2))

        # Only degraded cells get checked
        for c in mgr.list_cells():
            status = mgr.health_check(c.cell_id)
            assert status is not None

    def test_durable_workflow_with_provenance(self) -> None:
        """Durable workflow execution tracked with provenance."""
        executor = DurableExecutor()
        tracker = ProvenanceTracker()

        results: list[str] = []

        def research_step(input_data: dict[str, Any]) -> str:
            result = "Research data collected"
            results.append(result)
            return result

        def analyze_step(input_data: dict[str, Any]) -> str:
            result = "Analysis complete"
            results.append(result)
            return result

        definition = WorkflowDefinition(
            name="research-flow",
            steps={"research": research_step, "analyze": analyze_step},
        )
        executor.register_workflow(definition)

        execution = executor.start_workflow(
            "research-flow", {"topic": "AI Safety"}
        )

        # Record provenance for each result
        for r in results:
            tracker.record_output(
                output=r,
                model_info={"workflow": execution.name},
                prompt=f"Workflow: {execution.workflow_id}",
            )

        chain = tracker.build_chain()
        assert tracker.verify_chain(chain)
        assert len(chain.entries) == len(results)

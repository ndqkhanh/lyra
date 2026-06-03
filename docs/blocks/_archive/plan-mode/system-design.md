# Plan Mode System Design

## Overview

This document describes the high-level system design for Plan Mode: the abstractions, API contracts, state management, error handling, and scalability considerations. It serves as the bridge between architecture (what components exist) and implementation (how to build them).

## Core Abstractions

### 1. The Planner Interface

The Planner is a stateless agent that consumes context and produces a plan artifact.

```python
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class PlanningContext:
    """Input context for the Planner."""
    task: str                          # User's original request
    session_id: str                    # Unique session identifier
    repo_snapshot: RepoSnapshot        # Read-only view of repository
    config: PlanConfig                 # User configuration
    previous_plan: Optional[PlanArtifact] = None  # For revisions
    execution_state: Optional[ExecutionState] = None  # For mid-execution replans


@dataclass
class RepoSnapshot:
    """Read-only repository state."""
    root_path: str
    git_hash: Optional[str]            # Current commit (if git repo)
    file_tree: dict[str, FileMetadata] # Path -> metadata
    recent_edits: list[EditHistory]    # Last 24h changes
    
    def read_file(self, path: str) -> str:
        """Read file contents."""
        pass
    
    def search(self, pattern: str, file_pattern: str = "*") -> list[SearchResult]:
        """Search across files."""
        pass
    
    def get_symbols(self, path: str) -> list[Symbol]:
        """Get code symbols (functions, classes) via LSP."""
        pass


class Planner(ABC):
    """Abstract planner interface."""
    
    @abstractmethod
    async def generate_plan(self, context: PlanningContext) -> PlanArtifact:
        """
        Generate a plan artifact from context.
        
        Raises:
            PlanningError: If planning fails
            ValidationError: If generated plan doesn't match schema
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, context: PlanningContext) -> float:
        """Estimate cost in USD before generating plan."""
        pass


class ModelBackedPlanner(Planner):
    """Planner implementation using LLM."""
    
    def __init__(self, model_id: str, permission_manager: PermissionManager):
        self.model_id = model_id
        self.permissions = permission_manager
        self.system_prompt = PLANNER_SYSTEM_PROMPT
    
    async def generate_plan(self, context: PlanningContext) -> PlanArtifact:
        """
        1. Set PermissionMode.PLAN
        2. Create agent with read-only tools
        3. Execute with task + repo snapshot
        4. Parse and validate output
        5. Return PlanArtifact
        """
        with self.permissions.scope(PermissionMode.PLAN):
            tools = self._get_read_only_tools(context.repo_snapshot)
            agent = Agent(
                model=self.model_id,
                system_prompt=self.system_prompt,
                tools=tools,
            )
            
            user_prompt = self._build_user_prompt(context)
            response = await agent.run(user_prompt)
            
            plan = self._parse_plan(response.content, context)
            self._validate_plan(plan, context.repo_snapshot)
            
            return plan
```

### 2. Permission System

Plan Mode relies on a permission system that enforces read-only constraints.

```python
from enum import Enum
from contextlib import contextmanager
from typing import Callable

class PermissionMode(Enum):
    """Execution permission modes."""
    PLAN = "plan"              # Read-only planning
    DEFAULT = "default"        # Standard execution with asks
    ACCEPT_EDITS = "acceptEdits"  # Auto-accept file edits
    ASK_ALL = "askAll"         # Confirm every tool call


class ToolPermission(Enum):
    """Permission decisions for tool invocations."""
    ALLOW = "allow"            # Execute without asking
    DENY = "deny"              # Block with error
    ASK = "ask"                # Prompt user for approval


class PermissionManager:
    """Manages permission modes and tool allowlists."""
    
    def __init__(self):
        self._mode_stack: list[PermissionMode] = [PermissionMode.DEFAULT]
        self._tool_rules: dict[PermissionMode, dict[str, ToolPermission]] = {
            PermissionMode.PLAN: {
                "Read": ToolPermission.ALLOW,
                "Grep": ToolPermission.ALLOW,
                "Glob": ToolPermission.ALLOW,
                "WebFetch": ToolPermission.ALLOW,
                "LSP": ToolPermission.ALLOW,
                "AskUser": ToolPermission.ALLOW,
                "Write": ToolPermission.DENY,
                "Edit": ToolPermission.DENY,
                "Bash": ToolPermission.DENY,
                "Delete": ToolPermission.DENY,
            },
            # ... other modes
        }
    
    @contextmanager
    def scope(self, mode: PermissionMode):
        """Context manager for temporary permission mode."""
        self._mode_stack.append(mode)
        try:
            yield
        finally:
            self._mode_stack.pop()
    
    def check_tool(self, tool_name: str) -> ToolPermission:
        """Check if tool is allowed in current mode."""
        current_mode = self._mode_stack[-1]
        rules = self._tool_rules.get(current_mode, {})
        return rules.get(tool_name, ToolPermission.ASK)
    
    def enforce(self, tool_name: str) -> None:
        """Enforce permission check (raises if denied)."""
        permission = self.check_tool(tool_name)
        if permission == ToolPermission.DENY:
            raise PermissionDeniedError(
                f"Tool '{tool_name}' is denied in {self._mode_stack[-1].value} mode"
            )
```

### 3. Approval Gateway

The approval gateway coordinates the three approval mechanisms.

```python
from abc import ABC, abstractmethod
from enum import Enum

class ApprovalSource(Enum):
    """Source of plan approval."""
    INTERACTIVE = "interactive"
    AUTO = "auto"
    CI_SIGNED = "ci-signed"


class ApprovalDecision(Enum):
    """User's decision on plan."""
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"          # User edited plan, re-validate


@dataclass
class ApprovalResult:
    """Result of approval process."""
    decision: ApprovalDecision
    source: ApprovalSource
    approver: Optional[str]     # User ID or CI run ID
    signature: Optional[str]    # For CI-signed approvals
    edited_plan: Optional[PlanArtifact] = None  # If decision == EDITED


class ApprovalGateway(ABC):
    """Abstract approval interface."""
    
    @abstractmethod
    async def request_approval(self, plan: PlanArtifact) -> ApprovalResult:
        """Request approval for a plan."""
        pass


class InteractiveApprovalGateway(ApprovalGateway):
    """CLI/Web-based interactive approval."""
    
    def __init__(self, renderer: PlanRenderer, editor: Optional[str] = None):
        self.renderer = renderer
        self.editor = editor or os.getenv("EDITOR", "vim")
    
    async def request_approval(self, plan: PlanArtifact) -> ApprovalResult:
        """
        1. Render plan to terminal/web
        2. Prompt user: /approve, /reject, /edit, /question
        3. Handle response
        4. Return decision
        """
        self.renderer.render(plan)
        
        while True:
            command = await self._prompt_user()
            
            if command.startswith("/approve"):
                return ApprovalResult(
                    decision=ApprovalDecision.APPROVED,
                    source=ApprovalSource.INTERACTIVE,
                    approver=os.getenv("USER"),
                )
            
            elif command.startswith("/reject"):
                return ApprovalResult(
                    decision=ApprovalDecision.REJECTED,
                    source=ApprovalSource.INTERACTIVE,
                    approver=os.getenv("USER"),
                )
            
            elif command.startswith("/edit"):
                edited = await self._open_editor(plan)
                return ApprovalResult(
                    decision=ApprovalDecision.EDITED,
                    source=ApprovalSource.INTERACTIVE,
                    approver=os.getenv("USER"),
                    edited_plan=edited,
                )
            
            elif command.startswith("/question"):
                # Agent answers question, re-render
                await self._handle_question(command[10:])
                self.renderer.render(plan)


class AutoApprovalGateway(ApprovalGateway):
    """Auto-approve for CI."""
    
    async def request_approval(self, plan: PlanArtifact) -> ApprovalResult:
        """Immediately approve with CI metadata."""
        ci_run_id = os.getenv("CI_RUN_ID", "local")
        logger.info(f"Auto-approving plan {plan.session_id} in CI run {ci_run_id}")
        
        return ApprovalResult(
            decision=ApprovalDecision.APPROVED,
            source=ApprovalSource.AUTO,
            approver=f"ci:{ci_run_id}",
        )


class CISignedApprovalGateway(ApprovalGateway):
    """Verify HMAC signature for CI-signed plans."""
    
    def __init__(self, secret: str):
        self.secret = secret
    
    async def request_approval(self, plan: PlanArtifact) -> ApprovalResult:
        """Verify signature matches expected value."""
        signature = os.getenv("LYRA_PLAN_SIGNATURE")
        if not signature:
            raise ValueError("LYRA_PLAN_SIGNATURE not provided")
        
        expected = self._compute_signature(plan)
        if not hmac.compare_digest(expected, signature):
            raise SecurityError("Plan signature verification failed")
        
        return ApprovalResult(
            decision=ApprovalDecision.APPROVED,
            source=ApprovalSource.CI_SIGNED,
            approver="ci:signed",
            signature=signature,
        )
    
    def _compute_signature(self, plan: PlanArtifact) -> str:
        """Compute HMAC-SHA256 of plan identity."""
        message = f"{plan.path}|{plan.goal_hash}|{plan.session_id}".encode()
        return hmac.new(self.secret.encode(), message, hashlib.sha256).hexdigest()
```

### 4. Plan Storage

Plans are persisted as files with an in-memory index for fast lookups.

```python
from pathlib import Path
import json
from typing import Optional

class PlanStore:
    """Manages plan artifact persistence."""
    
    def __init__(self, plans_dir: Path):
        self.plans_dir = plans_dir
        self.index_path = plans_dir / "index.json"
        self._index: dict[str, dict] = self._load_index()
    
    def save(self, plan: PlanArtifact) -> Path:
        """
        Save plan to file system and update index.
        
        Returns:
            Path to saved plan file
        """
        # Determine filename
        if plan.revision_num > 0:
            filename = f"{plan.session_id}.rev-{plan.revision_num}.md"
        else:
            filename = f"{plan.session_id}.md"
        
        plan_path = self.plans_dir / filename
        
        # Write markdown
        plan_path.write_text(plan.to_markdown())
        
        # Update index
        self._index[plan.session_id] = {
            "session_id": plan.session_id,
            "created_at": plan.created_at.isoformat(),
            "title": plan.title,
            "status": "pending",
            "revisions": plan.revision_num,
            "path": str(plan_path),
        }
        self._save_index()
        
        return plan_path
    
    def load(self, session_id: str, revision: Optional[int] = None) -> PlanArtifact:
        """Load plan by session ID."""
        if session_id not in self._index:
            raise KeyError(f"No plan found for session {session_id}")
        
        # Get path from index
        if revision is not None:
            path = self.plans_dir / f"{session_id}.rev-{revision}.md"
        else:
            path = Path(self._index[session_id]["path"])
        
        if not path.exists():
            raise FileNotFoundError(f"Plan file missing: {path}")
        
        # Parse markdown
        content = path.read_text()
        return PlanArtifact.from_markdown(content)
    
    def mark_approved(self, session_id: str, approver: str, source: ApprovalSource):
        """Update index to mark plan as approved."""
        if session_id not in self._index:
            raise KeyError(f"No plan found for session {session_id}")
        
        self._index[session_id]["status"] = "approved"
        self._index[session_id]["approver"] = approver
        self._index[session_id]["approval_source"] = source.value
        self._save_index()
    
    def list_all(self) -> list[dict]:
        """List all plans in index."""
        return list(self._index.values())
    
    def _load_index(self) -> dict:
        """Load index.json if exists, else return empty dict."""
        if self.index_path.exists():
            return json.loads(self.index_path.read_text())
        return {}
    
    def _save_index(self):
        """Persist index to disk."""
        self.index_path.write_text(json.dumps(self._index, indent=2))
```

## API Contracts

### Main Plan Mode Orchestrator

```python
class PlanModeOrchestrator:
    """
    Coordinates the full plan mode workflow.
    """
    
    def __init__(
        self,
        planner: Planner,
        approval_gateway: ApprovalGateway,
        plan_store: PlanStore,
        permission_manager: PermissionManager,
        heuristics: TrivialityHeuristics,
    ):
        self.planner = planner
        self.approval = approval_gateway
        self.store = plan_store
        self.permissions = permission_manager
        self.heuristics = heuristics
    
    async def run(self, task: str, session_id: str, config: PlanConfig) -> PlanResult:
        """
        Execute full plan mode workflow.
        
        Returns:
            PlanResult with approved plan or skip decision
        """
        # 1. Check if task is trivial
        repo_snapshot = await self._create_repo_snapshot()
        
        if self.heuristics.is_trivial(task, repo_snapshot):
            logger.info(f"Task marked trivial, skipping plan mode")
            return PlanResult.skipped(reason="trivial")
        
        # 2. Generate plan
        context = PlanningContext(
            task=task,
            session_id=session_id,
            repo_snapshot=repo_snapshot,
            config=config,
        )
        
        plan = await self.planner.generate_plan(context)
        
        # 3. Save plan
        plan_path = self.store.save(plan)
        logger.info(f"Plan saved to {plan_path}")
        
        # 4. Request approval
        approval_result = await self.approval.request_approval(plan)
        
        # 5. Handle approval decision
        if approval_result.decision == ApprovalDecision.APPROVED:
            self.store.mark_approved(
                session_id,
                approval_result.approver,
                approval_result.source,
            )
            return PlanResult.approved(plan)
        
        elif approval_result.decision == ApprovalDecision.REJECTED:
            return PlanResult.rejected()
        
        elif approval_result.decision == ApprovalDecision.EDITED:
            # User edited plan; validate and re-save
            edited = approval_result.edited_plan
            self._validate_plan(edited, repo_snapshot)
            self.store.save(edited)
            return PlanResult.approved(edited)


@dataclass
class PlanResult:
    """Result of plan mode workflow."""
    status: str  # "approved" | "rejected" | "skipped"
    plan: Optional[PlanArtifact] = None
    skip_reason: Optional[str] = None
    
    @classmethod
    def approved(cls, plan: PlanArtifact):
        return cls(status="approved", plan=plan)
    
    @classmethod
    def rejected(cls):
        return cls(status="rejected")
    
    @classmethod
    def skipped(cls, reason: str):
        return cls(status="skipped", skip_reason=reason)
```

## State Management

### Session State Machine

```python
from enum import Enum

class SessionPhase(Enum):
    """Phases of a Lyra session."""
    INIT = "init"                  # Session created
    PLANNING = "planning"          # Generating plan
    APPROVAL_PENDING = "approval_pending"  # Waiting for approval
    EXECUTING = "executing"        # Running agent loop
    VERIFYING = "verifying"        # Final verification
    COMPLETED = "completed"        # Session ended successfully
    FAILED = "failed"              # Session ended with error


class SessionState:
    """Tracks session lifecycle."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.phase = SessionPhase.INIT
        self.plan: Optional[PlanArtifact] = None
        self.execution_progress: list[str] = []  # Completed feature items
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def transition_to(self, new_phase: SessionPhase):
        """Validate and execute phase transition."""
        valid_transitions = {
            SessionPhase.INIT: [SessionPhase.PLANNING, SessionPhase.EXECUTING],
            SessionPhase.PLANNING: [SessionPhase.APPROVAL_PENDING, SessionPhase.FAILED],
            SessionPhase.APPROVAL_PENDING: [SessionPhase.EXECUTING, SessionPhase.PLANNING],
            SessionPhase.EXECUTING: [SessionPhase.VERIFYING, SessionPhase.PLANNING, SessionPhase.FAILED],
            SessionPhase.VERIFYING: [SessionPhase.COMPLETED, SessionPhase.FAILED],
        }
        
        if new_phase not in valid_transitions.get(self.phase, []):
            raise InvalidTransitionError(
                f"Cannot transition from {self.phase.value} to {new_phase.value}"
            )
        
        logger.info(f"Session {self.session_id}: {self.phase.value} → {new_phase.value}")
        self.phase = new_phase
        self.updated_at = datetime.utcnow()
    
    def mark_item_complete(self, item_index: int):
        """Mark a feature item as completed."""
        if self.phase != SessionPhase.EXECUTING:
            raise ValueError("Can only mark items complete during execution")
        
        self.execution_progress.append(str(item_index))
        self.updated_at = datetime.utcnow()
```

## Error Handling

### Error Hierarchy

```python
class PlanModeError(Exception):
    """Base exception for plan mode errors."""
    pass

class PlanningError(PlanModeError):
    """Planner failed to generate valid plan."""
    pass

class ValidationError(PlanModeError):
    """Plan artifact doesn't match schema."""
    pass

class ApprovalTimeoutError(PlanModeError):
    """User didn't respond to approval request within timeout."""
    pass

class SecurityError(PlanModeError):
    """Security violation (e.g., invalid signature)."""
    pass

class PermissionDeniedError(PlanModeError):
    """Tool usage denied by permission system."""
    pass
```

### Retry Strategy

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

class ResilientPlanner:
    """Planner with automatic retry logic."""
    
    @retry(
        retry=retry_if_exception_type((ModelTimeoutError, RateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    async def generate_plan(self, context: PlanningContext) -> PlanArtifact:
        """Generate plan with retries for transient errors."""
        return await self.planner.generate_plan(context)
    
    async def generate_plan_with_fallback(
        self,
        context: PlanningContext,
    ) -> PlanArtifact:
        """Try primary model, fall back to secondary if primary fails."""
        try:
            return await self.generate_plan(context)
        except (ModelTimeoutError, ModelUnavailableError) as e:
            logger.warning(f"Primary model failed: {e}, trying fallback")
            
            # Switch to fallback model
            fallback_planner = ModelBackedPlanner(
                model_id=context.config.smart_fallback,
                permission_manager=self.permissions,
            )
            return await fallback_planner.generate_plan(context)
```

## Scalability Considerations

### Concurrent Planning

Plan Mode supports concurrent sessions:

```python
import asyncio
from typing import Dict

class PlanModeService:
    """Service managing multiple concurrent plan mode sessions."""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_sessions: Dict[str, asyncio.Task] = {}
    
    async def start_session(
        self,
        task: str,
        session_id: str,
        config: PlanConfig,
    ) -> PlanResult:
        """Start a new plan mode session (with concurrency limit)."""
        async with self.semaphore:
            orchestrator = self._create_orchestrator(config)
            return await orchestrator.run(task, session_id, config)
    
    def _create_orchestrator(self, config: PlanConfig) -> PlanModeOrchestrator:
        """Factory method for orchestrator."""
        # ... create dependencies
        return PlanModeOrchestrator(
            planner=planner,
            approval_gateway=approval,
            plan_store=store,
            permission_manager=permissions,
            heuristics=heuristics,
        )
```

### Plan Artifact Size Limits

To prevent unbounded growth:

```python
class PlanValidator:
    """Validates plan artifacts against constraints."""
    
    MAX_FEATURE_ITEMS = 30
    MAX_EXPECTED_FILES = 100
    MAX_TITLE_LENGTH = 200
    
    def validate(self, plan: PlanArtifact, repo: RepoSnapshot):
        """Validate plan meets all constraints."""
        errors = []
        
        # Size limits
        if len(plan.feature_items) > self.MAX_FEATURE_ITEMS:
            errors.append(
                f"Too many feature items ({len(plan.feature_items)}). "
                f"Maximum: {self.MAX_FEATURE_ITEMS}. Consider breaking into sub-tasks."
            )
        
        if len(plan.expected_files) > self.MAX_EXPECTED_FILES:
            errors.append(f"Too many expected files ({len(plan.expected_files)})")
        
        # Schema validation
        if not plan.acceptance_tests:
            if not any("test_gen" in item.get("skill", "") for item in plan.feature_items):
                errors.append("No acceptance tests and no test_gen item")
        
        # File existence
        for file_entry in plan.expected_files:
            path = file_entry["path"]
            if path not in repo.file_tree and "new" not in file_entry.get("note", ""):
                errors.append(f"Expected file doesn't exist: {path}")
        
        if errors:
            raise ValidationError("\n".join(errors))
```

## Integration with Execution Loop

After plan approval, execution loop uses plan as contract:

```python
class ExecutionLoop:
    """Agent loop that executes an approved plan."""
    
    def __init__(
        self,
        plan: PlanArtifact,
        model_id: str,
        permission_manager: PermissionManager,
        verifier: Verifier,
    ):
        self.plan = plan
        self.model_id = model_id
        self.permissions = permission_manager
        self.verifier = verifier
        self.current_item = 0
    
    async def run(self) -> ExecutionResult:
        """Execute all feature items in plan."""
        # Exit plan mode, enter execution mode
        permission_mode = self._determine_permission_mode()
        
        with self.permissions.scope(permission_mode):
            agent = Agent(
                model=self.model_id,
                system_prompt=self._build_execution_prompt(),
                tools=self._get_execution_tools(),
            )
            
            # Execute items sequentially
            for i, item in enumerate(self.plan.feature_items):
                self.current_item = i
                result = await self._execute_item(agent, item)
                
                if result.status == "blocked":
                    # Replan needed
                    return ExecutionResult.replan_needed(
                        completed_items=i,
                        blocker=result.error,
                    )
            
            # Verify plan compliance
            verification = await self.verifier.verify(self.plan)
            
            return ExecutionResult.completed(verification)
    
    def _build_execution_prompt(self) -> str:
        """Include plan summary in execution agent prompt."""
        return f"""
You are executing an approved plan.

Plan summary:
- Title: {self.plan.title}
- Acceptance tests: {len(self.plan.acceptance_tests)} tests must pass
- Expected files: {len(self.plan.expected_files)} files to create/modify
- Forbidden files: {[f['path'] for f in self.plan.forbidden_files]}

Current feature item: {self.current_item + 1} of {len(self.plan.feature_items)}
"""
```

## Next Steps

- [Architecture Overview](architecture.md) — System components and data flow
- [Architecture Tradeoffs](architecture-tradeoffs.md) — Design decisions explained
- [Implementation Guide](implementation-guide.md) — Build Plan Mode step-by-step
- [Deep Dive](deep-dive.md) — Internal algorithms and optimizations

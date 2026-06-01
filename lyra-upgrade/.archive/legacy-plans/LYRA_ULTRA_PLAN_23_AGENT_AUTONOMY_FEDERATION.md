# LYRA ULTRA PLAN 23: Agent Autonomy & Federation — Breakthrough Blueprint

**Version:** 1.0.0 | **Status:** Active Planning | **Created:** 2026-05-26
**Parent Plan:** [LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md](LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md)

---

## Executive Summary

Lyra's agents currently operate as interactive session-bound entities. They cannot run unattended, federate across trust boundaries, coordinate as teams with structured roles, or communicate efficiently. This plan bridges those gaps in a unified architecture drawn from 10+ research sources.

**The core insight:** True AGI requires agents that can operate autonomously for days (not minutes), cooperate in teams with structured roles, communicate across zero-trust boundaries, and compress their internal communication to preserve context. Each of these capabilities exists in research prototypes but has never been synthesized into a single cohesive system.

**Key innovations synthesized:**

| Capability | Source | Lyra Innovation |
|-----------|--------|----------------|
| Continuous operation | Continuous-Claude relay-race | Triple-budget governance + stall detection |
| Goal persistence | Claude Code Goals | Dependency-aware goal trees with auto-resume |
| Compound reasoning | OpenDev 5-slot architecture | Plan/Execute/Verify/Reflect/Compress slots |
| Agent teams | Claude Code Agent Teams | DAG-based task decomposition + consensus |
| Zero-trust federation | Ruflo mesh topology | mTLS + behavioral trust scoring |
| Latent communication | RecursiveMAS (arXiv:2604.25917) | RecursiveLink with 75.6% token reduction |
| Output compression | RTK / Caveman / TokenJuice | Adaptive compression selector |
| Autonomous safety | Claude Code permission modes | Escalation tiers + action auditing |

**Target outcome:** Lyra agents that run for days unattended, coordinate in teams of 10+, federate across machines, communicate with 75% less overhead, and never violate safety bounds.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    AGENT AUTONOMY & FEDERATION LAYER                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │              CONTINUOUS AUTONOMY ENGINE (23.1)                  │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │     │
│  │  │ Relay-   │  │ Triple-  │  │ Stall    │  │ Check-   │       │     │
│  │  │ Race     │  │ Budget   │  │ Detect   │  │ point    │       │     │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │     │
│  └───────┼─────────────┼─────────────┼─────────────┼─────────────┘     │
│          │             │             │             │                     │
│  ┌───────▼─────────────▼─────────────▼─────────────▼─────────────┐     │
│  │              GOAL-DRIVEN AUTONOMOUS MODE (23.2)                │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │     │
│  │  │ Goal     │  │ Progress │  │ Depend-  │  │ Auto-    │       │     │
│  │  │ Registry│  │ Tracker  │  │ ency Map │  │ Resume   │       │     │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │     │
│  └───────┼─────────────┼─────────────┼─────────────┼─────────────┘     │
│          │             │             │             │                     │
│  ┌───────▼─────────────▼─────────────▼─────────────▼─────────────┐     │
│  │              TEAM ORCHESTRATION LAYER (23.4)                   │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │     │
│  │  │ Shared   │  │ DAG Task │  │ Consensus│  │ Parallel │       │     │
│  │  │ Task List│  │ Decompose│  │ Engine   │  │ Fan-out  │       │     │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │     │
│  └───────┼─────────────┼─────────────┼─────────────┼─────────────┘     │
│          │             │             │             │                     │
│  ┌───────▼─────────────▼─────────────▼─────────────▼─────────────┐     │
│  │              COMPOUND AGENT ARCHITECTURE (23.3)                │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │     │
│  │  │ Plan     │  │ Execute  │  │ Verify   │  │ Reflect  │       │     │
│  │  │ Slot     │  │ Slot     │  │ Slot     │  │ Slot     │       │     │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │     │
│  └────────────────────────────────────────────────────────────────┘     │
│                                                                           │
├──────────────────────────────────────────────────────────────────────────┤
│                    FEDERATION & INFRASTRUCTURE                            │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Zero-Trust   │  │ Inter-Agent  │  │ Compression  │                   │
│  │ Federation   │  │ Comms        │  │ Engine       │                   │
│  │ (23.5)       │  │ (23.6)       │  │ (23.7)       │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                           │
├──────────────────────────────────────────────────────────────────────────┤
│                    SAFETY GOVERNANCE                                       │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Permission   │  │ Budget       │  │ Action       │                   │
│  │ Escalation   │  │ Enforcement  │  │ Audit Log    │                   │
│  │ (23.8)       │  │ (23.8)       │  │ (23.8)       │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 23.1: Continuous Autonomy Engine (Weeks 1-2)

Transform Lyra from session-bound interaction to persistent autonomous operation. The relay-race pattern hands off execution between sessions, preserving context through checkpointing.

### 23.1.1 Relay-Race Autonomy

Inspired by Continuous-Claude: instead of a single long-running session, Lyra operates as a chain of short sessions where each session picks up from the previous checkpoint.

```python
class RelayRaceEngine:
    """Continuous operation via relay-race session handoffs."""
    
    def __init__(self, storage_path: Path):
        self.storage = storage_path
        self.storage.mkdir(parents=True, exist_ok=True)
    
    async def start(
        self,
        task: str,
        max_iterations: int = 100,
        cost_budget_usd: float = 10.0,
        duration_hours: float = 48.0
    ) -> str:
        """Start a relay-race autonomous run.
        
        Spawns a session, monitors it, and on completion or near-full
        context, spawns the next session with state carried forward.
        """
        run_id = f"relay_{int(time.time())}"
        
        # Create initial session
        session = await self._create_session(run_id, task)
        
        # Track budgets
        budget = BudgetTracker(
            max_iterations=max_iterations,
            max_cost=cost_budget_usd,
            deadline=datetime.now() + timedelta(hours=duration_hours)
        )
        
        # Start relay loop in background
        asyncio.create_task(self._relay_loop(run_id, session, budget))
        
        return run_id
    
    async def _relay_loop(
        self,
        run_id: str,
        session: AutonomousSession,
        budget: BudgetTracker
    ) -> None:
        """Main relay-race loop."""
        iteration = 0
        
        while not budget.exhausted():
            # Execute session until: context near-full, stall, or budget hit
            result = await session.run_until_completion(
                max_turns=budget.remaining_iterations()
            )
            
            # Check for stall
            if self._is_stalled(result):
                result = await self._recover_from_stall(session, result)
            
            # Create checkpoint
            checkpoint_id = await self._checkpoint(run_id, session, iteration)
            
            # Auto-summary for handoff
            summary = await self._summarize_for_handoff(session, result)
            
            # Hand off to next session (relay race)
            session = await self._create_relay_session(run_id, summary, checkpoint_id)
            
            budget.record_iteration(summary)
            iteration += 1
        
        # Final summary
        await self._finalize_run(run_id, session)
    
    def _is_stalled(self, result: SessionResult) -> bool:
        """Detect stall via no-progress heuristic."""
        if len(result.recent_actions) < 3:
            return False
        recent_diff = result.recent_actions[-3:]
        return all(
            a.action_type == recent_diff[0].action_type
            for a in recent_diff
        )
    
    async def _recover_from_stall(
        self,
        session: AutonomousSession,
        result: SessionResult
    ) -> SessionResult:
        """Auto-recover from stall by switching strategy."""
        # Log stall
        logger.warn(f"Stall detected: {result.session_id}")
        
        # Generate alternative approach
        new_strategy = await session.llm.generate(
            f"The current approach is stalled. Last 3 actions: {result.recent_actions[-3:]}"
            f"Generate a completely different strategy to make progress."
        )
        
        # Apply new strategy
        return await session.apply_strategy(new_strategy)
```

### 23.1.2 Triple-Budget Governance

Three independent budgets that each can trigger session termination:

```python
@dataclass
class BudgetTracker:
    """Triple-budget governance for autonomous operation."""
    
    max_iterations: int
    max_cost: float
    deadline: datetime
    
    iterations_used: int = 0
    cost_used: float = 0.0
    
    def exhausted(self) -> bool:
        """Check if any budget is exhausted."""
        if self.iterations_used >= self.max_iterations:
            logger.info(f"Iteration budget exhausted: {self.iterations_used}/{self.max_iterations}")
            return True
        if self.cost_used >= self.max_cost:
            logger.info(f"Cost budget exhausted: ${self.cost_used:.2f}/${self.max_cost:.2f}")
            return True
        if datetime.now() >= self.deadline:
            logger.info(f"Duration budget exhausted: deadline passed")
            return True
        return False
    
    def remaining_iterations(self) -> int:
        return max(0, self.max_iterations - self.iterations_used)
```

### 23.1.3 Checkpoint/Resume System

Full state serialization for cross-session persistence:

```python
@dataclass
class Checkpoint:
    """Serialized agent state for cross-session persistence."""
    checkpoint_id: str
    run_id: str
    iteration: int
    session_state: dict  # Serialized agent context
    current_task: str
    completed_tasks: list[str]
    artifacts: list[Path]
    timestamp: datetime
    summary: str  # LLM-generated summary for next session

class CheckpointManager:
    """Manage checkpoints across autonomous sessions."""
    
    def __init__(self, storage_path: Path):
        self.path = storage_path / "checkpoints"
        self.path.mkdir(parents=True, exist_ok=True)
    
    async def save(self, checkpoint: Checkpoint) -> str:
        """Persist checkpoint to disk. Returns checkpoint ID."""
        ckpt_path = self.path / checkpoint.checkpoint_id
        ckpt_path.mkdir(parents=True, exist_ok=True)
        
        # Serialize state
        async with aiofiles.open(ckpt_path / "state.json", "w") as f:
            await f.write(json.dumps(checkpoint.session_state, indent=2))
        
        # Write summary
        async with aiofiles.open(ckpt_path / "summary.md", "w") as f:
            await f.write(checkpoint.summary)
        
        # Record metadata
        metadata = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "run_id": checkpoint.run_id,
            "iteration": checkpoint.iteration,
            "timestamp": checkpoint.timestamp.isoformat(),
            "completed_tasks": checkpoint.completed_tasks,
        }
        async with aiofiles.open(ckpt_path / "metadata.json", "w") as f:
            await f.write(json.dumps(metadata, indent=2))
        
        return checkpoint.checkpoint_id
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from disk."""
        ckpt_path = self.path / checkpoint_id
        if not ckpt_path.exists():
            return None
        
        async with aiofiles.open(ckpt_path / "state.json") as f:
            state = json.loads(await f.read())
        async with aiofiles.open(ckpt_path / "summary.md") as f:
            summary = await f.read()
        async with aiofiles.open(ckpt_path / "metadata.json") as f:
            metadata = json.loads(await f.read())
        
        return Checkpoint(
            checkpoint_id=metadata["checkpoint_id"],
            run_id=metadata["run_id"],
            iteration=metadata["iteration"],
            session_state=state,
            current_task=state.get("current_task", ""),
            completed_tasks=metadata["completed_tasks"],
            artifacts=[],
            timestamp=datetime.fromisoformat(metadata["timestamp"]),
            summary=summary
        )
    
    def list_checkpoints(self, run_id: str) -> list[dict]:
        """List all checkpoints for a run with metadata."""
        checkpoints = []
        for ckpt_dir in sorted(self.path.glob("ckpt_*")):
            meta_path = ckpt_dir / "metadata.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                if meta.get("run_id") == run_id:
                    checkpoints.append(meta)
        return sorted(checkpoints, key=lambda x: x["iteration"])
```

### 23.1.4 CLI Commands

```bash
# Continuous autonomy
lyra auto-start "Refactor user service to async" --max-iterations 100 --budget 5.00 --duration 24h
lyra auto-status                           # Show running autonomous tasks
lyra auto-pause <run-id>                   # Pause autonomous task
lyra auto-resume <run-id>                  # Resume from last checkpoint
lyra auto-stop <run-id>                    # Stop autonomous task
lyra auto-log <run-id>                     # Show execution log
lyra auto-checkpoints <run-id>             # List all checkpoints

# Checkpoint management
lyra checkpoint list <run-id>              # List checkpoints
lyra checkpoint show <checkpoint-id>       # Show checkpoint details
lyra checkpoint rewind <checkpoint-id>     # Rewind to checkpoint
```

---

## Phase 23.2: Goal-Driven Autonomous Mode (Weeks 2-3)

Persistent goals that survive across sessions with auto-resume, hierarchical decomposition, and dependency-aware execution.

### 23.2.1 Goal Architecture

```python
@dataclass
class Goal:
    """A persistent, trackable goal for autonomous agents."""
    id: str
    title: str
    description: str
    criteria: list[str]            # Checkable completion criteria
    status: GoalStatus             # active | paused | completed | failed | blocked
    priority: GoalPriority         # P0 | P1 | P2 | P3
    agent_type: str                # code | research | design | sre | auto
    created_at: datetime
    deadline: Optional[datetime]
    parent_goal: Optional[str]     # For goal tree hierarchy
    sub_goals: list[str]           # Child goal IDs
    dependencies: list[str]        # Goal IDs that must complete first
    blocks: list[str]              # Goal IDs blocked by this goal
    auto_approve: bool             # Can act without user confirmation
    max_turns: int                 # Per-session turn limit
    max_cost_usd: float            # Cost budget for this goal
    check_interval: int            # Minutes between progress checks
    metrics: GoalMetrics           # Progress tracking
    history: list[GoalEvent]       # Execution log
    checkpoint_id: Optional[str]   # Last checkpoint for resume

@dataclass
class GoalMetrics:
    turns_completed: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    files_changed: int = 0
    tests_passing: int = 0
    completion_pct: float = 0.0   # Estimated from criteria
    last_activity: Optional[datetime] = None

class GoalRegistry:
    """Central registry for all autonomous goals."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.goals: dict[str, Goal] = {}
        self._load_goals()
    
    def create(
        self,
        title: str,
        description: str,
        criteria: list[str],
        priority: GoalPriority = GoalPriority.P2,
        agent_type: str = "auto",
        dependencies: Optional[list[str]] = None,
        auto_approve: bool = False
    ) -> Goal:
        """Create a new goal and register it."""
        goal = Goal(
            id=f"goal_{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            criteria=criteria,
            status=GoalStatus.ACTIVE if not dependencies else GoalStatus.BLOCKED,
            priority=priority,
            agent_type=agent_type,
            created_at=datetime.now(),
            dependencies=dependencies or [],
            auto_approve=auto_approve,
            max_turns=100,
            max_cost_usd=5.0,
            check_interval=30,
            metrics=GoalMetrics(),
            history=[]
        )
        self.goals[goal.id] = goal
        self._save_goals()
        return goal
    
    def get_ready_goals(self) -> list[Goal]:
        """Get goals that are ready to execute (dependencies met)."""
        ready = []
        for goal in self.goals.values():
            if goal.status != GoalStatus.ACTIVE:
                continue
            # Check dependencies
            deps_met = all(
                self.goals.get(dep) and self.goals[dep].status == GoalStatus.COMPLETED
                for dep in goal.dependencies
            )
            if deps_met:
                ready.append(goal)
        # Sort by priority
        ready.sort(key=lambda g: (g.priority.value, g.created_at))
        return ready
```

### 23.2.2 Goal Decomposition

```python
class GoalDecomposer:
    """Decompose complex goals into sub-goal trees."""
    
    def __init__(self, llm_client, registry: GoalRegistry):
        self.llm = llm_client
        self.registry = registry
    
    async def decompose(self, goal: Goal, max_depth: int = 3) -> list[Goal]:
        """Decompose a complex goal into manageable sub-goals.
        
        Uses LLM to identify natural decomposition boundaries
        and dependency relationships between sub-goals.
        """
        if max_depth <= 0:
            return [goal]
        
        # Ask LLM to decompose
        decomposition = await self.llm.generate(f"""
        Decompose this goal into 3-7 sub-goals:
        
        Title: {goal.title}
        Description: {goal.description}
        Criteria: {goal.criteria}
        
        For each sub-goal provide:
        - Title (actionable, specific)
        - Description (what needs to be done)
        - Criteria (checkable completion conditions)
        - Dependencies (which sub-goals must come first)
        
        Return as JSON list.
        """)
        
        sub_goals = parse_sub_goals(decomposition)
        
        # Create sub-goals in registry
        created = []
        for sg in sub_goals:
            sub = self.registry.create(
                title=sg["title"],
                description=sg["description"],
                criteria=sg["criteria"],
                priority=goal.priority,
                agent_type=goal.agent_type,
                dependencies=sg.get("dependencies", []),
                auto_approve=goal.auto_approve
            )
            sub.parent_goal = goal.id
            created.append(sub)
        
        # Link to parent
        goal.sub_goals = [g.id for g in created]
        self.registry.update(goal)
        
        return created
```

### 23.2.3 Goal Executor

```python
class GoalExecutor:
    """Execute goals with auto-resume and progress tracking."""
    
    def __init__(self, registry: GoalRegistry, checkpoint_mgr: CheckpointManager):
        self.registry = registry
        self.checkpoints = checkpoint_mgr
    
    async def execute(self, goal: Goal) -> GoalResult:
        """Execute a single goal to completion or failure."""
        
        # Check for existing checkpoint
        if goal.checkpoint_id:
            checkpoint = await self.checkpoints.load(goal.checkpoint_id)
            if checkpoint:
                # Resume from checkpoint
                return await self._resume_execution(goal, checkpoint)
        
        return await self._fresh_execution(goal)
    
    async def _fresh_execution(self, goal: Goal) -> GoalResult:
        """Execute goal from scratch."""
        iteration = 0
        
        while iteration < goal.max_turns:
            # Execute one turn
            turn_result = await self._execute_turn(goal)
            
            # Update metrics
            goal.metrics.turns_completed += 1
            goal.metrics.tokens_used += turn_result.tokens_used
            goal.metrics.cost_usd += turn_result.cost
            goal.metrics.last_activity = datetime.now()
            
            # Check completion
            if self._criteria_met(goal, turn_result):
                goal.status = GoalStatus.COMPLETED
                goal.metrics.completion_pct = 100.0
                break
            
            # Check cost
            if goal.metrics.cost_usd >= goal.max_cost_usd:
                goal.status = GoalStatus.PAUSED
                break
            
            iteration += 1
        
        self.registry.update(goal)
        return GoalResult(
            goal_id=goal.id,
            status=goal.status,
            metrics=goal.metrics
        )
    
    def _criteria_met(self, goal: Goal, result: TurnResult) -> bool:
        """Check if completion criteria are satisfied."""
        # Each criterion maps to a checkable condition
        # For now: LLM evaluates based on execution result
        return result.criteria_satisfied >= len(goal.criteria) * 0.8
```

### 23.2.4 CLI Commands

```bash
# Goal management
lyra goal "Refactor auth service to use JWT"           # Create goal
lyra goal list                                          # List active goals
lyra goal list --all                                    # All goals including completed
lyra goal show <goal-id>                                # Goal details + progress
lyra goal pause <goal-id>                               # Pause goal
lyra goal resume <goal-id>                              # Resume goal
lyra goal cancel <goal-id>                              # Cancel goal
lyra goal retry <goal-id>                               # Retry failed goal
lyra goal status                                        # All goals overview
lyra goal log <goal-id>                                 # Goal execution log
lyra goal decompose <goal-id>                           # Decompose into sub-goals
```

---

## Phase 23.3: Compound Agent Architecture (Weeks 3-4)

Inspired by OpenDev's 5-slot compound architecture. Instead of a single monolithic agent, each Lyra agent contains five specialized reasoning slots that collaborate on tasks.

### 23.3.1 Five-Slot Design

```
Agent Instance
├── Slot 1: PLAN (reasoning model)
│   ├── Task analysis and decomposition
│   ├── Approach selection
│   ├── Resource estimation
│   └── Risk identification
│
├── Slot 2: EXECUTE (coding/reasoning model)
│   ├── Tool calls and file operations
│   ├── Code generation and editing
│   ├── Shell command execution
│   └── API interactions
│
├── Slot 3: VERIFY (different model family)
│   ├── Result correctness checking
│   ├── Edge case analysis
│   ├── Security review
│   └── Criteria satisfaction check
│
├── Slot 4: REFLECT (reasoning model)
│   ├── Execution quality assessment
│   ├── Improvement identification
│   ├── Learning extraction
│   └── Strategy adjustment
│
└── Slot 5: COMPRESS (fast model)
    ├── Context compaction
    ├── Memory consolidation
    ├── Redundancy removal
    └── Token budget management
```

### 23.3.2 Slot Orchestrator

```python
class SlotOrchestrator:
    """Orchestrate the five reasoning slots for compound reasoning."""
    
    def __init__(self, config: SlotConfig):
        self.plan_slot = Slot(config.plan_model, SlotRole.PLAN)
        self.execute_slot = Slot(config.execute_model, SlotRole.EXECUTE)
        self.verify_slot = Slot(config.verify_model, SlotRole.VERIFY)
        self.reflect_slot = Slot(config.reflect_model, SlotRole.REFLECT)
        self.compress_slot = Slot(config.compress_model, SlotRole.COMPRESS)
    
    async def process_task(self, task: Task) -> TaskResult:
        """Process a task through the 5-slot pipeline."""
        
        # 1. PLAN slot
        plan = await self.plan_slot.run(
            f"Analyze this task and create an execution plan:\n{task.description}"
        )
        
        # 2. EXECUTE slot (iterative, with verify loop)
        max_attempts = 3
        for attempt in range(max_attempts):
            result = await self.execute_slot.run(
                plan.output,
                context={"task": task, "plan": plan.output}
            )
            
            # 3. VERIFY slot (different model family for adversarial verification)
            verification = await self.verify_slot.run(
                f"Verify this execution result:\nTask: {task.description}"
                f"\nPlan: {plan.output}\nResult: {result.output}"
            )
            
            if verification.metadata.get("passed", False):
                break
            
            # Refine plan based on verification
            plan = await self.plan_slot.run(
                f"The previous execution failed verification. "
                f"Errors: {verification.output}\nRevise the plan."
            )
        
        # 4. REFLECT slot
        reflection = await self.reflect_slot.run(
            f"Analyze this execution quality:\n"
            f"Task: {task.description}\nPlan: {plan.output}\n"
            f"Result: {result.output}\nVerification: {verification.output}"
        )
        
        # 5. COMPRESS slot (reduce token footprint)
        compressed = await self.compress_slot.run(
            f"Compress this execution record for storage, "
            f"preserving key decisions and outcomes:\n"
            f"Plan: {plan.output}\nResult: {result.output}\n"
            f"Reflection: {reflection.output}"
        )
        
        return TaskResult(
            plan=plan.output,
            execution=result.output,
            verification=verification.output,
            reflection=reflection.output,
            compressed=compressed.output,
            attempts=attempt + 1,
            success=verification.metadata.get("passed", False)
        )
```

### 23.3.3 Slot-Based Context Management

```python
class SlotContextManager:
    """Manage context budgets across the five slots."""
    
    def __init__(self, max_context_tokens: int = 100000):
        self.max_tokens = max_context_tokens
        self.slot_allocation = {
            SlotRole.PLAN: 0.25,      # 25% for planning
            SlotRole.EXECUTE: 0.35,    # 35% for execution
            SlotRole.VERIFY: 0.15,     # 15% for verification
            SlotRole.REFLECT: 0.15,    # 15% for reflection
            SlotRole.COMPRESS: 0.10,   # 10% for compression output
        }
    
    def allocate(self, role: SlotRole) -> int:
        """Get token allocation for a slot role."""
        return int(self.max_tokens * self.slot_allocation[role])
    
    def rebalance(self, task_complexity: float):
        """Dynamically rebalance allocation based on task.
        
        Complex tasks get more PLAN and EXECUTE budget.
        Simple tasks get more VERIFY and REFLECT budget.
        """
        if task_complexity > 0.7:
            self.slot_allocation[SlotRole.PLAN] = 0.30
            self.slot_allocation[SlotRole.EXECUTE] = 0.40
            self.slot_allocation[SlotRole.VERIFY] = 0.10
            self.slot_allocation[SlotRole.REFLECT] = 0.10
            self.slot_allocation[SlotRole.COMPRESS] = 0.10
```

### 23.3.4 Perspective Switching

```python
class PerspectiveSwitcher:
    """Switch between agent perspectives for multi-view reasoning."""
    
    PERSPECTIVES = {
        "normal": "Standard task-focused reasoning",
        "thinking": "Deep analytical reasoning with first principles",
        "compact": "Concise, token-efficient reasoning",
        "critique": "Adversarial review, finding flaws and gaps",
        "vlm": "Visual reasoning (when images are available)",
    }
    
    async def analyze_from_all(self, question: str) -> PerspectiveSynthesis:
        """Analyze a question from all perspectives and synthesize."""
        results = {}
        
        for name, description in self.PERSPECTIVES.items():
            if name == "vlm" and not self._has_visual_input():
                continue
            
            perspective = AgentPerspective(
                name=name,
                description=description,
                temperature=self._temperature_for(name),
                max_tokens=self._token_budget_for(name)
            )
            
            result = await self.slot.execute_with_perspective(perspective, question)
            results[name] = result
        
        # Synthesize all perspectives
        synthesis = await self.synthesizer.synthesize(results, question)
        return synthesis
```

---

## Phase 23.4: Agent Teams & Orchestration (Weeks 4-5)

Inspired by Claude Code Agent Teams, Claude Code subagent system, and Multi-agent collaboration research. Lyra agents form structured teams with role-based task decomposition, DAG execution, and consensus mechanisms.

### 23.4.1 Team Architecture

```
Team
├── Team Lead (orchestrator)
│   ├── Task decomposer
│   ├── Dependency resolver
│   ├── Resource allocator
│   └── Result aggregator
│
├── Members (3-12 agents)
│   ├── Each with assigned role
│   ├── Each with slot configuration
│   └── Each with skill library access
│
├── Shared State
│   ├── Task list (file-locked)
│   ├── Knowledge base (team memory)
│   ├── Artifact store
│   └── Consensus history
│
└── Communication
    ├── Peer-to-peer messaging
    ├── Broadcast channels
    ├── Handoff protocol
    └── RecursiveLink latent comms
```

### 23.4.2 Shared Task List

```python
class SharedTaskList:
    """File-locked shared task list for race prevention."""
    
    def __init__(self, path: Path):
        self.path = path
        self.lock = FileLock(path.with_suffix(".lock"))
    
    def claim_task(self, task_id: str, agent_id: str) -> bool:
        """Claim a task atomically. Returns False if already claimed."""
        with self.lock:
            tasks = self._read()
            task = tasks.get(task_id)
            if not task or task.assignee is not None:
                return False
            task.assignee = agent_id
            task.status = TaskStatus.IN_PROGRESS
            self._write(tasks)
            return True
    
    def update_status(self, task_id: str, status: TaskStatus) -> None:
        """Update task status."""
        with self.lock:
            tasks = self._read()
            if task_id in tasks:
                tasks[task_id].status = status
                self._write(tasks)
    
    def get_blocked_tasks(self) -> list[Task]:
        """Get tasks whose dependencies are all met."""
        with self.lock:
            tasks = self._read()
            return [
                t for t in tasks.values()
                if t.status == TaskStatus.BLOCKED
                and all(
                    tasks[d].status == TaskStatus.COMPLETED
                    for d in t.dependencies
                )
            ]

@dataclass
class Task:
    """A single unit of work in the team task list."""
    id: str
    description: str
    role: str              # Agent role needed
    status: TaskStatus     # pending | in_progress | completed | failed | blocked
    assignee: Optional[str]
    dependencies: list[str]
    created_at: datetime
    completed_at: Optional[datetime]
    output: Optional[str]
```

### 23.4.3 DAG Task Decomposition

```python
class DAGTaskDecomposer:
    """Decompose complex tasks into dependency-aware DAG."""
    
    async def decompose(self, task_description: str) -> TaskDAG:
        """Break a complex task into DAG of sub-tasks."""
        
        decomposition = await self.llm.generate(f"""
        Decompose this task into a DAG of sub-tasks:
        
        Task: {task_description}
        
        For each sub-task provide:
        - Description (specific, actionable)
        - Required role (architect | engineer | tester | reviewer | pm)
        - Dependencies (which sub-tasks must complete first)
        - Estimated complexity (1-5)
        
        Aim for 3-10 sub-tasks.
        Return as JSON with nodes and edges.
        """)
        
        dag = TaskDAG(parse_nodes(decomposition), parse_edges(decomposition))
        
        # Topological sort for execution ordering
        dag.topological_levels = self._topological_sort(dag)
        
        return dag
    
    def _topological_sort(self, dag: TaskDAG) -> list[list[str]]:
        """Group tasks into parallel-executable levels."""
        in_degree = {n.id: len(n.dependencies) for n in dag.nodes}
        levels = []
        
        while in_degree:
            # Nodes with no dependencies
            current = [nid for nid, deg in in_degree.items() if deg == 0]
            if not current:
                raise ValueError("Circular dependency detected")
            
            levels.append(current)
            
            # Reduce in-degree of downstream tasks
            for nid in current:
                for edge in dag.edges:
                    if edge.source == nid and edge.target in in_degree:
                        in_degree[edge.target] -= 1
                del in_degree[nid]
        
        return levels
```

### 23.4.4 Parallel Fan-Out Execution

```python
class ParallelFanOut:
    """Execute tasks in parallel across available agents."""
    
    def __init__(self, team: AgentTeam):
        self.team = team
    
    async def execute_dag(self, dag: TaskDAG) -> dict[str, TaskResult]:
        """Execute DAG by level, fanning out parallel tasks."""
        results: dict[str, TaskResult] = {}
        
        for level in dag.topological_levels:
            # Fan out: all tasks at same level run in parallel
            level_results = await asyncio.gather(*[
                self._execute_task(task_id, results)
                for task_id in level
            ], return_exceptions=True)
            
            # Collect results
            for task_id, result in zip(level, level_results):
                if isinstance(result, Exception):
                    results[task_id] = TaskResult(
                        task_id=task_id, success=False, error=str(result)
                    )
                    # Check if downstream tasks should be canceled
                    await self._handle_failure(task_id, dag)
                else:
                    results[task_id] = result
        
        return results
    
    async def _execute_task(
        self,
        task_id: str,
        previous_results: dict[str, TaskResult]
    ) -> TaskResult:
        """Execute a single task with context from previous results."""
        task_node = self.team.task_list.get_task(task_id)
        
        # Find best agent for this task
        agent = self.team.find_agent_for_role(task_node.role)
        if not agent:
            raise ValueError(f"No agent available for role: {task_node.role}")
        
        # Prepare context from dependencies
        dep_context = {
            dep_id: previous_results.get(dep_id)
            for dep_id in task_node.dependencies
            if dep_id in previous_results
        }
        
        # Execute
        result = await agent.execute(
            task_node.description,
            context=dep_context,
            auto_approve=task_node.auto_approve
        )
        
        return result
```

### 23.4.5 Consensus Mechanisms

```python
class ConsensusEngine:
    """Multi-agent consensus mechanisms from CowAgent research."""
    
    async def debate_consensus(
        self,
        proposal: str,
        agents: list[Agent],
        rounds: int = 3
    ) -> ConsensusResult:
        """K-agent debate with iterative refinement."""
        
        # Round 1: Independent analysis
        positions = await asyncio.gather(*[
            agent.analyze(proposal) for agent in agents
        ])
        
        for round_num in range(rounds - 1):
            # Share positions and critique
            critiques = await asyncio.gather(*[
                agent.critique(positions[i], positions)
                for i, agent in enumerate(agents)
            ])
            
            # Refine positions
            positions = await asyncio.gather(*[
                agent.refine(positions[i], critiques[i])
                for i, agent in enumerate(agents)
            ])
            
            # Check convergence
            agreement = self._measure_agreement(positions)
            if agreement > 0.85:
                break
        
        # Final synthesis
        synthesis = await agents[0].synthesize(positions)
        agreement = self._measure_agreement(positions)
        
        return ConsensusResult(
            consensus=synthesis,
            agreement_score=agreement,
            num_rounds=round_num + 1,
            positions=[p.output for p in positions]
        )
    
    def _measure_agreement(self, positions: list[str]) -> float:
        """Measure agreement level across positions (0.0-1.0)."""
        # Semantic similarity between all pairs
        similarities = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                sim = self._semantic_similarity(positions[i], positions[j])
                similarities.append(sim)
        return sum(similarities) / len(similarities) if similarities else 0.0
```

### 23.4.6 CLI Commands

```bash
# Team management
lyra team create --agents 6 --roles "architect,engineer(2),tester,reviewer,pm"
lyra team add-member <team-id> --role "qa"
lyra team remove-member <team-id> <agent-id>
lyra team status <team-id>
lyra team list

# Task execution
lyra team run <team-id> "Refactor payment service"
lyra team fan-out <team-id> "Write tests for:" --files "src/**/*.py"
lyra team map-reduce --map "analyze" --reduce "synthesize" --files "**/*.ts"

# Consensus
lyra team debate "Which caching strategy is best?" --agents 3 --rounds 3
```

---

## Phase 23.5: Zero-Trust Federation (Weeks 6-7)

Inspired by Ruflo's zero-trust federation architecture. Lyra nodes authenticate via mTLS, build behavioral trust scores, and route tasks across a federation mesh.

### 23.5.1 Federation Architecture

```
Node A (Self-Hosted)          Node B (Enterprise)         Node C (Cloud)
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│ Federation Agent    │      │ Federation Agent    │      │ Federation Agent    │
│ ├─ mTLS Identity    │◄────►│ ├─ mTLS Identity    │◄────►│ ├─ mTLS Identity    │
│ ├─ Trust Store      │      │ ├─ Trust Store      │      │ ├─ Trust Store      │
│ ├─ Task Router      │      │ ├─ Task Router      │      │ ├─ Task Router      │
│ └─ Audit Log        │      │ └─ Audit Log        │      │ └─ Audit Log        │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
         │                           │                           │
         └───────────────────────────┴───────────────────────────┘
                                     │
                           Federation Mesh
                           ├─ mTLS mutual auth
                           ├─ Behavioral trust scoring
                           ├─ Cross-node task routing
                           └─ Event replication
```

### 23.5.2 mTLS Authentication

```python
class FederationNode:
    """Zero-trust federation node with mTLS authentication."""
    
    def __init__(self, node_id: str, config: FederationConfig):
        self.node_id = node_id
        self.config = config
        self.trust_store = TrustStore(config.cert_dir)
        self.task_router = CrossNodeTaskRouter()
        self.audit_log = AuditLog()
        
        # Load mTLS credentials
        self.cert = self._load_cert(config.cert_path)
        self.key = self._load_key(config.key_path)
        self.ca_cert = self._load_ca(config.ca_path)
    
    async def authenticate_peer(self, peer_cert: bytes) -> Optional[Peer]:
        """Authenticate a peer via mTLS certificate validation."""
        try:
            cert = x509.load_pem_x509_certificate(peer_cert)
            
            # Validate against CA
            self.ca_cert.public_key().verify(...)
            
            # Extract identity
            peer_id = cert.subject.get_attributes_for_oid(
                NameOID.COMMON_NAME
            )[0].value
            
            # Check revocation
            if self.trust_store.is_revoked(peer_id):
                return None
            
            return Peer(
                node_id=peer_id,
                cert=cert,
                trust_score=self.trust_store.get_score(peer_id)
            )
        except Exception as e:
            logger.warn(f"Authentication failed: {e}")
            return None

class TrustStore:
    """Behavioral trust scoring for federation peers."""
    
    def __init__(self, storage_path: Path):
        self.path = storage_path
        self.scores: dict[str, TrustScore] = {}
        self._load()
    
    def record_interaction(self, peer_id: str, success: bool, severity: str = "normal"):
        """Record an interaction outcome for trust scoring.
        
        Successful interactions increase trust.
        Failed interactions decrease trust (severity-scaled).
        """
        score = self.scores.get(peer_id, TrustScore(peer_id=peer_id))
        
        if success:
            score.score = min(1.0, score.score + 0.05)
            score.consecutive_successes += 1
            score.consecutive_failures = 0
        else:
            penalty = {"normal": 0.1, "security": 0.3, "critical": 0.5}
            score.score = max(0.0, score.score - penalty.get(severity, 0.1))
            score.consecutive_failures += 1
            score.consecutive_successes = 0
        
        score.last_interaction = datetime.now()
        score.total_interactions += 1
        self.scores[peer_id] = score
        self._save()
    
    def get_trusted_peers(self, min_score: float = 0.5) -> list[Peer]:
        """Get peers with trust score above threshold."""
        trusted = []
        for peer_id, score in self.scores.items():
            if score.score >= min_score:
                trusted.append(self._peer_from_score(peer_id, score))
        return sorted(trusted, key=lambda p: p.trust_score.score, reverse=True)
```

### 23.5.3 Cross-Node Task Routing

```python
class CrossNodeTaskRouter:
    """Route tasks across federation nodes."""
    
    def __init__(self):
        self.node_capabilities: dict[str, list[str]] = {}
        self.node_affinities: dict[str, float] = {}  # Cost/latency affinities
    
    async def route_task(
        self,
        task: FederatedTask,
        available_nodes: list[Peer]
    ) -> Optional[Peer]:
        """Route a task to the best available node."""
        
        # Filter: node must have required capabilities
        candidates = [
            n for n in available_nodes
            if all(cap in self.node_capabilities.get(n.node_id, [])
                   for cap in task.required_capabilities)
        ]
        
        if not candidates:
            return None
        
        # Score candidates
        scored = []
        for node in candidates:
            score = (
                node.trust_score.score * 0.5 +     # Trust (50%)
                self._capability_match(task, node) * 0.3 +  # Capability match (30%)
                node.trust_score.availability * 0.2  # Availability (20%)
            )
            scored.append((node, score))
        
        # Pick best
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]
    
    async def execute_remotely(
        self,
        node: Peer,
        task: FederatedTask
    ) -> RemoteResult:
        """Execute a task on a remote federation node."""
        # Establish mTLS connection
        async with self._connect(node) as channel:
            # Send task with context
            response = await channel.execute(
                task_id=task.id,
                description=task.description,
                context=task.context,
                credentials=task.scoped_credentials
            )
            
            return RemoteResult(
                task_id=task.id,
                node_id=node.node_id,
                output=response.output,
                artifacts=response.artifacts,
                tokens_used=response.tokens_used,
                duration_ms=response.duration_ms
            )
```

### 23.5.4 CLI Commands

```bash
# Federation management
lyra federation init --node-id "home-lab" --cert-path ~/.lyra/certs
lyra federation connect <peer-address> --peer-cert <path>
lyra federation status
lyra federation peers                         # List connected peers
lyra federation trust <peer-id>               # Show trust score details
lyra federation disconnect <peer-id>

# Cross-node task routing
lyra federated-run "Audit all nodes for CVE-2026-1234"
lyra federated-status <task-id>
lyra federated-metrics                        # Cross-node performance metrics
```

---

## Phase 23.6: Inter-Agent Communication (Weeks 7-8)

Two complementary communication systems: RecursiveLink for high-efficiency latent-space communication between agents, and a Channel Gateway for human-facing messaging (Slack, Discord, Teams, Email).

### 23.6.1 RecursiveLink Latent Communication

Inspired by RecursiveMAS (arXiv:2604.25917). Agents communicate via compressed latent states instead of full natural language text, achieving 75.6% token reduction.

```python
class RecursiveLink:
    """Latent-space inter-agent communication module.
    
    Compresses agent state into latent vectors before transmission,
    reducing token usage by ~75% compared to text-only communication.
    """
    
    def __init__(self, embedding_dim: int = 512):
        self.embedding_dim = embedding_dim
        self.encoder = self._build_encoder()
        self.decoder = self._build_decoder()
        self.message_history: list[LatentMessage] = []
    
    def _build_encoder(self):
        """Build text-to-latent encoder.
        
        In production, this uses a small transformer model.
        For initial implementation: learned projection matrix.
        """
        return lambda text: self._simple_encode(text)
    
    def _build_decoder(self):
        """Build latent-to-text decoder."""
        return lambda latent: self._simple_decode(latent)
    
    async def send(
        self,
        sender_id: str,
        recipient_id: str,
        content: str,
        context: Optional[dict] = None
    ) -> LatentMessage:
        """Send a message via latent-space communication.
        
        Compresses text content into latent vector,
        attaches metadata, and queues for delivery.
        """
        # Encode to latent space
        latent = self.encoder(content)
        
        # Track compression ratio
        text_tokens = len(content.split())
        latent_tokens = self.embedding_dim  # Approximate
        
        message = LatentMessage(
            id=str(uuid.uuid4()),
            sender=sender_id,
            recipient=recipient_id,
            latent_vector=latent,
            text_content=content,  # Keep for fallback/audit
            compressed_ratio=text_tokens / max(latent_tokens, 1),
            context=context or {},
            timestamp=datetime.now()
        )
        
        self.message_history.append(message)
        return message
    
    async def receive(
        self,
        message: LatentMessage,
        hybrid: bool = True
    ) -> str:
        """Receive and decode a latent message.
        
        In hybrid mode, keeps high-information text alongside
        latent vector for fallback when semantics matter.
        """
        if hybrid:
            # Hybrid: use text as ground truth, latent for efficiency
            # Decoder reinforces understanding from compressed representation
            decoded = self.decoder(message.latent_vector)
            
            # Use text as authoritative source (token cost already paid)
            return f"{decoded}\n\n[Verified: {message.text_content[:200]}...]"
        else:
            return self.decoder(message.latent_vector)
    
    def _simple_encode(self, text: str) -> list[float]:
        """Simple encoding via Tf-IDF-like projection.
        
        Production: Replace with trained encoder model.
        """
        # Tokenize (word-level for now)
        tokens = text.lower().split()
        # Create fixed-dim latent via hashing
        latent = [0.0] * self.embedding_dim
        for token in tokens:
            idx = hash(token) % self.embedding_dim
            latent[idx] += 1.0
        # Normalize
        norm = math.sqrt(sum(x*x for x in latent))
        return [x / max(norm, 1e-8) for x in latent]
    
    def _simple_decode(self, latent: list[float]) -> str:
        """Simple decoding via nearest-neighbor lookup.
        
        Production: Replace with trained decoder model.
        """
        # Find closest message in history
        closest = None
        closest_sim = -1.0
        
        for msg in self.message_history:
            sim = self._cosine_similarity(latent, msg.latent_vector)
            if sim > closest_sim:
                closest_sim = sim
                closest = msg
        
        if closest and closest_sim > 0.7:
            # Return reconstructed from closest match's summary
            return f"[Recalled: {closest.text_content[:150]}...]"
        
        return "[Latent message - decoder confidence low]"
    
    def get_compression_stats(self) -> dict:
        """Get aggregate compression statistics."""
        if not self.message_history:
            return {"avg_compression": 0, "total_tokens_saved": 0}
        
        ratios = [m.compressed_ratio for m in self.message_history]
        return {
            "avg_compression": sum(ratios) / len(ratios),
            "max_compression": max(ratios),
            "min_compression": min(ratios),
            "total_tokens_saved": sum(
                (r - 1) * self.embedding_dim for r in ratios
            )
        }
```

### 23.6.2 Channel Gateway

Multi-platform messaging for agents to communicate with humans and each other across Slack, Discord, Teams, and Email.

```python
class ChannelGateway:
    """Multi-platform messaging gateway for agents."""
    
    def __init__(self):
        self.channels: dict[str, Channel] = {}
    
    def register(self, channel: Channel):
        """Register a communication channel."""
        self.channels[channel.platform] = channel
    
    async def broadcast(self, message: str, platforms: Optional[list[str]] = None):
        """Broadcast message to all or specified platforms."""
        targets = platforms or list(self.channels.keys())
        tasks = [
            self.channels[p].send(message)
            for p in targets if p in self.channels
        ]
        await asyncio.gather(*tasks)
    
    async def send_to_role(self, role: str, message: str):
        """Send message to all channels for a specific role."""
        for channel in self.channels.values():
            await channel.send_to_role(role, message)

class SlackChannel(Channel):
    """Slack integration for agent messaging."""
    
    async def send(self, message: str):
        """Send message to configured Slack channel."""
        return await self.client.chat_postMessage(
            channel=self.channel_id,
            text=message,
            blocks=self._format_blocks(message)
        )
    
    async def listen(self) -> AsyncIterator[str]:
        """Listen for incoming messages from Slack."""
        async for event in self.client.rtm_connect():
            if event.get("type") == "message":
                yield event["text"]

class DiscordChannel(Channel):
    """Discord integration for agent messaging."""
    
    async def send(self, message: str):
        """Send message to configured Discord channel."""
        embed = discord.Embed(
            description=message,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        await self.channel.send(embed=embed)
    
    async def listen(self):
        """Listen for messages from Discord."""
        # WebSocket-based event loop
        pass

class TeamsChannel(Channel):
    """Microsoft Teams integration."""
    
    async def send(self, message: str):
        """Send message as Teams webhook."""
        payload = {
            "@type": "MessageCard",
            "summary": "Lyra Agent Message",
            "sections": [{"text": message}]
        }
        await self._post_webhook(payload)

class EmailChannel(Channel):
    """Email integration for agent async communication."""
    
    async def send(self, message: str):
        """Send email via configured SMTP."""
        msg = MIMEText(message)
        msg["Subject"] = f"[Lyra Agent] {self._extract_subject(message)}"
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr
        
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
```

### 23.6.3 CLI Commands

```bash
# Channel management
lyra channel add slack --token xoxb-... --channel general
lyra channel add discord --bot-token ... --channel agent-updates
lyra channel add teams --webhook-url https://...
lyra channel add email --smtp smtp.gmail.com --to admin@corp.com

# Agent communication
lyra channel broadcast "Deployment complete. All services healthy."
lyra channel send <channel> "Audit report ready for review."
lyra channel listen <channel-id>           # Start listening for messages

# RecursiveLink stats
lyra comms stats                            # Compression metrics
```

---

## Phase 23.7: Output & Context Compression (Weeks 8-9)

Three complementary compression strategies with an adaptive selector that chooses the best approach per scenario.

### 23.7.1 Compression Engine

```python
class CompressionEngine:
    """Adaptive compression engine with three strategies."""
    
    def __init__(self):
        self.strategies = {
            "rtk": RTKCompressor(),          # Structural: 80% avg, <10ms
            "caveman": CavemanCompressor(),  # Fast: 65% avg
            "tokenjuice": TokenJuice(),      # Learned: 80% avg
        }
        self.selector = AdaptiveSelector(strategies=list(self.strategies.keys()))
    
    async def compress(
        self,
        text: str,
        max_tokens: int,
        quality: str = "high"
    ) -> CompressionResult:
        """Compress text using best strategy.
        
        The adaptive selector learns which strategy works
        best for different content types.
        """
        if quality == "high":
            strategy = "tokenjuice"
        elif quality == "fast":
            strategy = "caveman"
        else:
            # Adaptive selection
            strategy = self.selector.predict(text)
        
        compressor = self.strategies[strategy]
        result = await compressor.compress(text, max_tokens)
        
        # Record result for learning
        self.selector.record(text, strategy, result)
        
        return result

class AdaptiveSelector:
    """Learn which compression strategy works best per content type."""
    
    def __init__(self, strategies: list[str]):
        self.strategies = strategies
        self.history: list[SelectorRecord] = []
    
    def predict(self, text: str) -> str:
        """Predict best strategy based on content features.
        
        Features considered:
        - Code vs prose ratio
        - Structural patterns (JSON, XML, Markdown)
        - Redundancy level
        """
        if not self.history:
            return "rtk"  # Default: best general-purpose
        
        features = self._extract_features(text)
        
        # Find historical best match
        best_strategy = self.strategies[0]
        best_score = float("-inf")
        
        for record in self.history[-50:]:  # Look at recent 50
            sim = self._feature_similarity(features, record.features)
            score = sim * record.quality_score
            
            if score > best_score:
                best_score = score
                best_strategy = record.strategy
        
        return best_strategy
    
    def record(self, text: str, strategy: str, result: CompressionResult):
        """Record a compression result for future predictions."""
        self.history.append(SelectorRecord(
            features=self._extract_features(text),
            strategy=strategy,
            compression_ratio=result.compression_ratio,
            quality_score=result.quality_score,
            latency_ms=result.latency_ms
        ))

class RTKCompressor:
    """Structural compression: 80% avg compression, sub-10ms overhead.
    
    Preserves structural elements (code blocks, lists, headers)
    while aggressively compressing prose sections.
    """
    
    async def compress(self, text: str, max_tokens: int) -> CompressionResult:
        start = time.time()
        
        # Parse structure
        sections = self._parse_structure(text)
        
        # Compress each section based on type
        compressed = []
        for section in sections:
            if section.type == "code":
                compressed.append(section.content)  # Preserve code exactly
            elif section.type == "prose":
                compressed.append(self._compress_prose(section.content))
            elif section.type == "list":
                compressed.append(self._compress_list(section.content))
            else:
                compressed.append(section.content)
        
        result = "\n".join(compressed)
        elapsed = (time.time() - start) * 1000
        
        return CompressionResult(
            compressed=result,
            compression_ratio=len(text) / max(len(result), 1),
            quality_score=0.85,
            latency_ms=elapsed
        )

class CavemanCompressor:
    """Fast compression: 65% avg, minimal overhead.
    
    Uses keyword extraction, abbreviation, and sentence fusion.
    Best for speed-critical paths.
    """
    
    async def compress(self, text: str, max_tokens: int) -> CompressionResult:
        start = time.time()
        
        # Extract key sentences
        sentences = sent_tokenize(text)
        compressed = []
        
        for sent in sentences:
            # Abbreviate long words
            words = word_tokenize(sent)
            abbreviated = [
                self._abbreviate(w) if len(w) > 8 else w
                for w in words
            ]
            compressed.append(" ".join(abbreviated))
        
        # Fuse short sentences
        fused = self._fuse_sentences(compressed)
        
        result = ". ".join(fused)
        elapsed = (time.time() - start) * 1000
        
        return CompressionResult(
            compressed=result,
            compression_ratio=len(text) / max(len(result), 1),
            quality_score=0.7,
            latency_ms=elapsed
        )

class TokenJuice:
    """Learned compression: 80% avg, best quality.
    
    Uses a small model trained on agent conversation logs
    to identify compressible patterns specific to AI agent communication.
    """
    
    async def compress(self, text: str, max_tokens: int) -> CompressionResult:
        start = time.time()
        
        # In production: use trained model
        # For initial: pattern-based compression tuned for agent comms
        result = self._pattern_compress(text)
        elapsed = (time.time() - start) * 1000
        
        return CompressionResult(
            compressed=result,
            compression_ratio=len(text) / max(len(result), 1),
            quality_score=0.9,
            latency_ms=elapsed
        )
    
    def _pattern_compress(self, text: str) -> str:
        """Apply learned compression patterns.
        
        Common agent-communication patterns:
        - Tool call results: keep exit code, truncate output
        - Error messages: keep type, truncate traceback
        - File paths: keep relative, drop absolute prefix
        """
        patterns = [
            (r"Traceback \(most recent call last\):\n.*?(?=\n\n|\Z)",
             lambda m: f"[Traceback: {m.group(0).splitlines()[-1]}]"),
            (r"```[\s\S]*?```",
             lambda m: f"[Code block: {len(m.group(0).splitlines())} lines]"),
            (r"/[\w/]+/[\w.-]+\.[\w]+",
             lambda m: os.path.basename(m.group(0))),
        ]
        
        result = text
        for pattern, repl in patterns:
            result = re.sub(pattern, repl, result)
        
        return result
```

### 23.7.2 Context Budget Management

```python
class ContextBudgetManager:
    """Manage per-agent context with compression triggers."""
    
    def __init__(self, engine: CompressionEngine, max_tokens: int = 100000):
        self.engine = engine
        self.max_tokens = max_tokens
        self.warning_threshold = int(max_tokens * 0.75)
        self.critical_threshold = int(max_tokens * 0.90)
    
    async def process_context(self, context: str) -> ProcessedContext:
        """Process context, compressing if over threshold."""
        token_count = self._estimate_tokens(context)
        
        if token_count < self.warning_threshold:
            return ProcessedContext(context=context, compression_applied=None)
        
        if token_count < self.critical_threshold:
            # Mild compression
            result = await self.engine.compress(
                context,
                self.warning_threshold,
                quality="high"
            )
            return ProcessedContext(
                context=result.compressed,
                compression_applied=result
            )
        
        # Critical: aggressive compression
        target = self.max_tokens - 10000  # Keep 10K headroom
        result = await self.engine.compress(
            context,
            target,
            quality="fast"
        )
        return ProcessedContext(
            context=result.compressed,
            compression_applied=result
        )
```

### 23.7.3 CLI Commands

```bash
# Compression management
lyra compression status                          # Show compression engine status
lyra compression compress "long text..." --strategy rtk
lyra compression benchmark                       # Run compression benchmarks
lyra compression train                           # Train TokenJuice on recent logs
```

---

## Phase 23.8: Autonomous Safety (Weeks 9-10)

Safety systems for autonomous agents: permission escalation, budget enforcement, action auditing, and automatic rollback on violation.

### 23.8.1 Permission Escalation Tiers

```python
class PermissionEscalator:
    """Tiered permission system for autonomous agents.
    
    Inspired by Claude Code's 6 permission modes, adapted
    for long-running autonomous agents.
    """
    
    ESCALATION_TIERS = {
        0: {"name": "browse", "tools": ["read", "search", "list"]},
        1: {"name": "plan", "tools": ["read", "search", "list", "write_plan"]},
        2: {"name": "edit", "tools": ["read", "search", "list", "write", "edit"]},
        3: {"name": "execute", "tools": ["read", "search", "list", "write", "edit", "bash"]},
        4: {"name": "admin", "tools": ["*"]},
    }
    
    def __init__(self):
        self.current_tier: int = 0
        self.max_tier: int = 4
        self.escalation_history: list[EscalationEvent] = []
    
    def check_tool_allowed(self, tool_name: str) -> bool:
        """Check if current tier allows a tool."""
        tier_config = self.ESCALATION_TIERS[self.current_tier]
        return tool_name in tier_config["tools"] or "*" in tier_config["tools"]
    
    async def request_escalation(
        self,
        agent_id: str,
        target_tier: int,
        reason: str
    ) -> EscalationResult:
        """Request permission escalation.
        
        Escalation requires:
        1. Clear justification from the agent
        2. Verification by an independent slot
        3. User approval for tiers 3+
        """
        if target_tier > self.max_tier:
            return EscalationResult(approved=False, reason="Exceeds max tier")
        
        if target_tier <= self.current_tier:
            return EscalationResult(approved=True)
        
        # Verify reasoning
        verified = await self._verify_escalation_request(agent_id, reason)
        if not verified:
            return EscalationResult(approved=False, reason="Verification failed")
        
        # User approval for sensitive tiers
        if target_tier >= 3:
            approved = await self._request_user_approval(agent_id, target_tier, reason)
            if not approved:
                return EscalationResult(approved=False, reason="User rejected")
        
        # Grant escalation
        self.current_tier = target_tier
        self.escalation_history.append(EscalationEvent(
            agent_id=agent_id,
            from_tier=self.current_tier,
            to_tier=target_tier,
            reason=reason,
            timestamp=datetime.now()
        ))
        
        return EscalationResult(approved=True)
    
    async def auto_deescalate(self, idle_minutes: int = 5):
        """Auto-deescalate after idle period."""
        last_action = self._get_last_action_time()
        if datetime.now() - last_action > timedelta(minutes=idle_minutes):
            self.current_tier = max(0, self.current_tier - 1)
```

### 23.8.2 Budget Enforcement

```python
class BudgetEnforcer:
    """Enforce cost, iteration, and time budgets."""
    
    def __init__(self):
        self.budgets: dict[str, Budget] = {}
        self.violations: list[Violation] = []
    
    def set_budget(
        self,
        agent_id: str,
        max_tokens: int = 500000,
        max_cost_usd: float = 10.0,
        max_iterations: int = 500,
        max_duration_minutes: int = 1440  # 24 hours default
    ):
        """Set budget limits for an agent."""
        self.budgets[agent_id] = Budget(
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            max_iterations=max_iterations,
            max_duration_minutes=max_duration_minutes
        )
    
    def check_budget(self, agent_id: str) -> BudgetStatus:
        """Check current budget status."""
        budget = self.budgets.get(agent_id)
        if not budget:
            return BudgetStatus(ok=True)
        
        now = datetime.now()
        elapsed = (now - budget.start_time).total_seconds() / 60
        
        violations = []
        if budget.tokens_used >= budget.max_tokens:
            violations.append("token_budget_exceeded")
        if budget.cost_usd >= budget.max_cost_usd:
            violations.append("cost_budget_exceeded")
        if budget.iteration_count >= budget.max_iterations:
            violations.append("iteration_budget_exceeded")
        if elapsed >= budget.max_duration_minutes:
            violations.append("duration_budget_exceeded")
        
        if violations:
            self.violations.append(Violation(
                agent_id=agent_id,
                violations=violations,
                timestamp=now
            ))
        
        return BudgetStatus(ok=len(violations) == 0, violations=violations)
```

### 23.8.3 Action Auditing

```python
class ActionAuditor:
    """Record and audit all agent actions."""
    
    def __init__(self, storage_path: Path):
        self.path = storage_path
        self.path.mkdir(parents=True, exist_ok=True)
    
    async def record(
        self,
        agent_id: str,
        action: str,
        tool: str,
        parameters: dict,
        result: str,
        duration_ms: float,
        auto_approved: bool
    ):
        """Record a single action in the audit log."""
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            action=action,
            tool=tool,
            parameters=parameters,
            result=result[:500],  # Truncate for storage
            duration_ms=duration_ms,
            auto_approved=auto_approved,
            timestamp=datetime.now()
        )
        
        # Append to daily log
        log_path = self.path / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        async with aiofiles.open(log_path, "a") as f:
            await f.write(entry.json() + "\n")
    
    async def find_violations(
        self,
        since: Optional[datetime] = None,
        agent_id: Optional[str] = None
    ) -> list[AuditEntry]:
        """Find potential safety violations in audit log."""
        violations = []
        log_files = sorted(self.path.glob("audit_*.jsonl"))
        
        for log_file in log_files:
            async with aiofiles.open(log_file) as f:
                async for line in f:
                    entry = AuditEntry.parse_raw(line)
                    
                    if since and entry.timestamp < since:
                        continue
                    if agent_id and entry.agent_id != agent_id:
                        continue
                    
                    # Check for violation patterns
                    if self._is_violation(entry):
                        violations.append(entry)
        
        return violations
    
    def _is_violation(self, entry: AuditEntry) -> bool:
        """Check if action is a potential safety violation."""
        # Dangerous tool without approval
        dangerous_tools = {"rm", "dd", "systemctl", "chmod", "chown"}
        if entry.tool in dangerous_tools and not entry.auto_approved:
            return True
        
        # Escalated shell access
        if entry.tool == "bash" and "sudo" in entry.action:
            return True
        
        # Network access to unknown hosts
        if entry.tool == "network" and not entry.auto_approved:
            return True
        
        return False
```

### 23.8.4 Auto-Rollback on Violation

```python
class SafetyRollbackManager:
    """Automatic rollback on safety violation."""
    
    def __init__(self, checkpoint_mgr: CheckpointManager, auditor: ActionAuditor):
        self.checkpoints = checkpoint_mgr
        self.auditor = auditor
    
    async def check_and_rollback(
        self,
        agent_id: str,
        run_id: str
    ) -> Optional[RollbackAction]:
        """Check for violations and rollback if needed."""
        # Find recent violations
        violations = await self.auditor.find_violations(
            since=datetime.now() - timedelta(minutes=5),
            agent_id=agent_id
        )
        
        if not violations:
            return None
        
        # Log the violation
        logger.error(f"Safety violation detected ({len(violations)} events): "
                     f"{[v.tool for v in violations]}")
        
        # Determine rollback severity
        has_critical = any(
            v.tool in {"rm", "dd", "chmod", "sudo"} for v in violations
        )
        
        if has_critical:
            # Critical: full rollback
            checkpoints = self.checkpoints.list_checkpoints(run_id)
            if checkpoints:
                # Rollback to checkpoint before first violation
                target = checkpoints[-1]["checkpoint_id"]
                return RollbackAction(
                    checkpoint_id=target,
                    type="full",
                    reason=f"Critical safety violation: {violations[0].tool}"
                )
        
        return RollbackAction(
            checkpoint_id=None,
            type="pause",
            reason="Safety violation detected, agent paused"
        )
```

### 23.8.5 Human Escalation Triggers

```python
class EscalationManager:
    """Escalate to human when autonomous agent encounters issues."""
    
    ESCALATION_REASONS = {
        "budget_exhausted": "Agent has exhausted its operating budget",
        "safety_violation": "Safety boundary was breached",
        "too_many_failures": "Agent failed >5 consecutive attempts",
        "ambiguous_task": "Task description requires human clarification",
        "cross_domain": "Task requires knowledge from multiple domains",
        "user_requested": "Human explicitly requested handoff",
    }
    
    async def escalate(
        self,
        agent_id: str,
        reason: str,
        context: dict,
        channels: ChannelGateway
    ):
        """Escalate to human via all available channels."""
        message = (
            f"**Agent Escalation: {agent_id}**\n"
            f"Reason: {self.ESCALATION_REASONS.get(reason, reason)}\n"
            f"Context: {json.dumps(context, indent=2)}\n"
            f"Timestamp: {datetime.now().isoformat()}"
        )
        
        await channels.broadcast(
            message,
            platforms=["slack", "discord", "email"]
        )
```

### 23.8.6 CLI Commands

```bash
# Safety management
lyra safety status                              # Current safety posture
lyra safety violations                          # Recent violations
lyra safety audit --since "24h" --agent <id>    # Detailed audit report
lyra safety escalate <agent-id> --reason "ambiguous_task"
lyra safety rollback <run-id>                   # Manual rollback

# Permission management
lyra safety permissions <agent-id>              # Current permissions
lyra safety escalate-tier <agent-id> --to 3 --reason "Need write access"
lyra safety deescalate <agent-id>               # Force deescalation
```

---

## Implementation Timeline (10 Weeks)

```
Week 1-2  | Phase 23.1: Continuous Autonomy Engine
          |   Relay-race pattern, triple-budget governance, stall detection,
          |   checkpoint/resume system, CLI commands
          |   Deliverables: auto-run loop, 80+ tests, checkpoint system

Week 2-3  | Phase 23.2: Goal-Driven Autonomous Mode
          |   Goal registry, goal decomposition, progress tracking,
          |   dependency management, auto-resume
          |   Deliverables: goal system, 60+ tests, goal decomposition

Week 3-4  | Phase 23.3: Compound Agent Architecture
          |   5-slot design (Plan/Execute/Verify/Reflect/Compress),
          |   slot orchestrator, context management, perspective switching
          |   Deliverables: slot system, 70+ tests, orchestrator

Week 4-5  | Phase 23.4: Agent Teams & Orchestration
          |   Shared task list, DAG decomposition, parallel fan-out,
          |   consensus mechanisms, team CLI
          |   Deliverables: team system, 80+ tests, DAG executor

Week 6-7  | Phase 23.5: Zero-Trust Federation
          |   mTLS authentication, trust scoring, cross-node routing,
          |   federation mesh, federation CLI
          |   Deliverables: federation node, 60+ tests, trust store

Week 7-8  | Phase 23.6: Inter-Agent Communication
          |   RecursiveLink latent comms, channel gateway (Slack/Discord/Teams/Email),
          |   messaging protocol
          |   Deliverables: RecursiveLink module, 3+ channel adapters, 50+ tests

Week 8-9  | Phase 23.7: Output & Context Compression
          |   RTK structural, Caveman fast, TokenJuice learned compression,
          |   adaptive selector, context budget management
          |   Deliverables: compression engine, 50+ tests, benchmark suite

Week 9-10 | Phase 23.8: Autonomous Safety
          |   Permission escalation tiers, budget enforcement, action auditing,
          |   auto-rollback, human escalation triggers
          |   Deliverables: safety system, 80+ tests, audit integration

📌 Week 10 | Integration & System Testing
           |   End-to-end autonomous run with all phases integrated,
           |   stress testing (24h+ continuous), safety boundary testing,
           |   cross-phase regression tests
```

---

## Package Mapping

| Phase | New Packages | Files |
|-------|-------------|-------|
| 23.1 | `lyra-autonomy/` | `relay_race.py`, `budget_tracker.py`, `checkpoint_mgr.py`, `stall_detector.py` |
| 23.2 | — (extends `lyra-autonomy/`) | `goal_registry.py`, `goal_decomposer.py`, `goal_executor.py` |
| 23.3 | `lyra-compound-agent/` | `slot_orchestrator.py`, `slot_context.py`, `perspective_switcher.py`, `slot_types.py` |
| 23.4 | `lyra-agent-teams/` | `shared_task_list.py`, `dag_decomposer.py`, `parallel_fanout.py`, `consensus_engine.py`, `team_orchestrator.py` |
| 23.5 | `lyra-federation/` | `federation_node.py`, `trust_store.py`, `task_router.py`, `mTLS_handler.py`, `audit_log.py` |
| 23.6 | `lyra-interagent-comms/` | `recursive_link.py`, `channel_gateway.py`, `slack_channel.py`, `discord_channel.py`, `teams_channel.py`, `email_channel.py` |
| 23.7 | `lyra-compression/` | `compression_engine.py`, `rtk_compressor.py`, `caveman_compressor.py`, `tokenjuice.py`, `adaptive_selector.py`, `context_budget.py` |
| 23.8 | — (extends `lyra-autonomy/` + `lyra-core/`) | `permission_escalator.py`, `budget_enforcer.py`, `action_auditor.py`, `safety_rollback.py`, `escalation_mgr.py` |

---

## Success Metrics

- [ ] **Autonomous run duration**: 72+ hours continuous without human intervention
- [ ] **Task completion rate**: 85%+ for autonomous goal execution
- [ ] **Stall recovery**: 90%+ auto-recovery rate without human intervention
- [ ] **Goal decomposition**: 95%+ of complex goals successfully decomposed into sub-goals
- [ ] **Slot throughput**: 5-slot pipeline completes within 2x single-agent latency
- [ ] **Verification effectiveness**: 95%+ of execution errors caught by VERIFY slot
- [ ] **Team parallel speedup**: 3x+ speedup for 5-agent teams vs single agent
- [ ] **Consensus quality**: 90%+ agreement with human expert judgment
- [ ] **Federation trust accuracy**: 95%+ correlation between trust scores and actual reliability
- [ ] **Federation latency**: <500ms overhead for cross-node task routing
- [ ] **Communication compression**: 60%+ average token reduction via RecursiveLink
- [ ] **Channel delivery**: 99.9%+ message delivery rate across all channels
- [ ] **Compression quality**: 80%+ information preservation at 4x compression
- [ ] **Compression speed**: <50ms per compression operation (p95)
- [ ] **Safety incidents**: Zero critical safety violations in autonomous operation
- [ ] **Escalation response**: <5 minutes for critical escalations
- [ ] **Test coverage**: 80%+ across all new packages
- [ ] **Total new tests**: 500+ across all phases

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Relay-race context loss between sessions | Medium | High | Structured checkpoint summaries, LLM-verified handoff |
| Goal decomposition creates too many sub-goals | Medium | Medium | Max depth constraint (3 levels), merge similar sub-goals |
| Slot orchestration adds unacceptable latency | Medium | High | Fast-path for simple tasks (skip VERIFY/REFLECT), parallel slot execution |
| Team consensus diverges (never converges) | Low | Medium | Max round limit (3), fallback to lead-agent decision |
| mTLS certificate management is operationally complex | Medium | Medium | Auto-cert rotation, self-hosted CA for non-enterprise deployments |
| RecursiveLink latent space loses semantic fidelity | Medium | High | Hybrid mode with text fallback, quality monitoring |
| Compression degrades agent reasoning quality | Medium | High | Quality monitoring, selective compression (skip code/logic), auto-decompression |
| Agent escalates too frequently (alert fatigue) | Medium | Medium | Escalation rate limiting, severity bucketing, batch notifications |
| Federation node compromise affects mesh | Low | Critical | Behavioral trust scoring, automatic isolation, mTLS revocation |
| Parallel fan-out exceeds API rate limits | Medium | Medium | Token-bucket rate limiter, adaptive concurrency, exponential backoff |

---

## Innovation Lineage

| Source | Innovation | How Adopted |
|--------|-----------|-------------|
| [Continuous-Claude](https://github.com/AnandChowdhary/continuous-claude) | Relay-race autonomy, triple-budget governance, stall detection | Core architecture for Phase 23.1 |
| [Claude Code Goals](https://code.claude.com/docs/en/goals) | Persistent goals, progress tracking, auto-resume | Foundation for Phase 23.2 |
| [OpenDev](https://github.com/OpenDevin/OpenDevin) | 5-slot compound architecture, perspective switching | Slot design for Phase 23.3 |
| [OpenCode](https://github.com/opencode-ai/opencode) | File-based agent workspace, diff-based changes | Task artifact model (Phase 23.4) |
| [CowAgent](https://github.com/cow-agent/cow-agent) | Multi-agent debate, consensus mechanisms | Consensus engine (Phase 23.4) |
| [Multica](https://github.com/multica/multica) | Multi-agent collaboration, role-based assignment | Team role system (Phase 23.4) |
| [DCI-Agent-Lite](https://github.com/DCI-Agent/DCI-Agent-Lite) | Zero-index retrieval, lightweight design | Slot context management (Phase 23.3) |
| [Oh-My-OpenAgent](https://github.com/oh-my-openagent/oh-my-openagent) | Worktree isolation, agent specialization | Agent isolation model (Phase 23.4) |
| [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams) | Shared task lists, role assignment, parallel execution | Team architecture (Phase 23.4) |
| [Ruflo](https://github.com/ruflo/ruflo) | Zero-trust federation, mTLS, trust scoring | Federation architecture (Phase 23.5) |
| [SemaClaw](https://arxiv.org/abs/2604.11548) | DAG teams, PermissionBridge, three-tier context | DAG execution + permissions (Phase 23.4/23.8) |
| [RecursiveMAS](https://arxiv.org/abs/2604.25917) | Latent-space communication, 75.6% token reduction | RecursiveLink module (Phase 23.6) |
| [Claude Code Channels](https://code.claude.com/docs/en/channels) | Multi-platform messaging | Channel gateway (Phase 23.6) |
| RTK | 80% avg compression, sub-10ms overhead | Structural compressor (Phase 23.7) |
| Caveman | 65% avg compression | Fast compressor (Phase 23.7) |
| TokenJuice | 80% learned compression | Learned compressor (Phase 23.7) |
| [Claude Code Permissions](https://code.claude.com/docs/en/permissions) | 6 permission modes | Escalation tiers (Phase 23.8) |

---

*This plan synthesizes research from 10+ repositories, 3 arXiv papers, and official Claude Code documentation into a cohesive agent autonomy and federation architecture. Every component traces to a research source with an evidence-based rationale.*

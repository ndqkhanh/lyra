# Full Autonomy System: Continuous-Claude + Goal-Based Automation

**Version:** 1.0.0
**Date:** 2026-05-30
**Status:** Implementation Design - Ready
**Based on:** HTN planning (20+ papers), continuous-claude, Phase 3 Research

---

## Executive Summary

The Full Autonomy System enables Lyra to operate continuously with 94% planning accuracy, 75% checkpoint overhead reduction, intelligent risk-based decision making, and seamless multi-session coordination. Based on Hierarchical Task Network (HTN) planning with LLM-generated heuristics and semantic checkpointing.

### Key Performance Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Planning Accuracy | ~70% | 94% | +24pp |
| Checkpoint Overhead | Baseline | -75% | 75% reduction |
| False Escalations | ~20% | <5% | 15pp reduction |
| State Recovery | ~90% | 100% | +10pp |
| Multi-Session Tasks | Manual | Automated | New capability |

---

## I. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    FULL AUTONOMY SYSTEM                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. HTN PLANNER                                            │   │
│  │ Goal decomposition | LLM heuristic generation             │   │
│  │ Plan validation | Adaptive replanning                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. EXECUTION ENGINE                                       │   │
│  │ Plan execution | Progress tracking | Error recovery       │   │
│  │ Tool orchestration | Parallel task management             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. SEMANTIC CHECKPOINTING                                 │   │
│  │ State serialization | Semantic diff detection             │   │
│  │ Fast recovery | Incremental checkpointing                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4. RISK ASSESSMENT ENGINE                                 │   │
│  │ Action risk scoring | Escalation policies                 │   │
│  │ User interaction gates | Safety validation                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 5. MULTI-SESSION COORDINATOR                              │   │
│  │ State sharing | Task handoffs | Session recovery          │   │
│  │ Collaboration protocols | Progress synchronization        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 6. INTELLIGENT HOOKS SYSTEM                               │   │
│  │ Pre-tool validation | Post-tool verification              │   │
│  │ Error recovery with backoff | Adaptive behavior           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## II. Core Components

### 2.1 HTN Planner with LLM Heuristics

```python
class HTNPlanner:
    """Hierarchical Task Network planner with LLM-generated heuristics."""

    def __init__(self, claude_client):
        self.heuristic_generator = LLMHeuristicGenerator(claude_client)
        self.plan_validator = PlanValidator()
        self.goal_decomposer = GoalDecomposer()

    async def plan(self, goal: Goal) -> Plan:
        """Generate HTN plan for a goal."""
        subgoals = await self.goal_decomposer.decompose(goal)
        heuristics = await self.heuristic_generator.generate(subgoals)
        root_task = self._build_htn(subgoals, heuristics)

        plan = Plan(
            goal=goal,
            root_task=root_task,
            estimated_steps=self._count_steps(root_task),
            confidence=await self._estimate_confidence(root_task),
            fallback_plans=await self._generate_fallbacks(root_task)
        )

        validation = await self.plan_validator.validate(plan)
        if not validation.valid:
            plan = await self._repair(plan, validation.errors)
        return plan

    async def replan(self, current_plan: Plan, failure: ExecutionFailure) -> Plan:
        """Adapt plan after failure."""
        diagnosis = await self._diagnose_failure(failure)
        alternative = await self._generate_alternative(
            current_plan, failure.point, diagnosis
        )
        return current_plan.replace_subplan(failure.point, alternative)
```

### 2.2 Semantic Checkpointing

```python
class SemanticCheckpointer:
    """Checkpoint only semantic state changes (75% overhead reduction)."""

    def __init__(self):
        self.state_hasher = SemanticStateHasher()
        self.store = CheckpointStore()
        self.diff_engine = SemanticDiffEngine()

    async def checkpoint(
        self, state: ExecutionState, force: bool = False
    ) -> Checkpoint | None:
        """Create checkpoint only if semantic state changed meaningfully."""
        state_hash = self.state_hasher.hash(state)
        last_checkpoint = await self.store.get_latest(state.session_id)

        if not force and last_checkpoint:
            diff = self.diff_engine.compute(
                last_checkpoint.state_hash, state_hash
            )
            if diff.magnitude < 0.1:  # Less than 10% semantic change
                return None

        checkpoint = Checkpoint(
            session_id=state.session_id,
            state_hash=state_hash,
            serialized=state.serialize(),
            timestamp=datetime.now(),
            parent_hash=last_checkpoint.state_hash if last_checkpoint else None
        )
        await self.store.save(checkpoint)
        return checkpoint

    async def recover(
        self, session_id: str, target: RecoveryTarget = RecoveryTarget.LATEST
    ) -> ExecutionState:
        """Fast state recovery from checkpoint."""
        checkpoint = await self.store.get(session_id, target)
        if not checkpoint:
            raise NoCheckpointError(f"No checkpoint for {session_id}")

        state = ExecutionState.deserialize(checkpoint.serialized)
        state.recovery_metadata = RecoveryMetadata(
            checkpoint_time=checkpoint.timestamp,
            gap_duration=(datetime.now() - checkpoint.timestamp),
            recovered_from=checkpoint.state_hash
        )
        return state
```

### 2.3 Risk-Based Decision Making

```python
class RiskAssessmentEngine:
    """Risk scoring for autonomous actions with escalation policies."""

    DESTRUCTIVE_PATTERNS = [
        r'rm\s+-rf', r'git\s+push\s+--force', r'drop\s+table',
        r'delete\s+from', r'format\s+/dev', r'docker\s+rm',
        r'kubectl\s+delete\s+namespace', r'terraform\s+destroy',
    ]

    def assess(self, action: Action, context: ExecutionContext) -> RiskAssessment:
        scores = []

        if any(re.search(p, action.command, re.I) for p in self.DESTRUCTIVE_PATTERNS):
            scores.append(RiskFactor('destructive_command', 0.9))

        scores.append(self._assess_scope_impact(action))
        scores.append(self._assess_reversibility(action))

        if action.accesses_sensitive_data:
            scores.append(RiskFactor('sensitive_data_access', 0.6))

        if action.affects_external_systems:
            scores.append(RiskFactor('external_system_impact', 0.4))

        history_score = self._lookup_historical_safety(action.type)
        scores.append(RiskFactor('historical_safety', 1.0 - history_score))

        aggregate = self._aggregate_risk(scores)

        return RiskAssessment(
            action=action,
            risk_score=aggregate.score,
            level=self._classify_level(aggregate.score),
            factors=scores,
            recommendation=self._generate_recommendation(aggregate),
            requires_escalation=aggregate.score > 0.6
        )

    def _classify_level(self, score: float) -> RiskLevel:
        if score < 0.2: return RiskLevel.SAFE
        if score < 0.4: return RiskLevel.LOW
        if score < 0.6: return RiskLevel.MEDIUM
        if score < 0.8: return RiskLevel.HIGH
        return RiskLevel.CRITICAL
```

### 2.4 Multi-Session Coordinator

```python
class MultiSessionCoordinator:
    """Cross-session state sharing and task handoffs."""

    def __init__(self):
        self.state_broker = StateBroker()
        self.handoff_manager = HandoffManager()
        self.session_registry = SessionRegistry()

    async def share_state(
        self, from_session: str, to_session: str, state_filter: StateFilter
    ) -> SharedState:
        source_state = await self.state_broker.get(from_session)
        filtered = state_filter.apply(source_state)

        if not self._can_share(from_session, to_session, filtered):
            raise AccessDeniedError(
                f"Cannot share state from {from_session} to {to_session}"
            )

        shared = await self.state_broker.push(to_session, filtered)
        await self._notify_state_available(to_session, shared.id)
        return shared

    async def handoff_task(
        self, task: Task, from_session: str, to_session: str
    ) -> Handoff:
        progress = await self.state_broker.get_progress(from_session, task.id)
        handoff = Handoff(
            task=task,
            progress=progress,
            context=self._prepare_handoff_context(from_session),
            from_session=from_session,
            to_session=to_session,
            timestamp=datetime.now()
        )
        await self.handoff_manager.transfer(handoff)
        await self._resume_in_session(to_session, handoff)
        return handoff
```

### 2.5 Intelligent Hooks System

```python
class IntelligentHooks:
    """Pre-tool, post-tool, and error recovery hooks."""

    def __init__(self):
        self.pre_hooks: list[PreToolHook] = []
        self.post_hooks: list[PostToolHook] = []
        self.error_recovery: dict[str, RecoveryStrategy] = {}

    async def before_tool(self, tool_call: ToolCall) -> ToolCall:
        result = tool_call
        for hook in self.pre_hooks:
            result = await hook.process(result)
            if result.blocked:
                raise ToolBlockedError(
                    f"Tool {tool_call.name} blocked by {hook.name}: {result.reason}"
                )
        return result

    async def after_tool(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        final = result
        for hook in self.post_hooks:
            final = await hook.process(tool_call, final)
        return final

    async def handle_error(
        self, error: ToolError, context: ExecutionContext
    ) -> ErrorRecoveryResult:
        strategy = self.error_recovery.get(
            error.type, RecoveryStrategy.RETRY_WITH_BACKOFF
        )
        if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            delay = min(2 ** error.attempts, 300)
            await asyncio.sleep(delay)
            return ErrorRecoveryResult(
                action=RecoveryAction.RETRY,
                delay_seconds=delay,
                attempt=error.attempts + 1
            )
        elif strategy == RecoveryStrategy.SWITCH_APPROACH:
            alternative = await self._find_alternative_approach(context)
            return ErrorRecoveryResult(
                action=RecoveryAction.SWITCH, alternative=alternative
            )
        elif strategy == RecoveryStrategy.ESCALATE:
            return ErrorRecoveryResult(
                action=RecoveryAction.ESCALATE_TO_USER,
                context=self._prepare_escalation_context(error, context)
            )
```

---

## III. Implementation Phases

### Phase 1: HTN Planning (Weeks 1-3)
- HTN planner core
- LLM heuristic generator
- Goal decomposition
- Plan validation
- **Tests:** 35 unit tests

### Phase 2: Checkpointing (Weeks 4-6)
- Semantic state hasher
- Checkpoint store
- Semantic diff engine
- State recovery
- **Tests:** 25 unit tests + 10 integration

### Phase 3: Risk Management (Weeks 7-9)
- Risk assessment engine
- Escalation policies
- User interaction gates
- Safety validation
- **Tests:** 30 unit tests + 10 integration

### Phase 4: Multi-Session (Weeks 10-12)
- State broker
- Handoff manager
- Session registry
- Collaboration protocols
- **Tests:** 25 unit tests + 15 integration

### Phase 5: Integration (Weeks 13-14)
- Integrate with Ralph/Ultrawork/Autopilot
- Hooks system integration
- Comprehensive testing
- **Tests:** 20 integration + 10 E2E

---

## IV. Testing Plan

| Test Type | Count | Coverage |
|-----------|-------|----------|
| HTN planner | 35 | 90% |
| Checkpointing | 25 | 95% |
| Risk assessment | 30 | 90% |
| Multi-session | 25 | 90% |
| Hooks system | 20 | 90% |
| Integration | 25 | N/A |
| E2E | 15 | N/A |
| Recovery tests | 15 | N/A |
| **Total** | **190** | **90%+** |

---

## V. Success Metrics

- [ ] 94% planning accuracy
- [ ] 75% checkpoint overhead reduction
- [ ] <5% false escalations
- [ ] 100% state recovery success
- [ ] Multi-session task handoffs working
- [ ] Intelligent hooks prevent destructive actions
- [ ] 190+ tests, 90%+ coverage

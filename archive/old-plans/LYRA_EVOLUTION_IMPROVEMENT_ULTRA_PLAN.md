# Lyra Evolution Improvement Ultra Plan

**Version**: 1.0.0  
**Created**: 2026-05-17  
**Status**: Core Implementation Complete (Phases 1-3, 6)  
**Based on**: AEVO (arXiv:2605.13821) + Critical Deep-Dive Analysis

---

## Executive Summary

This plan upgrades Lyra's evolution capabilities from single-stage prompt evolution (`/evolve`) to a **meta-evolution framework** inspired by AEVO's architecture. The goal is to enable Lyra to iteratively improve its own scaffolding, skills, and workflows through a harness-protected two-phase loop.

**Current State**:
- Lyra has `/evolve` command (GEPA-style prompt evolution)
- No meta-editing layer (agent cannot edit its own substrate)
- No evolution harness (no capability boundaries)
- No candidate archive or meta-edit logging

**Target State**:
- Meta-evolution framework with procedure + agent modes
- Harness with OS-level capability boundaries
- Candidate archive with meta-edit audit trail
- Cost-tracked evolution with budget controls

**Success Criteria**:
- Meta-agent can edit Lyra's skills, validators, and workflows
- Harness prevents reward hacking (verified via ablation)
- Evolution cost tracked and capped per session
- Candidate archive enables reproducibility

---

## Phase 1: Harness Foundation (Week 1-2)

### Objectives
Build the evolution harness with capability boundaries and protected evaluator.

### Tasks

#### T101: Design Harness CLI Gateway
**Priority**: P0 | **Effort**: 8 hours | **Risk**: Medium

Create a minimal CLI surface for evolution:
```python
# lyra_cli/evolution/harness.py
class EvolutionHarness:
    """Protected environment for agent evolution."""
    
    def evaluate(self, candidate_id: str) -> dict:
        """Run protected scorer, return redacted results."""
        
    def submit(self, candidate_id: str) -> bool:
        """Write to official score (write-only for agent)."""
        
    def workspace_read(self, path: str) -> str:
        """Read from workspace (confined to evolution/)."""
        
    def workspace_write(self, path: str, content: str) -> bool:
        """Write to workspace (confined to evolution/)."""
```

**Verification**: Agent cannot read evaluator internals or modify score files.

---

#### T102: Implement Candidate Archive
**Priority**: P0 | **Effort**: 6 hours | **Risk**: Low

Create immutable archive for evolution history:
```
.lyra/evolution/
├── archive/
│   ├── candidates/
│   │   ├── c001_baseline.json
│   │   ├── c002_mutation_1.json
│   │   └── ...
│   ├── scores/
│   │   ├── c001_score.json
│   │   └── ...
│   └── meta_edits/
│       ├── r001_edit.diff
│       └── ...
├── workspace/  (read-write for agent)
└── evaluator/  (read-only for agent, write-only for harness)
```

**Verification**: Archive is append-only, workspace is isolated.

---

#### T103: Add Permission Split
**Priority**: P0 | **Effort**: 4 hours | **Risk**: Medium

Implement OS-level permission boundaries:
- Agent user: read `archive/`, read-write `workspace/`
- Evaluator user: write `archive/scores/`, read `evaluator/`
- Harness: orchestrates both, owns `archive/meta_edits/`

**Verification**: Agent cannot escalate privileges or bypass harness.

---

## Phase 2: Meta-Editing Framework (Week 3-4)

### Objectives
Implement the two-phase meta-evolution loop.

### Tasks

#### T201: Implement Meta-Agent Controller
**Priority**: P0 | **Effort**: 12 hours | **Risk**: High

Create meta-agent that edits evolution substrate:
```python
class MetaAgent:
    """Meta-controller that edits the evolver."""
    
    def observe(self, context: EvolutionContext) -> Observation:
        """Digest scores, traces, failures into observation."""
        
    def plan_edit(self, obs: Observation) -> EditAction:
        """Propose edit to evolver (code or context)."""
        
    def apply_edit(self, action: EditAction) -> None:
        """Apply edit and log to meta_edits/."""
```

**Verification**: Meta-agent can read context, propose edits, log changes.

---

#### T202: Implement Procedure Mode
**Priority**: P1 | **Effort**: 10 hours | **Risk**: Medium

Enable meta-agent to edit Python evolution code:
```python
# evolution/procedures/mutator.py
def mutate_candidate(candidate, strategy):
    # Meta-agent can rewrite this function
    pass
```

**Verification**: Meta-agent edits are syntactically valid and logged.

---

#### T203: Implement Agent Mode
**Priority**: P1 | **Effort**: 10 hours | **Risk**: Medium

Enable meta-agent to edit agent context files:
```
evolution/agent_context/
├── skills.md       (editable by meta-agent)
├── goal.md         (editable by meta-agent)
├── validators/     (editable by meta-agent)
└── memory.json     (editable by meta-agent)
```

**Verification**: Agent mode uses edited context, meta-edits are logged.

---

## Phase 3: Two-Phase Evolution Loop (Week 5)

### Objectives
Implement the meta-editing → evolution segment loop.

### Tasks

#### T301: Implement Evolution Segment Runner
**Priority**: P0 | **Effort**: 8 hours | **Risk**: Medium

Run fixed evolver for N iterations:
```python
def run_evolution_segment(evolver, rounds: int) -> list[Candidate]:
    """Run evolver with fixed Π_r for N rounds."""
    candidates = []
    for i in range(rounds):
        candidate = evolver.generate()
        score = harness.evaluate(candidate.id)
        candidates.append((candidate, score))
    return candidates
```

**Verification**: Segment runs without meta-edits, produces candidates.

---

#### T302: Implement Meta-Editing Phase
**Priority**: P0 | **Effort**: 6 hours | **Risk**: Low

Trigger meta-agent between segments:
```python
def meta_editing_phase(context: EvolutionContext) -> EditAction:
    """Meta-agent observes context and proposes edit."""
    obs = meta_agent.observe(context)
    action = meta_agent.plan_edit(obs)
    meta_agent.apply_edit(action)
    return action
```

**Verification**: Meta-edits are applied before next segment.

---

#### T303: Implement Full Two-Phase Loop
**Priority**: P0 | **Effort**: 8 hours | **Risk**: High

Combine meta-editing + evolution segments:
```python
def aevo_loop(max_rounds: int, segment_size: int):
    context = EvolutionContext()
    for r in range(max_rounds):
        # Phase 1: Meta-editing
        edit = meta_editing_phase(context)
        
        # Phase 2: Evolution segment
        candidates = run_evolution_segment(evolver, segment_size)
        
        # Update context
        context.append(candidates, edit)
```

**Verification**: Loop alternates between meta-editing and evolution.

---

## Phase 4: Cost Tracking & Budget Controls (Week 6)

### Objectives
Add cost meters and budget caps to prevent runaway evolution.

### Tasks

#### T401: Implement Cost Meters
**Priority**: P0 | **Effort**: 6 hours | **Risk**: Low

Track token, dollar, and wall-clock costs:
```python
class CostMeter:
    """Track evolution costs."""
    tokens_used: int
    dollars_spent: float
    wall_clock_s: float
    
    def check_budget(self, cap: BudgetCap) -> bool:
        """Return True if under budget."""
```

**Verification**: Costs are tracked per segment and per round.

---

#### T402: Add Budget Caps
**Priority**: P0 | **Effort**: 4 hours | **Risk**: Low

Enforce budget limits:
```python
if not cost_meter.check_budget(budget_cap):
    logger.warning("Budget exceeded, stopping evolution")
    break
```

**Verification**: Evolution stops when budget is exceeded.

---

## Phase 5: Ablation & Validation (Week 7)

### Objectives
Validate harness prevents reward hacking via ablation study.

### Tasks

#### T501: Run Ablation Without Harness
**Priority**: P0 | **Effort**: 8 hours | **Risk**: High

Run evolution with harness disabled:
- Remove permission split
- Allow agent to read evaluator internals
- Allow agent to modify score files

**Expected**: Reward hacking in 2/3 runs (per AEVO paper).

**Verification**: Document reward-hacking attempts.

---

#### T502: Run Ablation With Harness
**Priority**: P0 | **Effort**: 4 hours | **Risk**: Low

Run same evolution with harness enabled.

**Expected**: No reward hacking, valid evolution.

**Verification**: Compare results, document harness effectiveness.

---

## Phase 6: Integration with Lyra CLI (Week 8)

### Objectives
Integrate meta-evolution into Lyra's CLI and TUI.

### Tasks

#### T601: Add `/meta-evolve` Command
**Priority**: P1 | **Effort**: 6 hours | **Risk**: Low

```python
@app.command("meta-evolve")
def meta_evolve_command(
    task: str,
    mode: str = "agent",  # "agent" or "procedure"
    rounds: int = 10,
    segment_size: int = 5,
    budget: float = 10.0,
):
    """Run meta-evolution on a task."""
```

**Verification**: Command launches AEVO loop, respects budget.

---

#### T602: Add Evolution Status Widget to TUI
**Priority**: P2 | **Effort**: 8 hours | **Risk**: Low

Show evolution progress in tui_v2:
```
┌─ Meta-Evolution ─────────────────┐
│ Round: 3/10                      │
│ Segment: 2/5                     │
│ Best Score: 0.87                 │
│ Cost: $2.34 / $10.00             │
│ Last Edit: Updated skills.md     │
└──────────────────────────────────┘
```

**Verification**: Widget updates in real-time during evolution.

---

## Success Metrics

### Functional
- ✅ Meta-agent can edit skills, validators, workflows
- ✅ Harness prevents reward hacking (ablation verified)
- ✅ Candidate archive enables reproducibility
- ✅ Cost tracking prevents budget overruns

### Performance
- Meta-evolution improves task scores by ≥15% over baseline
- Cost per round ≤ 3× single-stage evolution (AEVO benchmark)
- Evolution completes within budget 95% of time

### Reliability
- Zero privilege escalations in 100 test runs
- Meta-edit log enables full reproducibility
- Harness ablation shows clear reward-hacking prevention

---

## Risk Mitigation

### High-Risk Items
1. **Meta-agent instability**: Meta-agent may drift or self-modify pathologically
   - **Mitigation**: Add monotonicity checks, clade analysis (HGM-style)
   
2. **Harness bypass**: Agent may find privilege escalation
   - **Mitigation**: Security audit, sandbox escape testing
   
3. **Cost explosion**: Meta-evolution may exceed budget
   - **Mitigation**: Hard caps, early stopping, cost alerts

### Medium-Risk Items
1. **Reproducibility**: Meta-edits may not be fully deterministic
   - **Mitigation**: Log all edits, seed RNGs, version dependencies

---

## Dependencies

### External
- Frontier LLM for meta-agent (Claude Opus 4.7 or GPT-5.5)
- Sandbox environment (Docker or similar)
- Cost tracking API (Anthropic/OpenAI usage APIs)

### Internal
- Lyra's existing `/evolve` command (baseline)
- TUI v2 (for evolution status widget)
- Lyra's skill system (for agent-mode context)

---

## Timeline

**Total Duration**: 8 weeks

- Week 1-2: Harness Foundation
- Week 3-4: Meta-Editing Framework
- Week 5: Two-Phase Loop
- Week 6: Cost Tracking
- Week 7: Ablation & Validation
- Week 8: CLI/TUI Integration

**Milestones**:
- M1 (Week 2): Harness with capability boundaries
- M2 (Week 4): Meta-agent can edit substrate
- M3 (Week 5): Full AEVO loop functional
- M4 (Week 7): Ablation validates harness
- M5 (Week 8): Integrated into Lyra CLI

---

## Next Steps

1. Review this plan with team
2. Set up evolution workspace (`.lyra/evolution/`)
3. Begin Phase 1: Harness Foundation
4. Run pilot on simple task (e.g., prompt optimization)
5. Iterate based on pilot results

---

**Status**: Ready for review and approval

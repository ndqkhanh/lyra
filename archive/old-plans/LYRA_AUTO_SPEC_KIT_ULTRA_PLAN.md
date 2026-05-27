# Lyra Auto-Spec-Kit Ultra Plan

**Version**: 1.0.0  
**Created**: 2026-05-17  
**Status**: Planning Phase

---

## Executive Summary

Auto-Spec-Kit is Lyra's internal mechanism for automatically routing "build-a-thing" prompts through a structured constitution → spec → plan → tasks flow before any code is written. This prevents agents from jumping straight to implementation on complex features, ensuring thoughtful design and user approval at each stage.

**Key Innovation**: Unlike GitHub's spec-kit (manual slash command), Auto-Spec-Kit uses intelligent detection to automatically intercept spec-worthy prompts while staying invisible for simple tasks like "fix typo in README."

**Success Criteria**:
- Detector accuracy: >90% on spec-worthy prompts, <5% false positives on simple tasks
- Latency: <5ms for rule-based path, <800ms for LLM-assisted path
- Zero disk writes without explicit user approval
- Seamless TUI integration with streaming drafts and inline editing

---

## Phase 1: Foundation & Detection System (Week 1)

### 1.1 Core Infrastructure

**New Files**:
```
packages/lyra-cli/src/lyra_cli/spec_kit/
├── __init__.py
├── models.py          # Data models (Verdict, SpecKitState, etc.)
├── detector.py        # Two-stage classifier
├── state.py           # In-memory draft store
└── events.py          # AgentEvent extensions
```

**Key Components**:

#### Verdict Model
```python
@dataclass(frozen=True)
class Verdict:
    spec_worthy: bool
    confidence: float          # 0.0 to 1.0
    reasoning: str             # one-line explanation
    exemption_reason: str | None
    latency_ms: float
```

#### SpecKitState (Reactive)
```python
@dataclass
class SpecKitState:
    phase: Literal["idle", "constitution_check", "drafting_spec", 
                   "drafting_plan", "drafting_tasks", "writing_disk", 
                   "executing", "cancelled", "failed"]
    spec_draft: str = ""
    plan_draft: str = ""
    tasks_draft: str = ""
    constitution_draft: str = ""
    feature_id: str | None = None
    original_prompt: str = ""
```

### 1.2 Two-Stage Detector

**Stage 1: Rule-Based Pre-Classifier** (<5ms)

Confidence scoring system:
- **Spec-worthy signals** (+0.2 each):
  - Imperative verbs: build, create, implement, design, architect, add new
  - Multi-step nouns: system, module, subsystem, feature, pipeline, framework
  - Scope indicators: whole, end-to-end, production, MVP, v1
  - Length: >80 words (+0.3)

- **Exemption signals** (-0.3 each):
  - Fix, patch, update, bump, rename, small, quick, typo, one-liner
  - Direct file references with line numbers
  - Run, test, check, show me
  - Length: <15 words (-0.4)

- **Always-bypass** (return immediately):
  - Starts with `/` (slash command)
  - `LYRA_AUTOSPEC=off` env var
  - Active SpecKitState (phase != "idle")
  - Matches exempt-verb-only regex

**Stage 2: LLM-Assisted Classifier** (only if 0.4 ≤ confidence ≤ 0.8)

- Model: Haiku 4.5 (fast, cheap)
- Timeout: 800ms (fall through to "not spec-worthy" on timeout)
- JSON-mode output with strict schema
- Prompt template:
```
Classify this prompt as spec-worthy or not.
Spec-worthy = needs full design (spec/plan/tasks) before coding.
Not spec-worthy = simple fix, query, or single-file change.

Prompt: {user_prompt}

Return JSON: {"spec_worthy": bool, "confidence": float, "reasoning": str}
```

### 1.3 Event System Extensions

**New AgentEvent Variants**:
```python
class SpecDetectorRan(AgentEvent):
    kind: Literal["spec_detector_ran"]
    verdict: dict  # serialized Verdict

class SpecPhaseChanged(AgentEvent):
    kind: Literal["spec_phase_changed"]
    old_phase: str
    new_phase: str

class SpecDraftChunk(AgentEvent):
    kind: Literal["spec_draft_chunk"]
    artifact: Literal["spec", "plan", "tasks", "constitution"]
    chunk: str

class SpecApprovalRequested(AgentEvent):
    kind: Literal["spec_approval_requested"]
    artifact: str
    full_text: str

class SpecApprovalResolved(AgentEvent):
    kind: Literal["spec_approval_resolved"]
    artifact: str
    approved: bool
    edits: str | None

class SpecFilesWritten(AgentEvent):
    kind: Literal["spec_files_written"]
    feature_id: str
    paths: list[str]
```

---

## Phase 2: State Machine & Orchestration (Week 2)

### 2.1 State Machine Implementation

**New Files**:
```
packages/lyra-cli/src/lyra_cli/spec_kit/
├── orchestrator.py    # Public API, state machine controller
├── drafter.py         # LLM-based artifact generation
└── writer.py          # Disk write operations (gated on approval)
```

**State Transitions**:
```
idle
  ↓ [detector: spec_worthy]
constitution_check
  ↓ [approved OR no changes needed]
drafting_spec
  ↓ [approved OR edited]
drafting_plan
  ↓ [approved]
drafting_tasks
  ↓ [approved]
writing_disk
  ↓ [files written]
executing
  ↓ [normal agent loop]

Any state → cancelled [user Esc or /skip-spec]
Any state → failed [detector/LLM error] → fall back to normal loop
```

### 2.2 Orchestrator Public API

```python
class Orchestrator:
    def __init__(self, event_bus: EventBus, llm_client: Any):
        self.detector = Detector(llm_client)
        self.drafter = Drafter(llm_client, event_bus)
        self.writer = Writer(event_bus)
        self.state = SpecKitState()
    
    async def maybe_intercept(
        self, 
        prompt: str, 
        session: Session
    ) -> InterceptResult:
        """
        Returns InterceptResult(intercepted=False) for non-spec-worthy.
        For spec-worthy, runs state machine and returns 
        InterceptResult(intercepted=True, feature_id=...).
        """
```

### 2.3 Drafter Implementation

**Responsibilities**:
- Generate constitution check (if needed)
- Draft spec.md using LLM
- Draft plan.md using LLM
- Draft tasks.md using LLM
- Stream chunks via SpecDraftChunk events
- Handle user edits and redraft requests

**LLM Prompts** (stored in `templates/`):
```
templates/
├── constitution_check_prompt.md
├── spec_prompt.md
├── plan_prompt.md
└── tasks_prompt.md
```

Each prompt includes:
- Context from constitution.md
- User's original prompt
- Relevant codebase context
- Output format requirements

### 2.4 Writer Implementation

**Disk Layout**:
```
.specify/
└── memory/
    └── constitution.md  # Updated only if constitution check produces changes

specs/
└── <NNN>-<slug>/
    ├── spec.md
    ├── plan.md
    ├── tasks.md
    └── .draft-history/  # Optional: each approval round
        ├── spec.draft-1.md
        └── spec.draft-2.md
```

**Feature Numbering**:
- Scan `specs/` for highest `NNN-` prefix
- Use `NNN+1` for new feature
- Slug: 4-word summary from original prompt (via LLM)

**Idempotency**:
- If `specs/<NNN>-<slug>/spec.md` exists, append `.draft-N` suffix
- Surface conflict to user before writing

---

## Phase 3: TUI Integration (Week 3)

### 3.1 SpecDrawer Widget

**New Files**:
```
packages/lyra-cli/src/lyra_cli/tui_v2/widgets/
└── spec_drawer.py
```

**Widget Behavior**:
- Renders nothing when `SpecKitState.phase == "idle"`
- Opens right-side drawer (Horizontal split) when active
- Shows current phase as title
- Streams draft via `Markdown.get_stream()`
- Approval bar: `[Enter] approve · [E] edit · [R] redraft · [Esc] skip`

**Keyboard Bindings**:
- `Enter`: Approve current artifact
- `E`: Open inline editor with current draft
- `R`: Request redraft from LLM
- `Esc`: Cancel spec-kit flow, return to normal loop

### 3.2 Agent Integration Hook

**Modified File**: `packages/lyra-cli/src/lyra_cli/cli/agent_integration.py`

**Integration Point**:
```python
async def handle_user_message(prompt: str, session: Session) -> None:
    # NEW: Auto-Spec-Kit intercept
    if not session.spec_kit_active:
        result = await spec_orchestrator.maybe_intercept(prompt, session)
        if result.intercepted:
            # Orchestrator owns conversation until state machine completes
            return
    
    # Existing agent-loop path...
```

### 3.3 Event Bus Subscription

**SpecDrawer subscribes to**:
- `SpecPhaseChanged`: Update title, show/hide drawer
- `SpecDraftChunk`: Stream markdown content
- `SpecApprovalRequested`: Show approval bar
- `SpecFilesWritten`: Show success message, transition to executing

---

## Phase 4: Templates & Constitution (Week 4)

### 4.1 Artifact Templates

**New Files**:
```
packages/lyra-cli/src/lyra_cli/spec_kit/templates/
├── spec_template.md
├── plan_template.md
├── tasks_template.md
└── constitution_check_template.md
```

**Template Structure** (aligned with GitHub spec-kit):

**spec_template.md**:
```markdown
# {Feature Title}

## Problem Statement
{What problem does this solve?}

## Proposed Solution
{High-level approach}

## User Experience
{How will users interact with this?}

## Technical Design
{Architecture, data models, APIs}

## Risks & Mitigations
{What could go wrong? How to handle it?}

## Success Metrics
{How do we know it works?}
```

**plan_template.md**:
```markdown
# Implementation Plan: {Feature Title}

## Constitution Check
- [ ] Principle I: Truth Over Aesthetics
- [ ] Principle II: Non-Blocking by Default
- [ ] Principle III: Progressive Disclosure
- [ ] Principle IV: Streaming First-Class
- [ ] Principle V: Keyboard-First
- [ ] Principle VI: Single Source of Truth
- [ ] Principle VII: Observability

## Phase Breakdown
### Phase 1: {Name}
- Files to create: ...
- Files to modify: ...
- Dependencies: ...

### Phase 2: {Name}
...

## Risks & Tradeoffs
{Technical debt, complexity, performance}

## Testing Strategy
{Unit, integration, E2E tests}
```

**tasks_template.md**:
```markdown
# Tasks: {Feature Title}

## Phase 1: {Name}
- [ ] Task 1.1: {Description}
- [ ] Task 1.2: {Description}

## Phase 2: {Name}
- [ ] Task 2.1: {Description}

## Verification
- [ ] All tests pass
- [ ] Constitution compliance verified
- [ ] Documentation updated
```

### 4.2 Constitution Amendment

**Update**: `.specify/memory/constitution.md`

**New Principle VIII**:
```markdown
### VIII. Spec Before Build

Complex features require structured design before implementation. 
Auto-Spec-Kit automatically intercepts "build-a-thing" prompts and 
guides the user through constitution → spec → plan → tasks before 
any code is written.

**Exemptions** (bypass Auto-Spec-Kit):
- Simple fixes: typos, one-liners, small updates
- Direct file operations: "fix line 42 in foo.py"
- Queries: "show me", "explain", "what does X do"
- Slash commands: all `/` prefixed commands
- Explicit bypass: `/skip-spec` or `LYRA_AUTOSPEC=off`

**Sync Impact Report Required**: Any constitution amendment must 
include a Sync Impact Report showing which templates need updates.
```

---

## Phase 5: Testing & Validation (Week 5)

### 5.1 Test Suite

**New Files**:
```
packages/lyra-cli/tests/spec_kit/
├── test_detector.py
├── test_state_machine.py
├── test_orchestrator_e2e.py
├── test_no_disk_without_approval.py
├── test_misclassification_recovery.py
└── fixtures/
    └── test_prompts.json
```

### 5.2 Detector Accuracy Tests

**test_detector.py**:
- 20-prompt test suite (10 spec-worthy, 10 not)
- Assert confidence scores
- Assert latency <5ms for rule-based, <800ms for LLM-assisted
- Test always-bypass conditions

**Test Prompts** (examples):

**Spec-worthy** (should trigger):
1. "Build me a deep-research orchestrator that runs 5 sub-agents in parallel"
2. "Implement a TUI like Claude Code with hierarchical trees and progress indicators"
3. "Add a skill marketplace where users can discover and install community skills"
4. "Create an end-to-end testing framework for Lyra with snapshot testing"
5. "Design a context optimization system with sliding windows and semantic retrieval"

**Not spec-worthy** (should bypass):
1. "Fix the typo in README"
2. "Run the tests"
3. "Show me the agent integration code"
4. "Update line 42 in detector.py to use confidence >= 0.7"
5. "/model switch to opus"

### 5.3 State Machine Tests

**test_state_machine.py**:
- Test all valid transitions
- Test cancellation from each state
- Test failure recovery
- Test state persistence across phases

### 5.4 End-to-End Tests

**test_orchestrator_e2e.py**:
- Feed spec-worthy prompt
- Simulate user approvals at each phase
- Assert 4 files written to disk in correct structure
- Assert feature numbering increments correctly

**test_no_disk_without_approval.py**:
- Feed spec-worthy prompt
- Reject at spec-review step
- Assert zero files on disk
- Assert state returns to idle

**test_misclassification_recovery.py**:
- Feed "fix typo" prompt
- Assert detector returns not-spec-worthy
- Assert normal agent loop proceeds
- Assert latency <100ms

### 5.5 Constitution Compliance Tests

**test_constitution_compliance.py**:
- Principle II: Assert all LLM calls run in workers
- Principle IV: Assert drafts stream (not buffered)
- Principle VI: Assert single SpecKitState source of truth
- Principle VII: Assert structured logs emitted

---

## Phase 6: Documentation & Polish (Week 6)

### 6.1 User Documentation

**Update**: `packages/lyra-cli/README.md`

**New Section**:
```markdown
## Auto-Spec-Kit

Lyra automatically detects when you're asking for a complex feature 
and guides you through a structured design process before writing code.

### When it triggers
- "Build me a..." / "Create a..." / "Implement a..."
- Multi-step features requiring architecture
- Prompts >80 words describing a system

### When it doesn't trigger
- Simple fixes: "fix typo", "update line 42"
- Queries: "show me", "explain"
- Slash commands: `/model`, `/agents`

### How to opt out
- Globally: `export LYRA_AUTOSPEC=off`
- Per prompt: Type `/skip-spec` before submitting
- During flow: Press `Esc` at any phase

### The flow
1. **Constitution Check**: Verify alignment with Lyra principles
2. **Spec Draft**: Problem, solution, design, risks
3. **Plan Draft**: Phases, files, dependencies, tests
4. **Tasks Draft**: Checklist for implementation
5. **Approval**: Review and approve each artifact
6. **Execution**: Normal agent loop, scoped to tasks
```

### 6.2 Developer Documentation

**New File**: `packages/lyra-cli/docs/spec-kit-architecture.md`

**Contents**:
- System architecture diagram
- Detector algorithm explanation
- State machine flow chart
- Event bus integration
- Extension points for new artifact types

### 6.3 Logging & Observability

**Structured Logs** (via structlog):
```python
log.info(
    "spec_detector_ran",
    verdict=verdict.spec_worthy,
    confidence=verdict.confidence,
    latency_ms=verdict.latency_ms,
    session_id=session.id,
)

log.info(
    "spec_phase_changed",
    old_phase=old_phase,
    new_phase=new_phase,
    session_id=session.id,
)

log.info(
    "spec_files_written",
    feature_id=feature_id,
    paths=paths,
    session_id=session.id,
)
```

---

## Phase 7: Performance Optimization (Week 7)

### 7.1 Detector Optimization

**Targets**:
- Rule-based path: <5ms (99th percentile)
- LLM-assisted path: <800ms (95th percentile)
- Memory: <10MB for SpecKitState

**Optimizations**:
- Compile regex patterns once at module load
- Cache LLM responses for identical prompts (5-minute TTL)
- Truncate drafts at 100KB to prevent memory bloat
- Use asyncio.timeout for LLM calls

### 7.2 TUI Performance

**Targets**:
- Drawer open/close: <100ms
- Markdown streaming: 30fps minimum
- Memory: <50MB for SpecDrawer widget

**Optimizations**:
- Render coalescing for >20 chunks/sec
- Lazy load markdown syntax highlighting
- Virtualized scrolling for long drafts

### 7.3 Benchmarking

**New File**: `packages/lyra-cli/tests/spec_kit/bench_detector.py`

**Benchmarks**:
- 1000 prompts through detector
- Measure p50, p95, p99 latency
- Measure memory usage
- Assert performance targets met

---

## Phase 8: Integration & Rollout (Week 8)

### 8.1 Feature Flag

**Environment Variable**: `LYRA_AUTOSPEC`
- `on` (default): Auto-Spec-Kit enabled
- `off`: Disabled globally
- `verbose`: Enabled with debug logging

### 8.2 Gradual Rollout

**Week 8.1**: Internal testing
- Enable for Lyra core team
- Collect feedback on detector accuracy
- Tune confidence thresholds

**Week 8.2**: Beta release
- Enable for early adopters
- Monitor false positive/negative rates
- Iterate on LLM prompts

**Week 8.3**: General availability
- Enable by default for all users
- Publish blog post and documentation
- Monitor usage metrics

### 8.3 Metrics & Monitoring

**Track**:
- Detector accuracy (true positives, false positives, false negatives)
- Average latency per stage
- User approval/rejection rates per artifact
- Feature completion rates (spec → tasks → execution)
- Opt-out rates

**Dashboards**:
- Real-time detector performance
- User engagement with spec-kit flow
- Constitution compliance violations

---

## Risk Assessment & Mitigations

### Risk 1: Detector False Positives (High Impact)

**Risk**: Annoying users by intercepting simple prompts

**Mitigations**:
- Conservative threshold (0.7 confidence)
- Easy escape hatch (`Esc`, `/skip-spec`)
- Opt-out env var (`LYRA_AUTOSPEC=off`)
- Log every verdict for tuning
- A/B test thresholds with telemetry

### Risk 2: Detector False Negatives (Medium Impact)

**Risk**: Missing opportunities for structured design

**Mitigations**:
- Toast-level hint: "This looked spec-worthy — invoke `/spec` to retry"
- Retrospective signals: if user creates >5 files in one session, suggest spec-kit
- Manual trigger: `/spec` command to force spec-kit flow

### Risk 3: LLM Drafting Takes Too Long (Medium Impact)

**Risk**: User waits >10 seconds for draft

**Mitigations**:
- Stream chunks immediately (don't buffer)
- User can `[E]` edit at any point
- User can `[Esc]` skip and proceed to normal loop
- Timeout at 30 seconds, fall back to template

### Risk 4: Constitution Drift (Low Impact)

**Risk**: Features violate constitution over time

**Mitigations**:
- Every constitution amendment requires Sync Impact Report
- Constitution check phase surfaces conflicts
- Never silently mutate constitution
- Require explicit user approval for amendments

### Risk 5: Disk Write Conflicts (Low Impact)

**Risk**: Overwriting existing spec files

**Mitigations**:
- Idempotent writes: existing file → `.draft-N` suffix
- Surface conflict to user before writing
- Atomic file operations (write to temp, then rename)

---

## Success Metrics

### Quantitative

- **Detector Accuracy**: >90% true positives, <5% false positives
- **Latency**: <5ms rule-based, <800ms LLM-assisted
- **User Engagement**: >70% approval rate on drafted specs
- **Feature Completion**: >80% of spec-kit flows reach execution phase
- **Opt-out Rate**: <10% of users disable Auto-Spec-Kit

### Qualitative

- Users report feeling more confident about complex features
- Fewer "I started coding too early" incidents
- Better alignment between user intent and implementation
- Improved code quality from upfront design

---

## Dependencies & Prerequisites

### External Dependencies

- Python ≥3.11 (asyncio.TaskGroup)
- Textual ≥0.86 (MarkdownStream, Worker API)
- Anthropic SDK (for Haiku LLM calls)
- structlog (for structured logging)

### Internal Dependencies

- `lyra-cli/tui_v2`: TUI framework and widgets
- `lyra-cli/cli/agent_integration.py`: Agent loop entry point
- `lyra-cli/interactive/`: Session state management
- `.specify/memory/constitution.md`: Constitution v1.0.0

### New Dependencies

None required — all functionality uses existing dependencies.

---

## Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1. Foundation & Detection | Week 1 | Detector, models, events |
| 2. State Machine & Orchestration | Week 2 | Orchestrator, drafter, writer |
| 3. TUI Integration | Week 3 | SpecDrawer widget, agent hook |
| 4. Templates & Constitution | Week 4 | Artifact templates, Principle VIII |
| 5. Testing & Validation | Week 5 | 20+ tests, benchmarks |
| 6. Documentation & Polish | Week 6 | User docs, dev docs, logs |
| 7. Performance Optimization | Week 7 | Latency tuning, memory optimization |
| 8. Integration & Rollout | Week 8 | Feature flag, gradual rollout |

**Total**: 8 weeks from start to general availability

---

## Next Steps

1. **Review this plan** with Lyra core team
2. **Approve architecture** and state machine design
3. **Assign ownership** for each phase
4. **Set up tracking** (GitHub project, milestones)
5. **Begin Phase 1** implementation

---

## Appendix A: File Structure

```
packages/lyra-cli/
├── src/lyra_cli/
│   ├── spec_kit/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── detector.py
│   │   ├── state.py
│   │   ├── events.py
│   │   ├── orchestrator.py
│   │   ├── drafter.py
│   │   ├── writer.py
│   │   └── templates/
│   │       ├── spec_template.md
│   │       ├── plan_template.md
│   │       ├── tasks_template.md
│   │       └── constitution_check_template.md
│   ├── cli/
│   │   └── agent_integration.py  # MODIFIED
│   └── tui_v2/
│       └── widgets/
│           └── spec_drawer.py  # NEW
├── tests/spec_kit/
│   ├── test_detector.py
│   ├── test_state_machine.py
│   ├── test_orchestrator_e2e.py
│   ├── test_no_disk_without_approval.py
│   ├── test_misclassification_recovery.py
│   ├── test_constitution_compliance.py
│   ├── bench_detector.py
│   └── fixtures/
│       └── test_prompts.json
└── docs/
    └── spec-kit-architecture.md

.specify/
└── memory/
    └── constitution.md  # MODIFIED (add Principle VIII)

specs/
└── <NNN>-<slug>/  # Created by writer.py
    ├── spec.md
    ├── plan.md
    ├── tasks.md
    └── .draft-history/
```

---

## Appendix B: Constitution Compliance Checklist

- [x] **Principle I: Truth Over Aesthetics**
  - All phase transitions map to real SpecKitState changes
  - Detector verdict includes actual confidence score
  - File write status reflects real disk operations

- [x] **Principle II: Non-Blocking by Default**
  - Detector LLM call runs in Worker
  - Drafter LLM calls run in Workers
  - Writer disk operations run in Workers
  - All workers have explicit timeout and cancellation

- [x] **Principle III: Progressive Disclosure**
  - SpecDrawer hidden when phase == "idle"
  - Drafts expandable/collapsible
  - Approval bar shows keyboard shortcuts

- [x] **Principle IV: Streaming First-Class**
  - Drafts stream via SpecDraftChunk events
  - Markdown rendered incrementally via get_stream()
  - No buffering of full response

- [x] **Principle V: Keyboard-First**
  - Enter: approve
  - E: edit
  - R: redraft
  - Esc: cancel
  - All bindings visible in footer

- [x] **Principle VI: Single Source of Truth**
  - SpecKitState is the only state store
  - Widgets subscribe via reactives
  - No duplicate state in widgets

- [x] **Principle VII: Observability**
  - Structured logs for all events
  - session_id, phase, latency tracked
  - Logs to ~/.lyra/logs/

---

**End of Ultra Plan**

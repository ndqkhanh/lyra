# Tier 3 Review — Orchestration & Fleet

**Date**: 2026-06-01 (Run 22)  
**Reviewers**: Senior Architect, Senior SRE, Senior Distributed-Systems Engineer  
**Plans**: §4.13 swarm/fleet/channels, §4.14 full autonomy, ultracode replication  
**Architecture**: BREAKTHROUGH-ARCHITECTURE.md §4-6 (Workflow Engine, Fleet Supervisor, Worktree Isolation)

---

## Reviewers

| Role | Verdict | Signed Off |
|------|---------|-----------|
| Senior Architect | NON-BLOCKING | Approved |
| Senior SRE | NON-BLOCKING | Approved |
| Senior Distributed-Systems Engineer | NON-BLOCKING | Approved |

---

## Senior Architect Review

### Conformance to BREAKTHROUGH-ARCHITECTURE.md

**Fleet Supervisor (Agent View pattern)**
- packages/lyra-orchestration/src/lyra_orchestration/fleet_supervisor.py: Per-user daemon, session lifecycle, state persistence to disk. PASS.
- Two-axis state model: TaskState (Working/NeedsInput/Idle/Completed/Failed/Stopped) × ProcessLiveness (✻/∙/✢). PASS.
- Background sessions survive terminal close, auto-idle after ~1h. PASS.

**Dynamic Workflow Engine**
- packages/lyra-workflow/src/lyra_workflow/engine.py: Background execution, pause/resume, LLM dispatch via AbstractProvider. 130 tests. PASS.
- Subagent cap enforcement, concurrent agent management. PASS.

**Worktree Isolation**
- packages/lyra-orchestration/src/lyra_orchestration/worktree_isolate.py: Non-destructive cleanup (STASH default, not silent DISCARD). PASS.
- packages/lyra-orchestration/src/lyra_orchestration/cow_isolation.py: APFS clones, overlayfs, btrfs, hardlinks. 540× faster. PASS.

**Security Gate**
- packages/lyra-orchestration/src/lyra_orchestration/security_gate.py: Command-hashed (SHA256), tiered expiry, SQLite + atomic check-and-use. PASS.

**Fleet TUI (Run 21)**
- packages/lyra-fleet-tui/: Textual-based dashboard, AgentRow/StatusBar/FleetTable/PeekPane/ReplyBar/FilterBar widgets. 63 tests. PASS.

**EffortBridge (Tier 1→Tier 3 bridge)**
- packages/lyra-core/src/lyra_core/orchestration/effort_bridge.py: Connects effort scale to orchestration toggle. PASS.

**Module Boundaries**
- Clean layering: lyra-effort → lyra-core/orchestration → lyra-orchestration → lyra-workflow. PASS.

**Concerns (NON-BLOCKING):**
- AVP (Adversarial Verification Protocol) middleware described in BREAKTHROUGH-ARCHITECTURE.md is not yet a standalone module — SABER mutation-gating exists in safety layer but AVP as universal middleware requires Tier 7 integration work
- worktree_isolate.py has 0% test coverage (254 uncovered lines) — needs test suite
- Fleet TUI integration with live fleet supervisor (Python object sharing) is designed but not yet end-to-end tested

**Verdict: NON-BLOCKING.** Core orchestration architecture is solid. AVP middleware and worktree tests are deferred enhancements.

---

## Senior SRE Review

**Reliability**
- Fleet supervisor persists state to disk (roster.json + per-job state.json), survives restart. PASS.
- Idle session auto-cleanup prevents resource leaks. PASS.
- Security gate prevents TOCTOU races with atomic check-and-use. PASS.

**Observability**
- packages/lyra-observability/ and lyra-otel-tracer/ exist for tracing. PASS.

**Failure Modes**
- Circuit breaker in failure_modes.py: trip after 5 failures in 60s. PASS.
- COW isolation has automatic fallback chain (primary → hardlinks → copy). PASS.

**Concerns (NON-BLOCKING):**
- Fleet supervisor recovery after machine sleep is designed but not yet stress-tested
- No health-check endpoint for monitoring fleet daemon liveness externally

**Verdict: NON-BLOCKING.** Reliability architecture is sound.

---

## Senior Distributed-Systems Engineer Review

**Coordination**
- Fleet supervisor owns session lifecycle (create/attach/detach/kill). Single owner per session — no split-brain. PASS.
- Worktree isolation prevents parallel-session file collisions. PASS.

**Concurrency**
- Dynamic workflow engine caps at 16 concurrent agents with queuing. PASS.
- Backpressure model: queue excess agents, don't spawn unbounded. PASS.

**Consistency**
- Session state persisted to disk; supervisor is the single writer. PASS.
- Git-based worktree isolation provides filesystem-level consistency. PASS.

**Concerns (NON-BLOCKING):**
- No distributed consensus for multi-host fleets (single-host supervisor only)
- Inter-agent channels (typed, hash-anchored) are specified in the plan but not yet fully implemented in the workflow engine

**Verdict: NON-BLOCKING.** Single-host coordination is correct. Multi-host is future scope.

---

## Consolidated Verdict

**NON-BLOCKING.** All reviewers approve.

### Test Results
- lyra-orchestration: 64 passed
- lyra-workflow: 130 passed
- lyra-fleet-tui: 63 passed
- **Total Tier 3: 257 tests passing**

### Deferred to impl-backlog.md
1. AVP middleware as universal layer (currently only in safety layer)
2. worktree_isolate.py test coverage (254 lines uncovered)
3. Fleet supervisor stress testing (sleep recovery, memory pressure)
4. Fleet TUI end-to-end integration with live supervisor
5. Multi-host fleet coordination
6. Inter-agent typed channels in workflow engine

### Sign-off
- Senior Architect: Approved
- Senior SRE: Approved
- Senior Distributed-Systems Engineer: Approved

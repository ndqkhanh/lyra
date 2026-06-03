# Lyra Test Plan

> Run 1 — June 3, 2026 | Covers deep research, auto research, workflows, and fleet flows

## Test Infrastructure

- **Framework:** pytest (Python) + jest (TypeScript)
- **Coverage target:** 80%+ (per rules)
- **Execution:** DeepSeek API key from `~/.claude/settings.json` for test execution only (lower cost)

## Scenario Suites

### 1. Deep Research Flows

| ID | Scenario | Expected Outcome | Edge Cases |
|----|----------|-----------------|------------|
| DR-01 | Single-angle research query | Fan-out search across 4 angles → cross-check findings → cited report with ≥3 sources | Empty search results, paywalled sources, non-English sources |
| DR-02 | Multi-hop research | Agent follows citations from source A → B → C, synthesizes across chain | Circular citations, broken links, contradictory findings |
| DR-03 | Adversarial verification | Findings challenged by skeptic agent → false claims filtered → ≥2/3 verifiers confirm remaining | All claims rejected, unanimous rejection, tie vote |
| DR-04 | Evidence graph construction | Sources deposited into graph → cross-referenced → graph exported as artifact | Duplicate sources, conflicting evidence, missing links |
| DR-05 | Anti-fabrication | Claim without evidence path in graph → auto-flagged → report excludes unverifiable claims | All claims flagged, borderline evidence, LLM hallucination of sources |

### 2. Auto Research Flows

| ID | Scenario | Expected Outcome | Edge Cases |
|----|----------|-----------------|------------|
| AR-01 | Continuous research loop | Agent runs unattended → researches → checkpoints → resumes after interruption | Machine sleep, daemon restart, context reset |
| AR-02 | Self-organizing teams | Agents cluster around promising leads → shared success/failure log prevents redundancy | All leads fail, resource contention, agent departure |
| AR-03 | IterResearch workspace | Context reset → workspace reconstructed from memory → research continues with <5% information loss | Memory corruption, incomplete reconstruction |

### 3. Workflow Engine

| ID | Scenario | Expected Outcome | Edge Cases |
|----|----------|-----------------|------------|
| WF-01 | parallel() execution | N independent agents run concurrently → results collected → all complete or null | Agent crash, timeout, partial results |
| WF-02 | pipeline() execution | Items flow through stages independently → no barrier between stages | Stage failure, pipeline stall, item drop |
| WF-03 | Checkpoint/resume | Workflow interrupted mid-run → resume → cached results replayed, new calls run | All calls cached (no-op resume), partial cache |
| WF-04 | Budget enforcement | budget.spent() reaches total → agent() calls throw → workflow terminates gracefully | Budget reset, near-limit decisions |
| WF-05 | Adversarial quality pattern | Understand → Change → Verify loop → filter to confirmed findings | No findings, all rejected, verification loop |

### 4. Fleet & Supervisor

| ID | Scenario | Expected Outcome | Edge Cases |
|----|----------|-----------------|------------|
| FL-01 | Daemon start/stop | Supervisor starts on first use → persists state → self-exits when roster empty | Already running, crash recovery, zombie processes |
| FL-02 | Session dispatch | New session created → isolated worktree → runs independently | Worktree failure, non-git repo, env propagation |
| FL-03 | Peek/attach/detach | Peek shows latest output → attach opens full conversation → detach keeps session running | Session crashed, terminal resize, concurrent attach |
| FL-04 | Idle session cleanup | Idle unattached session → stopped after timeout → respawned on next peek | Dirty worktree, long-running task, user override |
| FL-05 | Non-destructive cleanup | Dirty worktree → auto-stashed + archived → worktree removed → stash recoverable | Stash conflict, archive failure, user chooses discard |

### 5. Voice Pipeline

| ID | Scenario | Expected Outcome | Edge Cases |
|----|----------|-----------------|------------|
| VC-01 | Push-to-talk | Hold key → speak → release → transcript in buffer | Background noise, silence, clipping |
| VC-02 | VI+EN transcription | Vietnamese input → accurate transcript → VI-aware post-processing | Code-switching, accents, technical terms |
| VC-03 | TTS output | Agent response → audio playback → natural prosody | Long responses, streaming interruption |
| VC-04 | Provider swap | Switch Whisper → Parakeet → pipeline continues without restart | Provider unavailable, latency difference |

### 6. Safety & Permissions

| ID | Scenario | Expected Outcome | Edge Cases |
|----|----------|-----------------|------------|
| SP-01 | Deny-first evaluation | Unknown tool → denied by default → user prompted | Auto mode, bypass mode, compound command |
| SP-02 | Collusion detection | Coordinated truthful evidence → flagged → agents isolated | False positives, threshold calibration |
| SP-03 | Unwatched session guard | Background session requests bypass → denied → requires prior human accept | Session restart, config override |
| SP-04 | Mutation-gated verification | Mutating action (write/delete) → triggers verification → predicted effect vs actual | False mutation classification, effect prediction error |

### 7. Multi-Provider

| ID | Scenario | Expected Outcome | Edge Cases |
|----|----------|-----------------|------------|
| MP-01 | Provider abstraction | Same agent code → runs on Claude, DeepSeek, GPT → identical behavior | Provider-specific features, tool format differences |
| MP-02 | Router fallback | Cheap model fails → retry on stronger model → succeed or escalate to human | Infinite escalation loop, all models fail |
| MP-03 | Capability degradation | Vision task → text-only provider → OCR fallback → degraded but functional | No fallback available, degradation too severe |

## Pass/Fail Criteria

| Severity | Criteria |
|----------|----------|
| **Block** | Data loss, security bypass, silent corruption |
| **Fail** | Incorrect output, missed deadline, feature regression |
| **Warn** | Performance degradation, UX regression, edge case gap |
| **Pass** | Expected outcome achieved, edge cases handled gracefully |

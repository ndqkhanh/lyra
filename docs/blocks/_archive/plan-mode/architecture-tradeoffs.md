# Plan Mode Architecture Tradeoffs

## Overview

This document examines the key design decisions in Plan Mode, the alternatives considered, and the rationale for each choice. Every architecture decision involves tradeoffs; understanding them helps users configure Plan Mode appropriately and contributors extend it effectively.

## Core Design Decisions

### 1. Read-Only Planning Phase

**Decision:** The Planner agent has zero write permissions during plan generation.

**Alternatives Considered:**

| Alternative | Pros | Cons | Why Not Chosen |
|------------|------|------|----------------|
| **Allow exploratory edits** | Planner can test hypotheses by trying changes | Risk of side effects before approval; harder rollback | User loses approval control point |
| **Sandbox mutations** | Safe experimentation in isolated env | Complex infra (containers/VMs); slow; resource heavy | Engineering complexity vs benefit ratio too high |
| **Diff-only mode** | Planner shows proposed changes without applying | Good preview, no side effects | Requires two-phase execution (preview then apply); confusing UX |

**Chosen:** Strict read-only with comprehensive read tools (Read, Grep, Glob, LSP, WebFetch).

**Rationale:**
- **User control:** Approval gate is meaningless if changes already happened
- **Simplicity:** No rollback logic needed
- **Trust:** Users approve before mutations, not after
- **Cost efficiency:** No wasted API calls on abandoned plans

**Tradeoffs:**
- ✅ Clear approval boundary
- ✅ Zero risk of accidental mutations
- ✅ Predictable permission model
- ❌ Planner can't verify edits by testing
- ❌ May produce plans that fail when executed

**Mitigation:** 
- Comprehensive read tools let Planner inspect current state thoroughly
- Verifier provides feedback loop to catch execution failures
- ReplanTool enables course correction

### 2. Two-Tier Model Routing (Smart/Fast Slots)

**Decision:** Use expensive "smart slot" model for planning, cheap "fast slot" for execution loop.

**Alternatives Considered:**

| Alternative | Cost | Quality | Latency | Why Not Chosen |
|------------|------|---------|---------|----------------|
| **Smart model always** | 5-10x higher | Best | Higher | Prohibitively expensive for iteration-heavy execution |
| **Fast model always** | Baseline | Good | Lowest | Plans lack depth; miss edge cases |
| **User chooses per task** | Variable | Variable | Variable | Decision fatigue; most users don't know which to pick |
| **Dynamic mid-session switching** | Optimal | Variable | Variable | Complex logic; hard to predict costs |

**Chosen:** Fixed two-tier: smart for planning, fast for execution.

**Cost Analysis (example task: add auth middleware):**

```
Scenario 1: Smart model always
- Planning: deepseek-v4-pro @ 200k tokens = $2.40
- Execution: deepseek-v4-pro @ 800k tokens (iterations) = $9.60
- Total: $12.00

Scenario 2: Fast model always
- Planning: deepseek-chat @ 200k tokens = $0.20
- Execution: deepseek-chat @ 800k tokens = $0.80
- Total: $1.00
- Result: Plan misses edge cases; execution fails 40% → replan cost

Scenario 3: Two-tier (chosen)
- Planning: deepseek-v4-pro @ 200k tokens = $2.40
- Execution: deepseek-chat @ 800k tokens = $0.80
- Total: $3.20
- Result: High-quality plan + efficient execution
```

**Rationale:**
- **Planning is high-leverage:** A better plan reduces total execution cost
- **Execution is iteration-heavy:** Fast model handles tactical edits well
- **Predictable costs:** Users know planning is expensive, loops are cheap
- **Quality where it matters:** Smart model for strategy, fast model for tactics

**Tradeoffs:**
- ✅ 60-70% cost reduction vs smart-only
- ✅ Better plans than fast-only
- ✅ Simple mental model (two roles)
- ❌ Fixed boundary (can't switch mid-execution)
- ❌ Fast model may struggle with complex execution steps

**Configuration Override:**

```yaml
models:
  smart_slot: deepseek-v4-pro      # Override with claude-opus-4.5 for max quality
  fast_slot: deepseek-v4-flash     # Override with deepseek-chat for cost
  force_smart_for_execution: false # Set true to use smart slot always
```

### 3. Plan Artifact as Markdown + YAML

**Decision:** Store plans as human-readable markdown files with YAML frontmatter.

**Alternatives Considered:**

| Alternative | Human-Readable | Machine-Parseable | Git-Friendly | Extensible |
|------------|----------------|-------------------|--------------|------------|
| **JSON** | ❌ (verbose, nested) | ✅ | ⚠️ (merge conflicts) | ✅ |
| **YAML only** | ⚠️ (structured) | ✅ | ✅ | ✅ |
| **SQLite DB** | ❌ | ✅ | ❌ (binary) | ⚠️ (schema migrations) |
| **Protobuf** | ❌ | ✅ | ❌ (binary) | ⚠️ (requires tooling) |
| **Markdown + YAML** | ✅ | ✅ | ✅ | ✅ |

**Chosen:** Markdown body with YAML frontmatter (Jekyll/Hugo pattern).

**Example:**

```markdown
---
session_id: 01HXK2N
planner_model: deepseek-v4-pro
---

# Plan: Add rate limiting

## Acceptance tests
- tests/middleware/test_rate_limit.py::test_blocks_after_threshold

## Steps
1. Create RateLimiter class with Redis backend
2. Add middleware to FastAPI app
```

**Rationale:**
- **Human-first:** Users review plans by eye; markdown is native format
- **Git-native:** Commits, diffs, PRs work naturally
- **No build step:** View plans in any text editor or GitHub UI
- **Machine-parseable:** YAML frontmatter for structured data, markdown sections for narrative
- **Extensible:** Add new sections without breaking schema

**Tradeoffs:**
- ✅ Perfect for review workflows
- ✅ Version control friendly
- ✅ No special tooling required
- ❌ Parsing ambiguity if markdown sections contain YAML-like content
- ❌ Not efficient for bulk queries (need index.json)

**Mitigation:**
- `index.json` provides fast lookups for CLI commands
- Parser uses frontmatter delimiters (`---`) to avoid ambiguity

### 4. Approval Gate with Multiple Paths

**Decision:** Support three approval mechanisms: interactive, auto-approve, CI-signed.

**Alternatives Considered:**

| Alternative | Security | Automation | Flexibility | Why Not Chosen |
|------------|----------|------------|-------------|----------------|
| **Always interactive** | ✅ | ❌ | ❌ | Blocks CI/CD |
| **Always auto-approve** | ❌ | ✅ | ❌ | Dangerous for production |
| **Signed approval only** | ✅ | ✅ | ⚠️ | Complex setup; overkill for solo devs |

**Chosen:** Three paths with clear use cases.

**Use Cases:**

```python
# Development (local)
lyra run "add auth"
# → Interactive approval: user reviews, types /approve

# CI testing (trusted env)
lyra run "add auth" --auto-approve
# → Skips approval; logs CI run ID

# Production deployment (paranoid mode)
# Step 1: Plan-only job
lyra plan "add auth" --sign-with $SECRET > plan-hash.txt
# Step 2: Human reviews plan artifact in PR
# Step 3: Execution job verifies signature
lyra run --execute-plan $(cat plan-hash.txt) --verify-sig $SECRET
```

**Security Model:**

```python
def verify_ci_signed_approval(plan_path: str, goal_hash: str, 
                              session_id: str, signature: str) -> bool:
    """
    HMAC verification for CI-signed plans.
    """
    import hmac
    import hashlib
    
    secret = os.getenv("LYRA_APPROVAL_SECRET")
    if not secret:
        raise ValueError("LYRA_APPROVAL_SECRET not set")
    
    message = f"{plan_path}|{goal_hash}|{session_id}".encode()
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(expected, signature)
```

**Rationale:**
- **Interactive:** Default for humans; provides review moment
- **Auto-approve:** Trusted CI environments; speeds up testing
- **CI-signed:** Separate planning from execution; human-in-the-loop without blocking

**Tradeoffs:**
- ✅ Flexible for different workflows
- ✅ Secure by default (interactive)
- ✅ Automation-friendly (auto-approve)
- ✅ Production-safe (CI-signed)
- ❌ Three paths to test and maintain
- ❌ User must understand when to use each

### 5. Plan Revisions via ReplanTool

**Decision:** Allow mid-execution replanning when agent detects plan is wrong.

**Alternatives Considered:**

| Alternative | Flexibility | Predictability | Cost | Why Not Chosen |
|------------|-------------|----------------|------|----------------|
| **Fail fast, no replan** | ❌ | ✅ | Low | Wastes progress; frustrates users |
| **Auto-replan always** | ✅ | ❌ | High | Unstable; plan thrashes |
| **User-triggered replan** | ⚠️ | ✅ | Medium | Requires user to notice failure |
| **Agent-triggered with approval** | ✅ | ✅ | Medium | Best balance |

**Chosen:** Agent calls `ReplanTool` when blocked; user re-approves.

**Replan Trigger Conditions:**

```python
class ReplanTrigger:
    """Conditions that justify a replan request."""
    
    MISSING_DEPENDENCY = "discovered_missing_dependency"
    # Example: Plan assumes library X exists, but it's not installed
    
    INCORRECT_ASSUMPTION = "incorrect_architectural_assumption"
    # Example: Plan assumes REST API, but codebase uses GraphQL
    
    SCOPE_CHANGE = "scope_change_required"
    # Example: "Add auth" also needs "Add user model" (not in original plan)
    
    FORBIDDEN_FILE_REQUIRED = "forbidden_file_actually_required"
    # Example: Plan marked package.json forbidden, but new dep is needed
```

**Replan Flow:**

```
1. Agent executing feature item 3 of 5
2. Agent discovers blocker (e.g., missing dependency)
3. Agent calls ReplanTool(reason="discovered_missing_dependency", evidence="...")
4. Execution pauses
5. Planner receives: original plan + progress so far + blocker reason
6. Planner generates revised plan (.rev-1.md)
7. User approves revision
8. Execution resumes from first changed item
```

**Rationale:**
- **Adaptive:** Handles unknowns discovered during execution
- **Controlled:** User approves each revision (no runaway changes)
- **Efficient:** Preserves progress; only redoes necessary items
- **Traceable:** Each revision is a separate artifact

**Tradeoffs:**
- ✅ Handles real-world uncertainty
- ✅ User stays in control
- ✅ Audit trail of plan evolution
- ❌ Frequent replans signal poor initial plan (telemetry tracks this)
- ❌ Adds latency (re-planning + re-approval)

**Metrics:**

```python
# Alert if replan rate > 20% per session
if session.revision_count / session.feature_items > 0.2:
    alert("high_replan_rate", {
        "session_id": session.id,
        "revisions": session.revision_count,
        "items": session.feature_items,
    })
```

### 6. Heuristic-Based Trivial Detection

**Decision:** Use weighted signals to auto-skip plan mode for trivial tasks.

**Alternatives Considered:**

| Alternative | Accuracy | Transparency | Maintainability |
|------------|----------|--------------|-----------------|
| **ML classifier** | High (after training) | Low (black box) | Complex (training pipeline) |
| **LLM meta-call** | Very high | Medium | Expensive (extra API call) |
| **Rule-based heuristic** | Medium-High | High | Simple |
| **Always plan** | N/A (no skipping) | Perfect | N/A |

**Chosen:** Weighted heuristic with transparent rules.

**Heuristic Logic:**

```python
def compute_triviality_score(task: str, repo: Repo, session: Session) -> float:
    """
    Returns 0.0 (definitely non-trivial) to 1.0 (definitely trivial).
    Threshold: 0.7 to skip plan mode.
    """
    score = 0.0
    
    # Task length (shorter = more trivial)
    if len(task) < 80:
        score += 0.3
    elif len(task) < 150:
        score += 0.1
    
    # Keyword matching
    trivial_keywords = ["typo", "fix comment", "rename", "format", "log"]
    if any(kw in task.lower() for kw in trivial_keywords):
        score += 0.4
    
    # File scope (single file = more trivial)
    file_mentions = re.findall(r'\b\w+\.\w{2,5}\b', task)
    if len(file_mentions) == 1:
        score += 0.2
    
    # Explicit complexity keywords (overrides trivial)
    complex_keywords = ["plan", "design", "architect", "refactor", "migrate"]
    if any(kw in task.lower() for kw in complex_keywords):
        return 0.0  # Force plan mode
    
    return min(score, 1.0)

# Usage
if compute_triviality_score(task, repo, session) >= 0.7:
    skip_plan_mode()
```

**Rationale:**
- **Fast:** No external calls
- **Transparent:** Users can audit decision
- **Tunable:** Adjust weights based on telemetry
- **Overridable:** `--no-plan` and `--force-plan` flags

**Tradeoffs:**
- ✅ Zero latency
- ✅ Explainable decisions
- ✅ No training required
- ❌ Lower accuracy than ML/LLM
- ❌ Requires periodic tuning

**Telemetry-Driven Tuning:**

```python
# Collect false positives/negatives
class Triviality:
    def __init__(self):
        self.false_positives = []  # Skipped but should have planned
        self.false_negatives = []  # Planned but could have skipped
    
    def record_false_positive(self, task: str, reason: str):
        """User explicitly said 'I needed a plan for this'."""
        self.false_positives.append({"task": task, "reason": reason})
    
    def record_false_negative(self, task: str):
        """Plan was trivial (1-2 items, <30 sec execution)."""
        self.false_negatives.append({"task": task})
    
    def suggest_tuning(self):
        """Analyze patterns and suggest weight adjustments."""
        # e.g., "Too many false positives on tasks with 'update' keyword"
        pass
```

## Performance Tradeoffs

### Latency vs Quality

| Phase | Latency | Quality Impact | Optimization Strategy |
|-------|---------|----------------|----------------------|
| Heuristic check | <10ms | N/A | In-memory rules |
| Planning (smart slot) | 5-30s | High | Acceptable for front-loading |
| Approval (interactive) | Variable (user) | N/A | Async; non-blocking for user |
| Execution (fast slot) | 1-5s/iteration | Medium | Cache + parallel tool calls |

### Cost vs Accuracy

```
Budget-conscious config:
  smart_slot: deepseek-chat          # Cheaper planning
  fast_slot: deepseek-chat           # Same model for consistency
  auto_skip_trivial: true            # Aggressive skipping
  → Cost: ~$0.50/task, Accuracy: 85%

Balanced config (default):
  smart_slot: deepseek-v4-pro        # High-quality planning
  fast_slot: deepseek-chat           # Efficient execution
  auto_skip_trivial: true            # Heuristic-based
  → Cost: ~$2.00/task, Accuracy: 95%

Quality-first config:
  smart_slot: claude-opus-4.5        # Best planning
  fast_slot: deepseek-v4-pro         # High-quality execution
  auto_skip_trivial: false           # Always plan
  → Cost: ~$8.00/task, Accuracy: 99%
```

## Maintainability Tradeoffs

### Simplicity vs Flexibility

**Current:** Fixed two-tier routing, hardcoded permission modes, schema validation.

**Alternative:** Plugin-based routing, custom permission rules, dynamic schemas.

**Chosen:** Simplicity for v1; extensibility via config, not code.

**Rationale:**
- 80% of users need the default behavior
- Power users configure via YAML, not code
- Reduces surface area for bugs
- Faster onboarding for contributors

**Future:** Plugin system for custom planners (v2 roadmap).

## Security Tradeoffs

### Open vs Signed Approvals

**Current:** Three approval modes (interactive, auto, signed).

**Risk:** Auto-approve in wrong context = unreviewed mutations.

**Mitigation:**
- Auto-approve only for `--auto-approve` flag (explicit opt-in)
- CI-signed requires shared secret (env var, not in code)
- Telemetry alerts on unusual approval patterns

**Future:** Role-based approval (junior dev plans, senior approves).

## Conclusion

Plan Mode's architecture prioritizes:

1. **User control** over automation
2. **Cost efficiency** over raw performance
3. **Simplicity** over flexibility (for v1)
4. **Transparency** over black-box intelligence

These tradeoffs reflect Lyra's design philosophy: empower users with structured workflows while keeping the system understandable and maintainable.

## Next Steps

- [Architecture Overview](architecture.md) — System components and data flow
- [System Design](system-design.md) — High-level abstractions and contracts
- [Implementation Guide](implementation-guide.md) — Build Plan Mode from scratch
- [Deep Dive](deep-dive.md) — Internal algorithms and optimizations

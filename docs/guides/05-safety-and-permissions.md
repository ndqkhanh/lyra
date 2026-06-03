# Guide: Safety and Permissions

> 📖 Guide — Walk through Lyra's 7-layer safety architecture from prompt input to audit trail. Learn which permission mode to use for different scenarios and how behavioral guardrails work.

Lyra's safety system is defense-in-depth -- seven layers that inspect, classify, and potentially block every input, tool call, and agent action.

---

## The 7 Safety Layers

### Layer 0: Input Validation

Before anything processes your input, Lyra scans for prompt injection patterns (`ignore previous instructions`, `<|im_start|>`), scrubs PII (SSNs, credit cards, API keys), and enforces rate limits. Combined with NeMo Guardrails, injection attack success rate drops from 17.6% to 1.75%.

### Layer 1: Cognitive-Executive Separation (Parallax)

The most important architectural safety measure. Reasoning and execution run in **structurally separated contexts**:

```
REASONING CONTEXT (read-only)    EXECUTION CONTEXT (action-capable)
  - Planning, analysis              - Tool invocation, file ops
  - CANNOT invoke tools             - ALL actions logged to HIR
```

A validator agent (running a different model family than the executor) reviews the execution plan for intent, scope, and safety before allowing it through. Block rate on adversarial attacks: 98.9%.

### Layer 2: Permission Gating

Three permission modes, selected per session:

| Mode | Description | Best For |
|---|---|---|
| plan | Read-only, writes blocked | New users, exploration |
| auto-edit | Common operations auto-approved | Experienced users (76% of sessions) |
| bypass | Full autonomy | Testing, CI automation |

Each tool call is classified against a 4-level risk gate:

| Risk | Gate | Example |
|---|---|---|
| LOW | AUTO | Read, Grep |
| MEDIUM | NOTIFY | Write, WebFetch |
| HIGH | CONFIRM | Bash, Delete |
| CRITICAL | BLOCK | Disarm safety |

### Layer 3: Multi-Agent Validation (ARIS)

Critical operations trigger a 3-stage validation chain: evidence integrity -> result-to-claim mapping -> claim auditing. False positive rate: 8.3% single agent, 0.7% multi-agent (91.6% reduction).

### Layer 4: Behavioral Monitoring

Continuous monitoring for anomalies: action-sequence analysis over time, intent deviation detection, statistical baselines per task type. Automatic lockdown on anomaly score above threshold.

### Layer 5: Unwatched Session Guardrails

Unattended sessions (L3+) default to `ask` permission mode -- read-only tools allowed, mutating actions blocked until the user attaches via `lyra attach`. Lyra is the only system that treats permission mode as a function of watchfulness.

### Layer 6: Behavioral Fingerprint (PRISM)

Daily comparison of recent performance signals against a rolling baseline:

| Level | Degradation | Action |
|---|---|---|
| NONE | < 5% | No action |
| WARNING | 5-15% | Schedule optimization |
| CRITICAL | > 15% | Rollback + alert |

---

## Permission Modes by Use Case

| Use Case | Recommended Mode | Why |
|---|---|---|
| Exploring a new codebase | plan | Read-only safe, no accidental writes |
| Normal daily development | auto-edit | Good balance (89% satisfaction) |
| Automated CI pipeline | bypass | Pre-approved operations |
| Unattended research | plan (falls to ask) | No write access unprompted |
| Testing destructive operations | auto-edit | Gate still catches rm -rf / sudo |

---

## The Audit Trail

Every safety decision across all layers is recorded in an append-only Ed25519-signed, SHA-256 hash-chained audit log. Retention: 90 days, rotated daily. Verify chain integrity with:

```bash
lyra audit verify-chain
```

This gives you cryptographic proof of what was decided and when -- no tampering possible without breaking the hash chain.

---

## Related Docs

- [Architecture: Safety and Security](../architecture/08-safety-security.md) -- full 6-layer defense, CaMeL, Progent
- [Block: Permission Bridge](../blocks/05-permission-bridge.md) -- PermissionStack, risk classification
- [Block: Safety Monitor](../blocks/12-safety-monitor.md) -- circuit breakers, behavioral monitoring
- [Concept: Permission Bridge](../concepts/09-permission-bridge.md) -- mode selection, approval gate
- [Guide: Skills and Evolution](03-skills-and-evolution.md) -- Misevolve safety gates
- [Guide: Fleet Orchestration](04-fleet-orchestration.md) -- subagent permissions, collusion detection

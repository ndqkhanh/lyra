# Safety Monitor -- How It Works

> Seven-layer defense-in-depth architecture. Parallax cognitive-executive separation achieves 98.9% block rate. AgentShield provides 5 scanners with 102 rules. Behavioral fingerprinting detects compromise in a 16-call window at 86% accuracy. PRISM drift detection catches policy drift over time.
> **Block:** 12 | **Phase:** 3 (Multi-Agent & Memory) | **Depends on:** Agent Loop, Permission Bridge, Hooks

## Seven-Layer Defense-in-Depth

Safety is not a single check -- it is seven independent layers with different detection mechanisms, false-positive profiles, and bypass surfaces. An attacker must defeat all seven to succeed:

```
Layer 1: Prompt Guard         [Input filtering: DeBERTa 86M + NeMo Colang]
Layer 2: Schema Gating        [Policy validation: Progent SMT + Z3 solver]
Layer 3: Runtime Approval     [Goal consistency: AlignmentCheck + Rogue Agent Monitor]
Layer 4: Tool Validation      [Output scanning: CodeShield static analysis]
Layer 5: Lifecycle Hooks      [Evolution safety: Misevolve + Collusion Detector]
Layer 6: Behavioral Fingerprint [Anomaly detection: 16-call window]
Layer 7: PRISM Drift          [Policy compliance: time-series drift detection]
```

Combined Attack Success Rate (ASR) on AgentDojo benchmark: 39.9% (no defense) -> 1.75% (all 7 layers).

### Layer 1: Prompt Guard

PromptGuard 2 DeBERTa (86M parameters, AUC 0.995, <20ms inference) filters prompt injections at the input boundary. NeMo Colang dialogue manager adds dialogue-level policy enforcement (99% harmful content block, 2% false positive rate).

### Layer 2: Schema Gating (Progent SMT)

Uses a Z3 SMT solver for monotonic confinement of policy updates. When an agent proposes a policy change, the solver checks whether the change is an **expansion** (new capabilities, needs human approval, 6% of cases) or a **narrowing** (restricting capabilities, auto-approved, 94% of cases).

ASR drops from 39.9% to 1.0% -- a 97.5% reduction in policy violations. Only 6% of updates require human review.

### Layer 3: Runtime Approval

AlignmentCheck uses chain-of-thought goal verification (83% recall at 2.5% FPR). Rogue Agent Monitor predicts action divergences by comparing the agent's planned action against the expected action distribution (ToolEmu, arXiv:2307.13854).

### Layer 4: Tool Validation (CodeShield)

Static analysis scans tool outputs for vulnerabilities (96% precision, 79% recall, 50+ CWE categories). A mutation gate detects test-drift patterns (commented-out assertions, disabled benchmarks).

### Layer 5: Lifecycle Hooks (Misevolve)

Five-gate pipeline: dependency integrity check, test coverage gate, refusal rate monitor, behavioral regression test, and collusion scan. Without Misevolve, refusal rate drops from 99.4% to 54.4% after self-evolution. With it, degradation is held to <5%.

## Parallax Cognitive-Executive Separation (98.9% Block)

Parallax separates the agent into two independent subsystems:

```
Cognitive Subsystem:  LLM reasoning, planning, strategy generation
    (CANNOT execute tools directly)
         │
         │ (proposed actions via structured channel)
         v
Executive Subsystem:  Tool dispatch, filesystem access, network calls
    (CANNOT generate plans or reason about strategy)
```

Any action that requires both reasoning AND tool execution must cross the cognitive-executive boundary via a structured, auditable channel. The executive cannot reason; the cognitive cannot touch.

This separation achieves a **98.9% block rate** against known attack types (prompt injection jailbreaks, tool call smuggling, policy bypass). The 1.1% failure rate is addressed by the outer layers.

## AgentShield (5 Scanners, 102 Rules)

A comprehensive rule engine with five specialized scanners:

| Scanner | Rules | Detects |
|---------|-------|---------|
| Injection | 25 rules | Prompt injection, delimiter smuggling, role-play attacks |
| Sabotage | 20 rules | Commented-out assertions, disabled tests, coverage bypass |
| Secrets | 30 rules | AWS keys, GitHub PATs, SSH keys, API tokens, bearer tokens |
| Policy | 17 rules | Mode violations, disallowed tool combinations, scope breaches |
| Anomaly | 10 rules | Unusual command patterns, frequency spikes, timing anomalies |

Total: **102 rules** across 5 scanners. Each rule has a confidence score (0.0-1.0) and maps to a severity level (info/warning/critical).

## Behavioral Fingerprint (16-Call Window)

The behavioral fingerprint module tracks agent activity in a 16-call sliding window and compares it against a learned baseline:

```python
class BehavioralFingerprint:
    def __init__(self):
        self.window = deque(maxlen=16)
        self.baseline = self._load_baseline()

    def observe(self, call: ToolCall) -> float:
        self.window.append(call)
        if len(self.window) < 16:
            return 0.0
        fingerprint = self._compute_fingerprint(self.window)
        anomaly_score = self._divergence(fingerprint, self.baseline)
        return anomaly_score  # >0.8 = likely compromised
```

Features: tool type distribution, argument length, inter-call timing, file path patterns, error rate. Anomaly score >0.8 triggers a compromise alert.

Detection accuracy on known compromise scenarios: **86%** at 5% false positive rate.

## PRISM Drift Detection

PRISM (Policy-Regularized Integrity Safety Monitor) tracks policy compliance over time using time-series analysis:

- Drift in refusal rate (expected: >99%, alert if <95%)
- Drift in tool type distribution (expected: ~60% reads, alert if >80% writes)
- Drift in error rate (expected: <5%, alert if >15%)
- Drift in permission block rate (expected: <1%, alert if >5%)

PRISM computes a rolling 7-day compliance score and alerts when any dimension drifts beyond 2 standard deviations from the baseline. This catches slow policy erosion that point-in-time checks miss.

## Performance

| Layer | Latency | Cost | ASR Reduction |
|-------|---------|------|---------------|
| Prompt Guard (DeBERTa) | <20ms | $0.000 | 39.9% -> 35% |
| Schema Gating (Z3) | <10ms | $0.000 | 35% -> 1.0% |
| Runtime Approval | 50-200ms | $0.001 | 1.0% -> 1.2% (adds info) |
| Tool Validation | 50-150ms | $0.001 | 1.2% -> 1.5% |
| Lifecycle Hooks | 5-20ms | $0.000 | 1.5% -> 1.75% |
| Behavioral Fingerprint | <1ms | $0.000 | Advisory |
| PRISM Drift | <1ms | $0.000 | Advisory |
| **Combined** | **~200ms** | **~$0.002** | **39.9% -> 1.75%** |

## Related Documents

- **Concepts:** [Safety Monitor](../concepts/11-safety-monitor.md), [Permission Bridge](../concepts/09-permission-bridge.md), [Agent Loop](../concepts/01-agent-loop.md)
- **Architecture:** [Safety and Security](../architecture/08-safety-security.md), [Architecture Overview](../architecture/11-architecture-overview.md), [Gap Analysis](../architecture/13-gap-analysis.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Permission Bridge](05-permission-bridge.md), [Hooks and TDD Gate](06-hooks-tdd.md), [Verifier](10-verifier.md)

---

*References: Parallax (arXiv:2604.12986), AgentDojo (arXiv:2410.03936), SWE-agent Sentinel (arXiv:2405.15793), Constitutional AI (arXiv:2212.08073), NeMo Guardrails (arXiv:2312.15863), ToolEmu (arXiv:2307.13854)*

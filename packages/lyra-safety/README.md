# lyra-safety — 4-Layer Defense-in-Depth

Safety guardrails with explicit failure modes per layer.

| Layer | Pattern | Fail Mode |
|-------|---------|-----------|
| 1 — Input Guard | LlamaFirewall (prompt injection + PII) | fail-CLOSED |
| 2 — CaMeL | Control/data separation | fail-CLOSED |
| 3 — NeMo | Programmable runtime rails | fail-OPEN |
| 4 — Progent | Least-privilege tool control | fail-CLOSED |

Plus: EvolutionSafetyGate (5-gate pipeline), MisevolveDefense (drift detection + rollback).

[Plan: plans/16-safety-alignment.md](../../lyra-upgrade/plans/16-safety-alignment.md)

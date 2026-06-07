# Harness Engineering: 5-Pillar Discipline for AI-Native Development
> **Status:** ✅ Implemented (cross-cutting) | [Plan](../lyra-upgrade/plans/26-harness-engineering.md)

## Abstract
Harness Engineering is the meta-discipline that makes Lyra's agents effective. Five pillars: (1) Context Engineering (compaction, memory, tool clearing — "less is more"), (2) Evaluation Infrastructure (capability evals + regression evals + continuous refresh), (3) Safety Architecture (5-layer defense-in-depth), (4) Methodology (spec-first, TDD, adversarial review), (5) Platform Prerequisites (CI/CD + IaC + observability). These pillars are not features — they are the substrate every feature builds on. The harness, not the model, determines agent reliability (OpenJarvis: 25-39pp drop from model swap alone, recovered by harness optimization).

## Method
Cross-cutting across all 37 modules. Each pillar is enforced through: hooks (safety checks), STRUCTURE.md conventions (methodology), CI pipeline (platform), DEBATE_LEDGER.md (architecture governance), and the build loop (spec→debate→test→build→verify→review→merge).

## Conclusion
All 5 pillars active. The harness is the product. Future: automated harness-quality scoring (pinchbench-style), continuous harness regression testing.

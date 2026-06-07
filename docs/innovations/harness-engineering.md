# Harness Engineering: 5-Pillar Discipline for AI-Native Development
> **Status:** ✅ Implemented (cross-cutting) | [Plan](../lyra-upgrade/plans/26-harness-engineering.md)

## Abstract
Harness Engineering is the meta-discipline that makes Lyra's agents effective. Five pillars: (1) Context Engineering (compaction, memory, tool clearing — "less is more"), (2) Evaluation Infrastructure (capability evals + regression evals + continuous refresh), (3) Safety Architecture (5-layer defense-in-depth), (4) Methodology (spec-first, TDD, adversarial review), (5) Platform Prerequisites (CI/CD + IaC + observability). These pillars are not features — they are the substrate every feature builds on. The harness, not the model, determines agent reliability (OpenJarvis: 25-39pp drop from model swap alone, recovered by harness optimization).

## Method
Cross-cutting across all 37 modules. Each pillar is enforced through: hooks (safety checks), STRUCTURE.md conventions (methodology), CI pipeline (platform), DEBATE_LEDGER.md (architecture governance), and the build loop (spec→debate→test→build→verify→review→merge).

## Working Flow

Every time Lyra is about to run a tool or generate a response, the harness runs a governance pipeline — a series of checks and transformations that happen automatically before the agent sees the result. This isn't a feature you toggle; it's the operating system that every Lyra module runs on top of.

**Example:** You tell Lyra "generate a revenue report."

1. **Safety layer** (Pillar 3) intercepts the request first — does it ask to access financial data? The PermissionGuard checks the scope. If it needs a database credential, the SecretScanner (Pillar 5) verifies the connection string is not hardcoded.
2. **Context Engineering** (Pillar 1) compacts the conversation history via `src/optimization/token_optimizer.py`, trimming irrelevant turns so the model stays within its context window.
3. Lyra calls a Python tool to query the database. **Evaluation Infrastructure** (Pillar 2) logs the tool input/output as an eval sample for regression testing later.
4. The result comes back. **Methodology** (Pillar 4) requires the debate ledger check: was this design debated? If not, the harness flags it for review.

## Use Cases

**Scenario 1: Building a new agent from scratch with governance.** A platform team is creating a custom agent for internal code review. Instead of bolting on safety and evaluation after the fact, they use Lyra's harness as their starting template. The safety pillar gives them PermissionGuard for file access and SecretScanner for credential leaks out of the box. The evaluation pillar records every review session as a regression test case. The methodology pillar enforces spec-first design through the debate ledger. Result: a production-ready agent in days, not months, with governance baked in from day one.

**Scenario 2: Enterprise compliance audit trail.** A regulated company needs to prove that its AI agents never access PII or modify production data without approval. Harness Engineering's 5-pillar architecture makes this auditable. The safety pillar logs every denied permission request. The context engineering pillar shows exactly what data each prompt saw. The CI/CD pillar provides a deploy-time attestation that every agent version passed safety checks. An auditor can trace a single agent action back to its pillar-level decision — without reading source code.

**Scenario 3: Regression-proofing an agent after a model upgrade.** A team swaps their underlying LLM from Sonnet to a fine-tuned model and sees quality drops in 30% of test cases. They run the harness evaluation suite, which compares old vs. new eval results side-by-side. The methodology pillar flags which spec violations caused the regressions. They fix the prompt templates, re-run the suite, and ship with confidence — knowing that the harness will catch the same regressions on the next upgrade.

## Conclusion
All 5 pillars active. The harness is the product. Future: automated harness-quality scoring (pinchbench-style), continuous harness regression testing.

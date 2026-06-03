# Brainstorm — Safety & Alignment (§4.17)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Breakthrough Idea #1: 5-Layer Defense-in-Depth with Provider-Agnostic Guardrails

**Sources Fused:** Anthropic 5-layer safety + Netflix 4-pillar platform + LlamaFirewall + NeMo Guardrails + CaMeL

**Core Mechanism:**
- **Layer 1 — Prompt:** Input sanitization, PromptGuard 2 injection detection, Llama Guard content classification
- **Layer 2 — Schema-Gating:** Tool calls validated against JSON schema before execution; Progent SMT-based monotonic confinement for tool permissions
- **Layer 3 — Runtime Approval:** Permission system (§4.12) gates all mutating actions; unwatched sessions can't use bypass/auto
- **Layer 4 — Tool-Level Validation:** Each tool validates its inputs; dangerous commands detected (rm -rf, curl | bash, sudo); sandbox containment
- **Layer 5 — Lifecycle Hooks:** PreToolUse + PostToolUse hooks inspect/modify/block tool calls; exit code 2 stops agent

**Why Provider-Agnostic:** All 5 layers are harness-level — they work regardless of which LLM backend is active. Provider-specific safety features (Claude's constitutional AI) are bonuses, not dependencies.

**Impact:** 5 | **Effort:** 5 | **Risk:** Low (architecture) / High (implementation)

---

## Breakthrough Idea #2: Self-Evolution Safety Validator ("Misevolve" Gate)

**Sources Fused:** "Misevolve" (2509.26354) + GEPA + MetaAgent-X

**Core Mechanism:**
- Any self-evolved artifact (skill, agent config, memory policy) must pass a SAFETY VALIDATOR before promotion:
  1. **Refusal Rate Check:** Does the evolved skill reduce the agent's refusal rate on harmful requests? (target: no degradation from baseline)
  2. **Tool Vulnerability Check:** Does the evolved skill introduce new tool misuse patterns? (target: no new vulnerabilities)
  3. **Alignment Check:** Does the evolved skill maintain alignment on the LLM Honesty Survey benchmark?
  4. **Sandbox Test:** Run the evolved skill in a sandbox on 100 adversarial prompts — any failures = rejection
- The validator itself is a SEPARATE model (not the same model that did the evolution) to avoid self-assessment bias
- Human-in-the-loop for harness-level changes (DGM-style code rewrites)

**Impact:** 5 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #3: Collusion-Resistant Channel Architecture

**Sources Fused:** Lying-with-Truths (2601.01685) + Identity Skews Anonymization (2510.07517) + CaMeL data/control separation

**Core Mechanism:**
- Channels between agents have MANDATORY monitoring — every message is logged and analyzed
- Collusion detection: scan for Writer-Editor-Director patterns (sequential truthful evidence fragments that collectively steer beliefs)
- Anonymized channels: agents see content but not source identity (prevents identity-weighted influence)
- CaMeL-inspired separation: control-plane messages (task assignments, permissions) use separate authenticated channels from data-plane messages (findings, evidence)
- When collusion likelihood exceeds threshold → flag, isolate agents, re-run with different agent pool
- Never auto-block on collusion suspicion — always log + flag for human review first (false positive risk)

**Impact:** 4 | **Effort:** 4 | **Risk:** Medium

---

## Expert Check

**Senior Security Engineer:** "Idea #2 (safety validator) is the most important and the hardest. 'Misevolve' shows concrete degradation — without this gate, self-evolution WILL reduce safety. The validator must be a separate model and its results must be reviewable."

**Senior AI Safety Engineer:** "Layer 4 (tool-level validation) is where most real-world failures happen. An agent with Bash access can do enormous damage even with perfect prompt-level safety. The tool sandbox is the last line of defense and should be the most hardened."

**Adversarial Skeptic:** "5-layer defense-in-depth sounds thorough but each layer adds latency and complexity. What's the measurable safety improvement over just Layer 3 (runtime approval) + Layer 4 (tool sandbox)? Prove each additional layer earns its cost with concrete ASR reduction numbers."

**Resolution:** Start with Layers 3+4 (runtime approval + tool sandbox) as the minimum viable safety. Add Layers 1+2+5 as evals show they reduce ASR beyond the baseline. The safety validator (Idea #2) is the (B) breakthrough — mandatory before any self-evolution ships.

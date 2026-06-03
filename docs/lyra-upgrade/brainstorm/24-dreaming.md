# Brainstorm — Memory Consolidation / Dreaming (§4.24)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Source Techniques Gathered

| Technique | Source | Core Idea | Key Numbers |
|-----------|--------|-----------|-------------|
| Anthropic Dreaming | Anthropic (May 2026) | LLM reviews 100 past conversations, reorganizes memory | ~6× task completion |
| LightMem Sleep-Time | LightMem (ICLR 2026) | Bio-inspired sensory→short→long consolidation | 105× token reduction, 309× fewer API calls |
| MetaClaw Idle Fine-Tuning | (2603.17187) | Opportunistic LoRA during user-inactive windows | Zero downtime |
| Conway Always-On | Anthropic | Memory Files + Dreams + Runtime loop | — |
| Field-Theoretic PDE | Mitra (2602.21220) | Continuous PDE-governed memory consolidation | +116% F1 LongMemEval |

---

## Breakthrough Idea #1: LLM-Based Dreaming with Review-Before-Accept

**Sources Fused:** Anthropic Dreaming + Memory Files + Conway always-on loop

**Core Mechanism:**
1. **Trigger:** Idle for N minutes (configurable, default 30) AND ≥M new conversations since last dream (default 5)
2. **Review:** Cheap model (Haiku-class) scans past conversations for memory-worthy content
3. **Draft:** Expensive model produces reorganized memory bank:
   - Merge duplicates (same fact remembered twice → one entry with combined evidence)
   - Replace outdated (contradictory newer info → update old entry, mark as superseded)
   - Resolve contradictions (flag conflicting memories for human review)
   - Surface cross-session patterns ("you've asked about X in 4 of the last 6 sessions")
4. **Review Gate:** Output is reviewable — user sees a diff of proposed changes before accepting
5. **Original Preservation:** Never modifies originals — changes are a new revision layer
6. **Frequency:** Configurable; streamable for live review during long sessions

**Why It Beats Baseline:** Lyra has MemoryConsolidator with basic merge_similar — no cross-session pattern detection, no dedup, no review gate.
**Impact:** 5 | **Effort:** 4 | **Risk:** Low

---

## Breakthrough Idea #2: Field-Theoretic PDE Consolidation (B-Tier Breakthrough)

**Sources Fused:** Mitra field theory + A-MAC admission control + LightMem bio-inspired timing

**Core Mechanism:**
- Treat all memories as a continuous field in semantic space governed by PDEs:
  - ∂m/∂t = D·∇²m (diffusion: similar memories attract) − λ·(1−I)·m (decay: low-importance fade) + κ·coupling (cross-agent alignment)
- Run numerical PDE solver during idle (sparse grid, finite difference methods)
- Field evolution discovers latent connections, merge candidates, forget candidates
- A-MAC admission gates what enters the field
- Result: consolidated memory graph with discovered cross-session patterns

**Trade-off:** More powerful consolidation vs more complex infrastructure. Gated behind bake-off vs LLM-based dreaming (Idea #1).

**Impact:** 5 | **Effort:** 5 | **Risk:** High

---

## Breakthrough Idea #3: Conway-Style Always-On Memory Loop

**Sources Fused:** Conway + MetaClaw opportunistic fine-tuning + Anthropic Memory Files

**Core Mechanism:**
- Three components running in a perpetual background loop:
  1. **Memory Files (Storage):** Topic/project/context-organized file system memory. Wiki-like user control. Selective reading vs single rolling summary.
  2. **Dreams (Maintenance):** During idle, review → dedup → reorganize → surface patterns
  3. **Runtime (Action):** Conway daemon monitors memory freshness, triggers re-indexing, handles invalidation
- MetaClaw integration: during user-inactive windows, opportunistically fine-tune LoRA adapters on recent successful trajectories
- The loop runs as a low-priority background process, never blocking the main agent

**Why It Beats Baseline:** Lyra has no always-on memory maintenance.
**Impact:** 4 | **Effort:** 5 | **Risk:** Medium

---

## Expert Check

**Senior AI Researcher:** "The LLM-based dreaming (Idea #1) is the practical starting point. It's what Anthropic actually shipped. The field-theoretic approach (Idea #2) is more elegant but unproven. Run both, measure both, ship the winner."

**Senior SRE:** "The 'never modifies originals' principle in Idea #1 is critical. Dreaming that silently corrupts memory is worse than no dreaming. The review gate is the safety mechanism."

**Adversarial Skeptic:** "Harvey's ~6× improvement is impressive but Harvey is a legal AI with highly repetitive tasks. Will dreaming show similar gains for a general-purpose coding/research agent? Measure Lyra-specific dreaming impact before making it always-on."

**Resolution:** LLM-based dreaming (Idea #1) is the (A) parity tier. Field-theoretic (Idea #2) is the (B) breakthrough — gated behind bake-off. Conway loop (Idea #3) is Phase 4 polish. The Skeptic's concern is valid — measure dreaming impact on Lyra-specific tasks before enabling by default.

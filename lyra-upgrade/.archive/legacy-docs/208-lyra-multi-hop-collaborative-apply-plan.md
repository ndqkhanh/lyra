# 208 — Lyra Apply Plan: Multi-Hop + Collaborative-AI Techniques into the CLI Coding Harness

> **Disambiguation.** This file is the **Lyra-specific** deep apply plan, extending the [203-polaris-multi-hop-reasoning-apply-plan](203-polaris-multi-hop-reasoning-apply-plan.md) pattern from Polaris to Lyra. The cross-project matrix is in [207-cross-project-collaborative-multi-hop-apply-plan](207-cross-project-collaborative-multi-hop-apply-plan.md); the multi-hop block is [198-multi-hop-qa-datasets-canon](198-multi-hop-qa-datasets-canon.md) → [202-multi-agent-multi-hop-reckoning-2026](202-multi-agent-multi-hop-reckoning-2026.md); the collaborative-AI block is [204-metagpt-foundationagents-2026-refresh](204-metagpt-foundationagents-2026-refresh.md) → [206-collaborative-ai-canon-2026](206-collaborative-ai-canon-2026.md).

## One-line definition

A staged plan to fold multi-hop reasoning + collaborative-AI techniques into Lyra — the **Lightweight Yielding Reasoning Agent**, a CLI-native general-purpose coding harness with `lyra-cli`, `lyra-core` (kernel + agent loop + tools + hooks + 5-layer context + procedural memory + skill loader + subagent orchestrator + optional TDD plugin), `lyra-evals`, `lyra-mcp`, and `lyra-skills` packages — without breaking its CLI-first identity, two-tier model split (`fast`/`smart`), 16-provider factory, or Argus integration ([LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md](../projects/lyra/LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md)).

## §1 — Why apply these techniques to Lyra

Lyra's existing strengths are clear: a polished CLI, four-mode router (`agent`/`plan`/`debug`/`ask`), 80+ slash commands, NGC-aware 5-layer context compactor, SQLite-FTS5 procedural memory, SKILL.md loader, subagent orchestrator with git worktrees + 3-way merge, and a published Argus integration plan (V3.8). What it lacks, relative to the [206-collaborative-ai-canon-2026](206-collaborative-ai-canon-2026.md) maturity matrix, is:

- **Multi-hop substrate for code-search** — Lyra's `Grep`/`Read`/`Glob` triad is single-hop by design. Cross-file refactors and "why is this slow?" investigations are inherently multi-hop and currently delegated to the LLM's parametric memory. Cf. [199-multi-hop-reasoning-techniques-arc](199-multi-hop-reasoning-techniques-arc.md).
- **Typed personal memory (ICPEA)** — Lyra has procedural memory (SQLite FTS5) and 5-layer context, but no typed personal-memory layer for the *user* (preferred libraries, code style, project conventions). Cf. [205-lobehub-collaborative-teammate-platform](205-lobehub-collaborative-teammate-platform.md) §2.1.
- **Branching as alternative-implementation UX** — Lyra's `agent` mode commits, edits, and runs; no built-in fork-and-compare for "show me three implementations of this." Cf. [206-collaborative-ai-canon-2026](206-collaborative-ai-canon-2026.md) §4.
- **Voyager-line skill auto-creation** — Lyra has a SKILL.md loader and Argus integration but no auto-promotion of recurring trajectories into skills. Cf. [167-autoskill-experience-driven-lifelong-learning](167-autoskill-experience-driven-lifelong-learning.md), [171-skill-self-evolution-2026-synthesis](171-skill-self-evolution-2026-synthesis.md).
- **Per-user constitution** — Lyra has 80+ slash commands as an interface but no serialised user-preference object. Cf. [206-collaborative-ai-canon-2026](206-collaborative-ai-canon-2026.md) §5.

Take these gaps seriously and three things change. (1) Lyra graduates from "great CLI coding agent" to "teammate that grows with the developer." (2) Cross-file refactors stop being LLM-parametric guesses and become graph-walked verifiable trajectories. (3) The Argus integration (V3.8) is amplified — Argus provides the trust gate; ICPEA provides the per-user routing signal; together they make skill activation user-aware in a way V3.8 alone doesn't reach.

## §2 — The Lyra × technique mapping table

Each row is one technique, mapped to a Lyra package + module + tier slot.

| Technique | Source | Lyra module | Tier | Effort | Payoff |
|---|---|---|---|---|---|
| **Multi-hop substrate (code-search-shaped)** | | | | | |
| HippoRAG over codebase symbol graph | [200-graph-grounded-multi-hop-retrieval](200-graph-grounded-multi-hop-retrieval.md) | `lyra-core/code_graph/hipporag.py` | 0 | M | Cross-file refactors via single-shot retrieval |
| LightRAG-style incremental ingest on file save | [200](200-graph-grounded-multi-hop-retrieval.md) | `lyra-core/code_graph/incremental.py` | 0 | S | Online graph update without full reindex |
| Tree-sitter symbol graph as the KG substrate | new | `lyra-core/code_graph/tree_sitter_graph.py` | 0 | S | Code-aware extraction |
| Self-Ask / IRCoT for cross-file reasoning | [199](199-multi-hop-reasoning-techniques-arc.md) Phase 1 | `lyra-core/reasoning/{self_ask,ircot}.py` | 0 | S | Externalised chain on multi-file tasks |
| Chain-of-Note per-file filter | [199](199-multi-hop-reasoning-techniques-arc.md) Phase 3 | `lyra-core/gates/chain_of_note.py` | 0 | S | Stops one bad file from poisoning a refactor |
| BELLE question-type router (refactor / debug / explain / generate) | [202](202-multi-agent-multi-hop-reckoning-2026.md) §1 | `lyra-core/routing/code_question_router.py` | 0 | S | Right reasoning method per task shape |
| DSPy multi-hop program for SWE-bench-style tasks | [199](199-multi-hop-reasoning-techniques-arc.md) Phase 2 | `lyra-skills/research/dspy_swe_program.py` | 1 | M | Compiled-against-evals beats hand-prompted |
| Plan-on-Graph backtracking on call-graph walks | [200](200-graph-grounded-multi-hop-retrieval.md) | `lyra-core/code_graph/plan_walk.py` | 1 | M | Recovers from wrong-path call traversal |
| Reason-in-Documents over retrieved code chunks | [199](199-multi-hop-reasoning-techniques-arc.md) Phase 4 | `lyra-core/reasoning/reason_in_code.py` | 1 | S | Denoise retrieved code before injection |
| Search-R1 RL on a code-grounded reward | [199](199-multi-hop-reasoning-techniques-arc.md) Phase 4 | `lyra-research/rl/search_r1_code.py` | 2 | L | Trained code-search policy beats prompted |
| **Collaborative-AI substrate** | | | | | |
| ICPEA five-layer personal memory | [205](205-lobehub-collaborative-teammate-platform.md) §2.1, [206](206-collaborative-ai-canon-2026.md) §1 | `lyra-core/memory/icpea/` (alongside existing procedural memory) | 0 | M | User-aware routing + per-project conventions |
| Async memory extractor on session close | [206](206-collaborative-ai-canon-2026.md) §1 | `lyra-core/memory/icpea/extractor.py` | 0 | S | Decouples memory write from chat latency |
| Per-agent layer access control | [205](205-lobehub-collaborative-teammate-platform.md) §2.1 | `lyra-core/memory/icpea/access.py` | 1 | S | TDD subagent sees Preference, not Identity |
| Branching as alternative-implementation UX | [206](206-collaborative-ai-canon-2026.md) §4 | `lyra-cli/branching/` | 1 | M | "Show 3 ways to do this" with git-worktree branches |
| Lobe Pages-style co-authored design doc | [205](205-lobehub-collaborative-teammate-platform.md) §2.2 | `lyra-cli/pages/` | 1 | M | Co-authored markdown surface with timeline |
| MCP-first marketplace + Argus trust gate | [205](205-lobehub-collaborative-teammate-platform.md) §2.3, V3.8 | `lyra-mcp/marketplace.py` (consuming `argus.HostAdapter`) | 1 | S | Trust-gated tool installation |
| Voyager-line skill auto-creation | [167](167-autoskill-experience-driven-lifelong-learning.md), [171](171-skill-self-evolution-2026-synthesis.md), V3.9 | `lyra-skills/auto_creator/` (consuming Argus curator) | 1 | M | Successful trajectories become reusable skills |
| Per-user constitution (ICAI/C3AI) | [206](206-collaborative-ai-canon-2026.md) §5 | `lyra-core/constitution/` | 2 | M | Serialised user-style preference object |
| **Cross-cutting discipline** | | | | | |
| Pure-function agents | [202](202-multi-agent-multi-hop-reckoning-2026.md) §4 | `lyra-core/loop/pure_function_agent.py` | 0 | S | Replayable trajectories for git-worktree subagents |
| Equal-budget benchmark harness | [202](202-multi-agent-multi-hop-reckoning-2026.md) §3 | `lyra-evals/equal_budget.py` | 0 | S | Settles single-vs-multi-agent debates honestly |
| TTC curve plotter | [199](199-multi-hop-reasoning-techniques-arc.md) | `lyra-evals/ttc_curve.py` | 0 | S | Detect plateau-or-decline on noisy retrievals |
| MuSiQue-Full + FRAMES + Seal-0 (code-adapted variants) | [198](198-multi-hop-qa-datasets-canon.md) | `lyra-evals/multi_hop_triple/` | 0 | S | Code-multi-hop regression triple in nightly |
| Decomposition cache | [199](199-multi-hop-reasoning-techniques-arc.md) | `lyra-core/memory/decomposition_cache.py` (next to procedural memory) | 0 | S | Latency cut on repeated sub-queries |

## §3 — Tier 0 (days 1-14): the multi-hop + ICPEA hardening surface

The cheapest, highest-payoff lifts. All compose with Lyra's existing `lyra-core` kernel without touching `lyra-cli`'s 4-mode router.

### 0.1 — HippoRAG over a tree-sitter symbol graph

**File.** `lyra-core/code_graph/{tree_sitter_graph,hipporag,incremental}.py`

**What.** A code-aware HippoRAG. At ingest, walk the codebase with **tree-sitter** to extract a typed symbol graph (functions, classes, methods, callers, imports). Run **Personalized PageRank** on the graph using query concepts (function names, error messages, file paths) as seeds. At query time, return multi-hop-coherent code passages in a single retrieval pass.

**Integration with existing Lyra surface.**

- **5-layer context.** HippoRAG-retrieved passages enter the `code` layer; the existing NGC compactor handles them as it would any other code blob.
- **`Grep`/`Read`/`Glob` tools.** HippoRAG augments — does not replace — these. They remain for cheap single-shot lookups; HippoRAG fires when the query is multi-hop ("the spouse of the director of Casablanca" but for code: "the writer of the function that calls X").
- **Procedural memory (SQLite FTS5).** Procedural memory stays for "I did X yesterday"; HippoRAG indexes the live codebase, not the user's history.

**Why now.** Cross-file refactors are the most common failure mode for single-shot code agents. HippoRAG is the canonical fix; tree-sitter is already a Lyra dependency conceptually (or a small lift to add).

### 0.2 — LightRAG incremental graph ingest

**File.** `lyra-core/code_graph/incremental.py`

**What.** When the user saves a file, the symbol graph updates incrementally. No full reindex on every change — LightRAG's incremental algorithm ([200](200-graph-grounded-multi-hop-retrieval.md) §2.10) is the right shape.

**Trigger.** Watchman-style filesystem watcher in `lyra-core/code_graph/watch.py`; debounced 250ms.

### 0.3 — BELLE-style code-question router

**File.** `lyra-core/routing/code_question_router.py`

**What.** A small classifier (prompted + few-shot to start) that types incoming queries into:
- **Refactor** — multi-file, structural — needs HippoRAG + Plan-on-Graph.
- **Debug** — trace-following, exception-driven — needs IRCoT + Reason-in-Documents.
- **Explain** — read-and-summarise — needs single-shot retrieval + Chain-of-Note.
- **Generate** — emit new code — needs procedural memory + skill library.

**Why this not full debate.** Tran & Kiela ([202-multi-agent-multi-hop-reckoning-2026](202-multi-agent-multi-hop-reckoning-2026.md) §3): debate doesn't beat single-agent under equal budget. The router is the cheap part of BELLE; defer the bi-level monitor to Tier 1.

### 0.4 — Self-Ask / IRCoT for cross-file reasoning

**File.** `lyra-core/reasoning/{self_ask,ircot}.py`

**What.** Two operator skills exposing externalised-chain patterns from [199-multi-hop-reasoning-techniques-arc](199-multi-hop-reasoning-techniques-arc.md) Phase 1. **The compositionality gap from [201](201-compositionality-gap-canon.md) is the formal justification** — never let a multi-hop code question execute without the chain materialised as tokens. Each emitted sub-question becomes a `lyra-cli` status-bar entry the user can interrupt.

### 0.5 — Chain-of-Note per-file filter

**File.** `lyra-core/gates/chain_of_note.py`

**What.** After HippoRAG retrieval, the LM writes a per-file note assessing relevance to the current task. Files scored irrelevant are dropped before reasoning. Becomes a hook-style gate in Lyra's existing hook lifecycle ([05-hooks](05-hooks.md), Lyra's `Hooks` module).

### 0.6 — ICPEA five-layer personal memory

**File.** `lyra-core/memory/icpea/{layers,extractor,injection}.py`

**What.** Adopt the ICPEA schema verbatim from [205-lobehub-collaborative-teammate-platform](205-lobehub-collaborative-teammate-platform.md) §2.1.

For Lyra specifically the layers map to:
- **I**dentity — "I'm a senior backend engineer working on a Python monorepo with strict typing."
- **C**ontext — current project, branch, recent files.
- **P**reference — preferred libraries (`httpx` over `requests`), code style (4-space, type hints required), test framework (`pytest`), commit-message format.
- **E**xperience — what worked (refactor patterns that the user accepted), what failed (subagent strategies the user rolled back).
- **A**ctivity — tool invocations, edited files, slash commands used.

**Async extractor.** Triggers on session close (lyra-cli exit). Reads the procedural memory + tool log, extracts ICPEA rows, validates, inserts.

**Injection.** Per-mode budget — `agent` mode injects all five layers; `ask` mode injects only Identity + Preference; `debug` mode injects Context + Activity heavily.

### 0.7 — Multi-hop benchmark triple in `lyra-evals`

**File.** `lyra-evals/multi_hop_triple/{musique_code,frames_code,seal0_code}/`

**What.** Code-adapted variants of MuSiQue-Full + FRAMES + Seal-0:
- **MuSiQue-Code** — synthesise multi-hop questions from real codebases (cross-file refactor, where-does-this-error-come-from).
- **FRAMES-Code** — multi-hop with citation accuracy (the function definition + call site + test must all be retrieved).
- **Seal-0-Code** — adversarial retrievals (similarly-named functions in different modules).

Run nightly; alarm on regression.

### 0.8 — Pure-function agents + equal-budget + TTC curve

**File.** `lyra-core/loop/pure_function_agent.py`, `lyra-evals/{equal_budget,ttc_curve}.py`

**What.** Cross-cutting discipline (cf. [203-polaris-multi-hop-reasoning-apply-plan](203-polaris-multi-hop-reasoning-apply-plan.md) §3). Critical for Lyra's git-worktree subagent orchestrator: a non-deterministic subagent can't be 3-way-merged reliably.

### 0.9 — Decomposition cache

**File.** `lyra-core/memory/decomposition_cache.py` (next to existing SQLite FTS5 procedural memory)

**What.** Memoise sub-question decompositions keyed by normalised question + project. Reuse on recurring queries. Sub-second hit time.

## §4 — Tier 1 (days 15-45): the architecture surface

After Tier 0, the multi-hop substrate is in place. Tier 1 makes the executor *user-aware* and exposes branching/Pages UX.

### 1.1 — DSPy multi-hop program for code

**File.** `lyra-skills/research/dspy_swe_program.py`

**What.** Compose Tier 0's operators into a DSPy `Module`. The DSPy compiler bootstraps few-shot demonstrations against held-out evals (MuSiQue-Code, FRAMES-Code) and produces a versioned, optimised program checked into `lyra-skills/`. Compiles nightly.

### 1.2 — Plan-on-Graph backtracking on call-graph walks

**File.** `lyra-core/code_graph/plan_walk.py`

**What.** Adopt PoG ([200](200-graph-grounded-multi-hop-retrieval.md) §"Plan-on-Graph") for any code-graph walk. When the agent wants to find "the function that calls X that handles Y" and the first walk leads to a wrong subgraph, the Reflection mechanism backtracks. The visited subgraph is logged in the procedural memory.

### 1.3 — Reason-in-Documents on retrieved code

**File.** `lyra-core/reasoning/reason_in_code.py`

**What.** Search-o1's denoising step adapted for code. Before injecting a retrieved code chunk into the reasoning context, a separate LM call summarises and filters. Composes orthogonally with Chain-of-Note (different granularity).

### 1.4 — Branching as alternative-implementation UX

**File.** `lyra-cli/branching/{tree,fork,compare}.py`

**What.** Adopt LobeHub's branching pattern at the CLI. Keyboard shortcut (e.g. `Ctrl-B`) to fork from any agent message into a parallel branch. Implementation:
- Each branch gets its own git worktree (Lyra already supports git worktrees for subagents).
- The branch tree is visualised as ASCII art in the Lyra status bar.
- A `/compare` slash command diffs the working trees of two branches.
- Pure-function agents (Tier 0) are non-negotiable — non-deterministic agents can't fork cleanly.

### 1.5 — Lobe Pages-style co-authored design doc

**File.** `lyra-cli/pages/{page,timeline,merge}.py`

**What.** A markdown document where the agent and the user concurrently edit. Notion-style timeline preserves prior versions per source. Shipped as a slash command (`/page architecture.md`) that opens an interactive editor.

### 1.6 — MCP marketplace + Argus trust gate

**File.** `lyra-mcp/marketplace.py` (consumes `argus.HostAdapter` per V3.8)

**What.** LobeHub's one-click MCP install pattern routed through Argus's trust gate. Sequence:
1. User picks an MCP server in the marketplace UI (or `/mcp install <name>`).
2. Argus's `HostAdapter` returns a typed trust verdict.
3. If verdict ≥ threshold, install proceeds; permission negotiation at install (not first use) shows the OAuth scopes.
4. If verdict < threshold, install requires explicit `--force` with a warning.

**Cross-link.** [LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md](../projects/lyra/LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md), [180-argus-skill-router-agent-design](180-argus-skill-router-agent-design.md).

### 1.7 — Voyager-line skill auto-creation

**File.** `lyra-skills/auto_creator/{extract,gate,promote}.py`

**What.** Successful trajectories (test pass + user accept + ≥2 occurrences) are extracted into skill candidates by an LLM-side extractor. Argus's curator (V3.9) gates them via held-out eval and surrogate verifier; promoted skills land in `~/.lyra/skills/auto/`.

**Cross-link.** [LYRA_V3_9_RECURSIVE_CURATOR_PLAN.md](../projects/lyra/LYRA_V3_9_RECURSIVE_CURATOR_PLAN.md), [167-autoskill-experience-driven-lifelong-learning](167-autoskill-experience-driven-lifelong-learning.md), [171-skill-self-evolution-2026-synthesis](171-skill-self-evolution-2026-synthesis.md).

## §5 — Tier 2 (days 46-90): the training surface

### 2.1 — Search-R1 RL on a code-grounded reward

**File.** `lyra-research/rl/search_r1_code.py`

**What.** Fork Search-R1 ([199](199-multi-hop-reasoning-techniques-arc.md) Phase 4) for code. Action tokens `<grep>...</grep>`, `<read>...</read>`, `<answer>...</answer>`. Retrieved-code-token masking. Outcome rewards based on:
- Test pass = +1
- Test fail = penalty
- Edited-file-not-imported-anywhere = penalty (catches "fixed" code that doesn't actually run)
- User-accepted edit (ICPEA Experience layer) = bonus
- User-rolled-back edit = penalty

**Backbone.** Qwen2.5-Coder-7B initial; consider 32B once recipe validates.

### 2.2 — Per-user constitution

**File.** `lyra-core/constitution/{model,inject,update}.py`

**What.** ICAI-style 3-principle constitution per user, derived from edit/rollback patterns over time. Examples for a coding user:
- "Always prefer explicit type hints in Python; reject inference-heavy code."
- "Avoid functions over 40 lines; refactor before exceeding."
- "Default to `httpx` and `pytest`; use library-author conventions when contributing upstream."

Injected in `agent` mode at every turn; surfaced in `/constitution` slash command for inspection and edit.

## §6 — How this maps onto Lyra's V3.x phasing

| Lyra version | Existing scope | This plan adds |
|---|---|---|
| V3.7 | Claude Code parity | (already shipped) |
| V3.8 | Argus integration | + MCP marketplace consumes Argus trust gate (Tier 1) |
| V3.9 | Recursive curator | + Voyager-line skill auto-creator consumes V3.9 curator (Tier 1) |
| V3.10 | Model provider extension | + Search-R1 RL across providers (Tier 2 prerequisite) |
| V3.11 (proposed) | Multi-hop substrate | HippoRAG + LightRAG + DSPy multi-hop + PoG + Reason-in-Code (Tier 0–1) |
| V3.12 (proposed) | Personal memory + branching | ICPEA + branching UX + Pages + per-user constitution (Tier 0–2) |
| V4.0 (proposed) | Trained executor | Search-R1 RL + RAGEN-style stability monitors (Tier 2) |

## §7 — Five sequencing decisions worth defending

### Decision 1 — Tree-sitter symbol graph as the HippoRAG substrate

Pure embedding-based KG extraction over codebases is noisier than tree-sitter's typed symbol graph. The ingest cost is comparable; the query-time precision is materially higher. Reserve LLM-side relation extraction for natural-language docs and comments only.

### Decision 2 — Branching via git worktrees, not in-memory forks

Lyra already uses git worktrees for subagents. Branching as alternative-implementation UX rides the same machinery — each branch is a worktree, the agent can pure-function-execute against it, and the user can `cd` into the branch directory at any time. In-memory branching would be cheaper but loses the "real working tree" property that makes the UX visceral.

### Decision 3 — ICPEA *alongside*, not *replacing*, procedural memory

Procedural memory (SQLite FTS5) is the activity log. ICPEA is the typed personalisation layer. Don't merge — they have different access patterns, different retention policies, and different trust models. The async extractor reads procedural memory and writes ICPEA rows.

### Decision 4 — BELLE *router* without BELLE *debate*

[202-multi-agent-multi-hop-reckoning-2026](202-multi-agent-multi-hop-reckoning-2026.md) §3 (Tran & Kiela) — debate doesn't beat single-agent under equal budget. The router gain is most of BELLE's value at a fraction of the cost. Defer the bi-level monitor to Tier 2 if at all.

### Decision 5 — Search-R1 RL last, not first

Don't train the executor before the gating surface and the multi-hop substrate are in place. Without held-out evals, retrieved-code-token masking, and test-pass-as-reward, RL training reward-hacks the agent into producing confident-looking code that doesn't run.

## §8 — Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Tree-sitter graph misses dynamic dispatch / metaclasses | Med | Med | Hybrid graph: tree-sitter primary + LLM-extracted fallback for dynamic edges |
| HippoRAG ingest cost on monorepos | Med | High | LightRAG-style incremental + lazy ingest of unaccessed subtrees |
| ICPEA cross-contaminates personal data into git history | Low | High | ICPEA stored in `~/.lyra/icpea/`, never in repo; per-project access scoping |
| Branching UX confuses users vs git native branches | Med | Low-Med | Visual differentiation in status bar; `/branch` vs `git checkout` semantics documented |
| Skill auto-creator over-promotes noise | Med | Med | Argus curator gating (V3.9) + 2-occurrence + held-out eval + surrogate verifier |
| Search-R1 reward-hacks tests | Med | High | Test mutation testing in eval pipeline; user-accept signal carries higher weight than test pass |
| MCP marketplace supply-chain attack | Med | High | Argus trust gate before install; sandboxed MCP execution; CVE feed integration |
| Decomposition cache poisons across projects | Low | Med | Cache key includes project root + branch + permissions context |
| Per-user constitution contradicts project conventions | Med | Low-Med | Constitution + project `.lyra/constitution.md` (project-level) compose; project overrides user on conflict |
| Equal-budget benchmarking misrepresents fast/smart split | High | Low-Med | Report per-tier cost separately; document Lyra's two-tier architecture in eval reports |

## §9 — Concrete day-by-day Tier 0 checklist

A 14-day Tier 0 with daily granularity:

- **Day 1-2** — `lyra-core/loop/pure_function_agent.py` base class; refactor existing executor.
- **Day 3** — `lyra-core/code_graph/tree_sitter_graph.py` over a sample monorepo; benchmark ingest time.
- **Day 4-5** — `lyra-core/code_graph/{hipporag,incremental}.py`; first end-to-end multi-hop code retrieval.
- **Day 6** — `lyra-core/routing/code_question_router.py` (prompted + 5-shot).
- **Day 7** — `lyra-core/reasoning/{self_ask,ircot}.py` operators; integrate with status-bar status updates.
- **Day 8** — `lyra-core/gates/chain_of_note.py` as a hook in the existing hook lifecycle.
- **Day 9-10** — `lyra-core/memory/icpea/{layers,extractor,injection}.py`; first session-close extraction.
- **Day 11** — `lyra-core/memory/decomposition_cache.py` next to procedural memory.
- **Day 12** — `lyra-evals/multi_hop_triple/` synthesised from a sample codebase.
- **Day 13** — `lyra-evals/{equal_budget,ttc_curve}.py`.
- **Day 14** — Tier 0 retro: which gates fired most? which question types route most? sign-off for Tier 1.

## §10 — Cross-references

- [203-polaris-multi-hop-reasoning-apply-plan](203-polaris-multi-hop-reasoning-apply-plan.md) — sibling Polaris plan (deep, multi-hop only).
- [207-cross-project-collaborative-multi-hop-apply-plan](207-cross-project-collaborative-multi-hop-apply-plan.md) — cross-project matrix (high-level, all projects).
- [LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md](../projects/lyra/LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md), [LYRA_V3_9_RECURSIVE_CURATOR_PLAN.md](../projects/lyra/LYRA_V3_9_RECURSIVE_CURATOR_PLAN.md), [LYRA_V3_10_MODEL_PROVIDER_EXTENSION_PLAN.md](../projects/lyra/LYRA_V3_10_MODEL_PROVIDER_EXTENSION_PLAN.md) — Lyra's existing roadmap.
- [62-everything-claude-code](62-everything-claude-code.md), [29-dive-into-claude-code](29-dive-into-claude-code.md), [52-dive-into-open-claw](52-dive-into-open-claw.md), [54-semaclaw-general-purpose-agent](54-semaclaw-general-purpose-agent.md) — coding-agent precedents Lyra inherits from.
- [144-build-your-own-harness](144-build-your-own-harness.md), [46-components-of-coding-agent](46-components-of-coding-agent.md), [145-comparing-coding-harnesses](145-comparing-coding-harnesses.md) — coding-harness design lineage.
- [13-react](13-react.md), [14-reflexion](14-reflexion.md), [15-tree-of-thoughts-lats](15-tree-of-thoughts-lats.md) — the agent loop primitives.
- [180-argus-skill-router-agent-design](180-argus-skill-router-agent-design.md), [194-argus-omega-enhanced-design](194-argus-omega-enhanced-design.md), [197-argus-omega-vol-3-recursive-skills-curator](197-argus-omega-vol-3-recursive-skills-curator.md) — Argus integration substrate.

## §11 — One-paragraph summary

Lyra's multi-hop + collaborative-AI subsystem ships in three tiers: Tier 0 (14 days) hardens the code-search surface with a tree-sitter symbol graph + HippoRAG + LightRAG incremental ingest + BELLE code-question router + Self-Ask/IRCoT externalised chains + Chain-of-Note quality gate + ICPEA five-layer personal memory + decomposition cache + multi-hop benchmark triple + pure-function agents; Tier 1 (30 days) makes the executor user-aware with DSPy multi-hop program + Plan-on-Graph backtracking + Reason-in-Code denoiser + branching as alternative-implementation UX (via git worktrees) + Lobe Pages co-authored design doc + MCP marketplace through Argus trust gate + Voyager-line skill auto-creator (consuming V3.9 curator); Tier 2 (60 days) trains the executor with Search-R1 RL on a code-grounded reward + per-user constitution. The five sequencing decisions defended in §7 turn the multi-hop and collaborative-AI literature into a Lyra-shaped roadmap that respects the CLI-first identity, the two-tier model split, the 16-provider factory, and the existing V3.8/V3.9/V3.10 plans.

**The one-line takeaway for harness designers:** Apply multi-hop + collaborative-AI to Lyra by making each technique a `lyra-core` module that *augments* the existing 5-layer context + procedural memory + skill loader + subagent orchestrator — never replaces them — and stage the work so each tier's outputs become the next tier's inputs (multi-hop substrate → user-aware executor → trained policy).

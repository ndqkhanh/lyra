# Imbad0202/academic-research-skills -- Deep-Read

**Repo**: `https://github.com/Imbad0202/academic-research-skills`
**Version**: v3.11.1 (2026-06-06)
**Author**: Cheng-I Wu
**License**: CC BY-NC 4.0 (non-commercial, not open-source)

## 1. Headline Feature & Mechanism

The headline feature is a **multi-agent academic research copilot framework** for Claude Code that orchestrates a complete research-to-publication pipeline through 38 agents across 4 skills and 25 modes, with **deterministic integrity gates** at every stage transition.

**What the code really does:**

1. **4 independent skills, one orchestrator:**
   - `deep-research` (13 agents, 7 modes) -- literature search, evidence synthesis, Socratic mentoring, systematic review, fact-checking.
   - `academic-paper` (12 agents, 10 modes) -- full paper drafting, Style Calibration, citation compliance, LaTeX/DOCX/PDF output, bilingual abstracts.
   - `academic-paper-reviewer` (7 agents, 6 modes) -- EIC + 3 dynamic reviewers + Devil's Advocate, Sprint Contract hard gate, calibration mode.
   - `academic-pipeline` (orchestrator) -- 10-stage state machine that dispatches the three skills with mandatory human checkpoints.

2. **Deterministic citation verification (v3.11, #182):** Cross-checks every cited reference against up to 4 bibliographic indexes (Semantic Scholar + OpenAlex + Crossref + arXiv) via API calls (not LLM). Persistent SQLite cache (90-day TTL) avoids redundant lookups. Default advisory; opt-in `terminal_policies.citation_existence == strict` makes failures terminal. A `lookup_verified == false` is narrowed to ID-keyed unmatched only (e.g., a specific DOI lookup that provably fails), so legitimate unindexed citations (humanities, regional) stay `unresolvable` and never block.

3. **L3 claim-faithfulness audit (v3.8, opt-in via `ARS_CLAIM_AUDIT=1`):** After the citation finalizer and before the formatter hard gate, a standalone LLM-as-judge fetches each cited source against its locator anchor and judges whether the claim is actually supported. Emits 5 HIGH-WARN annotation classes; the formatter REFUSE rules 6-10 gate-refuse output on any unresolved HIGH-WARN.

4. **Cross-index triangulation (v3.9-v3.11):** Advisory contamination signals across 4 indexes with 4 tiers of advisory severity, plus a terminal policy layer (`strict`, `strict_articles_only`) that can block output on triangulation failure.

5. **Material Passport**: A YAML-based serializable artifact ledger that tracks every claim, citation, decision, and integrity result throughout the pipeline. Enables cross-session resume, audit trails, and context-reset boundaries.

**How it really works:** The entire framework is prompt-engineered. The "agents" are not separate processes or microservices -- they are structured Markdown prompt templates (`.md` files) with frontmatter metadata, each defining a specific agent's role, rules, phase boundaries, and output format. The "pipeline" is a conversation state machine executed within a single Claude Code session. The "deterministic" verification is done by Python scripts (`scripts/arxiv_client.py`, `scripts/verification_cache.py`, `scripts/contamination_signals.py`) called from the prompt context. The L3 audit uses LLM-as-judge with structured schema validation. CI enforcement is through ~30 Python lint scripts wired into 10 GitHub Actions workflows.

## 2. Architecture & Core Modules

**Top-level entry points:**

| Path | Purpose |
|------|---------|
| `deep-research/SKILL.md` | 13-agent research team; 7 modes |
| `academic-paper/SKILL.md` | 12-agent paper writing; 10 modes |
| `academic-paper-reviewer/SKILL.md` | 7-agent multi-perspective review; 6 modes |
| `academic-pipeline/SKILL.md` | 10-stage orchestrator; coordinates all above |
| `commands/ars-*.md` | 14 slash commands for Claude Code plugin routing |
| `agents/` | 3 symlinks to downstream agents for plugin dispatch |
| `scripts/*.py` | ~30 Python verification/CI/lint scripts |
| `.claude-plugin/plugin.json` | Plugin manifest |
| `shared/` | Cross-skill contracts, schemas, protocols, patterns |

**Agent architecture (all 38 agents are Markdown prompt templates):**

- `deep-research/agents/` (13): research_question, research_architect, bibliography, source_verification, synthesis, report_compiler, editor_in_chief, devils_advocate, ethics_review, socratic_mentor, risk_of_bias, meta_analysis, monitoring, timeline_extraction
- `academic-paper/agents/` (12): intake, literature_strategist, structure_architect, argument_builder, draft_writer, citation_compliance, abstract_bilingual, peer_reviewer, formatter, socratic_mentor, visualization, revision_coach
- `academic-paper-reviewer/agents/` (7): field_analyst, eic, methodology_reviewer, domain_reviewer, perspective_reviewer, devils_advocate_reviewer, editorial_synthesizer
- `academic-pipeline/agents/` (5): pipeline_orchestrator, integrity_verification, state_tracker, collaboration_depth, claim_ref_alignment_audit

**Data flow pattern:**

```
User Input (RAW)
  --> deep-research [data_access_level: raw]
    --> source_verification elevates to REDACTED
      --> academic-paper [data_access_level: redacted]
        --> Gate 2.5 (7-mode integrity, VERIFIED_ONLY)
          --> academic-paper-reviewer [data_access_level: verified_only]
            --> academic-paper revision loop
              --> Gate 4.5 (final integrity)
                --> FINALIZE
```

**Architecture pattern:** **Prompt-engineered multi-agent chat pipeline** with deterministic shell-level verification. All "agents" are structured system prompts. All "state" is carried through conversation context and the Material Passport YAML file. All "integrity" is enforced by Python scripts invoked from the prompts. The pattern is **state machine with validation gates**, where each gate is a combination of prompt-level constraints and external API calls.

**Key design documents:**
- `docs/ARCHITECTURE.md` -- full pipeline flow, stage matrix, data access flow, quality gates
- `docs/design/2026-05-21-v3.10-182-promote-citation-gate-spec.md` -- citation existence gate spec
- `shared/ground_truth_isolation_pattern.md` -- three-layer data access isolation pattern
- `MODE_REGISTRY.md` -- all 25 modes with spectrum/oversight/triggers
- `POSITIONING.md` -- project philosophy and allowed/discouraged uses

## 3. Performance/Benchmarks

**Token costs (Opus 4.8, ~15k-word paper with ~60 references):**

| Mode | Input Tokens | Output Tokens | Estimated Cost |
|------|-------------|--------------|----------------|
| `deep-research` socratic | ~30K | ~15K | ~$0.60 |
| `deep-research` full | ~60K | ~30K | ~$1.20 |
| `deep-research` systematic-review | ~100K | ~50K | ~$2.00 |
| `academic-paper` plan | ~40K | ~20K | ~$0.80 |
| `academic-paper` full | ~80K | ~50K | ~$1.80 |
| `academic-paper-reviewer` full | ~50K | ~30K | ~$1.10 |
| `academic-paper-reviewer` quick | ~15K | ~8K | ~$0.30 |
| **Full pipeline (10 stages)** | **~200K+** | **~100K+** | **~$4-6** |
| + Cross-model verification | +~10K (external) | +~5K (external) | +~$0.60-1.10 |

**Citation verification overhead (v3.11):** The deterministic citation-existence gate calls external bibliographic APIs (not LLM), so it adds **no Claude token cost** -- only network latency on first lookup. Persistent SQLite cache (`~/.cache/ars/verification.db`, 90-day TTL) means each paper is verified once and reused across drafts.

**Sprint Contract reviewer cost (v3.6.2):** Each reviewer runs 2 LLM turns instead of 1 (Phase 1 paper-blind + Phase 2 paper-visible). Adds ~+30-40% input tokens per reviewer x 5 reviewers for `full` mode.

**Corpus consumer cost (v3.6.5):** When Material Passport carries `literature_corpus[]`, pre-screening adds +~3-5K input for ~50 entries up to +~25-40K for ~500 entries. Partially offset by reduced external-DB search.

**CI/Test metrics:**
- 967 pass / 3 skipped / 0 failed tests (per v3.7.3 convergence)
- ~30 Python lint scripts in `scripts/`
- 10 GitHub Actions workflows
- Multi-round cross-model review convergence (Codex x 10 + Gemini x 1, zero findings at round 10)

## 4. Trade-offs

### Wins

1. **Rigorous integrity obsession.** Every stage has mandatory gates: 7-mode AI Failure Mode Checklist (Lu 2026), deterministic citation verification (4-index), L3 claim-faithfulness audit, anti-leakage protocol, VLM figure verification. These are not aspirational -- they are enforced by Python scripts and CI lints.

2. **Human-in-the-loop, not full automation.** The pipeline has 10 decision-heavy checkpoints and 2 integrity gates that require human acknowledgment. No stage advances without user confirmation. This prevents the hallucination cascades documented in the AI Scientist paper.

3. **Data access level isolation.** Three-layer data isolation (raw -> redacted -> verified_only) prevents ground-truth contamination. The reviewer skill holds the rubric privately, never in the paper-generating agent's context.

4. **Comprehensive CI hardening.** ~30 Python lint scripts enforce schema, manifest, invariant, policy, and consistency checks. 10 GitHub Actions workflows. Multi-model cross-model verification. This is production-grade discipline unusual for an academic tool.

5. **Opt-in, not mandate.** Every hard feature (claim audit, passport reset, terminal policies, strict citation existence) is opt-in via env vars. Default behavior is advisory / non-blocking. This lets users ramp up gradually.

6. **Deterministic over LLM-weak.** Citation verification uses API calls to bibliographic indexes, not LLM-as-judge (except the L3 audit which is opt-in). The deterministic path has no hallucination risk.

7. **Plugin packaging.** Installs in 30 seconds via `/plugin marketplace add Imbad0202/academic-research-skills` + `/plugin install academic-research-skills`. 14 slash commands with model routing.

### Losses

1. **Heavy token cost.** Full pipeline ~$4-6 per run on Opus 4.8. Real papers with multiple revision rounds could cost $10-20+. Not suitable for budget-constrained workflows.

2. **Vendor lock-in.** Requires Claude Code. The sibling Codex distribution exists but the primary is Claude-only. The deep integration with Claude plugin APIs (hooks, slash commands, agents) makes cross-platform portability difficult.

3. **Non-open-source license.** CC BY-NC 4.0 prohibits commercial use. This is deliberate (to keep it free for academia) but means enterprises, consultancies, and commercial research labs are excluded without separate licensing.

4. **Prompt-layer enforcement only.** As the `ground_truth_isolation_pattern.md` explicitly notes: "Nothing in ARS enforces isolation at execution time by blocking API calls, sandboxing the filesystem, or intercepting prompt construction." The phase boundaries, data access levels, and integrity gates are convention + CI lint, not runtime enforcement.

5. **Steep learning curve.** 25 modes across 4 skills with 38 agents, ~30 env var flags, complex schema system (Schema 9-13+), YAML passport handoffs, 10-stage pipeline. The README is 76K -- documentation burden is high.

6. **No automated L3 audit at scale.** The L3 claim-faithfulness audit (v3.8) is opt-in, LLM-as-judge (which itself can hallucinate), and ships with only a 20-tuple gold set. Full corpus-scale evaluation is deferred as "future work."

7. **Human-in-the-loop means slow.** A full pipeline run spanning 10 stages with mandatory human checkpoints at every gate takes "hours to days." Cross-session resume exists but is clunky (paste YAML hash).

8. **Python scripts are auxiliary, not architectural.** The verification scripts are not wired into the pipeline at runtime; they are CI lints and standalone tools. The pipeline runs purely through prompt context. This means the "integrity gates" are only as strong as the prompt following the current Claude model.

## 5. Design Rationale

**Why multi-agent prompts, not code?** The entire framework is structured Markdown prompt files, not a codebase. This is because ARS runs inside Claude Code's agent dispatch system -- the "agents" are not processes but system prompts that Claude follows. The only actual Python is for external API integration (citation lookup, schema validation, CI lint).

**Why human-in-the-loop?** Directly motivated by Lu et al. (2026, Nature) documenting 7 failure modes of fully-autonomous AI research (The AI Scientist). ARS's premise: "a human researcher augmented by AI avoids these failure modes better than either alone." Every stage has mandatory checkpoints specifically to prevent the hallucination cascades documented in the literature.

**Why deterministic verification?** Because LLM-as-judge shares the same failure modes as the generating model -- fluent-but-wrong from parametric memory. Cross-referencing against 4 bibliographic API indexes produces a `lookup_verified` that is provable, not probabilistic. This is the same insight driving the "grounding" movement in RAG systems.

**Why three data access levels?** Inspired by Anthropic's automated-w2s-researcher (2026) three-tier sandbox (local / docker / RunPod). The key insight is that isolation is a property of system design, not a prompt-level instruction. "An agent that can see what counts as a correct answer will, over time, route toward surface features of correctness."

**Why opt-in, not mandate?** Because ARS targets humanities research, higher-education QA, and policy analysis -- domains where quality depends on domain judgment, not scalar metrics. Every optional feature preserves the "byte-equivalent to previous behavior" invariant. The user escalates from advisory to blocking only when they have the test infrastructure to support it.

**Why YAML Material Passport?** Cross-session resume requires serializable state that carries through human-paced work. JSON Schema-validated YAML provides a balance of human readability and machine checkability. The append-only ledger pattern (reset_boundary[]) enables context-reset without state loss.

## 6. Transfer to Lyra

**One idea: Material Passport + Integrity Gate framework.**

Lyra should adopt a per-pipeline **artifact provenance ledger** -- a serializable document (JSON Schema-validated) that tracks every claim, citation, decision, transformation, and integrity check through the pipeline. This ledger:

- Enables cross-session resume by carrying all relevant state in a single document (not conversation context).
- Provides an audit trail for every output artifact (the "who decided what and when" record).
- Allows deterministic verification gates between pipeline stages (not just LLM-as-judge, but API calls, regex checks, schema validation).
- Creates a human-readable "paper trail" that satisfies review requirements.

The integrity gate pattern is the most load-bearing: every stage transition must pass a verification gate before the next stage begins. Gates are tiered (advisory -> strict -> blocking), with the default being advisory (opt-up, not opt-down).

**Workstream route:** **Section 4.2 (Pipeline Orchestration)** -- the Material Passport + multi-stage gate architecture maps directly to Lyra's pipeline orchestration workstream. The gate-passing pattern (verification scripts called between stages) is the specific implementation detail Lyra should copy.

**Secondary route:** **Section 4.4 (Research & Workflow)** -- the systematic review pipeline, PRISMA diagram generation, and citation verification pipeline are directly applicable to Lyra's research workflow features.

**Impact: 9** -- The Material Passport + integrity gate combination solves Lyra's most pressing problems: auditability, reproducibility, cross-session state management, and verifiable output quality. These are foundational architecture concerns, not incremental features.

**Effort: 6** -- Requires designing JSON Schema for the ledger, building verification gate abstractions, retrofitting existing pipeline stages to check in/check out from the ledger, and building a CI-style test harness for gate correctness. The Material Passport itself is simple (one YAML/JSON file), but wiring it through every stage transition is the hard part.

**Tier: T2** -- Core architecture initiative. The integrity gate abstraction is necessary before Lyra can claim "verifiable pipeline" status. It changes how stages communicate and how outputs are validated, so it belongs in a T2 cycle.

**License note:** CC BY-NC 4.0 -- the code and prompts from this repo cannot be directly incorporated into Lyra (which appears to be a commercial product), but the design pattern is freely transferable under fair use for learning and architecture design.

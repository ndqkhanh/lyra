# Lyra Upgrade — Implementation Log

> Append-only: decisions, debates, deferrals + reasons, phase checkpoints.
> Started: 2026-06-07 (following completed deep-research run)

---

## Phase 0 — INGEST & ROADMAP (2026-06-07)

### Ground Truth Documents Read

**Master prompt re-read in full: §0–§9** — confirmed against prior research run. Key directives:
- §0: Four primary directions (multi-agent, self-evolving, auto-research, deep-research) + breakthroughs-everywhere rule + Voice Mode §4.18 flagship
- §1: Persist-until-done, checkpoint-don't-dump, local-library protocol, clone-and-expand
- §1.5: 18-persona expert panel with mandatory-persona maps + rules of engagement
- §2: Framework dependency policy (study, don't depend; LangGraph escape hatch)
- §3: Full corpus context (papers, books, repos, docs) — now fully categorized
- §4: 28 workstreams, each requiring breakthrough proposals
- §5: 3 specific investigations (rmux, multi-tenancy, voice/sound UX)
- §6: Documentation deliverable (visual, sourced, cross-linked)
- §7: Testing deliverable (DeepSeek API key)
- §8: Final output format
- §9: Final docs reminder

**FINAL_REPORT.md read** — top 10 breakthrough recommendations ranked, voice mode flagship architecture blueprint, full research coverage breakdown.

**All 31 plans read** — every plans/4.x-*.md and plans/5.x-*.md scanned for breakthrough proposals, evidence bases, baseline analyses, and implementation outlines.

**best-practices.md read** — 51 consolidated engineering practices from 40 books; binding on build process.

### Codebase Survey

[Awaiting subagent completion — will be appended]

### Gap Analysis

[To be written after codebase survey]

---

## Phase Checkpoints

| Phase | Status | Started | Completed | Key Decisions |
|-------|--------|---------|-----------|---------------|
| 0. Ingest & Roadmap | ⏳ In Progress | 2026-06-07 | — | — |
| 1. Substrate | ⏳ Pending | — | — | — |
| 2. Primary Directions | ⏳ Pending | — | — | — |
| 3. Voice Mode | ⏳ Pending | — | — | — |
| 3.5 Codebase Cleanup | ⏳ Pending | — | — | — |
| 4. Docs & Test Plan | ⏳ Pending | — | — | — |
| 5. Audit | ⏳ Pending | — | — | — |

### Codebase Survey Results (2026-06-07)

**Surprising finding: Lyra v7.2.1 is substantially built out (~30K LOC Python src/, ~824K across 108 packages, ~20K TypeScript UI).**

Key infrastructure already exists:
- **Provider routing** (src/routing/): Anthropic, OpenAI, DeepSeek, Google adapters WITH effort mapping, config, types — Item 1.1 (ProviderBackend) is PARTIALLY DONE
- **Memory** (src/memory/): 3-tier (STM/LTM/index) with consolidation, retrieval, vector search — Item 1.11 foundation EXISTS
- **Skills** (src/skills/ + packages/lyra-skills): Registry, parser, executor, importer, autoskill, evoskill, compiler — Item 1.23 foundation EXISTS
- **Hooks** (src/hooks/): v2 engine with PreToolUse, PostToolUse, Stop + handlers — Item 1.5 needs EXTENSION (3→25+), not rebuild
- **Safety** (src/safety/): 5-layer defense-in-depth with tool gate, evolution guard, frozen evaluators — Item R.3 is MOSTLY DONE
- **Voice** (src/voice/): Full cascaded pipeline (capture, STT, TTS, barge-in, latency tracking) — Phase 3 voice items are MOSTLY DONE for Tier A
- **Permissions** (src/permissions/): ALLOW/DENY/ASK with deny-first — Item 1.9 EXISTS
- **Tools** (src/tools/): Registry, executor, sandbox, builtins — Item 1.16 EXISTS
- **Sessions** (src/sessions/): SQLite-backed session persistence — Item 1.19 EXISTS
- **Orchestrator** (src/orchestrator/): Sub-task decomposition, worker pool, artifact mgmt — Item 2.1 partial

**Adjusted strategy (per master prompt §2: "propose enhancements rather than replacements"):**
- Items where infrastructure exists: ENHANCE, don't rebuild
- Items that are stubs: BUILD (desktop, rl_optimizer)
- Items that are missing: BUILD (field-theoretic memory, adversarial panel, SkillNet graph)

### Gap Analysis (adjusted for existing codebase)

| Item | Plan Says | Reality | Adjusted Approach |
|------|-----------|---------|-------------------|
| 1.1 ProviderBackend | Build from scratch | src/routing/ already has 4 adapters | ENHANCE: add capability map, formalize protocol ABC, add cost tracking |
| 1.5 Hooks 25+ events | Build from scratch | HookEngine v2 works with 3 events | EXTEND: add events, YAML config, hot-reload, matchers |
| 1.11 Memory 3-tier | Build breakthrough | STM/LTM/index exists | ENHANCE: add graph memory, cross-agent shared, field-theoretic dreaming |
| 1.20 Supervisor daemon | Build from scratch | supervisor/ stub exists | BUILD: full daemon with two-axis state, lifecycle |
| 2.1 Dynamic workflows | Build from scratch | orchestrator/ exists with DAG | BUILD: code-driven scripts, resumability, progress view |
| 3.1 Voice pipeline | Build cascaded | src/voice/ FULLY EXISTS | ENHANCE: add VI+EN, SFX layer, self-correction buffer |
| R.14 Desktop GUI | Build from scratch | src/desktop/ is STUB | BUILD: Electron + React thin GUI shell |

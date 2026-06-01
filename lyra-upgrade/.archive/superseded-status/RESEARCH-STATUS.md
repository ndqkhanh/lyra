# Lyra Upgrade Research - Run 2 Status

**Date**: 2026-05-31  
**Mode**: Iterative improvement with parallel dynamic workflow

---

## Active Research Agents (18 Running)

| Agent | Section | Sources | Status |
|-------|---------|---------|--------|
| 1 | §3.13 Voice & Audio | 7 sources | ✅ COMPLETE |
| 2 | §3.1 Claude Code Docs (batch 1) | 21/38 URLs | ✅ COMPLETE |
| 3 | §3.4 MemAgent Papers (batch 1) | 10 papers | 🔄 RUNNING |
| 4 | §3.5 arXiv Papers (batch 1) | 15 papers | 🔄 RUNNING |
| 5 | §3.2 Comparable Harnesses (batch 1) | 6 repos | 🔄 RUNNING |
| 6 | §3.15 Reliability/Observability | 8 sources | 🔄 RUNNING |
| 7 | §3.14 Model Routing (remaining) | 3 sources | 🔄 RUNNING |
| 8 | §3.6 AutoScientists | 4 sources | 🔄 RUNNING |
| 9 | §3.16 Safety/Alignment | 12 sources | 🔄 RUNNING |
| 10 | §3.9 Memory/Context Repos | 7 repos | 🔄 RUNNING |
| 11 | §3.18 Self-Evolving Agents | 6 sources | 🔄 RUNNING |
| 12 | §3.19 Deep Research/MCP/Tools | 18 sources | 🔄 RUNNING |
| 13 | §3.17 Memory/Context Papers | 13 papers | 🔄 RUNNING |
| 14 | §3.8 Terminal Multiplexers | 6 repos | 🔄 RUNNING |
| 15 | §3.11 Other Agent Frameworks | 13 repos | 🔄 RUNNING |
| 16 | §3.12 Workflows/Swarms/UX | 7 sources | 🔄 RUNNING |
| 17 | §3.10 Autonomy/Continuous | 1 source | 🔄 RUNNING |
| 18 | §3.3 Awesome Lists | 7 lists | 🔄 RUNNING |
| 19 | §3.2 Comparable Harnesses (batch 2) | 6 repos | 🔄 RUNNING |
| 20 | §3.7 Skills Systems Repos | 10 repos | 🔄 RUNNING |

---

## Coverage Projection

**Current baseline** (from prior runs): 16/286 sources (5.6%)

**In-flight research** (18 agents):
- §3.1: +21 URLs (21/38 complete, 17 remaining)
- §3.2: +12 repos (all covered)
- §3.3: +7 lists (all covered)
- §3.4: +10 papers (10/22 in this batch)
- §3.5: +15 papers (15/63 in this batch)
- §3.6: +4 sources (all covered)
- §3.7: +10 repos (all covered)
- §3.8: +6 repos (all covered)
- §3.9: +7 repos (all covered)
- §3.10: +1 source (all covered)
- §3.11: +13 repos (all covered)
- §3.12: +7 sources (all covered)
- §3.13: +7 sources (✅ already complete)
- §3.14: +3 sources (all covered)
- §3.15: +8 sources (all covered)
- §3.16: +12 sources (all covered)
- §3.17: +13 papers (all covered)
- §3.18: +6 sources (all covered)
- §3.19: +18 sources (all covered)

**Projected after current batch**: ~180/286 sources (63%)

**Remaining after current batch**:
- §3.1: 17 Claude Code docs URLs
- §3.4: 12 MemAgent papers
- §3.5: 48 arXiv papers

---

## Next Batch Planning

After current agents complete, launch:

**Batch 2 - MemAgent Papers** (12 remaining):
- Rows 71-86 in source-ledger

**Batch 2 - arXiv Papers** (48 remaining):
- Rows 102-149 in source-ledger

**Batch 2 - Claude Code Docs** (17 remaining):
- Complete rows 1-38 in source-ledger

**Estimated completion**: 95%+ coverage after Batch 2

---

## Research Quality Metrics

**Depth compliance**: All agents instructed to extract:
- Mechanism (how it works)
- Result/benchmark (quantitative)
- Limitation (what it can't do)
- Transferable idea (for Lyra)

**Traceability**: All findings linked to:
- Source URL in findings.md
- Source-ledger row marked "read"
- Workstream mapping (§4.X)

**Failure handling**: 
- Dead links → mark "failed" + log reason
- Inaccessible → mark "unresolved" + log reason
- Never invent content

---

## Deliverables Status

| Deliverable | Status | Notes |
|-------------|--------|-------|
| source-ledger.md | ✅ CREATED | 286 URLs tracked |
| findings.md | 🔄 POPULATING | Growing with each agent |
| PROGRESS.md | ⏳ PENDING | Update after batch completes |
| MASTER-PLAN.md | ⏳ PENDING | Add Run 2 changelog |
| brainstorm/*.md | ✅ EXISTS | 9 files, need deepening |
| plans/*.md | ✅ EXISTS | 9 files, need deepening |
| memory-architecture.md | ✅ EXISTS | Needs Run 2 enhancements |
| voice-mode.md | ✅ EXISTS | Needs Run 2 enhancements |
| test-plan.md | ⏳ PENDING | Create after research |
| review-audit.md | ⏳ PENDING | Final self-audit |

---

## Workflow Strategy

**Phase 1** (CURRENT): Parallel research across all sections
- 18 agents running simultaneously
- Maximize throughput on independent sources
- Each agent updates findings.md + source-ledger.md

**Phase 2** (NEXT): Complete remaining sources
- Launch Batch 2 agents for §3.1, §3.4, §3.5
- Target 95%+ coverage

**Phase 3**: Deepen existing plans
- Read all findings.md rows
- Enhance brainstorm files (ensure ≥3 cross-source ideas)
- Upgrade plan files with breakthrough tiers
- Add Mermaid diagrams where missing

**Phase 4**: Create missing deliverables
- test-plan.md (deep/auto/scientist research flows)
- Standalone memory-architecture.md enhancements
- Standalone voice-mode.md enhancements
- docs/README plan

**Phase 5**: Self-audit and finalize
- Create review-audit.md
- Verify every workstream has (A) parity + (B) breakthrough
- Verify every plan links to brainstorm file
- Update MASTER-PLAN.md with Run 2 changelog
- Final coverage tally

---

## Key Insights So Far

**Voice Mode** (§4.18 - Flagship):
- Full-duplex architecture (Moshi) achieves 200ms latency
- Modular extension system (TEN-Agent) enables hot-swap
- LLM-as-TTS (Orpheus) provides emotion control
- Recommended stack: Silero VAD + Smart Turn + NeMo Parakeet + Orpheus

**Claude Code Docs** (§4.1-§4.14):
- Progressive skills loading (3-level: metadata → instructions → resources)
- 5 hook types × 25+ lifecycle events
- MCP Tool Search (deferred schema loading, scales to 10K tools)
- Multi-layer permission system (modes + rules + sandboxing)
- Defense-in-depth approach to safety

**Skills Systems** (§4.4):
- SkillNet: NPM-like marketplace with 500k+ skills, 5-D evaluation
- Darwin Gödel Machine: Self-modifying agent, SWE-bench 20%→50%
- Auto-creation from repos/docs/conversations

**Model Routing** (§4.5):
- RouteLLM: 85% cost reduction at 95% GPT-4 performance
- BEST-Route: Multi-sampling from weak models
- FrugalGPT: 98% cost reduction with cascade

**Memory** (§4.2):
- A-MAC: 5-factor admission control (F1=0.583, -31% latency)
- SABER: Mutating actions reduce success 55-96%
- ERL: Heuristics > raw trajectories for transfer

---

**Status**: ACTIVE RESEARCH IN PROGRESS  
**Next Update**: After Batch 1 agents complete

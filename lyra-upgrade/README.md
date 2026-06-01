# Lyra Ultra Upgrade — Documentation

**Status**: All 9 tiers reviewed and approved (Run 22, 2026-06-01)  
**Tests**: ~2,500+ passing across all packages  
**Implementation**: Merged to `main`, pushed to `origin/main`

---

## Quick Navigation

### 🏗 00-architecture/ — Core Architecture

The foundational design documents. Start here.

| File | Description |
|------|-------------|
| `BASELINE.md` | Honest as-built review of Lyra's current architecture — what every upgrade is measured against |
| `SYNTHESIS.md` | Cross-source state-of-the-field analysis across 253+ sources, organized by theme |
| `ARCHITECTURE-DEBATE.md` | Multi-agent adversarial debate — 5 architecture candidates, 8+ personas, trade-off tables |
| `BREAKTHROUGH-ARCHITECTURE.md` | The unified novel architecture (capstone) — what's NEW vs what's ADOPTED vs what's REJECTED |
| `MASTER-PLAN.md` | Executive summary + prioritized roadmap + per-run improvement log |
| `memory-architecture.md` | 4-tier Temporal Knowledge Graph design with Mermaid diagrams + data models |
| `voice-mode.md` | Full voice pipeline architecture — DSP algorithms, latency math, provider-swappable design |

### 📋 01-plans/ — Per-Workstream Plans (26 files)

One detailed plan per §4/§5 workstream. Each plan includes: evidence synthesis, Lyra-specific design, data models, build outline, multi-provider notes, (A) parity + (B) breakthrough, expert review.

Key files:
- `00-voice-mode.md` (2,036 lines) — Flagship voice feature
- `19-ultracode-replication.md` (3,183 lines) — Claude Code effort + orchestration stack replication
- `04-skills-system.md` (2,891 lines) — Complete skills curator/loader/creator/evolver pipeline
- `12-swarm-fleet-channels.md` (1,699 lines) — Multi-agent orchestration + fleet supervisor

### 💡 02-brainstorms/ — Cross-Source Ideas (21 files)

Explicit brainstorming passes for each workstream. Each contains ≥3 novel cross-source breakthrough ideas, failure mode analysis, and expert feasibility checks.

### ✅ 03-reviews/ — Expert Panel Reviews (9 files)

Per-tier expert panel reviews with signed-off verdicts from Senior Architect, Senior AI Engineer, Senior Security, Senior SRE, Senior Safety, and Senior UX.

| File | Tier | Verdict |
|------|------|---------|
| `tier-1.md` | Provider & Reasoning | NON-BLOCKING |
| `tier-2.md` | Memory & Context | NON-BLOCKING |
| `tier-3.md` | Orchestration & Fleet | NON-BLOCKING |
| `tier-4.md` | Capability Surface | NON-BLOCKING |
| `tier-5.md` | Skills System | NON-BLOCKING |
| `tier-6.md` | Voice Mode | NON-BLOCKING |
| `tier-7.md` | Reliability & Safety | NON-BLOCKING |
| `tier-8.md` | UI/UX + rmux | NON-BLOCKING |
| `tier-9.md` | Docs & README | NON-BLOCKING |

### 🔬 04-research/ — Research Notes & Source Tracking

| File | Description |
|------|-------------|
| `source-ledger.md` | Every §3 URL tracked with depth + status (253/286 deep-read) |
| `findings.md` | 500KB+ of per-source findings — mechanisms, benchmarks, trade-offs |
| `research-log.md` | Which sources were consulted, failed, or left unresolved |
| `ultracode-mechanisms.md` | Deep technical analysis of Claude Code's dynamic workflow engine |
| `agent-view-worktree-mechanisms.md` | Claude Code Agent View + Worktree isolation mechanisms |
| `harnesses-deep-research.md` | Deep analysis of DeerFlow, OpenCode, Pi, Goose, Cline, Aider, and other harnesses |
| `core-papers-deep-research.md` | Deep-read analysis of key arXiv papers from §3.5 |
| `memory-papers/` | Full PDFs + text of A-MEM, memory survey, and related papers |

### 📊 05-tracking/ — Implementation Tracking

| File | Description |
|------|-------------|
| `IMPL-PROGRESS.md` | **Master tracker** — per-tier status, test counts, commit SHAs |
| `COMPLETION-STATUS.md` | Final completion verification (all 27 plans) |
| `FINAL-AUDIT.md` | Independent end-to-end audit of the full upgrade |
| `review-audit.md` | Self-audit of documentation quality + coverage |
| `impl-decisions.md` | Architecture decisions made during implementation |
| `impl-backlog.md` | Deferred enhancements ranked by impact×effort |

### 📦 06-deliverables/ — Final Deliverables

| File | Description |
|------|-------------|
| `NAVIGATION-GUIDE.md` | Complete navigation guide to all Lyra resources |
| `test-plan.md` | Detailed test plan for deep/auto/scientist-research flows |
| `FEATURE-PARITY-MATRIX.md` | Lyra vs Claude Code vs Hermes feature comparison |

---

## File Structure

```
lyra-upgrade/
├── README.md                  ← You are here
├── 00-architecture/           Core architecture (BASELINE, SYNTHESIS, DEBATE, BREAKTHROUGH, MASTER-PLAN)
├── 01-plans/                  Per-workstream plans (26 files covering §4.1–§5.3)
├── 02-brainstorms/            Cross-source breakthrough ideas (21 files)
├── 03-reviews/                Expert panel reviews (9 files, one per tier)
├── 04-research/               Source ledger, findings, research notes, downloaded papers
├── 05-tracking/               Progress tracking, audit, decisions, backlog
├── 06-deliverables/           Navigation guide, test plan, feature parity matrix
└── .archive/                  Superseded docs, phase research, duplicates (historical)
```

## Key Metrics

| Metric | Value |
|--------|-------|
| Total documentation | ~84,000+ lines |
| Plans | 26 (avg 1,100 lines each) |
| Brainstorms | 21 (total 9,885 lines) |
| Sources deep-read | 253/286 URLs |
| Expert reviews | 9 tiers, 27+ reviewer sign-offs |
| Architecture debate | 5 candidates, 10 trade-off dimensions |
| Implementation tests | ~2,500+ passing |

## Getting Started

1. **New to Lyra?** Read `00-architecture/MASTER-PLAN.md` for the executive summary
2. **Understanding the architecture?** Read `00-architecture/BREAKTHROUGH-ARCHITECTURE.md`
3. **Want to see the debate?** Read `00-architecture/ARCHITECTURE-DEBATE.md`
4. **Implementing a feature?** Find your workstream in `01-plans/`
5. **Tracking progress?** Read `05-tracking/IMPL-PROGRESS.md`
6. **Finding a source?** Look it up in `04-research/source-ledger.md`

## Changelog

| Date | Run | Changes |
|------|-----|---------|
| 2026-06-01 | 24 | Complete file structure reorganization. Moved from 40+ scattered top-level files to 7 clean numbered directories. Consolidated duplicate status docs into 05-tracking/. Archived superseded phase research. Removed backup/temp files. |

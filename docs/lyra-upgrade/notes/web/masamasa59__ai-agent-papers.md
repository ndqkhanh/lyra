# masamasa59/ai-agent-papers -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Headline**: A living, curated taxonomy of the AI agent research landscape, updated weekly from arXiv, with monthly deep-analytical trend newsletters (in Japanese) that synthesize emerging research directions into actionable practitioner guidance.

This is NOT a code repository -- it contains zero source code, zero configuration files, zero test suites. It is a **structured knowledge base** of approximately 60+ markdown files organized in a three-level taxonomy:

- **Level 1 -- Agent Capabilities** (16 files under `capability-papers/`): environment, ideation, planning, reasoning, profile, perception, tool-use, self-correction, search, memory, self-evolution, safety, agent tuning, evaluation, knowledge, prediction
- **Level 2 -- Agent Frameworks** (1 large file `agent-frameworks/agent-framework.md`): single-agent architectures, multi-agent systems, agent-ops/UX/business
- **Level 3 -- Agent Applications** (12 files under `application-papers/`): embodied agents, digital agents (GUI/Web/Mobile), software agents, data agents, research agents, deep research agents, API agents, agentic AI systems, enterprise agents, financial agents, multi-agent (MAD/problem solving/world simulation)

The curation mechanism is described in the README: the maintainer performs weekly arXiv searches using specific keywords and selectively adds papers that introduce "a distinctively new approach or novel concept." The repo explicitly states it does not aim for comprehensiveness.

The **monthly newsletter** (`newsletters/may_2026/trends_2026_05.md`, 1250+ lines) is the crown jewel -- it provides:
1. Executive summary identifying 4 major research pillars for the period
2. Per-pillar deep dives with abstract-level analysis, novelty assessment, and cross-pillar connections
3. "Cross-cutting insights" sections that trace how debates evolve month-over-month
4. Actionable "implementation tips" for practitioners at the end of each section
5. Key performance numbers from benchmark papers (e.g., "Claude Opus 4.7 achieves 62.2% on WildClawBench")

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Entry point**: `README.md` -- serves as the master navigation hub with:
- A definition of "AI Agent" (autonomous LLM system with perception, reasoning, tool-use)
- Links to all 3 categories (capability/framework/application) via relative markdown links
- Monthly highlights section at the top (most recent month first) that features ~10-40 curated papers per month
- References to related paper collection repos

**Data flow**: The repo is a static markware tree with no build pipeline, no CI, no automation visible. Papers flow through a human-in-the-loop process:
1. Weekly arXiv keyword searches
2. Manual filtering for novelty
3. Addition to the appropriate category file(s) with date prefix and paper link
4. Monthly synthesis into the Japanese-language newsletter with trend analysis

**Content patterns**:
- Each category file lists papers chronologically (oldest first) with: `[Month Year] "Title" [[paper](arxiv link)]`
- Papers are tagged with emoji prefixes: 🔥 = recommended, 📖 = survey, ⚖️ = benchmark
- Newsletter files use deep, structured markdown with numbered sections, tables, comparison matrices, and implementation checklists
- The May 2026 newsletter even includes "anti-pattern" sections ("things you should NOT do") and metric proposals

**Design pattern**: Taxonomy-first curation with analytical synthesis layer. The README is the shallow entry point; the newsletters provide the depth.

## 3. Performance/Benchmarks (real numbers from the repo)

The repo does not run benchmarks but reports key numbers from papers it curates:

**From May 2026 newsletter (trends_2026_05.md)**:
- `SkillScope`: over-privilege detection F1=94.53%, over-privilege invocation reduced by 88.56% across 7,039 real skills
- `SkillsVote`: Terminal-Bench 2.0 +7.9pp, SWE-Bench Pro +2.6pp
- `Ratchet`: MBPP+ hard-100 with Claude Opus 4.7 +0.328 improvement, with mathematical guarantee of no degradation below baseline
- `EvolveMem`: LoCoMo +25.7%, MemBench +18.9%
- `PaSaMaster`: 38 domains, 15.6x keyword search F1, zero source hallucination, outperforms GPT-5.2 at 1% compute
- `ExploitBench`: Non-public frontier models ~50% exploit success rate on V8 bugs
- `MemRepair`: SEC-Bench 58.0%, PatchEval 58.2%, Multi-SWE-bench 30.58% (SOTA)
- `WildClawBench`: Claude Opus 4.7 best at 62.2%, frontier models still struggle on long-horizon tasks
- `STALE`: Best model only 55.2% accuracy on memory staleness detection
- `Useful Memories Become Faulty`: GPT-5.4 fails 54% of previously-solved ARC-AGI problems with integrated memory
- `Life-Harness`: 126/116 settings improved across 7 environments, 18 models, average 88.5% relative improvement; harness built from 1 model transfers to 17 models
- `LongSeeker`: BrowseComp 61.5%, BrowseComp-ZH 62.5%
- `AgenticRAG`: BRIGHT 49.6% recall@1 (+21.8pp), WixQA 0.96 factuality, FinanceBench 92%
- `Cochise`: 597-line Python reference harness for autonomous pentesting
- `AEvo (Harnessing Agentic Evolution)`: 26% relative improvement over strongest baseline, SOTA on 3 open-ended optimization tasks

## 4. Trade-offs (wins vs loses)

**Wins**:
- **Curatorial precision**: Not trying to be comprehensive means every paper included has a clear "why it matters" signal. No noise from incremental/trivial work.
- **Analytical depth**: The monthly newsletters far exceed what any existing paper repo provides. They connect papers across categories, identify emergent trends, and provide actionable implications.
- **Temporal awareness**: Monthly highlights + monthly newsletter creates a clear picture of how the field evolves. The "cross-cutting insights" sections trace debates across months (e.g., the memory debate from Jan to May 2026).
- **Cross-referencing**: Papers are linked from multiple sections (e.g., a paper on harness evolution appears in both the framework and self-evolution sections).
- **Language accessibility**: Japanese-language newsletters serve a significant researcher/engineer demographic that may not have English as their primary reading language.

**Loses**:
- **No reproducibility**: No code, no configs, no automation. Cannot reproduce the curation process.
- **No versioning of links**: Papers are linked to arXiv, which is stable, but the curation criteria and selection rationale are undocumented.
- **Dependency on single maintainer**: The repo has one commit ("update: README") by `masamasa59`. Quality depends entirely on their continued effort and evolving judgment.
- **Japanese-only newsletters**: The analytical synthesis (the highest-value content) is only available to Japanese readers.
- **No structured metadata**: Papers are listed but not tagged with topics, keywords, or methodology types beyond the broad category emoji. No ability to filter by approach (e.g., "show all RL-based papers").
- **No licensing**: No LICENSE file means all rights reserved by default, limiting reuse.
- **No collaboration infrastructure**: No issues template, no contribution guidelines, no PR workflow visible.
- **Less systematic than academic surveys**: A human reading weekly arXiv picks will miss papers published on non-arXiv venues or papers the maintainer found less interesting.

## 5. Design Rationale (why this approach)

The repo's design reflects a clear philosophy: **quality over quantity, analysis over aggregation**.

1. **Weekly cadence + selective inclusion**: arXiv receives hundreds of AI papers weekly. A comprehensive collection would be overwhelming. The selective approach means each paper in the repo carries a signal -- it was deemed novel enough to include. This mirrors the "less is more" design principle also observed in the papers the repo covers (e.g., `Is Grep All You Need?`).

2. **Taxonomy-first organization**: The three-level scheme (capability / architecture / application) reflects the dominant conceptual frameworks in the AI agent literature. It is not arbitrary -- it maps to how researchers think about agents: what they can do, how they are built, and what they are used for.

3. **Newsletter as synthesis layer**: A list of papers, even well-organized, does not reveal trends. The monthly newsletter adds the critical analytical layer -- identifying which research questions are converging, which are diverging, and what practitioners should care about. This is the repo's primary value-add over simply bookmarking arXiv.

4. **Japanese language**: The choice of Japanese for newsletters suggests the maintainer serves a specific audience -- Japanese-speaking AI researchers and engineers who benefit from analysis in their native language. This is a deliberate niche strategy.

5. **No code, no automation**: The maintainer has chosen a low-overhead curation model. No CI pipeline means no maintenance burden. No code means no dependency rot. The repo is essentially a well-structured reading list with optional deep analysis -- sustainable for a single maintainer.

## 6. Transfer to Lyra (one idea + route + Impact/Effort/Tier + LICENSE)

**Transferable idea**: Adopt the monthly "trend newsletter" format for Lyra's own research synthesis, but with two enhancements: (1) link findings directly to Lyra's plan sections (e.g., "this paper proves memory corruption is real -- update §4.2 memory architecture to include `valid_until` timestamps"), and (2) produce an English-language version as a public-facing research blog that positions Lyra as a thought leader in agent harness engineering.

The newsletter's structure is directly applicable: an executive summary identifying 3-4 major research pillars, per-pillar deep dives with key numbers, cross-cutting insights tracing debates over time, and implementation checklists. The key differentiator from the original repo is linking each finding to a specific plan section with an action item -- turning research synthesis into engineering action.

**Workstream route**: §5.x Communications/Learning -- the newsletter format is an outward-facing knowledge product that builds community and attracts contributors.

**Impact**: 7/10 -- A regular research synthesis product would: (a) position Lyra as a thought leader, (b) attract external contributors who see their papers being analyzed, (c) create a forcing function for the team to stay current, and (d) provide a feedback loop into Lyra's own plans when papers reveal flaws in the current architecture.

**Effort**: 5/10 -- Producing a monthly newsletter requires: (1) weekly arXiv scanning (2-3 hours/week), (2) structured note-taking per paper, (3) monthly synthesis writing (8-12 hours), (4) cross-referencing against Lyra plans. Initial setup requires establishing the template and workflow. Can be started as an individual effort and grown into a team process.

**Tier**: "Adopt" -- this is a low-risk, high-visibility practice that can be implemented immediately without code changes.

**LICENSE**: The original repo has **no LICENSE file** (all rights reserved by default). Lyra should use an open license (MIT or CC-BY-4.0) for any derivative.

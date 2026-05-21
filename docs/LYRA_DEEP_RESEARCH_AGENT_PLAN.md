# Lyra Deep Research Agent — Master Plan

**Goal:** Transform Lyra into a personal super-intelligent Deep Research AI Researcher Agent
that can research the best papers, GitHub repos, and technical materials for any topic a user
wants to deep-dive into.

**Research Foundation:** Grounded in 9 deep synthesis documents:
- `313` Memory Research 2026 Master Synthesis
- `314` Memory OpenReview Paper Atlas 2026
- `315` Memory Canon & OSS Landscape 2026
- `316` LLM Agent Memory Systems Dense Synthesis
- `317` AI Research Agents 2026 Deep Synthesis
- `318` Context Engineering for AI Agents 2026
- `319` AI Agents Capstone 2026
- `320` Skills for AI Agents 2026
- `321` Spec-Driven Development & BMAD AI 2026

**Date:** 2026-05-14
**Status:** Master Planning — Do Not Implement Until This Plan Is Approved

---

## 1. Goal Definition

### What Lyra Must Do

When a user types `/research <topic>`, Lyra executes a full deep research pipeline and
produces a dense, citation-grounded synthesis report covering:

1. **Best papers** — top arXiv, OpenReview, Semantic Scholar, Papers With Code, ACL Anthology
   papers ranked by recency, citation impact, venue quality, and relevance
2. **Best GitHub repos** — top open-source implementations, tools, and benchmarks ranked by
   stars, activity, relevance, and code quality signals
3. **Key concepts and taxonomy** — a structured map of the topic's landscape
4. **Research gaps and opportunities** — what is missing, what is contested
5. **Cross-source synthesis** — how papers relate to each other, what contradicts what
6. **Actionable next steps** — for a researcher or practitioner wanting to go deeper

### What "Super Intelligent" Means Here

The research agent must be:
- **Comprehensive**: no major paper or repo silently missing
- **Verified**: every cited source is real and traceable
- **Synthesized**: not a list dump — conclusions and relationships are drawn
- **Compounding**: every research session makes future sessions on related topics smarter
- **Falsification-aware**: it surfaces counter-evidence and contested claims (Doc 317 Baby-AIGS)

---

## 2. Current State Assessment

### What Already Exists in lyra-research

| Component | File | Status | Gap |
|---|---|---|---|
| ArXiv search | `discovery.py:ArXivDiscovery` | Basic | No citation traversal, no quality filtering |
| GitHub search | `discovery.py:GitHubDiscovery` | Basic | No activity scoring, no code quality signals |
| Semantic Scholar | `discovery.py:SemanticScholarDiscovery` | Basic | No influence/citation graph traversal |
| Content fetcher | `fetchers.py:ContentFetcher` | Basic | No PDF parsing, no OpenReview support |
| Paper analysis | `analysis.py:PaperAnalyzer` | Stub | No LLM-powered insight extraction |
| Repo analysis | `analysis.py:RepositoryAnalyzer` | Stub | No code quality, no benchmark signals |
| Knowledge graph | `synthesis.py:KnowledgeGraph` | Struct only | Not populated, no graph traversal |
| Query expansion | `strategies.py:QueryExpander` | Static synonyms | No LLM-powered expansion |
| Research planner | `strategies.py:ResearchPlanner` | Basic | No adaptive strategy selection |
| Feynman explain | `lyra_research/feynman.py` | Unknown | — |
| Falsification | `lyra_research/falsification.py` | Unknown | — |

### What Already Exists in lyra-memory

| Component | Status | Research Relevance |
|---|---|---|
| MemoryRecord schema | Good — 5 types, temporal validity, provenance | Needs research-specific subtypes |
| MemoryStore | Good | Needs research-session scoping |
| Extractor | Basic | Needs paper/finding extraction |
| Compression | Basic | Needs research-aware compression |
| Evolution | Stub | Needed for research strategy learning |
| Playbook | Stub | Needed for research skill storage |
| Skills | Stub | Needed for research skill library |

### Critical Gaps vs. Goal

| Gap | Impact | Phase to Fix |
|---|---|---|
| No OpenReview source | Miss ICLR/NeurIPS workshop papers | Phase 1 |
| No HuggingFace Papers source | Miss ML practitioner ecosystem | Phase 1 |
| No Papers With Code source | Miss reproducibility-scored papers | Phase 1 |
| No Verifiable Checklist + Evidence Audit | Context rot, hallucinated citations | Phase 2 |
| No citation graph traversal | Misses related-work chains | Phase 1 |
| No research-specific memory types | Research findings not persisted well | Phase 3 |
| No Zettelkasten linking between notes | Knowledge silos between sessions | Phase 3 |
| No DCI-style local corpus search | Can't search downloaded papers | Phase 3 |
| No ReasoningBank-style strategy extraction | No compounding research intelligence | Phase 5 |
| No structured report generator | Only raw data, no usable output | Phase 4 |
| No gap/falsification analysis | Misses contested claims | Phase 2 |
| No `/research` TUI command | No user-facing entry point | Phase 6 |
| No research quality metrics | Can't measure or improve | Phase 7 |

---

## 3. Architecture

The architecture follows the **Controlled Research Pipeline** (RhinoInsight Pattern B, Doc 317)
combined with the **hybrid memory system** recommended for research assistants (Doc 315 §4) and
the **four context-engineering strategies** (Doc 318 §1).

### 3.1 The Seven-Layer Research Stack

```
L7  Research Intelligence
    Why research this? What do I already know? What's the gap?
    → ResearchGoalClarifier, KnowledgeGapAnalyzer

L6  Research Orchestration
    Plan → Search → Analyze → Synthesize → Verify → Report
    → ResearchOrchestrator, VerifiableChecklist, EvidenceAudit

L5  Context Engineering (Write / Select / Compress / Isolate)
    → ResearchNoteWriter, SourceSelector, AbstractCompressor, ParallelSearchIsolation

L4  Research Memory
    Working + Episodic + Semantic + Procedural + Experience memory
    → ResearchMemorySystem (A-Mem + Cognee + DCI inspired)

L3  Research Analysis & Synthesis
    Paper analysis, repo analysis, concept extraction, relationship mapping
    → PaperAnalyzer, RepositoryAnalyzer, ConceptExtractor, CrossSourceSynthesizer

L2  Research Discovery Tools
    arXiv, Semantic Scholar, GitHub, OpenReview, HF Papers, PwC, ACL Anthology
    → MultiSourceDiscovery (enhanced), CitationTraversal, DirectCorpusSearch

L1  Research Source Corpus
    Downloaded papers, README files, blog posts, patents
    → LocalCorpus (SQLite + embeddings + file store)

L0  Foundation Model Brain
    Claude Sonnet/Opus for analysis, Haiku for lightweight tasks
    → LLM routing by task complexity
```

### 3.2 The Controlled Research Pipeline (per query)

Inspired by RhinoInsight's Verifiable Checklist + Evidence Audit (Doc 317 §2 Pattern B):

```
User: /research <topic>
  │
  ▼
[1] CLARIFY
  ResearchGoalClarifier
  → What specifically do you want to know?
  → What depth? (survey | deep-dive | sota-only)
  → What recency? (all-time | last-2yr | last-6mo)
  → Known starting points? (optional)

  ▼
[2] PLAN
  VerifiableChecklistGenerator
  → Generates: N research questions to answer
  → Generates: Source priority list
  → Generates: Quality thresholds
  → Generates: Stopping criteria

  ▼
[3] SEARCH (parallel agents per source)
  MultiSourceDiscovery × N sources
  → arXiv, OpenReview, Semantic Scholar
  → GitHub, Papers With Code, HuggingFace Papers
  → ACL Anthology (for NLP), citation traversal
  → LocalCorpus (previously downloaded)

  ▼
[4] FILTER & RANK
  QualityScorer + ResultRanker
  → Citation score × recency score × venue score × relevance score
  → Stars × activity × relevance (for repos)
  → Deduplication across sources

  ▼
[5] FETCH & PARSE
  ContentFetcher × top-N ranked sources
  → PDFs via arxiv API
  → HTML abstracts + full text
  → GitHub README + repo stats
  → Store to LocalCorpus

  ▼
[6] ANALYZE
  PaperAnalyzer × each paper (LLM-powered)
  → Core contribution, method, benchmarks, results, weaknesses
  RepositoryAnalyzer × each repo (LLM-powered)
  → Purpose, quality signals, activity, relevance

  ▼
[7] EVIDENCE AUDIT
  EvidenceAudit (RhinoInsight-inspired)
  → Maps each claim to a source
  → Flags unverifiable claims
  → Detects contradictions across sources
  → Checks checklist completion

  ▼
[8] SYNTHESIZE
  CrossSourceSynthesizer (LLM-powered)
  → Taxonomy of the field
  → Best papers per sub-area
  → Best repos per use-case
  → Relationships: extends, contradicts, implements, benchmarks
  → Gap analysis: what is missing?
  → Falsification notes: what is contested?

  ▼
[9] REPORT
  ResearchReportGenerator
  → Structured Markdown with sections
  → Comparison tables
  → Citation-bound claims (no hallucination)
  → Gap map
  → Next steps

  ▼
[10] MEMORIZE
  ResearchMemorySystem
  → Save report to episodic memory
  → Extract findings to semantic memory
  → Extract strategies to procedural memory
  → Update knowledge graph with new nodes/edges
  → Update research strategy memory (ReasoningBank-style)
```

### 3.3 Research Memory Architecture

Based on Doc 315 §4 recommendation: **A-Mem + Cognee + DCI** for research assistant.

```
Research Memory System
├── WorkingResearchMemory       ← current session's active search state
│   ├── current_topic
│   ├── active_checklist
│   ├── sources_found (this session)
│   └── synthesis_in_progress
│
├── ResearchNoteStore           ← A-Mem style Zettelkasten
│   ├── ResearchNote: {id, topic, finding, sources, links, timestamp}
│   ├── linking: notes reference each other by ID
│   └── evolution: new notes can update/extend old notes
│
├── KnowledgeGraphStore         ← Cognee/Graphiti style
│   ├── nodes: Paper, Repo, Concept, Author, Venue, Method, Dataset
│   ├── edges: cites, implements, benchmarks, extends, contradicts
│   ├── temporal validity windows on edges
│   └── query: "what papers extend X?" "what repos implement Y?"
│
├── ResearchStrategyMemory      ← ReasoningBank style (Doc 313 §1)
│   ├── successful_strategies: {topic_type, strategy, outcome, score}
│   ├── failed_strategies: {topic_type, why_failed, lesson}
│   └── domain_models: {domain, preferred_sources, key_terms}
│
├── LocalCorpus                 ← DCI-style raw corpus (Doc 317 §4)
│   ├── downloaded PDFs indexed by SHA + metadata
│   ├── parsed abstracts + sections
│   ├── full-text search via embedded SQLite FTS5
│   └── terminal-style: grep/search/read over stored papers
│
└── SessionCaseBank             ← Memento-style episodic (Doc 313 §1)
    ├── past_research_sessions: {topic, report_path, quality_score}
    └── retrieval: "have I researched anything related to X before?"
```

### 3.4 Research Skills Library

Based on Doc 320 §1 (7-tuple skill formalism):

```
research_skills/
├── discovery/
│   ├── search_arxiv.skill        → query → [ResearchSource]
│   ├── search_openreview.skill   → query + venue → [ResearchSource]
│   ├── search_github.skill       → query + filters → [ResearchSource]
│   ├── search_semantic.skill     → query + semantic → [ResearchSource]
│   ├── search_huggingface.skill  → query → [ResearchSource]
│   └── traverse_citations.skill → paper_id → [ResearchSource]
│
├── analysis/
│   ├── analyze_paper.skill       → source → PaperAnalysis
│   ├── analyze_repo.skill        → source → RepositoryAnalysis
│   ├── extract_contributions.skill → paper → [Contribution]
│   └── score_quality.skill       → source → QualityScore
│
├── synthesis/
│   ├── synthesize_findings.skill → [Analysis] → Synthesis
│   ├── build_taxonomy.skill      → [Analysis] → Taxonomy
│   ├── find_gaps.skill           → [Analysis] → [Gap]
│   ├── map_relationships.skill   → [Analysis] → RelationshipGraph
│   └── detect_contradictions.skill → [Analysis] → [Contradiction]
│
├── reporting/
│   ├── generate_report.skill     → Synthesis → Report
│   ├── generate_comparison_table.skill → [Analysis] → Table
│   └── generate_gap_map.skill    → [Gap] → GapMap
│
└── memory/
    ├── extract_findings.skill    → Report → [MemoryRecord]
    ├── update_knowledge_graph.skill → Report → GraphDelta
    └── extract_strategy.skill    → Session → ResearchStrategy
```

### 3.5 Context Engineering Strategy

Following Doc 318's four verbs:

| Strategy | Application in Lyra Research |
|---|---|
| **Write** | After each session: research notes → ResearchNoteStore, findings → KnowledgeGraphStore, strategies → ResearchStrategyMemory |
| **Select** | Before each search: retrieve related past research notes, relevant strategies, known papers on topic |
| **Compress** | Paper abstracts compressed to structured JSON: {contribution, method, benchmark, result, weakness}. Long tool outputs truncated. |
| **Isolate** | Each source type runs in a parallel sub-agent (arXiv agent, GitHub agent, etc.) with scoped context. Synthesis agent gets only ranked summaries, not raw search dumps. |

---

## 4. Phase Plan

### Phase 0 — Specification & Architecture Design (Week 0, NOW)
**Deliverable:** This document. Approved architecture. No code yet.

**Tasks:**
- [x] Define the goal
- [x] Assess current state (existing packages)
- [x] Define architecture grounded in research docs
- [x] Map all phases
- [ ] User approves plan → Phase 1 begins

---

### Phase 1 — Research Discovery Engine (Weeks 1–2)
**Goal:** Complete multi-source discovery with quality ranking.

**Grounding:** Doc 317 §4 canonical systems, Doc 315 §3 OSS landscape

**Deliverables:**
1. `OpenReviewDiscovery` — search ICLR, NeurIPS, ICML, COLM papers by topic
2. `HuggingFacePapersDiscovery` — search HF Papers (daily ML paper feed)
3. `PapersWithCodeDiscovery` — search with reproducibility scores + SOTA tables
4. `ACLAnthologyDiscovery` — NLP/LLM-specific venue search
5. Enhanced `SemanticScholarDiscovery` — citation graph traversal (forward + backward)
6. Enhanced `GitHubDiscovery` — activity score (commits/month, issue velocity, contributor count)
7. `SourceQualityScorer` — multi-signal ranking: citations × recency × venue × relevance × stars
8. `CitationTraversal` — given a seed paper, find N generations of citing/cited papers

**Architecture impact:** Extends `lyra_research/discovery.py`, new source adapters

**Success criteria:**
- Given "agent memory systems" → returns top-30 real papers with accurate metadata
- Given "LLM agent memory" → returns top-20 real GitHub repos sorted by quality score
- All sources verified (no 404s, no hallucinated papers)

---

### Phase 2 — Research Intelligence Core (Weeks 2–3)
**Goal:** Transform raw discovery into verified, structured intelligence.

**Grounding:** RhinoInsight Pattern B (Doc 317 §5), Baby-AIGS falsification (Doc 317 §2)

**Deliverables:**
1. `VerifiableChecklistGenerator` — given topic → N researchable sub-questions
2. `EvidenceAudit` — maps each claim to ≥1 source; flags unverified claims
3. `ContradictionDetector` — finds conflicting claims across papers
4. `GapAnalyzer` — identifies under-researched sub-areas from the evidence
5. `FalsificationChecker` — for each major claim, finds counter-evidence (Baby-AIGS inspired)
6. `LLM-powered PaperAnalyzer` (replacing stub):
   - contribution, method, benchmark, headline_numbers, weaknesses, novelty
7. `LLM-powered RepositoryAnalyzer` (replacing stub):
   - purpose, quality_tier, activity_level, benchmark_support, key_techniques

**Architecture impact:** New `lyra_research/intelligence.py`, upgrades `analysis.py`

**Success criteria:**
- For "transformer attention mechanisms": produces a checklist with 8+ verifiable questions
- Every claim in output maps to a real source URL
- At least 1 contradiction/gap detected in any mature research area

---

### Phase 3 — Research Memory System (Weeks 3–5)
**Goal:** Research memory that persists across sessions and compounds knowledge.

**Grounding:** A-Mem (Doc 313), Graphiti temporal KG (Doc 315), DCI (Doc 317 §4),
ReasoningBank (Doc 313 §1), Memento case bank (Doc 313 §1)

**Deliverables:**
1. `ResearchNote` — extends MemoryRecord with: topic, findings, sources[], links[], quality
   - Zettelkasten-style: notes link to related notes by ID
   - New note creation can trigger evolution of linked old notes
2. `ResearchKnowledgeGraph` — extends KnowledgeGraph with:
   - Temporal edges (validity windows on relationships)
   - Node types: Paper, Repo, Concept, Author, Method, Dataset, Benchmark, Venue
   - Queries: "papers extending X", "repos implementing Y", "methods used by Z"
3. `LocalCorpus` — DCI-inspired local paper store:
   - SQLite with FTS5 for full-text search over downloaded papers
   - Stores: PDF metadata, abstract, parsed sections, source URL
   - Tool interface: `search_corpus(query)`, `read_paper(id)`, `find_related(id)`
4. `ResearchStrategyMemory` — ReasoningBank-style:
   - Saves successful search strategies with topic_type + outcome score
   - Saves failed strategies with root-cause lesson
   - Retrieves domain-matched strategies for new queries
5. `SessionCaseBank` — Memento-inspired:
   - Saves each completed research session as a case
   - Retrieves similar past sessions when new query overlaps
   - "I researched agent memory 2 weeks ago — here's what I found"
6. `ResearchMemoryController` — decides what to write, update, expire:
   - Checks for contradiction with existing notes before writing
   - Supersedes outdated facts when newer evidence found
   - Promotes high-confidence findings from episodic → semantic memory

**Architecture impact:** Major expansion of `lyra_memory/` and new
`lyra_research/memory_bridge.py`

**Success criteria:**
- Second research session on related topic is measurably faster (pre-populated context)
- Knowledge graph has ≥50 nodes after 3 research sessions
- Strategy memory retrieves a relevant past strategy for 80%+ of new queries on known domains

---

### Phase 4 — Research Synthesis & Report Engine (Weeks 4–6)
**Goal:** Generate dense, citation-grounded, publication-quality research reports.

**Grounding:** RhinoInsight report pipeline (Doc 317), 42AI paper authoring (Doc 317 §3),
ResearcherBench quality metrics (Doc 317 §2)

**Deliverables:**
1. `CrossSourceSynthesizer` — LLM-powered, receives ranked analyses → produces:
   - Field taxonomy (categories, sub-areas, relationships)
   - "Best paper" per sub-area with justification
   - "Best repo" per use-case with justification
   - How papers relate: extends/contradicts/implements/benchmarks
2. `ResearchReportGenerator` — produces structured Markdown report:

   ```
   # Deep Research: <Topic>
   
   ## Executive Summary (3 bullets)
   ## Field Taxonomy
   ## Best Papers
   ### Sub-area A
   | Paper | Venue | Year | Core Contribution | Results | Weakness |
   ## Best GitHub Repos
   | Repo | Stars | Purpose | Quality Tier | Key Feature |
   ## Key Concepts & Methods
   ## Relationships & Architecture Patterns
   ## Research Gaps
   ## Contested Claims & Counter-Evidence
   ## Recommended Reading Order
   ## Next Steps for Researcher / Practitioner
   ## References (all verified)
   ```

3. `CitationBinder` — ensures every claim in report has a `[source_id]` tag backed by a
   real fetched source — no hallucinated citations
4. `ReportQualityChecker` — self-evaluates report before delivery:
   - Completeness: checklist items addressed?
   - Citation fidelity: all sources verified?
   - Insight depth: surface stats vs. actual understanding?
   - Contradiction coverage: contested claims flagged?

**Architecture impact:** New `lyra_research/reporter.py`, upgrade `synthesis.py`

**Success criteria:**
- Report for "LLM agent memory 2026" passes all 4 quality checks
- Zero hallucinated citations (every reference is a real fetched URL)
- Report has ≥3 comparison tables, ≥1 gap map, ≥5 cited repos

---

### Phase 5 — Research Skills Library (Weeks 5–7)
**Goal:** Skills that accumulate domain expertise and improve query quality over time.

**Grounding:** Doc 320 (Skills 7-tuple), Doc 313 ReasoningBank §1,
Doc 318 Context Engineering Write strategy

**Deliverables:**
1. `ResearchSkillStore` — based on lyra-skills package + MemSkill patterns:
   - Skills stored as callable YAML/JSON with interface + verifier + lineage
   - Skills can be added, refined, pruned, composed
2. Domain-specific search skill templates:
   - `ml_paper_search.skill` — ML/DL specific: prefers ICLR/NeurIPS/ICML/COLM, uses benchmark scores
   - `nlp_paper_search.skill` — NLP: prefers ACL/EMNLP/NAACL + arXiv cs.CL
   - `systems_paper_search.skill` — prefers SOSP/OSDI/USENIX + GitHub activity
   - `general_research.skill` — fallback for unknown domains
3. `QueryRefinementSkill` — LLM-powered, learns from past queries:
   - Detects when initial query is too broad/narrow
   - Suggests better query formulations based on early results
4. `StrategyAdaptationSkill` — switches between strategies mid-research:
   - BREADTH_FIRST for survey
   - DEPTH_FIRST for deep-dive
   - CITATION_SNOWBALL for finding related work chains
   - Adapts based on discovered source density
5. `SkillEvolution` — after each research session:
   - Scores skill performance (result quality × coverage × time)
   - Saves delta to ResearchStrategyMemory
   - Proposes skill refinements for user approval

**Architecture impact:** Extends `lyra_skills/`, new `lyra_research/skills.py`

**Success criteria:**
- ML query uses ml_paper_search skill and returns conference-paper-dominated results
- After 5 sessions on same domain, query quality improves measurably (more relevant top-10)
- Skill evolution proposes ≥1 refinement per 3 sessions

---

### Phase 6 — Deep Research TUI Integration (Weeks 6–8)
**Goal:** First-class `/research` UX inside Lyra's terminal interface.

**Grounding:** Doc 318 Isolate strategy (parallel agents), Doc 319 agent-ops UX

**Deliverables:**
1. `/research <topic>` command:
   - Triggers the full 10-step controlled research pipeline
   - Shows real-time progress panel in TUI
2. Research progress display (new TUI panel):
   ```
   ┌─ Research: agent memory systems ─────────────────────┐
   │ [1/10] Clarifying research scope...          ✓       │
   │ [2/10] Generating checklist (8 questions)... ✓       │
   │ [3/10] Searching sources...                          │
   │   arXiv: 47 results  ████████░░ 80%                 │
   │   GitHub: 23 results ██████░░░░ 60%                 │
   │   OpenReview: ...    ████░░░░░░ 40%                 │
   │ [4/10] Filtering & ranking...                        │
   └──────────────────────────────────────────────────────┘
   ```
3. `/research list` — shows past research sessions with topic + date + quality score
4. `/research show <id>` — loads a past research report
5. `/research related <topic>` — finds prior sessions with related topics
6. Research report viewer — renders Markdown reports in-TUI with scrolling
7. Memory sidebar tab (Research) — shows research notes, knowledge graph stats,
   strategy count, corpus size

**Architecture impact:** New commands in `lyra_cli/commands/`, TUI panel in
`lyra_cli/tui_v2/`

**Success criteria:**
- `/research agent memory` runs end-to-end from TUI and shows progress
- Report renders correctly in TUI
- `/research list` shows 3+ past sessions after initial use

---

### Phase 7 — Research Quality Evaluation (Weeks 7–9)
**Goal:** Measure research quality so Lyra can improve continuously.

**Grounding:** DeepResearch-ReportEval (Doc 317 §2), ResearcherBench (Doc 317 §2),
FML-bench exploration metrics (Doc 317 §2), MemoryAgentBench (Doc 313 §1)

**Deliverables:**
1. `ResearchQualityMetrics` — 6-axis evaluation:

   | Metric | Measurement | Target |
   |---|---|---|
   | Coverage | checklist items answered / total items | ≥0.85 |
   | Citation Fidelity | verified citations / total citations | 1.00 |
   | Source Breadth | unique sources used / sources found | ≥0.60 |
   | Insight Depth | LLM-judged insight vs. surface stats | ≥0.75 |
   | Gap Detection | gaps identified / known gaps in field | ≥0.60 |
   | Contradiction Coverage | contested claims flagged / total contested | ≥0.50 |

2. `SelfEvaluationAgent` — after each report, runs quality check and reports scores
3. `BenchmarkAdapter` — integrates with ResearcherBench-style evaluation:
   - 65 frontier AI research questions adapted to Lyra's research domains
   - Track faithfulness and groundedness scores over time
4. `QualityTrendTracker` — stores quality scores per session, plots improvement over time
5. Automatic quality gates: report is not delivered until Coverage ≥0.75 and
   Citation Fidelity = 1.00

**Architecture impact:** New `lyra_evals/research_quality.py`

**Success criteria:**
- Quality metrics computed automatically after each session
- Citation Fidelity = 1.00 for all reports (no hallucinations)
- Coverage ≥0.80 average after 10 sessions

---

### Phase 8 — Continual Research Learning (Weeks 8–10)
**Goal:** Lyra gets measurably smarter at research with each session.

**Grounding:** ReasoningBank (Doc 313 §1), Memento case-based reasoning (Doc 313 §1),
AgentRxiv collaborative reuse (Doc 317 §2), Darwin Gödel Machine self-improvement (Doc 317 §4)

**Deliverables:**
1. `ResearchStrategyExtractor` — ReasoningBank-inspired:
   - After each successful session: "what search strategy worked best here?"
   - After each failed fetch or poor result: "what went wrong and why?"
   - Stores as typed strategy records with topic_type, outcome_score, key_steps
2. `CaseSelectionPolicy` — Memento-inspired:
   - Learns to select the best past case for a new research query
   - Uses topic similarity + domain match + outcome score
   - Online update without retraining the base LLM
3. `DomainExpertiseAccumulator` — per domain (ML, NLP, systems, etc.):
   - Builds a domain model: key venues, key researchers, landmark papers, key benchmarks
   - Used to bootstrap every new research session in that domain
   - Updates after each session with new discoveries
4. `ResearchWorkflowOptimizer` — analyzes patterns across sessions:
   - Which sources consistently have highest-quality results per domain?
   - Which query formulations produce most relevant top-10?
   - What stopping criteria should trigger for this domain?
5. `SelfImprovementGate` — before any skill/strategy update is applied:
   - Runs on ≥2 test research sessions
   - Update only applies if quality metrics improve
   - Full rollback if quality drops

**Architecture impact:** Extends `lyra_evolution/`, `lyra_memory/evolution.py`

**Success criteria:**
- Session 10 measurably better than Session 1 on same topic type (quality metrics)
- Domain expertise model for ML papers has ≥5 key venues, ≥20 landmark papers
- 0 regressions from any self-improvement update (gate works)

---

## 5. Implementation Sequence (10 Weeks)

```
Week  1   Phase 1: OpenReview, HuggingFace, PwC, Semantic Scholar citation traversal
Week  2   Phase 1: GitHub quality scoring + Phase 2: VerifiableChecklist + EvidenceAudit
Week  3   Phase 2: GapAnalyzer, FalsificationChecker + LLM-powered analyzers
Week  4   Phase 3: ResearchNote store, LocalCorpus (DCI-style)
Week  5   Phase 3: KnowledgeGraph, StrategyMemory, SessionCaseBank
Week  6   Phase 4: CrossSourceSynthesizer, ResearchReportGenerator, CitationBinder
Week  7   Phase 5: ResearchSkillStore, domain skills + Phase 6: /research command
Week  8   Phase 6: TUI panels + Phase 7: ResearchQualityMetrics
Week  9   Phase 7: SelfEvaluationAgent, BenchmarkAdapter
Week 10   Phase 8: StrategyExtractor, CaseSelectionPolicy, WorkflowOptimizer
```

---

## 6. Tech Stack Decisions

| Concern | Choice | Rationale |
|---|---|---|
| Paper search APIs | arxiv-py, Semantic Scholar API, OpenReview API | existing Python clients |
| GitHub search | PyGithub + GitHub REST API | existing in discovery.py |
| PDF parsing | pypdf2 + pymupdf (fitz) | reliable local parsing |
| Vector embeddings | sentence-transformers (local) | privacy-preserving, no API cost |
| Local corpus search | SQLite FTS5 | zero-dependency full-text search |
| Knowledge graph | NetworkX + SQLite persistence | lightweight, no external server |
| LLM calls | Claude Haiku for analysis, Sonnet/Opus for synthesis | matches Doc 318 routing |
| Report output | Markdown + optional PDF via pandoc | universal format |
| Test framework | pytest + hypothesis | existing in all packages |

---

## 7. Risk Map

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| API rate limits (Semantic Scholar, GitHub) | High | Medium | Exponential backoff + local cache |
| LLM hallucinated citations | High | Critical | CitationBinder + EvidenceAudit gates |
| PDF parsing failures | Medium | Low | Fallback to abstract-only mode |
| Knowledge graph becomes stale | Medium | Medium | Temporal validity windows + auto-expire |
| Research strategy memory drift | Low | Medium | Quality gates on every strategy update |
| Context window overflow on large topics | Medium | High | Compress + Isolate strategies (Doc 318) |
| OpenReview API instability | Medium | Low | Cache aggressively, degrade gracefully |

---

## 8. Relationship to Existing Evolution Plan

This plan is **additive**, not a replacement, to `LYRA_EVOLUTION_MASTER_PLAN.md`.

| Existing Evolution Goal | Relationship |
|---|---|
| Phase 1: Memory Foundation | Phase 3 (Research Memory) extends and specializes it |
| Phase 2: Skills Library | Phase 5 (Research Skills) builds on top of it |
| Phase 3: Self-Evolution Engine | Phase 8 (Continual Learning) is the research-domain instance |
| Phase 4: Multi-Agent Orchestration | Phase 2 + 6 use parallel source agents |
| Phase 5: Evaluation | Phase 7 (Research Quality) provides concrete metrics |

The **research agent capability is the primary user-facing feature**. Self-evolution (writing
Lyra's own code) is a longer-horizon goal. Research intelligence is the immediate value.

---

## 9. Definition of "Done" for Each Phase

| Phase | Done When |
|---|---|
| Phase 0 | This plan approved; no code written yet |
| Phase 1 | `/research agent memory` finds ≥5 real papers from ≥3 sources |
| Phase 2 | Checklist generated; all claims in output traced to sources; ≥1 gap found |
| Phase 3 | Second session on related topic shows pre-populated context; KG has nodes |
| Phase 4 | Full Markdown report generated; 0 hallucinated citations; tables present |
| Phase 5 | Domain skills retrieved correctly; strategy memory updated after session |
| Phase 6 | `/research` command works in TUI with live progress panel |
| Phase 7 | Quality metrics computed automatically; Coverage ≥0.80; Fidelity = 1.00 |
| Phase 8 | Session 10 measurably better than Session 1 on same topic type |

---

## 10. First Implementation Checklist (Phase 1, Week 1)

Before any other phase begins, these must be true:

- [ ] `OpenReviewDiscovery` returns real ICLR/NeurIPS/ICML papers for a query
- [ ] `HuggingFacePapersDiscovery` returns real ML papers from HF Papers feed
- [ ] `PapersWithCodeDiscovery` returns real papers with reproducibility scores
- [ ] `CitationTraversal` given arXiv ID, returns 5+ real citing papers
- [ ] `GitHubDiscovery` returns repos with quality score (not just star count)
- [ ] `SourceQualityScorer` ranks results sensibly (landmark papers rise to top)
- [ ] All unit tests pass (`pytest packages/lyra-research/`)
- [ ] Integration test: "agent memory 2026" query → top-10 results verified manually

---

*This plan is grounded in 9 research synthesis documents (313–321) covering 2,000+ pages of
research on AI agents, memory systems, context engineering, skills, and research agent
architectures. Implementation should not begin until this plan is reviewed and approved.*

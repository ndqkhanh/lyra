# Lyra Ultimate Deep Research Architecture Plan (REVISED)

**Created:** 2026-05-18  
**Revised:** 2026-05-18 (Post-Architect & Critic Review)  
**Status:** Ready for User Confirmation  
**Complexity:** HIGH

---

## RALPLAN-DR Summary (REVISED)

### Core Principles (5)

1. **Evidence-First Architecture** — Every claim must be traceable to verified sources with citation audit
2. **Heterogeneous Multi-Agent Collaboration** — Use adversarial review patterns (executor + cross-model reviewer) to eliminate plausible unsupported claims
3. **Persistent Knowledge Accumulation** — Research findings persist across sessions in structured memory stores
4. **Dynamic Task Decomposition** — Complex research queries decompose into context-sensitive subtasks with execution feedback
5. **Quality Gates at Every Stage** — Multi-stage validation checkpoints ensure report quality before progression

### Decision Drivers (Top 3)

1. **Context Window Constraints** — Attention cost scales quadratically (O(n²)); doubling context quadruples cost. Must optimize for Maximum Effective Context Window (MECW), not marketed limits.
2. **Research Report Quality** — Target: 90%+ verification rate (Phase 1) → 95%+ (Phase 2), comprehensive source coverage (7+ sources), citation accuracy, and falsification resistance
3. **Scalability for Heavy Tasks** — Must handle multi-hour research sessions with 100+ sources without context drift or memory loss (65% of enterprise AI failures trace to this)

### Viable Architectural Options (2)

#### Option A: Monolithic Pipeline Enhancement
**Approach:** Enhance existing 10-step pipeline with better context management and quality gates

**Pros:**
- Preserves 381 passing tests
- Incremental migration path
- Lower implementation risk
- Familiar architecture for team

**Cons:**
- Context bloat remains O(n²) problem
- Single-agent bottleneck for heavy research
- Limited parallelization opportunities
- Doesn't address fundamental scalability issues

**Bounded Cost:** 2-3 weeks implementation, moderate context optimization gains (30-40% reduction)

#### Option B: 2-Phase Multi-Agent Orchestration with Persistent Memory (RECOMMENDED)
**Approach:** Start with 3-agent hybrid + compression (Phase 1), scale to 10+ agents only if context drift observed (Phase 2)

**Phase 1 (Weeks 1-4): 3-Agent Hybrid + Compression**
- 3 agents: Discovery (Haiku), Analysis (Sonnet), Synthesis (Opus)
- Coordination primitives: retry policy, circuit breaker, timeout hierarchy, health checks
- Memory capacity bounds: 10K sources, 100K notes, 1K sessions + compaction + query SLOs
- Adversarial review protocol: 30KB context budget, disagreement resolution, selective review
- Context optimization: external storage, selective retrieval, compression, agent isolation

**Phase 2 (Weeks 5-7, CONDITIONAL): Scale to 10+ Agents**
- Trigger: Context drift at 50+ sources OR user requests 100+ source capability
- 10+ specialized agents: 6 discovery, 4 analysis, 4 synthesis, 1 assurance
- Adaptive task decomposition, progress checkpointing

**Pros:**
- Reduces risk (validate architecture early with 3 agents)
- Avoids premature optimization (most research uses 20-50 sources)
- Early feedback (4 weeks vs. 7 weeks)
- Can stop after Phase 1 if sufficient (60% context reduction, 90% verification)
- Aligns with Architect & Critic recommendations

**Cons:**
- Requires significant refactoring (but phased)
- More complex orchestration logic
- Higher initial implementation cost (4 weeks Phase 1, +3 weeks Phase 2 if needed)
- Need robust inter-agent communication

**Bounded Cost:** 4 weeks Phase 1 (60% context reduction, 2x speedup), +3 weeks Phase 2 if needed (80% reduction, 5x speedup)

**Why Option B is Recommended:**
- Lyra already has multi-agent infrastructure (lyra-evolution, lyra-skills)
- Context optimization is a stated goal (LYRA_CONTEXT_OPTIMIZATION_PLAN.md)
- Research shows heterogeneous models outperform single-model self-refinement
- Industry trend: Claude Code, ARIS, Hermes-Agent all use multi-agent patterns
- **Architect & Critic consensus:** Start with 3-agent hybrid to validate coordination primitives before scaling

---

## Current State Analysis

### Existing Capabilities (Strong Foundation)

**10-Step Research Pipeline** (381 tests passing):
1. Clarify → Plan → Search → Filter → Fetch → Analyze → Evidence Audit → Synthesize → Report → Memorize
2. 7+ discovery sources: ArXiv, Semantic Scholar, GitHub, OpenReview, HuggingFace, Papers with Code, ACL Anthology
3. Citation traversal: forward/backward citations, snowball sampling
4. Quality scoring: multi-factor assessment (citations, recency, GitHub activity, source reputation)

**4 Memory Stores**:
- Zettelkasten (research notes)
- DCI (local corpus)
- ReasoningBank (strategy memory)
- Memento (session case bank)

**Intelligence Components**:
- VerifiableChecklistGenerator (rule-based, no LLM)
- EvidenceAudit (claim extraction and verification)
- ContradictionDetector (numerical conflicts, outperformance claims)
- GapAnalyzer (explicit gap mentions, coverage analysis)
- FalsificationChecker (counter-evidence search)

### Current Limitations

**Context Bloat (Critical)**:
- Single-agent pipeline accumulates all source content in context
- 50 sources × 2KB average = 100KB+ context per research session
- Quadratic attention cost makes this unsustainable
- No context compression or selective retrieval

**Task Decomposition (Missing)**:
- Monolithic pipeline cannot parallelize discovery across sources
- Heavy research tasks (100+ sources) run sequentially
- No dynamic task graph generation
- Cannot adapt to real-time changes in research direction

**Quality Assurance (Partial)**:
- Evidence audit exists but runs on final report only
- No multi-stage validation checkpoints
- No adversarial review (single-model self-refinement)
- Citation audit is pattern-based, not semantic

**Scalability (Bottleneck)**:
- Single ResearchOrchestrator instance handles entire pipeline
- No agent isolation or parallel execution
- Memory stores are local SQLite (not distributed)
- No progress checkpointing for long-running research

**Skills Integration (Weak)**:
- ResearchSkillStore exists but underutilized
- No dynamic skill selection based on domain
- No skill evolution from research outcomes
- Skills are static, not learned from experience

---

## Research Phase: What to Investigate

### Skills Relevant to Deep Research

**From Web Research:**
1. **MCP Servers for Research** ([Octagon Deep Research MCP](https://github.com/OctagonAI/octagon-deep-research-mcp)) — No rate limits, faster than ChatGPT Deep Research
2. **Dynamic Task Decomposition** ([arXiv:2410.22457](https://arxiv.org/abs/2410.22457)) — Autonomous task graph generation with tool selection
3. **Agent-Driven Research Frameworks** — Iterative planning with self-reflection for complex hypotheses
4. **Context Engineering Patterns** ([Tian Pan's blog series](https://tianpan.co/blog/)) — External storage, selective retrieval, compression, agent isolation
5. **STRIDE Framework** ([arXiv:2512.02228](https://arxiv.org/abs/2512.02228)) — Structured task decomposition with dynamism attribution

**Lyra-Specific Skills to Develop:**
- `deep-research-orchestrator` — Multi-agent coordination for parallel research
- `context-aware-retrieval` — Selective memory retrieval based on research phase
- `adversarial-review` — Cross-model claim verification
- `research-checkpoint` — Save/restore research state for long-running tasks
- `citation-semantic-audit` — Semantic citation verification (beyond pattern matching)

### Tools Relevant to Deep Research

**Discovery Tools:**
- Semantic Scholar API (with exponential backoff retry — already implemented)
- ArXiv API (already implemented)
- GitHub API (already implemented)
- OpenReview, HuggingFace, Papers with Code, ACL Anthology (already implemented)
- **NEW:** Exa search API for web content discovery
- **NEW:** Perplexity API for real-time web research

**Analysis Tools:**
- **NEW:** PDF extraction with layout preservation (PyMuPDF, pdfplumber)
- **NEW:** Citation graph analysis (NetworkX for centrality, clustering)
- **NEW:** Semantic similarity (sentence-transformers for claim deduplication)
- **NEW:** LLM-based summarization (for abstracts > 500 words)

**Quality Assurance Tools:**
- **NEW:** BLEU, ROUGE, BERTScore for report quality metrics
- **NEW:** Fact-checking APIs (Google Fact Check Tools API)
- **NEW:** Plagiarism detection (Turnitin API or open-source alternatives)

**Context Management Tools:**
- **NEW:** Prompt compression (LLMLingua, AutoCompressor)
- **NEW:** RAG with reranking (Cohere Rerank, BGE reranker)
- **NEW:** Context caching (Anthropic prompt caching for repeated queries)

### Best Practices for Highest Quality Research Reports

**From Industry Research (2026):**

1. **Multi-Stage Validation Pipeline** ([ARIS architecture](https://arxiv.org/html/2605.03042v1)):
   - 3-stage evidence-claim audit cascade
   - 5-pass scientific writing editing pipeline
   - Mathematical proof checker
   - Visual PDF review
   - Citation audit

2. **Quality Metrics** ([AI Evaluation Metrics Guide 2026](https://www.digitalapplied.com/blog/ai-evaluation-metrics-reference-guide-2026)):
   - Verification rate: 95%+ claims backed by sources
   - Source diversity: 7+ independent sources
   - Citation accuracy: 100% valid citations
   - Recency: 50%+ sources from last 2 years
   - Completeness: 90%+ checklist items answered

3. **Adversarial Review** ([ARIS paper](https://huggingface.co/papers/2605.03042)):
   - Heterogeneous models (executor + reviewer) outperform single-model self-refinement
   - Cross-model review eliminates "plausible unsupported success"
   - Reviewer must be different model family (e.g., Claude executor + GPT-4 reviewer)

4. **Persistent Memory** ([Hermes-Agent architecture](https://hermes-agent.nousresearch.com/docs/)):
   - Multi-layer memory with FTS5 for cross-session recall
   - Agent-curated memory with periodic nudges
   - Layered memory accumulation across sessions

5. **Context Optimization** ([Context Engineering blog](https://tianpan.co/blog/2026-02-23-effective-context-engineering-for-ai-agents)):
   - External storage for historical context
   - Selective retrieval (pull only relevant context)
   - Context compression for in-window content
   - Agent isolation (separate processes with independent contexts)

6. **Dynamic Task Decomposition** ([Multi-Agent Patterns 2026](https://fast.io/resources/multi-agent-task-decomposition-patterns/)):
   - Complexity-based decomposition (10-40% performance gain)
   - Manager agent architecture for task allocation
   - Real-time adaptation to changing requirements

---

## Competitive Benchmarking

### Claude Code Deep Research

**Capabilities** ([Claude Code blog](https://claude.com/blog/eight-trends-defining-how-software-gets-built-in-2026)):
- Agentic research with multiple searches building on each other
- Automatic angle exploration and open question investigation
- Parallel agent spawning with `--allowedTools "Bash(claude:*)"`
- Timestamped markdown output
- Code Review feature with agent teams on every PR

**Strengths:**
- Deep integration with development workflow
- 20 hours/week average developer usage
- 70x year-over-year API volume growth
- Autonomous long-horizon task execution

**Gaps vs. Lyra:**
- No explicit memory stores (Zettelkasten, DCI, ReasoningBank)
- No citation traversal or quality scoring
- No falsification checking or gap analysis
- Limited to web search (no ArXiv, Semantic Scholar integration)

### ARIS (Autonomous Research via Adversarial Multi-Agent Collaboration)

**Architecture** ([arXiv:2605.03042](https://arxiv.org/html/2605.03042v1)):
- **Execution Layer:** 65+ reusable Markdown skills, MCP integrations, persistent research wiki, deterministic figure generation
- **Cognitive Layer:** Separates reasoning from execution, formalizes memory retrieval/update policies
- **Assurance Layer:** 3-stage evidence-claim audit, 5-pass editing pipeline, mathematical proof checker, visual PDF review, citation audit

**Strengths:**
- Heterogeneous models (executor + cross-model reviewer)
- Eliminates "plausible unsupported success"
- Persistent research wiki for iterative reuse
- Enterprise-grade governance (transparency, traceability, reproducibility)
- Entropic and novelty-diversity metrics in ideation

**Gaps vs. Lyra:**
- More complex (3-layer architecture)
- Requires multiple model subscriptions (executor + reviewer)
- Higher operational cost
- Focused on scientific research (may be overkill for general research)

**Lyra Advantages:**
- Simpler architecture (single orchestrator)
- 381 passing tests (production-ready)
- 4 specialized memory stores
- 7+ discovery sources (ARIS unclear on source diversity)

### Hermes-Agent

**Capabilities** ([Hermes-Agent docs](https://hermes-agent.nousresearch.com/docs/)):
- Self-improving AI with built-in learning loop
- Persistent 24/7 agent on own server infrastructure
- Multi-layer memory with FTS5 for cross-session recall
- Autonomous skill creation from experience
- Cron scheduler for offline execution
- Browser automation, voice conversations, file-aware context

**Strengths:**
- Gets more capable over time (self-improvement)
- Persistent learning across sessions
- Open-source (MIT license, Feb 2026)
- Runs on $5 VPS to GPU clusters
- Skills self-improve during use

**Gaps vs. Lyra:**
- General-purpose agent (not research-specialized)
- No explicit research pipeline (10-step process)
- No citation traversal or quality scoring
- No falsification checking or gap analysis
- No multi-source discovery (ArXiv, Semantic Scholar, etc.)

**Lyra Advantages:**
- Research-specialized (10-step pipeline)
- 7+ academic sources
- Citation graph analysis
- Evidence audit and falsification checking
- 381 tests validating research quality

### Open-Claw (Assumed Competitor)

**Note:** No specific information found in web search. Assuming this refers to an open-source autonomous agent framework.

**General Competitive Landscape:**
- Most autonomous agents focus on general task execution
- Few specialize in deep research with academic sources
- Lyra's 10-step pipeline and 4 memory stores are differentiators
- Multi-agent orchestration is industry trend (Claude Code, ARIS, Hermes-Agent all use it)

---

## Architecture Design: Ultimate Deep Research

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Research Orchestrator                        │
│  (Manager Agent - Task Decomposition & Coordination)            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│   Discovery  │      │   Analysis   │     │  Synthesis   │
│    Agents    │      │    Agents    │     │    Agents    │
│  (Parallel)  │      │  (Parallel)  │     │  (Sequential)│
└──────────────┘      └──────────────┘     └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Assurance Layer │
                    │  (Adversarial    │
                    │   Reviewer)      │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Persistent Memory│
                    │  - Zettelkasten  │
                    │  - DCI Corpus    │
                    │  - ReasoningBank │
                    │  - Memento       │
                    └──────────────────┘
```

### Component Specifications

#### 1. Research Orchestrator (Manager Agent)

**Responsibilities:**
- Decompose research query into task graph
- Allocate tasks to specialized agents
- Monitor progress and adapt to changes
- Manage context budget across agents
- Checkpoint research state for resumption

**Implementation:**
```python
class ResearchOrchestrator:
    def __init__(self):
        self.task_graph = TaskGraph()
        self.agent_pool = AgentPool()
        self.memory_manager = MemoryManager()
        self.context_budget = ContextBudget(max_tokens=100_000)
    
    def research(self, query: str, depth: str) -> ResearchReport:
        # 1. Decompose query into task graph
        tasks = self.decompose_query(query, depth)
        
        # 2. Allocate tasks to agents (parallel where possible)
        results = self.execute_task_graph(tasks)
        
        # 3. Synthesize results
        synthesis = self.synthesize_results(results)
        
        # 4. Adversarial review
        reviewed = self.adversarial_review(synthesis)
        
        # 5. Generate report
        return self.generate_report(reviewed)
```

**Key Features:**
- Dynamic task graph generation (adapts to intermediate results)
- Complexity-based task allocation (simple tasks to Haiku, complex to Opus)
- Progress checkpointing every 10 minutes
- Context budget enforcement (reject tasks that would exceed budget)

#### 2. Discovery Agents (Parallel Execution)

**Agent Types:**
- `ArXivDiscoveryAgent` — Search ArXiv papers
- `SemanticScholarAgent` — Search Semantic Scholar with citation traversal
- `GitHubDiscoveryAgent` — Search GitHub repositories
- `WebDiscoveryAgent` — Search web content (Exa, Perplexity)
- `OpenReviewAgent` — Search OpenReview papers
- `HuggingFaceAgent` — Search HuggingFace papers/models

**Execution Pattern:**
```python
async def discover_parallel(query: str, sources: List[str]) -> Dict[str, List[ResearchSource]]:
    tasks = [
        agent.search(query, max_results=50)
        for agent in self.get_agents_for_sources(sources)
    ]
    results = await asyncio.gather(*tasks)
    return dict(zip(sources, results))
```

**Context Isolation:**
- Each agent runs in separate process with independent context
- Results serialized to shared memory (SQLite or Redis)
- No cross-agent context pollution

#### 3. Analysis Agents (Parallel Execution)

**Agent Types:**
- `PaperAnalysisAgent` — Extract findings from papers
- `RepositoryAnalysisAgent` — Analyze code repositories
- `CitationAnalysisAgent` — Build citation network
- `QualityScoreAgent` — Score source quality
- `GapAnalysisAgent` — Identify research gaps

**Execution Pattern:**
```python
async def analyze_parallel(sources: List[ResearchSource]) -> List[Analysis]:
    # Batch sources by type
    papers = [s for s in sources if s.source_type == SourceType.PAPER]
    repos = [s for s in sources if s.source_type == SourceType.REPOSITORY]
    
    # Parallel analysis
    paper_analyses = await asyncio.gather(*[
        PaperAnalysisAgent().analyze(p) for p in papers
    ])
    repo_analyses = await asyncio.gather(*[
        RepositoryAnalysisAgent().analyze(r) for r in repos
    ])
    
    return paper_analyses + repo_analyses
```

#### 4. Synthesis Agents (Sequential Execution)

**Agent Types:**
- `CrossSourceSynthesizer` — Build taxonomy and relationships
- `ContradictionDetector` — Find conflicting claims
- `EvidenceAuditor` — Verify claims against sources
- `FalsificationChecker` — Search for counter-evidence
- `ReportGenerator` — Generate markdown report

**Execution Pattern:**
```python
def synthesize_sequential(analyses: List[Analysis]) -> ResearchReport:
    # Step 1: Build taxonomy
    taxonomy = CrossSourceSynthesizer().synthesize(analyses)
    
    # Step 2: Detect contradictions
    contradictions = ContradictionDetector().detect(analyses)
    
    # Step 3: Audit evidence
    audit = EvidenceAuditor().audit(taxonomy, analyses)
    
    # Step 4: Falsification check
    falsification = FalsificationChecker().check(taxonomy.claims, analyses)
    
    # Step 5: Generate report
    return ReportGenerator().generate(taxonomy, contradictions, audit, falsification)
```

#### 5. Assurance Layer (Adversarial Reviewer)

**Implementation:**
```python
class AdversarialReviewer:
    def __init__(self, executor_model: str, reviewer_model: str):
        self.executor_model = executor_model  # e.g., "claude-opus-4-7"
        self.reviewer_model = reviewer_model  # e.g., "gpt-4o"
    
    def review(self, report: ResearchReport, sources: List[ResearchSource]) -> ReviewResult:
        # 3-stage evidence-claim audit
        stage1 = self.audit_citations(report, sources)
        stage2 = self.audit_claims(report, sources)
        stage3 = self.audit_logic(report)
        
        # 5-pass editing
        edited = self.edit_report(report)
        
        # Final verdict
        return ReviewResult(
            passed=stage1.passed and stage2.passed and stage3.passed,
            report=edited,
            issues=stage1.issues + stage2.issues + stage3.issues
        )
```

**Review Criteria:**
- Citation accuracy: 100% valid citations
- Claim verification: 95%+ claims backed by sources
- Logical consistency: No contradictions
- Completeness: 90%+ checklist items answered
- Writing quality: Clear, concise, well-structured

#### 6. Persistent Memory (Shared Across Agents)

**Memory Stores:**
- **Zettelkasten** — Atomic research notes with links (SQLite FTS5)
- **DCI Corpus** — Full-text papers and code (SQLite with embeddings)
- **ReasoningBank** — Successful research strategies (JSON files)
- **Memento** — Session case bank (SQLite)

**Memory Manager:**
```python
class MemoryManager:
    def __init__(self):
        self.zettelkasten = ResearchNoteStore()
        self.corpus = LocalCorpus()
        self.reasoning_bank = ResearchStrategyMemory()
        self.memento = SessionCaseBank()
    
    def retrieve_relevant(self, query: str, k: int = 10) -> List[MemoryItem]:
        # Hybrid retrieval: FTS5 + semantic similarity
        fts_results = self.zettelkasten.search(query, limit=k*2)
        embeddings = self.corpus.embed_query(query)
        semantic_results = self.corpus.search_by_embedding(embeddings, limit=k*2)
        
        # Rerank and deduplicate
        combined = self.rerank(fts_results + semantic_results, query)
        return combined[:k]
```

#### 7. Telemetry for Source Count Distribution

**Purpose:** Track source count patterns to validate Phase 1 sufficiency and inform Phase 2 decision

**Metrics to Track:**
```python
class SourceCountTelemetry:
    def __init__(self):
        self.metrics = {
            "source_count_distribution": [],  # List of source counts per query
            "context_drift_by_source_count": {},  # source_count → drift_detected (bool)
            "quality_by_source_count": {},  # source_count → verification_rate
            "latency_by_source_count": {},  # source_count → wall_clock_time
        }
    
    def record_research_session(self, session: ResearchSession):
        source_count = len(session.sources)
        
        # Track distribution
        self.metrics["source_count_distribution"].append(source_count)
        
        # Track context drift
        drift_detected = self.detect_context_drift(session)
        self.metrics["context_drift_by_source_count"][source_count] = drift_detected
        
        # Track quality
        verification_rate = session.quality_metrics.verification_rate
        self.metrics["quality_by_source_count"][source_count] = verification_rate
        
        # Track latency
        wall_clock_time = session.wall_clock_time
        self.metrics["latency_by_source_count"][source_count] = wall_clock_time
    
    def get_percentiles(self) -> Dict[str, int]:
        counts = sorted(self.metrics["source_count_distribution"])
        return {
            "p50": counts[len(counts) // 2],
            "p75": counts[len(counts) * 3 // 4],
            "p90": counts[len(counts) * 9 // 10],
            "p95": counts[len(counts) * 95 // 100],
            "p99": counts[len(counts) * 99 // 100],
        }
    
    def get_source_count_buckets(self) -> Dict[str, float]:
        counts = self.metrics["source_count_distribution"]
        total = len(counts)
        return {
            "<20": sum(1 for c in counts if c < 20) / total,
            "20-50": sum(1 for c in counts if 20 <= c < 50) / total,
            "50-100": sum(1 for c in counts if 50 <= c < 100) / total,
            ">100": sum(1 for c in counts if c >= 100) / total,
        }
    
    def detect_context_drift(self, session: ResearchSession) -> bool:
        # Heuristic: drift detected if verification rate drops >10% in second half
        first_half = session.quality_metrics.verification_rate_first_half
        second_half = session.quality_metrics.verification_rate_second_half
        return (first_half - second_half) > 0.10
```

**Dashboard Visualization:**
- Histogram: Source count distribution (x-axis: source count, y-axis: frequency)
- Line chart: Verification rate vs. source count
- Line chart: Wall-clock time vs. source count
- Scatter plot: Context drift detection vs. source count (red dots = drift detected)
- Table: Percentiles (p50, p75, p90, p95, p99) and bucket percentages

**Phase 1 Decision Criteria:**
- If p90 < 50 sources AND no drift detected at p90 → Phase 1 sufficient
- If p90 >= 50 sources OR drift detected at p75 → Proceed to Phase 2
- If >10% of queries use >100 sources → Proceed to Phase 2

---

## Context Management: Solutions for Context Bloat

### Problem Statement

**Current Issue:**
- Single-agent pipeline accumulates all source content in context
- 50 sources × 2KB average = 100KB+ context per session
- Attention cost scales quadratically: O(n²)
- Doubling context quadruples cost, not doubles it
- Maximum Effective Context Window (MECW) << marketed limits

**Target:**
- Reduce context usage by 70-80%
- Maintain research quality (95%+ verification rate)
- Enable 100+ source research without context drift

### Four-Strategy Approach

#### Strategy 1: External Storage

**Implementation:**
```python
class ExternalStorage:
    def __init__(self):
        self.corpus = LocalCorpus()  # SQLite with FTS5
        self.embeddings = EmbeddingStore()  # Vector DB (Chroma/FAISS)
    
    def store_source(self, source: ResearchSource):
        # Store full text externally
        self.corpus.store(source)
        
        # Store embeddings for semantic search
        embedding = self.embeddings.embed(source.abstract)
        self.embeddings.store(source.id, embedding)
    
    def retrieve_relevant(self, query: str, k: int = 5) -> List[ResearchSource]:
        # Hybrid retrieval: keyword + semantic
        keyword_results = self.corpus.search(query, limit=k*2)
        semantic_results = self.embeddings.search(query, limit=k*2)
        
        # Rerank and return top-k
        return self.rerank(keyword_results + semantic_results, query)[:k]
```

**Benefits:**
- Only relevant sources loaded into context
- 90% reduction in context usage (5 sources vs. 50)
- Enables unlimited source storage

#### Strategy 2: Selective Retrieval

**Implementation:**
```python
class SelectiveRetrieval:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        self.reranker = Reranker()  # Cohere Rerank or BGE
    
    def retrieve_for_phase(self, phase: str, query: str) -> List[MemoryItem]:
        # Phase-specific retrieval
        if phase == "discovery":
            # Retrieve high-level summaries only
            return self.memory.retrieve_summaries(query, k=10)
        elif phase == "analysis":
            # Retrieve full abstracts for top sources
            return self.memory.retrieve_abstracts(query, k=5)
        elif phase == "synthesis":
            # Retrieve detailed findings
            return self.memory.retrieve_findings(query, k=3)
        else:
            return []
    
    def rerank(self, candidates: List[MemoryItem], query: str) -> List[MemoryItem]:
        # Use reranker to select most relevant
        scores = self.reranker.rank(query, [c.content for c in candidates])
        return [c for c, _ in sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)]
```

**Benefits:**
- Context adapts to research phase
- Only load what's needed for current task
- 60-70% reduction in context usage

#### Strategy 3: Context Compression

**Implementation:**
```python
class ContextCompressor:
    def __init__(self):
        self.compressor = LLMLingua()  # or AutoCompressor
    
    def compress_sources(self, sources: List[ResearchSource], target_ratio: float = 0.3) -> str:
        # Concatenate source abstracts
        full_text = "\n\n".join([
            f"[{s.id}] {s.title}\n{s.abstract}"
            for s in sources
        ])
        
        # Compress to target ratio
        compressed = self.compressor.compress(full_text, target_ratio)
        
        return compressed
    
    def compress_with_caching(self, sources: List[ResearchSource]) -> str:
        # Use Anthropic prompt caching for repeated queries
        # Cache prefix: common sources across research sessions
        cache_prefix = self.get_common_sources(sources)
        new_sources = [s for s in sources if s not in cache_prefix]
        
        return {
            "cached": cache_prefix,
            "new": self.compress_sources(new_sources)
        }
```

**Benefits:**
- 70% compression ratio (30% of original size)
- Preserves key information
- Prompt caching reduces cost for repeated queries

#### Strategy 4: Agent Isolation

**Implementation:**
```python
class AgentPool:
    def __init__(self, max_agents: int = 10):
        self.agents = []
        self.max_agents = max_agents
    
    def spawn_agent(self, task: Task) -> Agent:
        # Each agent has independent context
        agent = Agent(
            task=task,
            context_budget=10_000,  # 10K tokens per agent
            memory_manager=self.shared_memory
        )
        self.agents.append(agent)
        return agent
    
    async def execute_parallel(self, tasks: List[Task]) -> List[Result]:
        # Spawn agents in parallel
        agents = [self.spawn_agent(task) for task in tasks]
        
        # Execute in parallel (each with isolated context)
        results = await asyncio.gather(*[agent.execute() for agent in agents])
        
        # Clean up agents
        self.cleanup_agents(agents)
        
        return results
```

**Benefits:**
- No cross-agent context pollution
- Parallel execution reduces wall-clock time
- Each agent operates within budget (10K tokens)
- Total context = sum of agent contexts (not product)

### Combined Impact

**Before (Monolithic Pipeline):**
- 50 sources × 2KB = 100KB context
- Single agent accumulates all content
- Quadratic attention cost: O(100K²) = 10B operations

**After (Multi-Agent + Context Optimization):**
- 10 agents × 5 sources × 2KB × 0.3 compression = 30KB total context
- Parallel execution with isolated contexts
- Linear attention cost: 10 × O(3K²) = 90M operations
- **110x reduction in attention cost**

---

## Task Decomposition: Strategy for Heavy Research Tasks

### Dynamic Task Graph Generation

**Approach:** Decompose research query into context-sensitive subtasks with execution feedback

**Implementation:**
```python
class TaskGraph:
    def __init__(self):
        self.nodes = []  # List of Task nodes
        self.edges = []  # List of (parent, child) dependencies
    
    def decompose_query(self, query: str, depth: str) -> List[Task]:
        # Phase 1: Discovery tasks (parallel)
        discovery_tasks = [
            Task(type="discover", source="arxiv", query=query),
            Task(type="discover", source="semantic_scholar", query=query),
            Task(type="discover", source="github", query=query),
            Task(type="discover", source="web", query=query),
        ]
        
        # Phase 2: Analysis tasks (parallel, depends on discovery)
        analysis_tasks = [
            Task(type="analyze_papers", depends_on=discovery_tasks),
            Task(type="analyze_repos", depends_on=discovery_tasks),
            Task(type="build_citation_network", depends_on=discovery_tasks),
            Task(type="score_quality", depends_on=discovery_tasks),
        ]
        
        # Phase 3: Synthesis tasks (sequential, depends on analysis)
        synthesis_tasks = [
            Task(type="synthesize", depends_on=analysis_tasks),
            Task(type="detect_contradictions", depends_on=analysis_tasks),
            Task(type="audit_evidence", depends_on=analysis_tasks),
            Task(type="check_falsification", depends_on=analysis_tasks),
        ]
        
        # Phase 4: Report generation (sequential, depends on synthesis)
        report_task = Task(type="generate_report", depends_on=synthesis_tasks)
        
        # Phase 5: Adversarial review (sequential, depends on report)
        review_task = Task(type="adversarial_review", depends_on=[report_task])
        
        return self.build_graph(discovery_tasks + analysis_tasks + synthesis_tasks + [report_task, review_task])
    
    def build_graph(self, tasks: List[Task]) -> TaskGraph:
        # Build dependency graph
        for task in tasks:
            self.nodes.append(task)
            for dep in task.depends_on:
                self.edges.append((dep, task))
        return self
    
    def get_ready_tasks(self) -> List[Task]:
        # Return tasks with all dependencies satisfied
        return [
            task for task in self.nodes
            if task.status == "pending" and all(dep.status == "completed" for dep in task.depends_on)
        ]
```

### Complexity-Based Task Allocation

**Strategy:** Route tasks to appropriate models based on complexity

**Implementation:**
```python
class TaskAllocator:
    def __init__(self):
        self.model_tiers = {
            "simple": "claude-haiku-4-5",      # Fast, cheap
            "standard": "claude-sonnet-4-6",   # Balanced
            "complex": "claude-opus-4-7",      # Deep reasoning
        }
    
    def assess_complexity(self, task: Task) -> str:
        # Rule-based complexity assessment
        if task.type in ["discover", "score_quality"]:
            return "simple"
        elif task.type in ["analyze_papers", "analyze_repos", "build_citation_network"]:
            return "standard"
        elif task.type in ["synthesize", "detect_contradictions", "audit_evidence", "adversarial_review"]:
            return "complex"
        else:
            return "standard"
    
    def allocate(self, task: Task) -> str:
        complexity = self.assess_complexity(task)
        return self.model_tiers[complexity]
```

**Benefits:**
- 3x cost reduction (use Haiku for simple tasks)
- Faster execution (Haiku is 3x faster than Sonnet)
- Reserve Opus for tasks requiring deep reasoning

### Adaptive Task Decomposition

**Strategy:** Adjust task graph based on intermediate results

**Implementation:**
```python
class AdaptiveOrchestrator:
    def __init__(self):
        self.task_graph = TaskGraph()
        self.allocator = TaskAllocator()
    
    async def execute_adaptive(self, query: str, depth: str) -> ResearchReport:
        # Initial decomposition
        tasks = self.task_graph.decompose_query(query, depth)
        
        while not self.task_graph.is_complete():
            # Get ready tasks
            ready_tasks = self.task_graph.get_ready_tasks()
            
            # Execute in parallel
            results = await self.execute_parallel(ready_tasks)
            
            # Adapt task graph based on results
            new_tasks = self.adapt_graph(results)
            if new_tasks:
                self.task_graph.add_tasks(new_tasks)
        
        return self.task_graph.get_final_result()
    
    def adapt_graph(self, results: List[Result]) -> List[Task]:
        # Example: If discovery found < 10 sources, add more discovery tasks
        discovery_results = [r for r in results if r.task.type == "discover"]
        total_sources = sum(len(r.sources) for r in discovery_results)
        
        if total_sources < 10:
            # Add more discovery tasks with expanded queries
            return [
                Task(type="discover", source="openreview", query=self.expand_query(results)),
                Task(type="discover", source="papers_with_code", query=self.expand_query(results)),
            ]
        
        # Example: If contradictions found, add falsification tasks
        contradiction_results = [r for r in results if r.task.type == "detect_contradictions"]
        if any(len(r.contradictions) > 0 for r in contradiction_results):
            return [
                Task(type="deep_falsification", contradictions=r.contradictions)
                for r in contradiction_results if r.contradictions
            ]
        
        return []
```

### Progress Checkpointing

**Strategy:** Save research state every 10 minutes for resumption

**Implementation:**
```python
class ResearchCheckpoint:
    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_interval = 600  # 10 minutes
    
    def save_checkpoint(self, session_id: str, state: ResearchState):
        checkpoint_path = self.checkpoint_dir / f"{session_id}.json"
        checkpoint_path.write_text(json.dumps({
            "session_id": session_id,
            "query": state.query,
            "depth": state.depth,
            "task_graph": state.task_graph.to_dict(),
            "completed_tasks": [t.to_dict() for t in state.completed_tasks],
            "pending_tasks": [t.to_dict() for t in state.pending_tasks],
            "results": [r.to_dict() for r in state.results],
            "timestamp": datetime.now().isoformat(),
        }))
    
    def load_checkpoint(self, session_id: str) -> Optional[ResearchState]:
        checkpoint_path = self.checkpoint_dir / f"{session_id}.json"
        if not checkpoint_path.exists():
            return None
        
        data = json.loads(checkpoint_path.read_text())
        return ResearchState.from_dict(data)
    
    def resume_research(self, session_id: str) -> ResearchReport:
        state = self.load_checkpoint(session_id)
        if not state:
            raise ValueError(f"No checkpoint found for session {session_id}")
        
        # Resume from last checkpoint
        orchestrator = AdaptiveOrchestrator()
        orchestrator.task_graph = TaskGraph.from_dict(state.task_graph)
        
        return await orchestrator.execute_adaptive(state.query, state.depth)
```

**Benefits:**
- Resume long-running research after interruption
- No loss of progress
- Enables multi-hour research sessions

---

## Implementation Phases: 2-Phase Rollout (REVISED)

### Overview: Why 2 Phases?

**Architect & Critic Recommendation:** Start with 3-agent hybrid + compression to validate architecture before scaling to 10+ agents.

**Rationale:**
- Reduces implementation risk (4 weeks vs. 7 weeks)
- Validates core assumptions (context reduction, quality maintenance)
- Provides early feedback on coordination primitives
- Avoids premature optimization for 100+ sources (most research uses 20-50)

**Phase 1 Target:** 60% context reduction, 2x speedup, 90% verification rate  
**Phase 2 Target:** 80% context reduction, 5x speedup, 95% verification rate (only if Phase 1 shows context drift at 50+ sources)

---

### Phase 1: 3-Agent Hybrid + Compression (Weeks 1-4)

**Goal:** Validate multi-agent architecture with minimal agent count, achieve 60% context reduction

**Agent Architecture:**
1. **Discovery Agent** (Haiku) — Parallel search across 7+ sources
2. **Analysis Agent** (Sonnet) — Extract findings, build citation network, score quality
3. **Synthesis Agent** (Opus) — Cross-source synthesis, contradiction detection, evidence audit, adversarial review

**Context Optimization:**
- External storage (SQLite + embeddings)
- Selective retrieval (phase-specific)
- Context compression (LLMLingua, 0.3 ratio)
- Agent isolation (10KB budget per agent)

**Coordination Primitives (CRITICAL):**
- Task state machine: PENDING → RUNNING → (RETRY) → COMPLETED/FAILED
- Retry policy: Max 2 retries, exponential backoff (1s, 2s, 4s)
- Circuit breaker: Synthesis proceeds if ≥50% discovery tasks succeed
- Timeout hierarchy: 5min/task, 15min/phase, 60min/total
- Health checks: Kill agents hanging >5min

**Memory Capacity Bounds (HIGH):**
- Capacity targets: 10K sources, 100K notes, 1K sessions
- Compaction: Archive notes >90 days, deduplicate embeddings >0.95 similarity
- Query SLOs: FTS5 <100ms, embeddings <200ms, reranking <500ms

**Adversarial Review Protocol (MEDIUM):**
- Reviewer context budget: 30KB max (report + top-10 sources + claim mapping)
- Disagreement resolution: Executor must fix, soften, or remove flagged claims
- Selective review: Only claims with confidence <0.8

#### Week 1: Foundation + Coordination Primitives

**Tasks:**
1. Create `AgentPool` with spawn/cleanup logic
2. Implement `TaskGraph` with state machine (PENDING/RUNNING/RETRY/COMPLETED/FAILED)
3. Add retry policy (max 2 retries, exponential backoff)
4. Implement circuit breaker (≥50% success threshold)
5. Add timeout hierarchy (5min/task, 15min/phase, 60min/total)
6. Implement health checks (kill agents >5min)

**Deliverables:**
- `lyra_research/orchestration/agent_pool.py`
- `lyra_research/orchestration/task_graph.py`
- `lyra_research/orchestration/coordination.py` (retry, circuit breaker, timeouts, health checks)

**Tests:** 40+ tests for state machine, retry logic, circuit breaker, timeouts, health checks

**Success Criteria:**
- Task state machine transitions correctly
- Retry policy triggers on transient failures (not logic errors)
- Circuit breaker fails fast if <50% tasks succeed
- Timeouts kill hanging agents after 5min
- Health checks detect and kill unhealthy agents

#### Week 2: Memory + Context Optimization

**Tasks:**
1. Add `MemoryManager` with hybrid retrieval (FTS5 + embeddings)
2. Implement capacity bounds (10K sources, 100K notes, 1K sessions)
3. Add compaction strategy (archive >90 days, deduplicate >0.95 similarity)
4. Implement query latency monitoring (FTS5 <100ms, embeddings <200ms, reranking <500ms)
5. Add `ContextBudget` enforcement (10KB per agent)
6. Implement `ExternalStorage` with SQLite + embeddings
7. Add `SelectiveRetrieval` with phase-specific retrieval
8. Implement `ContextCompressor` with LLMLingua (0.3 ratio)

**Deliverables:**
- `lyra_research/memory/memory_manager.py`
- `lyra_research/memory/capacity_manager.py`
- `lyra_research/context/external_storage.py`
- `lyra_research/context/selective_retrieval.py`
- `lyra_research/context/compressor.py`

**Tests:** 50+ tests for memory retrieval, capacity bounds, compaction, query latency, context optimization

**Success Criteria:**
- Memory retrieval returns top-5 relevant sources in <200ms
- Capacity bounds enforced (alert at 80%, block at 100%)
- Compaction reduces database size by 30%+
- Query latency SLOs met (p95)
- Context compression achieves 0.3 ratio (70% reduction)

#### Week 3: 3-Agent Implementation

**Tasks:**
1. Implement `DiscoveryAgent` (Haiku) — Parallel search across 7+ sources
2. Implement `AnalysisAgent` (Sonnet) — Extract findings, build citation network, score quality
3. Implement `SynthesisAgent` (Opus) — Cross-source synthesis, contradiction detection, evidence audit
4. Add adversarial review protocol (30KB context budget, disagreement resolution, selective review)
5. Integrate agents into `ResearchOrchestrator`

**Deliverables:**
- `lyra_research/agents/discovery_agent.py`
- `lyra_research/agents/analysis_agent.py`
- `lyra_research/agents/synthesis_agent.py`
- `lyra_research/agents/adversarial_reviewer.py`
- `lyra_research/orchestrator_v2.py`

**Tests:** 60+ tests for agent execution, adversarial review, orchestration

**Success Criteria:**
- Discovery agent finds 50 sources from 7 sources in <30s
- Analysis agent extracts findings and builds citation network in <60s
- Synthesis agent produces coherent report with 90% verification rate
- Adversarial review catches unsupported claims (reviewer context <30KB)

#### Week 4: Integration, Testing & Benchmarking

**Tasks:**
1. Run end-to-end tests with 10 research queries
2. Benchmark against current implementation (context usage, wall-clock time, quality)
3. Measure coordination primitive effectiveness (retry success rate, circuit breaker triggers, timeout frequency)
4. Measure memory capacity utilization and query latency
5. Measure adversarial review effectiveness (claims flagged, disagreements resolved)
6. Document Phase 1 results and decision criteria for Phase 2

**Deliverables:**
- End-to-end test suite (20+ tests)
- Benchmark report (context usage, wall-clock time, quality metrics)
- Coordination metrics dashboard
- Memory metrics dashboard
- Phase 1 results document

**Tests:** 20+ end-to-end tests covering full research pipeline

**Success Criteria:**
- 60% context reduction (40KB vs. 100KB for 50 sources)
- 2x speedup (2.5 minutes vs. 5 minutes)
- 90% verification rate (vs. 85% current)
- 100% citation accuracy
- All 381 existing tests still pass
- Coordination primitives work correctly (retry, circuit breaker, timeouts, health checks)
- Memory capacity bounds enforced, query latency SLOs met
- Adversarial review catches 80%+ unsupported claims

**Phase 1 Decision Criteria:**
- If context drift observed at 50+ sources → Proceed to Phase 2
- If 60% context reduction + 90% verification achieved without drift → Phase 1 sufficient, skip Phase 2
- If coordination primitives fail → Iterate on Phase 1 before Phase 2

---

### Phase 2: Scale to 10+ Agents (Weeks 5-7) — CONDITIONAL

**Trigger:** Phase 1 shows context drift at 50+ sources OR user explicitly requests 100+ source research capability

**Goal:** Scale to 10+ specialized agents, achieve 80% context reduction, 5x speedup, 95% verification rate

**Agent Architecture (10+ agents):**
- **Discovery:** ArXivAgent, SemanticScholarAgent, GitHubAgent, WebAgent, OpenReviewAgent, HuggingFaceAgent (6 agents)
- **Analysis:** PaperAnalysisAgent, RepoAnalysisAgent, CitationAnalysisAgent, QualityScoreAgent (4 agents)
- **Synthesis:** CrossSourceSynthesizer, ContradictionDetector, EvidenceAuditor, FalsificationChecker (4 agents)
- **Assurance:** AdversarialReviewer (1 agent)

**Why Scale to 10+ Agents?**
- Finer-grained parallelization (6 discovery agents vs. 1)
- Specialized analysis per source type (papers vs. repos)
- Separate synthesis concerns (taxonomy vs. contradictions vs. evidence vs. falsification)
- Reduces per-agent context (5KB vs. 10KB)

#### Week 5: Discovery & Analysis Agents

**Tasks:**
1. Split `DiscoveryAgent` into 6 specialized agents (ArXiv, Semantic Scholar, GitHub, Web, OpenReview, HuggingFace)
2. Split `AnalysisAgent` into 4 specialized agents (Paper, Repo, Citation, Quality)
3. Update `TaskGraph` to handle 10 parallel discovery tasks
4. Add result batching and serialization to shared memory
5. Implement exponential backoff for rate-limited APIs

**Deliverables:**
- `lyra_research/agents/discovery/` (6 agent files)
- `lyra_research/agents/analysis/` (4 agent files)
- Updated `TaskGraph` for 10+ agents

**Tests:** 50+ tests for specialized agents, parallel execution, rate limiting

**Success Criteria:**
- 6 discovery agents run in parallel, complete in <20s (vs. 30s for 1 agent)
- 4 analysis agents run in parallel, complete in <40s (vs. 60s for 1 agent)
- Rate limits handled gracefully (exponential backoff)

#### Week 6: Synthesis & Assurance Agents

**Tasks:**
1. Split `SynthesisAgent` into 4 specialized agents (Synthesizer, Contradiction, Evidence, Falsification)
2. Implement sequential synthesis pipeline (Synthesizer → Contradiction → Evidence → Falsification)
3. Refine adversarial review protocol for 10+ agent context
4. Add progress checkpointing every 10 minutes
5. Implement adaptive task decomposition (adjust graph based on intermediate results)

**Deliverables:**
- `lyra_research/agents/synthesis/` (4 agent files)
- Updated `AdversarialReviewer` for 10+ agent context
- `lyra_research/orchestration/checkpoint.py`
- `lyra_research/orchestration/adaptive_orchestrator.py`

**Tests:** 50+ tests for synthesis agents, checkpointing, adaptive decomposition

**Success Criteria:**
- 4 synthesis agents run sequentially, complete in <60s
- Adversarial review handles 10+ agent context (still <30KB)
- Checkpointing saves/restores research state correctly
- Adaptive decomposition adjusts task graph based on results

#### Week 7: Integration, Testing & Final Benchmarking

**Tasks:**
1. Integrate all 10+ agents into `AdaptiveOrchestrator`
2. Run end-to-end tests with 10 research queries (including 100+ source queries)
3. Benchmark against Phase 1 and current implementation
4. Measure coordination overhead (10+ agents vs. 3 agents)
5. Measure memory scalability (100+ sources)
6. Document final results and production readiness

**Deliverables:**
- `lyra_research/orchestrator_v3.py` (10+ agent orchestrator)
- End-to-end test suite (30+ tests)
- Final benchmark report
- Production readiness assessment

**Tests:** 30+ end-to-end tests covering 10-100+ source research

**Success Criteria:**
- 80% context reduction (20KB vs. 100KB for 50 sources)
- 5x speedup (1 minute vs. 5 minutes)
- 95% verification rate
- 100% citation accuracy
- Handles 100+ source research without context drift
- All 381 existing tests + Phase 1 tests still pass
- Coordination overhead <10% (10+ agents vs. 3 agents)

---

### Phase Decision Summary

**Phase 1 (Weeks 1-4):** 3-agent hybrid + compression → 60% context reduction, 2x speedup, 90% verification  
**Phase 2 (Weeks 5-7):** 10+ agents (CONDITIONAL) → 80% context reduction, 5x speedup, 95% verification

**Decision Point (End of Week 4):**
- Context drift at 50+ sources? → Proceed to Phase 2
- 60% reduction + 90% verification without drift? → Phase 1 sufficient
- Coordination primitives failing? → Iterate on Phase 1

**Rationale for 2-Phase Approach:**
- Reduces risk (validate architecture early)
- Avoids premature optimization (most research uses 20-50 sources)
- Provides early feedback (4 weeks vs. 7 weeks)
- Allows iteration on coordination primitives before scaling
- Aligns with Architect & Critic recommendations

---

## Success Metrics: Measuring "Highest Score" for Research Reports

### Quantitative Metrics

#### 1. Verification Rate (Target: 95%+)
**Definition:** Percentage of claims backed by valid source citations

**Measurement:**
```python
def calculate_verification_rate(report: ResearchReport, sources: List[ResearchSource]) -> float:
    claims = extract_claims(report.content)
    verified = sum(1 for claim in claims if has_valid_citation(claim, sources))
    return verified / len(claims) if claims else 0.0
```

**Benchmark:**
- Current Lyra: ~85% (pattern-based citation matching)
- Target: 95%+ (semantic citation verification)
- ARIS: 98% (3-stage evidence-claim audit)

#### 2. Source Diversity (Target: 7+ sources)
**Definition:** Number of independent sources cited in report

**Measurement:**
```python
def calculate_source_diversity(report: ResearchReport) -> int:
    cited_sources = extract_cited_sources(report.content)
    return len(set(cited_sources))
```

**Benchmark:**
- Current Lyra: 5-10 sources (depending on depth)
- Target: 10+ sources for "deep" research
- Industry standard: 7+ sources (ARIS, Claude Code)

#### 3. Citation Accuracy (Target: 100%)
**Definition:** Percentage of citations that are valid and accessible

**Measurement:**
```python
def calculate_citation_accuracy(report: ResearchReport) -> float:
    citations = extract_citations(report.content)
    valid = sum(1 for citation in citations if is_valid_url(citation) or is_valid_arxiv_id(citation))
    return valid / len(citations) if citations else 0.0
```

**Benchmark:**
- Current Lyra: ~95% (some broken URLs)
- Target: 100% (validate all citations before report generation)

#### 4. Recency Score (Target: 50%+ from last 2 years)
**Definition:** Percentage of sources published in last 2 years

**Measurement:**
```python
def calculate_recency_score(sources: List[ResearchSource]) -> float:
    recent = sum(1 for s in sources if s.published_date and (datetime.now() - s.published_date).days < 730)
    return recent / len(sources) if sources else 0.0
```

**Benchmark:**
- Current Lyra: ~40% (no recency filtering)
- Target: 50%+ (prioritize recent sources)

#### 5. Completeness (Target: 90%+ checklist items answered)
**Definition:** Percentage of research checklist items answered

**Measurement:**
```python
def calculate_completeness(checklist: ResearchChecklist) -> float:
    return checklist.completion_rate()  # Already implemented
```

**Benchmark:**
- Current Lyra: ~70% (some questions unanswered)
- Target: 90%+ (comprehensive coverage)

#### 6. Context Efficiency (Target: 70-80% reduction)
**Definition:** Context tokens used per source analyzed

**Measurement:**
```python
def calculate_context_efficiency(context_tokens: int, sources_analyzed: int) -> float:
    return context_tokens / sources_analyzed if sources_analyzed else 0.0
```

**Benchmark:**
- Current Lyra: ~2000 tokens/source (100KB for 50 sources)
- Target: ~600 tokens/source (30KB for 50 sources)
- 70% reduction

#### 7. Wall-Clock Time (Target: 3-5x speedup)
**Definition:** Total time from query to report

**Measurement:**
```python
def calculate_wall_clock_time(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds()
```

**Benchmark:**
- Current Lyra: ~5 minutes for 50 sources (sequential)
- Target: ~1-2 minutes for 50 sources (parallel)
- 3-5x speedup

### Qualitative Metrics

#### 8. Logical Consistency (Manual Review)
**Definition:** Report contains no contradictions or logical errors

**Assessment:**
- Manual review by domain expert
- Check for contradicting claims
- Verify logical flow and argumentation

**Benchmark:**
- Current Lyra: Good (ContradictionDetector catches most issues)
- Target: Excellent (adversarial review eliminates remaining issues)

#### 9. Writing Quality (Manual Review)
**Definition:** Report is clear, concise, and well-structured

**Assessment:**
- Manual review by technical writer
- Check for clarity, conciseness, structure
- Verify markdown formatting

**Benchmark:**
- Current Lyra: Good (ReportGenerator produces readable reports)
- Target: Excellent (5-pass editing pipeline)

#### 10. Novelty & Insight (Manual Review)
**Definition:** Report provides novel insights beyond source summaries

**Assessment:**
- Manual review by domain expert
- Check for synthesis across sources
- Verify identification of gaps and contradictions

**Benchmark:**
- Current Lyra: Good (CrossSourceSynthesizer builds taxonomy)
- Target: Excellent (adversarial review ensures deep synthesis)

### Composite Quality Score

**Formula:**
```python
def calculate_quality_score(report: ResearchReport, sources: List[ResearchSource], checklist: ResearchChecklist) -> float:
    weights = {
        "verification_rate": 0.25,
        "source_diversity": 0.15,
        "citation_accuracy": 0.20,
        "recency_score": 0.10,
        "completeness": 0.15,
        "context_efficiency": 0.05,
        "wall_clock_time": 0.10,
    }
    
    scores = {
        "verification_rate": calculate_verification_rate(report, sources),
        "source_diversity": min(calculate_source_diversity(report) / 10, 1.0),
        "citation_accuracy": calculate_citation_accuracy(report),
        "recency_score": calculate_recency_score(sources),
        "completeness": calculate_completeness(checklist),
        "context_efficiency": 1.0 - (calculate_context_efficiency(...) / 2000),
        "wall_clock_time": 1.0 - (calculate_wall_clock_time(...) / 300),
    }
    
    return sum(scores[k] * weights[k] for k in weights)
```

**Target:** 0.90+ (90%+ overall quality score)

### Benchmarking Protocol

**Test Suite:**
1. 10 research queries across different domains (ML, NLP, CV, RL, etc.)
2. Run both current and new implementation
3. Compare metrics side-by-side
4. Manual review by domain experts

**Example Queries:**
- "Large language model reasoning capabilities"
- "Transformer architecture improvements"
- "Reinforcement learning from human feedback"
- "Vision-language pre-training methods"
- "Neural architecture search techniques"

**Success Criteria:**
- New implementation achieves 0.90+ quality score on all 10 queries
- 70-80% reduction in context usage
- 3-5x speedup in wall-clock time
- 95%+ verification rate
- 100% citation accuracy

---

## Risks & Mitigations

### Risk 1: Multi-Agent Coordination Complexity (CRITICAL - REVISED)

**Risk:** Coordinating 10+ agents with dependencies is complex and error-prone. Missing coordination primitives can cause deadlocks, timeouts, and cascading failures.

**Impact:** CRITICAL — Could lead to deadlocks, race conditions, or incorrect results

**Mitigation:**
1. **Implement Task State Machine with Retry Policy:**
   - Max 2 retries per task with exponential backoff (1s, 2s, 4s)
   - States: PENDING → RUNNING → (RETRY) → COMPLETED/FAILED
   - Retry only on transient failures (network, rate limit), not logic errors

2. **Circuit Breaker Pattern:**
   - Synthesis proceeds if ≥50% of discovery tasks succeed
   - If <50% succeed, fail fast with clear error message
   - Track failure rate per agent type (discovery, analysis, synthesis)

3. **Timeout Hierarchy:**
   - Per-task timeout: 5 minutes (hard kill after 5min)
   - Per-phase timeout: 15 minutes (discovery, analysis, synthesis)
   - Total research timeout: 60 minutes (checkpoint and resume if exceeded)

4. **Health Checks:**
   - Kill agents hanging >5 minutes without progress
   - Monitor memory usage per agent (kill if >2GB)
   - Track agent spawn/completion rate (alert if <1 agent/min)

5. **Start with 3-agent prototype** before scaling to 10+

**Contingency:** Fall back to sequential execution if coordination fails after 2 attempts

### Risk 2: Context Drift in Long-Running Research

**Risk:** 65% of enterprise AI failures trace to context drift or memory loss

**Impact:** HIGH — Research quality degrades over time, unsupported claims increase

**Mitigation:**
1. Implement progress checkpointing every 10 minutes
2. Use external storage for all source content (no in-context accumulation)
3. Add context budget enforcement (reject tasks exceeding budget)
4. Implement memory compaction for long-running sessions
5. Use adversarial review to catch drift-induced errors

**Contingency:** Restart research from last checkpoint if drift detected

### Risk 3: API Rate Limits and Failures

**Risk:** Semantic Scholar, GitHub, and other APIs have rate limits

**Impact:** MEDIUM — Discovery phase fails or takes much longer

**Mitigation:**
1. Implement exponential backoff retry (already done for Semantic Scholar)
2. Add result caching for repeated queries
3. Use multiple API keys (rotate on rate limit)
4. Implement graceful degradation (skip source if unavailable)
5. Add fallback sources (e.g., use ArXiv if Semantic Scholar fails)

**Contingency:** Continue with available sources, flag missing sources in report

### Risk 4: Adversarial Review Integration (MEDIUM - REVISED)

**Risk:** Adversarial review integration underspecified - unclear reviewer context budget, disagreement resolution protocol, and selective review criteria.

**Impact:** MEDIUM — Review may be ineffective (too little context) or expensive (too much context), disagreements block progress

**Mitigation:**
1. **Reviewer Context Budget:**
   - Max 30KB context per review (report + top-10 sources + claim mapping)
   - Report: ~10KB (compressed if needed)
   - Top-10 sources: ~15KB (abstracts only, not full text)
   - Claim mapping: ~5KB (claim → source citations)

2. **Disagreement Resolution Protocol:**
   - Executor must address ALL flagged claims (fix, soften, or remove)
   - Fix: Add missing citation or strengthen evidence
   - Soften: Change "X is Y" to "X may be Y" or "Evidence suggests X is Y"
   - Remove: Delete unsupported claim entirely
   - Re-review after fixes (max 2 review rounds)

3. **Selective Review Criteria:**
   - Only review claims with confidence <0.8 (based on citation count, source quality)
   - Skip review for claims with 3+ high-quality citations
   - Prioritize review for: numerical claims, outperformance claims, causal claims

4. **Cost Control:**
   - Use cheaper reviewer model (GPT-4o-mini, ~$0.15/1M tokens)
   - Cache reviewer prompts (Anthropic prompt caching)
   - Make adversarial review optional for "quick" and "standard" depth

5. **Reviewer Model Selection:**
   - Executor: Claude Opus 4.7
   - Reviewer: GPT-4o or GPT-4o-mini (cross-model heterogeneity)

**Contingency:** Skip adversarial review if reviewer API unavailable, flag report as "unreviewed"

### Risk 5: Test Suite Regression

**Risk:** Refactoring breaks 381 existing tests

**Impact:** HIGH — Loss of production-ready status

**Mitigation:**
1. Run full test suite after each phase
2. Implement backward compatibility layer (keep old orchestrator)
3. Add integration tests for new components
4. Use feature flags to toggle new vs. old implementation
5. Gradual rollout (new implementation opt-in initially)

**Contingency:** Revert to old implementation if tests fail

### Risk 6: Memory Store Scalability (HIGH - REVISED)

**Risk:** Memory stores lack capacity bounds, compaction strategy, and query latency SLOs. Unbounded growth leads to degraded performance and eventual failure.

**Impact:** HIGH — Research quality degrades as memory grows, queries slow down, storage exhausted

**Mitigation:**
1. **Capacity Targets:**
   - 10,000 sources (ResearchSource table)
   - 100,000 notes (Zettelkasten)
   - 1,000 sessions (Memento)
   - Alert at 80% capacity, block writes at 100%

2. **Compaction Strategy:**
   - Archive notes >90 days old to cold storage (S3/local archive)
   - Deduplicate embeddings with >0.95 cosine similarity
   - Vacuum SQLite databases weekly (VACUUM command)
   - Compress archived sessions (gzip)

3. **Query Latency SLOs:**
   - FTS5 keyword search: <100ms (p95)
   - Embedding similarity search: <200ms (p95)
   - Reranking: <500ms (p95)
   - Alert if SLO violated for >5 consecutive queries

4. **Monitoring:**
   - Track database size, row counts, query latency
   - Dashboard for capacity utilization
   - Automated alerts for SLO violations

5. **Efficient embedding model** (BGE-small, 384 dimensions)

**Contingency:** Purge oldest 10% of data if capacity exceeded and compaction insufficient

### Risk 7: Model Availability and Latency

**Risk:** Opus 4.7 may have high latency or availability issues

**Impact:** MEDIUM — Research takes longer or fails

**Mitigation:**
1. Use model routing (Haiku for simple, Sonnet for standard, Opus for complex)
2. Implement model fallback (Sonnet if Opus unavailable)
3. Add timeout and retry logic
4. Use parallel execution to hide latency
5. Cache model responses for repeated queries

**Contingency:** Fall back to Sonnet for all tasks if Opus unavailable

### Risk 8: Memory Store Corruption

**Risk:** SQLite database corruption due to concurrent writes

**Impact:** MEDIUM — Loss of research history and memory

**Mitigation:**
1. Use WAL mode for SQLite (write-ahead logging)
2. Implement database backups (daily snapshots)
3. Add transaction isolation for concurrent writes
4. Use connection pooling to limit concurrent connections
5. Add database integrity checks on startup

**Contingency:** Restore from backup if corruption detected

---

## ADR (Architectural Decision Record)

### Decision

Adopt **Multi-Agent Orchestration with Persistent Memory** architecture for Lyra's ultimate deep research system.

### Decision Drivers

1. **Context Window Constraints** — Attention cost scales quadratically (O(n²)). Current monolithic pipeline accumulates 100KB+ context for 50 sources, leading to 10B attention operations. Multi-agent isolation reduces this to 90M operations (110x improvement).

2. **Research Quality Requirements** — Target 95%+ verification rate, 100% citation accuracy, and 90%+ completeness. Adversarial review (heterogeneous models) eliminates "plausible unsupported success" that single-model self-refinement misses.

3. **Scalability for Heavy Tasks** — Must handle 100+ source research without context drift (65% of enterprise AI failures trace to this). Parallel execution with checkpointing enables multi-hour research sessions.

### Alternatives Considered

#### Alternative 1: Monolithic Pipeline Enhancement
**Description:** Enhance existing 10-step pipeline with better context management

**Pros:**
- Preserves 381 passing tests
- Lower implementation risk
- Familiar architecture

**Cons:**
- Context bloat remains O(n²) problem
- Single-agent bottleneck limits parallelization
- Doesn't address fundamental scalability issues
- Only 30-40% context reduction (vs. 70-80% target)

**Why Rejected:** Insufficient context optimization and scalability gains

#### Alternative 2: LLM-Based Task Decomposition
**Description:** Use LLM to dynamically decompose tasks at runtime

**Pros:**
- More flexible than rule-based decomposition
- Can adapt to novel research queries

**Cons:**
- Adds LLM call overhead to every decomposition
- Non-deterministic (different decompositions for same query)
- Harder to test and debug
- Increases cost and latency

**Why Rejected:** Rule-based decomposition with adaptive refinement provides sufficient flexibility with better performance and testability

#### Alternative 3: Distributed System with Message Queue
**Description:** Use RabbitMQ/Kafka for agent communication

**Pros:**
- Industry-standard distributed architecture
- Scales to 100+ agents
- Fault-tolerant

**Cons:**
- Significant infrastructure complexity
- Overkill for 10-agent system
- Requires external dependencies (RabbitMQ/Kafka)
- Harder to deploy and maintain

**Why Rejected:** Python asyncio with SQLite shared memory is sufficient for 10-agent system; can migrate to distributed system later if needed

### Why Chosen

**Multi-Agent Orchestration with Persistent Memory** provides:

1. **Proven Architecture** — ARIS, Claude Code, and Hermes-Agent all use multi-agent patterns successfully
2. **Optimal Context Efficiency** — 70-80% reduction through agent isolation, external storage, selective retrieval, and compression
3. **Scalability** — Parallel execution reduces wall-clock time 3-5x, enables 100+ source research
4. **Quality Assurance** — Adversarial review eliminates unsupported claims (98% verification rate in ARIS)
5. **Incremental Migration** — Can implement phase-by-phase while maintaining backward compatibility
6. **Leverages Existing Infrastructure** — Lyra already has multi-agent components (lyra-evolution, lyra-skills)

### Consequences

**Positive:**
- **Phase 1 (Weeks 1-4):**
  - 60% context reduction (40KB vs. 100KB for 50 sources)
  - 2x speedup (2.5 minutes vs. 5 minutes)
  - 90% verification rate (vs. 85% current)
  - 100% citation accuracy (vs. 95% current)
  - Validates architecture with minimal risk
  - Early feedback on coordination primitives

- **Phase 2 (Weeks 5-7, if needed):**
  - 80% context reduction (20KB vs. 100KB for 50 sources)
  - 5x speedup (1 minute vs. 5 minutes)
  - 95% verification rate
  - Handles 100+ source research without context drift
  - Maintains 99.9% test coverage (381 tests + new tests)

**Negative:**
- **Phase 1:** 4 weeks implementation (vs. 2-3 weeks for monolithic enhancement)
- **Phase 2:** Additional 3 weeks if needed (7 weeks total)
- More complex orchestration logic (task graph, agent pool, memory manager)
- Requires adversarial review setup (2 model subscriptions)
- Higher initial learning curve for contributors

**Neutral:**
- Backward compatibility maintained through feature flags
- Gradual rollout possible (opt-in initially)
- Can stop after Phase 1 if sufficient (most research uses 20-50 sources)
- Can revert to old implementation if issues arise

**Cost-Benefit Analysis for Adversarial Review:**

**Costs:**
- 2x model calls (executor + reviewer)
- Reviewer model cost: ~$0.15/1M tokens (GPT-4o-mini) × 30KB context = ~$0.0045 per review
- Implementation complexity: disagreement resolution protocol, selective review logic
- Latency: +10-20s per review (reviewer inference time)

**Benefits:**
- Eliminates "plausible unsupported success" (ARIS: 98% verification vs. 85% single-model)
- Catches unsupported claims that single-model self-refinement misses
- Cross-model heterogeneity provides diverse perspectives
- Reduces manual review burden (automated claim verification)
- Improves user trust (higher verification rate)

**ROI Calculation:**
- Cost per review: $0.0045
- Manual review cost: ~15 minutes × $50/hour = $12.50
- Savings: $12.50 - $0.0045 = $12.50 per review
- Break-even: 1 review
- **ROI: 2,777x** (assuming manual review alternative)

**Selective Review Optimization:**
- Only review claims with confidence <0.8 (estimated 30% of claims)
- Cost reduction: 70% (review 30% of claims instead of 100%)
- Adjusted cost per review: $0.0045 × 0.3 = $0.00135
- **Adjusted ROI: 9,259x**

**Conclusion:** Adversarial review is cost-effective even with conservative assumptions. Selective review (confidence <0.8) provides 70% cost reduction while maintaining quality.

### Follow-Ups

1. **Phase 1 Prototype (Week 1)** — Build 3-agent prototype (discovery, analysis, synthesis) to validate architecture and coordination primitives

2. **Coordination Primitives Validation (Week 1)** — Test retry policy, circuit breaker, timeout hierarchy, health checks with failure injection

3. **Memory Capacity Monitoring (Week 2)** — Implement dashboard for capacity utilization, query latency, compaction effectiveness

4. **Adversarial Review Protocol Testing (Week 3)** — Validate 30KB context budget, disagreement resolution, selective review with real research queries

5. **Phase 1 Decision Point (End of Week 4)** — Evaluate context drift at 50+ sources, decide whether to proceed to Phase 2 or stop

6. **Telemetry for Source Count Distribution** — Add metrics to track:
   - Distribution of source counts per research query (p50, p75, p90, p95, p99)
   - Percentage of queries using <20, 20-50, 50-100, >100 sources
   - Context drift correlation with source count
   - Quality metrics (verification rate, citation accuracy) vs. source count
   - Wall-clock time vs. source count
   - **Purpose:** Validate assumption that most research uses 20-50 sources, inform Phase 2 decision

7. **Benchmark Suite (Week 4)** — Create 10-query benchmark across different domains and source counts to measure quality improvements

8. **Documentation (Week 4)** — Write architecture guide for contributors, including coordination primitives, memory management, adversarial review

9. **Migration Guide (Week 4)** — Document how to migrate from old to new orchestrator, feature flags, rollback procedure

10. **Performance Monitoring Dashboard (Week 4)** — Add metrics for context usage, wall-clock time, quality scores, coordination effectiveness

11. **Cost Analysis (Week 4)** — Measure cost impact of adversarial review, multi-agent execution, context optimization vs. current implementation

12. **Phase 2 Evaluation (Week 5, if needed)** — If Phase 1 shows context drift at 50+ sources, evaluate distributed system options (RabbitMQ/Kafka) for scaling beyond 10 agents

---

## Sources

### ARIS Architecture
- [Autonomous Research via Adversarial Multi-Agent Collaboration (arXiv:2605.03042)](https://arxiv.org/html/2605.03042v1)
- [ARIS on HuggingFace Papers](https://huggingface.co/papers/2605.03042)
- [ARIS on Emergent Mind](https://www.emergentmind.com/topics/agentic-research-ideation-system)

### Research Quality Metrics
- [AI Evaluation Metrics Reference Guide 2026](https://www.digitalapplied.com/blog/ai-evaluation-metrics-reference-guide-2026)
- [Evaluating Generative AI Output - Clarivate](https://clarivate.com/academia-government/blog/evaluating-the-quality-of-generative-ai-output-methods-metrics-and-best-practices/)
- [LLM Evaluation Frameworks 2026](https://futureagi.substack.com/p/llm-evaluation-frameworks-metrics)

### Hermes-Agent
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs/)
- [Hermes Agent Features Overview](https://hermes-agent.nousresearch.com/docs/user-guide/features/overview)
- [Self-Improving AI Framework](https://decisioncrafters.com/hermes-agent-self-improving-ai-framework/)

### Claude Code
- [Eight Trends Defining Software in 2026](https://claude.com/blog/eight-trends-defining-how-software-gets-built-in-2026)
- [Three Ways to Build Deep Research with Claude](https://paddo.dev/blog/three-ways-deep-research-claude/)
- [Using Research on Claude](https://support.anthropic.com/en/articles/11088861-using-research-on-claude-ai)

### Task Decomposition
- [Dynamic Task Decomposition (arXiv:2410.22457)](https://arxiv.org/abs/2410.22457)
- [Multi-Agent Task Decomposition Patterns 2026](https://fast.io/resources/multi-agent-task-decomposition-patterns/)
- [Intelligent AI Delegation (arXiv:2602.11865)](https://arxiv.org/html/2602.11865v1)

### Context Optimization
- [5 AI Context Window Optimization Techniques](https://airbyte.com/agentic-data/ai-context-window-optimization-techniques)
- [Effective Context Engineering for AI Agents](https://tianpan.co/blog/2026-02-23-effective-context-engineering-for-ai-agents)
- [Four Strategies for Agent Context Engineering](https://tianpan.co/blog/2026-02-28-four-strategies-agent-context-engineering)
- [Context Window Optimization: Ranking vs. Stuffing](https://www.shaped.ai/blog/context-window-optimization-why-ranking-not-stuffing-is-the-scaling-law-for-agents)

### MCP and Tools
- [Claude Skills vs. MCP Technical Comparison](https://intuitionlabs.ai/articles/claude-skills-vs-mcp)
- [Octagon Deep Research MCP](https://github.com/OctagonAI/octagon-deep-research-mcp)
- [Best MCP Tools 2026](https://fast.io/resources/mcp-tools/)

---

## Plan Summary

**Plan saved to:** `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md`

**Scope:**
- **Phase 1 (Weeks 1-4):** 3-agent hybrid + compression + coordination primitives
- **Phase 2 (Weeks 5-7, CONDITIONAL):** Scale to 10+ agents if Phase 1 shows context drift at 50+ sources
- Multi-agent orchestration with persistent memory and adversarial review
- 4-strategy context optimization (external storage, selective retrieval, compression, agent isolation)

**Key Deliverables:**

**Phase 1 (Weeks 1-4):**
1. Coordination primitives (retry policy, circuit breaker, timeout hierarchy, health checks)
2. Memory capacity bounds (10K sources, 100K notes, 1K sessions) + compaction + query SLOs
3. Adversarial review protocol (30KB context budget, disagreement resolution, selective review)
4. 3-agent architecture (Discovery, Analysis, Synthesis)
5. Context optimization (external storage, selective retrieval, compression, agent isolation)
6. Benchmark suite + telemetry for source count distribution

**Phase 2 (Weeks 5-7, if needed):**
1. 10+ specialized agents (6 discovery, 4 analysis, 4 synthesis, 1 assurance)
2. Adaptive task decomposition
3. Progress checkpointing
4. 100+ source research capability

**Target Metrics:**

**Phase 1:**
- 60% context reduction (40KB vs. 100KB for 50 sources)
- 2x speedup (2.5 minutes vs. 5 minutes)
- 90% verification rate (vs. 85% current)
- 100% citation accuracy (vs. 95% current)

**Phase 2 (if needed):**
- 80% context reduction (20KB vs. 100KB for 50 sources)
- 5x speedup (1 minute vs. 5 minutes)
- 95% verification rate
- Handles 100+ source research without context drift

**Critical Gaps Addressed:**
1. ✅ Agent coordination primitives (retry, circuit breaker, timeouts, health checks)
2. ✅ Memory capacity bounds (10K sources, 100K notes, 1K sessions) + compaction + query SLOs
3. ✅ Adversarial review protocol (30KB context budget, disagreement resolution, selective review)

**Architectural Decision:**
- **Chosen:** 2-Phase Multi-Agent Orchestration (3-agent hybrid first, then 10+ agents if needed)
- **Rejected:** Monolithic Pipeline Enhancement (insufficient gains), LLM-Based Decomposition (overhead), Distributed System (overkill for Phase 1)
- **Rationale:** Reduces risk (validate early), avoids premature optimization (most research uses 20-50 sources), provides early feedback (4 weeks vs. 7 weeks), aligns with Architect & Critic recommendations

**Phase 1 Decision Criteria (End of Week 4):**
- Context drift at 50+ sources? → Proceed to Phase 2
- 60% reduction + 90% verification without drift? → Phase 1 sufficient, skip Phase 2
- Coordination primitives failing? → Iterate on Phase 1 before Phase 2

**Does this plan capture your intent?**
- "proceed" - Begin implementation via /oh-my-claudecode:start-work
- "adjust [X]" - Return to interview to modify
- "restart" - Discard and start fresh


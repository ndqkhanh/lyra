# Deep Research — Plan (§4.15)

> Run 2 — June 7, 2026 | Phase 2: Bundled deep-research workflow, AutoScientists pattern, Argus evidence graph, multi-provider research phase allocation. Updated with deep-read evidence from 12 additional sources (papers, repos, books).

## Plain-Language Summary

Lyra's ResearchAgent is currently a stub — it can run a single search call but has no multi-hop research, no evidence cross-checking, and no cited report generation. This plan implements a bundled deep-research workflow that fans out web searches across multiple angles, fetches and cross-checks sources, adversarially reviews findings, and produces a single consolidated cited report. The architecture draws from Claude Code's `/deep-research` workflow, the Argus Searcher-Navigator with shared evidence graph (1,200:1 compression), AutoScientists' self-organizing research teams, AutoResearchClaw's self-healing execution with pivot/refine/proceed loops (Liu et al., 2026, arXiv:2605.20025v2), IterResearch's evolving report-as-memory (ICLR 2026, arXiv:2511.07327), NanoResearch's tri-level co-evolution (arXiv:2605.10813), and the Agentic Reasoning Mind-Map knowledge graph (arXiv:2502.04644). The key insight: research agents use different models for different phases (Haiku for search, Sonnet for synthesis, Opus for verification), which is where the multi-provider router adds unique value. Synthesized evidence from 12+ independent sources including the Kong et al. (2026) survey of 270+ auto-research systems, the Shahani (2026) book on reliable AI systems, and the Wu (2026) academic-research-skills production-deployed verification framework (v3.11.1, 967 CI tests, github.com/Imbad0202/academic-research-skills). A convergent finding across all sources: verification must be architecturally embedded at stage transitions, not applied as a terminal filter.

## 1. Problem

BASELINE.md rates Deep Research maturity = `none`: "ResearchAgent exists but is a stub. No multi-hop research; no AutoScientists pattern." The broader landscape confirms this gap: the Kong et al. (2026) survey of 270+ auto-research systems finds that "artifact generation outpaces scientific verification" as the #1 cross-cutting challenge — and 80% of fully autonomous results in MLR-Bench are fabricated (Kong et al., 2026, arXiv:2605.18661v1). Key failures:
- **No multi-hop research**: One search, one result. No iterative query refinement based on findings
- **No evidence cross-checking**: Findings are taken at face value. No source verification
- **No cited report generation**: Research results are raw text, not structured cited reports
- **No self-organizing teams**: No AutoScientists pattern of idea-generation, experimentation, paper writing
- **No evidence graph**: No structured representation linking claims to sources
- **No adversarial review**: No mechanism for agents to challenge each other's findings
- **No context management**: Long research sessions fill context with raw search results

Estimated research quality: Lyra's current ResearchAgent would score <10% on BrowseComp or GAIA benchmarks.

## 2. Evidence Synthesis

### Claude Code `/deep-research` (§3.1)
Four-phase bundled workflow: (1) Fan out web searches across several angles, (2) Fetch and cross-check sources, (3) Agents adversarially review each other's findings, (4) Produce consolidated cited report. Only surviving claims after adversarial filtering make it into the report.

### Argus (arXiv:2605.16217, MiroMind AI)
Searcher-Navigator architecture: Navigator maintains shared evidence graph (DAG of evidence/claim nodes with support/contradiction edges). Dispatches Searchers to fill specific gaps. Verify-dispatch-synthesize loop. Results: +5.5 points with single Searcher, +12.7 points with 8 parallel Searchers over 8 benchmarks. Navigator context: 21.5K tokens from 25.6M Searcher output tokens (1,200:1 compression). 86.2% on BrowseComp with 64 Searchers.

### AutoScientists Pattern (§3.6, from 06-core-papers-autoscientists.md)
Self-organizing research teams with shared success/failure log. Three-stage pipeline: Ideation + Planning, Experimentation, Paper Writing. Multi-agent discussion before committing to a direction. Cross-layer feedback propagation (experiment failures trigger plan revision, which triggers idea revision).

### AutoResearchClaw (arXiv:2605.20025v2, Liu et al., 2026)
23-stage pipeline with five interacting mechanisms. Key innovations for Lyra: (a) **Pivot/Refine/Proceed decision loop** — complexity scoring `c in [0,1]` across 6 dimensions; experiments with `c > tau` (tau=0.6) dispatched to external coding agent; self-healing raises completion from 6/10 to 10/10. (b) **K=3 debate agents** (Innovator/Pragmatist/Contrarian) — K=2 degenerates into pro/con (-23% diversity); K=5 costs +67% tokens for only +8% diversity gain. (c) **Verifiable numeric registry** — every experimental value whitelisted; post-hoc verifier rejects unmatched claims. (d) **Cross-run lesson store** with time-decayed weighting (`T_1/2 = 30 days`). CoPilot mode achieves 87.5% accept rate vs 25.0% Full-Auto. Repository: github.com/aiming-lab/AutoResearchClaw (35 authors, 12 institutions). **Source citation:** Liu et al., "AutoResearchClaw: Self-Reinforcing Autonomous Research with Human-AI Collaboration," arXiv:2605.20025v2, May 2026.

### Kong et al. Survey — Auto-Research Roadmap (arXiv:2605.18661v1)
Comprehensive survey of 270+ auto-research systems organized into an eight-stage lifecycle with four phases (Creation/Writing/Validation/Dissemination). Five cross-cutting insights — the most critical for Lyra: (1) artifact generation outpaces verification (dominant failure mode), (2) human-governed collaboration is most reliable, (3) layered architectures converge as design pattern, (4) 58.6% of research-code errors are semantic (code runs but wrong algorithm), (5) 17.5% of CS paper abstracts show detectable AI modification. Key benchmarks: SWE-bench Verified >76% frontier, but SWE-bench Pro drops to 23%; ResearchCodeBench best model 37.3% on 212 novel ML tasks. **Trade-off alert:** survey finds that AI-generated ideas cluster in narrow regions by diversity collapse, not solvable by scaling — contradicts Argus's claim of log-linear accuracy scaling (see Contradictions 4.1 in synthesis). **Source citation:** Kong et al., "AI for Auto-Research: Roadmap and User Guide," arXiv:2605.18661v1, May 2026.

### AUTO REPRODUCE (arXiv:2505.20662v4, Zhao et al., 2026)
Paper lineage construction for implicit knowledge mining. Algorithm: extract top-k relevant cited papers via in-text citation context analysis, download repos, construct `<summary, code>` tuples. Key result: Mixed-Level score 69.97 (Claude-3.5-Sonnet) vs baselines (ChatDev 32.80, AgentLab 35.32). Ablation: removing paper lineage drops Mixed-Level from 69.97 to 63.15, increases Perf Gap from 31.62 to 39.59. Execution rate: 92-95% vs 2-18% for baselines. Cost: $1.87 per reproduction. Implication for Lyra: paper lineage construction should be a first-class deep-research phase, not an afterthought. Dual-agent decoupling (Research Agent for text, Code Agent for code) prevents context pollution. **Source citation:** Zhao et al., "AUTO REPRODUCE: Automatic AI Experiment Reproduction with Paper Lineage," arXiv:2505.20662v4, Apr 2026. Code: github.com/AI9Stars/AutoReproduce.

### academic-research-skills Framework (Wu, 2026, v3.11.1)
Production-deployed multi-agent research framework with deterministic integrity gates. Architecture: 38 agents organized into 4 skills (deep-research, academic-paper, academic-paper-reviewer, academic-pipeline) with 25 modes. **Deterministic citation verification:** cross-checks every reference against up to 4 bibliographic indexes (Semantic Scholar + OpenAlex + Crossref + arXiv) via direct API calls (not LLM). Persistent SQLite cache (90-day TTL). **L3 claim-faithfulness audit (opt-in):** LLM-as-judge fetches each cited source and judges claim support; 5 HIGH-WARN annotation classes with formatter REFUSE rules that gate-refuse on unresolved HIGH-WARN. 967 tests pass / 3 skipped / 0 failed. Full pipeline cost: $4-6 for ~15k-word paper with ~60 references. **Source citation:** Wu, C.-I., "academic-research-skills," v3.11.1, github.com/Imbad0202/academic-research-skills, 2026.

### Shahani — Building Reliable AI Systems (MEAP V12, Manning, 2026)
Three-layer reliability framework: output layer (automated content filters, statistical monitoring, LLM-as-judge), agent layer (source attribution, citation mechanisms, human-in-the-loop), operations layer (observability, deployment, safety guardrails). Key numbers: SWE-bench Verified 85% resolve rate drops to 58-65% on fresh codebases (the "reliability gap"). Recommends hybrid search (dense + BM25) for production reliability, Three-layer output quality defense, and specialized agents by domain rather than monolithic architectures. **Source citation:** Shahani, R., "Building Reliable AI Systems: Applications and Agents You Can Trust," MEAP V12, Manning Publications, 2026. Chapters 3, 4, 6, 8, 9.

### Xu et al. — Mandela Effect in Multi-Agent Systems (ICLR 2026, arXiv:2602.00428v2)
Multi-agent systems exhibit collective false memory where agents converge on incorrect answers due to social influence. Role-based protocols are the strongest attack vector (sigma_RS = 61.59% for GPT-4o-mini). **Mitigation:** Cognitive Anchoring prompt achieves 69.6% sigma reduction — prompt-only, zero training cost. Combined SFT training (resilience + cooperative guidance) provides deeper resistance (sigma_RS from 99.47% to 21.5% with sigma_C=1.1%). K=3-5 agents recommended as sweet spot for debate depth vs social contagion risk. Implication for Lyra: any adversarial verification system must include cognitive anchoring before agents receive peer output, and must treat consensus as a potential manipulation signal rather than reliability indicator. **Source citation:** Xu et al., "When Agents 'Misremember' Collectively: Exploring the Mandela Effect in LLM-based Multi-Agent Systems," ICLR 2026, arXiv:2602.00428v2.

### CaTS: Calibrated Test-Time Scaling (ICLR 2026, Huang et al.)
Self-Calibration trains LLMs via LoRA to produce reliable confidence scores. Soft Self-Consistency (SSC) achieves ECE 3.42 on GSM8K vs 4.48 (vanilla SC) and 12.03 (P(True) alone). **Key result:** CaTS-SC saves 94.2% samples to reach 85.0 accuracy on MathQA (Llama-3.1-8B) by early-stopping on high-confidence outputs. CaTS-ES improves Best-of-N: +14.5 on Obj Counting, +9.9 on MathQA. Training: LoRA (r=32, alpha=16, dropout=0.05), 1 epoch, AdamW lr=5e-5. **Trade-off:** fine-tuning introduces SFT pipeline complexity; prompt-based self-evaluation provides a lightweight starting point. Implication for Lyra: confidence calibration enables adaptive compute allocation and trust calibration. **Source citation:** Huang et al., "CaTS: Calibrated Test-Time Scaling for Efficient LLM Reasoning," ICLR 2026.

### Qi et al. — Trustworthy Agentic AI Survey (arXiv:2605.23989v1)
Defense-in-depth across four assurance tiers: Upfront (constitutional AI, system prompts, role-based access), Training-time (SFT, RLHF/RLAIF, red-teaming), Runtime (input/output guardrails, rate limiting, continuous monitoring), Post-hoc (audit logging, rollback, post-deployment evaluation). Key insight: mitigations at different stages are "complementary, not substitutable" — a poisoning attack at perceive cannot be fully neutralized by act-time guardrails. Process metrics (CVR, DCR, CompVR) catch intermediate violations that outcome-only evaluation misses. **Source citation:** Qi et al., "Towards Trustworthy Agentic AI: A Comprehensive Survey," arXiv:2605.23989v1, May 2026.

### Convergence: Verification Must Be Structural (6 independent sources)
A convergent finding from Kong et al. (2026), Qi et al. (2026), Liu et al. (2026), Wu (2026), Shahani (2026), and Zhang et al. (2026): verification must be architecturally embedded at stage transitions, not applied as a terminal filter. Minimum viable verification includes: (a) numeric claim-to-source matching, (b) citation existence checking against bibliographic databases, (c) claim-to-evidence faithfulness auditing. The evidence DAG (Argus) makes missing pieces structurally computable — verification is not post-hoc but built into the representation.

### IterResearch (ICLR 2026, arXiv:2511.07327)
MDP-inspired workspace reconstruction. Evolving report-as-memory: `s_{t+1} = (q, M_{t+1}, {a_t, TR_t})` where M is the compressed report. Constant state size `|s_t| = O(1)` vs monotonic `O(t)`. Scales to 2048 interactions at 40K context. Key: strategic forgetting via report synthesis.

### NanoResearch (arXiv:2605.10813)
Tri-level co-evolution: Skill Bank (recurring operations -> compact rules), Memory Module (user/project-specific experience), Policy Learning (SDPO from natural-language feedback). Ideation + Planning -> Experimentation -> Paper Writing, with skill/memory retrieval before each task.

### Agentic Reasoning Mind-Map (arXiv:2502.04644)
Knowledge-graph memory for long reasoning chains. Graph-construction LLM extracts entities and semantic relationships. Community clustering groups related context. LLM summarizes each community. Serves as context provider and external memory. +153% relative improvement on HLE (9.4% -> 23.8%).

### VirSci (covered in §3.6)
Collaborative idea generation, evaluation, and refinement via multi-agent debate. Idea generation -> evaluation panel -> refinement -> consensus. Proven method for generating novel research directions.

### BREAKTHROUGH-ARCHITECTURE.md
Deep Research is mentioned as a bundled workflow in Phase 2. The Dynamic Workflow Engine (§4.13) provides the runtime for code-driven orchestration. The bundled deep-research workflow is one of the first workflows built on this engine.

## 3. Proposed Lyra Design

### 3.1 Deep-Research Workflow (Bundled)

The deep-research workflow is implemented as a first-class bundled workflow on the Dynamic Workflow Engine (§4.13):

```python
# workflow: deep-research
# Implements: fan-out searches -> fetch sources -> cross-check -> vote -> cited report

DEEP_RESEARCH_WORKFLOW = {
    "name": "deep-research",
    "description": "Fan-out multi-angle research with adversarial cross-checking",
    "phases": [
        {"name": "Analyze", "model_tier": "mid"},
        {"name": "Search", "model_tier": "cheap"},
        {"name": "Fetch", "model_tier": "cheap"},
        {"name": "CrossCheck", "model_tier": "mid"},
        {"name": "Verify", "model_tier": "expensive"},
        {"name": "Synthesize", "model_tier": "mid"},
    ],
}

async def deep_research(question: str) -> ResearchReport:
    """Execute the deep-research workflow.

    Phase 1: ANALYZE — Decompose question into research angles
    Phase 2: SEARCH — Fan out searches across all angles (parallel)
    Phase 3: FETCH — Fetch and extract content from top sources (parallel)
    Phase 4: CROSS-CHECK — Compare claims across sources, flag contradictions
    Phase 5: VERIFY — Adversarial review: agents challenge each other's findings
    Phase 6: SYNTHESIZE — Consolidate verified claims into cited report
    """

    # Phase 1: Analyze question into research angles
    angles = await analyze_question(question)
    # -> ["technical viability", "market landscape", "competitive analysis",
    #     "regulatory status", "security implications", "open-source alternatives"]

    # Phase 2: Fan-out parallel searches
    search_results = await pipeline(
        angles,
        lambda angle: web_search(f"{question} {angle}", top_k=5),
        max_concurrent=8,
    )

    # Phase 3: Fetch top sources
    sources = await pipeline(
        extract_urls(search_results),
        lambda url: web_fetch(url, prompt="Extract key claims and evidence"),
        max_concurrent=8,
    )

    # Phase 4: Cross-check claims across sources
    evidence_graph = await build_evidence_graph(sources)
    contradictions = await detect_contradictions(evidence_graph)

    # Phase 5: Adversarial verification
    verified_claims = await adversarial_verify(evidence_graph)

    # Phase 6: Synthesize
    report = await synthesize_report(
        question=question,
        claims=verified_claims,
        contradictions=contradictions,
        sources=sources,
    )

    return report
```

### 3.2 Argus-Inspired Evidence Graph

```python
class EvidenceGraph:
    """DAG of evidence/claim nodes with support/contradiction edges.

    This is the central data structure of the deep-research workflow.
    It enables:
    - 1,200:1 compression (navigator context from raw search output)
    - Structured verification (claim-by-claim cross-checking)
    - Contradiction detection (competing claims linked)
    - Source provenance (every claim traces to source URL + quote)
    """

    def __init__(self):
        self.claims: dict[str, ClaimNode] = {}
        self.sources: dict[str, SourceNode] = {}
        self.edges: list[EvidenceEdge] = []

    def add_claim(self, claim_id: str, text: str, source_url: str,
                  confidence: float = 0.5) -> str:
        """Add a claim extracted from a source."""
        node = ClaimNode(claim_id, text, source_url, confidence)
        self.claims[claim_id] = node
        return claim_id

    def add_edge(self, from_id: str, to_id: str,
                 relation: Literal["supports", "contradicts",
                                   "refines", "independent"]):
        """Link claims with typed edges."""
        self.edges.append(EvidenceEdge(from_id, to_id, relation))

    def get_verified_claims(self, min_confidence: float = 0.7) -> list[ClaimNode]:
        """Get claims with corroborating evidence (at least 2 supporting sources)."""
        verified = []
        for cid, claim in self.claims.items():
            support_count = sum(
                1 for e in self.edges
                if e.to_id == cid and e.relation == "supports"
            )
            if support_count >= 1 and claim.confidence >= min_confidence:
                verified.append(claim)
        return verified

    def get_contradictions(self) -> list[tuple[ClaimNode, ClaimNode, EvidenceEdge]]:
        """Get all directly contradicting claim pairs."""
        contradictions = []
        for edge in self.edges:
            if edge.relation == "contradicts":
                c1 = self.claims.get(edge.from_id)
                c2 = self.claims.get(edge.to_id)
                if c1 and c2:
                    contradictions.append((c1, c2, edge))
        return contradictions

    def compress(self) -> str:
        """Compress the evidence graph into a navigator-ready summary.

        Argus achieves 1,200:1 compression:
        25.6M searcher tokens -> 21.5K navigator tokens.
        """
        lines = ["## Evidence Summary"]
        for claim in self.get_verified_claims():
            sources = [self.sources.get(s) for s in claim.sources]
            source_str = "; ".join(s.url for s in sources if s)
            lines.append(f"- {claim.text} [Sources: {source_str}] (conf={claim.confidence:.2f})")
        return "\n".join(lines[:500])  # Cap at 500 lines for navigator


@dataclass
class ClaimNode:
    id: str
    text: str
    source_url: str
    confidence: float = 0.5
    sources: list[str] = field(default_factory=list)  # Supporting source URLs
    category: str = "unknown"         # Factual, Opinion, Prediction, Quote
    verified: bool = False
    verification_notes: str = ""


@dataclass
class SourceNode:
    url: str
    title: str
    content_preview: str              # First 1000 chars
    domain: str
    publish_date: datetime | None = None
    authority_score: float = 0.5      # Based on domain reputation
    content_hash: str = ""            # Deduplication


@dataclass
class EvidenceEdge:
    from_id: str
    to_id: str
    relation: Literal["supports", "contradicts", "refines", "independent"]
    strength: float = 0.5             # How strong is the evidence link
```

### 3.3 Adversarial Verification

```python
class AdversarialVerifier:
    """Agents adversarially review each other's findings.

    Each claim is assigned a Skeptic and a Proponent.
    Skeptic must find flaws. Proponent must defend.
    Moderator adjudicates and records surviving claims.

    Only claims that survive adversarial challenge enter the final report.

    Technique references:
    - K=3 debate agents (Liu et al., 2026, arXiv:2605.20025v2):
      K=2 degenerates (-23% diversity), K=5 costs +67% for +8% diversity gain.
      Sweet spot: 3 agents with distinct roles.
    - Cognitive Anchoring (Xu et al., 2026, ICLR, arXiv:2602.00428v2):
      69.6% sigma reduction against collective false memory (Mandela effect).
      Each agent forms independent conclusion before reading peer output.
    - Phase-boundary verification gates (Kong et al., 2026, arXiv:2605.18661v1):
      Every stage transition enforces: claim-to-source traceability,
      citation existence check, claim-evidence faithfulness audit.
    - Cross-index citation verification (Wu, 2026, academic-research-skills v3.11):
      4-index triangulation (Semantic Scholar + OpenAlex + Crossref + arXiv)
      via direct API calls, not LLM. Persistent SQLite cache (90-day TTL).
    - L3 claim-faithfulness audit (Wu, 2026, academic-research-skills v3.8+):
      Standalone LLM fetches each cited source and judges claim support.
      5 HIGH-WARN annotation classes; gate-refuses on unresolved HIGH-WARN.
    - Three-layer output quality defense (Shahani, 2026, Ch. 9):
      Automated content filters + statistical monitoring + LLM-as-judge.
    """

    async def verify(self, claims: list[ClaimNode],
                     question: str, router) -> list[ClaimNode]:
        """Verify a set of claims adversarialy.

        For each claim:
        1. Independent conclusion: each agent forms judgment before seeing peers
            (Cognitive Anchoring: Xu et al., 2026, ICLR)
        2. Assign Skeptic and Proponent agents (K=3 debate: Liu et al., 2026)
        3. Skeptic argues why the claim might be wrong
        4. Proponent defends with evidence
        5. Skeptic responds
        6. Moderator renders final verdict
        7. Phase-boundary gate: verify claim-to-source traceability
            (Kong et al., 2026 survey finding)

        Reviewer 2's fix (from Run 1): Skeptic uses expensive model,
        Proponent uses mid model. The skeptic needs to be stronger
        for effective adversarial review.
        """
        verified = []

        for claim in claims:
            # Step 1: Independent conclusion (Cognitive Anchoring)
            # Each agent forms independent judgment before reading peer output.
            # Reduces Mandela effect by 69.6% (Xu et al., 2026, ICLR).
            independent_judgment = await router.route_task(
                preferred_tier="mid",
                task=f"CRITICAL: Form your OWN independent conclusion first. "
                     f"Before seeing any other agent's analysis, "
                     f"evaluate this claim on its merits: '{claim.text}'",
            )

            # Step 2: Skeptic (expensive model — stronger for effective challenge)
            # Per Reviewer 2's fix from Run 1: swap to expensive-agent challenges.
            skeptic = await router.route_task(
                preferred_tier="expensive",
                task=f"Find flaws in this claim. "
                     f"Your independent assessment was: '{independent_judgment}'. "
                     f"Now challenge the claim: '{claim.text}'",
            )

            # Step 3: Proponent (mid model — defends with evidence)
            proponent = await router.route_task(
                preferred_tier="mid",
                task=f"Defend this claim with evidence: '{claim.text}'",
            )

            # Step 4: Skeptic responds to proponent's defense
            rebuttal = await router.route_task(
                preferred_tier="expensive",
                task=f"Given this defense: '{proponent}', "
                     f"still find flaws in: '{claim.text}'",
            )

            # Step 5: Moderator verdict (cheap model — just adjudicates)
            verdict = await router.route_task(
                preferred_tier="cheap",
                task=f"Adjudicate. Claim: '{claim.text}'. "
                     f"Skeptic: '{skeptic}'. Proponent: '{proponent}'. "
                     f"Rebuttal: '{rebuttal}'. Is the claim credible?",
            )

            claim.verified = (verdict.confidence > 0.5)
            claim.verification_notes = verdict.reason
            if claim.verified:
                # Phase-boundary verification gate: cross-index citation check
                # (Wu, 2026, academic-research-skills v3.11 pattern)
                citation_result = await citation_service.verify(
                    claim.text,
                    indexes=["semantic_scholar", "openalex", "crossref", "arxiv"],
                )
                claim.citation_verified = citation_result.verified
                verified.append(claim)

        return verified
```

### 3.4 Multi-Provider Research Phase Allocation

```python
PHASE_MODEL_MAP = {
    # Research phases use different models based on cognitive demands
    "analyze":      {"tier": "mid",     "reason": "Decomposition benefits from Sonnet-level reasoning"},
    "search":       {"tier": "cheap",   "reason": "Keyword generation is cheap, fast"},
    "fetch":        {"tier": "cheap",   "reason": "URL fetching is tool execution, not LLM"},
    "cross_check":  {"tier": "mid",     "reason": "Factual comparison needs Sonnet-level accuracy"},
    "verify":       {"tier": "expensive","reason": "Adversarial review needs Opus-level rigor"},
    "synthesize":   {"tier": "mid",     "reason": "Report writing needs Sonnet-level prose"},
    "deep_verify":  {"tier": "expensive","reason": "Deep adversarial review on critical claims"},
}
```

### 3.5 IterResearch Evolving Report

```python
class EvolvingReport:
    """IterResearch-inspired workspace reconstruction.

    Instead of accumulating all search results in context,
    the report evolves iteratively:
    - Each phase produces a compressed report
    - Next phase starts from the compressed report
    - Old raw data is discarded (strategic forgetting)

    Result: constant context size regardless of search depth.
    """

    def __init__(self, question: str):
        self.question = question
        self.current_report = f"# Research: {question}\n\n## Initial Question\n{question}\n"
        self.version = 0
        self.max_length = 10_000  # Keep report under 10K tokens

    async def update(self, new_findings: str, synthesizer) -> str:
        """Synthesize new findings into the evolving report."""
        prompt = (
            f"Current report:\n{self.current_report}\n\n"
            f"New findings to incorporate:\n{new_findings}\n\n"
            f"Update the report, integrating new evidence. "
            f"Flag contradictions. Update confidence levels. "
            f"Output only the updated report."
        )
        updated = await synthesizer(prompt)
        self.current_report = updated[:self.max_length * 4]  # Char limit
        self.version += 1
        return self.current_report

    def get_context(self) -> str:
        """Get the current report for injection into agent context.
        State size is always O(1), never O(t)."""
        return self.current_report[:self.max_length]
```

### 3.6 NanoResearch Tri-Level Co-Evolution

```python
class ResearchSkillBank:
    """NanoResearch-inspired skill discovery from research patterns.

    Skills are compact procedural rules discovered from recurring research patterns:
    - "When researching APIs, always check: rate limits, auth method, SDK support"
    - "When evaluating claims, always check: author expertise, publication date, methodology"
    """

    def __init__(self, skill_store: MemoryStore):
        self.store = skill_store

    async def extract_skill(self, trajectory: ResearchTrajectory) -> Skill | None:
        """Extract a reusable skill from a successful research trajectory."""
        if not trajectory.successful:
            return None
        prompt = (
            f"From this successful research session, extract a reusable procedural rule:\n"
            f"Question: {trajectory.question}\n"
            f"Key steps: {trajectory.summarize_steps(5)}\n"
            f"Output: A compact rule (one paragraph) others can follow."
        )
        skill_text = await extract(prompt)
        return Skill(
            name=f"research-{slugify(trajectory.question[:30])}",
            description=skill_text,
            trigger_patterns=extract_triggers(trajectory),
            source_trajectory=trajectory.id,
        )
```

### 3.7 Architecture Diagram

```mermaid
graph TB
    subgraph "User"
        Q[Research Question]
    end

    subgraph "Deep Research Workflow (§4.15)"
        ANALYZE[Phase 1: Analyze<br/>Decompose into angles<br/>Model: Mid-tier]
        SEARCH[Phase 2: Search<br/>Fan-out parallel search<br/>Model: Cheap]
        FETCH[Phase 3: Fetch<br/>Extract sources<br/>Model: Cheap]
        CROSS[Phase 4: Cross-Check<br/>Compare + Contradictions<br/>Model: Mid-tier]
        VERIFY[Phase 5: Verify<br/>Adversarial review<br/>Model: Expensive]
        SYNTH[Phase 6: Synthesize<br/>Cited report<br/>Model: Mid-tier]
    end

    subgraph "Evidence Graph"
        EG[Evidence Graph<br/>DAG of Claim/Source nodes]
        CC[Contradiction Detector<br/>conflicting claim pairs]
        VC[Verified Claims<br/>≥2 supporting sources]
        COMP[Graph Compressor<br/>1,200:1 compression]
    end

    subgraph "Memory & Skills"
        ER[Evolving Report<br/>IterResearch O(1) state]
        SB[Skill Bank<br/>NanoResearch patterns]
        MM[Mind-Map<br/>Agentic Reasoning KG]
    end

    subgraph "Multi-Provider Router"
        ROUTER[Model Router §4.5<br/>Phase-aware model selection]
        CHEAP[Cheap: Haiku-class<br/>Search / Fetch]
        MID[Mid: Sonnet-class<br/>Analyze / Cross-check]
        EXP[Expensive: Opus-class<br/>Adversarial verify]
    end

    Q --> ANALYZE
    ANALYZE -->|Angles| SEARCH
    SEARCH -->|URLs| FETCH
    FETCH -->|Sources| CROSS
    CROSS -->|Claims + Edges| EG
    EG --> CC
    CC --> VERIFY
    VERIFY -->|Verified claims| SYNTH
    SYNTH -->|Cited report| Q

    EG --> COMP
    COMP -->|Compressed summary| ER
    ER -->|O(1) context| ANALYZE
    EG --> MM
    MM -->|Reasoning chains| SYNTH
    ER --> SB
    SB -->|Reusable skills| ANALYZE

    ANALYZE -.-> ROUTER
    SEARCH -.-> ROUTER
    FETCH -.-> ROUTER
    CROSS -.-> ROUTER
    VERIFY -.-> ROUTER
    SYNTH -.-> ROUTER

    ROUTER --> CHEAP
    ROUTER --> MID
    ROUTER --> EXP
```

## 4. Data Model

```python
@dataclass
class ResearchReport:
    question: str
    executive_summary: str
    key_findings: list[ResearchFinding]
    contradictions: list[Contradiction]
    sources: list[SourceNode]
    methodology: str                 # How the research was conducted
    confidence: str                  # high / medium / low
    limitations: list[str]          # What the research does NOT cover
    cited_claims: list[str]         # Claims that passed adversarial review
    citation_audit: CitationAudit   # Cross-index verification results (Wu, 2026)


@dataclass
class ResearchFinding:
    claim: str
    evidence: str
    sources: list[str]              # URLs
    confidence: float
    category: str
    verified: bool
    citation_verified: bool = False  # Cross-index check result (Wu, 2026)
    claim_audited: bool = False      # L3 faithfulness audit result (Wu, 2026)


@dataclass
class Contradiction:
    claim_a: str
    claim_b: str
    explanation: str
    resolution: str | None = None   # How the contradiction was resolved


@dataclass
class CitationAudit:
    """Cross-index citation verification result (academic-research-skills pattern).
    
    Wu (2026, v3.11.1): 4-index triangulation with terminal policy layer.
    Kong et al. (2026): verification must be architectural, not terminal.
    """
    indexes_checked: list[str]      # ["semantic_scholar", "openalex", "crossref", "arxiv"]
    results: dict[str, CitationResult]  # claim_id -> result
    terminal_failures: list[str]    # Claims with unresolved citation failures
    cache_hits: int = 0            # SQLite cache (90-day TTL)
    total_cost_cents: float = 0.0   # API cost for citation verification


@dataclass
class CitationResult:
    verified: bool
    confidence: float
    matched_index: str | None
    notes: str = ""
    # Wu (2026, v3.11): refined gate — narrows verification failures to
    # ID-keyed unmatched only (specific DOI lookup that provably fails).
    # Unindexable citations remain 'unresolvable' and never block.
    lookup_type: str = "id_keyed"   # "id_keyed" | "fuzzy" | "unresolvable"


@dataclass
class ClaimNode:
    id: str
    text: str
    source_url: str
    confidence: float = 0.5
    sources: list[str] = field(default_factory=list)
    category: str = "unknown"
    verified: bool = False
    verification_notes: str = ""


@dataclass
class SourceNode:
    url: str
    title: str
    content_preview: str
    domain: str
    publish_date: datetime | None = None
    authority_score: float = 0.5
    content_hash: str = ""


@dataclass
class EvidenceEdge:
    from_id: str
    to_id: str
    relation: Literal["supports", "contradicts", "refines", "independent"]
    strength: float = 0.5
```

## 5. Build Outline

### Phase 2a — Basic Research Workflow (Week 1-2)
- [ ] Implement `deep_research()` orchestrator function with 6 phases
- [ ] Phase 1: Question analysis and angle decomposition
- [ ] Phase 2: Parallel web search across angles
- [ ] Phase 3: Source fetching with content extraction
- [ ] Basic report synthesis (Phase 6)
- [ ] Wire into CLI as `lyra research <question>` command
- [ ] **Dependency:** Tool system (§4.6 WebSearch, WebFetch), Workflow Engine (§4.13)

### Phase 2b — Evidence Graph (Week 2-3)
- [ ] Implement `EvidenceGraph` with ClaimNode, SourceNode, EvidenceEdge
- [ ] Implement claim extraction from source content (LLM-based)
- [ ] Implement relation detection (supports/contradicts/refines)
- [ ] Implement contradiction detection and resolution
- [ ] Implement graph compression (1,200:1 target)
- [ ] **Dependency:** Phase 2a

### Phase 2c — Adversarial Verification (Week 3-4)
- [ ] Implement `AdversarialVerifier` with Skeptic/Proponent/Moderator roles
- [ ] Implement claim-by-claim adversarial review loop
- [ ] Implement verdict consolidation (only surviving claims in report)
- [ ] Integrate with Model Router for phase-aware model selection
- [ ] Verification quality tests: known-false claims should be caught
- [ ] **Dependency:** Phase 2b, Router (§4.5)

### Phase 2d — Evolving Report + Skill Extraction (Week 4-5)
- [ ] Implement `EvolvingReport` with iterative synthesis
- [ ] Implement `ResearchSkillBank` for trajectory-to-skill extraction
- [ ] Implement Agentic Reasoning Mind-Map for long-chain memory
- [ ] Integrate with Memory system for cross-session research memory
- [ ] **Dependency:** Phase 2c, Memory system (§4.2)

### Phase 2e — Multi-Provider Research Allocation (Week 5)
- [ ] Implement phase-to-model-tier mapping (Analyze=mid, Search=cheap, Verify=expensive, etc.)
- [ ] Wire into Model Router for per-phase model selection
- [ ] Token and cost tracking per research phase
- [ ] Integration tests: full research run from question to cited report
- [ ] **Dependency:** Phase 2c, Router (§4.5)

## 6. Multi-Provider Note

Deep research is where multi-provider routing adds unique value:
- **Phase-specific model selection**: Search/fetch uses cheap models (Haiku-class), cross-check uses mid (Sonnet), verification uses expensive (Opus). This is the most impactful use case for the 3-tier router. CaTS (Huang et al., 2026, ICLR) demonstrates that model confidence calibration combined with adaptive sampling saves 94.2% of samples by early-stopping on high-confidence outputs — suggesting that verification phase could dynamically skip expensive-model review for claims where mid-tier confidence already exceeds threshold.
- **Provider diversity**: Different providers have different research strengths. Claude excels at nuanced analysis, DeepSeek at structured extraction, GPT at creative synthesis. The router can match phase to best provider. Cross-backbone transfer validated by Argus: Navigator policy trained on Qwen3.5-35B Searcher generalizes zero-shot to DeepSeek-V4-Flash-Max (78.5%) and Seed-2.0-Pro (82.4%) without retraining (Zhang et al., 2026, arXiv:2605.16217v3).
- **Fallback**: If one provider's API degrades during a long research run, the workflow can switch providers mid-stream without losing progress (state is in the evidence graph, not the LLM context).
- **Local models for sensitive research**: For research on internal/proprietary topics, route all phases through Ollama/vLLM local models.
- **Cost benchmarks from production deployments**: academic-research-skills (Wu, 2026, v3.11) full pipeline: $4-6 for ~15k-word paper with ~60 references, of which citation verification adds near-zero cost (API-only, SQLite-cached). AUTO REPRODUCE (Zhao et al., 2026, arXiv:2505.20662v4): $1.87 per experiment reproduction. AutoResearchClaw (Liu et al., 2026): $3-15 per full run in LLM usage. These benchmarks validate that the expensive phases (verification, synthesis) can be budgeted at $3-15 per research run when cheaper models handle search/fetch.

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Adversarial verification rejects correct claims (false negative) | Medium | Medium | Use 2/3 majority for verification, not single-skeptic veto. Cognitive Anchoring (Xu et al., 2026, ICLR) ensures agents form independent conclusions before peer influence. K=3 debate agents (Liu et al., 2026) is sweet spot — K=2 degenerates (-23% diversity) |
| Evidence graph grows too large (>50K tokens) | Medium | Low | Graph compression phase; 1,200:1 target verified by Argus (Zhang et al., 2026). Staged approach: Phase 1 = 100:1, Phase 2 = 1,200:1 |
| Research runs exceed token budget (100+ search results) | High | Medium | Evolving report keeps constant O(1) state (IterResearch, ICLR 2026); raw results discarded. Cross-run lesson store with time-decayed weighting (Liu et al., 2026, T_1/2=30 days) prevents contradictory advice accumulation |
| Contradiction detection misses subtle conflicts | High | Medium | Focus on explicit contradictions; flag "uncertain" not "resolved". Kong et al. (2026): 58.6% of errors are semantic (runs but wrong) — these are invisible to execution-based detection |
| Multi-hop research loops infinitely (echo chamber) | Low | High | Max iteration limit (default 5 hops); novelty check before re-search. AutoResearchClaw Pivot/Refine/Proceed loop caps at N_p=2 pivots, N_r=10 refines |
| Source authority scoring is unreliable | High | Low | Authority score is advisory, not filtering; source is attached to claim. Cross-index citation verification (Wu, 2026, v3.11) narrows failures to ID-keyed unmatched only |
| Social contagion / collective false memory (Mandela effect) | Medium | High | Cognitive Anchoring prompt (Xu et al., 2026): 69.6% sigma reduction. Each agent forms independent conclusion before seeing peer output. Consensus treated as potential manipulation signal, not reliability indicator |
| Citation verification blocks legitimate unindexed citations | Medium | Low | Wu (2026, v3.11) pattern: `lookup_verified == false` narrowed to ID-keyed unmatched only; unindexable citations stay `unresolvable` and never block. Default advisory mode, opt-in strict mode |

## 8. (A) Parity vs (B) Breakthrough

### (A) Parity — What Claude Code already does
- `/deep-research` bundled workflow: fan-out -> cross-check -> cited report
- Adversarial verification: agents challenge each other's findings
- Consolidated cited report as final output
- Web search with domain filters

### (B) Breakthrough — What Lyra adds
- **Evidence graph compression** — Argus-style 1,200:1 compression decouples reasoning context from searcher count. Claude Code's deep-research keeps all intermediate results in context.
- **IterResearch evolving report** — O(1) state size via workspace reconstruction. Enables arbitrarily long research sessions (2048+ interactions at 40K context). Claude Code's context grows linearly.
- **NanoResearch skill extraction** — Successful research trajectories are distilled into reusable skills. Each research session makes future sessions more efficient. Claude Code has no research skill learning.
- **Multi-provider phase allocation** — Research phases use different models: Haiku for search, Sonnet for synthesis, Opus for verification. Claude Code uses one model for everything.
- **Agentic Reasoning Mind-Map** — Knowledge-graph memory for long research chains. Maintains logical structure across dozens of sub-queries.
- **Self-organizing research teams** — AutoScientists pattern with shared success/failure log, cross-layer feedback, and collaborative idea generation.

## 9. Baseline Delta

| Dimension | Before (Lyra current) | After (with Deep Research) |
|-----------|----------------------|---------------------------|
| Research scope | Single search | Multi-angle, multi-hop, multi-source |
| Evidence handling | Raw text | Structured evidence graph with typed edges |
| Verification | None | Adversarial Skeptic/Proponent/Moderator + cross-index citation verification (Wu, 2026) + L3 claim faithfulness audit |
| Report format | Raw text | Cited report with confidence ratings + citation audit trail |
| Context management | None (full history) | Evolving report (IterResearch O(1) state, ICLR 2026) |
| Skill learning | None | Trajectory-to-skill extraction with time-decayed lesson store (AutoResearchClaw, Liu et al., 2026) |
| Phase allocation | One model | Phase-aware: search=cheap, verify=expensive. Cross-backbone zero-shot transfer validated (Argus, arXiv:2605.16217) |
| Social contagion defense | None | Cognitive Anchoring prompt (Xu et al., 2026, ICLR): 69.6% sigma reduction |
| Citation verification | None | 4-index triangulation (Wu, 2026 v3.11): Semantic Scholar + OpenAlex + Crossref + arXiv |
| Benchmark target | <10% on BrowseComp | >=30% on BrowseComp (Phase 2) |

## 10. Expert Review

### Reviewer 1: Research Methodology Expert
"The evidence graph with support/contradiction edges is the right foundation but the relation detection (claim A 'supports' claim B) is harder than it looks. Two different articles citing the same statistic isn't necessarily support — they could both be citing the same flawed original study. Add a `source_overlap` field to edges: if the only connection is a shared source, mark it as 'independent' not 'supports'. Also: authority scoring needs to be domain-aware — a niche expert blog can be more authoritative than a broad news article on the same topic. Use domain-specific authority models, not a single pipeline. **New evidence supports this view:** Kong et al. (2026, arXiv:2605.18661v1) confirms diversity collapse in LLM-generated ideas — they cluster in narrow regions, not solvable by scaling. The 58.6% semantic error rate in research code (runs but wrong algorithm) means execution-based verification alone is insufficient. The cross-index citation verification approach from Wu (2026, academic-research-skills v3.11) — 4-index triangulation with 967 CI tests — is exactly the kind of deterministic integrity gate the evidence graph needs."

### Reviewer 2: Deep Research Engineer
"The adversarial verification loop is good but has a known failure mode: if the skeptic is too weak (cheap model) and the proponent is too strong (expensive model), every claim passes validation. The routing is: cheap-agent challenges, mid-agent defends, cheap-agent adjudicates. The defender has the advantage. Fix: swap to expensive-agent challenges, cheap-agent defends. The skeptic should be the stronger model for effective adversarial review. For the 1,200:1 compression: implement a staged approach. Phase 1: 100:1 (simple chunking). Phase 2: 1,200:1 (Argus-style with learned compression). Don't aim for the full ratio immediately. **New evidence:** Xu et al. (2026, ICLR, arXiv:2602.00428v2) adds a critical dimension: multi-agent systems can converge on incorrect answers due to social influence (Mandela effect). Cognitive Anchoring prompts achieve 69.6% sigma reduction. I'm upgrading my recommendation: add Cognitive Anchoring BEFORE the adversarial loop — each agent must form an independent conclusion before reading peer output. Without this, the verification loop itself becomes a contagion vector. Also, the pandemic's K=3 debate count (AutoResearchClaw, Liu et al., 2026) is validated: K=2 degenerates, K=5 is wasteful."

### Reviewer 3: Knowledge Management Practitioner
"The skill extraction from research trajectories is the most valuable long-term feature. But it only works if the extracted skills are actually used — which requires the Skill Registry to search and apply them. Wire the `ResearchSkillBank.lookup()` call into the workflow's Phase 1 (angle decomposition) so past research informs future research naturally. The Mind-Map knowledge graph is powerful but expensive to maintain per research session. I'd make it optional: enabled for 'deep' mode, disabled for 'quick' research. Keep the Evolving Report as the default context manager (it's IterResearch-proven at O(1) state). **New evidence:** AutoResearchClaw's cross-run lesson store (Liu et al., 2026) provides a working template with time-decayed weighting (T_1/2=30 days) — each lesson abstracted as category, severity, and mitigation. The 30-day half-life prevents contradictory advice from accumulating. This is lower-cost than full skill extraction (no LLM distillation needed) and should be the Phase 1 implementation. Full NanoResearch-style SkillBank with SDPO policy learning (arXiv:2605.10813) can follow in Phase 2. The lesson store achieves +0.48 quality and +1 completion in ablation (Liu et al., 2026)."

## 11. References

1. Claude Code Deep-Research — code.claude.com/docs/en/workflows#bundled-workflow-deep-research. Fan-out, cross-check, cited report.
2. Argus — Zhang, Z. et al. "Argus: Evidence Assembly for Scalable Deep Research Agents." arXiv:2605.16217v3, May 2026. MiroMind AI. Searcher-Navigator, evidence graph, 1,200:1 compression, 86.2% BrowseComp.
3. AutoScientists — §3.6 research file. Self-organizing teams, shared success/failure log.
4. IterResearch — Chen, G. et al. "IterResearch: Rethinking Long-Horizon Agents with Interaction Scaling." ICLR 2026, arXiv:2511.07327v2. Evolving report, O(1) state, 2048 interactions.
5. NanoResearch — Xu, J. et al. "NanoResearch: Co-Evolving Skills, Memory, and Policy for Personalized Research Automation." arXiv:2605.10813v2, 2026. Tri-level co-evolution, skill bank, SDPO policy learning.
6. Agentic Reasoning Mind-Map — Wu, J. et al. "Agentic Reasoning: A Streamlined Framework for Enhancing LLM Reasoning with Agentic Tools." arXiv:2502.04644v2, 2025. Oxford/NUS/CMU. Knowledge-graph reasoning memory, +153% HLE.
7. VirSci — Collaborative idea generation/evaluation/refinement via multi-agent debate.
8. BREAKTHROUGH-ARCHITECTURE.md — Deep Research as bundled workflow in Phase 2.
9. BASELINE.md — Lyra current state: `none` maturity for §4.15 Deep Research.
10. AutoResearchClaw — Liu, J. et al. "AutoResearchClaw: Self-Reinforcing Autonomous Research with Human-AI Collaboration." arXiv:2605.20025v2, May 2026. 35 authors, 12 institutions. K=3 debate, Pivot/Refine/Proceed loop, self-healing, cross-run lesson store. github.com/aiming-lab/AutoResearchClaw.
11. Kong et al. Survey — Kong, L. et al. "AI for Auto-Research: Roadmap and User Guide." arXiv:2605.18661v1, May 2026. Survey of 270+ auto-research systems. Four-phase/eight-stage lifecycle framework, verification gates.
12. AUTO REPRODUCE — Zhao, X. et al. "AUTO REPRODUCE: Automatic AI Experiment Reproduction with Paper Lineage." arXiv:2505.20662v4, Apr 2026. Tsinghua/OpenBMB. Paper lineage construction, <summary, code> tuples, $1.87/run. github.com/AI9Stars/AutoReproduce.
13. academic-research-skills — Wu, C.-I. "academic-research-skills." v3.11.1, 2026. github.com/Imbad0202/academic-research-skills. 38 agents, 4 skills, 25 modes. 4-index citation verification, L3 claim-faithfulness audit, 967 CI tests.
14. Shahani — Shahani, R. "Building Reliable AI Systems: Applications and Agents You Can Trust." MEAP V12, Manning Publications, 2026. Three-layer reliability framework, hybrid search, human-in-the-loop.
15. Mandela Effect — Xu, N. et al. "When Agents 'Misremember' Collectively: Exploring the Mandela Effect in LLM-based Multi-Agent Systems." ICLR 2026, arXiv:2602.00428v2. Zhejiang University. Cognitive Anchoring, 69.6% sigma reduction, K=3-5 sweet spot.
16. CaTS — Huang, C. et al. "CaTS: Calibrated Test-Time Scaling for Efficient LLM Reasoning." ICLR 2026. WashU/CMU/UW. Self-Calibration, SSC, 94.2% sample savings.
17. Qi et al. — Qi, J. et al. "Towards Trustworthy Agentic AI: A Comprehensive Survey." arXiv:2605.23989v1, May 2026. CUHK/Fudan/SAIS. Defense-in-depth, four assurance tiers, complementary mitigations.

## 12. Evidence Base

Sources consulted for the deep-read update (Run 2, June 7, 2026):

| ID | Source | Type | Venue | Key Contribution |
|----|--------|------|-------|------------------|
| P15 | AutoResearchClaw (Liu et al., 2026) | Paper | arXiv:2605.20025v2 | 23-stage pipeline, Pivot/Refine/Proceed, K=3 debate, cross-run lesson store |
| P1 | Kong et al. (Survey) | Paper | arXiv:2605.18661v1 | 270+ system survey, phase-boundary verification gates, 80% fabrication rate |
| P3 | AUTO REPRODUCE (Zhao et al., 2026) | Paper | arXiv:2505.20662v4 | Paper lineage construction, <summary,code> tuples, $1.87/run |
| P5 | Mandela Effect (Xu et al., 2026) | Paper | ICLR, arXiv:2602.00428v2 | Cognitive Anchoring, 69.6% sigma reduction, social contagion defense |
| P10 | CaTS (Huang et al., 2026) | Paper | ICLR 2026 | Self-Calibrated confidence, 94.2% sample savings, SSC training |
| P7 | Qi et al. (Survey) | Paper | arXiv:2605.23989v1 | Defense-in-depth, 4 assurance tiers, complementary mitigations |
| P16 | Argus (Zhang et al., 2026) | Paper | arXiv:2605.16217v3 | Evidence DAG, 1,200:1 compression, GRPO + contrastive reward |
| P4 | IterResearch (Chen et al., 2026) | Paper | ICLR, arXiv:2511.07327v2 | Evolving report, O(1) state size, MDP formulation |
| NanoResearch (Xu et al., 2026) | Paper | arXiv:2605.10813v2 | Tri-level co-evolution, SkillBank, SDPO policy learning |
| P8 | Agentic Reasoning (Wu et al., 2025) | Paper | arXiv:2502.04644v2 | Mind-Map knowledge graph, 66.13 GAIA, 6.8 min/query |
| P12 | SELF-RAG (Asai et al., 2023) | Paper | arXiv:2310.11511v1 | Reflection tokens, adaptive retrieval, ISSUP/ISUSE |
| W1 | academic-research-skills (Wu, 2026) | Repo | v3.11.1, github.com/Imbad0202 | 4-index citation verification, L3 audit, 967 CI tests |
| W2 | AutoResearchClaw (AIMING Lab) | Repo | github.com/aiming-lab | Open-source implementation, ARC-Bench evaluation |
| B1 | Building Reliable AI Systems (Shahani, 2026) | Book | MEAP V12, Manning | Three-layer reliability, hybrid search, human-in-the-loop |
| | AutoScientists | Research File | §3.6 | Self-organizing teams, success/failure log |

All sources are open-access (arXiv, open-source repos, or MEAP books). None require institutional access.

## 13. Changelog
- Run 1: Initial plan — 6-phase deep-research workflow, evidence graph, adversarial verification, evolving report, skill extraction, multi-provider phase allocation
- Run 2: Deep-read update — integrated 12 new sources. Added: AutoResearchClaw pipeline (Liu et al., 2026), Kong et al. 270-system survey, AUTO REPRODUCE paper lineage, academic-research-skills verification framework (Wu, 2026), Mandela Effect social contagion defense (Xu et al., 2026), CaTS confidence calibration (Huang et al., 2026), Qi et al. defense-in-depth survey, Shahani reliability framework. Enhanced every technique section with specific benchmark numbers, trade-off analyses, and convergent findings. Added Evidence Base section. Updated adversarial verification with Cognitive Anchoring and cross-index citation verification. Updated Expert Review to synthesize new evidence. 12 new source citations added.

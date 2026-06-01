# §4.15 Implementation Plan: Deep Research System

**Status**: PLAN  
**Priority**: HIGH×HIGH (P0)  
**Effort**: 4-5 weeks  
**Dependencies**: §4.13 (Swarm Fleet), §4.14 (Full Autonomy)

---

## 1. Overview

Implement self-organizing deep research system combining:
- **AutoScientists decentralized coordination** for team self-organization
- **Agentic reasoning** with interleaved tool use during reasoning
- **Multi-stage pipeline** (planning → execution → analysis → synthesis)
- **Adversarial validation** with peer critique before execution
- **Citation integrity** with 4-layer verification

**Target Capabilities**:
- Self-organizing research teams around promising directions
- Parallel exploration with cross-team knowledge sharing
- Adversarial validation to prevent wasted compute
- Deep research reports (5,000-6,500 words) with verified citations
- Autonomous decision loops (PROCEED/REFINE/PIVOT)

**Performance Targets** (based on research):
- +8.33% improvement through decentralized coordination (AutoScientists)
- 1.9× faster convergence through team-based exploration
- +18.3% robustness through self-learning (AutoResearchClaw)

---

## 2. Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Research Orchestrator                       │
│  - Topic decomposition                                       │
│  - Team formation                                            │
│  - Progress monitoring                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Team A  │  │  Team B  │  │  Team C  │
        │ (Hypo 1) │  │ (Hypo 2) │  │ (Hypo 3) │
        └──────────┘  └──────────┘  └──────────┘
                │             │             │
                └─────────────┼─────────────┘
                              ▼
                    ┌──────────────────┐
                    │  Shared State    │
                    │  - Champions     │
                    │  - Exp. logs     │
                    │  - Forums        │
                    │  - Queues        │
                    │  - Dead-ends     │
                    └──────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Analyst  │  │Experiment│  │ Critic   │
        │  Agent   │  │  Agent   │  │  Agent   │
        └──────────┘  └──────────┘  └──────────┘
```

### 2.2 Agent Types

**1. Analyst Agent**:
- Reads experiment logs and discussion forums
- Ranks proposals by effect size and feasibility
- Maintains hypothesis documents
- Updates dead-end registry
- Writes to team proposal queues

**2. Experiment Agent**:
- Claims proposals from queue
- Applies modifications to champion solution
- Executes experiments (code, simulations, analysis)
- Records results to log and forum
- Noise-gated confirmation with second seed

**3. Critic Agent**:
- Reviews proposals before execution
- Identifies flaws, risks, redundancies
- Checks dead-end registry
- Provides adversarial feedback
- Approves or rejects proposals

**4. Synthesizer Agent**:
- Aggregates findings across teams
- Generates research reports
- Ensures citation integrity
- Produces visualizations and charts

### 2.3 Research Workflow

**Phase 1: Scoping** (AutoResearchClaw pattern)
1. Topic decomposition into research questions
2. Hardware detection (GPU/MPS/CPU)
3. Initial hypothesis generation

**Phase 2: Literature Review**
1. Multi-source search (OpenAlex, Semantic Scholar, arXiv)
2. Paper retrieval and parsing
3. Knowledge extraction and clustering
4. Gap identification

**Phase 3: Hypothesis Formation**
1. Multi-agent debate for hypothesis generation
2. Hypothesis ranking by promise
3. Team formation around top hypotheses
4. Initial proposal generation

**Phase 4: Parallel Exploration**
1. Teams work independently on hypotheses
2. Analyst agents generate proposals
3. Critic agents review proposals
4. Experiment agents execute approved proposals
5. Cross-team knowledge sharing via shared state

**Phase 5: Dynamic Reorganization**
1. Monitor team progress
2. Detect stagnation (no improvement for N iterations)
3. Trigger re-discussion phase
4. Reform teams around new promising directions

**Phase 6: Synthesis**
1. Aggregate findings across teams
2. Identify champion solutions
3. Generate comprehensive report
4. Verify citations (4-layer verification)
5. Produce visualizations

---

## 3. Implementation Phases

### Phase 1: Shared State Infrastructure (Week 1)

**Tasks**:
1. Extend shared context store from §4.13 for research-specific data
2. Add experiment log schema
3. Add discussion forum with threading
4. Add proposal queue with priority ranking
5. Add dead-end registry with similarity matching
6. Write unit tests

**Deliverables**:
- `packages/lyra-research/src/shared-state.ts`
- `packages/lyra-research/src/schemas/`
- Unit tests

**Acceptance Criteria**:
- Shared state persists across agent restarts
- Concurrent access is thread-safe
- Dead-end similarity matching works (>80% accuracy)
- Proposal ranking by effect size

### Phase 2: Agent Implementations (Week 1-2)

**Tasks**:
1. Implement `AnalystAgent` class
2. Implement `ExperimentAgent` class
3. Implement `CriticAgent` class
4. Implement `SynthesizerAgent` class
5. Add agent communication via channels (§4.13)
6. Write integration tests

**Deliverables**:
- `packages/lyra-research/src/agents/analyst.ts`
- `packages/lyra-research/src/agents/experiment.ts`
- `packages/lyra-research/src/agents/critic.ts`
- `packages/lyra-research/src/agents/synthesizer.ts`
- Integration tests

**Acceptance Criteria**:
- Analyst generates ranked proposals
- Experiment executes proposals and logs results
- Critic provides adversarial feedback
- Synthesizer produces coherent reports

### Phase 3: Team Self-Organization (Week 2-3)

**Tasks**:
1. Implement team formation algorithm
2. Add hypothesis ranking logic
3. Implement stagnation detection
4. Add dynamic reorganization triggers
5. Write team coordination tests

**Deliverables**:
- `packages/lyra-research/src/team-formation.ts`
- `packages/lyra-research/src/stagnation-detection.ts`
- Team coordination tests

**Acceptance Criteria**:
- Teams form around top hypotheses
- Stagnation detected after N iterations without improvement
- Reorganization triggers successfully
- Teams maintain focus on assigned hypotheses

### Phase 4: Literature Review Pipeline (Week 3)

**Tasks**:
1. Integrate OpenAlex API for paper search
2. Integrate Semantic Scholar API
3. Integrate arXiv API
4. Implement paper parsing (PDF extraction)
5. Add knowledge clustering
6. Write literature review tests

**Deliverables**:
- `packages/lyra-research/src/literature/`
- API integrations
- Literature review tests

**Acceptance Criteria**:
- Multi-source search returns relevant papers
- Paper parsing extracts key information
- Knowledge clustering identifies gaps
- Citation extraction works correctly

### Phase 5: Agentic Reasoning with Tool Use (Week 4)

**Tasks**:
1. Implement interleaved tool use during reasoning
2. Add search tools (web, academic, code)
3. Add code execution sandbox
4. Add computational verification tools
5. Write reasoning tests

**Deliverables**:
- `packages/lyra-research/src/reasoning/`
- Tool integrations
- Reasoning tests

**Acceptance Criteria**:
- Tools invoked during reasoning, not after
- Search results integrated into reasoning chain
- Code execution provides verification
- Reasoning quality improves with tool use

### Phase 6: Citation Integrity System (Week 4-5)

**Tasks**:
1. Implement 4-layer citation verification
2. Add arXiv ID validation
3. Add CrossRef/DataCite DOI lookup
4. Add Semantic Scholar title matching
5. Add LLM relevance scoring
6. Write citation verification tests

**Deliverables**:
- `packages/lyra-research/src/citations/`
- Citation verification tests

**Acceptance Criteria**:
- 4-layer verification catches fabricated citations
- arXiv ID validation works
- DOI lookup succeeds for valid papers
- Title matching handles variations
- LLM relevance scoring accurate

### Phase 7: Report Generation (Week 5)

**Tasks**:
1. Implement report structure (5,000-6,500 words)
2. Add section-by-section drafting
3. Add visualization generation (charts, diagrams)
4. Add LaTeX export
5. Add peer review pass
6. Write report generation tests

**Deliverables**:
- `packages/lyra-research/src/report-generation/`
- Report templates
- Report generation tests

**Acceptance Criteria**:
- Reports meet word count target
- Sections flow logically
- Visualizations support findings
- LaTeX export compiles successfully
- Peer review identifies issues

---

## 4. API Design

### 4.1 Starting Deep Research

```typescript
import { DeepResearch } from '@lyra/research';

const research = new DeepResearch({
  topic: 'Optimizing transformer attention mechanisms for long sequences',
  maxTeams: 3,
  maxIterations: 50,
  budget: {
    maxCost: 200.00,
    maxDuration: 86400000, // 24 hours
  },
  literatureSources: ['openalex', 'semantic-scholar', 'arxiv'],
  adversarialValidation: true,
  citationVerification: true,
});

await research.start();
```

### 4.2 Monitoring Progress

```typescript
// Subscribe to research events
research.on('team-formed', (team) => {
  console.log(`Team formed: ${team.name} (hypothesis: ${team.hypothesis})`);
});

research.on('proposal-submitted', (proposal) => {
  console.log(`Proposal: ${proposal.description}`);
});

research.on('proposal-critiqued', (critique) => {
  console.log(`Critique: ${critique.verdict} - ${critique.reasoning}`);
});

research.on('experiment-complete', (result) => {
  console.log(`Experiment: ${result.status} (effect size: ${result.effectSize})`);
});

research.on('team-reorganized', (event) => {
  console.log(`Teams reorganized: ${event.reason}`);
});

research.on('research-complete', (report) => {
  console.log('Research complete!');
  console.log(`Champion solution: ${report.champion.description}`);
  console.log(`Total experiments: ${report.totalExperiments}`);
  console.log(`Report: ${report.path}`);
});
```

### 4.3 Shared State Access

```typescript
// Analyst agent submits proposal
await sharedState.submitProposal('team-a', {
  id: generateId(),
  description: 'Use sparse attention with local windows',
  hypothesis: 'Sparse attention reduces complexity from O(n²) to O(n√n)',
  expectedEffectSize: 0.75,
  estimatedCost: 5.00,
  author: analystId,
});

// Critic agent reviews proposal
const proposal = await sharedState.claimProposal('team-a', criticId);
const critique = await criticAgent.review(proposal);

if (critique.verdict === 'REJECT') {
  await sharedState.rejectProposal(proposal.id, critique.reasoning);
} else {
  await sharedState.approveProposal(proposal.id);
}

// Experiment agent executes approved proposal
const approvedProposal = await sharedState.claimApprovedProposal('team-a', experimentId);
const result = await experimentAgent.execute(approvedProposal);

await sharedState.logExperiment({
  id: generateId(),
  proposalId: approvedProposal.id,
  result: result.status,
  metrics: result.metrics,
  insights: result.insights,
  timestamp: Date.now(),
  author: experimentId,
});

// Check if approach is dead-end before proposing
if (await sharedState.isDeadEnd('full-attention-with-caching')) {
  console.log('Approach already tried and failed, skipping');
  return;
}
```

### 4.4 Team Self-Organization

```typescript
// Initial team formation
const teams = await formTeams({
  hypotheses: [
    'Sparse attention reduces complexity',
    'Linear attention approximates full attention',
    'Hierarchical attention captures long-range dependencies',
  ],
  maxTeams: 3,
  agentsPerTeam: 3, // 1 analyst, 1 experiment, 1 critic
});

// Monitor for stagnation
const stagnationDetector = new StagnationDetector({
  threshold: 5, // No improvement for 5 iterations
  metric: 'effectSize',
});

stagnationDetector.on('stagnation-detected', async (team) => {
  console.log(`Team ${team.name} stagnated, triggering reorganization`);
  
  // Re-discussion phase
  const newHypotheses = await generateNewHypotheses({
    learnings: await sharedState.getExperiments({ team: team.name }),
    deadEnds: await sharedState.getDeadEnds(),
  });
  
  // Reform teams
  const newTeams = await formTeams({
    hypotheses: newHypotheses,
    maxTeams: 3,
    agentsPerTeam: 3,
  });
  
  // Resume exploration
  await resumeExploration(newTeams);
});
```

---

## 5. Adversarial Validation

### 5.1 Critique Protocol

**Before Execution**:
1. Analyst submits proposal to queue
2. Critic claims proposal for review
3. Critic checks:
   - Is approach in dead-end registry?
   - Is proposal redundant with recent experiments?
   - Are expected results plausible?
   - Is cost justified by expected effect size?
   - Are there obvious flaws in reasoning?
4. Critic provides verdict: APPROVE, REJECT, REVISE
5. Only approved proposals move to execution queue

**Implementation**:
```typescript
class CriticAgent {
  async review(proposal: Proposal): Promise<Critique> {
    // Check dead-ends
    if (await this.sharedState.isDeadEnd(proposal.approach)) {
      return {
        verdict: 'REJECT',
        reasoning: 'Approach already tried and failed',
        confidence: 'HIGH',
      };
    }
    
    // Check redundancy
    const recentExperiments = await this.sharedState.getExperiments({
      limit: 10,
      team: proposal.team,
    });
    
    if (this.isRedundant(proposal, recentExperiments)) {
      return {
        verdict: 'REJECT',
        reasoning: 'Similar experiment already conducted',
        confidence: 'HIGH',
      };
    }
    
    // LLM-based critique
    const llmCritique = await this.llm.critique({
      proposal: proposal.description,
      hypothesis: proposal.hypothesis,
      context: await this.sharedState.getContext(proposal.team),
    });
    
    return llmCritique;
  }
}
```

### 5.2 Cross-Team Knowledge Sharing

**Mechanism**:
- All experiment results written to shared log (visible to all teams)
- Dead-end registry shared across teams
- Discussion forum allows cross-team communication
- Champion solutions visible to all teams

**Benefits**:
- Prevents redundant exploration
- Enables cross-pollination of ideas
- Accelerates convergence through shared learnings

---

## 6. Citation Integrity

### 6.1 4-Layer Verification

**Layer 1: arXiv ID Check**
```typescript
async function verifyArxivId(citation: Citation): Promise<boolean> {
  if (!citation.arxivId) return false;
  
  const response = await fetch(`https://export.arxiv.org/api/query?id_list=${citation.arxivId}`);
  const xml = await response.text();
  
  return xml.includes('<entry>'); // Paper exists
}
```

**Layer 2: CrossRef/DataCite DOI Lookup**
```typescript
async function verifyDoi(citation: Citation): Promise<boolean> {
  if (!citation.doi) return false;
  
  try {
    const response = await fetch(`https://api.crossref.org/works/${citation.doi}`);
    const data = await response.json();
    return data.status === 'ok';
  } catch {
    // Try DataCite
    const response = await fetch(`https://api.datacite.org/dois/${citation.doi}`);
    const data = await response.json();
    return data.data !== undefined;
  }
}
```

**Layer 3: Semantic Scholar Title Match**
```typescript
async function verifyTitle(citation: Citation): Promise<boolean> {
  const response = await fetch(
    `https://api.semanticscholar.org/graph/v1/paper/search?query=${encodeURIComponent(citation.title)}`
  );
  const data = await response.json();
  
  if (!data.data || data.data.length === 0) return false;
  
  // Fuzzy match on title
  const similarity = stringSimilarity(citation.title, data.data[0].title);
  return similarity > 0.8;
}
```

**Layer 4: LLM Relevance Scoring**
```typescript
async function verifyRelevance(citation: Citation, context: string): Promise<number> {
  const prompt = `
Given the research context:
${context}

And the cited paper:
Title: ${citation.title}
Abstract: ${citation.abstract}

Rate the relevance of this citation on a scale of 0.0 to 1.0.
Consider: Does the citation support the claim? Is it from a reputable source?
  `;
  
  const response = await llm.complete(prompt);
  return parseFloat(response); // 0.0 to 1.0
}
```

**Combined Verification**:
```typescript
async function verifyCitation(citation: Citation, context: string): Promise<VerificationResult> {
  const results = await Promise.all([
    verifyArxivId(citation),
    verifyDoi(citation),
    verifyTitle(citation),
    verifyRelevance(citation, context),
  ]);
  
  return {
    arxivValid: results[0],
    doiValid: results[1],
    titleValid: results[2],
    relevanceScore: results[3],
    overallValid: results[0] || results[1] || (results[2] && results[3] > 0.7),
  };
}
```

---

## 7. Report Generation

### 7.1 Report Structure

**Sections** (5,000-6,500 words total):
1. **Abstract** (200-300 words)
2. **Introduction** (800-1,000 words)
3. **Related Work** (1,000-1,500 words)
4. **Methodology** (1,200-1,500 words)
5. **Results** (1,500-2,000 words)
6. **Discussion** (800-1,000 words)
7. **Conclusion** (300-400 words)
8. **References** (verified citations)

### 7.2 Section-by-Section Drafting

```typescript
class ReportGenerator {
  async generateReport(research: ResearchContext): Promise<Report> {
    const sections: ReportSection[] = [];
    
    // Draft each section sequentially
    sections.push(await this.draftAbstract(research));
    sections.push(await this.draftIntroduction(research));
    sections.push(await this.draftRelatedWork(research));
    sections.push(await this.draftMethodology(research));
    sections.push(await this.draftResults(research));
    sections.push(await this.draftDiscussion(research));
    sections.push(await this.draftConclusion(research));
    
    // Verify citations
    const citations = this.extractCitations(sections);
    const verifiedCitations = await this.verifyCitations(citations, research);
    
    // Generate visualizations
    const visualizations = await this.generateVisualizations(research);
    
    // Peer review pass
    const review = await this.peerReview(sections);
    if (review.hasIssues) {
      sections = await this.revise(sections, review.feedback);
    }
    
    // Export to LaTeX
    const latex = await this.exportToLatex(sections, verifiedCitations, visualizations);
    
    return {
      sections,
      citations: verifiedCitations,
      visualizations,
      latex,
      wordCount: this.countWords(sections),
    };
  }
}
```

### 7.3 Visualization Generation

**Chart Types**:
- Line charts for performance over iterations
- Bar charts for comparing approaches
- Heatmaps for attention patterns
- Scatter plots for correlation analysis
- Architecture diagrams for system design

**Implementation**:
```typescript
async function generateVisualizations(research: ResearchContext): Promise<Visualization[]> {
  const visualizations: Visualization[] = [];
  
  // Performance over iterations
  visualizations.push(await generateLineChart({
    title: 'Performance Improvement Over Iterations',
    xAxis: 'Iteration',
    yAxis: 'Effect Size',
    data: research.experiments.map(e => ({ x: e.iteration, y: e.effectSize })),
  }));
  
  // Approach comparison
  visualizations.push(await generateBarChart({
    title: 'Comparison of Approaches',
    xAxis: 'Approach',
    yAxis: 'Effect Size',
    data: research.champions.map(c => ({ x: c.approach, y: c.score })),
  }));
  
  return visualizations;
}
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

- Shared state operations (CRUD, concurrency)
- Agent implementations (analyst, experiment, critic, synthesizer)
- Team formation algorithm
- Stagnation detection
- Citation verification (4 layers)
- Report generation

### 8.2 Integration Tests

- End-to-end research pipeline with simple topic
- Team self-organization and reorganization
- Adversarial validation workflow
- Cross-team knowledge sharing
- Literature review pipeline
- Report generation with verified citations

### 8.3 Performance Tests

- Shared state throughput (1000+ ops/sec)
- Team formation latency (<5 seconds for 3 teams)
- Citation verification latency (<2 seconds per citation)
- Report generation time (<10 minutes for 6,000 words)

---

## 9. Success Criteria

- [ ] Teams self-organize around hypotheses
- [ ] Adversarial validation prevents wasted compute
- [ ] Cross-team knowledge sharing works
- [ ] Stagnation detection triggers reorganization
- [ ] Citation verification catches fabricated citations
- [ ] Reports meet word count target (5,000-6,500 words)
- [ ] LaTeX export compiles successfully
- [ ] Integration tests pass for full research pipeline
- [ ] Performance targets met (+8.33% improvement, 1.9× faster)

---

## 10. References

- AutoScientists: Decentralized coordination, self-organizing teams, +8.33% improvement
- Agentic Reasoning: Interleaved tool use during reasoning
- AutoResearchClaw: 23-stage pipeline, citation integrity, +18.3% robustness
- Anthropic multi-agent research: Orchestrator-worker, 90.2% improvement
- Open Deep Research: Multi-stage pipeline, plan-and-execute
- GPT Researcher: Planner-execution-publisher, multi-source aggregation
- Tongyi DeepResearch: Agentic training, IterResearch heavy mode

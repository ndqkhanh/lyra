# Brainstorm: Deep Research & AutoScientists (§4.15) — Self-Organizing Research Teams

**Workstream**: §4.15 Deep/Multi-hop/Auto/Scientist Research  
**Date**: 2026-05-31  
**Status**: Breakthrough ideas generated

---

## Sources Gathered

### Research Agent Frameworks
1. **AutoScientists** — Self-organizing decentralized teams, hypothesis generation, experiment design, shared success/failure log
2. **Open Deep Research** — LangChain configurable research agent
3. **Tongyi DeepResearch** — Alibaba web agent on par with OpenAI DR
4. **IterResearch** — Iterative long-horizon research via interaction scaling, report-as-memory
5. **GPT Researcher** — Autonomous cited-report research agent

### Knowledge & Reasoning
6. **Agentic Reasoning** — Tool-using agents with Mind-Map knowledge-graph memory for long reasoning chains
7. **SciencePedia** — Socratic agent + cross-model consensus, decompresses science into verifiable knowledge
8. **MemSearcher** — Search agent with compact question-relevant memory across turns
9. **Anthropic multi-agent research** — Orchestrator-worker, +90.2% vs single agent

### Benchmarks & Evaluation
10. **GAIA** — General AI assistant benchmark
11. **BLADE** — Benchmark for data-driven science, scores multifaceted analytical decisions
12. **Ask-before-Plan** — Proactive clarification from ambiguous instructions

---

## Novel Breakthrough Ideas (≥3 Required)

### Idea 1: **Adversarial Research Teams with Competing Hypotheses**

**Sources Combined**:
- AutoScientists self-organizing teams + shared success/failure log
- SciencePedia Socratic agent + cross-model consensus
- Agentic Reasoning Mind-Map knowledge graph
- Lyra's swarm (§4.13 adversarial coordination)

**Mechanism**:
Research teams **compete** to find the best answer:
1. **Hypothesis generation**: Multiple agents generate competing hypotheses
2. **Evidence gathering**: Each agent researches its hypothesis independently
3. **Adversarial critique**: Agents attack each other's hypotheses
4. **Socratic refinement**: Losing hypotheses refined or abandoned
5. **Convergence**: Teams converge on strongest hypothesis with most evidence
6. **Knowledge graph**: All findings stored in Mind-Map for future queries

**Example research flow**:
```
Query: "What causes long COVID?"

Hypothesis A (Agent 1): "Viral persistence in tissues"
Hypothesis B (Agent 2): "Autoimmune response"
Hypothesis C (Agent 3): "Microbiome disruption"

Evidence gathering (parallel):
- Agent 1: Finds 15 papers on viral persistence
- Agent 2: Finds 22 papers on autoimmunity
- Agent 3: Finds 8 papers on microbiome

Adversarial critique:
- Agent 2 attacks A: "Viral persistence doesn't explain neurological symptoms"
- Agent 1 attacks B: "Autoimmune markers not found in all patients"
- Agent 3 attacks both: "Both ignore gut-brain axis"

Socratic refinement:
- Agent 1 revises: "Viral persistence + immune dysregulation"
- Agent 2 revises: "Autoimmune response triggered by viral fragments"
- Agent 3 abandoned (weak evidence)

Convergence:
- Agents 1+2 merge: "Viral persistence triggers autoimmune response"
- Final report: Synthesized hypothesis with 37 citations
```

**Why It Beats Individual Sources**:
- AutoScientists alone: Self-organizing but no adversarial critique
- SciencePedia alone: Verification but not hypothesis generation
- **Fusion**: Competing hypotheses prevent confirmation bias, adversarial critique strengthens findings

**Expected Impact**: 2-3× better research quality, 80% reduction in false conclusions

**Rough Effort**: VERY HIGH (14-16 weeks) — hypothesis generation + adversarial critique + convergence logic

**Failure Modes**:
- Hypotheses too similar → no real competition
- Critique too aggressive → all hypotheses rejected
- Convergence fails → no final answer

---

### Idea 2: **Iterative Research with Adaptive Depth**

**Sources Combined**:
- IterResearch interaction scaling + report-as-memory
- MemSearcher compact question-relevant memory
- Lyra's context optimization (§4.3 auto-compaction)
- Anthropic orchestrator-worker (+90.2%)

**Mechanism**:
Research **adapts depth** based on query complexity:
1. **Initial assessment**: Classify query complexity (simple/medium/complex)
2. **Depth levels**:
   - **Level 1 (Simple)**: Single web search + summarize (1 iteration)
   - **Level 2 (Medium)**: Multi-source search + synthesis (2-3 iterations)
   - **Level 3 (Complex)**: Deep multi-hop research + expert consultation (5-10 iterations)
3. **Iteration loop** (IterResearch):
   - Gather evidence → Update report-as-memory → Identify gaps → Repeat
4. **Adaptive stopping**: Stop when diminishing returns (new info <10% per iteration)
5. **Context management**: Compact memory after each iteration (§4.3)

**Depth adaptation example**:
```
Query: "What is the capital of France?"
Assessment: SIMPLE
→ Level 1: Single search → "Paris" → Done (1 iteration)

Query: "Compare Paris and Rome architecture"
Assessment: MEDIUM
→ Level 2: 
  Iteration 1: Research Paris architecture
  Iteration 2: Research Rome architecture
  Iteration 3: Synthesize comparison
  → Done (3 iterations)

Query: "How did Renaissance architecture influence modern urban planning?"
Assessment: COMPLEX
→ Level 3:
  Iteration 1: Research Renaissance architecture
  Iteration 2: Research modern urban planning
  Iteration 3: Find connections (multi-hop)
  Iteration 4: Consult expert sources
  Iteration 5: Synthesize findings
  Iteration 6: Identify gaps (e.g., missing Asian influence)
  Iteration 7: Research Asian influence
  Iteration 8: Final synthesis
  → Done (8 iterations, diminishing returns)
```

**Why It Beats Individual Sources**:
- IterResearch alone: Fixed iteration count
- MemSearcher alone: Compact memory but no adaptive depth
- **Fusion**: Adapts to query, stops when done, manages context efficiently

**Expected Impact**: 60-70% cost reduction (no over-research), 2× faster simple queries

**Rough Effort**: MEDIUM-HIGH (8-10 weeks) — complexity classifier + adaptive stopping + context management

**Failure Modes**:
- Complexity classifier inaccurate → wrong depth level
- Stopping criteria too early → incomplete research
- Stopping criteria too late → wasted iterations

---

### Idea 3: **Research with Proactive Clarification**

**Sources Combined**:
- Ask-before-Plan proactive clarification
- GAIA general AI assistant benchmark
- Tongyi DeepResearch web agent
- Lyra's skills system (§4.4 research skills)

**Mechanism**:
Research agent **asks clarifying questions** before diving deep:
1. **Ambiguity detection**: Identify unclear aspects of query
2. **Question generation**: Generate 2-5 clarifying questions
3. **User interaction**: Ask user to clarify (or make reasonable assumptions)
4. **Refined research**: Research with clarified intent
5. **Iterative refinement**: Ask follow-ups if needed

**Clarification example**:
```
Query: "Research AI safety"

Ambiguity detection:
- "AI safety" is broad (technical safety? alignment? policy?)
- No time frame specified (current? future?)
- No depth specified (overview? deep dive?)

Questions generated:
1. "Are you interested in technical AI safety (e.g., robustness, adversarial attacks) or AI alignment (e.g., value learning, corrigibility)?"
2. "Should I focus on current AI systems or future AGI?"
3. "Do you want a high-level overview or a deep technical analysis?"

User answers:
1. "Technical safety for current systems"
2. "Current AI systems"
3. "Deep technical analysis"

Refined research:
→ Focus: Technical safety (robustness, adversarial attacks, verification)
→ Scope: Current LLMs and vision models
→ Depth: Deep dive with papers and benchmarks
```

**Why It Beats Individual Sources**:
- Ask-before-Plan alone: Clarification but not research-focused
- Tongyi DeepResearch alone: Research but no clarification
- **Fusion**: Prevents wasted research on wrong interpretation

**Expected Impact**: 90% reduction in misunderstood queries, 50% faster to correct answer

**Rough Effort**: MEDIUM (6-8 weeks) — ambiguity detection + question generation + user interaction

**Failure Modes**:
- Ambiguity detection too sensitive → too many questions (annoying)
- Questions too vague → don't help clarify
- User doesn't answer → research proceeds with assumptions

---

### Idea 4: **Research with Automatic Expert Consultation**

**Sources Combined**:
- SciencePedia cross-model consensus
- BLADE benchmark for data-driven science
- AutoScientists expert roles
- Lyra's model router (§4.5)

**Mechanism**:
Research agent **automatically consults experts** when needed:
1. **Expert identification**: Detect when query needs domain expertise
2. **Expert routing**: Route to specialized models/agents
   - Medical queries → medical-tuned model
   - Legal queries → legal-tuned model
   - Code queries → code-specialized model
3. **Cross-expert consensus**: Multiple experts vote on answer
4. **Confidence scoring**: Aggregate expert confidence
5. **Escalation**: If experts disagree, escalate to human

**Expert consultation example**:
```
Query: "Is this drug interaction dangerous?"

Expert identification: MEDICAL domain detected

Expert routing:
- Expert 1 (Medical LLM): "Yes, dangerous interaction"
- Expert 2 (PubMed search): "15 papers report adverse events"
- Expert 3 (Drug database): "FDA warning issued"

Cross-expert consensus: ALL AGREE → High confidence

Final answer: "Yes, dangerous. FDA warning + 15 adverse event reports."
```

**Why It Beats Individual Sources**:
- SciencePedia alone: Consensus but not domain-specific
- BLADE alone: Benchmark but not expert routing
- **Fusion**: Automatic expert consultation, cross-expert consensus

**Expected Impact**: 95%+ accuracy on domain-specific queries, 80% reduction in hallucinations

**Rough Effort**: HIGH (10-12 weeks) — expert identification + routing + consensus logic

**Failure Modes**:
- Expert identification inaccurate → routes to wrong expert
- Experts disagree → no consensus
- Expert models not available → falls back to general model

---

## Parked Ideas (For Future Runs)

1. **Research caching**: Cache research results for similar queries
2. **Research templates**: Pre-defined research workflows for common query types
3. **Research metrics**: Track research quality, cost, time per query
4. **Research replay**: Record and replay research for debugging
5. **Research collaboration**: Multiple users contribute to shared research

---

## Promoted to Plan (B) Breakthrough Tier

**Selected**: Idea 1 (Adversarial Research Teams) + Idea 2 (Iterative Research with Adaptive Depth)

**Rationale**:
- Idea 1: Highest quality improvement (2-3×), prevents confirmation bias
- Idea 2: Highest cost reduction (60-70%), adapts to query complexity
- Idea 3: Good but overlaps with existing clarification patterns
- Idea 4: Interesting but requires domain-specific models (not always available)

---

**END OF BRAINSTORM**

# Brainstorm — Deep Research (§4.15)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Source Techniques Gathered

| Technique | Source | Core Idea | Key Numbers |
|-----------|--------|-----------|-------------|
| Argus Searcher-Navigator | (2605.16217) | Shared evidence graph, Searcher→Navigator→Synthesizer | BrowseComp 86.2, 1,200:1 compression |
| NanoResearch Tri-Level | (2605.10813) | Skill Bank + Memory Module + SDPO planner co-evolution | — |
| AutoScientists | Harvard (2605.28655) | Decentralized self-organizing teams, shared success/failure log | — |
| VirSci | Su et al. (2410.09403) | Virtual Scientists: generate→evaluate→refine ideas | Beats SOTA on novel ideation |
| Agentic Reasoning | Wu et al. (2502.04644) | Tool-using agents + Mind-Map KG memory | — |
| IterResearch | Alibaba (2511.07327) | MDP workspace reconstruction, report-as-memory | — |
| Open Deep Research | LangChain | Configurable open deep-research agent | — |
| Tongyi DeepResearch | Alibaba (2510.24701) | On par with OpenAI Deep Research | — |
| Claw AI Lab | (2605.22662) | Lab-native autonomous research, anti-fabrication harness | — |
| Anthropic Multi-Agent Research | Anthropic | Orchestrator-worker, +90.2% vs single agent | — |

---

## Breakthrough Idea #1: Argus + AutoScientists Hybrid — Evidence-Graph Self-Organizing Research Teams

**Sources Fused:** Argus evidence graph + AutoScientists decentralized teams + VirSci ideation + Anthropic orchestrator-worker

**Core Mechanism:**
1. **Orchestrator** receives research question, decomposes into sub-questions
2. **Searcher agents** fan out across web/academic sources, deposit findings into a SHARED EVIDENCE GRAPH (Argus-style, 1,200:1 compression)
3. **Navigator agents** traverse the evidence graph, identify gaps, spawn new searches
4. **Synthesizer agents** draft claims from graph evidence
5. **Adversarial verifiers** (anonymized, bias-corrected per §4.25) cross-check every claim against the evidence graph
6. **Self-organizing teams** (AutoScientists pattern): agents cluster around the most promising leads, share a success/failure log to avoid redundant work
7. **Final report** with cited claims, confidence scores, and the evidence graph as an interactive artifact

**Why It Beats Individual Sources:** Argus has no self-organization. AutoScientists has no evidence graph compression. Anthropic's system has no adversarial verification.

**Impact:** 5 | **Effort:** 5 | **Risk:** Medium

---

## Breakthrough Idea #2: NanoResearch Tri-Level Co-Evolution for Persistent Research Improvement

**Sources Fused:** NanoResearch tri-level + IterResearch MDP workspace + Claw AI Lab anti-fabrication

**Core Mechanism:**
- **Level 1 — Skill Bank:** Research skills (how to search PubMed, how to evaluate a paper, how to synthesize findings) evolve via GEPA-style optimization. Skills improve with each research run.
- **Level 2 — Memory Module:** Research findings persist across sessions in the Zettelkasten graph memory. New research queries find and build on prior findings. Contradictions are flagged.
- **Level 3 — SDPO Planner:** The research plan itself is optimized via RL — which sub-questions to pursue, in what order, with what depth — based on past research outcomes.
- **IterResearch Workspace:** Research state is reconstructed from memory after context resets, avoiding context suffocation on long research runs.
- **Anti-Fabrication Harness:** Every claim must be traceable to a specific source in the evidence graph. Fabrication detection: claim has no evidence path → flag and remove.

**Why It Beats Baseline:** Lyra has no deep research capability at all. This creates a self-improving research engine.
**Impact:** 5 | **Effort:** 5 | **Risk:** High

---

## Breakthrough Idea #3: Mind-Map Knowledge Graph for Long-Horizon Reasoning

**Sources Fused:** Agentic Reasoning Mind-Map + LP-RAG link prediction + SciencePedia inverse knowledge search

**Core Mechanism:**
- During research, build a structured Mind-Map knowledge graph (hierarchical nodes, typed edges, evidence links)
- Mind-Map serves as external working memory for long reasoning chains (prevents context suffocation)
- LP-RAG link prediction discovers latent connections between Mind-Map nodes
- SciencePedia-style inverse knowledge search: decompress findings into a verifiable Long-CoT knowledge base
- Cross-model consensus: multiple models verify each node in the Mind-Map
- Final output: the Mind-Map IS the research artifact (interactive, explorable, verifiable)

**Why It Beats Baseline:** Current Lyra has no long-horizon reasoning support.
**Impact:** 4 | **Effort:** 4 | **Risk:** Medium

---

## Expert Check (Research Personas)

**Senior AI Researcher:** "Idea #1 (evidence graph + self-organizing teams) is the most practical. Argus's 1,200:1 compression makes the evidence graph feasible at scale. The AutoScientists self-organization avoids the 'every agent searches the same thing' problem."

**Senior SRE:** "Long research runs (hours/days) need checkpointing and resumability. The IterResearch MDP workspace reconstruction is critical — without it, a context reset loses all research state."

**Adversarial Skeptic:** "Anti-fabrication is the most important feature and the hardest to get right. The Claw AI Lab paper shows fabrication is the #1 failure mode for research agents. If the evidence graph can't trace every claim to a source, the research is worthless."

**Resolution:** Idea #1 (Argus + AutoScientists) is the (B) breakthrough. The anti-fabrication harness is mandatory — claims without evidence paths in the graph are auto-flagged. Start with the Anthropic orchestrator-worker as the (A) parity baseline, then add evidence graph + self-organization.

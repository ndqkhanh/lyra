# LYRA ULTRA PLAN 13: BREAKTHROUGH SYNTHESIS — From Deep Research to AGI

**Version:** 1.0.0
**Status:** Active
**Created:** 2026-05-25
**Research Scope:** 50+ links, 9 papers, 30+ GitHub repos, 33 Claude Code docs, 30+ web searches

---

## Executive Summary

After deep research across 50+ sources, Lyra is well-positioned but has 6 critical gaps to AGI. This plan identifies the highest-leverage improvements ordered by impact-to-effort ratio.

**Key finding:** The harness — not the model — is the decisive factor in agent capability. Claude Code's dominance ($2.5B ARR, 140K stars) comes from its orchestration layer: Dream memory consolidation, permission architecture, sub-agent system, and hook lifecycle. Lyra must close 6 gaps to achieve AGI-grade capability.

---

## Research Absorption Matrix

### Papers Absorbed (9 new)

| # | Paper | Key Innovation | Relevance | Action |
|---|-------|---------------|-----------|--------|
| 1 | AutoResearchClaw (2605.20025) | Pivot/Refine failure recovery, cross-run evolution, 7-mode HITL | 9/10 | Implement error DB + Pivot/Refine loop |
| 2 | RecursiveMAS (2604.25917) | Latent-space agent communication, 75.6% token reduction | 8/10 | Add RecursiveLink for inter-agent latent comms |
| 3 | Knowing-Doing Gap (2605.14038) | Tool-use recognition vs. execution gap, probe-based monitoring | 8/10 | Add tool-call verification step |
| 4 | Meta-Harness (2603.28052) | Outer-loop harness optimization, +7.7pts with 4x fewer tokens | 10/10 | Build meta-optimization loop for Lyra's harness |
| 5 | Code as Harness (2605.18747) | Three-layer framework: interface, mechanisms, scaling | 10/10 | Adopt as architectural reference |
| 6 | AEvo (2605.13821) | Meta-agent edits procedures, 26% relative improvement | 9/10 | Meta-agent for procedure evolution |
| 7 | ARIS (2605.03042) | Cross-model adversarial review, 3-stage evidence verification | 9/10 | Default adversarial verification |
| 8 | SciencePedia (2510.26854) | Inverse knowledge search, cross-model consensus | 7/10 | Adopt for research pipeline |
| 9 | SR2AM (2605.22138) | Self-regulated simulative planning, 8B matches 1T systems | 10/10 | System I/II/III reasoning architecture |

### Repositories Studied (25+ analyzed)

| Repo | Stars | Key Takeaway for Lyra |
|------|-------|----------------------|
| Hermes-agent | 167K | GEPA self-evolution, 40+ tools, omnichannel gateway, FTS5 memory |
| Cline | 58K | Model-agnostic, Plan/Act toggle, MCP marketplace |
| Aider | 42K | Architect/Editor model split, tree-sitter RepoMap |
| OpenHands | 73K | Docker runtime, ToM module, weekly releases |
| CrewAI | 52K | Role-based agent teams, 1.8M monthly downloads |
| AutoGPT | 184K | Agent marketplace, low-code builder |
| LangGraph | 28K | Stateful DAG orchestration, checkpointing |
| DCI-Agent-Lite | — | Zero-index retrieval, tiered context management |
| claude-mem | — | Progressive disclosure, memory as files |
| MemPalace | — | Verbatim-first retrieval, temporal anchoring |
| Acontext | 3.4K | Memory as editable Markdown, skill=memory equivalence |
| continuous-claude | — | Relay-race autonomy, probabilistic progress, markdown memory |
| Claude Code Best Practice | — | Command→Agent→Skill orchestration, context management strategies |

### MCP & Tool Ecosystem

- **10,000+ MCP servers**, 97M+ monthly SDK downloads, 232% growth
- **37 Claude Code tools** documented — Agent, Bash, LSP, Cron, Notify, Team
- **Tool Search** enables 10K-tool catalogs with deferred schema loading (85% context savings)
- **Enterprise MCP gateways** from Uber and Amazon

### Safety Architecture (Critical)

| Layer | Mechanism | Block Rate |
|-------|-----------|------------|
| Cognitive-Executive Separation | Parallax — structural separation of reasoning from action | 98.9% (100% at max) |
| Symbolic Rule Enforcement | 74% of policies enforceable via deterministic rules | No utility sacrifice |
| Multi-Agent Validation | Executor→Validator→Critic pipeline | Cross-check system |
| Intent Monitoring | Action sequence analysis for deviation | Behavioral |
| TEE Verifiability | Cryptographic proof of guardrail execution | Enterprise |

---

## The 6 Critical Gaps to AGI

### Gap 1: No Self-Evolving Harness → **Build GEPA + AEvo Meta-Optimization Loop**

Lyra's current self-evolution (GEPA optimizer) optimizes prompts but not the harness code itself. Meta-Harness shows +7.7pts improvement with 4x fewer tokens. AEvo shows 26% relative improvement. Hyperagents improved SWE-bench from 20% to 50% through self-code-rewriting.

**Action:** Build a meta-optimization loop where a meta-agent observes Lyra's execution traces, identifies harness bottlenecks, and proposes code edits to the orchestration layer — verified by adversarial review before deployment.

### Gap 2: Text-Only Agent Communication → **Implement RecursiveLink Latent Comms**

Lyra's agents communicate via natural language text, consuming 35-75% more tokens than necessary. RecursiveMAS's RecursiveLink module enables latent-space communication with 75.6% token reduction and 1.2-2.4x speedup.

**Action:** Implement a lightweight RecursiveLink module for inter-agent latent state transfer, starting with the most communication-heavy agent pairs (Orchestrator↔Specialists).

### Gap 3: No Architectural Safety Separation → **Implement Parallax-Style Cognitive-Executive Split**

Lyra's safety relies on prompt-level guardrails. Research proves these provide zero protection when reasoning is compromised. Parallax's cognitive-executive separation achieves 98.9% block rate through architectural separation.

**Action:** Restructure Lyra's agent loop so reasoning (planning, analysis) and execution (tool calls, file writes) run in structurally separated contexts with independent verification.

### Gap 4: Flat Memory Architecture → **Deploy Dream-Style 4-Phase Consolidation**

Lyra's 8-level memory hierarchy lacks the consolidation intelligence of Claude Code's "Dream" system: Orient → Gather → Consolidate → Prune. Mem0 achieves 91.6 on LoCoMo, 93.4 on LongMemEval through ADD-only extraction.

**Action:** Implement 4-phase background memory consolidation with ADD-only extraction, entity linking, multi-signal retrieval, and Ebbinghaus adaptive forgetting.

### Gap 5: No Self-Regulated Planning → **Implement SR2AM 3-System Reasoning**

Lyra plans via CoT but doesn't self-regulate planning depth. SR2AM shows an 8B model matching 1T systems using 25.8-95.3% fewer reasoning tokens through System I (reactive), System II (world-model simulation), and System III (learned configurator).

**Action:** Add a System III planning configurator that learns when and how deeply to plan per task type, supported by reasoning graphs for cross-session learning.

### Gap 6: Static Tool Loading → **Implement Progressive Tool Discovery**

Lyra loads all tool definitions into context. Claude Code's Tool Search reduces context usage by ~85% by loading only tool names at startup and fetching schemas on demand. Wareel proved removing 80% of tools improved results.

**Action:** Implement deferred tool schema loading with semantic tool search, tool categorization, and auto-pruning based on task relevance.

---

## Implementation Roadmap

### Phase 13.1: Foundation (Weeks 1-2) — IMMEDIATE

**13.1.1: Pivot/Refine Failure Recovery Loop**
- Error database with structured failure patterns
- Pivot/Refine executor: on failure, analyze → generate alternative → retry
- Cross-run evolution: persist errors as future safeguards
- Integration with existing AgentLoop error handling
- **Files:** `lyra-core/src/lyra_core/loop/pivot_refine.py`, `lyra-core/src/lyra_core/loop/error_db.py`
- **Inspiration:** [AutoResearchClaw](https://arxiv.org/abs/2605.20025)

**13.1.2: Tool-Call Verification (Knowing-Doing Gap)**
- Post-hoc auditing: compare tool necessity vs. actual usage
- Hidden-state confidence probe before tool execution
- Tool-call confidence threshold with fallback to direct reasoning
- **Files:** `lyra-core/src/lyra_core/verifier/tool_audit.py`
- **Inspiration:** [Knowing-Doing Gap](https://arxiv.org/abs/2605.14038)

**13.1.3: Cross-Model Adversarial Verification**
- Default pairing: executor (Sonnet) + reviewer (different model family)
- Three-stage evidence verification (integrity → result-to-claim → claim auditing)
- Reviewer approval gate for self-evolution changes
- **Files:** `lyra-core/src/lyra_core/verifier/adversarial.py`
- **Inspiration:** [ARIS](https://arxiv.org/abs/2605.03042)

**13.1.4: Dream-Style Memory Consolidation (Phase 1)**
- ADD-only extraction for new memories
- Background deduplication of stored knowledge
- Entity linking across memory layers
- **Files:** `lyra-memory/src/lyra_memory/dream_consolidator.py`
- **Inspiration:** Claude Code Dream system, [Mem0](https://github.com/mem0ai/mem0), [TencentDB-Agent-Memory](https://github.com/Tencent/TencentDB-Agent-Memory)

**13.1.5: Progressive Tool Discovery**
- Deferred tool schema loading
- Semantic tool search (embed task → find relevant tools)
- Tool categorization with auto-pruning
- **Files:** `lyra-core/src/lyra_core/tools/tool_search.py`
- **Inspiration:** Claude Code Tool Search, [Wareel tool pruning](https://arxiv.org/abs/2603.28052)

### Phase 13.2: Intelligence Core (Weeks 3-4)

**13.2.1: RecursiveLink Latent Communication**
- Lightweight module for inter-agent latent state transfer
- Hybrid text+latent communication layer
- Inner-outer loop for multi-agent credit assignment
- Target: 35-50% token reduction for agent communication
- **Files:** `lyra-agent-swarm/src/lyra_agent_swarm/recursive_link.py`
- **Inspiration:** [RecursiveMAS](https://arxiv.org/abs/2604.25917)

**13.2.2: SR2AM Self-Regulated Planning**
- System I (reactive, fast path for simple tasks)
- System II (world-model simulation via CoT for medium)
- System III (learned configurator that decides depth)
- RL-trained planning horizon with minimal frequency growth
- **Files:** `lyra-reasoning/src/lyra_reasoning/sr2am/`
- **Inspiration:** [SR2AM](https://arxiv.org/abs/2605.22138)

**13.2.3: Reasoning Graphs**
- Persist CoT as structured graph edges per evidence item
- Evidence-centric feedback across runs
- Cross-session reasoning pattern learning
- **Files:** `lyra-reasoning/src/lyra_reasoning/reasoning_graph.py`
- **Inspiration:** Reasoning Graphs (ACL 2026)

**13.2.4: DCI Zero-Index Retrieval Mode**
- Direct corpus interaction via grep/rg without pre-built indexes
- Tiered context management (truncation → compaction → summarization)
- 5 configurable runtime levels for context budgets
- **Files:** `lyra-research/src/lyra_research/zero_index.py`
- **Inspiration:** [DCI-Agent-Lite](https://github.com/DCI-Agent/DCI-Agent-Lite)

### Phase 13.3: Safety Architecture (Weeks 5-6)

**13.3.1: Cognitive-Executive Separation**
- Structural separation of reasoning and tool execution
- Independent verification agent reviews all execution plans
- Reasoning context cannot directly invoke tools
- Target: 98%+ block rate on adversarial attacks
- **Files:** `lyra-core/src/lyra_core/safety/parallax.py`
- **Inspiration:** [Parallax](https://arxiv.org/abs/2604.12986)

**13.3.2: Multi-Agent Validation Pipeline**
- Executor → Validator → Critic pipeline for all critical operations
- Validator from different model family than executor
- Critic reviews validator's reasoning, not just output
- **Files:** `lyra-core/src/lyra_core/safety/validate_pipeline.py`
- **Inspiration:** AWS Stop Hallucinations Workshop

**13.3.3: Intent-Based Behavioral Security**
- Continuous monitoring of action sequences for intent deviation
- Temporal pattern analysis (sequence of tool calls over time)
- Anomaly detection on agent behavior patterns
- **Files:** `lyra-core/src/lyra_core/safety/intent_monitor.py`
- **Inspiration:** Radware Intent-Based Security

**13.3.4: PRISM Prompt Drift Detection**
- Daily automated detection of LLM prompt degradation
- Auto-repair via GEPA re-optimization
- Target: 99% prompt reliability, <30 min repair time
- **Files:** `lyra-core/src/lyra_core/evolve/drift_detector.py`
- **Inspiration:** [PRISM](https://arxiv.org/abs/2605.14454)

### Phase 13.4: Harness Evolution (Weeks 7-8)

**13.4.1: Meta-Harness Optimization Loop**
- Outer-loop system that searches over Lyra's own harness code
- Agentic proposer with filesystem access to all prior candidates
- Cross-model generalization testing
- Target: +5-8pts on coding benchmarks
- **Files:** `lyra-meta-evolution/src/lyra_meta_evolution/harness_opt.py`
- **Inspiration:** [Meta-Harness](https://arxiv.org/abs/2603.28052)

**13.4.2: AEvo Meta-Editing**
- Meta-agent observes accumulated state and edits procedures
- Harnessed meta-editing: stable interface for evidence
- Prevents drift in long-horizon evolution
- **Files:** `lyra-meta-evolution/src/lyra_meta_evolution/aevo_meta.py`
- **Inspiration:** [AEvo](https://arxiv.org/abs/2605.13821)

**13.4.3: GEPA v2 — Multi-Agent Prompt Evolution**
- Parallel prompt learning across fleet (Combee-inspired, 17x speedup)
- Pareto frontier selection of complementary improvements
- Joint optimization of prompts + harness code
- **Files:** `lyra-evolution/src/lyra_evolution/gepa_v2.py`
- **Inspiration:** [GEPA (ICLR 2026)](https://arxiv.org/abs/2310.03714), [Combee](https://arxiv.org/abs/2604.15771)

### Phase 13.5: Scaling & Enterprise (Weeks 9-10)

**13.5.1: MCP Enterprise Gateway**
- Stateless HTTP transport (SEP-1442 compliant)
- OAuth 2.1 authentication with auto-discovery
- Allow/deny lists with managed policy enforcement
- Per-server tool execution timeout
- **Files:** `lyra-mcp/src/lyra_mcp/gateway.py`
- **Inspiration:** Uber/Amazon MCP gateways, Claude Code MCP

**13.5.2: Agent Teams with Shared Task Lists**
- File-locked shared task list for race prevention
- Peer-to-peer messaging via SendMessage
- Task dependency tracking (blocked/unblocked)
- Quality gates via lifecycle hooks
- **Files:** `lyra-agent-swarm/src/lyra_agent_swarm/agent_teams.py`
- **Inspiration:** Claude Code Agent Teams

**13.5.3: Checkpoint & Rewind System**
- Automatic file state snapshots before each edit
- Rewind menu: restore code, conversation, or both
- Checkpoints persist across sessions (30-day retention)
- Separate from git, complements version control
- **Files:** `lyra-core/src/lyra_core/checkpoint/`
- **Inspiration:** Claude Code Checkpointing

**13.5.4: Enterprise Settings Hierarchy**
- 4-tier scope: managed > CLI > local > project > user
- Managed settings via file-based policy + policy helper
- Deny-first permission evaluation
- Drop-in directory for independent policy fragments
- **Files:** `lyra-core/src/lyra_core/config/settings_hierarchy.py`
- **Inspiration:** Claude Code Settings System

---

## Skills Ecosystem Enhancement (Parallel Track)

### 15 New Domain Skills to Create

**Engineering:**
1. **system-design** — Architecture decision records, trade-off analysis, C4 diagrams
2. **performance-engineering** — Profiling, bottleneck identification, optimization patterns
3. **database-engineering** — Schema design, migration strategies, query optimization
4. **api-design** — REST/GraphQL/gRPC patterns, versioning, rate limiting

**SRE/DevOps:**
5. **incident-response** — Runbook execution, root cause analysis, postmortem generation
6. **infrastructure-as-code** — Terraform/Pulumi patterns, drift detection, cost optimization
7. **observability** — Dashboard design, alert configuration, SLO definition
8. **chaos-engineering** — Experiment design, blast radius control, steady-state verification

**AI/ML Research:**
9. **paper-analysis** — Structured paper extraction, methodology evaluation, replication planning
10. **experiment-design** — Hypothesis formulation, A/B test design, statistical analysis
11. **model-evaluation** — Benchmark design, ablation studies, fairness auditing

**Product & Business:**
12. **prd-writing** — Product requirement documents, user story mapping, acceptance criteria
13. **competitive-analysis** — Feature matrices, SWOT analysis, differentiation strategy
14. **stakeholder-communication** — Executive summaries, technical briefings, roadmap presentations

**Creative:**
15. **brainstorm-facilitator** — Divergent/convergent thinking, ideation frameworks, innovation prompts

### Skills Auto-Compaction Enhancement
- Per-section reference tracking (already built in `compaction.py`)
- 90-day stale archival (already built)
- Tag similarity merge detection (already built)
- Add: skill effectiveness scoring from execution traces
- Add: automatic skill retirement on sustained underperformance
- Add: skill versioning with rollback capability

---

## UI/UX Breakthrough (Parallel Track)

### Color Theme System Expansion — 25 Themes in 5 Families

Already planned in Plan 6. Enhancement from research:

**New themes discovered from research:**
- **Rose Pine** — Warm rosy dark with dawn variants
- **Kanagawa** — Japanese ink wash inspired, serene
- **Ayu** — Three variants (Dark, Mirage, Light)
- **Night Owl** — Accessible dark with careful contrast ratios
- **Solarized** — Ethan Schoonover's classic, scientifically balanced

**Implementation reference:** Claude Code's theme system uses 30+ color tokens in a JSON file with live reload via file watching. Lyra should adopt the same architecture.

### Keybinding System — 20 Contexts, 80+ Actions

Based on Claude Code's complete keybinding reference:

**16 contexts to implement:**
Global, Chat, Autocomplete, Confirmation, Transcript, History, HistorySearch, Task, ThemePicker, Help, Tabs, Attachments, Footer, MessageSelector, DiffDialog, ModelPicker, Select, Plugin, Settings, Doctor, Scroll, Voice

**Custom keybinding config:** `~/.lyra/keybindings.json` with context-keyed action maps.

### Voice & Audio System Enhancement

From research:
- **CESP v1.0** (already built in `cesp_engine.py`)
- **6-layer pack selection hierarchy** (already built)
- **Audio suppression** with silent hours, meeting detection, spam throttling (already built)
- **Voice dictation** — Claude Code's approach: hold-to-talk (push-to-talk on Space), tap-to-record, 21 languages, coding-vocabulary-tuned transcription
- **Sound packs** — Warcraft III Peon, Sci-Fi, Minimal, Nature, Custom
- **Hook-based triggers** — SessionStart, UserPromptSubmit, Stop, PreCompact

**New from research:**
- **Funny voice on session start** — "Ready to work!" (Peon-style), "Systems online" (robot), etc.
- **Waveform visualization** in footer during recording
- **Auto-submit** on release in tap mode (>3 words)
- **Language auto-detection** from settings

### Status Line Framework
- Shell script receiving JSON session data on stdin
- Context window usage bar, cost tracking, git status
- Multi-line support (git info line + context bar line)
- Interactive actions via ANSI OSC sequences

---

## Documentation Update Plan

### README.md Enhancement
- Update to reflect 13 ultra plans
- Add new research paper absorption matrix entries
- Update innovation table with new techniques
- Add visual architecture diagrams for new components

### ARCHITECTURE.md Enhancement  
- Add 6-layer safety architecture diagram
- Add Dream-style memory consolidation flow
- Add self-evolving harness pipeline diagram
- Update design decisions table with new rationale

### SOUL.md Enhancement
- Add new research inspirations
- Update innovation lineage with new papers
- Add operating principles for self-evolution safety

### New Docs to Create
- `docs/research/breakthrough-synthesis.md` — This plan's key findings
- `docs/architecture/safety-architecture.md` — Parallax-style cognitive-executive separation
- `docs/architecture/harness-evolution.md` — Meta-optimization loop design
- `docs/architecture/memory-consolidation.md` — Dream-style 4-phase consolidation

---

## Benchmark Strategy

### Target: Rank #1 Across All Categories

| Benchmark | Current SOTA | Lyra Target | Key Lever |
|-----------|-------------|-------------|-----------|
| SWE-bench Pro | 57.0% (GPT-5.3-Codex) | 60%+ | Meta-harness optimization |
| GAIA Level 3 | ~68% | 75%+ | SR2AM planning + Pivot/Refine |
| TerminalBench 2 | 76.4% (DSPy) | 80%+ | DSPy auto-optimization |
| LoCoMo | 91.6 (Mem0) | 93%+ | Dream consolidation |
| LongMemEval | 93.4 (Mem0) | 95%+ | Multi-graph memory |
| WebArena | 42.6% (vs human 78.2%) | 55%+ | Zero-index retrieval + recursive planning |

### Evaluation Integrity

UC Berkeley proved ALL major benchmarks can be gamed. Lyra will:
1. Build exploit-resistant evaluation suite
2. Use cross-model adversarial verification for results
3. Implement cryptographic proof-of-evaluation
4. Monthly red-team testing for benchmark exploits

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Self-code-rewriting degrades performance | High | Adversarial reviewer approval gate, rollback capability |
| Latent-space communication loses semantic fidelity | Medium | Hybrid text+latent mode, keep text fallback |
| Cognitive-executive separation adds latency | Medium | Fast-path for simple operations, System I routing |
| Meta-harness optimization overfits to benchmarks | High | Cross-model generalization testing, diverse eval suite |
| Memory consolidation loses critical context | Medium | Verbatim-first retrieval, user-inspectable memory files |

---

## Success Metrics

- [ ] 60%+ on SWE-bench Pro (from current baseline)
- [ ] 35-50% reduction in inter-agent token usage via RecursiveLink
- [ ] 98%+ adversarial attack block rate via Parallax separation
- [ ] 93%+ on LoCoMo via Dream consolidation
- [ ] 25%+ improvement in harness efficiency via meta-optimization
- [ ] 85%+ context savings via progressive tool discovery
- [ ] 99% prompt reliability via PRISM drift detection
- [ ] 25 professional color themes with live preview
- [ ] 15 new domain skills with auto-evaluation
- [ ] 80+ rebindable keybindings across 16 contexts

---

*This plan synthesizes research from 50+ sources across papers, repositories, official documentation, and community best practices. Every recommendation traces to its source with an evidence-based rationale.*

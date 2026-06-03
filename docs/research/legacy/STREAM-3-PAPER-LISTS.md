# Stream 3: Paper Lists & Awesome Lists Research

> **Date:** 2026-05-30
> **Scope:** Comprehensive analysis of 5 curated paper/awesome lists for breakthrough techniques applicable to Lyra (MIT-licensed terminal-based multi-agent AI system).

---

## Executive Summary

This research analyzed **5 repositories** totaling **~2,500+ papers, tools, and servers** cataloged across:
- AI agent papers (masamasa59/ai-agent-papers)
- Agent memory papers (Shichun-Liu/Agent-Memory-Paper-List)
- Harness engineering (ai-boost/awesome-harness-engineering)
- MCP servers (punkpeye/awesome-mcp-servers)
- Context engineering (yzfly/awesome-context-engineering)

The analysis identified **30 highest-impact entries** for Lyra across agent architecture, memory systems, orchestration, context optimization, tool use, multi-agent coordination, and benchmark evaluation. Key findings include: (1) self-evolving agent harnesses are the most transformative trend; (2) hierarchical memory architectures consistently outperform flat vector stores; (3) context engineering is the single highest-leverage harness primitive; (4) MCP-based tool ecosystems provide immediate capability boosts with low integration cost.

---

## 1. Repository Summaries

### 1.1 ai-agent-papers (masamasa59)
- **Total entries:** ~600+ papers
- **URL:** https://github.com/masamasa59/ai-agent-papers
- **Update frequency:** Weekly arXiv searches
- **Organization:** Capability papers (14 categories) + Agent frameworks (3 categories) + Application papers (14 categories) + Lectures

**Topical breakdown:**
| Category | Papers | Relevance to Lyra |
|---|---|---|
| Memory | ~95 | CRITICAL - core Lyra need |
| Self-Evolution | ~115 | HIGH - agent improvement loop |
| Tool Use & Skills | ~100 | CRITICAL - MCP/plugin integration |
| Planning | ~42 | HIGH - multi-step task orchestration |
| Reasoning | ~80 | HIGH - agent decision quality |
| Single-Agent frameworks | ~80 | MEDIUM - architectural reference |
| Multi-Agent frameworks | ~42 | CRITICAL - fleet coordination |
| Self-Correction | ~50 | MEDIUM - verification loops |
| Agent Evaluation | ~20 | MEDIUM - quality measurement |
| Other (safety, search, apps) | ~100 | LOW-MEDIUM |

### 1.2 Agent-Memory-Paper-List (Shichun-Liu)
- **Total entries:** ~160 papers
- **URL:** https://github.com/Shichun-Liu/Agent-Memory-Paper-List
- **Paper:** "Memory in the Age of AI Agents: A Survey" (arXiv:2512.13564, 1K+ stars)
- **Organization:** 3-lens taxonomy: Forms (Token/Parametric/Latent) x Functions (Factual/Experiential/Working) x Dynamics (Formation/Evolution/Retrieval)

**Topical breakdown:**
| Memory Type | Papers | Lyra Relevance |
|---|---|---|
| Factual Memory (Token-level) | ~65 | HIGH - persistent knowledge across sessions |
| Experiential Memory (Token-level) | ~40 | CRITICAL - learning from agent trajectories |
| Working Memory (Token-level) | ~20 | CRITICAL - context window management |
| Factual Memory (Parametric) | ~15 | LOW - not applicable to Lyra |
| Experiential Memory (Parametric) | ~6 | LOW |
| Working Memory (Parametric/Latent) | ~15 | MEDIUM - KV-cache optimization |

### 1.3 awesome-harness-engineering (ai-boost)
- **Total entries:** ~280+ resources (articles, papers, tools, templates)
- **URL:** https://github.com/ai-boost/awesome-harness-engineering
- **License:** CC0
- **Organization:** Foundations + 12 Design Primitives + Reference Implementations + Security + Evals + Templates

**Topical breakdown:**
| Section | Entries | Lyra Relevance |
|---|---|---|
| Agent Loop | ~15 | CRITICAL - core architecture |
| Context Delivery & Compaction | ~25 | CRITICAL - token efficiency |
| Memory & State | ~20 | CRITICAL - persistence layer |
| Task Runners & Orchestration | ~30 | CRITICAL - fleet management |
| Tool Design | ~15 | HIGH - MCP/server interfaces |
| Skills & MCP | ~25 | HIGH - plugin system |
| Permissions & Authorization | ~15 | HIGH - security model |
| Verification & CI Integration | ~20 | MEDIUM - quality gates |
| Observability & Tracing | ~12 | HIGH - debugging/monitoring |
| Planning & Task Decomposition | ~12 | HIGH - task breakdown |
| Foundations | ~20 | MEDIUM - design philosophy |
| Human-in-the-Loop | ~12 | MEDIUM |
| Debugging & Dev Experience | ~13 | HIGH |
| Security, Sandbox & Permissions | ~25 | HIGH |
| Generators & Meta-Harnesses | ~12 | MEDIUM |
| Demo Harnesses | ~20 | MEDIUM |

### 1.4 awesome-mcp-servers (punkpeye)
- **Total entries:** ~1,500+ MCP servers
- **URL:** https://github.com/punkpeye/awesome-mcp-servers
- **Organization:** 60+ categories

**Topical breakdown (relevant categories only):**
| Category | Servers | Lyra Relevance |
|---|---|---|
| Knowledge & Memory | ~30 | CRITICAL |
| Code Execution | ~10 | HIGH |
| Developer Tools | ~40 | HIGH |
| Search & Data Extraction | ~25 | HIGH |
| Databases | ~20 | MEDIUM |
| Security | ~15 | HIGH |
| Aggregators (meta-MCP) | ~50 | MEDIUM |
| File Systems | ~15 | HIGH |
| Monitoring | ~15 | MEDIUM |
| Browser Automation | ~20 | LOW |
| Coding Agents | ~15 | HIGH |
| Command Line | ~10 | HIGH |

### 1.5 awesome-context-engineering (yzfly)
- **Total entries:** ~25 featured articles + ~15 core research areas + ~15 tools
- **URL:** https://github.com/yzfly/awesome-context-engineering
- **License:** CC0
- **Organization:** Articles + Research Papers + Tools + Expert Insights + MCP

**Topical breakdown:**
| Section | Entries | Lyra Relevance |
|---|---|---|
| Featured Articles | ~15 | CRITICAL - design principles |
| Research Papers (Survey) | 1 major survey (1400+ papers) | HIGH |
| Core Research Areas | ~10 papers | HIGH |
| Tools & Projects | ~15 | CRITICAL |
| Expert Insights | Karpathy quote + 5 principles | HIGH |

---

## 2. Top 30 Most Relevant Papers/Repos for Lyra (Ranked)

### Tier 0: Foundation (Must-Read)

**1. "Building Effective AI Coding Agents for the Terminal: Scaffolding, Harness, Context Engineering, and Lessons Learned"**
- arXiv: 2603.05344 (March 2026)
- The most directly applicable paper for Lyra. Covers eager-construction scaffolding, compound multi-model architecture, 5-layer defense-in-depth safety, and schema-filtered planning subagents. Written from building OpenDev.

**2. "Memory in the Age of AI Agents: A Survey" (Shichun-Liu et al.)**
- arXiv: 2512.13564 (December 2025)
- The definitive taxonomy of agent memory: Forms (Token/Parametric/Latent) x Functions (Factual/Experiential/Working) x Dynamics. Essential framework for designing Lyra's memory architecture.

**3. "Harness Engineering" (OpenAI, Martin Fowler, Anthropic)**
- Multiple sources: openai.com/index/harness-engineering, martinfowler.com
- Defines the discipline: context engineering, architectural constraints, entropy management. The "humans on the loop" framing is the clearest conceptual map of harness design.

**4. "A Survey of Context Engineering for Large Language Models"**
- arXiv: 2507.13334 (July 2025)
- Formal taxonomy of context engineering from 1,400+ papers. Defines context retrieval, processing, management, compression, and isolation as first-class engineering disciplines.

**5. "Effective context engineering for AI agents" (Anthropic)**
- anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Systematically reframes harness design as "what configuration of context produces the desired behavior?" rather than prompt engineering alone.

### Tier 1: Agent Architecture & Harness Design

**6. "The Design Space of Today's and Future AI Agent Systems"**
- arXiv: 2604.14228 (April 2026)
- Reverse-engineers Claude Code's architecture: five-stage progressive compaction, subagent isolation with rebuilt permission contexts, 27-event-type hook pipeline. Most detailed public analysis of a production agent loop.

**7. "Natural-Language Agent Harnesses"**
- arXiv: 2603.25723 (March 2026)
- Proposes externalizing agent control logic as portable natural-language artifacts (NLAHs) executed by a shared Intelligent Harness Runtime. Directly addresses harness fragility.

**8. "Meta-Harness: End-to-End Optimization of Model Harnesses"**
- arXiv: 2603.28052 (March 2026)
- Treats the entire harness (system prompt, tool definitions, context management, completion logic) as a joint optimization target. 10M-token diagnostic context for harness search.

**9. "Agents Learn Their Runtime: Interpreter Persistence as Training-Time Semantics"**
- arXiv: 2603.01209 (March 2026)
- Controlled experiment showing persistence is a learned semantic that must be honored at deployment. 80% missing-variable errors or 3.5x token overhead if mismatched.

**10. "Terminal Agents Suffice for Enterprise Automation"**
- arXiv: 2604.00073 (April 2026)
- Directly validates Lyra's terminal-first approach. Terminal agents are sufficient for enterprise-scale automation.

### Tier 2: Memory Systems

**11. "Agentic Memory: Learning Unified Long-Term and Short-Term Memory Management for LLM Agents"**
- arXiv: 2601.01885 (January 2026)
- Unified memory management learning to decide what goes into long-term vs. short-term memory.

**12. "MemEvolve: Meta-Evolution of Agent Memory Systems"**
- arXiv: 2512.18746 (December 2025)
- The memory system itself evolves. Meta-evolution of how agents store and retrieve.

**13. "Prism: An Evolutionary Memory Substrate for Multi-Agent Open-Ended Discovery"**
- arXiv: 2604.19795 (April 2026)
- Evolutionary memory substrate specifically for MULTI-AGENT systems. Critical for Lyra's fleet memory.

**14. "HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models"**
- arXiv: 2405.14831 (May 2024)
- Hippocampus-inspired indexing for long-term memory. Proven approach with strong benchmarks.

**15. "MAGMA: Multi-Graph Agentic Memory Architecture"**
- arXiv: 2601.03236 (January 2026)
- Four orthogonal graphs (semantic, temporal, causal, entity). Outperforms MemGPT by 18.5% accuracy.

**16. "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory"**
- arXiv: 2504.19413 (April 2025)
- Production-grade memory layer used by AWS Agent SDK. Drop-in persistent memory.

**17. "Active Context Compression: Autonomous Memory Management in LLM Agents"**
- arXiv: 2601.07190 (January 2026)
- Focus Agent architecture: agent decides when to consolidate history into persistent Knowledge block. 22.7% token reduction, no accuracy loss.

### Tier 3: Multi-Agent Orchestration

**18. "AORCHESTRA: Automating Sub-Agent Creation for Agentic Orchestration"**
- arXiv: 2602.03786 (February 2026)
- Automates sub-agent creation for orchestration. Dynamically spawns specialized agents.

**19. "Language Model Teams as Distributed Systems"**
- arXiv: 2603.12229 (March 2026)
- Treats multi-agent systems as distributed systems with typed schemas, constrained action schemas, explicit boundary validation.

**20. "Task-Adaptive Multi-Agent Orchestration (AdaptOrch)"**
- arXiv: 2602.16873 (February 2026)
- Dynamically selects orchestration topology (parallel/sequential/hierarchical/hybrid) based on task dependency graphs. 12-23% improvement over model selection alone.

**21. "Recursive Multi-Agent Systems"**
- arXiv: 2604.25917 (April 2026)
- Recursive agent spawning. Agents can create sub-agents that create sub-agents.

**22. "AgentFactory: A Self-Evolving Framework Through Executable Subagent Accumulation and Reuse"**
- arXiv: 2603.18000 (March 2026)
- Accumulates and reuses executable subagents across tasks. Learning at the agent level.

### Tier 4: Context Engineering & Optimization

**23. "Experience Compression Spectrum: Unifying Memory, Skills, and Rules in LLM Agents"**
- arXiv: 2604.15877 (April 2026)
- Unifies memory, skills, and rules as different points on a compression spectrum. Foundational for Lyra's skill/memory continuum.

**24. "Everything is Context: Agentic File System Abstraction for Context Engineering"**
- arXiv: 2512.05470 (December 2025)
- Filesystem-based context delivery. Agents interact via read_file, grep, find, shell. Microsoft's Azure SRE agent saw 45% -> 75% "Intent Met" score using this approach.

**25. "A Self-Evolving Framework for Efficient Terminal Agents via Observational Context Compression"**
- arXiv: 2604.19572 (April 2026)
- Terminal-specific context compression for agents. Directly applicable to Lyra's terminal UX.

**26. "Context Engineering for Reliable AI Agents: Lessons from Building Azure SRE Agent"**
- Microsoft techcommunity (2026)
- Production case study: filesystem-based context engineering outperformed 100+ bespoke tools. 75% Intent Met on novel incidents.

### Tier 5: Skills, Tools & Evaluation

**27. "ReAct: Synergizing Reasoning and Acting in Language Models"**
- arXiv: 2210.03629 (October 2022)
- The foundational Thought/Action/Observation loop. Required reading for agent architecture.

**28. "SoK: Agentic Skills -- Beyond Tool Use in LLM Agents"**
- arXiv: 2602.20867 (February 2026)
- Systematization of knowledge on agent skills. Taxonomy beyond simple tool use.

**29. "SKILL0: In-Context Agentic Reinforcement Learning for Skill Internalization"**
- arXiv: 2604.02268 (April 2026)
- Skills learned in-context via reinforcement learning. No fine-tuning needed.

**30. "Measuring Agents in Production"**
- arXiv: 2512.04123 (December 2025)
- Framework for evaluating agents in production, not just in benchmarks. Essential for Lyra's quality metrics.

---

## 3. Key Techniques Extracted from Most Promising Sources

### 3.1 Self-Evolving Agent Architecture

The single most transformative trend across all 5 lists is **self-evolving agents** -- agents that modify their own prompts, tools, memory structure, and orchestration patterns based on execution feedback.

**Key technique papers:**

| Paper | Key Innovation | Lyra Application |
|---|---|---|
| Meta-Harness (2603.28052) | Joint optimization of entire harness via filesystem-backed search | Auto-tune Lyra's AGENTS.md, tool configs, memory structure |
| AutoAgent (2603.09716) | Elastic memory orchestration + evolving cognition | Adaptive memory allocation per task complexity |
| AgentFactory (2603.18000) | Executable subagent accumulation and reuse | Build a library of reusable subagents from prior runs |
| HyperAgents (2603.19461) | Self-modifying prompts, tools, strategy | Let Lyra evolve its own scaffolding |
| AORCHESTRA (2602.03786) | Automated sub-agent creation | Dynamically spawn specialists for subtasks |
| Natural-Language Agent Harnesses (2603.25723) | Portable NLAH artifacts | Make Lyra's harness inspectable, version-controlled, transferable |

**Implementation approach:**
```
1. Trace execution (capture full agent trajectories)
2. Diagnose failures (causal graph analysis, not just pass/fail)
3. Propose harness changes (prompt edits, tool reconfig, memory structure)
4. Validate in sandbox (regression test before deployment)
5. Deploy and iterate
```

### 3.2 Hierarchical Multi-Tier Memory Architecture

The consistent finding across the memory literature: **hierarchical memory architectures outperform flat vector stores** by 18-51% on long-horizon tasks.

**Key technique papers:**

| Paper | Architecture | Token Reduction | Accuracy Gain |
|---|---|---|---|
| TencentDB-Agent-Memory | 4-tier: Conversation -> Atom -> Scenario -> Persona | 61% | +51% pass rate |
| MAGMA (2601.03236) | 4-graph: semantic/temporal/causal/entity | Not reported | +18.5% over MemGPT |
| Letta/MemGPT | 3-tier: core/archival/recall | Not reported | Reference architecture |
| Mem0 (2504.19413) | Production-grade universal memory | Not reported | AWS SDK default |
| Prism (2604.19795) | Evolutionary memory for multi-agent | Not reported | Multi-agent specific |

**Recommended Lyra memory architecture:**
```
Layer 0: Working Memory (active context window)
  - Token-level, session-scoped
  - Managed by active context compression (Focus Agent pattern)

Layer 1: Episodic Memory (recent trajectory store)
  - Structured event records with causal links
  - Auto-pruned by recency + importance

Layer 2: Semantic Memory (persistent knowledge)
  - Multi-graph: entity graph + task graph + skill graph + convention graph
  - Policy-guided retrieval: different graph views for different task phases

Layer 3: Procedural Memory (reusable skills/patterns)
  - Version-controlled skill artifacts (SKILL.md)
  - Experience compression: trajectories -> reusable procedures

Layer 4: Fleet Memory (cross-agent shared knowledge)
  - Gossip protocol or shared blackboard
  - Conflict resolution with versioned belief revision
```

### 3.3 Context Engineering as the Highest-Leverage Harness Primitive

Context engineering is the single most impactful harness primitive. Multiple sources converge on the same finding: **context delivery method matters more than model choice.**

**Key techniques:**

| Technique | Source | Impact |
|---|---|---|
| Filesystem-as-context | Azure SRE Agent + Everything is Context (2512.05470) | 45% -> 75% Intent Met |
| Autonomous context compression | Focus Agent (2601.07190) | 22.7% token reduction |
| KV-cache optimization | Manus Context Engineering | Cache hit rate = cost/performance lever |
| Append-only context | Claude Code Best Practices | Preserves cache validity |
| Mask, don't remove tools | Manus Context Engineering | Better action selection |
| Progressive disclosure | Trellis, OpenViking | Load only what's needed per step |
| Context isolation (subagents) | Claude Code Architecture | 67% fewer tokens in multi-domain |

**Implementation for Lyra:**
```
1. Filesystem-first context delivery: expose everything as files, let agent grep/find/read
2. Append-only context log: never modify history, only append
3. Autonomous compression: agent decides when to compact (between tasks, not mid-task)
4. Subagent isolation: spawn subagents with clean contexts for independent subtasks
5. Tool masking: hide irrelevant tools rather than removing (preserves attention structure)
```

### 3.4 Multi-Agent Coordination Patterns

**Key techniques:**

| Pattern | Source | When to Use |
|---|---|---|
| Supervisor/Worker | LangGraph, AutoGen | Centralized task decomposition |
| Decentralized Handoff | OpenAI Agents SDK | Peer-to-peer delegation |
| Blackboard Architecture | Multi-Agent LLM Systems (2507.01701) | Shared state with opportunistic agents |
| Task DAG Execution | AdaptOrch (2602.16873) | Complex dependency graphs |
| Git-based Coordination | Anthropic (Building C Compiler) | File-based claim system, no central orchestrator |
| Gossip Protocol | Distributed systems literature | Fleet convergence |

**Lyra-specific recommendation:**
- Use **supervisor/worker** for explicit task decomposition
- Use **git-based coordination** for parallel independent work
- Use **gossip protocol** for fleet-level knowledge sharing
- Support **recursive delegation** (agents can spawn sub-agents)

### 3.5 Security & Permission Architecture

**Key techniques from harness engineering list:**

| Technique | Source | Implementation |
|---|---|---|
| 5-layer permission evaluation | Claude Agent SDK | hooks -> deny -> mode -> allow -> canUseTool |
| Intent-based authorization | nah (github.com/manuelschipper/nah) | Classify tool calls by intent, not command name |
| Pre-action authorization | Open Agent Passport (2603.20953) | 53ms median, signed audit records |
| Defense-in-depth sandboxing | NVIDIA OpenShell | Landlock + seccomp + OPA/Rego network proxy |
| Runtime authorization fabric | Microsoft (4509161) | Policy Enforcement Point + Policy Decision Point |

### 3.6 Verification & Quality Gates

**Key techniques:**

| Technique | Source | Impact |
|---|---|---|
| Behavioral fingerprinting | AgentAssay (2603.02601) | 86% regression detection vs 0% binary |
| Pass^k reliability (not pass@k) | Backtesting AI Agents | All N trials must succeed |
| Causal graph root cause analysis | AgentTrace (2603.14688) | 93.6% accuracy, 69x faster than LLM |
| Trace-driven harness evolution | Meta-Harness, AutoAgent | Automated improvement loop |
| Eval-driven development | Red Hat (March 2026) | 8-stage maturity model |

---

## 4. MCP Servers Worth Bundling with Lyra

Based on analysis of the awesome-mcp-servers catalog (1,500+ servers), here are the highest-value servers for a terminal-based multi-agent system:

### Tier 1: Core Infrastructure (Bundle Default)

| Server | Purpose | Stars |
|---|---|---|
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | Official reference implementations (filesystem, git, postgres, etc.) | Reference |
| [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | Browser automation via accessibility tree snapshots | High |
| [context7](https://github.com/upstash/context7) | Up-to-date code documentation for LLMs | High |
| [mcp-gateway](https://github.com/MikkoParkkola/mcp-gateway) | Universal MCP gateway, 4 meta-tools replace 100+ registrations | New |
| [ViperJuice/mcp-gateway](https://github.com/ViperJuice/mcp-gateway) | Meta-server for minimal tool bloat with progressive disclosure | New |

### Tier 2: Memory & Knowledge (High Priority)

| Server | Purpose |
|---|---|
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | Universal memory layer (AWS SDK default) |
| [letta-ai/letta](https://github.com/letta-ai/letta) | 3-tier memory architecture (MemGPT successor) |
| [getzep/zep](https://github.com/getzep/zep) | Temporal knowledge graph for agent memory |
| [alash3al/stash](https://github.com/alash3al/stash) | Self-hosted 8-stage consolidation pipeline |
| [MemPalace/mempalace](https://github.com/MemPalace/mempalace) | 96.6% R@5 on LongMemEval, zero LLM calls |
| [Tencent/TencentDB-Agent-Memory](https://github.com/Tencent/TencentDB-Agent-Memory) | 4-tier progressive memory, 61% token reduction |

### Tier 3: Code Intelligence (High Priority)

| Server | Purpose |
|---|---|
| [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | Tree-sitter AST analysis, 120x token reduction |
| [MinishLab/semble](https://github.com/MinishLab/semble) | Natural-language code search, 98% token reduction |
| [Mibayy/token-savior](https://github.com/Mibayy/token-savior) | Symbol-indexed code navigation, 77% token reduction |
| [mksglu/context-mode](https://github.com/mksglu/context-mode) | Sandbox tool output outside context window |

### Tier 4: Orchestration & Multi-Agent (High Priority)

| Server/Repo | Purpose |
|---|---|
| [Jovancoding/Network-AI](https://github.com/Jovancoding/Network-AI) | Multi-agent orchestration with shared blackboard, 20+ tools |
| [lastmile-ai/mcp-agent](https://github.com/lastmile-ai/mcp-agent) | Production-grade MCP agent framework |
| [A2A Protocol](https://github.com/a2aproject/A2A) | Agent-to-Agent protocol (Google) |
| [mastra-ai/mastra](https://github.com/mastra-ai/mastra) | TypeScript agent framework, 22K+ stars |

### Tier 5: Security & Observability (Medium Priority)

| Server | Purpose |
|---|---|
| [tldrsec/prompt-injection-defenses](https://github.com/tldrsec/prompt-injection-defenses) | Complete catalog of prompt injection defenses |
| [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) | 7-package runtime security toolkit |
| [NVIDIA/OpenShell](https://github.com/NVIDIA/OpenShell) | Kernel-level sandbox enforcement |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | Self-hosted LLM observability |
| [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | Self-hosted trace UI and eval runtime |

---

## 5. Context Engineering Techniques Worth Adopting

### 5.1 Proven Techniques (Immediate Adoption)

| Technique | Description | Reference |
|---|---|---|
| **Append-only context** | Never modify previous messages; add new ones at end | Claude Code Best Practices |
| **Filesystem-as-context** | Expose everything as files; agent uses grep/find/read | Azure SRE Agent (45% -> 75% improvement) |
| **Autonomous compression** | Agent decides when to compact, not fixed token threshold | Focus Agent (2601.07190) |
| **Subagent context isolation** | Spawn subagents with clean contexts for independent subtasks | Claude Code architecture |
| **Progressive context disclosure** | Load only needed standards/specs per step | Trellis, OpenViking |
| **KV-cache optimization** | Design prompts for maximum cache hit rates | Manus Context Engineering |
| **Tool masking (not removal)** | Hide irrelevant tools rather than removing from schema | Manus Context Engineering |

### 5.2 Advanced Techniques (Research Phase)

| Technique | Description | Reference |
|---|---|---|
| **Context as memory continuum** | Memory, skills, rules as compression spectrum | Experience Compression Spectrum (2604.15877) |
| **Observational context compression** | Terminal-specific compression for agents | 2604.19572 |
| **Schema-filtered planning subagents** | Enforce behavioral constraints via tool schema | 2603.05344 |
| **Context negotiation** | Agents request specific context formats | Vercel Content Negotiation |
| **MIDDLEWARE hooks** | 6 intercept points in agent loop for context modification | LangChain AgentMiddleware |

### 5.3 Context Failure Modes (Avoid)

| Failure Mode | Description | Mitigation |
|---|---|---|
| **Context rot** | Performance degrades as context grows | Compaction at strategic points |
| **Context poisoning** | Malicious inputs in context | Input sanitization, canary tokens |
| **Context distraction** | Irrelevant information pulls attention | Relevance filtering, subagent isolation |
| **Context clash** | Contradictory information in context | Belief revision, versioned facts |
| **Compaction amnesia** | Critical info lost during compaction | CLAUDE.md for persistent rules |

---

## 6. Gap Analysis: What Lyra Is Missing

Based on analysis of all 5 lists against Lyra's current architecture:

### 6.1 Critical Gaps

| Gap | Evidence | Priority |
|---|---|---|
| **No structured memory architecture** | 95+ memory papers exist; Lyra has no systematic memory tiering | P0 |
| **No self-evolution mechanism** | 115+ papers on self-evolving agents; Lyra has no harness improvement loop | P0 |
| **No context compression strategy** | 25+ tools/papers on context engineering; Lyra lacks autonomous compression | P0 |
| **No multi-agent fleet memory** | Prism, MAGMA, AGENT KB papers; Lyra agents don't share learned knowledge | P1 |
| **No causal failure diagnosis** | AgentTrace, AgentRx, AgentDebug; Lyra lacks systematic debugging | P1 |

### 6.2 Moderate Gaps

| Gap | Evidence | Priority |
|---|---|---|
| **No agent evaluation harness** | 20+ eval frameworks exist; Lyra has no systematic quality measurement | P2 |
| **No skill versioning/lifecycle** | SkillsBench, SkillFlow, SkillsVote; Lyra's skills lack governance | P2 |
| **No structured permission model** | 15+ papers/tools on auth; Lyra needs intent-based authorization | P2 |
| **No cross-session task resumption** | LangGraph checkpointing, Temporal.io; Lyra tasks are single-session | P2 |
| **No observability/tracing** | 12+ tools; Lyra lacks OpenTelemetry integration | P3 |

### 6.3 Opportunity Gaps

| Gap | Evidence | Priority |
|---|---|---|
| **No meta-harness optimization** | Meta-Harness paper, AutoAgent, harness-evolver; Lyra doesn't auto-tune itself | P3 |
| **No subagent accumulation** | AgentFactory; Lyra doesn't learn reusable subagents from runs | P3 |
| **No protocol-level multi-agent** | A2A, MCP; Lyra agents lack standardized interop | P3 |
| **No sandbox isolation per agent** | E2B, Daytona, OpenShell; Lyra agents share execution environment | P3 |

---

## 7. Priority Ranking of Proposed Adoptions (Impact x Effort)

### Quadrant 1: High Impact, Low Effort (DO FIRST)

| Adoption | Impact | Effort | Description |
|---|---|---|---|
| **Filesystem-as-context for agents** | HIGH | LOW | Expose tools as files; agent uses grep/find/read. 45->75% improvement in Azure case. |
| **Append-only context log** | HIGH | LOW | Never modify history; KV-cache stays valid. Trivial implementation change. |
| **CLAUDE.md for persistent rules** | HIGH | LOW | Move critical rules to system-prompt-level file. Survives compaction. |
| **Subagent context isolation** | HIGH | MEDIUM | Spawn subagents with clean, task-scoped contexts. 67% fewer tokens. |
| **Autonomous compression trigger** | HIGH | MEDIUM | Agent decides when to compact between tasks, not at fixed thresholds. |
| **MCP gateway for tool aggregation** | MEDIUM | LOW | One meta-server exposing all tools; reduce tool schema bloat. |

### Quadrant 2: High Impact, High Effort (PLAN NEXT)

| Adoption | Impact | Effort | Description |
|---|---|---|---|
| **Hierarchical 4-tier memory** | VERY HIGH | HIGH | Working/Episodic/Semantic/Procedural memory tiers with policy-guided retrieval. |
| **Self-evolving harness loop** | VERY HIGH | HIGH | Trace -> Diagnose -> Propose -> Validate -> Deploy cycle for harness improvement. |
| **Multi-agent fleet memory (Prism)** | HIGH | HIGH | Cross-agent knowledge sharing via evolutionary memory substrate. |
| **Structured verification pipeline** | HIGH | HIGH | Pass^k reliability, behavioral fingerprinting, causal root cause analysis. |
| **Skill lifecycle management** | HIGH | MEDIUM | Version-controlled skills with evaluation gates, governance policies. |

### Quadrant 3: Medium Impact, Low Effort (DO WHEN CONVENIENT)

| Adoption | Impact | Effort | Description |
|---|---|---|---|
| **OpenTelemetry tracing** | MEDIUM | LOW | Add OTEL spans to agent loop; use existing ecosystem (Grafana, Datadog). |
| **Tree-sitter code intelligence** | MEDIUM | LOW | Integrate codebase-memory-mcp for 120x token reduction on code navigation. |
| **BM25 context retrieval** | MEDIUM | LOW | Replace grep with semantic retrieval for tool output filtering. |
| **Structured error taxonomy** | MEDIUM | LOW | Categorize agent failures into memory/planning/action/system classes. |
| **Prompt caching setup** | MEDIUM | LOW | Cache repeated system prompts, tool definitions across sessions. |

### Quadrant 4: Medium Impact, High Effort (DEFER)

| Adoption | Impact | Effort | Description |
|---|---|---|---|
| **Protocol-level multi-agent (A2A)** | MEDIUM | HIGH | Standardize agent-to-agent communication with discovery, handoff, payment. |
| **Sandbox isolation per agent** | MEDIUM | HIGH | Docker/Firecracker per agent execution. Security at cost of complexity. |
| **Meta-harness optimization** | MEDIUM | HIGH | Outer loop that auto-tunes AGENTS.md, tool configs, memory structure. |

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Implement filesystem-as-context pattern
- Set up append-only context log
- Create CLAUDE.md with persistent rules
- Integrate MCP gateway for tool aggregation

### Phase 2: Memory Architecture (Weeks 3-4)
- Implement 4-tier memory: Working/Episodic/Semantic/Procedural
- Integrate autonomous context compression
- Add subagent context isolation

### Phase 3: Multi-Agent (Weeks 5-6)
- Build fleet memory (Prism-inspired evolutionary substrate)
- Implement supervisor/worker orchestration
- Add recursive subagent delegation

### Phase 4: Self-Evolution (Weeks 7-8)
- Build harness improvement loop (trace -> diagnose -> propose -> validate)
- Implement skill lifecycle management
- Add verification pipeline with causal root cause analysis

### Phase 5: Production (Weeks 9-10)
- OpenTelemetry tracing
- Structured permission model
- Sandbox isolation per agent
- Eval-driven development pipeline

---

## 9. References

### Primary Lists Analyzed
1. masamasa59/ai-agent-papers - https://github.com/masamasa59/ai-agent-papers
2. Shichun-Liu/Agent-Memory-Paper-List - https://github.com/Shichun-Liu/Agent-Memory-Paper-List
3. ai-boost/awesome-harness-engineering - https://github.com/ai-boost/awesome-harness-engineering
4. punkpeye/awesome-mcp-servers - https://github.com/punkpeye/awesome-mcp-servers
5. yzfly/awesome-context-engineering - https://github.com/yzfly/awesome-context-engineering

### Key Papers (by Lyra relevance tier)
See Section 2 for the ranked top-30 list with arXiv identifiers.

### Adjacent Lists (also worth exploring)
- VoltAgent/awesome-ai-agent-papers (363+ papers, weekly updates)
- EvoMap/awesome-agent-evolution (self-evolution focus)
- Picrew/awesome-agent-harness (150 entries, 84% GitHub projects)
- bradAGI/awesome-cli-coding-agents (80+ terminal agents)
- e2b-dev/awesome-ai-agents (agent frameworks by use case)
- Meirtz/Awesome-Context-Engineering (comprehensive context survey)

---

*Research conducted 2026-05-30. All arXiv links verified as of research date. Some papers may have updated versions.*

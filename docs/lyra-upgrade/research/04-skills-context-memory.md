# Lyra Research: Skills Systems, Context Management, and Agent Memory

This document deep-reads and analyzes all referenced skills systems (section 3.7) and memory/context supplement sources (section 3.17). Each entry follows a structured template: core mechanism, real benchmark numbers, trade-offs, design rationale, transferable ideas for Lyra (sections 4.2-4.4), and gap vs. Lyra's current `SkillRegistry` + `MemoryStore` baselines.

---

## Table of Contents

- [SKILLS SYSTEMS](#skills-systems)
  - [SkillNet](#skillnet)
  - [SkillOS](#skillos)
  - [Obsidian Skills](#obsidian-skills)
  - [multica-ai/andrej-karpathy-skills](#multica-aianbrej-karpathy-skills)
  - [forrestchang/andrej-karpathy-skills](#forrestchanganbrej-karpathy-skills)
  - [obra/superpowers](#obrasuperpowers)
  - [SkillOpt (Microsoft)](#skillopt-microsoft)
  - [academic-research-skills](#academic-research-skills)
  - [cheetahclaws](#cheetahclaws)
  - [CLI-Anything](#cli-anything)
  - [oh-my-openagent](#oh-my-openagent)
  - [claude-skills (alirezarezvani)](#claude-skills-alirezarezvani)
  - [Letta / MemGPT](#letta--memgpt)
  - [Zep Graphiti](#zep-graphiti)
  - [Mem0](#mem0)
  - [lean-ctx](#lean-ctx)
- [MEMORY & CONTEXT PAPERS](#memory--context-papers)
  - [Mem0 Paper](#mem0-paper)
  - [ACON: Adaptive Agent Context Compression](#acon-adaptive-agent-context-compression)
  - [AnnaAgent: Tertiary Memory](#annaagent-tertiary-memory)
  - [DAVIS: Knowledge-Graph Inner Monologue](#davis-knowledge-graph-inner-monologue)
  - [MSI-Agent: Multi-Scale Insight](#msi-agent-multi-scale-insight)
  - [Field-Theoretic Memory (Mitra)](#field-theoretic-memory-mitra)
  - [COMPASS: Hierarchical Context Management](#compass-hierarchical-context-management)
  - [ExtAgents: Scaling External Knowledge](#extagents-scaling-external-knowledge)
  - [CFGM: Coarse-to-Fine Grounded Memory](#cfgm-coarse-to-fine-grounded-memory)
  - [MemAgent (ICLR 2026 Oral)](#memagent-iclr-2026-oral)
  - [PISA: Pragmatic Psych-Inspired Memory](#pisa-pragmatic-psych-inspired-memory)
  - [Memory Survey (Du, 2026)](#memory-survey-du-2026)
  - [Anthropic Context Engineering](#anthropic-context-engineering)
  - [Awesome-Memory-for-Agents (enumeration)](#awesome-memory-for-agents-enumeration)
- [SYNTHESIS](#synthesis)

---

# SKILLS SYSTEMS

---

## SkillNet

**URL:** https://github.com/zjunlp/SkillNet | Paper: https://arxiv.org/abs/2603.04448

**Core Mechanism:** SkillNet is an open infrastructure/"npm for AI skills" comprising:
- **Skill Creation Pipeline**: Ingests heterogeneous inputs (execution trajectories, GitHub repos, office docs (PDF/PPT/Word), natural language prompts) and converts them into structured skill packages via LLM calls.
- **5-Dimension Evaluation**: Safety, Completeness, Executability, Maintainability, Cost-Awareness -- each scored Good/Average/Poor via an LLM judge (GPT-4o-mini) with fine-grained rubrics, supplemented by optional sandbox script execution.
- **Skill Relationship Graph**: Auto-discovers `similar_to`, `belong_to`, `compose_with`, `depend_on` edges between skills via hybrid embedding + LLM inference.
- **Three-Layer Ontology**: Skill Taxonomy (categories/tags) -> Skill Relation Graph (typed edges) -> Skill Package Library (physical file organization).
- **Open Resources**: REST API (keyword + vector search), Python SDK/CLI (`pip install skillnet-ai`), 200K+ candidate skills / 150K+ curated, MCP Server integration.

Source code analysis of `skillnet-ai/` reveals: `client.py` (facade for 5 operations), `creator.py` (LLM-based skill generation with CodeAnalyzer for Python AST + regex for JS/TS/Java/Go/Rust/C++), `evaluator.py` (Loader walks SKILL.md/scripts/references, ScriptRunner executes with py_compile + usage extraction, LLMClient evaluates with json-repair fallback), `analyzer.py` (LLM-based graph inference), `searcher.py` (keyword + vector REST queries).

The Skill package standard: `skill-name/SKILL.md` (YAML frontmatter + markdown instructions) + optional `scripts/`, `references/`, `assets/`.

**Results (real numbers):**
- On ALFWorld, WebShop, ScienceWorld: +40% average reward, -30% execution steps vs. ReAct baseline
- DeepSeek V3.2+SkillNet: ALFWorld Seen 80.60 (ReAct 66.43), Unseen 83.57 (69.40); WebShop 46.18 (31.55); ScienceWorld 81.31 (64.67)
- Gemini 2.5 Pro+SkillNet: ALFWorld Seen 91.43 (60.00), Unseen 91.04 (61.94)
- Gains robust across model capacities (o4 Mini, DeepSeek V3.2, Gemini 2.5 Pro)
- Validation: MAE < 0.03 across all 5 dimensions, QWK ~1.000 (near-perfect inter-annotator agreement)

**Trade-offs:**
- LLM-dependent creation and evaluation; quality hinges on underlying judge model
- Safety mechanism detects some adversarial skills but "cannot fully mitigate" poisoned contributions
- No end-to-end pipeline for natural-language -> instantiated agent
- Private/specialized domain skills resist capture

**Design Rationale:** Skills as "unified knowledge representation" bridging unstructured language with structured executable logic. Three-step: Discovery (metadata), Activation (full instructions), Execution (code + instructions). File-based, version-controlled for portability.

**Transferable Idea for Lyra (SS4.4 Skills):**
1. SkillNet's 5-dimension evaluation rubric (Safety/Completeness/Executability/Maintainability/Cost-Awareness) should be adapted as Lyra's `SkillRegistry.evaluate()` quality gate before adding skills to the registry.
2. The `similar_to`/`compose_with`/`depend_on` relationship graph should be adopted for Lyra's skill dependency resolution in DAG routing.
3. The creation-from-trajectory pipeline is directly applicable: Lyra should auto-generate skills from agent execution traces.
4. The skill package standard (SKILL.md + scripts + references) aligns with Lyra's existing `Soul`-based skills; adoption of the frontmatter metadata format would enable SkillNet marketplace compatibility.
5. MCP Server integration for skill search/install is a low-effort, high-impact add.

**Gap vs Baseline (Lyra's SkillRegistry):** Lyra's current `SkillRegistry` lacks:
- Quality scoring gates (any skill can be registered)
- Relationship graph (skills are flat, no dependency/composition metadata)
- Auto-creation from trajectories or source inputs
- Search/discovery API (local or networked)
- Versioning and evaluation provenance

---

## SkillOS

**URL:** https://github.com/MontrealAI/skillos

**Core Mechanism:** Self-improving agent operating system with a compounding loop: work -> trace -> lesson -> candidate skill -> verification -> release -> routing upgrade -> better future work. Python reference implementation with:
- **Data models**: `Agent`, `Job`, `Trace`, `Lesson`, `SkillVersion`, `Release` (all dataclasses)
- **Storage layer**: `SkillOSStorage` (SQLite-backed)
- **LearningEngine**: Discovers lessons from traces by analyzing human edits and scores
- **SkillTrainer**: Creates candidate skill versions from lessons via bounded edits
- **Release management**: Versioned skills with rollback support
- **Proof system**: Public GitHub Actions proofs with deterministic benchmarks, pre-registered gates, verifier courts, risk gates, JSON receipts, badges

**Results (real numbers):** Proof system is reference/deterministic -- no published benchmark numbers for the skill improvement loop itself. The value is architectural: a complete, measurable loop design.

**Trade-offs:**
- Heavy infrastructure for the proof/audit system (JSON receipts, badges, GitHub Actions)
- `_bounded_edit` is trivial (appends learned behavior as a new section) -- not yet a sophisticated skill merge
- Learning from traces requires human-edited output as signal; cold-start problem

**Design Rationale:** "Intelligence should not be trapped inside one agent, one prompt, one workflow, or one team. Verified capability should become reusable infrastructure." The core flywheel: completed work -> verified traces -> reusable skills -> releases -> routing improvements.

**Transferable Idea for Lyra (SS4.4 Skills):**
1. The `Trace -> Lesson -> SkillVersion -> Release` pipeline is directly transferable. Lyra should implement `TraceRepository` -> `LearningEngine` -> `SkillTrainer` as the skill evolution loop.
2. The bounded-edit pattern (appending learned behaviors rather than rewriting skills) prevents destructive updates.
3. The public proof/gate system is aspirational but the concept of pre-registered verification gates before skill release is practical.
4. Versioned skills with rollback support (`Release.rollback_version`) should be added to Lyra's `SkillRegistry`.

**Gap vs Baseline:** Lyra has no lesson extraction from traces, no automatic skill versioning from learned patterns, and no release gating.

---

## Obsidian Skills

**URL:** https://github.com/kepano/obsidian-skills

**Core Mechanism:** A collection of Claude Code skills designed for the Obsidian knowledge management ecosystem. Skills are standard `.claude/skills/` packages (SKILL.md format) focused on note-taking, knowledge graph operations, and plugin development workflows. Includes hooks configurations for automatic skill activation based on file operations.

The repo is lightweight -- primarily a curated skill pack rather than a platform or infrastructure.

**Transferable Idea for Lyra (SS4.4 Skills):**
- Demonstrates that domain-specific skill packs (Obsidian knowledge management) are a viable distribution model. Lyra could support domain-specific skill registries per project type.
- The SKILL.md convention as discovered by Claude Code shows the standard import mechanism works.

**Gap vs Baseline:** Minimal -- this is a skill collection, not an infrastructure contribution.

---

## multica-ai/andrej-karpathy-skills

**URL:** https://github.com/multica-ai/andrej-karpathy-skills

**Core Mechanism:** A single high-quality skill (`karpathy-guidelines`) packaged as:
- Claude Code skill (SKILL.md)
- Cursor rule (`.mdc` file)
- Plugin manifest for marketplace distribution

The skill encodes Andrej Karpathy's 4 behavioral guidelines for reducing LLM coding mistakes: (1) Think Before Coding, (2) Simplicity First, (3) Surgical Changes, (4) Goal-Driven Execution.

**Transferable Idea for Lyra (SS4.4 Skills):**
- Multi-harness packaging (same content as Claude Code skill + Cursor rule + Gemini config) demonstrates cross-platform skill distribution. Lyra should target multi-platform export.
- The behavioral-guideline skill format (principles + checklist + examples) is the "instruction-only" archetype that SkillNet's evaluator rate as `executability: Good` even without scripts.

**Gap vs Baseline:** Lyra's skills are currently Claude Code-only (.claude/skills). Multi-platform export would increase reach.

---

## forrestchang/andrej-karpathy-skills

**URL:** https://github.com/forrestchang/andrej-karpathy-skills

**Core Mechanism:** An earlier/alternative implementation of Karpathy coding guidelines as Claude Code skills. Similar content to multica-ai's version but packaged differently.

**Transferable Idea:** Confirms the Karpathy-guidelines pattern as a canonical skill format for behavioral shaping.

**Gap vs Baseline:** Nil beyond confirmation of pattern.

---

## obra/superpowers

**URL:** https://github.com/obra/superpowers

**Core Mechanism:** A zero-dependency Claude Code plugin providing 14 production-tested skills that auto-trigger based on conversation context. Key architecture elements:
- **`using-superpowers` bootstrap skill**: The core discovery mechanism that causes skills to auto-trigger at session start
- **Skill format**: Standard `.claude/skills/` SKILL.md files
- **Trigger patterns**: Skills activate based on keyword detection in user prompts (e.g., "brainstorming" skill triggers on open-ended requests before any code is written)
- **Hook system**: PostToolUse hooks for verification, code review, and TDD enforcement
- **Skills catalog**: `brainstorming`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `verification-before-completion`, `writing-plans`, `writing-skills`, `using-superpowers`

Project has a 94% PR rejection rate (maintainers are exceptionally rigorous). Skills are "code that shapes agent behavior" -- changes require eval evidence.

**Results (real numbers):** No published benchmarks. Value is in the tested, production-hardened skill interaction patterns.

**Trade-offs:**
- Zero-dependency constraint limits integration options but ensures portability
- Skill content is finely tuned; changes to "Red Flags tables, rationalization lists" rejected without eval evidence
- Auto-triggering can be intrusive if not well-calibrated

**Design Rationale:** Skills should auto-trigger at the right moments without user prompt. The `using-superpowers` bootstrap is the entry point; without it, "skills are dead weight -- present on disk but never invoked." Skill content explicitly departs from Anthropic's published guidance in favor of empirically tested alternatives.

**Transferable Idea for Lyra (SS4.4 Skills):**
1. Skill auto-triggering (bootstrap + keyword detection) is the critical missing piece in Lyra. Current skills require explicit invocation.
2. The `using-superpowers` bootstrap pattern -- a meta-skill that discovers and activates other skills -- should be Lyra's `SkillOrchestrator` design pattern.
3. The concept of "eval evidence required for skill changes" aligns with Lyra's quality gates.
4. The verification-before-completion pattern (PostToolUse hook after tool calls) should be a standard Lyra workflow.

**Gap vs Baseline:** Lyra lacks (a) auto-triggering of skills based on context, (b) a bootstrap meta-skill for discovery, (c) PostToolUse verification hooks integrated with the skill system, (d) empirical eval requirements for skill changes.

---

## SkillOpt (Microsoft)

**URL:** https://github.com/microsoft/SkillOpt

**Core Mechanism:** Treats agent skill documents as trainable parameters and optimizes them with the discipline of deep learning training loops. Architecture:
- **Training loop**: rollout (run agent with current skill) -> reflect (analyze failures) -> aggregate (collect edit candidates) -> select (choose best edit) -> update (apply if validation improves) -> evaluate (held-out test)
- **Textual learning rate**: Bounded number of add/delete/replace edits per epoch
- **Optimizer model**: Separate LLM that generates bounded skill edits from scored rollouts
- **Rejected-edit buffer**: Prevents cyclic edits
- **Slow/meta update**: Epoch-wise update mode for stability
- **Deployment artifact**: Single `best_skill.md` (300-2000 tokens), zero inference-time model calls
- **Multi-backend**: OpenAI, Azure, Claude, Qwen, MiniMax
- **WebUI**: Gradio dashboard for monitoring

Source code analysis: `skillopt/optimizer/` contains `skill.py` (core editing), `select.py` (edit selection), `update_modes.py` (fast/slow/meta), `rewrite.py` (skill rewriting), `reflect.py` (failure analysis), `aggregate.py` (candidate rollup), `scheduler.py` (learning rate scheduling), `clip.py` (edit budget), `lr_autonomous.py` (self-tuning learning rate).

**Results (real numbers):**
- 52 evaluated (model, benchmark, harness) cells: SkillOpt is **best or tied-best on ALL**
- GPT-5.5: +23.5 points (direct chat), +24.8 (Codex agentic loop), +19.1 (Claude Code CLI)
- Transfers across model scales, between Codex and Claude Code harnesses, to nearby benchmarks
- 6 benchmarks, 7 target models, 3 execution harnesses

**Trade-offs:**
- Requires multiple rollout iterations per epoch (compute cost during training)
- Skill quality depends on optimizer model quality
- Textual edits may miss subtle improvements that continuous parameter tuning would capture
- Validation gate requires a held-out test set per skill

**Design Rationale:** "Train agent skills like you train neural networks -- with epochs, batch sizes, learning rates, and validation gates -- but without touching model weights." The key insight: skill documents are the trainable state of a frozen agent.

**Transferable Idea for Lyra (SS4.4 Skills):**
1. This is the single most important reference for Lyra's skill optimization. The entire training loop architecture (rollout -> reflect -> aggregate -> select -> update -> evaluate) should be Lyra's `SkillOptimizer`.
2. Textual learning rate (bounded edits per epoch) prevents catastrophic skill degradation.
3. The rejected-edit buffer prevents oscillation.
4. The slow/meta update distinction (epoch-wise vs. per-rollout) enables multi-timescale learning.
5. Validation gate requiring strictly improved held-out scores is the correct quality bar.
6. The `best_skill.md` export pattern (small, deployable artifact) aligns with Lyra's Soul format.

**Gap vs Baseline:** Lyra has zero skill optimization capability. Skills are static. Implementing a SkillOpt-derived training loop would be the largest gap-closing contribution.

---

## academic-research-skills

**URL:** https://github.com/Imbad0202/academic-research-skills

**Core Mechanism:** Collection of Claude Code skills for academic research workflows. Covers literature review, paper writing, peer review response, statistical analysis guidance, etc.

**Transferable Idea:** Demonstrates the viability of domain-specific skill packs for academic contexts. Lyra's skill marketplace could include domain-specific registries.

---

## cheetahclaws

**URL:** https://github.com/SafeRL-Lab/cheetahclaws

**Core Mechanism:** Research project from SafeRL-Lab focusing on safe reinforcement learning. The "claws" naming convention aligns with the "claw" ecosystem (OpenClaw, JiuwenClaw). The repo explores safe skill execution and constraint-based agent behavior.

**Transferable Idea for Lyra (SS4.4):** The safety constraints approach for skill execution can inform Lyra's permission/scope system for skills.

---

## CLI-Anything

**URL:** https://github.com/HKUDS/CLI-Anything

**Core Mechanism:** Converts arbitrary CLI applications into LLM-agent-accessible tools. Bridges command-line interfaces with agent skill systems, allowing agents to discover and use CLI tools dynamically.

**Transferable Idea for Lyra:** Dynamic tool discovery from CLI applications. Lyra could use this pattern to expand its tool registry beyond hardcoded tools.

---

## oh-my-openagent

**URL:** https://github.com/code-yeongyu/oh-my-openagent

**Core Mechanism:** An earlier open-source multi-agent orchestration framework. Provides agent management, tool integration, and skill-like capabilities. Predecessor-style work in the "oh-my-" ecosystem.

**Transferable Idea:** The multi-agent routing patterns (agent discovery, capability-based dispatch) inform Lyra's subagent routing.

---

## claude-skills (alirezarezvani)

**URL:** https://github.com/alirezarezvani/claude-skills

**Core Mechanism:** A comprehensive skills library with 338+ production-ready skills across 16 domains:
- Engineering (78 advanced skills), Engineering Team (51 core skills), C-Level Advisory (66 skills), Marketing (46 skills), Agents (51+ skills), Project Management, RA/QM Compliance, Business Growth/Operations, Commercial, Finance, Research, etc.
- Each skill: SKILL.md + scripts/ (Python CLI tools) + references/ (expert knowledge) + assets/ (templates)
- Slash commands (87+): `/changelog`, `/tdd`, `/prd`, etc.
- Agent personas (51+): cs-* agents with specialized roles
- Plugin registry, Marketplace distribution

**Architecture Pattern:**
```
skill-name/
├── SKILL.md              # Master documentation
├── scripts/              # Python CLI tools (no ML/LLM calls)
├── references/           # Expert knowledge bases
└── assets/               # User templates
```
Design: "Knowledge flows from references/ -> into SKILL.md workflows -> executed via scripts/ -> applied using assets/ templates."

**Results (real numbers):** No published benchmarks. Scale is the metric: 338+ skills, 533 Python automation tools, 676 reference guides, 62 marketplace plugins.

**Trade-offs:**
- Massive catalog requires significant maintenance effort
- Quality consistency across 338 skills is challenging
- Some skills are inevitably domain-specific, reducing general applicability

**Design Rationale:** "Skills are self-contained packages. Each includes executable tools, knowledge bases, and user-facing templates. Teams can extract a skill folder and use it immediately."

**Transferable Idea for Lyra (SS4.4 Skills):**
1. The "knowledge flows" pattern (references -> SKILL.md -> scripts -> assets) is a superior skill architecture that Lyra should adopt.
2. The orchestrator + sub-skills pattern (e.g., `engineering-team` orchestrator dispatching to specialized sub-skills) maps to Lyra's DAG routing.
3. The per-skill Python toolkit pattern (scripts/ with no ML/LLM calls) aligns with Lyra's separation of deterministic logic from LLM reasoning.
4. The Matt Pocock "Forcing-question library" pattern in every SKILL.md is a concrete technique for improving skill activation reliability.

**Gap vs Baseline:** Lyra's skill catalog is orders of magnitude smaller. The orchestrator/sub-skill pattern is not yet implemented.

---

## Letta / MemGPT

**URL:** https://github.com/letta-ai/letta

**Core Mechanism:** "LLM-as-OS" with self-editing memory. LLM agents manage their own memory through tool calls, using:
- **Core memory**: In-context memory organized as labeled `Block` objects (persona, human, etc.). Agent can edit blocks via tools (e.g., `core_memory_replace`, `core_memory_append`).
- **Recall memory**: Full message history stored in external DB, retrievable via `recall` queries.
- **Archival memory**: External knowledge stored as passages with vector embeddings, retrievable via `archival_memory_search`.
- **Memory filesystem**: Git-backed structured memory for agents managing code projects.
- **Context window management**: `ContextWindowOverview` tracks tokens across system prompt/core memory/archival summary/recall memory/functions/messages, enabling the agent to manage its own context budget.

Source code (`letta/schemas/memory.py`): `Memory` class wraps `List[Block]` with prompt template; `ContextWindowOverview` tracks 15+ token categories. The `BaseAgent` class (`letta/agents/base_agent.py`) uses `MessageManager`, `AgentManager`, `PassageManager` for tiered storage.

**Results (real numbers):** No published benchmarks in the repo. The architecture has been deployed in production environments.

**Trade-offs:**
- Self-editing memory can drift; agent may incorrectly modify its own core memory
- SQLite-backed archival search scales to ~millions of passages but not billions
- Context window tracking is LLM-provider-specific (different tokenizers)

**Design Rationale:** "LLMs should be able to edit their own memory -- it's the only way to achieve truly long-running, stateful agents." Three-tier architecture separates in-context working memory (editable blocks), searchable history (recall), and long-term knowledge (archival).

**Transferable Idea for Lyra (SS4.2 Memory):**
1. Letta's three-tier architecture (core/recall/archival) is directly applicable as Lyra's `MemoryStore` redesign:
   - Core memory = Lyra's working context (persona, human, tools)
   - Recall = Lyra's session store
   - Archival = Lyra's knowledge base with vector search
2. Self-editing memory via tool calls is a more scalable pattern than manual memory management. Lyra's agent should be able to `memory_append`, `memory_replace` via tool calls.
3. The `ContextWindowOverview` token budget tracking should be adopted for Lyra's context window management.
4. Git-backed memory filesystem for code-aware agents is a novel pattern Lyra could adopt for project-specific memory.
5. The Block-based memory organization (labeled sections) aligns with Lyra's structured soul/context sections.

**Gap vs Baseline:** Lyra's current `MemoryStore` is a single tier (flat key-value store). No self-editing, no tiered storage, no context window tracking, no archival search.

---

## Zep Graphiti

**URL:** https://github.com/getzep/graphiti

**Core Mechanism:** Temporal knowledge graph architecture for agent memory. Uses:
- **Entity Nodes**: People, places, concepts extracted from conversations
- **Episodic Edges**: Temporal connections linking entities to conversation episodes
- **Community Edges**: Group-level relationship summaries
- **Multiple search strategies**: Hybrid search (embedding + keyword + cross-encoder), node distance, RRF fusion
- **Neo4j backend**: Graph database for storage and traversal
- **LLM-based extraction**: Uses OpenAI-compatible LLMs for entity/edge extraction from text
- **Cross-encoder reranking**: BGE, OpenAI, Gemini rerankers for precision retrieval
- **Saga graph**: Higher-level narrative summaries connecting multiple episodes

Source code (`graphiti_core/graphiti.py`): Central `Graphiti` class manages `GraphDriver` (Neo4j), `LLMClient`, `EmbedderClient`, `CrossEncoderClient`. Node types: `EpisodicNode`, `EntityNode`, `CommunityNode`, `SagaNode`. Edge types: `EpisodicEdge`, `EntityEdge`, `CommunityEdge`, `HasEpisodeEdge`, `NextEpisodeEdge`.

**Trade-offs:**
- Neo4j dependency adds infrastructure weight
- LLM-based extraction costs per conversation turn
- Graph construction latency (not real-time)
- Scalability depends on graph DB performance

**Design Rationale:** Agent memory benefits from explicit relational structure (knowledge graphs) rather than flat vector stores. Temporal edges capture when events occurred, enabling time-aware retrieval.

**Transferable Idea for Lyra (SS4.2 Memory):**
1. Graph-based memory with typed edges (entity, episodic, community) enables rich relational queries that vector similarity alone cannot support.
2. The hybrid search pattern (embedding + keyword + reranker + graph distance) should be Lyra's retrieval pipeline.
3. Saga-level summarization (grouping episodes into narrative arcs) is a compaction strategy Lyra should adopt.
4. The cross-encoder reranking stage significantly improves retrieval precision.

**Gap vs Baseline:** Lyra's `MemoryStore` has no graph structure, no typed relationships, no temporal dimension, and no multi-stage retrieval pipeline.

---

## Mem0

**URL:** https://github.com/mem0ai/mem0

**Core Mechanism:** Production-ready memory layer for LLM agents with:
- **Dynamic extraction** from conversation turns
- **Consolidation** merging new facts into existing memory (deduplication)
- **Retrieval** of relevant memories via hybrid search
- **Graph-enhanced variant** for relational structure capture
- **20+ vector store backends**: Chroma, Qdrant, Pinecone, Weaviate, Milvus, pgvector, Elasticsearch, etc.
- **15+ LLM providers**: OpenAI, Anthropic, Azure, Ollama, Gemini, etc.
- **Reranker support**: Cohere, HuggingFace, Sentence-Transformer, ZeroEntropy, LLM-based
- **Entity extraction**: Spacy-based NER for memory topic tagging
- **Memory types**: Additive (append-only) and procedural (system-level) memory
- **Server/MCP**: REST API server + MCP protocol for multi-client access

Source code (`mem0/memory/main.py`): `MemoryBase` abstraction with `add()`, `search()`, `get_all()`, `update()`, `delete()` operations. Factory pattern for embedding/LLM/vector-store/reranker backends. Scoring with BM25 + entity boost + embedding similarity.

**Results (real numbers):**
- +26% relative LLM-as-a-Judge metric over OpenAI baseline
- Graph variant adds ~2% overall
- 91% lower p95 latency vs full-context processing
- >90% token cost savings vs full-context

**Trade-offs:**
- Higher latency than no-memory baseline (extraction + retrieval overhead)
- Graph variant adds ~2% accuracy at additional complexity cost
- Dependency on external vector store infrastructure
- Extraction quality depends on LLM quality

**Design Rationale:** "Fixed context windows pose fundamental challenges for maintaining consistency over prolonged multi-session dialogues." The architecture is production-oriented (p95 latency, token economics) with memory-as-a-service framing.

**Transferable Idea for Lyra (SS4.2 Memory):**
1. The `add()` -> `search()` -> `update()` -> `delete()` memory API abstraction should be Lyra's standard `MemoryStore` interface.
2. The hybrid scoring (embedding similarity + BM25 + entity boost + recency) improves retrieval relevance over vector-only.
3. The factory pattern (swappable backends for LLM/embedding/vector-store) is the correct architecture for Lyra's provider abstraction.
4. The graph-enhanced variant proves that relational structure provides meaningful accuracy gains.
5. The MCP server enables multi-client memory access, useful for Lyra's subagent coordination.

**Gap vs Baseline:** Lyra's `MemoryStore` has minimal search (no hybrid scoring), no extraction/consolidation pipeline, no graph variant, and no multi-backend factory pattern.

---

## lean-ctx

**URL:** https://github.com/yvgude/lean-ctx

**Core Mechanism:** A local Rust binary that serves as a "Cognitive Context Layer" between AI code agents and their context window. Features:
- **Map-mode file reads**: Cached re-reads at ~13 tokens vs ~2000 tokens each
- **Compressed CLI output**: `git status` from ~800 tokens to ~120 tokens
- **Cross-session memory**: Context persists across chat sessions
- **Real-time budget dashboard**: Token + USD savings visible live
- **Zero config**: Works with Cursor, Claude Code, Copilot, Windsurf, Codex, Gemini, and 24+ other agents
- **Rust compiled binary for speed**
- **24+ agent harness compatibility**

Key claims: cached re-reads at ~13 tokens (vs ~2000), compressed `git status` at ~120 tokens (vs ~800).

**Transferable Idea for Lyra (SS4.3 Context):**
1. Map-mode file reading (compressed representation instead of raw text) saves massive token budgets.
2. Shell command output compression (structured summaries instead of raw output) should be Lyra's default for tool responses.
3. The cross-session context persistence pattern (allowing memory to bridge chat sessions) is a higher-level capability Lyra needs.
4. The real-time budget dashboard gives users visibility and control -- Lyra should expose token budgets per session.
5. Rust implementation for performance is aspirational but the architectural pattern (local binary intercepting agent-context communication) is novel.

**Gap vs Baseline:** Lyra has no context compression, no output compression, no cross-session persistence, no token budget visibility.

---

# MEMORY & CONTEXT PAPERS

---

## Mem0 Paper

**URL:** https://arxiv.org/abs/2504.19413

**Core Mechanism:** (Covered extensively in the Mem0 repo analysis above). The paper formalizes the write -> consolidate -> retrieve loop with optional graph enhancement.

**Results (real numbers):** +26% LLM-as-a-Judge, 91% lower p95 latency, >90% token cost savings, +2% from graph variant.

**Transferable Idea:** The consolidation step (merging new facts with existing) is the key algorithmic contribution Lyra should adopt to prevent memory bloat.

---

## ACON: Adaptive Agent Context Compression

**URL:** https://arxiv.org/abs/2510.00615 | Venue: ICML 2026

**Core Mechanism:** ACON optimizes context compression for LLM agents via:
- **Two-level compression**: Separate compressors for interaction history and observations, activated only when exceeding token thresholds (optimal: 4096 hist, 1024 obs)
- **Natural-language optimization**: An optimizer LLM generates contrastive feedback comparing trajectories that succeed vs fail with compression, then refines the compression prompt. No model weights are updated.
- **Two-stage optimization**:
  - Utility Maximization (UT): Maximize task success under compression
  - Compression Optimization (CO): Minimize context size while maintaining success
- **Distillation**: Teacher compressor (GPT-4.1) distilled into small student models (Qwen3-14B via LoRA, Qwen3-8B, Phi-4) preserving >95% performance
- **POMDP formalization**: Agent tasks as partially observable MDPs with cost = expected reward - lambda * context cost

**Results (real numbers):**
- Peak token reduction: 26-54% across benchmarks
- AppWorld (GPT-4.1): 56.5% accuracy (hist+obs comp) vs 56.0% no-compression baseline (net zero loss!)
- Small model agent uplift: +32.4% on AppWorld (Qwen3-14B: 25.6 -> 33.9), +45.6% on 8-obj QA
- Distilled compressor cost: $0.0004/example vs $0.045 teacher (99.1% reduction)
- Optimizer cost: <$2 per benchmark
- 8-Objective QA: peak tokens reduced 54.5%, dependency reduced 61.5%

**Trade-offs:**
- Compression adds wall-clock latency (~15-30% more time)
- UT+CO best for noisy environments; UT-only safer for information-seeking tasks
- Distillation gap may widen with more diverse task distributions
- KV-cache benefits not fully proportional to token reduction

**Design Rationale:** "Environment rollouts are extremely expensive since each reward requires multi-step executions." Natural-language optimization avoids high-variance policy gradients. Two-stage optimization ensures both accuracy and compression.

**Transferable Idea for Lyra (SS4.3 Context):**
1. Separate history vs. observation compression at threshold-based trigger points is Lyra's required context management architecture.
2. The contrastive failure analysis (compare trajectories that succeed without compression but fail with it) is a concrete optimization technique.
3. Distillation of compressors into small models (preserving >95% performance at 99% cost reduction) makes per-agent compression viable.
4. The <$2 per-benchmark optimization cost makes this practical for Lyra's training pipeline.
5. Small model agent uplift (+32-46%) demonstrates that compression helps most where it's needed most.

**Gap vs Baseline:** Lyra has zero adaptive compression. Current context management is "keep everything" -- the exact anti-pattern ACON solves.

---

## AnnaAgent: Tertiary Memory

**URL:** https://arxiv.org/abs/2506.00551

**Core Mechanism:** A tertiary memory system for multi-session psychological counseling simulation:
- **Real-time memory**: Current session conversation as full context
- **Short-term memory**: Self-report scales + randomly matched profile events from a trigger dataset
- **Long-term memory**: Scales and conversations from previous sessions via Agentic RAG
- **Emotion Inferencer**: Qwen2.5-7B fine-tuned on D4 dataset to predict next-utterance emotion categories
- **Emotion Perturber**: Random weighted selection from emotion groups to avoid fixed patterns
- **Chief Complaint Chain Generator**: Predicts how the patient's presenting problem evolves across sessions
- **Complaint Elicitor** (Algorithm 1): Iterates through a complaint chain, advancing when current stage is recognized

**Results (real numbers):**
- Anthropomorphism BERT-F1: 0.6691 (D4+PsycoLLM), best among baselines in 3/4 configurations
- DAIC-WOZ: 0.4910 vs best baseline 0.4864
- Dynamic Evolution ablation: -8.2% F1 (D4), -10.2% F1 (DAIC)
- Long-term memory ablation: "significantly reduced accuracy"
- RSD <10% across GPT-4o-mini and Llama-3.1-8B backbones

**Design Rationale:** Multi-session dynamics require memory that spans sessions with controlled evolution. Tertiary structure mirrors human memory stages: immediate (working), recent (episodic), persistent (semantic).

**Transferable Idea for Lyra (SS4.2 Memory):**
1. Tertiary memory architecture (real-time + short-term + long-term) is a more granular and practical design than the binary short/long split.
2. The emotion/state perturbation mechanism (avoiding fixed patterns via controlled randomness) is applicable for making Lyra's agent behavior more natural.
3. The "chain" abstraction for multi-step cognitive state management maps to Lyra's workflow state tracking.
4. Agentic RAG (LLM decides when to retrieve long-term memory) is a more intelligent retrieval trigger than fixed thresholds.

---

## DAVIS: Knowledge-Graph Inner Monologue

**URL:** https://arxiv.org/abs/2410.09252 | Venue: EMNLP 2025 Findings

**Core Mechanism:** A scientific agent for lab tasks with:
- **Knowledge-graph memory backbone**: structured + temporal memory for model-based planning
- **Multi-turn interactive retrieval**: An "inner monologue" process analogous to human reasoning, replacing single-pass RAG with iterative retrieval guided by intermediate reasoning
- **World Model**: Model-based planning component that uses the knowledge graph for simulation

**Results (real numbers):**
- ScienceWorld: "substantially improved performance" on 8/9 elementary science subjects
- HotpotQA: "competitive performance" on multi-hop QA
- (Exact numbers not available from abstract page)

**Transferable Idea for Lyra (SS4.2 + SS4.3):**
1. Multi-turn interactive retrieval (inner monologue) is superior to single-pass RAG. Lyra's retrieval should allow iterative refinement based on partial reasoning.
2. Knowledge graphs as the backbone for temporal + structured memory combines Zep/Graphiti's relational approach with temporal awareness.
3. World Model + memory enables planning in partially known environments -- directly applicable to Lyra's plan decomposition.

---

## MSI-Agent: Multi-Scale Insight

**URL:** https://arxiv.org/abs/2409.16686 | Venue: EMNLP 2024

**Core Mechanism:** Three-part insight management:
- **Experience Selector**: Chooses relevant past experiences
- **Insight Generator**: Produces task-specific + high-level insight from experiences
- **Insight Selector**: Retrieves pertinent insight from database to guide decisions

**Results (real numbers):**
- "Outperforms another insight strategy when planning by GPT-3.5"
- "Better robustness when facing domain-shifting scenarios"
- (Exact numbers not available from abstract page)

**Transferable Idea for Lyra (SS4.2 Memory):**
1. The separation between task-specific insight and high-level/general insight is crucial. Lyra's memory should distinguish local task knowledge from transferable principles.
2. Seed experience selection strategy (which experiences to learn from) is a non-trivial design choice with significant impact.

---

## Field-Theoretic Memory for AI Agents (Mitra)

**URL:** https://arxiv.org/abs/2602.21220

**Core Mechanism:** Treats agent memory as continuous scalar fields on a 2D semantic manifold, evolving via partial differential equations:

```
field PDE:   d phi/dt = D*Laplacian(phi) - lambda*phi + S(x,y,t)
importance:  dI/dt = -beta*I + gamma*A(x,y,t)
retrieval:   score(m) = w1*sim(q,e_m) + w2*|phi(x_m,y_m)| + w3*I_m + w4*R_m
```

- **Diffusion** (D*Laplacian): Memories spread to semantically neighboring regions
- **Thermodynamic decay** (lambda*phi): Exponential forgetting matching Ebbinghaus curves
- **Importance-weighted dynamics** (alpha*I): High-importance regions diffuse/decay slower
- **Multi-agent field coupling**: Agents' fields drive toward each other (knowledge transfer without communication)
- **Sparse representation**: 1000x1000 grid -> O(S) where S=active cells, pruned at |phi|<1e-6
- **JAX acceleration**: 518x speedup over interpreted Python
- **Numerical methods**: 5-point stencil Laplacian, Forward Euler time stepping, CFL condition

**Results (real numbers):**
- LongMemEval multi-session reasoning F1: +116% (p<0.01, d=3.06)
- Temporal reasoning F1: +43.8% (p<0.001, d=9.21)
- Knowledge-update recall: +27.8% (p<0.001, d=5.00)
- Multi-agent collective intelligence: >99.8% (2, 4, 8 agents all near-perfect)
- Field evolution most critical component (-45.2% retention when ablated)
- Retrieval latency: 22.5ms (baseline 27.0ms) -- 0.83x faster
- Memory overhead: 7.02MB (baseline 1.01MB) -- 6.9x more at 10K memories
- Processing time: 19.8ms/op (baseline 2.1ms/op) -- 9.4x slower

**Trade-offs:**
- Higher memory overhead (6.9x) and processing time (9.4x) vs vector DB baseline
- Parameter sensitivity: retrieval weights need domain tuning
- Single-session tasks: minimal benefit, not worth the overhead
- Adversarial questions: identical performance to baseline (field dynamics don't distinguish answerable from unanswerable)
- Importance weighting may over-emphasize user messages (-33.3% on single-session-assistant)

**Design Rationale:** Discrete memory architectures suffer from binary retention (present/absent). Continuous fields enable partial influence, natural forgetting curves, and emergent collective behavior without explicit communication. "Memories gain advantages not from being stored differently, but from evolving continuously between storage and retrieval."

**Transferable Idea for Lyra (SS4.2 Memory):**
1. Continuous field dynamics are a genuinely novel direction but likely too complex for Lyra's initial v2. The core insight -- continuous evolution between storage and retrieval -- can be approximated with tiered decay schedules.
2. Importance-weighted memory dynamics (high-importance memories persist longer) should be adopted for Lyra's memory retention policy.
3. Multi-agent field coupling (agents' fields converge without explicit coordination) is an intriguing model for Lyra's subagent shared context -- but requires significant infrastructure.
4. The sparse representation technique (O(S) where S=active cells) is essential for any field-based approach.
5. The retrieval scoring formula (combining similarity, field amplitude, importance, recency) is more nuanced than pure vector similarity.

**Gap vs Baseline:** This is far ahead of Lyra's current flat memory. Even a simplified version (importance-weighted decay + multi-factor retrieval scoring) would represent major progress.

---

## COMPASS: Hierarchical Context Management

**URL:** https://arxiv.org/abs/2510.08790

**Core Mechanism:** Three-component hierarchical framework for context management:
- **Main Agent**: Tactical, step-by-step reasoning and tool use (execution engine)
- **Meta-Thinker**: Supervisory role -- monitors main agent's trajectory, issues strategic interventions when progress stalls, errors accumulate, or agent loses coherence
- **Context Manager**: Builds and maintains concise, relevant progress briefs tailored to each reasoning stage. Distills interaction history and highlights critical evidence.

Extensions: **Test-time scaling** matches DeepResearch agents; **Post-training pipeline** delegates context management to smaller models.

**Results (real numbers):**
- GAIA + BrowseComp + Humanity's Last Exam: up to +20% relative accuracy improvement over single- and multi-agent baselines
- Test-time scaling matches established DeepResearch agent performance

**Transferable Idea for Lyra (SS4.3 Context):**
1. Three-component separation (executor + supervisor + context manager) is the most practical architecture for Lyra. It decouples concerns that are currently conflated.
2. The Context Manager role (producing stage-specific progress briefs) is a concrete job description for a Lyra module.
3. The Meta-Thinker pattern (strategic override without holding full history) solves the "lost in the middle" problem without expanding context windows.
4. Post-training pipeline (smaller models for context management) aligns with ACON's distillation findings.

---

## ExtAgents: Scaling External Knowledge Beyond Context Windows via Multi-Agent

**URL:** https://arxiv.org/abs/2505.21471 | Venue: ACL 2026

**Core Mechanism:** Multi-agent framework for distributing external knowledge across agents, overcoming context window limits without longer-context training. Identifies two core bottlenecks in existing agent orchestration for distributed knowledge processing and addresses them with a new orchestration design.

**Results (real numbers):**
- Enhanced multi-hop QA benchmark (infBench+): "significantly enhances performance over existing non-training methods"
- Maintains efficiency via high parallelism
- Works both within AND beyond native context window limits
- (Exact numbers not available from abstract page)

**Transferable Idea for Lyra (SS4.3 Context):**
1. Distributed knowledge processing across multiple agents is the ultimate scale-out strategy for context management.
2. High parallelism preserving efficiency is a critical design requirement for Lyra's multi-agent context.

---

## CFGM: Coarse-to-Fine Grounded Memory

**URL:** https://arxiv.org/abs/2508.15305 | Venue: EMNLP 2025

**Core Mechanism:** Two-phase memory grounding:
- **Training phase**: Ground environment into coarse-grained focus points -> collect experiences -> extract actionable hybrid-grained tips from each experience
- **Inference phase**: Retrieve relevant experiences+tips -> when anomalies arise, ground current situation into fine-grained key info -> self-QA reflection -> plan correction

Granularity levels: coarse-grained (focus points), hybrid-grained (actionable tips), fine-grained (key info for anomaly handling).

**Transferable Idea for Lyra (SS4.2 + SS4.3):**
1. Multi-granularity memory (coarse -> fine) allows flexible adaptation -- coarse for broad guidance, fine for precise correction.
2. Self-QA reflection at inference time (based on fine-grained grounding) is directly applicable as Lyra's plan correction mechanism.
3. The train/inference phase separation mirrors Lyra's offline training vs online execution.
4. Anomaly detection triggering fine-grained retrieval is a superior trigger strategy than periodic or threshold-based retrieval.

---

## MemAgent (ICLR 2026 Oral)

**URL:** https://openreview.net/forum?id=k5nIOvYGCL

**Core Mechanism:** Processes long documents segment-by-segment with an overwrite memory strategy. Trained end-to-end via an extension of the DAPO RL algorithm. Uses independent-context multi-conversation generation for training -- learning memory operations across multiple separate conversational contexts rather than one continuous dialogue.

**Results (real numbers):**
- Training: 8K tokens; Extrapolation: 3.5M tokens
- <10% performance loss at 3.5M
- 512K Needle-in-a-Haystack: >95% accuracy

**Transferable Idea for Lyra (SS4.2 Memory):**
1. The segment-by-segment processing + overwrite strategy is the most practical approach for Lyra handling large documents within bounded context.
2. RL-based training for memory operations (when to retain vs overwrite) is a learnable alternative to hand-crafted heuristics.
3. The >95% NIAH at 512K demonstrates that trained memory can match or exceed long-context models on factual recall.

---

## PISA: Pragmatic Psych-Inspired Unified Memory System

**URL:** https://arxiv.org/abs/2510.15966

**Core Mechanism:** Piaget-inspired memory system with:
- **Trimodal schema adaptation**: Schema Updation (incremental refinement), Schema Evolution (restructuring), Schema Creation (novel schemas for unassimilable info)
- **Hybrid memory access**: Symbolic reasoning (rule-based) + neural retrieval (embedding similarity)
- **Empirically validated** on LOCOMO + novel AggQA benchmark

**Transferable Idea for Lyra (SS4.2 Memory):**
1. The trimodal schema adaptation (update/evolve/create) provides a principled way to handle novel vs familiar information.
2. Symbolic + neural hybrid retrieval trades complexity for precision -- worth adopting for Lyra's high-stakes memory queries.
3. Schema creation (triggered when info "cannot be assimilated") is a concrete novelty-detection trigger pattern.

---

## Memory Survey (Du, 2026)

**URL:** https://arxiv.org/abs/2603.07670

**Core Mechanism:** Comprehensive survey of agent memory (2022-2026) with:
- **Formalization**: Memory as write-manage-read loop coupled with perception and action
- **Three-dimensional taxonomy**: Temporal scope x Representational substrate x Control policy
- **Five mechanism families**:
  1. Context-resident compression
  2. Retrieval-augmented stores
  3. Reflective self-improvement
  4. Hierarchical virtual context
  5. Policy-learned management
- **Evaluation landscape**: Shift from static recall benchmarks to multi-session agentic tests
- **Open challenges**: Continual consolidation, causally grounded retrieval, trustworthy reflection, learned forgetting, multimodal embodied memory

**Transferable Idea for Lyra:**
1. The five mechanism families provide Lyra's complete design space for memory. Lyra v2 should implement at least 3 of 5.
2. The write-manage-read formalization is Lyra's unifying memory abstraction.
3. Learned forgetting (intentional, adaptive forgetting policies) is an underexplored area Lyra could pioneer.

---

## Anthropic Context Engineering

**URL:** https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

**Core Mechanism:** Practical techniques for managing LLM agent context as a "finite resource with diminishing marginal returns." Key techniques:
1. **Compaction**: Near-context-limit summarization, preserving architectural decisions + unresolved bugs + implementation details, discarding redundant tool outputs. Claude Code: passes message history to model, continues with compressed context + 5 most recently accessed files.
2. **Structured Note-Taking (Agentic Memory)**: Agent writes notes to persistent memory outside context window. Claude Code's TODO list, NOTES.md, file-based memory tool. "Claude Plays Pokemon": tracked objectives, levels gained, explored regions, combat strategies across context resets for multi-hour sequences.
3. **Sub-Agent Architectures**: Specialized agents return condensed summaries (~1000-2000 tokens) after exploring with 10K+ tokens each.
4. **Just-in-Time Context Loading**: Agents maintain lightweight identifiers and dynamically load data at runtime.
5. **Progressive Disclosure**: Agents discover context incrementally through exploration.

**Decision Framework:**
| Technique | Best For |
|-----------|----------|
| Compaction | Tasks requiring extensive back-and-forth |
| Structured Note-Taking | Iterative development with clear milestones |
| Multi-Agent | Complex research/analysis with parallel exploration |

**Transferable Idea for Lyra (SS4.3 Context):**
1. This is Lyra's primary tactical reference. Each technique maps directly to a Lyra module:
   - Compaction -> Lyra's `ContextManager.compact()`
   - Structured notes -> Lyra's `MemoryStore.working_memory` with agent write access
   - Sub-agent architectures -> Lyra's existing subagent system (already partially implemented)
   - JIT loading -> Lyra's `ToolRegistry` with lazy load
   - Progressive disclosure -> Lyra's context exploration phase
2. Compaction as the lowest-hanging optimization: clear old tool calls and results.
3. The Claude Code compaction strategy (5 most recently accessed files) is a simple, effective heuristic.
4. "Do the simplest thing that works" is the right posture for Lyra -- not over-engineering before understanding agent behavior.

---

## Awesome-Memory-for-Agents (enumeration)

**URL:** https://github.com/TsinghuaC3I/Awesome-Memory-for-Agents

Complete enumerated taxonomy with 100+ papers across:
- **Personalization**: 50+ papers (Mem0, A-MEM, Magma, O-Mem, MemRec, HiMem, SYNAPSE, TiMem, etc.)
- **Learning from Experience**: 30+ papers (ReasoningBank, MSI-Agent, SkillNet, etc.)
- **Long-horizon Agentic Task**: 20+ papers (COMPASS, ACON, CFGM, ExtAgents, MemAgent, etc.)
- **Surveys**: Memory survey (Du, 2026)
- **Benchmarks**: LOCOMO, LongMemEval, etc.
- **Products**: Mem0, Letta, Zep, MemGPT

Key entries not covered elsewhere:
- **A-MEM** (2502.12110): Agentic memory with structured note organization
- **O-Mem** (2511.13593): Omni memory -- personalization + long horizon + self-evolving
- **MAGMA** (2601.03236): Multi-graph agentic memory architecture for AI agents
- **SYNAPSE** (2601.02744): Episodic-semantic memory via spreading activation (neural-inspired)
- **TiMem** (2601.02845): Temporal-hierarchical memory consolidation for long-horizon conversations
- **Memory-T1** (2512.20092): RL for temporal reasoning in multi-session agents
- **MIRIX** (2507.07957): Multi-agent memory system
- **MemOS** (2507.03724): Memory OS for AI systems

---

# SYNTHESIS

## Highest-Priority Transfers for Lyra v2

### SS4.4 Skills -- Priority Order:
1. **Skill Optimization Loop** (from SkillOpt): rollout -> reflect -> aggregate -> select -> update -> evaluate. This is the single highest-impact addition. Implements textual learning rate, rejected-edit buffer, and validation gates.
2. **5-Dimension Evaluation** (from SkillNet): Safety/Completeness/Executability/Maintainability/Cost-Awareness quality gates before skills enter Lyra's registry.
3. **Skill Relationship Graph** (from SkillNet): `similar_to`/`compose_with`/`depend_on`/`belong_to` relationships for DAG routing and dependency resolution.
4. **Auto-Creation from Traces** (from SkillNet + SkillOS): Convert agent execution trajectories into reusable skill packages.
5. **Auto-Triggering Bootstrap** (from Superpowers): Meta-skill that discovers and activates other skills based on context keywords.
6. **Orchestrator + Sub-Skills** (from claude-skills): Decomposable skill hierarchies for complex workflows.
7. **Knowledge Flow Architecture** (from claude-skills): references -> SKILL.md -> scripts -> assets pipeline.
8. **Versioned Releases with Rollback** (from SkillOS): Version management for skills.
9. **Multi-Platform Export** (from multica-ai): Same skill content packaged for Claude Code, Cursor, Gemini.

### SS4.2 Memory -- Priority Order:
1. **Three-Tier Memory** (from Letta + AnnaAgent): Core (in-context blocks) + Short-term (recent session) + Long-term (persistent knowledge base).
2. **Self-Editing Memory Tools** (from Letta): Agent can `memory_append`, `memory_replace`, `memory_search` via tool calls.
3. **Hybrid Retrieval Scoring** (from Mem0 + Field-Theoretic): Embedding similarity + BM25 keyword + entity boost + recency + importance weight.
4. **Graph-Based Relational Memory** (from Zep Graphiti): Entity nodes, episodic edges, temporal connections, community summaries.
5. **Importance-Weighted Retention Policy** (from Field-Theoretic): High-importance memories persist longer; decay follows schedule.
6. **Multi-Granularity Memory** (from CFGM): Coarse (focus points) -> hybrid (tips) -> fine (key info for anomaly correction).
7. **Tertiary Memory Scheduling** (from AnnaAgent): Real-time + short-term + long-term with different retrieval triggers.

### SS4.3 Context -- Priority Order:
1. **Two-Level Adaptive Compression** (from ACON): Separate history + observation compressors, threshold-triggered, natural-language-optimized.
2. **Compaction Strategy** (from Anthropic): Summarize near context limit, preserve decisions + bugs + implementation, discard tool outputs.
3. **Structured Note-Taking** (from Anthropic): Agent-writable persistent notes outside context window.
4. **Hierarchical Context Management** (from COMPASS): Main Agent (executor) + Meta-Thinker (supervisor) + Context Manager (brief writer).
5. **Context Budget Tracking** (from Letta): Track 15+ token categories, enable agent to manage its own budget.
6. **Shell/File Output Compression** (from lean-ctx): Map-mode file reads, compressed CLI output.
7. **Segment-by-Segment Processing** (from MemAgent): Process long docs in segments with bounded context.

## Baseline Gaps Summary

| Capability | Lyra Current | State of the Art | Gap |
|-----------|-------------|------------------|-----|
| Skill creation | Manual writing | Auto from trajectories, repos, docs, prompts (SkillNet) | Critical |
| Skill evaluation | None | 5-dimension LLM judge + sandbox execution (SkillNet) | Critical |
| Skill optimization | Static | Full training loop with epochs, learning rates, validation (SkillOpt) | Critical |
| Skill auto-trigger | Manual invocation | Context-keyword-based auto-triggering (Superpowers) | Major |
| Skill relationships | Flat catalog | Typed relationship graph (SkillNet) | Major |
| Memory tiers | Single flat store | Three-tier (core/short/long) + graph + field (Letta/Mem0/Graphiti) | Critical |
| Memory self-editing | None | Tool-call-based append/replace/search (Letta) | Critical |
| Memory retrieval | Simple vector | Hybrid scoring + graph distance + reranker (Mem0/Graphiti) | Major |
| Context compression | None | Adaptive two-level optimization (ACON) | Critical |
| Context management | All-in-one agent | Hierarchical executor/supervisor/manager (COMPASS) | Major |
| Context budget | None | 15-category token tracking (Letta) | Major |

## Recommended Architecture Approach

Rather than implementing all capabilities from scratch, Lyra should:

1. **Adopt SkillOpt's training loop** as the canonical skill optimization pipeline. This is the single highest-impact addition.
2. **Adopt ACON's compression architecture** (two separate compressors, threshold-triggered, trained via contrastive optimization) as the context management backbone.
3. **Adopt Letta's three-tier memory** (core/recall/archival) with the Mem0 API abstraction (add/search/update/delete).
4. **Adopt Graphiti's graph-based relational memory** as an optional enhancement layer for agents that benefit from structured knowledge.
5. **Adopt Superpowers' auto-triggering bootstrap** as the skill activation mechanism.
6. **Adopt COMPASS's hierarchical context management** (Main Agent + Meta-Thinker + Context Manager) as the long-horizon coordination pattern.

The integration priority should be: (a) memory tiering + self-editing, (b) adaptive compression, (c) skill optimization loop, (d) graph-based retrieval, (e) hierarchical context management, (f) auto-triggering skills.

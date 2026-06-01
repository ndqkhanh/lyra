# Deep Research & MCP Research Findings (§3.19)

**Research Date**: 2026-05-31  
**Sources**: 18 URLs from source-ledger rows 269-286  
**Coverage**: Complete (18/18)

---

## Summary Table

| # | Source | Capability | Mechanism | Transferable Pattern | Impact | Effort | Tier |
|---|--------|------------|-----------|---------------------|--------|--------|------|
| 1 | [GPT Researcher](https://github.com/assafelovic/gpt-researcher) | Autonomous deep research producing 2,000+ word reports with citations from 20+ sources; tree-like exploration with configurable depth/breadth | Planner-executor-publisher pattern: planner generates research questions, parallel executors gather info per question with JS-enabled scraping, publisher aggregates filtered summaries. Maintains memory/context throughout. Supports web + local docs (PDF, CSV, Excel, etc.) | Multi-agent decomposition with specialized roles (planning/execution/synthesis); recursive exploration with smart context management; hybrid retrieval (web + MCP); source aggregation for bias reduction (more sites = less incorrect data) | 5 | 3 | BREAKTHROUGH |
| 2 | [Open Deep Research](https://github.com/langchain-ai/open_deep_research) | Automated deep research achieving #6 on Deep Research Bench (0.4344 RACE score); multi-provider LLM support; 22 domain coverage | Multi-stage pipeline: search agent (research LLM) → summarization model → compression model → final report model. Task-specific model allocation optimizes cost/performance. Configurable search_api and mcp_config for tool swapping | Task-specific model allocation (different models for summarization vs synthesis); configurable tool integration without architectural changes; evaluation-driven development with 100 PhD-level tasks; legacy pattern preservation for reference architectures | 4 | 3 | HIGH |
| 3 | [Tongyi DeepResearch](https://github.com/Alibaba-NLP/DeepResearch) | Long-horizon information-seeking for complex research; 30.5B params (3.3B activated per token); multi-step web search + document analysis + reasoning | Data synthesis pipeline (fully automatic agentic pre-training/SFT/RL); continual pre-training on agentic interaction data; Group Relative Policy Optimization with token-level gradients. Dual inference modes: ReAct + "heavy" test-time scaling | Synthetic agentic data generation + continual pre-training + on-policy RL creates autonomous navigation capability; dual inference modes (intrinsic vs maximum performance); modular tool integration via env vars; 128K context with auto-compaction | 5 | 5 | BREAKTHROUGH |
| 4 | [DeepResearch Paper](https://arxiv.org/abs/2510.24701) | SOTA on research benchmarks (Humanity's Last Exam, BrowseComp, WebWalkerQA, FRAMES); sparse 30.5B architecture with 3.3B activation | Agentic mid-training + agentic post-training for scalable reasoning; fully automatic data synthesis without human annotation; customized environments per training stage | Staged training approach (separate mid/post-training for agentic behavior); scalable synthetic data without annotation; sparse activation for efficient inference; end-to-end agentic training optimizing for autonomous multi-step completion | 4 | 4 | HIGH |
| 5 | [IterResearch Paper](https://arxiv.org/abs/2511.07327) | Addresses context suffocation in long-horizon research; interaction scaling to 2048 steps (3.5% → 42.5% performance improvement) | MDP-inspired design with strategic workspace reconstruction; maintains evolving report as memory with periodic synthesis; Efficiency-Aware Policy Optimization with geometric reward discounting; adaptive downsampling for stable distributed training | Periodic synthesis into persistent report structure (vs linear accumulation); iterative refinement cycles (exploration → synthesis → reconstruction); dual-mode utility (trained agent + prompting strategy improving frontier models by 19.2pp); efficiency incentives in reward structure | 5 | 4 | BREAKTHROUGH |
| 6 | [Agentic Reasoning Framework](https://arxiv.org/abs/2502.04644) | SOTA among public models, comparable to OpenAI Deep Research; integrates external tool-using agents for complex problems | Mind-Map agent constructs knowledge graph for reasoning context + logical relationships; Web-Search agent with optimized search; dynamic tool selection (web search, code execution, structured memory); deployed on DeepSeek-R1 | Knowledge graphs for context/logical relationships during multi-step reasoning; separated concerns (dedicated agents for search/execution/memory); structured memory prevents context loss; dynamic tool selection based on problem requirements; multi-agent composition vs monolithic reasoning | 5 | 4 | BREAKTHROUGH |
| 7 | [MCP Protocol](https://github.com/modelcontextprotocol/modelcontextprotocol) | Open protocol enabling AI apps to connect with external data sources/tools; standardized interface for databases, APIs, file systems, services | Client-server architecture: servers expose resources/tools/prompts, clients make requests via JSON-RPC over stdio/HTTP+SSE. Capability negotiation during init; resource discovery; tool invocation with structured params; prompt template retrieval | Server-side tool exposure with schemas; capability-based discovery; stateless requests with context in params; schema-driven validation (TypeScript/JSON Schema); transport flexibility (stdio for local, HTTP/SSE for remote) | 5 | 3 | BREAKTHROUGH |
| 8 | [MCP Servers](https://github.com/modelcontextprotocol/servers) | Reference implementations: Everything, Fetch, Filesystem, Git, Memory, Sequential Thinking, Time. 10 language SDKs (C#, Go, Java, Kotlin, PHP, Python, Ruby, Rust, Swift, TypeScript) | Servers run via npx (TypeScript) or uvx/pip (Python). Connect through client config (e.g., Claude Desktop mcpServers JSON). Filesystem demonstrates configurable access controls | Reference implementations as teaching tools; SDK-based development per language; secure by design (access controls); specialized capabilities per domain; environment configuration for sensitive data; not production-ready (educational examples) | 4 | 2 | HIGH |
| 9 | [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) | Agents write code instead of direct tool calls; 98.7% reduction in token usage; efficient data processing with intermediate results in execution env | Present MCP servers as code APIs via filesystem structure; each tool = importable function; agent discovers tools by exploring filesystem, reads only needed definitions. Progressive disclosure via search_tools with detail levels | Reduced context consumption (load only needed tools); intermediate results stay in execution env; progressive disclosure (search then load); state management via Skills (saved functions for reuse); sandboxing + resource limits + monitoring required | 5 | 4 | BREAKTHROUGH |
| 10 | [OpenHands](https://github.com/All-Hands-AI/OpenHands) | AI-driven development platform with SDK, CLI, GUI, Cloud/Enterprise; SWEBench 77.6 score; autonomous code generation, multi-file modifications, terminal execution | Modular design: Python SDK core engine powers all interfaces; Docker containerization; REST API + React SPA; Kubernetes for enterprise; LLM agnostic (Claude, GPT, etc.) | Layered architecture (core SDK separate from UIs); multiple consumption models (CLI/GUI/API) sharing backend; LLM agnostic design; evaluation-driven development (public benchmarks); progressive deployment (local → cloud → enterprise); safety through isolation (Docker); integration ecosystem (Slack, Jira, GitHub) | 5 | 4 | BREAKTHROUGH |
| 11 | [Anthropic Multi-Agent Research](https://www.anthropic.com/engineering/built-multi-agent-research-system) | Multi-agent research system for Claude; 90.2% performance improvement over single-agent Opus 4; searches web + Google Workspace + integrations | Orchestrator-worker pattern: lead agent (Opus 4) coordinates subagents (Sonnet 4). Lead uses extended thinking for planning, spawns 3-5 subagents simultaneously. Subagents use interleaved thinking after tool results. Parallel tool calling (3+ tools per subagent) | Separation of concerns (each subagent has own context/tools/trajectory); dynamic compression (subagents compress insights before returning); stateful execution with checkpoints/resume; memory persistence (plans saved to external memory at 200K tokens); citation post-processing (dedicated CitationAgent) | 5 | 5 | BREAKTHROUGH |
| 12 | [Terminal-Bench](https://github.com/laude-institute/terminal-bench) | Benchmark for AI agents on real-world terminal tasks (compiling, training models, server setup); 89 hard tasks with verification | Task dataset (instruction + test script + reference solution) + execution harness (connects LLMs to sandboxed Docker terminal). CLI: `tb run --agent terminus --model anthropic/claude-3-7-latest` | Sandboxed execution (Docker isolation for destructive ops); verification scripts (objective pass/fail); reference solutions (ground truth); versioned task sets (reproducible comparisons); structured task format; concurrent execution; adapter pattern for multiple frameworks | 4 | 3 | HIGH |
| 13 | [Terminal-Bench Paper](https://arxiv.org/abs/2601.11868) | 89 hard, real-world terminal tasks; frontier models score <65%; comprehensive verification tests per task | Each task has unique environment, human-written solution, robust testing infrastructure. Error analysis identifies improvement areas. Tasks mirror actual workflows | Realistic task design (mirror workflows); comprehensive verification (robust testing); difficulty calibration (challenge frontier systems); error analysis methodology (categorize failure modes); long-horizon evaluation (multi-step completion) | 4 | 3 | HIGH |
| 14 | [AgentBench](https://github.com/THUDM/AgentBench) | First benchmark for LLM-as-Agent across 8 environments (OS, DB, KG, DCG, LTP, ALFWorld, WebShop, Mind2Web); AgentBench FC with function-calling; integrated with AgentRL | Docker containerization for reproducible eval; workers handle concurrent execution. Dev/test splits require ~4k and ~13k generations. Resource requirements vary (webshop: 16GB RAM, 3min startup; OS/KG: <500MB, 5s startup) | Environment diversity (embodied, web, databases, knowledge, reasoning); multi-turn interaction (sustained reasoning + context management); practical deployment (Docker + workers + Redis allocation); infrastructure complexity (environment-specific services); memory/scaling challenges (leak detection) | 4 | 4 | HIGH |
| 15 | [AgentBench Paper](https://arxiv.org/abs/2308.03688) | Multi-dimensional benchmark with 8 interactive environments; top commercial LLMs show strong agent capabilities but significant disparity vs open-source ≤70B | Main obstacles: poor long-term reasoning, decision-making, instruction following. Improving instruction following + high quality multi-round alignment data improves agent performance. Code training shows ambivalent impacts | Multi-round alignment data critical for agent performance; instruction following is key bottleneck; agent evaluation requires interactive multi-step environments (not single-turn); long-term reasoning/decision-making distinct from general language understanding | 4 | 3 | HIGH |
| 16 | [GAIA Benchmark](https://arxiv.org/abs/2311.12983) | Benchmark for General AI Assistants testing reasoning, multi-modality, web browsing, tool-use; 466 questions (300 withheld for leaderboard) | Humans: 92% accuracy vs GPT-4 with plugins: 15%. Questions "conceptually simple for humans yet challenging for most advanced AIs" | Design philosophy: target tasks where average humans show robustness (not expert-level); performance gap as signal (large human-AI disparities on "simple" tasks indicate AGI progress); evaluation approach: combine reasoning + tool use + multi-modal understanding; benchmark integrity: withhold test answers | 4 | 2 | HIGH |
| 17 | [Ask-before-Plan](https://arxiv.org/abs/2406.12639) | Proactive Agent Planning framework where agents predict ambiguity, seek clarification, then plan; CEP (Clarification-Execution-Planning) with 3 specialized agents | Clarification agent + execution agent (invokes external tools) + planning agent. Trajectory tuning for clarification/execution. Memory recollection mechanism tracks conversation/interaction history | Decompose ambiguity handling (separate clarification/execution/planning); proactive information gathering (recognize insufficient context, request it); trajectory-based learning (fine-tune on complete interaction sequences); memory mechanisms (maintain conversation/environment history); multi-agent specialization | 4 | 3 | HIGH |
| 18 | [BLADE](https://arxiv.org/abs/2408.09667) | Benchmarks LM-based agents on open-ended data science tasks; 12 real research questions from scientific literature vs expert ground truth | Agents have planning, memory, code execution capabilities. LLMs alone default to basic analyses. Agents with data interaction show improved but non-optimal analytical diversity | Multi-faceted evaluation (match outputs across different valid representations); iterative integration (combine domain knowledge + statistical expertise + semantic understanding); interactive capability matters (data access improves analytical diversity beyond static knowledge) | 3 | 3 | MEDIUM |

---

## Key Patterns by Category

### Deep Research Patterns

1. **Multi-agent decomposition**: Separate planning, execution, synthesis into specialized agents (GPT Researcher, Open Deep Research)
2. **Recursive exploration**: Tree-like depth/breadth exploration with smart context management (GPT Researcher, IterResearch)
3. **Periodic synthesis**: Evolving report as memory with strategic workspace reconstruction (IterResearch)
4. **Orchestrator-worker**: Lead agent coordinates subagents with dynamic compression (Anthropic Multi-Agent Research)
5. **Knowledge graphs**: Structured memory for reasoning context and logical relationships (Agentic Reasoning Framework)
6. **Staged training**: Separate mid-training and post-training for agentic behavior (Tongyi DeepResearch)

### MCP Patterns

1. **Client-server architecture**: Servers expose resources/tools/prompts, clients make requests (MCP Protocol)
2. **Capability-based discovery**: Query what servers provide, selectively use what's needed (MCP Protocol)
3. **Schema-driven validation**: Tools declare input/output schemas for validation (MCP Protocol)
4. **Transport flexibility**: stdio for local, HTTP/SSE for remote (MCP Protocol)
5. **Code-as-API**: Present MCP servers as importable functions via filesystem (Code Execution with MCP)
6. **Progressive disclosure**: Search tools with detail levels, load only needed definitions (Code Execution with MCP)

### Coding Agent Patterns

1. **Layered architecture**: Core SDK separate from UIs (OpenHands)
2. **LLM agnostic**: Support multiple model providers (OpenHands)
3. **Progressive deployment**: Local → cloud → enterprise (OpenHands)
4. **Safety through isolation**: Docker containerization (OpenHands, Terminal-Bench)

### Benchmark Patterns

1. **Sandboxed execution**: Docker isolation for destructive operations (Terminal-Bench)
2. **Verification scripts**: Objective pass/fail signals (Terminal-Bench)
3. **Environment diversity**: Test across multiple domains (AgentBench)
4. **Multi-turn interaction**: Sustained reasoning and context management (AgentBench)
5. **Human-AI gap as signal**: Large disparities on "simple" tasks indicate AGI progress (GAIA)

---

## Transferable to Lyra

### For §4.15 Deep Research

- **Implement orchestrator-worker pattern** with lead agent + specialized subagents
- **Add periodic synthesis**: evolving report as persistent memory structure
- **Knowledge graph** for reasoning context and logical relationships
- **Recursive exploration** with configurable depth/breadth
- **Multi-agent decomposition**: separate planning, execution, synthesis
- **Dynamic compression**: subagents return condensed summaries to coordinator

### For §4.8 MCP Integration

- **Adopt client-server architecture** for tool integration
- **Implement capability-based discovery** for MCP servers
- **Schema-driven validation** for tool invocation
- **Progressive disclosure**: search then load only needed tools
- **Code-as-API presentation** for reduced token consumption (98.7% reduction)
- **Transport flexibility**: stdio for local, HTTP/SSE for remote

### For §4.6 Tools

- **Layered architecture**: core engine separate from interfaces
- **LLM agnostic design** for model flexibility
- **Docker isolation** for safety
- **Verification scripts** for objective evaluation
- **Multi-turn interaction support** for sustained reasoning

---

## Quantitative Highlights

- **Open Deep Research**: #6 on Deep Research Bench (0.4344 RACE)
- **IterResearch**: 3.5% → 42.5% with interaction scaling to 2048 steps
- **Anthropic Multi-Agent**: 90.2% improvement over single-agent Opus 4
- **Code Execution with MCP**: 98.7% token reduction
- **OpenHands**: SWEBench 77.6 score
- **Terminal-Bench**: Frontier models <65% on real-world tasks
- **GAIA**: Humans 92% vs GPT-4 with plugins 15%

---

## Implementation Recommendations

### Priority 1: MCP Integration (§4.8)

**Effort**: 3-4 weeks  
**Impact**: BREAKTHROUGH

1. Implement MCP client in Lyra core
2. Add capability-based discovery for MCP servers
3. Schema-driven validation for tool invocation
4. Progressive disclosure pattern (search → load only needed)
5. Code-as-API presentation for token efficiency

### Priority 2: Deep Research System (§4.15)

**Effort**: 6-8 weeks  
**Impact**: BREAKTHROUGH

1. Orchestrator-worker pattern with lead + subagents
2. Periodic synthesis with evolving report structure
3. Knowledge graph for reasoning context
4. Recursive exploration with depth/breadth config
5. Dynamic compression from subagents

### Priority 3: Benchmark Integration (§4.16)

**Effort**: 2-3 weeks  
**Impact**: HIGH

1. Terminal-Bench integration for evaluation
2. AgentBench for multi-environment testing
3. Sandboxed execution with Docker
4. Verification scripts for objective metrics

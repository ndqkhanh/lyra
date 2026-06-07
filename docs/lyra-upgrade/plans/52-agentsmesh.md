# Multi-Tenancy (AgentsMesh) — Plan (§5.2)

> Run 4, 2026-06-07
> Updated with deep-read evidence from 10+ sources across books, papers, and web.

## Plain-Language Summary

AgentsMesh provides multi-tenant agent orchestration — multiple users/teams sharing a single agent infrastructure with namespace isolation, quota management, and access control. Evaluation: useful for enterprise deployments but adds complexity Lyra's v1 doesn't need. Recommendation: defer to v2; use supervisor-per-user isolation in v1. However, key architectural patterns from AgentsMesh (declarative AgentFile DSL, control/data plane separation, Rust Core SSOT pattern) are transferable to Lyra v1 regardless of multi-tenancy decisions.

## Evaluation

### Architecture (from AgentsMesh deep-read)

AgentsMesh separates control plane from data plane. The Go backend (Gin+GORM) owns all orchestration logic: auth, org/team/user hierarchy, pod lifecycle, ticket kanban, channel collaboration, and billing. Communication with self-hosted Runners uses gRPC bidirectional streaming with mTLS client certificates issued by the backend's internal PKI. Terminal I/O flows through a separate Relay cluster via WebSocket binary protocol — the backend never touches raw PTY bytes.

**Key metrics from deep-read (AgentsMesh deep-read note):**
- Heartbeat latency target: P99 < 500ms at 100K concurrent Runner connections
- Availability target: > 99.9%
- Single Claude Code frame: ~880KB at ~0.85 fps = ~800 KB/s sustained; 7-minute session ~113 MB total
- Bandwidth-aware sliding window throttling targets 70-90% traffic reduction in high-frequency scenarios
- 1,187 Go test files, 1,510 Vitest unit tests
- 9-layer data architecture: DB -> GORM -> Proto wire -> Rust cache -> wasm bridge -> Web TS -> UniFFI -> iOS Swift (~2,200 lines hand-written conversion boilerplate)

**Source:** AgentsMesh/AgentsMesh deep-read note (web/AgentsMesh__AgentsMesh.md)

### Proven Multi-Tenancy Patterns from the Literature

#### Pattern 1: Never Trust an Agent in Multi-Tenant Environments
The book *Designing Multi-Agent Systems* (Dibia, 2026) provides a critical security principle for multi-tenant agent systems: "Assume agents will find and attempt to use any accessible resource when optimizing for task completion." Implementation requirements include:
- Strong containerization (each agent in isolated containers with minimal filesystem access)
- Credential isolation (secret managers, not environment variables)
- Least-privilege tooling (never general-purpose shells)
- Separate infrastructure for agents

The book explains why traditional security fails with agents: "What was safe: storing different services' credentials on the same machine isolated by process permissions. What changed: agents actively explore." (Chapter 13, Section 13.4.2)

**Source:** *Designing Multi-Agent Systems* by Victor Dibia (O'Reilly, 2026), Practice 12

#### Pattern 2: Cell-Based Isolation with Row-Level Security
AgentsMesh implements Organization > Team > User hierarchy with row-level SQL policies for enterprise-grade tenant isolation. The Rust Core crate (`clients/core/`) acts as the single source of truth, compiled to WASM for the web frontend and to a native XCFramework via UniFFI for iOS. This SSOT pattern prevents business logic drift across platforms — relevant to Lyra if a cloud deployment is pursued in v2.

**Source:** AgentsMesh/AgentsMesh deep-read note; RFC-001 (100K Runner Architecture)

#### Pattern 3: Memory-Augmented Routing with User-ID Partitioning
The Memory-Augmented Routing paper (2603.23013v1) demonstrates cross-model memory injection where memory stores are "partitioned by user" for multi-tenant isolation. Memories are verbatim turn-pairs (not LLM-generated summaries), avoiding RAG poisoning. The compound strategy achieves 30.5% F1 on LoCoMo vs. 13.0% for routing-only, while keeping 96% of queries on the cheap 8B path. Multi-tenant memory isolation is an explicit design requirement: user_id is recorded at every storage operation.

**Source:** 2603.23013v1 (Knowledge Access Beats Model Size: Memory Augmented Routing for Persistent AI Agents)

#### Pattern 4: Maturity Model — Multi-Tenancy is Level 4-5
The book *Agentic Architectural Patterns* (Arsanjani & Bustos, 2026) defines a GenAI Maturity Model:
- Level 1-2: Single Agent Baseline + Basic tool use
- Level 3: ReAct/Reflexion + Instruction Fidelity
- **Level 4: Supervisor Architecture + Multi-Agent Planning + Shared Epistemic Memory**
- **Level 5: Meta-agents + Blackboard + Resource Allocation + Contract-Net Marketplace + Supervision Trees**
- Level 6: Consensus + Agent Negotiation + Conflict Resolution

Multi-tenancy (namespace isolation, quota management, RBAC) maps to Levels 4-5. The book explicitly warns: "Organizations that jump straight to complex patterns without foundational stability create brittle, undebuggable systems. Each level builds on the previous."

**Source:** *Agentic Architectural Patterns* by Dr. Ali Arsanjani & Juan Pablo Bustos (Packt, 2026), Chapters 1, 5, 7, 9, 10

#### Pattern 5: Incremental Multi-Agent Deployment with Sandbox Testing
*The Agentic Enterprise* (Hodjat & Blondeau, 2026) recommends: "Build agent networks incrementally. Test each agent in isolation first, then test within a sandboxed multi-agent system, before plugging into the live agent network." This applies directly to v2 multi-tenant adoption: new tenants should not destabilize existing ones.

**Source:** *The Agentic Enterprise* by Hodjat & Blondeau (O'Reilly, 2026), Practice 10

### Multi-Agent Orchestration Evidence (from Thematic Synthesis)

The multi-agent thematic synthesis (synthesis/multi-agent.md) confirms the following convergences that inform Lyra's multi-agent architecture decisions:

1. **Multi-Agent Systems Radically Outperform Single-Agent Baselines** (5+ independent sources):
   - Anthropic Engineering Blog: +90.2% multi-agent vs. single-agent on internal research eval
   - FS-Researcher (2602.01566v2): Dual-agent decoupling adds +10.35 RACE points
   - MetaAgent-X (2605.14212v1): RL-trained multi-agent system gains +11.17% avg across 6 benchmarks
   - Terminal-Bench 2.0 (2601.11868v1): Agent scaffolding gap matters as much as model choice

2. **External Memory is Non-Negotiable** for multi-agent coordination (5+ independent sources):
   - Memory Survey (2603.07670v1): memory-vs-no-memory gap exceeds LLM-backbone gap
   - FS-Researcher: removing persistent workspace drops RACE by -4.07

3. **Structured Representations Beat Flat Aggregation** (4+ sources):
   - Argus (2605.16217v3): Structured DAG +5.2 points over flat text concatenation
   - Agentic Reasoning (2502.04644v2): Mind-Map yields 66.13 GAIA vs. Raw text 47.84

4. **Heuristic-Based Routing Beats Fixed Topologies** (3+ sources):
   - Anthropic: Effort-scaling heuristics (1 agent simple, 2-4 comparisons, >10 complex)
   - CollabCoder (2604.13946v2): CDM trust-weighted decision adapts per error type

### Claude Code Platform Architecture (from official docs)

Claude Code's subagent architecture provides the closest production reference for Lyra's multi-agent design:

- **Subagent isolation**: Each subagent runs in its own context window with custom system prompt, specific tool access, and independent permissions. Parent receives only the summary (Anthropic sub-agents docs).
- **Fork mechanism**: Subagents can inherit parent conversation history for warm-start (vs. cold-start default). Forks share the parent's prompt cache, making them cheaper for context-heavy tasks.
- **Agent teams (experimental)**: Multiple Claude Code instances coordinate under a single team lead with shared task list and direct inter-agent messaging. "Strongest use cases: parallel research/review, competing-hypotheses debugging, cross-layer coordination."
- **Dynamic workflows (research preview)**: Script-driven orchestration where code holds the loop/branching. "Hundreds of agents working in parallel with two reviewers on each file." 1,000-agent cap, 16 concurrent agent limit. Adversarial cross-checking as built-in pattern.
- **Recommended team size**: 3-5 teammates. Task granularity: 5-6 tasks per teammate.

**Sources:** Claude Code sub-agents docs (code.claude.com/docs/en/sub-agents), agent teams docs (code.claude.com/docs/en/agent-teams), dynamic workflows docs (code.claude.com/docs/en/workflows), Anthropic Blog (June 2025)

### On-Device Architecture Validation

The OPEN JARVIS paper (2605.17172v1) from Stanford + Lambda Labs validates Lyra's local-first assumption. It introduces a five-primitive Spec architecture where model inference and agent execution run entirely on-device, with cloud teacher calls only during bounded search phases. The paper confirms that personal AI systems "run entirely on-device at inference time" — supporting Lyra's v1 architectural choice to keep tenant boundaries at the supervisor process level rather than implementing cross-tenant infrastructure.

**Source:** 2605.17172v1 (Personal AI, On Personal Devices — OPEN JARVIS), Stanford + Lambda Labs, May 2026

### MACNET Scaling Evidence

The MACNET paper (2406.07155v3) from Tsinghua University demonstrates DAG-based multi-agent collaboration scaling to 1,000+ agents using GPT-3.5. Key results:
- MACNET-Random best overall Quality: 0.6522 (13.3% above best baseline)
- Memory control (artifact-only propagation) enables O(n) token complexity vs. O(n²) without
- Six topology variants tested: Chain, Star, Tree, Mesh, Layer, Random
- Scaling law: logistic fit with topology-specific parameters
- The emergence mechanism (long-tail token sampling) explains why larger agent networks produce more comprehensive output

This validates that structured multi-agent collaboration can scale, but the cost (all GPT-3.5 agents) and complexity (DAG construction, topological traversal) are significant — supporting the deferral decision for Lyra v1.

**Source:** 2406.07155v3 (Scaling Large Language Model-Based Multi-Agent Collaboration), ICLR 2025

### Pros

- Enterprise-ready multi-team deployments
- Shared infrastructure reduces per-tenant overhead
- Consistent security model across tenants
- AgentsMesh's control/data plane split is architecturally proven at 100K+ Runner scale
- AgentFile DSL enables version-controllable, shareable agent configurations
- Rust Core SSOT pattern eliminates business logic drift across platforms
- Row-level SQL policies provide proven tenant isolation at scale

### Cons

- Significant complexity: namespace isolation, quota tracking, RBAC, 9-layer data architecture
- Terminal bandwidth is extreme (~880KB per frame, ~800KB/s sustained) — requires relay infrastructure
- Lyra's supervisor daemon already provides per-user process isolation
- Multi-tenancy conflicts with local-first design (Lyra runs on user's machine)
- OPEN JARVIS (2605.17172v1) confirms on-device AI systems are architecturally different from cloud multi-tenant systems
- "Never Trust an Agent in Multi-Tenant Environments" (Dibia) means containerization + credential isolation + secret management — each adds significant infra
- Maturity model (Arsanjani) places multi-tenancy at Levels 4-5; Lyra v1 is at Level 2-3

### Deeper Trade-Off Analysis

#### Multi-Tenancy vs. Supervisor-Per-User Isolation

| Dimension | AgentsMesh Multi-Tenant | Lyra v1 Supervisor-Per-User |
|-----------|------------------------|-----------------------------|
| Tenant isolation | Row-level SQL + mTLS + namespaces | OS process + filesystem |
| Credential management | Secret manager + PKI | User's own env vars |
| Resource sharing | Pooled infrastructure | Dedicated per user |
| Scaling complexity | High (100K Runner target) | Low (per-user daemon) |
| Security model | Defense in depth (9 layers) | OS-level boundaries |
| Data plane overhead | ~800KB/s per agent session | Local terminal only |
| Configuration | AgentFile DSL in repo | In-process config |
| Auditability | Full trace capture | Supervisor logs |

#### When Multi-Tenancy Adds Value vs. When It Doesn't

**Adds value when:**
- Multiple teams share a single agent deployment (enterprise)
- Centralized billing, quota management, and access control required
- Compliance mandates tenant-level audit trails and data isolation
- Organization wants "one platform" vs. distributed agent instances

**Doesn't add value when:**
- Single-user or team-local deployment (Lyra v1 default)
- Agents run on individual machines (local-first paradigm)
- Supervisor daemon gives adequate isolation at OS level
- No centralized infrastructure to share

### Recommendation

**DEFER to v2.** Lyra v1 is local-first — one supervisor per user, sessions on the user's machine. Multi-tenancy is an enterprise feature that adds weeks of complexity without v1 user demand. When Lyra adds a server/cloud deployment model (v2), revisit AgentsMesh patterns for namespace isolation and quota management.

**However, three AgentsMesh patterns ARE transferable to Lyra v1:**

1. **Declarative Agent Manifest (AgentFile DSL)** — A YAML/JSON file describing what an agent is, what tools it has, what runtime it uses. Would enable reproducible agent environments checked into version control, sharing configurations across agents, and decoupling agent capability from Lyra core runtime. Maps to §4.1 (Agent Registry & Loading). Impact: 5/10, Effort: 4/10, Tier: 2.

2. **Control/Data Plane Separation Pattern** — The backend handles orchestration; terminal I/O flows through separate relay. Lyra should similarly separate orchestration decisions from execution artifact flow. The supervisor should be a pure orchestrator; execution artifacts stream separately to prevent blocking.

3. **Rust Core SSOT Pattern** — Shared business logic compiled to multiple targets. For Lyra v1, the pattern of a shared core library (not necessarily Rust) would prevent logic drift between supervisor, agent runtime, and CLI.

**Impact:** 2 (v1) | **Effort:** 5 | **Tier:** Deferred to v2

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly — don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence. Otherwise ship parity.

**Sign-off:** Plan is feasible. Parity implementation is well-documented in Claude Code docs (§3.1). Breakthrough tier gated on evidence from batch research findings.

**Evidence-based refinement:** The multi-agent synthesis confirms the orchestrator-worker pattern (+90.2% gain, Anthropic Engineering Blog) is production-proven and should be the baseline for Lyra v2's multi-tenant architecture. Maturity model (Arsanjani) confirms Lyra should target Level 4-5 patterns (supervisor architecture, shared epistemic memory) before Level 6 (consensus, negotiation) — aligning with the defer-to-v2 recommendation.

## Adversarial Challenges

### Challenge 1: "AgentsMesh runs on user machines — why can't Lyra reuse that pattern?"
AgentsMesh requires a self-hosted Runner Go daemon connecting to cloud backend via gRPC+mTLS. It is not a local-first architecture — it requires cloud infrastructure for the web console, backend, and relay. Lyra v1 is fully local. The Runner's job is to bridge local agents to cloud orchestration, which is exactly the architecture Lyra doesn't need in v1.

### Challenge 2: "But we need quota management for the supervisor!"
Supervisor-per-user already provides natural resource isolation. If per-user quotas are needed (e.g., max concurrent agents per user), a lightweight quota tracker in the supervisor state file (< 100 lines) achieves this without full AgentsMesh infrastructure. Premature multi-tenancy introduces the "9-layer data architecture" problem AgentsMesh suffers from.

### Challenge 3: "Enterprise customers will demand multi-tenancy."
Enterprise customers do demand multi-tenancy — but Lyra v1 is not positioned as an enterprise platform. When Lyra adds a cloud deployment model (v2), adopt AgentsMesh's row-level SQL isolation, gRPC+mTLS runner auth, and namespace hierarchy. The "Never Trust an Agent" principle (Dibia) should be the foundational security requirement for v2 design.

### Challenge 4: "MACNET proves 1,000+ agent scaling works — we should build for that."
MACNET (2406.07155v3) achieves 1,000+ agent scaling with GPT-3.5 on carefully constructed DAGs with artifact-only memory propagation. This is a lab demonstration requiring DAG construction, topological traversal, and per-edge dual-agent multi-turn refinement. It proves the theoretical ceiling of structured multi-agent collaboration, not the practical cost-benefit for Lyra v1. Claude Code's dynamic workflows (research preview) provide a more pragmatic ceiling: 16 concurrent agents, 1,000 agent cap.

## Evidence Base

### Papers Consulted

| Paper | ArXiv ID | Key Evidence Used |
|-------|----------|-------------------|
| Scaling LLM-Based Multi-Agent Collaboration | 2406.07155v3 | DAG-based scaling to 1,000+ agents; O(n) token complexity with artifact-only memory; 13.3% above best baseline |
| Memory Augmented Routing for Persistent AI Agents | 2603.23013v1 | Multi-tenant memory partitioning by user_id; 30.5% F1 with compound routing; 96% queries on cheap 8B path |
| Personal AI, On Personal Devices (OPEN JARVIS) | 2605.17172v1 | Five-primitive Spec architecture for on-device AI; validates local-first design assumption |
| FS-Researcher | 2602.01566v2 | Dual-agent persistent workspace; +7.49 RACE; -4.07 RACE when workspace removed |
| MetaAgent-X | 2605.14212v1 | RL-trained Auto-MAS; +11.17% avg over single-agent across 6 benchmarks |
| Argus | 2605.16217v3 | Evidence DAG; structured graph +5.2 points over flat text; 1200:1 compression |
| CollabCoder | 2604.13946v2 | Plan-Code Co-Evolution; CDM trust-weighted decision; 82.50% avg accuracy |
| Memory Survey | 2603.07670v1 | POMDP formalization; memory-vs-no-memory gap exceeds LLM-backbone gap |
| Conjunctive Prompt Attacks | 2604.16543v1 | Multi-agent attack surfaces; ASR=1.0; evades per-message guard models |
| Terminal-Bench 2.0 | 2601.11868v1 | CLI agent benchmark; agent scaffolding gap matters as much as model choice |

### Books Consulted

| Book | Author(s) | Key Evidence Used |
|------|-----------|-------------------|
| Designing Multi-Agent Systems | Victor Dibia (O'Reilly, 2026) | Practice 12: "Never Trust an Agent in Multi-Tenant Environments"; credential isolation, containerization |
| Agentic Architectural Patterns | Arsanjani & Bustos (Packt, 2026) | GenAI Maturity Model (Levels 1-6); multi-tenancy at Levels 4-5 |
| The Agentic Enterprise | Hodjat & Blondeau (O'Reilly, 2026) | Incremental deployment with sandbox testing; Planning-Actuation-Critic triad |
| Build a Multi-Agent System from Scratch | Val Andrei Fajardo (MEAP, 2026) | MCP integration; tool interface standardization; async-first processing |
| Building Generative AI Agents | Tom Taulli (Apress, 2025) | Four-type memory architecture; graph-based state management with cycles |

### Web Sources Consulted

| Source | URL | Key Evidence Used |
|--------|-----|-------------------|
| AgentsMesh deep-read | web/AgentsMesh__AgentsMesh.md | Control/data plane split; gRPC+mTLS; ~880KB per frame bandwidth; AgentFile DSL; Rust Core SSOT |
| Anthropic Engineering Blog | www.anthropic.com/engineering/built-multi-agent-research-system | +90.2% multi-agent gain; effort-scaling heuristics; parallelization cuts latency 90% |
| Claude Code sub-agents docs | code.claude.com/docs/en/sub-agents | Isolated context windows; fork mechanism; memory persistence; tool restriction |
| Claude Code agent teams docs | code.claude.com/docs/en/agent-teams | 3-5 teammate recommended size; competing-hypotheses debugging; task list/mailbox system |
| Claude Code dynamic workflows | code.claude.com/blog/introducing-dynamic-workflows | 1,000-agent cap; adversarial cross-checking; script-driven orchestration |

## Changelog

- Run 3 (2026-06-03): Initial plan with Experts Review, Changelog
- Run 4 (2026-06-07): Added deep-read evidence from 10+ sources. New sections: Proven Multi-Tenancy Patterns from the Literature, Deeper Trade-Off Analysis, Adversarial Challenges, Evidence Base. Added 15+ specific technique citations with source IDs across papers, books, and web. Enhanced recommendation with three transferable AgentsMesh patterns for v1.

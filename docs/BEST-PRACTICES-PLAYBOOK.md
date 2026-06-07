# Lyra Engineering Playbook — Cross-Book Best Practices

> Synthesized from 40 AI-agent engineering books. Each practice tagged with source books + the §4 workstream it informs.

## 1. Agent Architecture

### 1.1 Hierarchical Orchestrator-Specialist Pattern
**Source:** *Agentic Architectural Patterns* (Arsanjani), *30 Agents Every AI Engineer Must Build* (Ahmad), *Designing Multi-Agent Systems* (Dibia)

- Coordinator breaks down task → Planner sequences steps → Specialist agents execute → Reviewer validates
- NEVER have one agent do everything. Decompose by role.
- → §4.13 Swarm

### 1.2 Perceive-Evaluate-Respond (PER) Loop
**Source:** *Agentic AI for Engineers* (Nagasubramanian)

- Every agent runs: Perceive (gather input) → Evaluate (reason about it) → Respond (act or report)
- The PER loop is the universal agent primitive
- → §4.14 Autonomy

### 1.3 Graduated Autonomy Levels
**Source:** *Agentic AI for Engineers* (Nagasubramanian), *Agentic AI For Dummies* (Baker)

- L1: Human-directed (agent suggests, human decides)
- L2: Human-delegated (agent decides within bounds, human reviews)
- L3: Autonomous with oversight (agent acts, human monitors)
- L4: Fully autonomous (agent acts, reports exceptions only)
- Start at L1, graduate when trust is earned
- → §4.14 Autonomy, §4.17 Safety

## 2. Memory Architecture

### 2.1 Three-Tier Memory is Universal
**Source:** *Managing Memory for AI Agents* (Labaschin), *Agentic AI Data Architectures* (Stewart), 10+ other books

- Working (context window) → Episodic (session) → Semantic (persistent)
- Every production agent system converges on this structure
- The gap between "has memory" and "no memory" often exceeds the gap between LLM backbones
- → §4.2 Memory

### 2.2 Memory Admission Control
**Source:** *Managing Memory for AI Agents* (Labaschin), *Agentic AI Data Architectures* (Stewart)

- Not everything should be remembered. Admission is an inference problem.
- Key factors: utility, confidence, novelty, recency, content type
- Content type alone explains 60%+ of admission decisions
- → §4.2 Memory

### 2.3 Distributed SQL as Memory Backbone
**Source:** *Agentic AI Data Architectures* (Stewart)

- Unified SQL + vector search eliminates fragmented memory stacks
- One database for structured metadata + embeddings + full-text
- → §4.2 Memory, §4.23 RAG

## 3. Safety and Guardrails

### 3.1 Defense-in-Depth is Non-Negotiable
**Source:** *Building Reliable AI Systems* (Shahani), *Agentic Architectural Patterns* (Arsanjani), *Claude Code Definitive Guide*

- Minimum 3 layers: prompt-level instructions + tool-level validation + runtime approval
- OPENDEV's 5-layer architecture is the reference (Prompt → Schema → Runtime → Tool → Lifecycle)
- Every layer must fail CLOSED (deny by default)
- → §4.17 Safety

### 3.2 Mutation-Gated Verification
**Source:** *Building Reliable AI Systems* (Shahani), *Agentic Architectural Patterns* (Arsanjani)

- Distinguish READ from WRITE operations
- Auto-approve reads; require verification for writes
- The single highest-leverage safety pattern
- → §4.17 Safety, §4.25 Verification

### 3.3 Skill Security Scanning
**Source:** *Agentic Architectural Patterns* (Arsanjani), *Building AI Agent Platforms* (Mahony)

- Scan every skill before install: data exfiltration, prompt injection, malicious payloads
- Declare required permissions upfront
- Verify publisher identity
- → §4.4 Skills, §4.17 Safety

## 4. Context Engineering

### 4.1 "Less is More" is Proven
**Source:** *Claude Code Definitive Guide*, *Generative AI Design Patterns* (Lakshmanan), *Agentic AI for Engineers* (Nagasubramanian)

- 400-line prompt → 15 lines improved pass rate from 83% to 92%
- 12 tools → 3 primitives improved pass rate further
- The best context engineering REMOVES content
- → §4.3 Context

### 4.2 Lazy Loading for Skills
**Source:** *Claude Code Definitive Guide*, *Patterns for Building AI Agents* (Bhagwat)

- Skills cost zero context until triggered
- Don't inline everything; reference and load on demand
- → §4.3 Context, §4.4 Skills

### 4.3 Context Delivery Format Matters
**Source:** *Generative AI Design Patterns* (Lakshmanan), *Building Generative AI Agents* (Taulli)

- Inline vs file-based delivery changes accuracy by margins comparable to swapping models
- Grep-style search often beats vector search for code
- → §4.3 Context

## 5. Multi-Agent Coordination

### 5.1 Identity-Anonymized Debate
**Source:** *Designing Multi-Agent Systems* (Dibia), *Untangling AI Agents* (Kesby)

- Agents are biased toward their own output
- Strip identity markers before peer review
- The fix is ~10 lines of code and eliminates documented bias
- → §4.13 Swarm, §4.25 Verification

### 5.2 Adversarial Review is Production-Standard
**Source:** *Building Agentic AI Systems* (Biswas), *Agentic Architectural Patterns* (Arsanjani)

- Agent A writes → Agent B reviews → Agent C orchestrates
- Never trust a single agent's output on critical decisions
- → §4.13 Swarm, §4.16 Reliability

### 5.3 Small-World Topology
**Source:** *Designing Multi-Agent Systems* (Dibia), *Patterns for Building AI Agents* (Bhagwat)

- Random/small-world communication graphs beat fully-connected for collaboration
- Regular topologies create echo chambers
- → §4.13 Swarm

## 6. Testing and Evaluation

### 6.1 Capability + Regression + Continuous Evals
**Source:** *Building Reliable AI Systems* (Shahani), *Agentic AI For Dummies* (Baker)

- Capability evals: ceiling ("how good can we be?")
- Regression evals: floor ("are we getting worse?")
- Continuous evals: drift ("are we changing?")
- 100% pass rate = useless signal (benchmarks must be hard enough to fail)
- → §4.16 Reliability

### 6.2 Agentic Benchmark Checklist
**Source:** *Building Reliable AI Systems* (Shahani), *Agentic Architectural Patterns* (Arsanjani)

- Unambiguous success criteria
- Multiple trials (pass^k, not pass@1)
- Diverse tasks (not all from same distribution)
- No contamination with training data
- → §4.16 Reliability, §7 Testing

## 7. Deployment and Operations

### 7.1 Platform Prerequisites Before Agents
**Source:** *Building Agentic AI Systems* (Biswas), *Building AI Agent Platforms* (Mahony)

- Netflix's rule: CI/CD + observability + security scanning FIRST
- Agents accelerate broken practices — fix foundations before deploying agents
- → §4.26 Harness Engineering

### 7.2 AgentOps
**Source:** *A Complete Guide to Agentforce* (Kovala), *Agentic Architectural Patterns* (Arsanjani)

- Structured logging with trace IDs across agent calls
- Health scorecard per agent (success rate, latency, cost)
- Cost tracking per session/agent/task
- → §4.16 Reliability, §4.19 Monitoring

### 7.3 Cost Governance
**Source:** *Agentic AI for Engineers* (Nagasubramanian), *Building Generative AI Agents* (Taulli)

- Per-session token budget
- Cheap model for monitoring/routing; expensive model for reasoning
- Cascade routing: try cheap first, escalate if low confidence
- → §4.5 Router, §3.22 Economics

## 8. Voice and Multimodal

### 8.1 Voice as Steering Surface, Not Primary Interface
**Source:** *Building Multimodal Generative AI* (Kar), *Agentic AI For Dummies* (Baker)

- Voice is best for: status checks, quick decisions, fleet steering
- Text is best for: complex reasoning, code review, architecture
- Voice agents retain only 30-45% of text capability
- → §4.18 Voice

### 8.2 Hybrid STT→LLM→TTS, Not Full-Duplex
**Source:** *Agentic AI For Dummies* (Baker)

- Reasoning agents need to THINK before speaking
- Full-duplex sacrifices reasoning quality for conversational feel
- Hold-to-talk is the right default for agent harnesses
- → §4.18 Voice

---

## Anti-Patterns (What NOT to Do)

1. **"One agent to rule them all"** — Single-agent monoliths fail on complex tasks. Decompose. *(Arsanjani, Ahmad, Dibia)*
2. **"Remember everything"** — Indiscriminate memory creates noise that degrades retrieval. Forget aggressively. *(Labaschin, Stewart)*
3. **"Trust the agent"** — Single-pass without verification. Always verify mutating actions. *(Shahani, Biswas)*
4. **"Ship without evals"** — You can't improve what you don't measure. *(Shahani, Baker)*
5. **"More context is better"** — Context bloat degrades performance. Less is more. *(Lakshmanan, Nagasubramanian)*
6. **"Build the agent first, add safety later"** — Safety is not a feature; it's architecture. *(Shahani, Arsanjani)*
7. **"Prompt engineering alone is enough"** — Prompt-only agents plateau. You need memory, tools, and verification. *(Ahmad, Nagasubramanian)*
8. **"One model for everything"** — Cascade routing (cheap for easy, expensive for hard) always beats single-model. *(Nagasubramanian, Taulli)*

---

*Playbook synthesized 2026-06-07 from 40 AI-agent engineering books. See `docs/lyra-upgrade/notes/books/` for chapter-level notes per book.*

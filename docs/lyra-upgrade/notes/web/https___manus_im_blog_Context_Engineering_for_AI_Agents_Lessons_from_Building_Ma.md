# Context Engineering for AI Agents: Lessons from Building Manus (Manus/Meta)

**Author:** Yichao "Peak" Ji
**Published:** July 18, 2025
**Source:** https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

---

## Core Thesis

Manus chose **context engineering** over model training -- building on frontier models' in-context learning rather than training an end-to-end agentic model. The strategic bet: stay orthogonal to underlying models, treating model progress as "the rising tide" and Manus as "the boat, not the pillar stuck to the seabed." Their iterative approach is called **"Stochastic Graduate Descent"** (architecture searching, prompt fiddling, empirical guesswork); the agent framework has been rebuilt four times.

---

## Key Technical Claims

### Principle 1: Design Around the KV-Cache
KV-cache hit rate is "the single most important metric for a production-stage AI agent."

- **100:1** average input-to-output token ratio (vastly higher than chatbots)
- Claude Sonnet pricing: cached **$0.30/MTok** vs. uncached **$3.00/MTok** -- **10x difference**
- Keep prompt prefix stable; even a single-token difference (e.g., second-precise timestamps) invalidates the cache from that token onward
- Use append-only context with deterministic JSON serialization (warns that many languages/libraries don't guarantee stable key ordering)
- Mark cache breakpoints explicitly when frameworks lack automatic incremental prefix caching
- For self-hosted vLLM: enable prefix/prompt caching and use session IDs for consistent routing across distributed workers

### Principle 2: Mask, Don't Remove
Dynamic tool addition/removal is harmful because:
1. Tool definitions sit near the context front; any change invalidates the KV-cache for all subsequent actions
2. Previous observations referencing removed tools cause schema violations or hallucinated actions

**Solution -- Context-Aware State Machine with logit masking:**
Three Hermes-format function-calling modes:
| Mode | Prefill | Behavior |
|------|---------|----------|
| Auto | `<|im_start|>assistant` | May or may not call function |
| Required | `<|im_start|>assistant<tool_call>` | Must call, any choice |
| Specified | `<|im_start|>assistant<tool_call>{"name": "browser_` | Must call from specific subset |

All browser tools prefixed `browser_`, shell tools prefixed `shell_` -- enables group-level tool selection "without using stateful logits processors."

### Principle 3: Use the File System as Context
Three pain points with large context windows:
1. Observations (web pages, PDFs) blow past context limits
2. Model performance degrades beyond certain context length
3. Long inputs remain expensive even with prefix caching

**Core insight:** The agent must predict the next action based on all prior state, and you cannot reliably predict which observation might become critical ten steps later. Irreversible compression carries risk.

**Approach:** File system treated as "the ultimate context" -- unlimited, persistent, directly operable by the agent. Compression strategies are always **restorable**: e.g., drop web page content but preserve the URL; omit document contents but retain the sandbox file path. The model learns to write and read from files on demand as structured, externalized memory.

**Speculative:** State Space Models (SSMs) might become "the real successors to Neural Turing Machines" by combining SSM efficiency with file-based externalized long-term state.

### Principle 4: Manipulate Attention Through Recitation
Manus creates a `todo.md` during complex tasks and updates it step-by-step. By constantly rewriting the todo list, the model "is reciting its objectives into the end of the context," pushing the global plan into the model's recent attention span. This addresses "lost-in-the-middle" issues using only natural language. A typical Manus task requires **~50 tool calls on average** -- a long decision loop vulnerable to topic drift.

### Principle 5: Keep the Wrong Stuff In
Error recovery is "one of the clearest indicators of true agentic behavior," yet "still underrepresented in most academic work and public benchmarks." Hiding errors removes the evidence the model needs to adapt -- seeing failed actions with stack traces lets the model implicitly update its beliefs and reduce repeat mistakes. "Failure is not the exception; it's part of the loop."

### Principle 6: Don't Get Few-Shotted
Language models are "excellent mimics." When context contains many similar past action-observation pairs, the model persists in that pattern even when suboptimal. Example: reviewing 20 resumes -- the agent falls into a rhythm, leading to drift, overgeneralization, or hallucination.

**Fix:** Introduce structured variation -- different serialization templates, alternate phrasing, minor noise in order or formatting -- to break patterns. "The more uniform your context, the more brittle your agent becomes."

---

## Architecture/Mechanism Details

- **KV-cache stability rules:** append-only, deterministic serialization, stable prefixes
- **Non-destructive constraint:** logit masking (not tool removal) with 3-mode Hermes format state machine
- **Externalized memory:** file system as context with restorable compression (drop content, keep reference)
- **Attention biasing:** recitation of objectives into recent context via todo.md
- **Learning from failure:** preserve error traces to update implicit beliefs
- **Pattern breaking:** controlled variation to prevent few-shot mimicry loops

---

## Numbers & Benchmarks

| Metric | Value |
|--------|-------|
| Input:output token ratio | ~100:1 |
| Cached vs uncached cost (Claude Sonnet) | $0.30 vs $3.00 per MTok (10x) |
| Average tool calls per task | ~50 |
| Framework rewrites | 4 |
| User base tested across | Millions |

---

## Transfer to Lyra

### One Idea: Use the File System as Ultimate Context with Restorable Compression

This is the most paradigm-shifting idea for Lyra. Currently, context management focuses on compression within the window -- truncation, summarization, or dropping low-value tokens. Manus's insight is that the filesystem itself can serve as unlimited, persistent, agent-operable memory, with compression being **restorable by reference**.

**For Lyra this means:**
- When reading web pages, drop the full content from context but keep the URL and a 1-line summary -- the agent can re-fetch on demand
- When processing documents, retain only the sandbox path -- the agent opens it when needed
- Treat all observations as having a "stub" form (small, in-context) and a "full" form (on disk, loaded by tool call)
- The agent learns a read/write discipline: it externalizes state to disk rather than letting context blo

### Workstream Route: Primary §03-context-compaction, cross-reference §02-memory

This directly extends the existing §03-context-compaction plan with a concrete mechanism (restorable compression via filesystem). It also connects to §02-memory for externalized long-term storage patterns.

### Why §03-context-compaction Specifically
The plan already addresses context window management. Adding "filesystem as context with restorable compression" gives it a concrete architectural pattern that is both cost-efficient (huge savings on token transmission) and scalable (no effective window limit for observations). The secondary connection to §02-memory provides the persistence layer for cross-session state.

---

*Rigor note prepared 2026-06-07*

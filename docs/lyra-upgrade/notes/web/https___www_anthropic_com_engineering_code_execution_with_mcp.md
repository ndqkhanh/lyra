# Code execution with MCP: Building more efficient agents (Anthropic Engineering Blog)

**URL:** https://www.anthropic.com/engineering/code-execution-with-mcp
**Authors:** Adam Jones, Conor Kelly
**Published:** November 4, 2025
**Source:** Anthropic / Engineering at Anthropic

---

## Key Technical Claims

1. **Tool definition loading is the dominant context cost.** Loading all MCP tool definitions upfront forces agents to process "hundreds of thousands of tokens before reading a request." The quantitative anchor: loading 150,000 tokens of tool definitions can be reduced to 2,000 tokens with on-demand discovery (98.7% savings).

2. **Intermediate tool results compound the waste.** Every output from every tool call flows back through the model. A 2-hour meeting transcript (~50,000 tokens) downloaded from Google Drive and forwarded to Salesforce passes through context twice. Large documents can exceed context windows entirely.

3. **Copypasta errors are real.** Models "may be more likely to make mistakes when copying data between tool calls" -- an observation that justifies keeping intermediate results inside a code runtime rather than round-tripping through the LLM.

4. **LLMs write code well; lean into it.** The core design claim: LLMs are adept at writing code, so present MCP servers as code APIs (TypeScript wrappers in a filesystem tree) rather than discrete tool-calling primitives. The model writes JavaScript/TypeScript that imports and calls these wrappers inside a secure sandbox.

---

## Architecture / Mechanism Details

### Tool organization: filesystem-based progressive disclosure

Tools live as a directory tree per server:

```
servers/
├── google-drive/
│   ├── getDocument.ts
│   ├── ... (per-tool files)
│   └── index.ts
├── salesforce/
│   └── ...
```

Each `.ts` file wraps a generic `callMCPTool` function with typed inputs/outputs. The agent discovers tools by listing `./servers/` and reading specific files on demand rather than loading everything into context.

### Execution model: agent writes code, runtime executes it

Instead of the model issuing discrete tool calls (one per turn, results back via context), the model generates a script that chains multiple operations together. The script runs in a secure sandbox. Only the final output (or explicitly logged intermediate values) returns to the model.

### Six named benefits

| # | Benefit | How it works |
|---|---------|-------------|
| 1 | Progressive disclosure | Navigate filesystem or use `search_tools` with detail levels to load only relevant tool definitions |
| 2 | Context-efficient results | Filter, aggregate, join, and extract fields in code before returning only what the model needs |
| 3 | Powerful control flow | Loops, conditionals, error handling in standard code -- saves time-to-first-token vs. model evaluating each branch |
| 4 | Privacy-preserving operations | Intermediate data stays in the runtime; only explicitly logged values reach the model. Supports automatic PII tokenization (e.g., `[EMAIL_1]` untokenized at call time) |
| 5 | State persistence & skills | Write intermediate results to filesystem; persist reusable code as functions; `SKILL.md` for structured capability references |
| 6 | Reduced cost & latency | Token savings of 98.7% on tool definitions, plus reduced round-trips from chained operations |

### Caveats and trade-offs

- Requires a secure execution environment with sandboxing
- Needs resource limits and monitoring (CPU, memory, timeout)
- Adds operational overhead vs. direct tool calls
- Benefits must be weighed against implementation costs

### Design kinship

Cloudflare published a similar approach under the term "Code Mode." Both teams independently converged on the same architecture: the model writes code, the runtime executes it, and only relevant results surface back to the LLM.

---

## Numbers & Benchmarks

| Metric | Value |
|--------|-------|
| Tool definition token reduction | 150,000 tokens -> 2,000 tokens |
| Percent savings on tool loading | 98.7% |
| Extra tokens for 2-hr meeting through context twice | ~50,000 tokens |
| Spreadsheet rows visible to model after filter | 5 rows (down from 10,000) |
| Community MCP servers built since Nov 2024 | "Thousands" |
| Scale mentioned | "Hundreds or thousands of tools across dozens of MCP servers" |

---

## Transfer to Lyra

### One transferable idea

**Code-first tool orchestration with progressive loading.**

Lyra's current agent loop (as documented in the ARCHITECTURE-DEBATE.md / MASTER-PLAN.md documents) loads all tool definitions upfront and round-trips every intermediate result through the model. This is exactly the pattern the Anthropic post identifies as the core inefficiency.

For Lyra, the actionable pattern: instead of declaring every tool in the system prompt or tool-use block, organize tools into a discoverable filesystem tree with typed wrappers. The agent navigates the tree to load only the tools relevant to the current task (progressive disclosure). Tool results are filtered/aggregated in a code runtime before returning to the LLM.

### Workstream route

**Section 4.x: Agent Loop Orchestration** (specifically 4.2: Tool Execution/Context Management).

This maps cleanly to Lyra's existing conversation loop, particularly the tool-use and result-processing phases. The code-execution model replaces the current "call tool -> return result to LLM -> call next tool" sequential pattern with a "generate script -> execute in sandbox -> return filtered results" batched pattern.

### Implementation sketch for Lyra

1. **Wrap MCP server tools as a typed filesystem tree** under `lyra/tools/servers/<server-name>/<tool-name>.ts` using the existing MCP client infrastructure.
2. **Add a Jupyter/Node sandbox executor** (Lyra already uses Python; a secure subprocess runner or container-based sandbox for JS/TS).
3. **Modify the orchestration loop**: when the model needs to interact with tools, it writes a script that imports the relevant wrappers, chains operations, and exports only the needed results.
4. **Add privacy tokenization hooks** for sensitive data paths (PII in CRM tools, API keys in external service calls).

### Impact scoring

- **Impact:** 9/10 -- Directly addresses the most expensive part of Lyra's agent loop (context waste from tool definitions + intermediate results). 98.7% token savings on a single dimension is transformative for cost and latency.
- **Effort:** 6/10 -- Requires a secure sandbox runtime, filesystem-based tool discovery, and orchestration loop changes. Non-trivial but well-scoped.
- **Tier:** Core -- This is a foundational architecture change, not a surface feature. It reshapes how Lyra's agent loop consumes tools and produces output.

### Related Lyra documents

- `docs/lyra-upgrade/ARCHITECTURE-DEBATE.md` -- Section 4.x on agent loop orchestration
- `docs/lyra-upgrade/MASTER-PLAN.md` -- Tool execution and conversation loop plans
- `docs/lyra-upgrade/brainstorm/05-router.md` -- Tool routing concerns
- `docs/lyra-upgrade/plans/02-memory.md` -- Context management overlap

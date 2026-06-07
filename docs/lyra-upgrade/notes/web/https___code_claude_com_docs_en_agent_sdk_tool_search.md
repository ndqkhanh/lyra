# Scale to Many Tools with Tool Search (Anthropic Agent SDK Docs)

Source: https://code.claude.com/docs/en/agent-sdk/tool-search

## Key Technical Claims

1. Tool search enables agents to work with hundreds or thousands of tools by dynamically discovering and loading only what is needed, on demand, rather than loading all tool definitions upfront into the context window.
2. Two fundamental scaling problems solved:
   - **Context efficiency**: 50 tool definitions can consume 10,000--20,000 tokens, crowding out the actual task.
   - **Tool selection accuracy**: Accuracy degrades when more than 30--50 tools are loaded at once.
3. Architecture: tool definitions are withheld from context on every turn; the agent receives only a summary of available tools and searches when a capability not already loaded is needed. The 3--5 most relevant tools are fetched per search.
4. After discovery, tools stay in context for subsequent turns. When compaction evicts them (SDK summarises earlier messages), the agent re-searches as needed.
5. One extra round-trip on first discovery, but offset by smaller context on every subsequent turn. For fewer than ~10 tools, loading everything upfront is typically faster.
6. Maximum catalog size: 10,000 tools.
7. Tool search requires Claude Sonnet 4 or later, or Opus 4 or later. Haiku models do not support it.
8. Tool search is disabled by default on Vertex AI (supported for Sonnet 4.5+ / Opus 4.5+) and when ANTHROPIC_BASE_URL points to a non-first-party host. Overridable via ENABLE_TOOL_SEARCH environment variable.

## Architecture/Mechanism Details

### ENABLE_TOOL_SEARCH values

| Value      | Behaviour                                                                                                                                                                                                                                                                                                                                   |
| :--------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| (unset)    | Tool search is ON. Definitions are deferred and discovered on demand. Falls back to loading upfront on Vertex AI or non-first-party ANTHROPIC_BASE_URL.                                                                                                                                                                                     |
| `true`     | Always on. Sends the beta header even on Vertex AI and through proxies. Fails on Vertex AI models earlier than Sonnet 4.5 / Opus 4.5, and on proxies that do not support tool_reference blocks.                                                                                                                                              |
| `auto`     | Checks the combined token count of ALL tool definitions against the model's context window. If they exceed 10%, tool search activates. If under 10%, all tools are loaded into context normally.                                                                                                                                              |
| `auto:N`   | Same as `auto` with a custom percentage. Example: `auto:5` activates when tool definitions exceed 5% of the context window. Lower values activate sooner.                                                                                                                                                                                     |
| `false`    | Tool search is off. All tool definitions are loaded into context on every turn.                                                                                                                                                                                                                                                               |

### Discovery optimisation

- The search mechanism matches queries against tool **names** and **descriptions**.
- Concrete names like `search_slack_messages` surface more broadly than `query_slack`.
- Descriptions with specific keywords ("Search Slack messages by keyword, channel, or date range") match more queries than generic ones ("Query Slack").
- A system prompt section listing available tool categories is recommended: "You can search for tools to interact with Slack, GitHub, and Jira."

### Configuration example (TypeScript/Python)

```typescript
for await (const message of query({
  prompt: "Find and run the appropriate database query",
  options: {
    mcpServers: {
      "enterprise-tools": {
        type: "http",
        url: "https://tools.example.com/mcp"
      }
    },
    allowedTools: ["mcp__enterprise-tools__*"],
    env: {
      ENABLE_TOOL_SEARCH: "auto:5"
    }
  }
})) { ... }
```

## Numbers & Benchmarks

| Metric                          | Value                          |
| ------------------------------- | ------------------------------ |
| Token cost of 50 tools          | 10,000--20,000 tokens          |
| Accuracy degradation threshold  | > 30--50 tools loaded at once  |
| Tools loaded per search         | 3--5 most relevant             |
| Maximum catalog size            | 10,000 tools                   |
| Default activation threshold    | 10% of context window (`auto`) |
| Small-tool fast-path threshold  | ~10 tools (load upfront)       |
| Model requirement               | Sonnet 4+ / Opus 4+            |

## Transfer to Lyra

### One transferable idea

**Percentage-based tool search activation with a configurable threshold** (the `auto:N` heuristic). Lyra currently has no principled mechanism for deciding when to defer tool definition loading. The `auto:N` pattern -- measure the combined token budget of all tool/service definitions against the model's context window, and activate dynamic discovery only when that budget exceeds N% -- is a clean, model-aware heuristic that generalises beyond Anthropic's SDK. Any agent framework (including Lyra's Router/Agency system) can implement it.

### Workstream route

**Section 4.x -- Router / Tool Discovery workstream** (or §4.4 Planner, or a new subsection on "Tool Discovery and Loading"). This maps directly to Lyra's Router component, which decides which tool definitions to inject into the agent's context. The Router should:
1. Compute the combined token footprint of all registered adapters, MCP servers, and plugin tools.
2. Compare against the available context window for the selected model.
3. If above a configurable threshold (default: 10%), switch to a "tool search" mode where definitions are withheld and only the top-N matching definitions are injected per turn.
4. Add a system-prompt hint listing available tool categories so the agent can express intent.

This is a low-effort, high-impact change: it requires no new infrastructure, just a measurement-and-gate check in the Router's context assembly loop, and a search/index over tool descriptions (trivially an in-memory TF-IDF or embedding cosine-similarity index).

# Manage costs effectively (Anthropic / Claude Code Documentation)

Source: https://code.claude.com/docs/en/costs

## Key Technical Claims

- Claude Code charges by API token consumption, not by seat. Per-developer costs vary widely based on model selection, codebase size, and usage patterns (parallel instances, automation).
- Average cost across enterprise deployments: **~$13 per developer per active day**, **$150-250 per developer per month**.
- Costs remain **below $30 per active day for 90% of users**.
- Agent teams use **approximately 7x more tokens** than standard sessions when teammates run in plan mode, because each teammate maintains its own context window as a separate Claude instance.
- Background token usage (conversation summarization, command processing) is small -- typically under $0.04 per session even without active interaction.
- Extended thinking is billed as output tokens; the default budget can be tens of thousands of tokens per request depending on model.
- The docs frame cost management as a **context-size problem**: token costs scale with context size, so minimizing context is the primary lever.

## Architecture / Mechanism Details

### Cost-tracking tools
- `/usage` command: shows token usage for current session (Session block) and plan-level breakdown by skills, subagents, plugins, MCP servers (attribution as percentages over 24h/7d windows).
- Claude Console: authoritative billing, workspace spend limits, admin reporting.
- Pro/Max: `/usage-credits` command for monthly spend limits on usage credits.
- Bedrock/Vertex/Foundry: Claude Code does not send metrics; enterprises use LiteLLM (open-source, unaffiliated) for per-key spend tracking.

### Rate limit recommendations (TPM/RPM per user by team size)

| Team size | TPM per user | RPM per user |
|---|---|---|
| 1-5 | 200k-300k | 5-7 |
| 5-20 | 100k-150k | 2.5-3.5 |
| 20-50 | 50k-75k | 1.25-1.75 |
| 50-100 | 25k-35k | 0.62-0.87 |
| 100-500 | 15k-20k | 0.37-0.47 |
| 500+ | 10k-15k | 0.25-0.35 |

TPM per user decreases as team size grows because fewer users tend to be concurrent in larger orgs. Rate limits apply at the organization level, not per individual user.

### Cost-reduction mechanisms (built-in)
1. **Prompt caching**: automatically reduces costs for repeated content like system prompts.
2. **Auto-compaction**: summarizes conversation history when approaching context limits.
3. **MCP tool search (deferred by default)**: only tool names enter context until Claude uses a specific tool.

### Recommended cost-reduction strategies
1. **Model selection**: Sonnet for standard coding, Opus only for architecture/reasoning, Haiku for subagents.
2. **Context minimization**: `/clear` between unrelated tasks, `/rename` before clear, custom compaction instructions via CLAUDE.md or `/compact`.
3. **MCP discipline**: prefer CLI tools (gh, aws, gcloud) over MCP servers (no per-tool listing overhead); disable unused servers via `/mcp`.
4. **Code intelligence plugins**: replace text-based search (grep + read multiple candidates) with precise "go to definition" -- reduces unnecessary file reads. Also reports type errors automatically after edits.
5. **Hooks for preprocessing**: PreToolUse hooks can filter verbose output (e.g., grep ERROR from 10k-line log file) before Claude sees it -- reducing context from tens of thousands of tokens to hundreds.
6. **Skills for on-demand knowledge**: move specialized instructions from CLAUDE.md to skills (load only when invoked). Keep CLAUDE.md under 200 lines.
7. **Extended thinking budget**: reduce via `/effort`, `/model`, `/config`, or `MAX_THINKING_TOKENS=8000`.
8. **Subagents for verbose ops**: delegate test runs, doc fetching, log processing to subagents so verbose output stays in subagent context; only summary returns to main conversation.
9. **Specific prompts**: vague requests trigger broad scanning; specific requests minimize file reads.
10. **Plan mode before implementation**: Shift+Tab to explore and propose approach before costly wrong-direction rework. Early course-correction via Escape, `/rewind`.

## Numbers & Benchmarks

| Metric | Value |
|---|---|
| Average cost per dev per active day | $13 |
| Average cost per dev per month | $150-250 |
| 90th percentile cost per active day | $30 |
| Agent team token multiplier (plan mode) | 7x |
| Background token cost per idle session | < $0.04 |
| Recommended CLAUDE.md max length | 200 lines |
| Max thinking tokens (lowered budget example) | 8,000 |
| Session cost example (from `/usage`) | $0.55 |

## Transfer to Lyra

### One transferable idea: **Cost-aware agent router with context-budget enforcement**

The Claude Code docs make a powerful implicit argument: **the single biggest cost lever in an agent system is controlling what enters context**. Every token that enters a context window -- whether from verbose MCP tool descriptions, overly long CLAUDE.md files, unfiltered log output, or broad exploratory searches -- is a cost that compounds linearly with every subsequent turn.

Lyra should implement a **cost-aware task router** that operates at two levels:

**Level 1 -- Model routing**: Route tasks to the cheapest model that can reliably complete them. Simple code generation and subagent work -> Haiku. Standard coding and coordination -> Sonnet. Deep architectural reasoning -> Opus. This alone can deliver 3-10x cost improvements on the majority of workload.

**Level 2 -- Context budgeting per agent invocation**: Before spinning up any agent (subagent, research agent, code agent), the router estimates the context baseline (system prompt + loaded skills + MCP tools) and caps verbose output from that agent. Concretely:

- Implement preprocessing hooks that filter/strip agent output before it enters the parent context (grep for relevant lines only, truncate to first N lines, etc.).
- Move domain knowledge from monolithic config files (analogous to CLAUDE.md) to on-demand "skill" files loaded only when the corresponding workstream is invoked.
- Assign each spawned agent a per-invocation token budget (e.g., soft limit + hard cap on output tokens). This prevents a single runaway research task from consuming the entire session budget.
- Track cumulative token spend per session and emit warnings when approaching configured limits (analogous to Claude Code's `/usage-credits`).

### Workstream route: **§4.3** (Cost / Resource Optimization)

This architecturally fits in Lyra's resource optimization workstream, where the router sits between the user request and agent dispatch -- analogous to Claude Code's model-switching (/model) and subagent delegation patterns but with explicit cost-awareness and token budgets.

### Estimated impact vs effort

| Dimension | Rating | Reasoning |
|---|---|---|
| **Impact** | 8/10 | Direct cost reduction (3-10x on most tasks); scales with agent count |
| **Effort** | 6/10 | Requires router refactor, budget tracking infra, hook/filter system for agent output |
| **Tier** | Gold | High ROI; concrete and implementable; well-understood pattern from Claude Code docs |

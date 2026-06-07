# Orchestrate subagents at scale with dynamic workflows (Claude Code Documentation / Anthropic)

## Key Technical Claims

1. **Dynamic workflows move the plan into code**: A JavaScript script (not Claude's turn-by-turn reasoning) holds the loop, branching, and intermediate results. Claude's context window holds only the final answer, dramatically reducing context pressure at scale.

2. **Workflows are script-driven, not prompt-driven**: Unlike subagents, skills, or agent teams where Claude decides what to spawn next, a workflow script codifies the orchestration. This makes it repeatable, reviewable, diffable, and resumable.

3. **Adversarial cross-checking as a built-in pattern**: Workflows can "have independent agents adversarially review each other's findings before they're reported" — a quality mechanism that is cumbersome with subagents/teams but natural when the orchestration is in code.

4. **Ultracode mode**: Setting `/effort ultracode` combines xhigh reasoning effort with automatic workflow orchestration — Claude decides when a task warrants a workflow and writes one without being asked.

5. **Persistence model**: Runs write their script to `~/.claude/projects/`. Saved workflows become `/` commands from `.claude/workflows/` (project-shared) or `~/.claude/workflows/` (personal). Input is passed via typed `args` parameter (not parsed strings).

## Architecture/Mechanism Details

- **Runtime isolation**: The workflow runtime executes in an isolated environment, separate from the conversation. Intermediate results live in script variables, not Claude's context.
- **Progress model**: `/workflows` view shows phases with agent counts, token totals, and elapsed time. Users can drill into any phase/agent to read prompts, tool calls, and results.
- **Resumability**: Completed agents return cached results; pending ones run live. Works within the same session; session exit restarts fresh.
- **Permission model**: Subagents spawned by workflows always run in `acceptEdits` mode, inherit the user's tool allowlist. File edits are auto-approved. Shell/web/MCP calls not in allowlist still prompt. Permission mode only controls the launch prompt, not mid-run prompts.
- **Script visibility**: The runtime writes the script to disk. Users can open it, diff vs. previous runs, edit it, and ask Claude to relaunch from the edited version.
- **No mid-run user input**: Only agent permission prompts can pause a run. For sign-off between stages, each stage must be its own workflow.

## Numbers & Benchmarks

| Constraint | Value | Rationale |
|---|---|---|
| Max concurrent agents | 16 (fewer on limited CPU cores) | Bounds local resource use |
| Max agents per run | 1,000 | Prevents runaway loops |
| Min Claude Code version | v2.1.154+ | Required for workflow runtime |
| Availability | Pro, Max, Team, Enterprise, API, Bedrock, Vertex AI, Foundry | All paid surfaces |

- Workflows use **meaningfully more tokens** than conversational work to the same goal. Cost is bounded by the 1,000-agent cap.
- Token usage per agent visible live in `/workflows` view.
- Recommendation: run on a small slice first to gauge spend before committing to a large task.

## Transfer to Lyra (one idea)

**Adversarial cross-check verification as a distinct pipeline phase.**

The documentation explicitly states that workflows can "have independent agents adversarially review each other's findings before they're reported, or draft a plan from several angles and weigh them against each other, so you get a more trustworthy result than a single pass."

Lyra's current research pipeline (per the phase documents) runs synthesis after investigation. Adding an explicit **adversarial cross-check phase** — where multiple verification agents independently audit each claim from the synthesis, then vote on claim validity — would raise output trustworthiness significantly. This pattern is uniquely enabled by script-driven orchestration (workflows) because the script holds references to all intermediate agent results, making cross-comparison natural.

**Workstream route: §4.3 — add adversarial verification phase within the research pipeline script, not as a post-hoc step.** The workflow script should: (1) fan out investigation agents, (2) collect findings into structured claims, (3) launch N verification agents that each independently check every claim against source material, (4) aggregate votes, (5) filter claims that fail verification, (6) synthesize only validated claims into the final report.

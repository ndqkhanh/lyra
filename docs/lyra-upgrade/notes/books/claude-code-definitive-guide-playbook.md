# Claude Code: The Definitive Guide to Agentic Development — Best Practices Playbook

## Practice 1: Verification Criteria as the Highest-Leverage Prompting Technique
- **What:** Always include verification criteria in agent prompts — test commands, expected output, visual targets, behavioral descriptions, or existing test suites. This converts one-shot generation into an automatic generate-test-fix loop.
- **Why:** Without verification criteria, Claude operates in "generate-and-hope" mode. With them, it self-corrects until the criteria are met. The cost is 30 seconds of typing; the benefit is measured in hours of debugging time saved. Roughly one-third of tasks succeed on first attempt without verification; automated verification through tests/types/linters significantly increases first-attempt success rates.
- **Lyra route:** §4.6 (Reliability/Verification) — Build verification criteria into every agent task definition. Make verification infrastructure a first-class concern.
- **Source:** Chapter 8 (Prompt Craft for Agentic Tools)

## Practice 2: CLAUDE.md as Compounding Institutional Memory
- **What:** Treat CLAUDE.md as a living document that accumulates project-specific knowledge across sessions. After each session, ask the agent to review what it learned and suggest additions. Check CLAUDE.md into version control. Keep it under 500 lines, focus on what the agent cannot infer from code.
- **Why:** Without persistent memory, every new session starts with a blank context window — "agent amnesia." Teams that maintain CLAUDE.md across 5+ sessions report dramatically better results. Knowledge compounds: one developer's discovery prevents the same error for every future team member. Even non-code domains (financial analysis, research, data science) benefit.
- **Lyra route:** §4.2 (Memory) — This is the foundational memory pattern for Lyra. CLAUDE.md maps to Lyra's persistent agent memory layer. The end-of-session update loop maps to Lyra's learning/reflection cycle.
- **Source:** Chapter 3 (Context Engineering)

## Practice 3: Plan Before Parallelizing
- **What:** Always create a detailed plan before launching parallel agents. The plan specifies task boundaries (which agent owns which files), interface contracts, dependency order, and acceptance criteria. 10,000 tokens of planning prevents 500,000+ tokens of wasted, conflicting execution.
- **Why:** Without a plan, parallel agents make different assumptions, write conflicting code, solve overlapping problems in incompatible ways, and you spend more time resolving conflicts than you saved through parallelism. This is the default outcome of naive parallelization, not a theoretical concern.
- **Lyra route:** §4.3 (Context/Routing) — Plan-first parallelization is essential for Lyra's multi-agent orchestration.
- **Source:** Chapter 4 (Multi-Agent Orchestration)

## Practice 4: The Expensive Brain, Cheap Hands Model
- **What:** Use the most capable model for orchestration (planning, decomposition, quality evaluation) and cheaper, faster models for execution (implementation, exploration, grunt work). Configure subagents with their own model preferences.
- **Why:** Orchestration is a small fraction of total token usage. Planning a refactor consumes ~10K tokens; executing it across 20 files consumes ~500K tokens. If execution runs on a model that costs 1/5 as much per token, total costs drop ~80% with no loss in planning quality. This maps to an organizational metaphor: senior architect plans, junior developers implement.
- **Lyra route:** §4.5 (Router) — Model routing by task complexity; cost-aware model selection.
- **Source:** Chapter 4 (Multi-Agent Orchestration)

## Practice 5: Context Isolation via Subagents
- **What:** Route any operation that produces high-volume output through a subagent. Subagents run in their own context window — only the summary returns to the main session. Use for: reading large modules, running comprehensive test suites, exploring sprawling directory trees, searching across hundreds of files.
- **Why:** Context isolation is the primary value of subagents, more than parallelism. In one documented case, 14 subagents completed a complex migration while the main session stayed at 143K/200K tokens. The orchestrator's context stayed lean, focused on coordination rather than implementation details. Instruct subagents to be concise in returns — specific answers, not comprehensive reports — or write detailed findings to a file and return only the path.
- **Lyra route:** §4.3 (Context) — Subagent isolation is the primary context management strategy for Lyra.
- **Source:** Chapter 4 (Multi-Agent Orchestration)

## Practice 6: Spec-Driven Development as the Default Workflow
- **What:** Replace the default prompt-code-debug-repeat cycle with: Research (parallel subagents explore the codebase) → Spec (write a comprehensive specification as a file on disk) → Refine (interview the user for clarifications via structured questioning) → Tasks (break into atomic tasks, each implemented by a subagent with fresh context) → Done.
- **Why:** The spec file survives context compaction, session restarts, and subagent failures. It is the recovery point for the entire workflow. One storage layer migration: 14 tasks, 15+ files changed, completed in ~45 minutes with better quality than manual implementation. Spec-driven development produces higher-quality output and cleaner architecture than iterative prompt-code-debug.
- **Lyra route:** §4.3 (Context), §4.1 (Research) — Spec documents as persistent artifacts; research-first workflow.
- **Source:** Chapter 8 (Prompt Craft for Agentic Tools)

## Practice 7: Backpressure via Strict Tooling
- **What:** Invest in strict linting, comprehensive type checking, and thorough test suites — not just for human code quality, but as a component of your agent's prompt. Pre-commit hooks that run the test suite and linter create automated feedback that makes agents self-correct at the commit boundary.
- **Why:** Your linting configuration is literally part of your prompt. Claude reads linting errors, type errors, and test failures, then self-corrects. This automated backpressure catches AI errors that would otherwise require manual review. Spend your limited human feedback budget on architecture, design decisions, and domain logic — let tooling handle mechanical issues. TDD is the ultimate expression: the agent writes tests first, then must satisfy them.
- **Lyra route:** §4.6 (Reliability), §4.7 (Safety) — Verification infrastructure as a first-class design element.
- **Source:** Chapter 8 (Prompt Craft for Agentic Tools), Chapter 10 (Failure Modes)

## Practice 8: Defense in Depth via Hooks + Permissions + Sandbox
- **What:** Layer multiple security mechanisms: deny sensitive files via `permissions.deny`, restrict network access via sandbox allowlists, validate tool inputs via PreToolUse hooks, log all external access via MCP hooks, and use devcontainers for headless/CI execution. Never rely on a single layer.
- **Why:** A devcontainer prevents accidental network access but cannot prevent credential exfiltration from malicious project code. A PreToolUse hook can block destructive commands but cannot stop a confused agent from making bad decisions. Each layer covers gaps in others. The enterprise-correct posture is layered defense.
- **Lyra route:** §4.7 (Safety) — Safety architecture and permission model for Lyra.
- **Source:** Chapter 2 (The Permission and Trust Architecture)

## Practice 9: The Slot Machine Recovery Pattern
- **What:** When a task is going wrong, commit the current state, let Claude run autonomously for a fixed time (20–30 minutes), then make a binary decision: accept the result or `git revert` and restart with a fresh session and better prompt. Do not spiral into corrections.
- **Why:** The correction spiral — explain, patch, new problem, explain again — consumes more time and tokens than two fresh attempts. A fresh session with a better prompt (informed by what went wrong) beats a degraded session with accumulated confusion. Starting over often has a higher success rate than trying to fix mistakes mid-stream.
- **Lyra route:** §4.6 (Reliability) — Recovery strategies for autonomous agent execution.
- **Source:** Chapter 10 (Failure Modes and Recovery)

## Practice 10: Define Agent Roles by Task, Not Personality
- **What:** Use concrete, behavioral role definitions: "Review all files in `src/api/` for SQL injection vulnerabilities" — not personality-based roles: "You are the security-conscious team member." Keep role definitions narrow and verifiable.
- **Why:** Personality-based roles produce emergent, unpredictable behavior because each agent draws on training data to interpret its "character." A "cautious reviewer" can become an obstructionist. A "CEO" can defer excessively to a "consultant." In one documented case, a four-agent trading hierarchy degraded to effectively one agent because personality conflicts paralyzed the system. Task-based definitions produce task-focused, predictable output.
- **Lyra route:** §4.4 (Multi-agent architecture) — Agent role definitions in Lyra's orchestrator.
- **Source:** Chapter 4 (Multi-Agent Orchestration)

## Practice 11: Use Context Cost Hierarchy for Architecture Decisions
- **What:** Make context cost the primary consideration when choosing between CLAUDE.md, skills, MCP, subagents, and hooks. CLAUDE.md and MCP cost tokens every request; skills cost only descriptions until invoked; subagents run isolated; hooks are zero-context. Choose the right mechanism for each type of information.
- **Why:** Getting the classification wrong hurts both ways. Put reference material in CLAUDE.md and you waste context on every request. Put always-needed rules in a skill and Claude violates them whenever the skill is not loaded. The context budget is the binding constraint on every session.
- **Lyra route:** §4.2 (Memory), §4.3 (Context) — Context budget management; choosing the right persistence mechanism.
- **Source:** Chapter 3 (Context Engineering)

## Practice 12: End-of-Session Continuous Improvement Loop
- **What:** At the end of each session, ask Claude to: (1) review what it learned and suggest additions to CLAUDE.md, and (2) suggest improvements to the workflow itself — not just knowledge additions but process refinements. Commit the updated CLAUDE.md. Extend this to have Claude identify patterns, gotchas, and architecture decisions for capture.
- **Why:** This turns CLAUDE.md from a static configuration file into a knowledge accumulator that improves with every session. One team reported that this loop — updating both knowledge and process — made subsequent iterations measurably more effective. The distinction matters: process improvements ("the deployment script should run lint before build") compound differently than knowledge additions ("the test database uses port 5433").
- **Lyra route:** §4.2 (Memory), §4.8 (Self-improvement) — Reflection and learning loop for Lyra.
- **Source:** Chapter 3 (Context Engineering)

## Practice 13: The Guided Adoption Path
- **What:** For team or individual adoption, follow a staged progression: Stage 1 (Codebase Q&A — Claude reads only) → Stage 2 (Small fixes — easy to verify) → Stage 3 (Plan mode — separate understanding from implementation) → Stage 4 (Full autonomy — calibrated expectations). This takes 2–4 weeks per developer. Skipping stages produces the uneven results that make teams give up.
- **Why:** Each stage builds confidence and institutional knowledge. Stage 1 reveals whether the codebase is legible to Claude at all. Stage 2 teaches verification and critical review habits. Stage 3 catches most implementation failures (misunderstandings) before they become code. Stage 4 works because the preceding stages calibrated expectations.
- **Lyra route:** §4.x (All workstreams) — Adoption and deployment strategy for Lyra.
- **Source:** Chapter 11 (Team Adoption Patterns)

## Practice 14: Exhaustive Questioning Before Implementation
- **What:** Before any complex task, instruct the agent: "Before you start, ask me questions exhaustively about anything you are uncertain about. Do not proceed until you have asked every question." Use the AskUserQuestion tool for structured, focused questions.
- **Why:** Claude fills in assumptions when specifications are incomplete, and those assumptions are often wrong. Exhaustive questioning surfaces gaps in your own specifications — you discover decisions you had not made. Practitioners report 30–50% improvement in first-pass quality on complex tasks. The cost is a few minutes of answering questions; the benefit is implementation that matches actual requirements instead of the agent's plausible assumptions.
- **Lyra route:** §4.2 (Memory/Context), §4.3 (Context) — Requirements gathering and clarification workflow.
- **Source:** Chapter 8 (Prompt Craft for Agentic Tools)

## Practice 15: Commit-Frequently as Foundation for All Recovery
- **What:** Commit before starting any complex task. Commit as Claude works. The commit-frequently pattern is the foundation of every recovery strategy — checkpoint-and-rollback, slot machine, spec-driven development, and safe autonomous operation.
- **Why:** Claude Code's checkpoint system tracks only direct file edits (Write/Edit tools), not bash-command file operations. Git is the universal undo mechanism. Without frequent commits, you have no clean state to revert to when things go wrong. The discipline required is emotional, not technical — reverting feels like wasting work, but the work was already wasted by the failure.
- **Lyra route:** §4.7 (Safety), §4.6 (Reliability) — Safe autonomous execution; recovery strategies.
- **Source:** Chapter 10 (Failure Modes and Recovery), Chapter 1

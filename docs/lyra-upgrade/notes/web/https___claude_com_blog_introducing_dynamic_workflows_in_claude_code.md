# Introducing Dynamic Workflows in Claude Code (Claude Blog, May 28, 2026)

> Research preview: Claude Code autonomously writes orchestration scripts that fan work across tens to hundreds of parallel subagents with built-in adversarial verification.

## Key Technical Claims

1. **Autonomous multi-agent fan-out**: On workflow trigger, Claude dynamically plans, decomposes the prompt into subtasks, and fans work across parallel subagents -- all without a hand-authored orchestration script.

2. **Built-in adversarial verification**: Results are checked before folding in. Multiple agents approach the problem from independent angles, dedicated refuter agents try to break the findings, and the run iterates until answers converge.

3. **Resilient long-running execution**: Progress is checkpointed to disk during the run. An interrupted job picks up where it left off (hours-to-days runtime supported).

4. **Coordination decoupled from conversation**: The orchestration plan lives outside the conversation context, so the plan stays on track regardless of scale.

## Architecture / Mechanism Details

- **Two invocation paths**: (a) direct natural-language request ("Create a workflow that...") or (b) enable the `ultracode` setting, which sets effort level to `xhigh` and lets Claude autonomously decide when a workflow is appropriate.
- **Parallel subagent model**: One orchestrator agent decomposes work, fans out to N parallel workers. In the Bun rewrite case, "hundreds of agents working in parallel with two reviewers on each file."
- **Adversarial verification**: "Adversarial agents working to break the result before you see it" -- dedicated refuter agents that try to falsify findings.
- **Confirmation gate**: First workflow trigger shows what will run and asks for confirmation.
- **Admin controls**: Enterprise org admins can disable workflows via managed settings. Off by default for Enterprise; on by default for Max and Team.
- **Recommended approach**: Start scoped. Turn on auto mode for the best experience.

## Numbers and Benchmarks

- **Parallelism scale**: "Tens to hundreds of parallel subagents in a single session"
- **Bun rewrite case study** (Jarred Sumner): ~750,000 lines of Rust ported from Zig, first commit to merge in **eleven days**, **99.8%** of existing test suite passing. One workflow handled lifetime annotations; another wrote every `.rs` file as behavior-preserving port. A "fix loop" drove build and test to cleanliness. An overnight workflow addressed unnecessary copies and opened individual PRs.
- **Availability**: Research preview in Claude Code CLI, Desktop, and VS Code. Max, Team, Enterprise (admin-enabled), plus API, Bedrock, Vertex AI, Microsoft Foundry.

## Transfer to Lyra

**One idea: adopt the adversarial multi-agent fan-out pattern as the core execution primitive for Lyra's dynamic workflow engine.**

Specifically:
- Replace Lyra's current single-agent loop (AgentLoop) with a orchestrator-subagent model where the planner dynamically decomposes tasks and fans out to parallel workers with independent verification.
- Build a verification panel where dedicated refuter agents try to break each subagent's output before surfacing results to the user.
- Introduce an `ultracode`-equivalent effort level (`xhigh`) that autonomously triggers workflow mode when task complexity exceeds a threshold.
- Adopt the checkpoint-and-resume pattern for Lyra's supervisor daemon (§4.13) so that long-running fleet workflows survive sleep/interruption.

**Workstream route**: §4.25 (Adversarial Verification Panel - core home for the refuter-agent pattern) + §4.13 (Swarm/Fleet - subagent fan-out infrastructure) + §4.14 (Full Autonomy - checkpoint/resume for long-running workflows) + §4.20 (Planning - effort-level-triggered workflow escalation à la `ultracode`).

**Priority**: Integrate the subagent fan-out mechanism into Lyra Phase 2 (The Brain: Dynamic Workflow Engine). The adversarial verification layer can follow in Phase 4 (The Reflexes), but the core orchestration primitive should be built now to unblock everything else.

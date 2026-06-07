# Orchestrate Teams of Claude Code Sessions (code.claude.com)

## Key Technical Claims

1. **Agent teams** coordinate multiple independent Claude Code instances (each with its own context window) under a single team lead, with a shared task list and direct inter-agent messaging via a mailbox system.
2. Unlike **subagents** (hierarchical: spawn -> work -> report back, no peer communication), agent team **teammates** message each other directly, claim work from a shared task list, and self-coordinate.
3. Strongest use cases claimed: (a) parallel research/review, (b) new modules/features with clear ownership boundaries, (c) debugging with competing hypotheses, (d) cross-layer coordination (frontend + backend + tests).
4. Requires Claude Code v2.1.32+. Experimental, disabled by default -- opt in via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env var.
5. Subagent definitions can be reused as teammate role templates (tools allowlist and model carry over; skills/MCP servers do NOT).
6. Hooks available: `TeammateIdle`, `TaskCreated`, `TaskCompleted` -- exit code 2 to reject and send feedback.

## Architecture/Mechanism Details

- **Components**: Team lead (main session), Teammates (separate Claude instances), Task list (shared, file-locked), Mailbox (messaging system).
- **Storage**: Team config at `~/.claude/teams/{team-name}/config.json`; task list at `~/.claude/tasks/{team-name}/` -- both auto-generated, not hand-editable.
- **Display modes**: (1) In-process -- all in main terminal, Shift+Down cycles through teammates, type to message. (2) Split panes -- requires tmux or iTerm2 with `it2` CLI.
- **Task lifecycle**: Three states (pending, in-progress, completed). Dependencies supported -- blocked tasks auto-unblock when prerequisites complete. File locking prevents race conditions on simultaneous claims.
- **Teammate plan-approval workflow**: Teammate works in read-only plan mode -> sends approval request to lead -> lead approves/rejects with feedback -> if rejected, teammate revises and resubmits -> once approved, implements.
- **Context isolation**: Each teammate loads project context (CLAUDE.md, MCP servers, skills) independently. Lead's conversation history does NOT carry over. No nested teams. Lead is fixed.
- **Permissions**: Teammates inherit lead's permission mode at spawn. Per-teammate modes can be changed post-spawn but not set at spawn time.

## Numbers & Benchmarks

- **No concrete benchmarks or token numbers provided** in this document.
- Qualitative guidance only: "token costs scale linearly" with active teammates; agent teams "use significantly more tokens than a single session"; "for routine tasks, a single session is more cost-effective."
- Recommended team size: **3-5 teammates** for most workflows.
- Recommended task granularity: **5-6 tasks per teammate**.
- Staffing heuristic: 15 independent tasks -> 3 teammates as starting point.
- No hard limit on teammate count, but coordination overhead and diminishing returns apply.

## Transfer to Lyra

**One idea**: The **competing-hypotheses debugging pattern** -- spawn multiple agent teammates to investigate different theories of a bug/failure and have them actively try to disprove each other, then converge on the theory that survives adversarial challenge. The doc explicitly motivates this: "Sequential investigation suffers from anchoring: once one theory is explored, subsequent investigation is biased toward it."

**Transfer mechanism**: Lyra already runs multi-agent orchestrators (via OMC/ultrawork/team modes). The missing piece is an **adversarial verification phase** where N agents independently review a plan or code change, each with a deliberately different lens (security, correctness, performance, edge-case), then debate their findings before converging. This directly addresses Lyra's reliability/safety workstream and the known problem that a single reviewer tends to "gravitate toward one type of issue."

**Workstream route**: This maps most naturally to **Section 4.x** of the Lyra upgrade plan -- specifically the **Reliability** and **Safety** workstreams, where multi-perspective adversarial review can be formalized as a pipeline step between implementation and merge.

## Key Citations

- "Subagents only report results back to the main agent and never talk to each other. In agent teams, teammates share a task list, claim work, and communicate directly with each other."
- "Teammates don't inherit the lead's `/model` selection by default."
- "Having 5-6 tasks per teammate keeps everyone productive without excessive context switching."
- "The debate structure is the key mechanism here. Sequential investigation suffers from anchoring..."
- "Teammates load project context automatically... but they don't inherit the lead's conversation history."

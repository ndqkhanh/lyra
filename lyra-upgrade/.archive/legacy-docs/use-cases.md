---
title: Use cases
description: Task-driven recipes — "I want to ship a feature with TDD / debug a bug / run on a tight budget / evaluate against benchmarks / …" — each shows the feature stack to use and a one-screen invocation.
---

# Use cases <span class="lyra-badge guide">guide</span>

> **Status:** v3.5.5 snapshot. Task-driven companion to the
> exhaustive [Features catalogue](features.md). Where the catalogue
> lists every feature with a one-line use case, this page goes the
> other way — **start with the task, end with the invocation**.
> Each recipe links to the concept and how-to pages for depth.
>
> Every recipe on this page works against a real provider key
> (DeepSeek, Anthropic, OpenAI, Gemini, …) today. Recipes that
> required forward-compat shims were removed in v3.5.5 — see the
> [CHANGELOG](https://github.com/lyra-contributors/lyra/blob/main/projects/lyra/CHANGELOG.md).

## How to use this page

1. Find the scenario closest to your task.
2. Read the **feature stack** to understand which Lyra subsystems
   collaborate.
3. Run the **one-screen recipe** as-is, then iterate.
4. Click through to **dig deeper** if you need to customise.

If your scenario isn't here, the [Features catalogue](features.md)
is grouped by subsystem — start there, then file an issue if a
common scenario is missing.

---

## 1. "I want to ship a feature with full TDD discipline"

**Problem.** You want the agent to write a failing test first, then
the minimal code to pass, then refactor — and you want a hard gate
that refuses to merge code without a test diff.

**Feature stack.**
[Plan mode](concepts/plan-mode.md) → [TDD gate](howto/tdd-gate.md) → [Tournament TTS](features.md#9-test-time-scaling-tts) → [Verifier](concepts/verifier.md) → [ReasoningBank](concepts/reasoning-bank.md) → [Reflexion loop](features.md#10-plan-mode--org-mode).

**One-screen recipe.**

```bash
lyra brain install tdd-strict
lyra
> /tdd-gate on
> /mode plan_mode
> Add a `parse_iso_duration` function to src/dates.py that handles "PT1H30M"
  format. Tests in tests/test_dates.py.
> /approve
> /cycle                    # advances RED → GREEN → REFACTOR per attempt
> /reflect on               # capture lessons into ReasoningBank
```

**What happens.**

1. **`plan_mode`** produces an approvable `plan.md` with acceptance
   criteria — no edits yet.
2. **`/approve` switches to `edit_automatically`.** First attempt is
   forced into `red` permission mode (write tests only, no
   implementation).
3. **TDD gate refuses** any diff with implementation but no test
   change. The diff is rejected before it lands.
4. After RED is green, **`/cycle` advances to `green`** (write minimal
   implementation), then `refactor`.
5. **Tournament TTS** (if `--tournament-n N` passed to `lyra run`)
   runs N parallel attempts, distills winners, and re-runs.
6. **Verifier** (objective + different-family judge) gates the
   final diff.
7. **Reflexion** writes the lesson — what worked, what didn't —
   into `<repo>/.lyra/reasoning_bank.db` for next time.

**Dig deeper:** [TDD discipline](tdd-discipline.md) · [Verifier](concepts/verifier.md) · [Use ReasoningBank](howto/use-reasoning-bank.md).

---

## 2. "I want to debug a thorny bug systematically"

**Problem.** Something is broken intermittently. You want the agent
to investigate without writing speculative fixes.

**Feature stack.**
[Debug mode](howto/debug-mode.md) → [Replay-trace](howto/replay-trace.md) → [HIR + observability](concepts/observability.md) → [`/why`](reference/commands.md#observability) → [Reflexion](features.md#10-plan-mode--org-mode).

**One-screen recipe.**

```bash
lyra
> /mode auto_mode           # router will pick ask_before_edits for debug-shaped prompts
> /skill load systematic-debugging
> The /api/users endpoint returns 500 about 1 in 5 requests under load.
  Reproduce, find the cause, propose a fix. Don't edit anything yet.
> /trace                    # open the live trace viewer
> /why <tool-call-id>       # explain why a particular tool ran
> /hir                      # show the HIR span tree
> /reflect add "race in connection-pool checkout when N>50"
```

**What happens.**

1. **`auto_mode`** classifies the debugging prompt and dispatches to
   `ask_before_edits` (the right permission posture for risky probe
   writes during investigation). The systematic-debugging skill loads
   the hypothesis-test scaffold so the agent reads logs, traces, git
   history, and runs tests — confirming each diagnostic write — until
   you flip back to `edit_automatically` to apply the real fix.
2. **Every tool call emits an HIR span** plus an OTel span (if
   exporter configured). The trace JSONL lands in
   `.lyra/sessions/<id>/trace.jsonl`.
3. **`/why <id>`** explains the precise reason a tool ran — useful
   for "why did the agent grep this file?".
4. **`lyra retro`** re-runs the session deterministically against
   the same tool inputs to confirm the diagnosis.
5. **`/reflect add`** captures the lesson so the next time a 500
   appears under load, ReasoningBank surfaces "race in conn-pool
   checkout when N>50" as a candidate hypothesis.

**Dig deeper:** [Debug mode](howto/debug-mode.md) · [Replay a trace](howto/replay-trace.md) · [Observability and HIR](concepts/observability.md).

---

## 3. "I want my agent to remember lessons across sessions"

**Problem.** Your agent keeps re-discovering the same gotchas
("oh right, our test runner needs `--no-cov` in CI"). You want it
to stop.

**Feature stack.**
[ReasoningBank](concepts/reasoning-bank.md) → [Memory tiers](concepts/memory-tiers.md) → [SOUL.md persona](features.md#5-memory-subsystem-3-tiers--reasoningbank) → [MaTTS](features.md#9-test-time-scaling-tts) → [Reflexion](features.md#10-plan-mode--org-mode).

**One-screen recipe.**

```bash
lyra brain install default
lyra memory record \
  --title "test runner needs --no-cov in CI" \
  --description "pytest crashes with coverage on CI runners; pass --no-cov" \
  --content "Run: pytest -q --no-cov in CI. Reason: coverage plugin OOMs."
lyra memory list                       # confirm it landed
lyra
> /reflect on                          # auto-distill new lessons after each task
> Add a CI step that runs the full test suite.
# Lyra recalls the --no-cov lesson and includes it in the agent's prefix.
```

**What happens.**

1. **`lyra memory record`** writes a structured `Lesson` to
   `<repo>/.lyra/reasoning_bank.db` (SQLite + FTS5).
2. **On the next task, the agent recalls** lessons matching the
   query via FTS5 search, ranked + diversified via MMR.
3. **`/reflect on`** also writes new lessons automatically after
   each task using the **heuristic distiller** (no LLM cost).
4. **MaTTS** rotates *different slices* of the bank into each
   parallel attempt when you run Tournament TTS — so attempts
   don't all read the same top-3 lessons.
5. **SOUL.md** captures the durable persona ("Lyra writes Python
   3.12, prefers ruff, never edits secrets") in a never-compacted
   layer.

**Dig deeper:** [ReasoningBank concept](concepts/reasoning-bank.md) · [Use ReasoningBank](howto/use-reasoning-bank.md) · [Memory tiers](concepts/memory-tiers.md).

---

## 4. "I want to run N parallel attempts on the same hard task"

**Problem.** This is a hard problem — you want 4–8 attempts in
parallel, distilled and tournament-voted, instead of betting on
one shot.

**Feature stack.**
[Tournament TTS](features.md#9-test-time-scaling-tts) → [Subagents + worktrees](concepts/subagents.md) → [Prompt-cache coordination](concepts/prompt-cache-coordination.md) → [Diversity guard](features.md#8-verifier) → [MaTTS](features.md#9-test-time-scaling-tts).

**One-screen recipe.**

```bash
lyra run "Refactor src/auth/* to use the new SessionManager API. \
          Keep all existing tests green; add tests for any behaviour \
          you change." \
  --tournament-n 4 \
  --tournament-rounds 2 \
  --matts-prefix-k 3 \
  --diversity-guard on
```

**What happens.**

1. **Subagent orchestrator** spawns 4 isolated git worktrees, one
   per attempt — they can't see each other's edits.
2. **Prompt-cache prewarm** sends the shared prefix (system prompt
   + repo summary + skill rolodex) to the provider once on the
   parent thread; the 4 subagents *hit* the cached prefix on
   hosted-API providers — saves N-1 prefill costs.
3. **MaTTS** injects 3 *different* ReasoningBank slices into each
   subagent's prefix → 4 attempts read different priors.
4. **Diversity guard** raises if the 4 attempts collapse into a
   monoculture (paper #23 § 5.2 remediation hint).
5. **Tournament voting** (different-family judges) eliminates weak
   attempts. Round 2 reseeds the survivors with distilled insight
   from the eliminated ones.
6. The **winning diff** is verified by the cross-channel verifier
   before being applied to your repo.

**Dig deeper:** [Subagents](concepts/subagents.md) · [Prompt-cache coordination](concepts/prompt-cache-coordination.md) · [Tournament TTS in features](features.md#9-test-time-scaling-tts).

---

## 5. "I want to run on a tight budget"

**Problem.** You're paying per token. You want 80 % of turns to go
to a cheap fast slot and only escalate when the fast model is
unsure. You also want a hard cap so the bill can't surprise you.

**Feature stack.**
[Two-tier routing](concepts/two-tier-routing.md) → [Cost tracking](features.md#16-cost-optimisation-surface) → [Budget cap](features.md#16-cost-optimisation-surface) → [Cost burn-down](features.md#16-cost-optimisation-surface) → [Prompt-cache coordinator](concepts/prompt-cache-coordination.md) → [Per-tool quotas](features.md#16-cost-optimisation-surface).

**One-screen recipe.**

```bash
lyra setup                                 # configure DeepSeek + Anthropic keys
lyra --budget 5.00 --model auto
> /model fast=deepseek-chat smart=anthropic-sonnet
> /config set quotas.tools.bash=20         # max 20 shell calls per turn
> /config set tdd_gate=on
# work normally; /cost any time
> /cost
> /budget save 5.00                        # persist as default
# Outside the REPL:
lyra burn --since 7d --by repo,model       # weekly cost report
```

**What happens.**

1. **`auto` model picks DeepSeek first** (priority order:
   DeepSeek → Anthropic → OpenAI → Gemini → xAI → Groq → Cerebras
   → Mistral → Qwen → OpenRouter → LM Studio → Ollama).
2. **Two-tier cascade**: every turn first runs in the *fast slot*
   (DeepSeek). The router escalates to the *smart slot*
   (Anthropic) when the fast slot's confidence falls below
   threshold (FrugalGPT + RouteLLM lineage, papers #10–12).
3. **Prompt-cache coordinator** auto-anchors any shared prefix
   under both providers — Anthropic and OpenAI both give 50 % +
   discounts on cache hits.
4. **Budget cap** refuses new LLM calls once spend ≥ $5; raise on
   demand with `/budget set 10`.
5. **`lyra burn`** breaks down spend by day / repo / model — find
   out which subagent or which provider is bleeding budget.

**Dig deeper:** [Two-tier routing](concepts/two-tier-routing.md) · [Configure providers](howto/configure-providers.md) · [Budgets and quotas](howto/budgets-and-quotas.md).

---

## 6. "I want enterprise-grade safety"

**Problem.** This agent will run against production code. You need
hard policy gates, no destructive surprises, and an audit trail.

**Feature stack.**
[Permission bridge](concepts/permission-bridge.md) → [Permission modes](reference/permission-modes.md) → [Safety monitor](concepts/safety-monitor.md) → [Destructive command detector](features.md#12-safety--permissions) → [HIR + OTel observability](concepts/observability.md) → [Worktree sandbox](concepts/subagents.md).

**One-screen recipe.**

```bash
export LYRA_PERMISSION_MODE=confirm-each-write
export LYRA_OTEL_EXPORTER=otlp://traces.example.com:4317
lyra brain install tdd-strict
lyra --budget 25.00
> /config set safety_monitor=on
> /config set destructive_patterns.strict=on
> /tools                                   # see exactly what's enabled
# every write requires explicit approval; every shell command
# matched against destructive_patterns.yaml is blocked unless
# you type the full command back.
```

**What happens.**

1. **Permission mode `confirm-each-write`** prompts for explicit
   approval on every file write.
2. **Safety monitor** runs a cheap-model classifier every N steps
   against red-team patterns (`safety/redteam.py`) — raises if a
   tool sequence matches a known attack template.
3. **Destructive command detector** matches every shell command
   against `cron/destructive_patterns.yaml` (`rm -rf /`, `DROP
   TABLE`, …) — blocks unless you type the full command back as
   confirmation.
4. **OTel + HIR** export every tool call, hook decision, and
   permission verdict. Audit later via `lyra retro` or your OTel
   collector.
5. **Worktree sandbox** ensures any spawned subagent can't touch
   the parent's working tree.

**Dig deeper:** [Permission bridge](concepts/permission-bridge.md) · [Permission modes](reference/permission-modes.md) · [Safety monitor](concepts/safety-monitor.md) · [Threat model](threat-model.md).

---

## 7. "I want to evaluate the agent against benchmarks"

**Problem.** You're comparing Lyra against another harness, or
proving a regression / improvement, or just want to know your
honest pass rate.

**Feature stack.**
[Eval framework](features.md#14-eval-framework) → [`pass@k` + `pass^k`](features.md#14-eval-framework) → [Rubric scorer](features.md#14-eval-framework) → [Drift-gate](features.md#14-eval-framework) → [τ-bench / Terminal-Bench-2 / SWE-bench-Pro / LoCoEval adapters](features.md#14-eval-framework).

**One-screen recipe.**

```bash
# Run a small golden-task suite under the smart slot, K=4 attempts each
lyra evals --suite golden --passk 4 --json > evals/today.json

# Industry benchmarks
lyra evals --suite tau --emit-submission tau_submission.jsonl
lyra evals --suite terminal-bench-2 --emit-submission tb2_submission.jsonl

# BYO-corpus benchmarks (you supply the JSONL)
lyra evals --suite swe-bench-pro --tasks-path swebp.jsonl
lyra evals --suite loco-eval --tasks-path loco.jsonl

# Drift-gate against your last known-good baseline
lyra evals --suite golden --baseline evals/last_good.json
# Exits non-zero (CI-friendly) if the score drifts beyond threshold.
```

**What happens.**

1. **Eval runner** loads the suite (`golden`, `red-team`, `tau`,
   `terminal-bench-2`, `swe-bench-pro`, `loco-eval`), spins up
   isolated worktrees per task, runs the agent, captures
   `trace.jsonl` + `diff.patch` + `acceptance_tests`.
2. **Scorers run on each task** — `pass@k`, `pass^k` (reliability
   gap), rubric (different-family LLM judge), PRM (process-reward
   model), drift-gate (vs. baseline).
3. **`pass^k`** is your **silent-flakiness detector**. A high
   `pass@4` with a low `pass^4` means "passes sometimes, breaks
   the rest" — the kind of bug that only appears under load.
4. **Adapter outputs** (`--emit-submission`) are upload-ready for
   τ-bench and Terminal-Bench-2.
5. **LoCoEval** drives the 50-turn long-horizon repo conversation
   per sample, enforces the per-turn token budget, and scores
   set-based requirement coverage — bring your own LoCoEval JSONL
   per the published corpus license.

**Dig deeper:** [Run an eval](howto/run-eval.md) · [Eval scorers in features](features.md#14-eval-framework) · [Reference benchmarks in repos](research/repos.md#e-model-weights--benchmark-corpora).

---

## 8. "I want to add a custom tool / skill / hook / MCP server"

**Problem.** You want Lyra to know about your internal API,
private dataset, or proprietary linter.

**Feature stack.**
[MCP adapter](concepts/tools-and-hooks.md) → [Skills](concepts/skills.md) → [Hooks](concepts/tools-and-hooks.md) → [Plugins](howto/write-plugin.md).

**One-screen recipe — MCP server (the one most people want).**

```bash
# Add an MCP server (your internal API, a database, a linter, …)
lyra mcp add company-api \
  --command "python3 -m company_mcp" \
  --env COMPANY_TOKEN=xyz
lyra mcp doctor                            # sanity-check
lyra mcp save                              # persist to .lyra/mcp.toml
lyra
> /mcp                                     # list registered MCP servers
> /tools                                   # confirm the server's tools are visible
```

**One-screen recipe — Skill.**

```bash
mkdir -p ~/.lyra/skills/my-skill
cat > ~/.lyra/skills/my-skill/SKILL.md <<'EOF'
---
id: my-skill
license: MIT
description: Resolve internal Jira tickets by ID
triggers:
  - "JIRA-\\d+"
  - "ticket"
---
# My skill body — markdown describing what to do, with examples.
EOF
lyra skill add ~/.lyra/skills/my-skill
lyra skill smoke my-skill                  # verify it loads + smoke runs
```

**One-screen recipe — Hook.**

```python
# ~/.lyra/hooks/no_secrets.py
from lyra_core.hooks import hook, ToolEvent, HookDecision

@hook("pre_tool_call")
def block_secrets_in_writes(ev: ToolEvent) -> HookDecision:
    if ev.tool_name == "write_file" and "AWS_SECRET" in (ev.args.get("contents") or ""):
        return HookDecision.deny("would write a literal AWS secret")
    return HookDecision.allow()
```

**Dig deeper:** [Add an MCP server](howto/add-mcp-server.md) · [Write a skill](howto/write-skill.md) · [Write a hook](howto/write-hook.md) · [Write a plugin](howto/write-plugin.md).

---

## 9. "I want to replay / audit a past session"

**Problem.** Something weird happened in yesterday's run. You want
to see exactly what the agent did and why.

**Feature stack.**
[Sessions persistence](concepts/sessions-and-state.md) → [HIR](concepts/observability.md) → [Trace viewer](features.md#11-observability--hir) → [Retro](features.md#1-cli-surface) → [`/why`](reference/commands.md#observability).

**One-screen recipe.**

```bash
lyra session list                          # last sessions in this repo
lyra session show abcd1234                 # metadata + summary
lyra retro abcd1234                        # re-run deterministically
# OR resume + inspect interactively:
lyra --resume abcd1234
> /trace                                   # full trace viewer
> /hir                                     # HIR span tree
> /why <tool-call-id>                      # explain a specific call
> /logs                                    # tail this session's logs
```

**What happens.**

1. **Every session is a JSONL log** at `.lyra/sessions/<id>/`
   (turns + trace + diffs + skills used).
2. **`lyra retro`** re-runs against the same inputs (mock LLM
   wraps deterministic responses from the stored trace) — the
   replay is byte-for-byte reproducible.
3. **`/why <id>`** answers questions like *"why did the agent
   grep `auth.py` at step 14?"* by walking the HIR span causally
   back to the prompt that triggered it.

**Dig deeper:** [Sessions and state](concepts/sessions-and-state.md) · [Replay a trace](howto/replay-trace.md).

---

## 10. "I want a team of role-typed agents (PM / Architect / Engineer / QA)"

**Problem.** A solo agent rushes. You want a planning persona to
spec, an architect to decide, an engineer to build, and a QA to
verify.

**Feature stack.**
[Teams](features.md#10-plan-mode--org-mode) → [Brains](features.md#5-memory-subsystem-3-tiers--reasoningbank) → [DAG-Teams](features.md#7-subagents) → [Reflexion](features.md#10-plan-mode--org-mode).

**One-screen recipe.**

```bash
lyra brain install research                # adds the PM/Architect/QA prompts
lyra
> /team show
# pm · architect · engineer · reviewer · qa  (default 5 roles)

> /team plan "Add SSO via SAML to the admin portal"
# pm produces a brief; architect produces a design;
# engineer + qa wait their turn.

> /team run
# Hands off PM → Architect → Engineer (writes code) → Reviewer →
# QA (runs tests). Each role runs in its own subagent worktree;
# the parent thread coordinates handoffs.
```

**What happens.**

1. **`/team show`** lists role descriptions + which model each
   role uses by default (PM = smart slot, Engineer = fast slot,
   etc.).
2. **`/team plan`** is the MetaGPT pattern (paper #15) — each
   role produces its artifact (brief, design, …) and hands off
   role-typed payloads.
3. **`/team run`** is the execution phase — each role runs in
   isolation (worktree subagent), then results merge into the
   parent.
4. **Reflexion** captures lessons per role ("the PM under-spec'd
   the auth requirements") — surfaces next time.

**Dig deeper:** [Teams in features](features.md#10-plan-mode--org-mode) · [paper #15 MetaGPT](research/papers.md#wave-2--performance-edges) · [paper #16 ChatDev](research/papers.md#wave-2--performance-edges).

---

## 11. "I want to embed Lyra into another tool / IDE / custom UI"

**Problem.** You're building a product on top of Lyra — an IDE
plugin, a custom UI, a domain-specific assistant.

**Feature stack.**
[ACP server](features.md#15-integration-surfaces) → [Embeddable Python kernel](features.md#0-four-ways-to-use-lyra) → [LSP backend](features.md#15-integration-surfaces) → [HTTP gateway](features.md#15-integration-surfaces).

**One-screen recipe — ACP.**

```bash
# Speak the Agent Client Protocol over stdio
lyra acp
# Now your IDE plugin / UI sends ACP frames on stdin and reads
# events on stdout. Same agent loop, no REPL.
```

**One-screen recipe — embedded Python kernel.**

```python
from pathlib import Path

from lyra_core.loop import AgentLoop
from lyra_core.providers import provider_for

loop = AgentLoop(
    repo_root=Path.cwd(),
    provider=provider_for("anthropic"),
    permission_mode="confirm-each-write",
)
result = loop.run(task="Add type hints to src/utils.py")
print(result.diff)
```

**One-screen recipe — HTTP gateway.**

```bash
lyra serve --port 8080
# POST /v1/run with {"task": "...", "options": {...}}
# Streaming events on /v1/events?session=<id>
```

**Dig deeper:** [Architecture topology](architecture/topology.md) · [Harness plugins](architecture/harness-plugins.md) · [`lyra_core/acp/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/acp).

---

## 12. "I want to evolve / optimize a prompt automatically"

**Problem.** You have a prompt that works *most* of the time. You
want to find a better one against a held-out task corpus.

**Feature stack.**
[`lyra evolve` (GEPA)](features.md#10-plan-mode--org-mode) → [Pareto-front filtering](features.md#9-test-time-scaling-tts) → [Eval framework](features.md#14-eval-framework).

**One-screen recipe.**

```yaml title="evolve_spec.yaml"
seed_prompt: "You are a careful Python reviewer..."
mutator: templated
score_fn:
  type: rubric
  suite: golden
generations: 8
population: 6
selection: pareto    # score↑ vs length↓ — short + good wins
```

```bash
lyra evolve --task evolve_spec.yaml > evolved.json
# evolved.json: top-K candidates with score, length, lineage
```

**What happens.**

1. **GEPA evolver** generates N mutated prompts per generation
   (templated mutator by default).
2. **Each candidate runs against the score function** (rubric on
   the `golden` suite, in this case).
3. **Pareto-front filtering** keeps candidates that aren't
   dominated on (score, length) — short-and-good beats
   long-and-marginally-better.
4. **Lineage** records which mutations produced which candidates,
   so you can trace why a winner won.

**Dig deeper:** [Evolve in features](features.md#10-plan-mode--org-mode) · [paper #17 DSPy](research/papers.md#wave-2--performance-edges).

---

## 13. "I want a HUD / dashboard for what the agent is doing right now"

**Problem.** You want a live view of cost, context fill, active
tools, and pending todos without opening another window.

**Feature stack.**
[Bottom toolbar (always on)](features.md#14-hud-live-status) → [`lyra hud preview`](features.md#14-hud-live-status) → [`lyra hud inline` for tmux](features.md#14-hud-live-status).

**One-screen recipe.**

```bash
# In any Lyra session you already see the bottom-toolbar (always on):
#   ◆ repo X  │  mode agent  │  model auto  │  turn 1  │  tok 1,691  │  cost $0.0005  │  skin aurora
# (Auto-truncates to terminal width. Make your terminal wider to see all segments.)

# Multi-line preview from the CLI
lyra hud preview --preset full
lyra hud preview --preset compact
lyra hud presets                          # list all 4 presets

# Pipe into tmux's status-right
echo 'set -g status-right "#(lyra hud inline)"' >> ~/.tmux.conf
```

**What happens.**

1. **Bottom toolbar** renders inside the prompt_toolkit REPL via
   `_bottom_toolbar()`. Always on, no flag needed. It's the line
   you've been seeing all along.
2. **`lyra hud preview --preset full`** renders the 9-widget
   multi-line panel — useful for designing your own preset or for
   one-shot status snapshots from CI / scripts.
3. **`lyra hud inline`** is one line, suitable for piping into
   any external status bar (tmux, Starship, byobu).

**Dig deeper:** [Customize the HUD](howto/customize-hud.md) · [HUD in features](features.md#14-hud-live-status).

---

## 14. "I want to run Lyra on a long-horizon project (50+ turns)"

**Problem.** This isn't a one-shot. You're going to be in this
session for hours or days. The context window is going to overflow.

**Feature stack.**
[Context engine](concepts/context-engine.md) → [NGC compaction](features.md#16-cost-optimisation-surface) → [SOUL.md persona](features.md#5-memory-subsystem-3-tiers--reasoningbank) → [Sessions persistence](features.md#13-sessions--persistence) → [`/rewind` / `/redo`](features.md#13-sessions--persistence) → [ReasoningBank](concepts/reasoning-bank.md).

**One-screen recipe.**

```bash
# Pin a session id so you can resume it from any terminal
lyra --session ssn-saml-rollout-202605 --budget 50.00
> /reflect on
> /tdd-gate on
# Work for hours. Hit Ctrl-D when done.

# Tomorrow:
lyra --resume ssn-saml-rollout-202605
> /status                                 # cost, context fill, model, mode
> /rewind                                 # undo the last turn if needed
> /redo                                   # re-apply
```

**What happens.**

1. **Context engine** compacts L1 (working memory) using NGC-style
   block-level eviction at cadence δ (paper #5) — keeps the
   context within budget without losing coherence.
2. **SOUL.md** is *never* compacted — your persona survives every
   compaction.
3. **JSONL persistence** writes every turn to disk; killing the
   process loses zero state.
4. **`--resume`** (or `--continue` for "latest") restores the chat
   history, mode, model, and cost.
5. **`/rewind` + `/redo`** — symmetric undo for the last turn,
   with on-disk JSONL kept in lockstep.
6. **ReasoningBank** accumulates the lessons across days — the
   agent gets *better* over the project's lifetime.

**Dig deeper:** [Context engine](concepts/context-engine.md) · [Sessions and state](concepts/sessions-and-state.md) · [LoCoEval adapter for stress-testing long-horizon runs](features.md#14-eval-framework).

---

## 15. "I want to schedule a hands-off skill (cron-style)"

**Problem.** "Every night at 3 a.m., run the docs-link checker
skill across the repo and open an issue if anything's broken."

**Feature stack.**
[Cron skills](features.md#15-integration-surfaces) → [Skills](concepts/skills.md) → [Hooks](concepts/tools-and-hooks.md).

**One-screen recipe.**

```yaml title="<repo>/.lyra/cron.yaml"
- skill: docs-link-checker
  schedule: "0 3 * * *"          # cron syntax
  on_failure:
    - skill: open-github-issue
      args:
        title: "Broken docs links — {date}"
        body: "{trace_summary}"
```

```bash
# One-shot test
lyra cron run docs-link-checker
# Then deploy as systemd / launchd / GH Actions cron
```

**Dig deeper:** [Cron skills](howto/cron-skill.md) · [Cron module](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/cron).

---

## When to reach for what — at-a-glance

| If your first question is… | Start at… |
|---|---|
| "What can Lyra do?" | This page (you're already here) |
| "What's the full feature list?" | [Features catalogue](features.md) |
| "How does X actually work under the hood?" | [Concepts](concepts/index.md) |
| "How do I do X step-by-step?" | [How-to guides](howto/index.md) |
| "What's the precise CLI / config syntax?" | [Reference](reference/index.md) |
| "Where did this idea come from?" | [Reference papers](research/papers.md) |
| "Which OSS repo does Lyra read for this?" | [Reference repositories](research/repos.md) |
| "Why is the architecture this way?" | [Architecture](architecture/index.md) · [Architecture trade-offs](architecture-tradeoff.md) |
| "What's coming in v1.7 / v2 / v2.5?" | [Roadmap v1.5 → v2](roadmap-v1.5-v2.md) |

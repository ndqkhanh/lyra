# Lyra Upgrade — Master Research & Planning Prompt

## 0. Mission

You are an autonomous research-and-planning agent working on **Lyra**, my MIT-licensed,
terminal-based **multi-agent AI system** (an agent harness in the spirit of Claude Code and
Hermes Agent, but aiming far broader — an *omni-agent* for deep research, coding, solution
architecture, design, SRE, PM/BA, and brainstorming).

**Goal:** research the corpus below exhaustively, then produce concrete, prioritized **upgrade
plans** (and updated docs) that move Lyra toward being the best-performing, most interactive,
most optimized, most autonomous multi-agent system across coding / deep research / solution
architecture / design / SRE. Optimize for genuine state-of-the-art capability and benchmark
competitiveness — not slogans.

Time, context budget, and cost are **not** constraints. Maximum effort.

> **Headline priority:** Lyra's **next flagship feature is Voice Mode (§4.18)** — give it the
> deepest research and the most complete ultra-plan of any workstream, while still completing all
> the others.

## 1. Operating Mode (the loop)

1. **Persist until done.** Work in a loop across all workstreams in §4 and all research targets
   in §3. Do not stop or hand back until every topic below has been (a) researched, (b) turned
   into a concrete plan, and (c) reflected in updated docs. After each pass, re-scan for gaps and
   keep going until there are none.
2. **Checkpoint, don't dump.** After each major workstream, write an intermediate artifact
   (notes + plan) to disk so progress is recoverable and resumable. Treat this like a long-running
   job that can be interrupted and continued.
3. **Be resilient to bad links.** Several URLs may be unreachable, paywalled, or 404. Log each
   failure, skip it, and continue — never let one dead link block the loop. Where a primary source
   is unreachable, find the nearest equivalent (mirror, abstract, summary, or related work).
4. **Clone-and-expand.** For the "awesome list" / paper-list repos in §3.3, clone them, then
   enumerate and research the repos/papers *they* reference (one hop out), prioritizing the most
   relevant to Lyra.
5. **Cite your inspirations.** Every technique you propose adopting must carry a reference link
   (paper or repo) so any builder can trace it back. This applies to both the plans and the docs.
6. **Prioritize.** Rank every proposed change by impact × effort. Flag the breakthrough-tier
   items separately from incremental polish.

## 1.5 Expert Panel (assume these personas when researching, debating, and planning)

When operating in ultracode / dynamic-workflow mode, do NOT reason as a single generalist. Spawn and
embody this panel of senior experts. Each source read, each architecture candidate, and each plan is
debated by the relevant personas BEFORE it is finalized. Each persona owns a domain and carries a
**signature challenge** — the question it always presses — which is what keeps the debate sharp and
realistic rather than agreeable.

- **Senior AI Solutions Architect** — owns end-to-end solution fit. *Challenge: "Do these pieces
  actually compose into one working product that delivers the §0 goal, or is this a pile of features?"*
- **Senior Software Architect** — owns system design, module boundaries, data flow, interfaces.
  *Challenge: "Where are the seams, and what breaks when this scales or a component is swapped?"*
- **Senior Backend Engineer** — owns implementation feasibility: APIs, storage, concurrency, state.
  *Challenge: "Can this actually be built and run reliably, and what's the simplest version that works?"*
- **Senior AI Researcher** — owns whether the technique is real. *Challenge: "What do the papers
  actually show vs. claim — is there real evidence (numbers, ablations), and what's the failure mode?"*
- **Senior AI Engineer (LLMOps)** — owns inference cost, latency, context budgets, evals, provider
  limits. *Challenge: "What does this cost in tokens/latency, and how does it degrade on a weaker
  provider like DeepSeek?"*
- **Senior SRE / Reliability Engineer** — owns reliability, observability, failure modes, ops burden.
  *Challenge: "How does this fail at 3am unattended, how would we even know, and how do we recover?"*
- **Senior Security Engineer** — owns credentials, permissions, sandboxing, injection, agent misuse.
  *Challenge: "What's the blast radius if this is compromised or the agent misbehaves (§4.17)?"*
- **Senior Distributed-Systems Engineer** — owns the swarm/fleet (§4.13) and workflow engine.
  *Challenge: "Where are the races, the coordination bottlenecks, and the consistency assumptions?"*
- **Senior Data / Knowledge Engineer** — owns ingestion, indexing, retrieval, memory plumbing (§3.25).
  *Challenge: "Where does the data come from, how stays it fresh, and how is retrieval grounded?"*
- **Senior Product Manager** — owns scope realism and sequencing. *Challenge: "Is this worth the
  effort, what ships first, and what would we cut under time pressure?"*
- **Senior Product / UX Designer** — owns usability and interaction (§4.1, §4.22). *Challenge: "How
  does a real user discover, steer, interrupt, and trust this?"*
- **Senior Technical Writer / DX** — owns clarity (§6 docs). *Challenge: "Could a new builder
  understand and adopt this from the docs alone?"*
- **Senior ML Evaluation / Benchmark Scientist** — owns measurement honesty and the §3.26 scoreboard.
  *Challenge: "How is this measured, what's the current SOTA to beat, and is the eval rigorous or
  gameable (contamination, leakage, cherry-picked splits)?"*
- **Senior Performance / Cost Engineer** — owns the §3.22 economics. *Challenge: "What does this cost
  per run in tokens, latency, and dollars, where does parallelism stop paying, and what's the
  cache-hit strategy?"*
- **Senior Planning / Reasoning Specialist** — owns the §3.21 deliberation layer. *Challenge: "Does
  this task actually need search/planning, or is single-pass cheaper and just as good — and where does
  explicit planning earn its cost?"*
- **Senior AI Safety / Alignment Engineer** — owns §4.17 and the self-evolution guardrails. *Challenge:
  "How could this misevolve, be jailbroken, or take an unsafe action unattended — and what bounds it?"*
- **Senior Voice / Audio / Realtime Engineer** — owns the §4.18 flagship. *Challenge: "What's the
  end-to-end latency budget, how does barge-in/turn-taking actually feel, and does VI+EN hold up?"*
- **Adversarial Red-Team / Skeptic ("the contrarian")** — owns disconfirmation. Assigned to attack the
  CURRENT front-runner design. *Challenge: "Here is the simplest boring alternative that might beat
  this; prove the added complexity is worth it." Its job is to prevent groupthink and premature
  consensus — it must produce at least one serious objection before any design is finalized.*

**Mandatory personas per topic (convene at least these for each area's debate):**
- §4.2 memory / §3.25 ingestion → AI Researcher + Data/Knowledge Engineer + Architect + Performance.
- §4.3 context/compaction → AI Engineer (LLMOps) + Performance + AI Researcher.
- §4.4 skills / §3.18 self-evolution → AI Researcher + Backend + Safety + Solutions Architect.
- §4.5 router / §3.22 economics → AI Engineer + Performance + Architect.
- §4.13 swarm + workflow engine / "ultracode" → Distributed-Systems + SRE + Architect + Performance.
- §4.14 autonomy + §3.20 self-knowledge → AI Researcher + Safety + SRE + PM.
- §3.21 planning layer → Planning Specialist + AI Researcher + Performance.
- §4.16 reliability + §3.26 benchmarks → SRE + Evaluation Scientist + Backend.
- §4.17 safety + §3.24 sandboxing → Safety + Security + Distributed-Systems.
- §4.18 voice → Voice/Audio + AI Engineer + UX + Performance.
- §4.1 UI/UX + §4.22 steering → UX + Product Manager + Technical Writer.
The **Adversarial Skeptic joins every architecture-level and breakthrough debate**, regardless of topic.

**Rules of engagement (prompt-engineering discipline):**
- Argue from your discipline; challenge others' assumptions; demand evidence (real numbers, cited
  papers) over assertion. Disagreement is the point — surface it, don't smooth it over.
- The goal is the MOST REALISTIC, buildable, grounded design that survives cross-disciplinary
  scrutiny — not the most impressive-sounding one. Red-team optimistic claims and "it just works."
- Make trade-offs explicit and attribute them: who objects, on what grounds, and how it's resolved.
- No design, plan, or architecture is finalized until the relevant personas have signed off that it
  is feasible, grounded, and honestly stated — or the unresolved disagreement and its decisive
  trade-off is recorded.
- Match the persona to the task: don't convene all of them for a trivial decision; convene the ones
  who own the judgment at hand (see the mandatory-personas map above). Reserve the full panel for
  architecture-level and breakthrough calls.
- **Anti-groupthink (required):** no design is finalized on first agreement. At least one persona must
  voice a substantive objection and the panel must address it; if everyone agrees immediately, the
  Adversarial Skeptic must manufacture the strongest opposing case anyway before sign-off.
- **Steelman the loser:** when a candidate is rejected, record the STRONGEST version of it and the
  single decisive reason it lost — so the choice is defensible and revisitable on a later run.
- **One voice at a time, attributed:** in the debate record, attribute each claim to its persona
  (e.g. "SRE: …", "Skeptic: …") so disagreements are legible and not blended into a consensus mush.

## 2. Reference: Lyra's current state

Lyra's UI/UX is already solid. The point of studying Hermes Agent and the Claude Code docs is to
**find specific things we can port into Lyra** — not to rebuild what already works. Where Lyra
already has a capability, propose enhancements rather than replacements.

---

## 3. Research Corpus (read / fetch / clone — all of it)

> **Expand the corpus with TOP-VENUE papers.** Beyond the links listed here, actively search for and
> pull in more recent, highly-cited, high-profile papers relevant to each workstream — but hold a
> QUALITY BAR on venue and track:
> - **Venues:** A / A*-ranked only (CORE A/A* or equivalent) — e.g. NeurIPS, ICML, ICLR, ACL, EMNLP,
>   NAACL, CVPR, ICCV, ECCV, AAAI, IJCAI, KDD, SIGIR, COLM, TMLR, and similarly top venues for the
>   topic.
> - **Track:** main / findings / spotlight / oral / poster from the MAIN proceedings only. Do **NOT**
>   rely on workshop, demo, short non-archival, or non-peer-reviewed tracks as primary evidence
>   (they're fine only as a pointer to a stronger source). The §3.4 MemAgent workshop set is the one
>   deliberate exception already curated here.
> - **Recency + impact:** prefer the last ~18 months and well-cited / highly-discussed work; verify
>   the venue and track before trusting a paper, and record venue+track+year in findings.
> - arXiv preprints are acceptable when they are the canonical version of work accepted at such a
>   venue, or are clearly high-impact; note the publication status. When in doubt about venue/track,
>   verify rather than assume, and never invent a venue.
> This applies to every §3 subsection below and to the synthesis: ground breakthroughs in top-tier,
> peer-reviewed evidence, not gray literature.

### 3.1 Claude Code official docs (mine for portable features)
- **Skills — ⭐ the standout Claude Code feature; primary input for the §4.4 skills system:**
  - Claude Code Skills (Agent Skills open standard + Claude Code's extensions: invocation control,
    subagent execution, dynamic context injection; bundled skills like /code-review /debug /loop;
    `.claude/skills/<name>/SKILL.md` format): https://code.claude.com/docs/en/skills
  - Agent Skills overview (architecture, pre-built vs custom, SKILL.md frontmatter):
    https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
  - Agent Skills best practices (authoring + naming conventions):
    https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  - Agent Skills in the SDK (filesystem loading via setting_sources, the `Skill` tool, allowed-tools
    behavior — key for Lyra's harness-level, provider-agnostic loader in §4.4):
    https://platform.claude.com/docs/en/agent-sdk/skills
  - Note: the Agent Skills format is an **open standard** (works across Claude Code, Codex, Gemini
    CLI, Cursor, Hermes, etc.) — this is exactly why Lyra can implement a model-agnostic skills
    system; see also the §3.7 skills repos.
- Plugins: https://code.claude.com/docs/en/plugins-reference
- Tools: https://code.claude.com/docs/en/tools-reference
- Goals / automation: https://code.claude.com/docs/en/goal
- Hooks guide: https://code.claude.com/docs/en/hooks-guide
- Hooks reference: https://code.claude.com/docs/en/hooks
- MCP: https://code.claude.com/docs/en/mcp
- Interactive mode: https://code.claude.com/docs/en/interactive-mode
- Commands: https://code.claude.com/docs/en/commands
- Checkpointing / sessions: https://code.claude.com/docs/en/checkpointing
- Permissions: https://code.claude.com/docs/en/permissions
- Agent teams (swarm): https://code.claude.com/docs/en/agent-teams
- Channels: https://code.claude.com/docs/en/channels-reference
- Env vars / credentials: https://code.claude.com/docs/en/env-vars
- **More Claude Code docs (grouped; mine each for portable features):**
  - Core CLI & config: CLI reference https://code.claude.com/docs/en/cli-reference ·
    settings https://code.claude.com/docs/en/settings ·
    model config https://code.claude.com/docs/en/model-config ·
    terminal config https://code.claude.com/docs/en/terminal-config ·
    glossary https://code.claude.com/docs/en/glossary
  - Sub-agents (→ §4.13 swarm): https://code.claude.com/docs/en/sub-agents
  - Tool search (agent-SDK dynamic tool discovery → §4.6): https://code.claude.com/docs/en/agent-sdk/tool-search
  - UI/UX (→ §4.1): keybindings https://code.claude.com/docs/en/keybindings ·
    statusline https://code.claude.com/docs/en/statusline ·
    fullscreen https://code.claude.com/docs/en/fullscreen ·
    output styles https://code.claude.com/docs/en/output-styles
  - Voice dictation (→ §4.18 flagship voice mode): https://code.claude.com/docs/en/voice-dictation
  - Security & isolation (→ §4.17 safety): sandboxing https://code.claude.com/docs/en/sandboxing ·
    sandbox environments https://code.claude.com/docs/en/sandbox-environments ·
    security https://code.claude.com/docs/en/security
  - Observability & cost (→ §4.16 reliability + §4.5 router cost targets):
    monitoring usage https://code.claude.com/docs/en/monitoring-usage ·
    costs https://code.claude.com/docs/en/costs
  - Effort & orchestration (→ §4.14 effort scale + §4.13 swarm; the "ultracode" building blocks):
    effort levels https://code.claude.com/docs/en/model-config#adjust-effort-level ·
    dynamic workflows https://code.claude.com/docs/en/workflows ·
    effort (API semantics) https://platform.claude.com/docs/en/build-with-claude/effort ·
    fast mode https://code.claude.com/docs/en/fast-mode
  - ⭐ **Agent View — the background-session FLEET layer (research preview, CC v2.1.139+); a flagship
    port target → §4.13 fleet + §4.14 autonomy + §4.22 steering + §4.11 sessions + §5.1 rmux:**
    https://code.claude.com/docs/en/agent-view
    > WHAT IT IS: `claude agents` opens one full-terminal screen managing every *background* session —
    > each a complete Claude Code conversation that keeps running with NO terminal attached. You
    > dispatch tasks as rows, watch state at a glance, peek/reply without attaching, and attach for the
    > full conversation only when needed. This is the "run many agents unattended and steer by
    > exception" model — distinct from subagents (spawned within one session) and agent teams (peers
    > that message each other); agent view manages top-level independent sessions.
    > ARCHITECTURE TO REPLICATE (decompose into primitives for Lyra):
    >   (1) SUPERVISOR/DAEMON — a per-user host process, separate from the terminal, that owns session
    >       lifecycle. Starts on first background/agent-view use; hosts each session as its OWN process;
    >       persists state on disk (roster.json + per-job state.json under ~/.claude/jobs/<id>/);
    >       survives terminal close, auto-updates, supervisor restarts, and machine sleep (reconnects on
    >       wake); stops idle unattached sessions after ~1h to free resources and respawns them from
    >       disk on next peek/reply/attach; sheds idle-then-pinned sessions under memory pressure;
    >       self-exits when nothing is live. Lyra needs an equivalent supervisor for a true detached
    >       fleet — this is the spine of §4.14 autonomy.
    >   (2) STATE MODEL — two orthogonal axes: task-state (Working/Needs-input/Idle/Completed/Failed/
    >       Stopped) AND process-liveness (alive / exited-but-resumable / loop-sleeping). Rows group by
    >       Ready-for-review / Needs-input / Working / Completed; blocked + open-PR rows stay pinned-
    >       visible. Lyra's §4.13 fleet view should adopt this exact orthogonality (what the agent is
    >       doing vs whether its process is hot).
    >   (3) CHEAP ROW SUMMARIES — a Haiku-class model writes the one-line "what this session is doing/
    >       needs/produced" per row, refreshed ≤ once/15s + at each turn end. Key design idea: a small
    >       cheap model powers the monitoring surface so you never open transcripts → ties to §4.5
    >       router (use the cheapest model for meta/monitoring) + §4.22 steering.
    >   (4) STEER-BY-EXCEPTION UX — peek panel (latest output / the exact question / PRs) with
    >       multiple-choice hotkeys + `Tab` suggested-reply + `!`-prefixed bash; attach/detach that
    >       never stops the session; `←`-to-background any live session into the fleet; filters
    >       (a:agent, s:state, #PR); pin/reorder/rename. This is the §4.22 human-steering reference
    >       implementation — interrupt/redirect/approve without babysitting.
    >   (5) FILE-EDIT ISOLATION — before first edit, a background session auto-moves into a git worktree
    >       under .claude/worktrees/ so parallel sessions share a checkout but each writes its own;
    >       skip-conditions + a `worktree.bgIsolation:"none"` escape + a WorktreeCreate hook for non-git
    >       VCS. Directly informs §5.1 rmux and the §4.13 parallel-execution safety story.
    >   (6) DISPATCH SURFACE — from agent view input, from inside a session (`/bg`), or shell
    >       (`claude --bg`, `--name`, `--agent`, `--model`, `--effort`, `--permission-mode`); `! cmd`
    >       runs a PTY shell job as a row (no model); per-session model/effort/permission override;
    >       quota is consumed per-session (N agents ≈ N× usage). Shell-scriptable mgmt: agents/--json/
    >       attach/logs/stop/respawn/respawn --all/rm/daemon status.
    > TRADE-OFFS TO CARRY INTO THE PLAN: per-session quota multiplies cost (the §4.5 router + §3.22
    > economics must govern fleet size); sessions are LOCAL (survive sleep, die on shutdown → recover by
    > re-attach); Claude-created worktrees are destroyed on session-delete (uncommitted work lost unless
    > pushed) — a real data-loss footgun Lyra must handle more safely. SECURITY (→ §4.17): bypass/auto
    > permission modes are gated behind a one-time interactive accept before any unwatched session can
    > use them — Lyra's autonomous fleet needs the same "you can't silently grant an unwatched agent
    > dangerous permissions" guardrail.
    > LYRA TRANSFERABLE IDEA: build the supervisor + fleet-view as the concrete realization of
    > §4.13 (fleet of detached sessions, not just in-session subagents) + §4.14 (they run unattended) +
    > §4.22 (steer-by-exception peek/reply) — and make the row-summary model a deliberate §4.5 cheap-
    > model routing decision. This is arguably the highest-leverage UX/architecture port available.
  - ⭐ **Worktrees — the parallel-edit ISOLATION primitive under the fleet/swarm (→ §4.13 parallel
    execution + §4.11 sessions + §5.1 rmux; the safety substrate Agent View's primitive (5) depends
    on):** https://code.claude.com/docs/en/worktrees
    > WHAT IT IS: each parallel session/subagent runs in its own git worktree — a separate working
    > directory with its own files + branch but sharing one repo history/remote — so edits in one
    > session never touch another's. This is the mechanism that makes a fleet of concurrent agents SAFE
    > to run on one checkout. Distinct from subagents/teams (which coordinate the WORK); worktrees
    > isolate the FILES.
    > MECHANISM TO REPLICATE (decompose for Lyra's §4.13/§5.1):
    >   • Creation: `claude --worktree <name>` (or `-w`) makes `.claude/worktrees/<name>/` on branch
    >     `worktree-<name>`; auto-generates a name if omitted; an in-session `EnterWorktree` tool lets
    >     the agent move itself into/between worktrees on demand (the previous one stays on disk). Lyra
    >     needs the equivalent: a tool the agent calls to isolate itself before editing.
    >   • Base-branch policy: branches from `origin/HEAD` (clean tree matching remote) by DEFAULT, falls
    >     back to local HEAD if no remote; `worktree.baseRef:"head"` makes worktrees carry unpushed
    >     commits/feature state (needed when isolating subagents that must operate on in-progress work);
    >     `#<PR>`/PR-URL branches from `pull/<n>/head` into `.claude/worktrees/pr-<n>`. The fresh-vs-head
    >     choice is a real design decision Lyra must expose.
    >   • Gitignored-file propagation: a `.worktreeinclude` file (.gitignore syntax) copies matched-AND-
    >     gitignored files (e.g. `.env`, secrets) into each new worktree — only gitignored ones, so
    >     tracked files are never duplicated. Lyra's fleet needs this or every isolated session starts
    >     without its env/secrets and breaks.
    >   • Subagent isolation: `isolation: worktree` in subagent frontmatter (or "use worktrees for your
    >     agents") gives each subagent a temp worktree auto-removed if it finishes with no changes →
    >     directly the §4.13 parallel-subagent safety story.
    >   • Cleanup state machine: clean exit (no uncommitted/untracked/new-commits) → worktree+branch
    >     auto-removed (named sessions prompt instead); dirty exit → PROMPT keep-or-remove (remove
    >     DISCARDS uncommitted work — the data-loss footgun); `-p` non-interactive runs are NOT
    >     auto-cleaned; a `cleanupPeriodDays` sweep removes only clean Claude-created subagent/background
    >     worktrees, never `--worktree` ones.
    >   • Non-git VCS: `WorktreeCreate`/`WorktreeRemove` hooks replace the default git logic entirely
    >     (the doc shows an SVN checkout hook reading the name from stdin, printing the dir); note
    >     `.worktreeinclude` is then NOT processed — the hook must copy local config itself.
    > TRADE-OFFS / FOOTGUNS TO IMPROVE ON (→ §4.13/§4.17): removing a dirty worktree silently discards
    > uncommitted changes + untracked files + local commits — Lyra should default to SAFER (auto-stash/
    > archive/confirm, never silent-destroy); each worktree is a full checkout (disk + per-tree env
    > setup cost — deps/venvs must be re-initialized per worktree); outside a git repo there's no
    > isolation unless a WorktreeCreate hook is configured, so parallel sessions editing the same files
    > collide. TRANSFERABLE IDEA: make worktree-isolation the substrate Lyra's fleet/swarm writes
    > through — an agent isolates (its own tool call) before any edit, env propagates via a
    > .worktreeinclude analog, cleanup is non-destructive by default, and non-git repos fall back to a
    > hook or a copy-on-write/overlay scheme rather than unsafe shared edits.
  - What's new (track latest Claude Code features to port): https://code.claude.com/docs/en/whats-new ·
    https://code.claude.com/docs/en/whats-new/2026-w20 · https://code.claude.com/docs/en/whats-new/2026-w19

### 3.2 Comparable harnesses (port their tools + UX)
- Hermes Agent: https://github.com/nousresearch/hermes-agent
- Kilo Code — all-in-one open-source agentic engineering platform (VS Code / JetBrains / CLI /
  Slack / Cloud; Architect/Coder/Debugger/Analyst modes, MCP marketplace, 500+ models, `--auto`
  fully-autonomous flag, Memory Bank persistent context; Apache-2.0 — note its CLI is a fork of
  OpenCode): https://github.com/Kilo-Org/kilocode
- Kilo Marketplace — curated Skills / MCP servers / Modes for the Kilo ecosystem (study the skill +
  mode packaging): https://github.com/Kilo-Org/kilo-marketplace
- OpenClaw — MIT self-hosted autonomous AI agent (formerly Moltbot/Clawdbot): BYOK model router
  across OpenAI/Anthropic/Google/DeepSeek/local, persistent long-term memory, `SOUL.md` personality
  file, modular TypeScript skill system, 50+ messaging integrations. Primary entry via the curated
  list (verify the canonical core repo from there): https://github.com/SamurAIGPT/awesome-openclaw
- (already in §3.11) opencode: https://github.com/anomalyco/opencode — relevant here too since
  Kilo CLI forks it.

**Broader harness landscape (study architecture + UX; star counts approximate, verify):**
- DeerFlow 2.0 — ByteDance (MIT) ⭐ closest analog to Lyra: open-source long-horizon **SuperAgent
  harness** that researches, codes, and creates via sandboxes + persistent memory + tools + skills
  + subagents + a message gateway; LangGraph stateful-graph orchestration, Docker-sandboxed agents,
  five roles (Coordinator/Planner/Researcher/Coder/Reporter), model-agnostic (any OpenAI-compatible
  API), embeddable as a Python lib, report+PPT+podcast deliverables, TIAMAT cloud memory backend.
  Study orchestration, sandboxing, the skill system, and the gateway: https://github.com/bytedance/deer-flow
- OpenCode — the most-starred provider-agnostic terminal harness (MIT, 75+ providers, terminal +
  desktop + IDE): https://github.com/sst/opencode
- Pi — Armin Ronacher (notable for a sub-1,000-token system prompt + lazy-loading skill system that
  injects instructions only when needed; directly relevant to §4.3/§4.4): https://github.com/getpi/pi
- Goose — Block / Linux Foundation (autonomous local agent, CLI + desktop, MCP-native, "Recipes"
  for recurring workflows): https://github.com/block/goose
- Cline — model-agnostic VS Code agent with Plan/Act oversight, permissioned file/terminal/browser/
  MCP access, parallel agents (Apache-2.0): https://github.com/cline/cline
- Aider — git-native terminal pair-programmer (repomap + automatic commits; Apache-2.0): https://github.com/Aider-AI/aider
- Crush — terminal coding agent (FSL→MIT): https://github.com/charmbracelet/crush

### 3.2.5 MANGO Company AI/ML Engineering Blogs (NEW — June 2026 deep research)
> Production AI agent patterns from the largest tech companies. Mine for architecture patterns,
> reliability practices, and platform design — not just papers but how they ship agents at scale.
> Deep-dive each blog post/source; extract actionable patterns for Lyra.

**Meta AI Research (FAIR):**
- Hyperagents / DGM-H (ICLR 2026): self-improving agents rewriting own harness, SWE-bench 20%→50%,
  cross-domain meta-skill transfer. Paper: https://arxiv.org/pdf/2603.19461 ·
  Code: https://github.com/facebookresearch/HyperAgents
- Dr. Zero (Jan 2026): zero-data self-evolving search agents, proposer-solver co-evolution, HRPO
  algorithm. Paper: https://arxiv.org/pdf/2601.07055
- MetaAgent-X (May 2026): end-to-end trainable multi-agent systems, Designer+Executor co-evolution
  via GRPO. Paper: https://arxiv.org/pdf/2605.14212 · Code: https://github.com/pettingllms-ai/PettingLLMs
- Production AI Agents at Hyperscale (May 2026): unified agents autonomously optimizing global infra.
  https://www.infoq.com/news/2026/05/meta-ai-agents-hyperscale/

**Google DeepMind / Google AI:**
- Co-Scientist (Nature, May 2026): multi-agent research system, Generate→Debate→Evolve phases, idea
  tournament from AlphaGo. https://deepmind.google/blog/co-scientist-a-multi-agent-ai-partner-to-accelerate-research/
- Aletheia (Feb 2026): Generator-Verifier-Reviser architecture, 95.1% IMO-Proof Bench, solved 4 open
  Erdős problems. https://gigazine.net/gsc_news/en/20260212-google-deep-gemini-mind-aletheia/
- AI Co-Mathematician (May 2026): hierarchical agent, 48% FrontierMath Tier 4, 7 design principles
  for research-agent UX. https://www.technologyreview.com/2026/05/22/1137813/
- Agent Scaling Science (Apr 2026): 260 configs, diminishing returns after ~45% single-agent accuracy.
  Paper: https://arxiv.org/html/2512.08296v3
- Demis Hassabis AGI Interview (Apr 2026): 3 missing pieces — Continual Learning, Long-term Reasoning,
  True Memory. "Einstein Test" as AGI benchmark.

**OpenAI:**
- Fully Automated AI Researcher (Mar 2026): AI research intern by Sep 2026, full system by 2028.
  https://www.technologyreview.com/2026/03/20/1134438/
- Harness Engineering (Feb 2026): 1M lines production code, zero human-written — the harness IS the
  product. "Most important engineering discipline of 2026."
- GPT-5.5 & Agentic Computing (2026): Codex as early agent platform, multi-step autonomous work.

**Apple Machine Learning Research:**
- On-Device AI Agent (2026): autonomous iOS app operation, sub-200ms latency, >90% success across
  50+ apps. On-device via Neural Engine.
- Ferret-UI Lite (2026): 3B on-device GUI agent, 53.3% ScreenSpot-Pro, beats 7B competitor by 15pts.
- Core AI Framework (WWDC 2026): native Agent Architecture replacing Core ML — intent recognition,
  task planning, tool calling, Dynamic MoE, local sandboxed memory in Secure Enclave.
- PORTool (ACL 2026 Workshop): policy optimization for multi-tool agents, step-level importance scores.
- UX for Computer Use Agents (Feb 2026): taxonomy of UX considerations, Wizard-of-Oz validation.
  https://machinelearning.apple.com/research/mapping

**Netflix Technology Blog:**
- Multi-Agent Platform Engineering (May 2026, Code w/ Claude): Lead agent decomposition → specialized
  sub-agents (deployment history, error logs, metrics, tickets) → parallel event-driven collaboration
  on shared filesystem. "Adversarial code review": Agent A writes → Agent B evaluates → Agent C
  orchestrates. Incident investigations: hours → minutes.
  https://www.theregister.com/software/2026/04/04/netflix-meta-ibm-speakers-discuss-ai-and-their-workdays/
- 4-Pillar Gen AI Platform (prerequisite before agents): throttling/resiliency + Braintrust evaluation
  + MCP-standardized tool ecosystem + dedicated RAG. Without this, "near-zero adoption."
- AI Agents for Advertising (May 2026): autonomous ad buying/optimization, $3B revenue target.
- 70% of 2027 pipeline planned for agentic workflows on LangChain 0.4 + Weaviate 1.25.

> **Cross-company synthesis & Lyra implications:** See docs/999-mango-ai-blogs-jun-2026.md for the
> full analysis. Key patterns: (1) Harness > Model, (2) Adversarial verification is production-
> standard, (3) Self-improving agents are the 2026 frontier, (4) Memory is the AGI bottleneck,
> (5) Terminal-native is the winning form factor, (6) MCP is consolidating despite growing pains.

### 3.3 Paper lists & awesome lists (clone these, then research the repos/papers they link)
- AI agent papers: https://github.com/masamasa59/ai-agent-papers
- Agent memory paper list: https://github.com/Shichun-Liu/Agent-Memory-Paper-List
- Awesome harness engineering: https://github.com/ai-boost/awesome-harness-engineering
- Awesome MCP servers: https://github.com/punkpeye/awesome-mcp-servers
- Awesome context engineering: https://github.com/yzfly/awesome-context-engineering
- Awesome Context Engineering (Meirtz): https://github.com/Meirtz/Awesome-Context-Engineering
- Context Engineering for AI Agents — Lessons from Building Manus:
  https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

### 3.4 Memory papers — ICLR 2026 MemAgent Workshop (basis for the new Lyra memory architecture)
Deep-dive each, then synthesize a **proposed breakthrough memory architecture for Lyra** (see §4.2):
> Note: entries below without a description (QufkvHbQs7, YPoHy6lgKP, Tts94WVw40,
> nmFfyHEs76, Qr5bhBbBOb, tc9GAKlxQC, um6VpjcOtj, eC4ygDs02R, jL7fwchScm, K3n5jPkrU6, 1cymflI2Lh,
> BSYn7ah4KX, jrSc4RJXy1) couldn't be auto-resolved during prompt prep (fetch cache collisions);
> open each URL directly at runtime to read its title/abstract before deep-diving.
- https://openreview.net/pdf?id=AIJsjIqfsp — *Memory Transplants for LLM Agents* (UCSD): disentangles memory **architecture** vs. **content** transfer across a code→math shift; architecture transfer is system-dependent, weaker models gain more (→ §4.2)
- https://openreview.net/pdf?id=FiM0M8gcct — *A-MEM: Agentic Memory* (Rutgers): Zettelkasten-style dynamically linked/evolving memory notes (workshop version of arXiv 2502.12110) (→ §4.2)
- https://openreview.net/pdf?id=iGRGjdhl9r — *Did You Check the Right Pocket? Cost-Sensitive Store Routing* (Gaikwad): picks **which memory store** to query as a cost-sensitive routing problem; selective retrieval cuts tokens + improves accuracy (→ §4.2 + §4.5)
- https://openreview.net/pdf?id=lVn5vLOkjP — *SelfEvoWM*: generate–verify–repair self-evolving loop for DROID-grounded generative world models with a VLM consistency critic (robotics; loop pattern → §4.4/§4.16)
- https://openreview.net/pdf?id=xOW2jXDKG3 — *Norm-Guided KV-Cache Eviction*: gradient-free KV-cache compression scoring tokens by ℓ2-norm of key vectors (→ §4.3 context/auto-compaction)
- https://openreview.net/attachment?id=UTRuEFJ57H&name=pdf — *R-KVHash*: SimHash/LSH-based KV-cache compression that evicts redundant reasoning-trace tokens, ~2× decoding throughput (→ §4.3 context)
- https://openreview.net/attachment?id=l9Ly41xxPb&name=pdf — *From Storage to Experience: A Survey on the Evolution of LLM Agent Memory* — frames memory as Storage→Reflection→Experience; design roadmap (strong → §4.2 anchor)
- https://openreview.net/forum?id=hQgSl6kj1W — *Experiential Reflective Learning* (Illuin): reflects on trajectories to generate reusable heuristics retrieved at test time; +7.8% over ReAct on Gaia2 (→ §4.4/§4.2)
- https://openreview.net/pdf?id=Y8Txo8vaH7 — *LP-RAG: Link Prediction-Based RAG* (Souza et al.): graph RAG that casts retrieval as inductive link prediction over chunk–query links (LLM-prompted chunker + synthetic per-chunk queries); model-agnostic predictor (→ §4.2 memory/retrieval)
- https://openreview.net/attachment?id=En2z9dckgP&name=pdf — *SABER: Small Actions, Big Errors* (Amazon AGI): distinguishes mutating vs non-mutating actions; mutation-gated verification + targeted reflection + context cleaning; +28% Airline; also releases τ-Bench Verified (→ §4.16 verifier + §4.17 safety)
- https://openreview.net/attachment?id=Q16XXJou3O&name=pdf — *AOI: Multi-Agent Framework for Intelligent IT Operations*: 3 agents + context compressor + 3-layer (Working/Episodic/Semantic) memory; 72.4% compression, −34.4% MTTR (→ §4.16 SRE + §4.2 + §4.13)
- https://openreview.net/pdf?id=QufkvHbQs7
- https://openreview.net/attachment?id=GeaPE7iw1V&name=pdf — *MemGrad* (TCS): textual gradients turn batched feedback into retrospective/prospective memory + prompt updates (no fine-tuning); applied to multi-agent AgileCoder (→ §4.4 + §4.2 + §4.13)
- https://openreview.net/pdf?id=YPoHy6lgKP
- https://openreview.net/pdf?id=Tts94WVw40
- https://openreview.net/attachment?id=ztmwHisqJ4&name=pdf — *Agentic Memory Should Localize Compression* (KAIST): position paper — compress within modular memory units to minimize retrieval–update interference/drift (→ §4.2 + §4.3)
- https://openreview.net/pdf?id=nmFfyHEs76
- https://openreview.net/attachment?id=Uw5G3H26ps&name=pdf — *Feedback Descent*: open-ended text-artifact optimization (prompts/code/molecules) via pairwise textual-rationale feedback at inference time; matches GEPA, beats GRPO (→ §4.4 prompt/skill optimization)
- https://openreview.net/pdf?id=Qr5bhBbBOb
- https://openreview.net/pdf?id=tc9GAKlxQC
- https://openreview.net/pdf?id=um6VpjcOtj
- https://openreview.net/attachment?id=mmdqUrEY24&name=pdf — *A-MAC: Adaptive Memory Admission Control* (Workday): five-factor (future utility / confidence / novelty / recency / type) memory admission; LoCoMo F1 0.583, −31% latency (→ §4.2)
- https://openreview.net/pdf?id=eC4ygDs02R
- https://openreview.net/pdf?id=jL7fwchScm
- https://openreview.net/pdf?id=K3n5jPkrU6
- https://openreview.net/pdf?id=1cymflI2Lh
- https://openreview.net/pdf?id=BSYn7ah4KX
- https://openreview.net/pdf?id=jrSc4RJXy1
- **Browse the full workshop for more papers:**
  https://openreview.net/group?id=ICLR.cc/2026/Workshop/MemAgent&referrer=%5BHomepage%5D(%2F)#tab-accept

### 3.5 Core agent / research-agent / RL / algorithm-discovery papers
> **Auto-categorize on read.** This is a mixed inbox of agent papers (many are 2026 arXiv IDs).
> When you fetch each one, read the abstract and route its insights to the workstream it actually
> belongs to — memory→§4.2, context→§4.3, voice→§4.18, routing→§4.5, reliability→§4.16,
> safety→§4.17, skills/self-improvement→§4.4, deep research→§4.15, swarm→§4.13, tools→§4.6 — rather
> than treating every paper as generic. Note each paper's resolved title + mapped workstream in the
> research log. If an ID 404s (some new-year IDs may differ), log it and find the nearest match.

**⭐ HIGH-PRIORITY — Pre-researched June 2026 papers (titles verified, deep-dived):**
- https://arxiv.org/pdf/2603.19461 — **Hyperagents / DGM-H** (Meta/UBC, ICLR 2026): Darwinian Gödel Machine, self-improving agents rewriting own harness, SWE-bench 20%→50%, cross-domain meta-skill transfer (→ §4.4 + §4.14)
- https://arxiv.org/pdf/2601.07055 — **Dr. Zero** (Meta/UIUC): zero-data self-evolving search agents via proposer-solver co-evolution, HRPO algorithm, beats supervised baselines 14.1% (→ §4.4 + §4.15)
- https://arxiv.org/pdf/2605.14212 — **MetaAgent-X**: end-to-end trainable multi-agent systems, Designer+Executor co-evolution via GRPO, Qwen3 8B 38.33% avg (→ §4.13)
- https://arxiv.org/pdf/2603.17187 — **MetaClaw**: continual meta-learning in production, skill-driven fast adaptation + opportunistic LoRA fine-tuning, zero downtime (→ §4.4 + §4.14)
- https://arxiv.org/pdf/2605.20189 — **SOLAR** (AAAI 2026): self-optimizing autonomous reasoner, parameter-level meta-learning, plasticity-stability balance (→ §4.4)
- https://arxiv.org/pdf/2605.16217 — **Argus**: Searcher-Navigator deep research architecture, shared evidence graph, BrowseComp 86.2 (→ §4.15)
- https://arxiv.org/pdf/2605.10813 — **NanoResearch**: tri-level co-evolving multi-agent research, Skill Bank + Memory Module + SDPO planner (→ §4.15)
- https://arxiv.org/pdf/2605.22662 — **Claw AI Lab**: autonomous multi-agent research team, code harness, real-time dashboard (→ §4.15)
- https://arxiv.org/pdf/2603.05344 — **Building AI Coding Agents for the Terminal** (OpenDev): 5-role compound AI, adaptive context compaction, 5-layer safety architecture (→ §4.1 + §4.3)
- https://arxiv.org/pdf/2604.17658 — **ErrorProbe** (KCL/Amazon Alexa): semantic failure attribution in MAS, 3-stage pipeline pinpointing responsible agent (→ §4.16)
- https://arxiv.org/pdf/2601.01685 — **Lying with Truths** (Hu et al.): first cognitive collusion attack, truthful evidence + LLM overthinking = belief manipulation (→ §4.17)
- https://arxiv.org/pdf/2604.08708 — **MATU**: uncertainty quantification for multi-agent systems via tensor decomposition (→ §4.16 + §4.19)
- https://arxiv.org/pdf/2605.22154 — **IdleSpec**: speculative planning during tool-waiting idle time, 2-3× agent loop speedup (→ §4.14 + §4.21)
- https://arxiv.org/pdf/2604.04820 — **ANX Protocol**: 3EX decoupled architecture, 47-66% token reduction vs MCP (→ §4.8 + §4.3)
- https://arxiv.org/pdf/2603.23013 — **Knowledge Access Beats Model Size**: memory lets cheap small model answer repeat queries, expensive model handles first-time (→ §4.5 + §4.2)
- https://arxiv.org/pdf/2604.13552 — **TF-TTCL**: training-free test-time contrastive learning, Explore-Reflect-Steer loop, works on ANY provider (→ §4.4)

**Additional ICLR 2026 Memory Papers (MemAgent Workshop deep-dives):**
- https://openreview.net/pdf?id=MemGAS — **MemGAS**: multi-granularity memory (session/turn/summary/keyword), GMM clustering + entropy routing, 38.4% over HippoRAG 2 (→ §4.2)
- https://github.com/bingreeky/MemGen — **MemGen**: generative latent memory tokens woven into inference stream, no external DB, open-source (→ §4.2)
- https://openreview.net/forum?id=CraniMem — **CraniMem**: neurocognitive gated bounded multi-stage memory, active forgetting reduces noise 11-16% (→ §4.2)
- https://openreview.net/forum?id=REMem — **REMem**: episodic memory reasoning, +13.4% reasoning vs Mem0/HippoRAG 2 (→ §4.2)
- https://openreview.net/forum?id=LightMem — **LightMem** (ZJU/NUS/NJU): bio-inspired sensory→short→long-term memory, 105× token reduction, 309× fewer API calls (→ §4.2 + §4.21)

**GEPA & Neuro-Symbolic:**
- https://github.com/gepa-ai/gepa — **GEPA** (ICLR 2026 Oral): reflective prompt evolution outperforming RL (GRPO), gradient-free (→ §4.4)

**Original uncategorized list (fetch + categorize each):**
- https://arxiv.org/pdf/2605.24220
- https://arxiv.org/pdf/2605.29790
- https://arxiv.org/pdf/2605.29341
- https://arxiv.org/pdf/2605.29795
- https://arxiv.org/pdf/2605.29796
- https://arxiv.org/pdf/2605.29225
- https://arxiv.org/pdf/2605.27366
- https://arxiv.org/pdf/2605.25815
- https://arxiv.org/pdf/2605.25480
- https://arxiv.org/pdf/2605.25430
- https://arxiv.org/pdf/2605.24426
- https://arxiv.org/pdf/2605.23989
- https://arxiv.org/pdf/2605.22721
- https://arxiv.org/pdf/2605.22794
- https://arxiv.org/pdf/2605.22343
- https://arxiv.org/pdf/2605.17734
- https://arxiv.org/pdf/2605.16233
- https://arxiv.org/pdf/2605.13941
- https://arxiv.org/pdf/2605.12061
- https://arxiv.org/pdf/2605.11891
- https://arxiv.org/pdf/2604.18976
- https://arxiv.org/pdf/2604.18005
- https://arxiv.org/pdf/2604.16543
- https://arxiv.org/pdf/2604.12461
- https://arxiv.org/pdf/2604.07791
- https://arxiv.org/pdf/2510.18407
- https://arxiv.org/pdf/2509.26100
- https://arxiv.org/pdf/2508.21720
- https://arxiv.org/pdf/2508.04482
- https://arxiv.org/pdf/2507.03928
- https://arxiv.org/pdf/2506.03939
- https://arxiv.org/pdf/2506.02546
- https://arxiv.org/pdf/2505.24575
- https://arxiv.org/pdf/2505.18581
- https://arxiv.org/pdf/2505.18218
- https://arxiv.org/pdf/2502.11271
- https://arxiv.org/pdf/2604.06170 — *(ORAL paper — couldn't auto-resolve title via search; open directly at runtime, title + categorize, likely high-impact given oral acceptance)*
- https://arxiv.org/pdf/2605.27276
- https://arxiv.org/pdf/2605.30152
- https://arxiv.org/pdf/2512.13564
- https://arxiv.org/pdf/2605.26112
- https://arxiv.org/pdf/2507.02825v1 — *Establishing Best Practices for Building Rigorous Agentic Benchmarks*: shows reward/setup flaws in SWE-bench Verified & τ-bench, introduces the Agentic Benchmark Checklist (→ §4.16 reliability/eval)
- https://arxiv.org/pdf/2506.02153 — *Small Language Models are the Future of Agentic AI* (NVIDIA): SLMs are sufficient/cheaper for repetitive agent calls; heterogeneous multi-model systems — theory backing for the §4.5 model router
- https://arxiv.org/pdf/2506.01716 — *Self-Challenging Language Model Agents* (Meta/Berkeley): agent generates its own Code-as-Task problems (instruction + verifier + tests) to self-train (→ §4.4 self-evolving skills)
- https://arxiv.org/pdf/2506.21931 — *ARAG: Agentic RAG for Personalized Recommendation*: 4-agent RAG pipeline (user-understanding/NLI/summary/ranker) over long-term + session context (→ §4.2 memory/retrieval, swarm)
- https://arxiv.org/pdf/1809.01703
- https://arxiv.org/pdf/2502.12110v1 — *A-MEM: Agentic Memory for LLM Agents*: Zettelkasten-style dynamically linked memory notes (contextual descriptions/keywords/tags) (→ §4.2 memory; see §3.17)
- https://arxiv.org/pdf/2605.23904
- https://arxiv.org/pdf/2605.20025
- https://arxiv.org/pdf/2604.25917
- https://arxiv.org/pdf/2605.14038
- https://arxiv.org/pdf/2603.28052
- https://arxiv.org/abs/2605.15184
- https://arxiv.org/abs/2605.18747
- https://arxiv.org/pdf/2510.26854 — *SciencePedia / Inverse Knowledge Search*: decompresses science into a verifiable Long-CoT knowledge base via a Socratic agent + cross-model consensus (→ §4.15 research, §4.16 verifier)
- https://arxiv.org/pdf/2605.13821
- https://arxiv.org/abs/2605.03042
- https://arxiv.org/pdf/2605.09942
- https://arxiv.org/pdf/2605.28773v1
- https://arxiv.org/pdf/2605.18661
- https://arxiv.org/pdf/2605.06716
- https://arxiv.org/pdf/2604.26622
- https://arxiv.org/pdf/2604.20261
- https://arxiv.org/pdf/2604.16839
- https://arxiv.org/pdf/2604.14362
- https://arxiv.org/pdf/2604.12776
- https://arxiv.org/pdf/2604.07798
- https://arxiv.org/pdf/2602.01766
- https://arxiv.org/pdf/2602.01566
- https://arxiv.org/pdf/2601.10702
- https://arxiv.org/pdf/2511.02805 — *MemSearcher*: search agent keeps a compact question-relevant memory across turns (stable context) trained with multi-context GRPO (→ §4.2/§4.3/§4.15)
- https://arxiv.org/pdf/2508.06433 — *Memp: Agent Procedural Memory*: learnable/updatable lifelong procedural memory distilled from past trajectories into steps + scripts, with Build/Retrieve/Update (→ §4.2/§4.4)
- https://arxiv.org/pdf/2506.06698 — *Contextual Experience Replay* (Princeton): training-free self-improvement; synthesizes past experience into an in-context memory buffer agents retrieve from (→ §4.4/§4.2)
- https://arxiv.org/pdf/2506.06254 — *PersonaAgent*: test-time personalization via episodic+semantic memory + per-user persona prompt that shapes actions and is refined by outcomes (→ §4.2 memory)
- https://arxiv.org/pdf/2604.25135
- https://arxiv.org/pdf/2605.24018
- https://arxiv.org/pdf/2604.23626
- https://arxiv.org/pdf/2602.23008
- https://arxiv.org/pdf/2602.00428
- AMAGO (Grigsby/Fan/Zhu 2023 — scalable in-context RL with long-sequence Transformers for
  generalization, long-term memory & meta-learning; foundational adaptive-agent RL): https://arxiv.org/pdf/2310.09971
- ProRL Agent Server (RL training/serving for agents): https://github.com/NVIDIA-NeMo/ProRL-Agent-Server
- AlphaEvolve (Gemini-powered algorithm-design agent):
  https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf
- Stanford CS191W project (Humishka / Zope):
  https://cs191w.stanford.edu/projects/Spring2025/Humishka___Zope_.pdf
- Microsoft Research — Code Researcher:
  https://www.microsoft.com/en-us/research/wp-content/uploads/2025/06/Code_Researcher-1.pdf

### 3.6 AutoScientists — self-organizing scientific agent teams (model for §4.15)
- Project: https://autoscientists.openscientist.ai
- Paper: https://arxiv.org/abs/2605.28655
- GitHub: https://github.com/mims-harvard/AutoScientists
> Decentralized teams of agents that generate hypotheses, design/run experiments, write code,
> analyze failures, and revise strategy as evidence accumulates — self-organizing around the most
> promising leads and keeping a shared success/failure log to avoid redundant work. Study the
> coordination model, the shared memory/log, and the adversarial critique-before-spend pattern,
> and propose how Lyra's research swarm should adopt it.
- AutoResearchClaw (auto/deep-research agent — study for §4.15):
  https://github.com/aiming-lab/AutoResearchClaw
- VirSci — "Many Heads Are Better Than One" (Su et al., Oct 2024 — "Virtual Scientists": a team of
  agents that collaboratively GENERATE, EVALUATE, and REFINE research ideas, mimicking real scientific
  teamwork; beats SOTA on producing novel ideas. A concrete idea-generation model for the §4.15
  research swarm): https://arxiv.org/pdf/2410.09403

### 3.7 Skills systems & skill libraries (basis for §4.4)
- ⭐ SkillNet — ZJU-NLP ("npm for AI skills"): end-to-end search / install / **create / evaluate /
  organize**; auto-generates skill packages (SKILL.md + scripts/references/assets) from GitHub
  repos, PDFs, conversation logs, or execution trajectories; scores skills on 5 quality dimensions;
  organizes them into a structured **skill graph** (similarity/composition/dependency) + ships an
  MCP server. Covers nearly the whole §4.4 curator/loader/creator/auto-evaluator pipeline — study
  the creation pipeline, the eval rubric, and the graph model closely:
  https://github.com/zjunlp/SkillNet · tech report https://arxiv.org/pdf/2603.04448
- https://github.com/MontrealAI/skillos
- https://github.com/kepano/obsidian-skills
- https://github.com/multica-ai/andrej-karpathy-skills
- https://github.com/forrestchang/andrej-karpathy-skills
- https://github.com/obra/superpowers
- https://github.com/microsoft/SkillOpt
- https://github.com/Imbad0202/academic-research-skills
- https://github.com/SafeRL-Lab/cheetahclaws
- https://github.com/HKUDS/CLI-Anything
- "oh-my-claude" / oh-my-openagent: https://github.com/code-yeongyu/oh-my-openagent
- claude-skills — alirezarezvani (large multi-platform library: 330+ skills / 30+ agents / 70+
  commands across engineering, research, PM, product, finance, etc.; stdlib-only Python tools,
  converts to Claude Code / Codex / Gemini CLI / Hermes / Cursor — strong source for §4.4's
  concrete skills): https://github.com/alirezarezvani/claude-skills

### 3.8 Terminal multiplexers & multi-agent orchestration (basis for §5.1 rmux rebuild)
- tmux: https://github.com/tmux/tmux
- cmux: https://github.com/manaflow-ai/cmux
- rmux: https://github.com/Helvesec/rmux
- Warp terminal: https://github.com/warpdotdev/warp
- alphaclaw: https://github.com/chrysb/alphaclaw
- AgentsMesh (multi-tenant — evaluate for §5.2): https://github.com/AgentsMesh/AgentsMesh

### 3.9 Memory / context / graph repos
- TencentDB Agent Memory: https://github.com/Tencent/TencentDB-Agent-Memory
- Acontext: https://github.com/memodb-io/Acontext
- claude-mem: https://github.com/thedotmack/claude-mem
- MemPalace: https://github.com/MemPalace/mempalace
- graphify: https://github.com/safishamsi/graphify
- codegraph: https://github.com/colbymchenry/codegraph
- spaCy (NLP for memory/extraction): https://github.com/explosion/spaCy

### 3.10 Autonomy / continuous-operation
- continuous-claude (full-autonomy loop): https://github.com/AnandChowdhary/continuous-claude

### 3.11 Other agent frameworks / harnesses to mine
- gbrain: https://github.com/garrytan/gbrain
- gstack: https://github.com/garrytan/gstack
- ruflo: https://github.com/ruvnet/ruflo
- opencode: https://github.com/anomalyco/opencode
- CowAgent: https://github.com/zhayujie/CowAgent
- opendev: https://github.com/opendev-to/opendev
- multica: https://github.com/multica-ai/multica
- openhuman: https://github.com/tinyhumansai/openhuman
- rtk: https://github.com/rtk-ai/rtk
- caveman: https://github.com/juliusbrussee/caveman
- abtop: https://github.com/graykode/abtop
- ECC: https://github.com/affaan-m/ECC
- DCI-Agent-Lite: https://github.com/DCI-Agent/DCI-Agent-Lite
- Claude Code best practices: https://github.com/shanraisshan/claude-code-best-practice

### 3.12 Workflows, swarms, UX-sound references
- Companies as a graph of algorithms (workflow modeling):
  https://danielmiessler.com/blog/companies-graph-of-algorithms
- RoadMapper (BUPT, Apr 2026 — multi-agent system for research-roadmap generation: 3 stages =
  initial generation → knowledge augmentation → iterative critique-revise-evaluate; ships the RoadMap
  benchmark; the critique-revise-evaluate loop → §4.15 scientist research + §4.16 verifier):
  https://arxiv.org/pdf/2604.27616
- ⭐ Latent Agents (Boston U, Apr 2026 — *Internalized Multi-Agent Debate*: distills multi-agent
  debate INTO a single LLM via 2-stage fine-tuning; matches/exceeds explicit debate at up to 93%
  FEWER tokens; finds agent-specific subspaces in activation space. Key tension for Lyra: explicit
  debate (our §4.13 panel/review) is token-expensive — consider when to internalize vs. run live
  debate; the Skeptic should weigh this. → §4.13 + §4.3 cost):
  https://arxiv.org/pdf/2604.24881
- ⭐ Actor-Observer Asymmetry / ReTAS (Li et al., Apr 2026 — multi-agent role-play induces a cognitive
  BIAS: an agent as actor (self-reflection) blames external factors; as observer (auditing others)
  blames internal faults — perspective-swap triggers it in >20% of cases. Ships an Ambiguous Failure
  Benchmark + ReTAS (Thesis-Antithesis-Synthesis dialectical alignment) to fix it. CRITICAL caveat
  for our debate/review panels — reviewers may systematically mis-attribute failures. → §4.13 + §4.16):
  https://arxiv.org/pdf/2604.19548
- MAGEO — "From Experience to Skill" (Apr 2026 — multi-agent generative-engine optimization:
  planning/editing/fidelity-eval agents execute, validated edit patterns are distilled into reusable
  engine-specific SKILLS; experience→skill distillation → §4.4 skills creator/learner + §3.18):
  https://arxiv.org/pdf/2604.19516
- ETI — "Explicit Trait Inference for Multi-Agent Coordination" (USC/Amazon, Apr 2026 — agents infer +
  track partner traits along warmth/trust & competence/skill from interaction history to coordinate;
  cuts payoff loss 45-77% in economic games, +3-29% on MultiAgentBench vs CoT → §4.13 swarm coordination):
  https://arxiv.org/pdf/2604.19278
- GTD — "Guided Topology Diffusion" (Jiang et al., Oct 2025 — generates TASK-ADAPTIVE multi-agent
  communication topologies via guided discrete graph diffusion, steered by a proxy predicting multi-
  objective rewards (accuracy/utility/cost); gradient-free, real-time, balances performance vs token
  cost vs robustness → §4.13 swarm topology + §3.22 economics): https://arxiv.org/pdf/2510.07799
- ⭐ "When Identity Skews Debate" (Choi/Zhu/Li, UW-Madison, Oct 2025 — multi-agent debate suffers
  identity-driven sycophancy + self-bias; formalizes it as identity-weighted Bayesian update, fixes it
  via RESPONSE ANONYMIZATION (strip identity markers so agents can't tell self from peer → equal
  weighting), defines Identity Bias Coefficient (IBC). Concrete fix for our debate panels — anonymize
  the debate; pairs with Actor-Observer Asymmetry → §4.13 + §4.16): https://arxiv.org/pdf/2510.07517
- RADAR — "Debating the Unspoken" (Apr 2026 — role-anchored multi-agent debate for *omission-aware*
  fact verification: Politician vs Scientist over shared evidence + neutral Judge + dual-threshold
  early-termination to cut reasoning cost; → §4.16 verifier + §4.13 debate):
  https://arxiv.org/pdf/2604.19005
- ⭐ ErrorProbe — "Towards Self-Improving Error Diagnosis in MAS" (KCL/Amazon Alexa, Apr 2026 — semantic
  FAILURE ATTRIBUTION: pinpoints the responsible agent + originating error step via 3-stage pipeline
  (failure-taxonomy anomaly detection → symptom-driven backward tracing → Strategist/Investigator/
  Arbiter team validating via tool-grounded execution). Directly relevant to debugging Lyra's own
  swarm + the §4.16 verifier; pairs with the HAFC failure-attribution idea in §0):
  https://arxiv.org/pdf/2604.17658
- MARS² — "Scaling Multi-Agent Tree Search via RL for Code Generation" (Apr 2026 — multiple
  independently-optimized agents collaborate inside a shared, LEARNABLE tree-structured search
  environment; bridges §3.21 planning/tree-search + §4.13 swarm + coding): https://arxiv.org/pdf/2604.14564
- MHGPO — "End-to-End Optimization of LLM-Driven Multi-Agent Search Systems via Heterogeneous-Group-
  Based RL" (mid-2025 — trains multi-agent search systems end-to-end; Multi-Agent Heterogeneous Group
  Policy Optimization estimates relative advantages across heterogeneous rollout groups, avoiding
  MAPPO's large critic networks / instability / memory cost → §4.13 swarm + training): https://arxiv.org/pdf/2506.02718
- Cultural-Alignment Debate (Ki et al., mid-2025 — two-agent debate for equitable cultural alignment;
  one variant pure-debate, another dynamically switches self-reflection vs debate per turn; 7 open
  models / 21 combos on NormAd-ETI, debate improves accuracy + cultural-group parity. Domain tangential
  but the self-reflect-vs-debate SWITCHING mechanism is useful → §4.13): https://arxiv.org/pdf/2505.24671
- ⭐ Tree-of-Debate (ToD; Feb 2025 — converts scientific papers into LLM personas that debate their
  respective novelties, dynamically building a DEBATE TREE for fine-grained analysis of independent
  novelty arguments. A structured method for "what's actually novel vs incremental" — directly useful
  for the baseline/novelty-assessment + the architecture debate → §4.13 + baseline review): https://arxiv.org/pdf/2502.14767
- DITS — "Efficient MAS Training with Data Influence-Oriented Tree Search" (Feb 2025 — improves
  MCTS-based synthetic-data generation for self-training MAS by guiding tree search + data selection
  with INFLUENCE scores (not just Q-values); influence estimation for non-differentiable metrics cuts
  compute → §4.13 swarm training + §3.18 self-improving): https://arxiv.org/pdf/2502.00955
- ⭐ "Preventing Rogue Agents Improves Multi-Agent Collaboration" (Barbi et al., Feb 2025 — tackles the
  single-point-of-failure problem where one agent sinks the whole task (e.g. terminating early while
  uncertain); MONITORS agents during action prediction + intervenes when a future error is likely;
  ships WhoDunitEnv. Pairs with the debate-bias/collusion cluster → §4.16 reliability + §4.13):
  https://arxiv.org/pdf/2502.05986
- Cross-Team Collaboration (CTC; Du/Qian et al., Jun 2024 — ChatDev lineage; multiple LLM agent TEAMS
  propose + communicate decisions in parallel, exploring multiple decision paths in the solution space
  instead of a single waterfall development chain → §4.13 swarm/fleet + coding): https://arxiv.org/pdf/2406.08979
- GenesisFunc (Xu et al., Apr 2026 — automated multi-agent pipeline generating function-calling
  TRAINING DATA from reliable benchmark tools; dialogue-generation system spanning diverse scenarios +
  multi-stage evaluation for quality/diversity → §4.6 tools/function-calling + §3.12 data synthesis):
  https://arxiv.org/pdf/2605.28835
- DRT — "Deep Reasoning Translation via Long CoT" (Wang et al., Dec 2024 — brings o1-style long-CoT to
  literary machine translation (similes/metaphors) via a multi-agent long-thought DATA-SYNTHESIS
  framework; domain tangential but the multi-agent thought-sample synthesis is the transferable bit
  → §3.12): https://arxiv.org/pdf/2412.17498
- CollabCoder — "Plan-Code Co-Evolution" (Apr 2026 — plan module + code module co-evolve via a
  collaborative decision process that picks which to run during debugging; matches/beats SOTA at lower
  compute, gains grow with task difficulty → §4.13 + coding): https://arxiv.org/pdf/2604.13946
- Murder-Mystery multi-agent scripts (Apr 2026 — collaborative multi-agent synthesis of role-driven
  multiplayer game scripts to train VLMs on multi-hop reasoning under imperfect/deceptive info;
  tangential to Lyra but useful for imperfect-information multi-agent reasoning → §4.13): https://arxiv.org/pdf/2604.11741
- Adversarial/agentic-workflow security: https://arxiv.org/abs/2605.11229
- Anthropic — agentic misalignment (safety, §4.17):
  https://www.anthropic.com/research/agentic-misalignment
- Warcraft III peon voice notifications for Claude Code:
  https://freedium-mirror.cfd/https://medium.com/@gentechimports/warcraft-iii-peon-voice-notifications-for-claude-code-a-developers-story-dd6842deb852
- Adding sound effects to Claude Code with hooks:
  https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/
- **Claude Code Dynamic Workflows — official announcement** (May 28, 2026, w/ Opus 4.8):
  https://claude.com/blog/introducing-dynamic-workflows-in-claude-code
- **Workflows — official docs** (the authoritative spec): https://code.claude.com/docs/en/workflows
- **Effort levels — official docs** (low/medium/high/xhigh/max; ultracode is NOT an API level):
  https://code.claude.com/docs/en/model-config#adjust-effort-level · https://platform.claude.com/docs/en/build-with-claude/effort
- Sub-agents (workflow workers): https://code.claude.com/docs/en/sub-agents

> **⭐ REPLICATE "ultracode" IN LYRA — study and rebuild for Lyra's swarm.** Dynamic workflows are in
> **research preview** (Claude Code v2.1.154+; Pro enables via the Dynamic workflows row in
> `/config`; on by default for Max/Team/Enterprise/API). IMPORTANT framing: **"ultracode" is not a
> model or a monolithic feature** — per Anthropic's effort docs it is *not* an additional API effort
> level. It is a thin Claude Code session setting that bundles `xhigh` reasoning effort + automatic
> dynamic-workflow orchestration. "Replicate ultracode" therefore decomposes into FOUR capabilities
> Lyra must build, each mapped to a workstream:
>   1. **Effort scale (→ §4.14 / §4.5).** A per-session reasoning-budget control. Claude Code's
>      `/effort` menu lists SIX selectable items — **low / medium / high / xhigh / max / ultracode**
>      — so in the UI ultracode is the top entry, a peer of the others. Under the hood, though, the
>      first five map to provider reasoning budgets while **ultracode is special**: selecting it
>      sends `xhigh` to the model AND flips on auto-orchestration (see #2) — it is not a distinct
>      6th budget tier at the API. Lyra should mirror this: expose all six in its `/effort` menu, map
>      low→max to per-provider thinking-token budgets (Anthropic budget_tokens; DeepSeek/others'
>      nearest equivalent or a prompt-level analog), and implement ultracode as "xhigh + orchestration
>      toggle" rather than as a sixth budget request — which is what makes it portable to providers
>      that only expose a couple of effort levels.
>   2. **Auto-orchestration toggle = "ultracode" (→ §4.14 + §4.13).** When ON, Lyra DECIDES ON ITS
>      OWN whether a task warrants a workflow rather than waiting to be asked; a single request can
>      fan into several workflows in a row — one to *understand*, one to *change/act*, one to
>      *verify* (the understand→change→verify loop). Session-scoped, resets on new session, drop back
>      to "high" for routine work. Also support the lighter trigger: the literal keyword **"workflow"**
>      in a prompt spins up a one-off fan-out without changing session effort.
>   3. **Dynamic-workflow engine (→ §4.13 swarm).** A **code-driven** orchestration script Claude
>      WRITES (JS/`workflow.js`-style) and the runtime executes in the BACKGROUND while the session
>      stays responsive. Intermediate results live in **script variables, not the orchestrator's
>      context window** — that's the key token/reliability win vs. turn-by-turn subagents. Must be
>      **resumable** mid-run, support pause/resume/stop/restart per agent, and expose a progress view
>      (phases × agent count × token total × elapsed). Cap concurrency (Anthropic caps at **1000
>      subagents/run**; real runs have hit errors near ~47 concurrent needing review — pick a safe
>      default + backpressure).
>   4. **Repeatable quality pattern + bundled `/deep-research` (→ §4.15 + §4.16).** The engine's value
>      isn't just "more agents": independent agents draft from several angles and/or **adversarially
>      review each other's findings, vote on each claim, and filter out claims that don't survive
>      cross-checking** before reporting — converging on a more trustworthy result. Ship a bundled
>      deep-research workflow (fan out searches across angles → fetch + cross-check → vote → cited
>      report) as Lyra's analog, and let users **save** a good run's script as a reusable command.
> Decision boundary to port (from the docs' subagents-vs-skills-vs-workflows table): use a workflow
> when the plan should live IN CODE (repeatable, resumable, dozens–hundreds of agents); use
> subagents/skills when Claude should hold the plan turn-by-turn. Be deliberate about token cost —
> ultracode is a "default-on swarm," so every substantive task costs more; start tightly scoped.

### 3.13 Voice & audio agents — ⭐ flagship corpus (feeds §4.18)
*Verify star counts / leaderboard positions before relying on them — this space moves monthly.*

**Frameworks / toolkits (cascaded STT→LLM→TTS pipelines):**
- Pipecat (real-time voice/multimodal agent framework): https://github.com/pipecat-ai/pipecat
- LiveKit Agents (realtime voice agents + WebRTC + telephony): https://github.com/livekit/agents
- TEN Framework (lower-level, multi-language realtime agent framework): https://github.com/TEN-framework/TEN-Agent
- Pipecat Smart Turn (open semantic turn detection, 23 langs incl. Vietnamese + English):
  https://github.com/pipecat-ai/smart-turn
- Silero VAD (de-facto open voice-activity detector): https://github.com/snakers4/silero-vad

**Speech-to-speech / full-duplex models (architecture references):**
- Moshi — Kyutai (first real-time full-duplex spoken LLM, Mimi codec): https://github.com/kyutai-labs/moshi · paper https://arxiv.org/abs/2410.00037
- CSM — Sesame (open conversational speech model, Llama backbone): https://github.com/SesameAILabs/csm
- OpenAI gpt-realtime / Realtime API (proprietary S2S baseline — barge-in, semantic VAD, MCP):
  https://developers.openai.com/api/docs/guides/realtime

**Open TTS / STT:**
- Kokoro-82M TTS (tiny, fast, high-quality, Apache): https://github.com/hexgrad/kokoro
- Orpheus TTS (expressive, emotion tags, voice cloning, low latency): https://github.com/canopyai/Orpheus-TTS
- NVIDIA Parakeet / Canary STT (NeMo — top of HF Open ASR leaderboard): https://github.com/NVIDIA/NeMo
- Whisper large-v3 / turbo (best multilingual open ASR baseline, strong VI+EN): https://github.com/openai/whisper
- Open ASR Leaderboard (reproducible ASR benchmark): https://arxiv.org/abs/2510.06961

**Voice-agent benchmarks (evaluation targets for §4.18):**
- Full-Duplex-Bench v1 (turn-taking, backchannel, interruption): https://arxiv.org/abs/2503.04721
- Full-Duplex-Bench v3 (disfluency + multi-step tool use): https://arxiv.org/abs/2604.04847
- τ-Voice (full-duplex voice over verifiable real-world tasks): https://arxiv.org/abs/2603.13686

### 3.14 LLM / model routing (feeds §4.5)
- RouteLLM — LMSYS/Berkeley (reference routing repo): https://github.com/lm-sys/RouteLLM · paper https://arxiv.org/abs/2406.18665
- Hybrid LLM — Microsoft (ICLR 2024, cost/quality router): https://github.com/microsoft/best-route-llm
- BEST-Route — Microsoft (ICML 2025, route model + #samples by difficulty): https://arxiv.org/abs/2506.22716
- FrugalGPT — Stanford (seminal LLM cascade / cost optimization): https://arxiv.org/abs/2305.05176
- "Knowledge Access Beats Model Size: Memory-Augmented Routing for Persistent AI Agents" (2026 —
  compound strategy where memory lets a cheap small model answer repeat queries while the expensive
  model handles only the first; the §4.2 memory ↔ §4.5 router bridge): https://arxiv.org/pdf/2603.23013
- ⚠️ "The Bitter Lesson of Diffusion LMs for Agentic Workflows" (SEU/Alibaba/NTU, Jan 2026 — NEGATIVE
  RESULT: diffusion LLMs (LLaDA, Dream), despite latency appeal, fail as agentic backbones — can't
  branch under temporal feedback in embodied tasks, can't hold strict JSON schemas under diffusion
  noise in tool-calling (Agentboard/BFCL). Router guidance: do NOT route agentic/tool tasks to dLLMs
  → §4.5 + §3.20 reliability): https://arxiv.org/pdf/2601.12979

### 3.15 Reliability / observability / verification (feeds §4.16)
- Langfuse (open LLM observability: tracing, evals, prompt mgmt): https://github.com/langfuse/langfuse
- OpenLLMetry — Traceloop (OpenTelemetry instrumentation for LLMs): https://github.com/traceloop/openllmetry
- Arize Phoenix (open LLM/agent tracing + eval on OTel): https://github.com/Arize-ai/phoenix
- τ-bench — Sierra (tool-agent-user reliability, pass^k metric): https://github.com/sierra-research/tau-bench · https://arxiv.org/abs/2406.12045
- τ²-bench — Sierra (dual-control conversational agent benchmark): https://github.com/sierra-research/tau2-bench · https://arxiv.org/abs/2506.07982
- SWE-bench Verified (human-validated coding-agent benchmark): https://www.swebench.com/verified.html

### 3.16 Safety / alignment / agent security (feeds §4.17)
- LlamaFirewall — Meta (open agent guardrail: PromptGuard 2, alignment checks, CodeShield):
  https://github.com/meta-llama/PurpleLlama/tree/main/LlamaFirewall · https://arxiv.org/abs/2505.03574
- Llama Guard — Meta (open input/output safety classifier): https://arxiv.org/abs/2312.06674
- NeMo Guardrails — NVIDIA (programmable runtime rails / Colang): https://github.com/NVIDIA-NeMo/Guardrails · https://arxiv.org/abs/2310.10501
- AgentDojo — ETH Zurich (NeurIPS 2024 prompt-injection attack/defense benchmark): https://github.com/ethz-spylab/agentdojo · https://arxiv.org/abs/2406.13352
- CaMeL "Defeating Prompt Injections by Design" — Google DeepMind (control/data-flow separation):
  https://github.com/google-research/camel-prompt-injection · https://arxiv.org/abs/2503.18813
- Progent — Berkeley/UCSB (programmable least-privilege tool-call control): https://github.com/sunblaze-ucb/progent · https://arxiv.org/abs/2504.11703
- "Your Agent May Misevolve" (Shao et al. 2025 — emergent risks in self-evolving agents:
  safety-alignment decay after memory accumulation, vulnerabilities from tool creation/reuse,
  across model/memory/tool/workflow pathways; the safety guardrail the §4.4 self-evolving skills
  system must defend against): https://arxiv.org/pdf/2509.26354
- ⭐ "Lying with Truths: Open-Channel Multi-Agent Collusion for Belief Manipulation" (Hu et al., Jan
  2026 — formalizes the FIRST cognitive collusion attack: colluding agents steer a victim's beliefs
  using only TRUTHFUL evidence fragments posted on public channels (no covert comms/backdoors/fakes),
  exploiting LLM overthinking; Writer-Editor-Director framework + CoPHEME dataset. Critical threat for
  Lyra's §4.13 channels/swarm — agents sharing a channel can be collusively manipulated → §4.17):
  https://arxiv.org/pdf/2601.01685

### 3.17 Memory & context (supplements §3.4 / §3.9; feeds §4.2 / §4.3)
- Mem0 (scalable cross-session memory layer): https://github.com/mem0ai/mem0 · https://arxiv.org/abs/2504.19413
- Letta / MemGPT — Berkeley ("LLM-as-OS" self-editing memory, paging): https://github.com/letta-ai/letta
- Zep / Graphiti (temporal knowledge-graph memory): https://github.com/getzep/graphiti
- Awesome-Memory-for-Agents (paper list): https://github.com/TsinghuaC3I/Awesome-Memory-for-Agents
- Anthropic — Effective Context Engineering for AI Agents (compaction + memory tool):
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- ACON — adaptive agent context compression (26–54% memory cut): https://arxiv.org/abs/2510.00615
- lean-ctx (MIT, single Rust binary — hybrid context optimizer: a shell-hook that transparently
  compresses CLI output BEFORE it reaches the LLM + an MCP server with 8 tools for cached file reads
  / dependency maps / entropy-filtered reads; claims 89–99% token cut via filter/group/truncate/dedup
  per command type + a "Token Dense Dialect" symbol shorthand. The sibling/superset of §3.11's rtk —
  read both for the §4.3 context-bloat + §4.8 MCP work; concrete, portable token-reduction middleware):
  https://github.com/yvgude/lean-ctx
- AnnaAgent (Wang et al. 2025 — tertiary memory integrating short- + long-term across multiple
  sessions; multi-session memory design): https://arxiv.org/pdf/2506.00551
- MemAgent (ICLR 2026 oral — the workshop's namesake: processes long text in segments, updates
  memory via an overwrite strategy, extends DAPO to optimize memory end-to-end; extrapolates 8K →
  3.5M tokens with <10% loss, >95% on 512K NIAH): https://openreview.net/forum?id=k5nIOvYGCL
- DAVIS (Pham Dinh et al. 2024 — generalist scientific/lab planning agent with a knowledge-graph-powered
  inner monologue for structured/temporal reasoning + safety): https://arxiv.org/pdf/2410.09252
- MSI-Agent (Fu et al. 2024 — Multi-Scale Insight: experience selector + insight generator + insight
  selector to summarize/retrieve long-term-memory insights across scales for planning): https://arxiv.org/pdf/2409.16686
- ⭐ Field-Theoretic Memory for AI Agents (Mitra, Jan 2026 — NOVEL paradigm: memory as continuous
  *fields governed by PDEs*, not discrete DB entries; memories diffuse through semantic space, decay
  thermodynamically by importance, couple across agents in multi-agent settings; +116% F1 multi-
  session reasoning on LongMemEval, open code. A genuinely fresh §4.2 direction worth deep study):
  https://arxiv.org/pdf/2602.21220
- COMPASS (Wan et al., Oct 2025 — names context management as the long-horizon bottleneck; hierarchical
  framework separating tactical execution (Main Agent), strategic oversight (Meta-Thinker issuing
  interventions), and context organization (Context Manager keeping concise progress briefs) →
  §4.3 context/auto-compaction + §4.13 + §3.21 planning): https://arxiv.org/pdf/2510.08790
- ExtAgents — "Scaling External Knowledge Input Beyond Context Windows via Multi-Agent Collaboration"
  (Liu et al., mid-2025 — scales inference-time knowledge integration BEYOND the context window by
  distributing massive input across agents; no long-context training, avoids context-extension info
  loss; ships ∞Bench+ multi-hop QA + long survey generation. Direct alternative to long-context for the
  harness → §4.3 context scaling + §4.2 + §3.25 ingestion): https://arxiv.org/pdf/2505.21471
- Coarse-to-Fine Grounded Memory (CFGM; Yang et al. 2025, rev. Feb 2026 — grounds multi-granularity
  coarse→fine memories with the LLM, beyond single-granularity experience, for flexible agent
  planning; cited by the §3.4 Memory Transplants paper): https://arxiv.org/pdf/2508.15305
- Survey: "Memory for Autonomous LLM Agents — Mechanisms, Evaluation, and Emerging Frontiers"
  (2026; decomposition/formalization of agent memory, mechanism trade-offs, downstream-performance
  evaluation — strong §4.2 anchor): https://arxiv.org/pdf/2603.07670

### 3.18 Self-improving / self-evolving agents (feeds §4.4 / §4.15)
- Darwin Gödel Machine — UBC/Sakana (self-rewriting coding agent, SWE-bench 20%→50%):
  https://github.com/jennyzzt/dgm · https://arxiv.org/abs/2505.22954
- SEAL "Self-Adapting Language Models" (Zweiger et al., MIT 2025 — model generates its own
  finetuning data + update directives ("self-edits") that produce *persistent weight updates*,
  trained via an RL loop rewarded by downstream performance; the weight-level end of the
  self-evolution spectrum vs. the prompt/memory-level methods elsewhere): https://arxiv.org/pdf/2506.10943
- ADAS "Automated Design of Agentic Systems" — UBC (ICLR 2025, meta agent search):
  https://github.com/ShengranHu/ADAS · https://arxiv.org/abs/2408.08435
- AlphaEvolve — Google DeepMind (evolutionary algorithm-design agent; white-paper only, no code):
  https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- ReflecTool (Liao et al. 2024 — reflection-aware tool-augmented agent that grows a long-term
  memory by saving successful solving processes + tool-wise experience; experience-accumulation
  loop relevant to §4.4 skills-learning + §4.2 memory): https://arxiv.org/pdf/2410.17657
- EvoTest (He et al. 2025 — gradient-free evolutionary *test-time* learning: evolves the whole
  agentic system after each episode, no fine-tuning; + the Jericho J-TTL benchmark for on-the-fly
  skill learning): https://arxiv.org/pdf/2510.13220
- TF-TTCL — "Training-Free Test-Time Contrastive Learning" (SCUT/Pazhou, Apr 2026 — frozen LLM, NO
  white-box/gradient access: "Explore-Reflect-Steer" loop — multi-agent role-play diversifies
  trajectories → contrastive distillation of superior-vs-inferior into explicit textual rules →
  contextual rule retrieval. Training-free ⇒ works on ANY provider incl. closed ones → §4.4/§4.15
  + fits the multi-provider constraint): https://arxiv.org/pdf/2604.13552
- SERM (NEU/ByteDance, Jan 2026 — self-evolving relevance model via two multi-agent modules: a sample
  miner detecting distribution shift + finding informative samples, and an annotator labeling via a
  two-level agreement framework; billion-request scale. Self-evolution under streaming data →
  §4.4/§4.15; domain-specific to search relevance): https://arxiv.org/pdf/2601.09515

### 3.19 Deep research, MCP/tools, coding agents & benchmarks (feeds §4.6 / §4.8 / §4.15)
- Open Deep Research — LangChain (configurable open deep-research agent): https://github.com/langchain-ai/open_deep_research
- Tongyi DeepResearch — Alibaba (open web agent on par with OpenAI DR): https://github.com/Alibaba-NLP/DeepResearch · https://arxiv.org/abs/2510.24701
- IterResearch (Alibaba 2025 — iterative long-horizon deep research via "interaction scaling":
  MDP-style workspace reconstruction with an evolving report-as-memory + periodic insight synthesis
  to avoid context suffocation; directly informs §4.3 auto-compaction): https://arxiv.org/pdf/2511.07327
- GPT Researcher (autonomous cited-report research agent): https://github.com/assafelovic/gpt-researcher
- Agentic Reasoning ⭐ (Wu et al. 2025 — tool-using agents for deep research: web search + code
  exec + structured Mind-Map knowledge-graph memory for long reasoning chains; user-flagged
  standout, prioritize): https://arxiv.org/pdf/2502.04644
- Model Context Protocol — spec + reference servers: https://github.com/modelcontextprotocol/modelcontextprotocol · https://github.com/modelcontextprotocol/servers
- Anthropic — Code Execution with MCP (≈98.7% token reduction pattern): https://www.anthropic.com/engineering/code-execution-with-mcp
- OpenHands / OpenDevin (open SWE-agent platform, SOTA SWE-bench Verified): https://github.com/All-Hands-AI/OpenHands
- Anthropic — multi-agent research system (orchestrator-worker, +90.2% vs single agent):
  https://www.anthropic.com/engineering/built-multi-agent-research-system
- GAIA benchmark (general AI assistant): https://arxiv.org/abs/2311.12983
- AgentBench (LLMs-as-agents across 8 environments): https://github.com/THUDM/AgentBench · https://arxiv.org/abs/2308.03688
- Terminal-Bench (containerized CLI agent tasks — directly relevant to Lyra): https://github.com/laude-institute/terminal-bench · https://arxiv.org/abs/2601.11868
- Ask-before-Plan (Zhang et al. 2024 — *Proactive Agent Planning*: predict clarification needs from
  ambiguous instructions; Clarification-Execution-Planning multi-agent framework + benchmark) (→ §4.14/§4.13): https://arxiv.org/pdf/2406.12639
- BLADE (Gu et al. 2024 — benchmark for LM agents on open-ended data-driven science; 12 datasets +
  expert ground-truth analyses, scores multifaceted analytical decisions) (→ §4.15/§4.16): https://arxiv.org/pdf/2408.09667
- STReasoner (Emory/Microsoft/Griffith, Jan 2026 — spatio-temporal reasoning over time series via
  spatial-aware RL; ships ST-Bench built with a network-SDE-based multi-agent data-synthesis pipeline.
  Tangential/domain-specific (time series), but the multi-agent synthesis pipeline + reasoning-over-
  accuracy framing → §4.15): https://arxiv.org/pdf/2601.03248
- CodeWiki (late 2025 — automated REPO-LEVEL documentation across 7 languages: hierarchical
  decomposition preserving architectural context, recursive multi-agent processing with dynamic task
  delegation, multi-modal synthesis (text + architecture diagrams). Directly serves the §6 docs/README
  deliverable + §4.15): https://arxiv.org/pdf/2510.24428
- InsightAgent (Qiu et al., 2025 — human-centered interactive agent that completes systematic reviews
  in hours: relevant-study identification + summary generation, with corpus + agent-trajectory
  visualizations for real-time human monitoring/feedback. The interactive-steering angle → §3.23
  human steering + §4.15 deep research): https://arxiv.org/pdf/2504.14822

### 3.20 Self-evaluation, uncertainty & introspection (NEW — feeds a new §4.19 self-knowledge layer)
How Lyra knows when it's failing, calibrates confidence, abstains, and decides ask-vs-proceed.
Seeds (verify venue/track + expand under the A/A* rule):
- "LLMs Must Be Taught to Know What They Don't Know" (NeurIPS 2024 — fine-tuned uncertainty
  estimation; calibrated confidence generalizes across models): https://arxiv.org/abs/2406.08391
- A Survey on the Honesty of LLMs (TMLR 2025 — self-knowledge: known/unknown, calibration, selective
  prediction): https://github.com/SihengLi99/LLM-Honesty-Survey
- "Beyond 'I Don't Know': discriminating data vs. model uncertainty" (2026): https://arxiv.org/abs/2604.17293
- A Survey of Confidence Estimation and Calibration in LLMs (NAACL 2024).
- MATU — "Every Response Counts" (ASU/UC Riverside, Apr 2026 — uncertainty quantification FOR
  multi-agent systems via tensor decomposition: handles cascading multi-step uncertainty, variable
  inter-agent comms paths, and diverse topologies by stacking reasoning-trajectory embedding matrices
  into a higher-order tensor; UQ for the swarm itself → §4.13 + §4.16): https://arxiv.org/pdf/2604.08708
> EXPAND: search top venues for selective prediction, abstention, self-consistency-as-signal,
> verbalized confidence, semantic-entropy hallucination detection, and meta-cognition / tool-use
> triggers. Lyra needs an introspection signal that gates autonomy (§4.14) and the verifier (§4.16).

### 3.21 Planning & reasoning architectures (NEW — feeds a new §4.20 planning layer above memory/skills)
Explicit deliberation/search as a layer over Lyra's memory + skills.
Seeds (all real ICLR/NeurIPS-tier — verify + expand):
- RAP — "Reasoning with Language Model is Planning with World Model" (EMNLP 2023; MCTS + LLM-as-world-
  model): https://arxiv.org/pdf/2305.14992
- SWE-Search (ICLR 2025 — MCTS + value agent for repo-level SWE tasks; directly relevant to Lyra coding):
  https://proceedings.iclr.cc/paper_files/paper/2025/file/a1e6783e4d739196cad3336f12d402bf-Paper-Conference.pdf
- AFlow (ICLR 2025 — MCTS over agentic workflows; nodes = whole workflows): https://arxiv.org/abs/2410.10762
- MC-DML (ICLR 2025 — MCTS + in-trial & cross-trial memory for planning): https://arxiv.org/abs/2502.13886
- Tree of Thoughts (NeurIPS 2023, foundational): https://arxiv.org/abs/2305.10601
> EXPAND: ToT/GoT, LATS, plan-and-solve, least-to-most, reflexion-style backtracking, learned value
> functions, and when explicit search beats single-pass reasoning (cost trade-off — tie to §3.22).

### 3.22 Cost & latency economics (NEW — feeds §4.5 router + a new §4.21 performance/economics workstream)
What makes a long-running multi-agent system actually affordable & fast.
Seeds (verify + expand):
- Prompt caching / KV-cache reuse across turns and agents (Anthropic & provider docs; quantify savings).
- Speculative decoding (Leviathan et al., ICML 2023): https://arxiv.org/abs/2211.17192
- Batching / request coalescing, and "Cost-Augmented MCTS" (budget-aware search): https://arxiv.org/abs/2505.14656
- FrugalGPT / cascades (already in §3.14 — connect here for the economics view).
> EXPAND: prompt-cache hit-rate strategy across a swarm, when parallelism stops paying (Amdahl for
> agents), token-budget accounting per workflow, latency-vs-quality knobs tied to the §4.5 effort scale.

### 3.23 Human–agent interaction & steering (NEW — feeds §4.1 + a new §4.22 steering workstream)
Interrupt, correct, and redirect a long autonomous run without restarting it.
Seeds (verify + expand under A/A* rule):
- Constitutional AI / preference learning foundations; interactive correction & steerability papers
  at ACL/EMNLP/CHI; "interruptible agents" / mid-task human feedback literature.
> EXPAND: barge-in/interrupt semantics (ties to §4.18 voice), mid-run preference capture, steating via
> natural-language correction, approval-gate UX, undo/rewind of agent actions, and trust calibration
> (link to §3.20 — users rely appropriately only when confidence is calibrated). Search CHI/ACL/EMNLP.

### 3.24 Environment, sandboxing & computer/browser use (NEW — feeds §4.6 tools + §4.17 safety)
The execution surface for a fully autonomous agent: isolation + computer/browser-use capability.
Seeds (verify + expand):
- Claude Code sandboxing/security docs (already in §3.1 — connect here).
- Computer-use / GUI-agent benchmarks: OSWorld (NeurIPS 2024): https://arxiv.org/abs/2404.07972 ;
  WebArena (ICLR 2024): https://arxiv.org/abs/2307.13854 ; WebVoyager (ACL 2024): https://arxiv.org/abs/2401.13919
- Code-execution isolation (gVisor/Firecracker/microVM patterns) + filesystem/network boundaries.
> EXPAND: secure code-exec sandboxes, browser-use agent stacks, computer-use action spaces, capability
> vs. blast-radius trade-offs, and the §4.17 containment story for full autonomy.

### 3.25 Data & knowledge ingestion (NEW — feeds §4.2 memory + a new §4.23 knowledge workstream)
RAG beyond conversational memory: indexing codebases/docs, multimodal inputs, keeping KBs fresh.
Seeds (verify + expand):
- Advanced/Graph RAG (GraphRAG — Microsoft): https://arxiv.org/abs/2404.16130 ;
  Self-RAG (ICLR 2024): https://arxiv.org/abs/2310.11511 ; HippoRAG (NeurIPS 2024, already noted): https://arxiv.org/abs/2405.14831
- MASS-RAG (BIT, **ACL 2026 Findings** — multi-agent synthesis RAG: role-specialized agents for
  evidence summarization / extraction / reasoning + a dedicated synthesis stage; wins most when
  retrieved evidence is noisy/incomplete/distributed → §4.2 + §3.25): https://arxiv.org/pdf/2604.18509
- SpreadsheetAgent (CUHK/SenseTime, Apr 2026 — two-stage multi-agent spreadsheet understanding: reads
  massive sheets INCREMENTALLY across modalities (code-exec results, images, LaTeX tables), builds a
  structural sketch + row/col summaries, then task-driven reasoning; for enterprise data/audit tasks
  → §4.6 tools + §3.25 ingestion): https://arxiv.org/pdf/2604.12282
- MATA (SNU, Feb 2026 — multi-agent TableQA: complementary reasoning paths + tools built on SMALL
  models, with an algorithm to minimize expensive LLM calls; strong with small open models + adapts
  across LLM types → §4.5 small-model offload + §4.6 + §3.25): https://arxiv.org/pdf/2602.09642
- Code indexing / repo-level retrieval (tie to §3.9 codegraph, spaCy); incremental re-indexing.
> EXPAND: chunking strategies, hybrid dense+sparse retrieval, multimodal ingestion (PDF/image/audio),
> freshness/invalidation, and how ingestion feeds the §4.2 memory architecture vs. living separately.

### 3.26 Benchmark TARGETS to rank #1 on (NEW — feeds §4.16; the scoreboard, not just references)
Treat these as leaderboards to BEAT, not just reading. For each: record the current SOTA number + the
top system, define how Lyra will be evaluated against it, and track Lyra's score over time.
- SWE-bench Verified (coding) · Terminal-Bench (CLI agents — most Lyra-relevant) · GAIA (general
  assistant) · τ-bench / τ²-bench (tool-agent) · OSWorld / WebArena (computer/web use) · BrowseComp ·
  AgentBench · BLADE (data science) · MLE-bench (ML engineering) · GPQA (reasoning).
> EXPAND: find each leaderboard's live SOTA + methodology, add any newer A/A*-venue benchmark that
> matters for an omni-agent, and turn §7's test plan into a benchmark-tracking scoreboard
> (current-SOTA vs Lyra) so "rank #1" (§0) becomes measurable rather than aspirational.

> **New workstreams implied by §3.20–§3.26** — add plans for these alongside §4.x:
> §4.19 Self-knowledge/uncertainty layer · §4.20 Planning/reasoning layer · §4.21 Performance &
> cost economics · §4.22 Human steering & interruptibility · §4.23 Knowledge ingestion/RAG. (§3.24
> environment/sandboxing folds into §4.6+§4.17; §3.26 folds into §4.16 + §7.)

### 3.27 "Dreaming" / Memory Consolidation During Idle (NEW — feeds §4.2 + new §4.24)
Anthropic's May 2026 "Dreaming" feature for Claude Managed Agents introduces a powerful new
pattern: agents consolidate memory during downtime, modeled on REM sleep. Key sources:
- Anthropic "Dreaming" (Code w/ Claude conference, May 2026): reviews up to 100 past conversations
  and memory stores during idle → produces fresh reorganized memory bank (merges duplicates, replaces
  outdated entries, resolves contradictions, surfaces cross-session patterns). Never modifies
  original — output is reviewable before accepting. Harvey (legal AI) saw ~6× task completion
  improvement. https://siliconangle.com/2026/05/06/anthropic-letting-claude-agents-dream-dont-sleep-job/
- Anthropic Memory Files (May 2026): file-system-based memory organized by topic/project/context,
  wiki-like user control, selective reading vs. single rolling summary that overflows.
  https://36kr.com/p/3824047027458182
- LightMem (ICLR 2026): bio-inspired "sleep-time update" — consolidates sensory→short→long-term
  memory during idle, achieving 105× token reduction and 309× fewer API calls.
- MetaClaw (2603.17187): opportunistic policy optimization during user-inactive windows via LoRA
  fine-tuning with Process Reward Models, zero downtime.
- Conway (Anthropic): always-on agent platform combining Memory Files (storage) + Dreams
  (maintenance) + Conway (runtime) for a complete autonomous memory→reflection→action loop.
> Lyra should implement a consolidation loop: after each session or during idle, replay, deduplicate,
> reorganize, and strengthen memory. This is the missing "hippocampus" piece Hassabis identified
> as one of the 3 remaining AGI gaps.

### 3.28 Harness Engineering as a Discipline (NEW — feeds all workstreams + new §4.26)
2026 has crystallized "harness engineering" as the critical meta-discipline for AI agent systems —
designing the constraints, feedback loops, evaluation infrastructure, and context management that
make agents effective. Key sources:
- OpenAI "1M Lines of Production Code, Zero Human-Written" (Feb 2026): small team + AI agents +
  right harness constraints → 1M lines. Called "the most important engineering discipline of 2026."
- Netflix 4-Pillar Gen AI Platform (May 2026, Code w/ Claude): throttling/resiliency + Braintrust
  evaluation system + MCP-standardized tool ecosystem + dedicated RAG system. Without this context
  layer, generic AI code assistants saw "near-zero adoption." Multi-agent architecture: Lead agent
  decomposes tasks → specialized sub-agents (deployment history, error logs, performance metrics,
  tickets) → parallel event-driven collaboration. "Adversarial code review": Agent A writes →
  Agent B evaluates → Agent C orchestrates.
  https://www.theregister.com/software/2026/04/04/netflix-meta-ibm-speakers-discuss-ai-and-their-workdays/
- ThoughtWorks "Beyond Vibe Coding" (2026): 5 building blocks of AI-native engineering — Agent,
  Model, Methodology (BMAD Method), Spec (SpecKit/OpenSpec), Context (AGENTS.md/CLAUDE.md).
  https://www.thoughtworks.com/en-us/insights/blog/generative-ai/beyond-vibe-coding-the-five-building-blocks-of-aI-native-engineering
- Anthropic Context Engineering Cookbook (Mar 2026): 3 strategies — Compaction + Tool Clearing +
  Memory; "less is more" finding (400-line prompt→15 lines, 12 tools→3 primitives, eval pass
  rate 83%→92%). https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools
- OpenDev Terminal Agent Architecture (2603.05344): 5-role compound AI system, 5-level adaptive
  context compaction, 5-layer safety architecture, dual-memory (episodic + working), 24 event-driven
  system reminders. The definitive terminal-agent harness reference.
> Lyra's harness quality IS the product. Formalize harness engineering as a first-class subsystem:
> context engineering, evaluation infrastructure, safety architecture, methodology, platform
> prerequisites. The harness matters more than the model.

> **Additional new workstreams implied by §3.27–§3.28 + June 2026 deep research:**
> §4.24 Memory Consolidation ("Dreaming") — idle-time replay, dedup, reorganize · §4.25 Adversarial
> Verification Panel — 3-verifier panel + skeptic + anonymization (not single checker) ·
> §4.26 Harness Engineering — formalize as Lyra subsystem (context, evals, safety, methodology,
> platform) · §4.27 RL-Based Skill & Agent Optimizer — GEPA-style gradient-free prompt evolution +
> MetaAgent-X-style Designer+Executor co-evolution.

---

## 4. Upgrade Workstreams (produce a concrete, referenced plan for each)

For every item: summarize the relevant source techniques, propose the specific Lyra design, give
an implementation outline, and rank impact × effort.

### 4.1 UI/UX
- **Multiple beautiful color themes** (design a palette set with names + hex tokens).
- **More keybindings** (propose a full keymap, including power-user bindings).
- **UX-boosting features** ported from Hermes Agent and Claude Code docs.

### 4.2 Memory — breakthrough architecture
Synthesize §3.4 (+ §3.9) into a **new multi-layer long/short-term memory architecture** for Lyra:
cross-session recall, conflict resolution, active forgetting, and (if justified) multi-agent shared
memory. Propose the design, the data model, and a migration path.

### 4.3 Context optimization & auto-compaction
Context-window management, retrieval, and an **auto-compaction** system.

### 4.4 Skills system + concrete skills
Design a **skills curator / intelligent loader / manager / learner / creator / auto-evaluator /
self-evolving** pipeline. Then **ship multiple concrete skills** covering: Engineering, Design, SRE,
AI Research, Solution Architecture, Cloud Engineering, PM, BA, Brainstorming (drawing on
superpowers / oh-my-claude / skillos / karpathy-skills / academic-research-skills).

**Provider-agnostic requirements (Lyra is multi-provider — must hold for every backend):**
- The skill loader is **harness-level**, not provider-API-level: read `SKILL.md` from the
  filesystem and inject it into the outgoing `messages` array. Never depend on a provider-specific
  "skills" endpoint (none of Claude / DeepSeek / Qwen / GPT / open-weights expose one).
- Use **progressive disclosure**: load only frontmatter (name + description) by default; load the
  full SKILL.md body only on selection, and referenced files only when the task reaches them.
- **Skill selection must not rely solely on the backing model auto-triggering.** Provide a
  deterministic / router-based matching path (keyword, embedding, or rule based) as a fallback,
  because instruction-following and auto-trigger reliability vary widely across providers and tiers
  (e.g. a small/fast model like `deepseek-v4-flash` triggers far less reliably than a frontier
  Claude model). Define per-provider trigger strategy.
- **Normalize provider-specific frontmatter.** Ignore or translate Claude-only fields (e.g. a
  `model:` pin, Claude Code subagent/dynamic-injection extensions) when the active backend isn't
  Claude; degrade gracefully rather than erroring.
- **Back hard guarantees with hooks (§4.10), not prompt instructions alone** — since on any
  provider an injected skill is a strong suggestion, not an enforced gate.
- Deliver a **provider × skill compatibility matrix** documenting expected behavior/limitations per
  backend.

### 4.5 Intelligent Model Router
Auto-route by task type: reasoning-heavy → a reasoning model (e.g. `claude-opus-4.7`,
`deepseek-v4-pro`); cheap/small execution → a fast model (e.g. `claude-sonnet-4.6`,
`deepseek-v4-flash`). Define the routing policy, fallbacks, and cost/latency targets.

**Multi-provider requirements:**
- Define a **provider-abstraction layer** so the rest of Lyra (skills, tools, memory, swarm) is
  written once and runs against any backend (Claude / DeepSeek / Qwen / GPT / open-weights),
  normalizing message format, tool-call schema, streaming, and token accounting per provider.
- **Router ↔ skills interop:** when routing to a non-Claude or small/fast tier, prefer
  deterministic skill matching over model-auto-trigger (§4.4) and strip/translate Claude-only skill
  frontmatter for that call.
- Handle per-provider differences in **tool-calling format, context window, and reliability**;
  define fallback/escalation (e.g. retry a failed cheap-tier task on a stronger model) and a
  capability map per provider (does it support tool use? JSON mode? vision? long context?).
- Credentials per provider come from §4.12; never hard-code keys.

### 4.6 Tools
**Implement all tools used by Hermes Agent and Claude Code** (per the tools-reference doc), mapped
to Lyra's tool interface.

### 4.7 Plugins — per the plugins-reference doc.
### 4.8 MCP — integration design + which servers from awesome-mcp-servers to bundle.
### 4.9 Commands & interactive mode — command set + interactive UX.
### 4.10 Hooks & automation — hooks + goal-driven automation.
### 4.11 Sessions — checkpointing & session management.
### 4.12 Permissions & credentials — permission model + env-var/credential handling.
### 4.13 Agent swarm / fleet / channels — parallel execution at scale; channel-based inter-agent comms.
  Must include a **fleet layer modeled on Claude Code's Agent View** (§3.1): a per-user SUPERVISOR/
  daemon that hosts each session as its own detached process, persists state to disk, survives
  terminal-close/restart/sleep, respawns idle sessions on demand, and a single-screen FLEET VIEW
  (dispatch / state-grouped rows / peek-reply / attach-detach / filters / pin) over it. Adopt the
  two-axis state model (task-state × process-liveness). For parallel-edit safety, build the
  **git-worktree isolation substrate** (§3.1 worktrees doc): an agent isolates itself into its own
  worktree (own tool, like EnterWorktree) BEFORE any edit; a `.worktreeinclude`-style mechanism copies
  gitignored env/secrets into each new worktree; a fresh-vs-head base-branch policy is exposed; cleanup
  is NON-DESTRUCTIVE by default (auto-stash/archive/confirm, never silently discard a dirty worktree
  the way Claude Code does); and non-git repos fall back to a WorktreeCreate-hook analog or overlay
  scheme rather than unsafe shared edits. This is the difference between "subagents inside one session"
  (already covered) and a true detached fleet that can edit concurrently without collisions.
### 4.14 Full autonomy — continuous-operation loop (continuous-claude pattern). Sessions run UNATTENDED
  via the §4.13 supervisor (no terminal required), steered by exception through the fleet view; the
  cheap-model row-summary surface (route via §4.5) lets the loop report status without spending big-
  model tokens on monitoring. Carry the Agent View security guardrail: unwatched sessions cannot use
  bypass/auto permission modes without a prior explicit human accept (→ §4.17).
### 4.15 Deep / multi-hop / auto / scientist research — self-organizing research teams (AutoScientists pattern).
### 4.16 Reliability — monitoring, tracing, an **intelligent verifier**, and SDLC integration.
### 4.17 Safety / alignment — guardrails informed by the agentic-misalignment research.

### 4.18 Voice Mode — ⭐ NEXT FLAGSHIP FEATURE (treat as top priority)
This is the designated **next big feature** for Lyra — give it the deepest research and the most
complete plan of any workstream. **Deep-research voice and sound in AI agents** broadly (not just
notification SFX): real-time speech-to-text and text-to-speech, streaming/low-latency voice loops,
barge-in / interruption handling, voice activity detection, turn-taking, wake words, diarization,
emotion/prosody, multilingual voice (incl. Vietnamese + English), on-device vs. cloud STT/TTS
trade-offs, latency budgets, and the leading open and commercial stacks (e.g. Whisper-family STT,
modern TTS engines, realtime voice APIs, and open-source voice-agent frameworks — survey the
current SOTA and benchmark them on latency / quality / cost / privacy).
Then deliver an **ultra plan** for Lyra voice mode covering:
- **Architecture:** the full voice pipeline (capture → VAD → STT → agent/router → TTS → playback),
  streaming and interruption model, and how it plugs into Lyra's provider-abstraction layer (§4.5)
  so STT/TTS providers are swappable like LLM providers.
- **Interaction design:** push-to-talk vs. always-listening, hotword, multi-turn voice
  conversations, reading back long answers, voice control of the swarm/workflows.
- **Personality / SFX layer:** the lighter UX from §5.3 (funny voice on session start, a voice cue
  when Lyra finishes an answer, selectable voice packs) folded in as one component of the larger
  voice-mode system, wired via hooks (§4.10).
- **Accessibility, privacy, and cost** considerations, plus a phased rollout (MVP → full duplex).
Reference the §5.3 write-ups (Warcraft peon notifications, sound-effects-via-hooks) for the SFX
layer, and survey the **§3.13 voice & audio corpus** (Pipecat, LiveKit, Smart Turn, Silero VAD,
Moshi, CSM, Kokoro, Orpheus, Parakeet/Whisper) plus the voice benchmarks (Full-Duplex-Bench,
τ-Voice) for the core pipeline.

### 4.19 Self-knowledge / uncertainty layer
(Planned — see §3.20 for the research corpus.)

### 4.20 Planning & reasoning layer
(Planned — see §3.21 for the research corpus.)

### 4.21 Performance & cost economics
(Planned — see §3.22 for the research corpus.)

### 4.22 Human steering & interruptibility
(Planned — see §3.23 for the research corpus.)

### 4.23 Knowledge ingestion / RAG
(Planned — see §3.25 for the research corpus.)

### 4.24 Memory Consolidation ("Dreaming") — ⭐ NEW (June 2026 Research)
**Source:** Anthropic "Dreaming" (May 2026), LightMem "sleep-time update" (ICLR 2026), MetaClaw
opportunistic fine-tuning (2603.17187)

Agents should consolidate, deduplicate, and reorganize memory during idle time — replaying past
interactions, merging duplicates, resolving contradictions, and surfacing cross-session patterns.
Modeled on REM sleep. Harvey (legal AI) saw ~6× task completion improvement with this pattern.

**Design outline:**
- Idle-time background process reviews past N conversations + memory stores
- Produces reorganized memory bank (never modifies original — reviewable before accept)
- Merges duplicates, replaces outdated entries, resolves contradictions
- Surfaces cross-session patterns no single agent could see
- Configurable frequency; streamable for live review
- Combined with Memory Files (topic/project/context-organized, wiki-like user control)
- Conway-like always-on loop: Memory Files (storage) + Dreams (maintenance) + Runtime (action)

**Impact:** Breakthrough | **Effort:** High | **Priority:** After §4.2 Memory baseline

### 4.25 Adversarial Verification Panel — ⭐ NEW (June 2026 Research)
**Source:** Netflix adversarial code review, Anthropic dynamic workflow verification, ErrorProbe
(2604.17658), SABER mutation-gated verification, "Lying with Truths" collusion attack (2601.01685)

The §4.16 Verifier should be redesigned as an adversarial multi-agent PANEL, not a single checker.
Current single-pass verifier is insufficient against documented 2026 failure modes.

**Design outline:**
- **3-Verifier Panel:** Correctness + Security + Reproducibility verifiers
- **Adversarial Skeptic:** One agent tasked with REFUTING the finding
- **Response Anonymization (2510.07517):** Strip identity markers so verifiers can't tell self from peer
- **Actor-Observer Correction (2604.19548):** Apply ReTAS dialectical alignment
- **Mutation-Gated Verification (SABER):** Distinguish mutating vs non-mutating actions; gate verification
- **Voting:** Claim survives only if ≥2/3 verifiers confirm after adversarial challenge
- **Collusion Detection:** Monitor for "Lying with Truths" pattern (truthful evidence steering beliefs)

**Impact:** Breakthrough | **Effort:** Medium | **Priority:** Before production deployment

### 4.26 Harness Engineering Discipline — ⭐ NEW (June 2026 Research)
**Source:** OpenAI "1M lines zero human code" (Feb 2026), Netflix 4-pillar platform, Anthropic
context engineering cookbook, ThoughtWorks 5 building blocks

The harness itself (constraints, feedback loops, evaluation, context management, methodology) is
now recognized as THE critical engineering discipline for AI agents — more important than model
selection. Lyra's entire value proposition is validated. Formalize it.

**Design outline — 5 Pillars:**
1. **Context Engineering:** Adaptive compaction, memory, tool clearing, "less is more" (400-line
   prompt→15 lines, 12 tools→3 primitives improved pass rate 83%→92%)
2. **Evaluation Infrastructure:** Capability evals (ceiling) + regression evals (floor) + simulation
   personas + continuous eval refresh (100% pass rate = useless signal)
3. **Safety Architecture:** 5-layer defense-in-depth (Prompt → Schema-gating → Runtime approval →
   Tool-level validation → Lifecycle hooks)
4. **Methodology:** BMAD Method, spec-to-code pipelines, AI-native SDLC (agent lanes in CI/CD)
5. **Platform Prerequisites:** CI/CD + IaC + observability + security scanning (agents accelerate
   broken practices — fix foundations first)

**Impact:** Breakthrough | **Effort:** Very High | **Priority:** Foundational (underpins all workstreams)

### 4.27 RL-Based Skill & Agent Optimizer — NEW (June 2026 Research)
**Source:** GEPA (ICLR 2026 Oral), MetaAgent-X (2605.14212), MemAgent RL training, Dr. Zero
(2601.07055), MemGrad textual gradients, TF-TTCL (2604.13552)

Current §4.4 is primarily prompt-based. 2026 research shows RL-based optimization outperforms
prompt engineering alone. Add an RL optimizer alongside the prompt-based curator.

**Design outline:**
- **Skill-level:** GEPA-style reflective prompt evolution — generate variants → evaluate → keep
  winners → mutate → repeat (gradient-free, works on ANY provider including closed ones)
- **Agent-level:** MetaAgent-X-style Designer+Executor co-evolution — Designer writes agent config
  scripts → Executor runs them → reward from task success → GRPO update
- **Memory-level:** MemAgent-style train memory read/write policy end-to-end via RL
- **Textual Gradients (MemGrad):** Turn batched feedback into retrospective/prospective memory +
  prompt updates without fine-tuning
- **Training-Free (TF-TTCL):** Explore-Reflect-Steer loop for closed-model providers

**Impact:** Breakthrough | **Effort:** Very High | **Priority:** After §4.4 Skills baseline

---

## 5. Specific Investigations (answer explicitly)

### 5.1 rmux-style rebuild
Study tmux / cmux / **rmux** architecture and ideas. Since Lyra is MIT-licensed, design a clean
**from-scratch rebuild** of the most valuable capabilities for Lyra (do not copy code with
incompatible licenses). Deliver the architecture and a build plan. Resolve cleanly against the §3.1
Agent View supervisor and the **git-worktree edit-isolation** primitive: decide what rmux owns
(terminal multiplexing / PTY hosting / detach-reattach) vs. what the supervisor owns (session
lifecycle) vs. what worktrees own (per-session file isolation), so the three don't reimplement each
other. The worktree layer (own tool to isolate-before-edit, `.worktreeinclude` env propagation,
non-destructive cleanup, non-git fallback) is the safety substrate this rebuild writes through.

### 5.2 Multi-tenancy (AgentsMesh)
Evaluate the **multi-tenant** concept from AgentsMesh for Lyra's multi-agent setup. Should we adopt
it? Lay out pros and cons carefully and give a clear recommendation.

### 5.3 Voice / sound UX (feeds the §4.18 flagship voice workstream)
Design voice notifications: a **funny voice on new-session start** and a **voice cue when Lyra
finishes an answer** (reference the Warcraft peon and sound-effects-via-hooks write-ups). Specify
the hook points and a few voice-pack options. Treat this as the personality/SFX layer of the larger
**Voice Mode** feature in §4.18 — design them together, not in isolation.

---

## 6. Documentation Deliverable

Update **all docs and `README.md`** to match Lyra's current + planned state. They must be:
- **Visual:** architecture **Mermaid** diagrams, charts, data models, flow diagrams.
- **Interactive, clean, easy to scan**, and attractive to other builders.
- **Sourced:** for every novel technique in Lyra, add the **inspiration** behind it with reference
  links (papers / GitHub repos) so readers can dig deeper.

Scan the whole codebase for docs describing novel techniques and back-fill these references.

---

## 7. Testing Deliverable

Produce a **detailed test plan** covering every flow related to deep research, auto research,
scientist research, AI-research-research, and workflows in Lyra. Include scenarios, expected
outputs, edge cases, and pass/fail criteria.

> For now, run tests using `DEEPSEEK_API_KEY` from `~/.claude/settings.json`.

---

## 8. Final Output Format

Deliver, as files on disk:
1. A **master plan** (executive summary + prioritized roadmap, breakthrough items flagged).
2. One **plan-per-workstream** (§4) and **per-investigation** (§5), each with referenced sources.
3. The **proposed memory architecture** write-up (§4.2) with diagrams.
4. The **updated docs + README** (§6).
5. The **test plan** (§7).
6. A **research log** listing every source consulted and every link that failed (so nothing is
   silently dropped).

---

## 9. Final Reminder — Documentation

Help me update all docs and `README.md` files to match the current state of Lyra. Make sure they
contain **multiple visualizations** (architecture Mermaid diagrams, charts, data models, …), and
are **interactive, clean, easy to read and catch up on, and attractive to other builders**.
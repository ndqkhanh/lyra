---
title: Features catalogue
description: Every feature shipped in Lyra v3.5.x — grouped by surface, with one-line use case, how to invoke, where it lives, and maturity. The single source of truth for "what does Lyra actually do?"
---

# Features catalogue <span class="lyra-badge reference">reference</span>

> **Status:** v3.5.5 snapshot. **Single source of truth** for "what
> does Lyra actually do?" Every shipped subsystem, CLI subcommand,
> slash command, building block, and provider — with the **use
> case**, the **invocation**, the **source path**, and the
> **maturity flag**. For task-driven recipes ("I want to do X →
> stack these features"), see [Use cases](use-cases.md).
>
> **The clean cut (v3.5.5).** This catalogue lists *only what ships
> and runs against a real provider key today*. Forward-compat
> shims (the `SharedKVPoolProvider`, `BlockStreamingProvider`, and
> `BrierLM` scorer) were removed in v3.5.5 because they had no
> upstream that could activate them. Future research is tracked in
> [Roadmap v1.5 → v2](roadmap-v1.5-v2.md), not here.

## Maturity legend

| Symbol | Meaning |
|:--:|---|
| 🟢 | **Production** — shipped, tested, used in the dogfood loop |
| 🟡 | **Beta** — shipped behind a flag or with known rough edges |

## 0. Four ways to use Lyra

| Surface | When to reach for it | How | Where it lives |
|---|---|---|---|
| **Interactive REPL** 🟢 | Day-to-day coding — you want a Claude-Code-style session with slash commands and a live HUD | `lyra` (no args) | [`lyra_cli/interactive/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/interactive) |
| **Scripted one-shot** 🟢 | CI, batch jobs, "do this one task and exit" | `lyra run "task description"` | [`lyra_cli/commands/run.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/run.py) |
| **ACP server (stdio)** 🟢 | Embed Lyra into another tool that speaks the [Agent Client Protocol](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/acp) (IDE plugins, custom UIs) | `lyra acp` | [`lyra_cli/commands/acp.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/acp.py), [`lyra_core/acp/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/acp) |
| **Embeddable Python kernel** 🟢 | You want to drive the agent from your own Python without the CLI | `from lyra_core.loop import AgentLoop` | [`lyra_core/loop/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/loop) |

## 1. CLI surface

### 1.1 Typer subcommands (19 commands)

The full top-level command tree. Every subcommand prints `--help`
with arg details.

| Command | Use case | Mode | Source |
|---|---|:--:|---|
| `lyra` | Start an interactive REPL session in the current repo | 🟢 | [`__main__.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/__main__.py) |
| `lyra init` | Scaffold `SOUL.md`, `.lyra/`, default skill packs in a fresh repo | 🟢 | [`commands/init.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/init.py) |
| `lyra setup` | Interactive provider auth (DeepSeek / Anthropic / OpenAI / …) into `~/.lyra/auth.json` | 🟢 | [`commands/setup.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/setup.py) |
| `lyra doctor` | Health check — env vars, providers, MCP, sandbox, git | 🟢 | [`commands/doctor.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/doctor.py) |
| `lyra run "task"` | Single-shot task with full agent loop (CI-friendly, JSON output via `--json`) | 🟢 | [`commands/run.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/run.py) |
| `lyra plan "task"` | Produce a plan artifact only; no edits | 🟢 | [`commands/plan.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/plan.py) |
| `lyra connect <target>` | Connect a remote dev environment / runner | 🟡 | [`commands/connect.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/connect.py) |
| `lyra retro [<id>]` | Session retrospective — grade the last run, extract lessons | 🟢 | [`commands/retro.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/retro.py) |
| `lyra serve` | Start the HTTP gateway (debug / inspector) | 🟡 | [`commands/serve.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/serve.py) |
| `lyra acp` | Host Lyra as a stdio Agent Client Protocol server | 🟢 | [`commands/acp.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/acp.py) |
| `lyra evals …` | Run the evals harness (golden / red-team / SWE-bench-Pro / loco-eval / τ-bench / terminal-bench) | 🟢 | [`commands/evals.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/evals.py) |
| `lyra evolve` | GEPA-style prompt evolver, Pareto-filtered (score↑ vs length↓) | 🟢 | [`commands/evolve.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/evolve.py) |
| `lyra session list\|show` | Browse persisted JSONL sessions | 🟢 | [`commands/session.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/session.py) |
| `lyra mcp list\|add\|remove\|doctor\|save` | Manage MCP server config | 🟢 | [`commands/mcp.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/mcp.py) |
| `lyra brain list\|show\|install` | Install curated brain bundles (`default`, `tdd-strict`, `research`, `ship-fast`) | 🟢 | [`commands/brain.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/brain.py) |
| `lyra hud preview\|presets\|inline` | Preview HUD layouts; pipe inline output to tmux `status-right` | 🟢 | [`commands/hud.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/hud.py) |
| `lyra burn …` | Cost burn-down analytics (per-day, per-repo, per-model breakdown) | 🟢 | [`commands/burn.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/burn.py) |
| `lyra skill list\|add\|remove\|smoke\|review\|curator-report` | Skill library management | 🟢 | [`commands/skill.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/skill.py) |
| `lyra memory record\|recall\|list\|…` | ReasoningBank operations from the CLI | 🟢 | [`commands/memory.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/memory.py) |

Top-level flags on `lyra` (the REPL): `--model / --llm`,
`--budget`, `--repo-root`, `--resume / -r`, `--continue / -c`,
`--session ID`, `--version`. See `lyra --help`.

### 1.2 Slash commands inside the REPL (~33 commands)

The full reference is at [Slash commands](reference/commands.md);
the runtime registry at
[`lyra_cli/commands/registry.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/registry.py)
wins on conflict. Key ones grouped by use case:

| Group | Commands | What they're for |
|---|---|---|
| **Session** 🟢 | `/help`, `/status`, `/cost`, `/clear`, `/save`, `/resume`, `/exit` | Day-to-day inspection + lifecycle |
| **Mode control** 🟢 | `/mode`, `/plan`, `/build`, `/approve`, `/reject`, `/run`, `/diff`, `/undo` | Switch the 4 modes; one-turn forms (`/plan` → `plan_mode`, `/build` → `edit_automatically`); revert via git stash |
| **Tools · agents** 🟢 | `/tools`, `/tool <name>`, `/agents`, `/spawn`, `/cycle` | Direct tool calls, parallel subagent spawn, advance TDD phase |
| **Observability** 🟢 | `/trace`, `/hir`, `/logs`, `/why <id>`, `/review` | Open trace viewer, HIR span tree, tail logs, explain a tool call, run review pass |
| **Config · theme** 🟢 | `/config`, `/model`, `/theme` | Inspect/edit config, switch model slot, switch colour skin |
| **Skill** 🟢 | `/skill`, `/skills` | List, add, remove, smoke-test, review skills |
| **MCP** 🟢 | `/mcp` | Add/remove/save MCP servers in this repo |
| **Plugin** 🟡 | `/plugin` | Enable/disable plugins for this session |
| **TDD** 🟢 | `/tdd-gate`, `/red`, `/green`, `/refactor` | Toggle TDD gate; force a phase |
| **HUD** 🟢 | `/hud`, `/hud preset <name>` | Switch HUD layout live |
| **Meta** 🟢 | `/version`, `/doctor`, `/feedback` | Version, in-session doctor, append a feedback note |
| **Reflexion (J.4)** 🟢 | `/reflect [on\|off\|add\|tag\|clear]` | Per-task verbal-RL retrospective loop |
| **Team (J.3)** 🟢 | `/team [show\|plan\|run]` | Org-Mode role-typed handoffs |

Pipe substitutions inside slash commands: `%file`, `%selection`,
`%line`, `%project` (auto-expanded from the active editor context).

### 1.3 Modes (4 modes)

The agent's runtime persona, switchable mid-session with `/mode`. The
v3.6.0 taxonomy is **permission-flavoured** — each mode corresponds
to a posture about *how aggressive the agent is about edits*. The
session boots in `edit_automatically` and remaps every legacy name
(v3.2 `agent`/`plan`/`debug`/`ask`; pre-v3.2 `build`/`run`/`explore`/`retro`)
to the canonical v3.6 mode.

| Mode | Use case | Permissions | Source |
|---|---|---|---|
| **edit_automatically** 🟢 | Default — write code, run tools, modify the repo without per-write confirmation | `permission_mode = normal` (cached approvals); subject to the permission bridge | [`agent_loop.md`](concepts/agent-loop.md) |
| **ask_before_edits** 🟢 | Same loop as `edit_automatically`, but every write or destructive tool call pauses for your confirmation | `permission_mode = strict` (always re-prompt) | [`four-modes.md`](start/four-modes.md#ask_before_edits-confirm-every-write) |
| **plan_mode** 🟢 | Read-only design pass — produces an approvable plan artifact | Read-only | [`plan-mode.md`](concepts/plan-mode.md) |
| **auto_mode** 🟢 | Heuristic router — picks `plan_mode` for design/explore prompts, `ask_before_edits` for risky/destructive prompts, `edit_automatically` otherwise | Inherits the chosen sub-mode's posture per turn | [`four-modes.md`](start/four-modes.md#auto_mode-let-lyra-pick) |

### 1.4 HUD (live status)

Two surfaces, both shipped, both inspired by `claude-hud`:

| Surface | What it shows | How |
|---|---|---|
| **Bottom toolbar (always on)** 🟢 | `repo / mode / model / turn / tok / cost / [deep / cap] / skin` — auto-truncates to terminal width | Renders inside the REPL via `prompt_toolkit` |
| **`lyra hud` subcommand** 🟢 | Multi-line preview of any preset; tmux-pipeable inline | `lyra hud preview --preset full` · `lyra hud inline` |

Four built-in presets: `minimal`, `compact`, `full`, `inline`.
Nine widgets in the `full` preset: `identity_line`, `context_bar`,
`usage_line`, `tools_line`, `agents_line`, `todos_line`, `git_line`,
`cache_line`, `tracer_line`. See [Customize the HUD](howto/customize-hud.md).

### 1.5 Themes (colour skins)

Switch with `/theme <name>`; the bottom-toolbar re-skins live.
Default is `aurora`. See [`lyra_cli/themes/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/themes).

## 2. The 14 building blocks (kernel)

The architectural backbone. Detail in [The 14 building blocks](reference/blocks-index.md);
each row links to its canonical spec.

| # | Block | Use case | Source |
|---|---|---|---|
| 01 | [Agent loop](blocks/01-agent-loop.md) 🟢 | The kernel: assemble → think → tool → reduce → repeat | [`lyra_core/loop/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/loop) |
| 02 | [Plan mode](blocks/02-plan-mode.md) 🟢 | Read-only design pass with an approvable plan artifact | [`lyra_core/plan/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/plan) |
| 03 | [DAG teams](blocks/03-dag-teams.md) 🟢 | Parallel multi-strand work with `PARK` for non-blocking approvals | [`lyra_core/adapters/dag_teams.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/adapters/dag_teams.py) |
| 04 | [Permission bridge](blocks/04-permission-bridge.md) 🟢 | Authorization as a runtime primitive, not an LLM decision | [`lyra_core/permissions/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/permissions) |
| 05 | [Hooks & TDD gate](blocks/05-hooks-and-tdd-gate.md) 🟢 | Deterministic Python on lifecycle events; flagship is the TDD gate | [`lyra_core/hooks/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/hooks), [`lyra_core/tdd/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/tdd) |
| 06 | [Context engine](blocks/06-context-engine.md) 🟢 | Five-layer transcript with prompt-cache breakpoints + never-compacted SOUL | [`lyra_core/context/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/context) |
| 07 | [Three-tier memory](blocks/07-memory-three-tier.md) 🟢 | Procedural / episodic / semantic + persona; SQLite FTS5 + Chroma | [`lyra_core/memory/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory) |
| 08 | [SOUL.md persona](blocks/08-soul-md-persona.md) 🟢 | The agent's persona partition; lives in L2; never compacted | per-repo `SOUL.md` |
| 09 | [Skill engine + extractor](blocks/09-skill-engine-and-extractor.md) 🟢 | Discover-by-description, narrowed tool surface, post-task extraction | [`lyra_core/skills/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills), [`packages/lyra-skills/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-skills) |
| 10 | [Subagent + worktree](blocks/10-subagent-worktree.md) 🟢 | Scoped agents in isolated git worktrees with structured returns | [`lyra_core/subagent/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/subagent) |
| 11 | [Verifier (cross-channel)](blocks/11-verifier-cross-channel.md) 🟢 | Two-phase: cheap objective checks then different-family LLM judge | [`lyra_core/verifier/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier) |
| 12 | [Safety monitor](blocks/12-safety-monitor.md) 🟢 | Continuous cheap-model monitor running every N steps | [`lyra_core/safety/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/safety) |
| 13 | [Observability + HIR](blocks/13-observability-hir.md) 🟢 | OTel + JSONL spans tagged with HIR primitives; replayable | [`lyra_core/observability/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/observability), [`lyra_core/hir/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/hir) |
| 14 | [MCP adapter](blocks/14-mcp-adapter.md) 🟢 | stdio + HTTP MCP client; wraps every external tool with the bridge | [`lyra_core/mcp/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/mcp) |

## 3. LLM provider matrix (16 providers)

Every provider Lyra can route to. Pick one with `--llm <name>` or
let `auto` try them in priority order.

| Provider | Use case | Auth | Source |
|---|---|---|---|
| **DeepSeek** 🟢 | Cheap default; `auto` priority #1 | `LYRA_DEEPSEEK_API_KEY` | [`providers/deepseek.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers) |
| **Anthropic** 🟢 | Premium quality; native prompt-cache support | `LYRA_ANTHROPIC_API_KEY` | [`providers/anthropic.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers) |
| **OpenAI** 🟢 | Frontier quality; native prompt-cache (50% discount on hits) | `LYRA_OPENAI_API_KEY` | [`providers/openai.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers) |
| **Gemini** 🟢 | Long context; native prompt-cache | `LYRA_GEMINI_API_KEY` | [`providers/gemini.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers) |
| **xAI Grok** 🟢 | Reasoning emphasis; OpenAI-compat surface | `LYRA_XAI_API_KEY` | OpenAI-compat |
| **Groq** 🟢 | Fast inference for low-latency hops | `LYRA_GROQ_API_KEY` | OpenAI-compat |
| **Cerebras** 🟢 | Fast inference (alt to Groq) | `LYRA_CEREBRAS_API_KEY` | OpenAI-compat |
| **Mistral** 🟢 | Cost-aware tier | `LYRA_MISTRAL_API_KEY` | OpenAI-compat |
| **Qwen** 🟢 | Cost-aware tier | `LYRA_QWEN_API_KEY` | OpenAI-compat |
| **OpenRouter** 🟢 | Hub for many models behind one key | `LYRA_OPENROUTER_API_KEY` | OpenAI-compat |
| **Ollama** 🟢 | Self-hosted local models | `LYRA_OLLAMA_HOST` | [`providers/ollama.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers) |
| **LM Studio** 🟢 | Self-hosted local; OpenAI-compat surface | `LYRA_LMSTUDIO_HOST` | OpenAI-compat |
| **Bedrock** 🟢 | AWS deployments | `LYRA_AWS_*` | [`providers/bedrock.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers) |
| **Vertex** 🟢 | GCP deployments | `LYRA_GCP_*` | [`providers/vertex.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers) |
| **Copilot** 🟢 | GitHub Copilot chat backend (gho_* OAuth → ghs_* session, lazy refresh on 401, OpenAI-shape adapter) | `LYRA_GITHUB_TOKEN` (or `lyra connect copilot --key gho_…`) | [`providers/copilot.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/providers/copilot.py) |
| **Mock** 🟢 | Deterministic in-process for tests | n/a | [`mock_llm/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/mock_llm) |

See [Configure providers](howto/configure-providers.md) for the
auth recipes; [Environment variables](reference/env-vars.md) for
the full env-var table.

## 4. Routing — two-tier cascade

| Feature | Use case | How | Source |
|---|---|---|---|
| **Two-tier routing** 🟢 | Send 80% of turns to a cheap "fast slot" model and escalate only when confidence is low — typical 60–80% cost cut at < 1 % quality regression | `/model fast=deepseek-chat smart=anthropic-sonnet` | [`routing/cascade.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/routing/cascade.py), concept: [Two-tier routing](concepts/two-tier-routing.md) |
| **Confidence-driven escalation** 🟢 | Auto-escalate when the fast slot's hidden-state confidence falls below threshold | (default; tune via config) | same module |
| **Per-turn budget cap** 🟢 | Refuse new LLM calls once spend crosses `--budget` (or `/budget set <usd>`) | `lyra --budget 5.00` · `/budget save 5.00` | [`agent/loop.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/agent/loop.py) |
| **Cost burn-down report** 🟢 | "How much have we spent this week, by repo, by model?" | `lyra burn` | [`commands/burn.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/burn.py) |

## 5. Memory subsystem (3 tiers + ReasoningBank)

| Feature | Use case | How | Source |
|---|---|---|---|
| **L1 working memory** 🟢 | Per-turn context window; managed by the context engine | (automatic) | [`context/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/context), concept: [Context engine](concepts/context-engine.md) |
| **L2 SOUL.md persona** 🟢 | Durable identity / persona pinned per-repo, never compacted | edit `<repo>/SOUL.md` | concept: [Sessions and state](concepts/sessions-and-state.md) |
| **L3 procedural / RAG** 🟢 | Episodic + semantic recall via SQLite FTS5 + Chroma | (automatic + `/skills`) | [`memory/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory) |
| **ReasoningBank lessons** 🟢 | Distill *successes and failures* into structured `Lesson`s; recall before similar tasks | `lyra memory record\|recall\|list` | [`memory/reasoning_bank.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/reasoning_bank.py), concept: [ReasoningBank](concepts/reasoning-bank.md) |
| **MaTTS — memory-aware TTS** 🟢 | Inject *different slices* of the bank into each parallel attempt to break monoculture | `tournament_tts.run(reasoning_bank=..., matts_prefix_k=4)` | [`tts/tournament.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/tts/tournament.py) |
| **Persistent SQLite + FTS5 store** 🟢 | Lessons survive across sessions; full-text searchable | (automatic) | [`memory/reasoning_bank_store.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/reasoning_bank_store.py) |
| **Heuristic distiller** 🟢 | Default — extracts lessons without LLM calls (deterministic, cheap) | (automatic) | [`memory/distillers.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/distillers.py) |
| **LLM distiller** 🟡 | Richer lesson extraction during periodic batch refinement | (opt-in via config) | same module |
| **Diversity-weighted recall (MMR)** 🟢 | Re-rank top-k by Maximal Marginal Relevance to avoid near-duplicates | `recall(diversify=True)` | concept: [ReasoningBank § Diversity-weighted recall](concepts/reasoning-bank.md#diversity-weighted-recall-mmr) |
| **Self-wiring brain bundles** 🟢 | Pre-curated personality + memory presets | `lyra brain install <default\|tdd-strict\|research\|ship-fast>` | [`brains/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/brains) |

## 6. Skills subsystem

| Feature | Use case | How | Source |
|---|---|---|---|
| **SKILL.md format** 🟢 | Anthropic-compatible Markdown front-matter that ships first-party + community skill packs | `lyra skill list\|add\|remove` | [`packages/lyra-skills/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-skills), concept: [Skills](concepts/skills.md) |
| **Skill router (description-match)** 🟢 | Default — picks SKILL.md packs by description match + lightweight retrieval | (automatic) | [`skills/router.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills/router.py) |
| **Skill-RAG router** 🟢 | Hidden-state probe + 4-action recovery (Query Rewrite / Question Decomp / Evidence Focus / Exit) — gates retrieval on the LM's own confidence | (automatic when probe available) | [`retrieval/skill_rag.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/retrieval/skill_rag.py), [paper #3](research/papers.md) |
| **Skill curator** 🟢 | Deterministic, no-LLM background grader for skills | `lyra skill curator-report` | [`skills/curator.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills/curator.py) |
| **Skill extractor** 🟢 | Generates `SkillManifest` proposals from successful trajectories | (automatic post-task) | [`skills/extractor.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills/extractor.py) |
| **Skill-Creator v2 4-agent loop** 🟢 | Executor / Grader / Comparator / Analyzer — measures + iterates a skill against a trigger corpus | (via Anthropic skill pack) | concept: [Skills](concepts/skills.md) |
| **License-allowlist gate** 🟢 | Skills with `license:` outside `{MIT, Apache-2.0, BSD, ISC}` fail to load unless overridden | (automatic; `--accept-agpl` to override) | [`lyra-skills/installer.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-skills/src/lyra_skills/installer.py) |
| **Smoke testing** 🟢 | Per-skill `smoke()` callable verified at install time | `lyra skill smoke <id>` | [`commands/skill.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/skill.py) |

How-to: [Write a skill](howto/write-skill.md).

## 7. Subagents

| Feature | Use case | How | Source |
|---|---|---|---|
| **Worktree-isolated subagents** 🟢 | Spawn N parallel subagents, each in its own git worktree, each with structured `Result` return | `/spawn "task"` · `SubagentOrchestrator.run_parallel(...)` | [`subagent/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/subagent), concept: [Subagents](concepts/subagents.md) |
| **DAG-Teams orchestration** 🟢 | Multi-strand parallel work with `PARK` semantics for non-blocking approvals | `/team plan` then `/team run` | [`adapters/dag_teams.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/adapters/dag_teams.py) |
| **ContextVars-propagated concurrency** 🟢 | Subagent threads inherit the parent's session id, repo, permissions, hooks | (automatic) | [`concurrency.py::submit_with_context`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/concurrency.py) |
| **Prompt-cache prewarm** 🟢 | One parent fills the cache; sibling subagents hit it — saves N-1 prefill costs on hosted APIs | `prewarm_for_specs(...)` then `hit_for_sibling(...)` | [`subagent/cache_prewarm.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/subagent/cache_prewarm.py), concept: [Prompt-cache coordination](concepts/prompt-cache-coordination.md) |
| **Vendored subagent presets** 🟢 | Specialised subagents (code reviewer, tester, architect, …) from `VoltAgent/awesome-claude-code-subagents` | `/spawn --preset <name>` | [repos.md § A11](research/repos.md#a-claude-code--coding-agent-ecosystem) |

## 8. Verifier

| Feature | Use case | How | Source |
|---|---|---|---|
| **Phase 1 — objective checks** 🟢 | Cheap deterministic gates: parses, types, tests, no merge conflicts | (automatic on every diff) | [`verifier/objective.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/objective.py), concept: [Verifier](concepts/verifier.md) |
| **Phase 2 — different-family judge** 🟢 | Subjective rubric scored by a different-family LLM (avoids self-grading drift) | (automatic when LLM family differs) | [`verifier/subjective.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/subjective.py) |
| **Cross-channel evidence** 🟢 | Verifier reads logs + traces + diffs + tests, not just chat | (automatic) | [`verifier/cross_channel.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/cross_channel.py) |
| **PRM (process reward model)** 🟢 | Per-step reward signal during reasoning; adopts Qwen team's lessons | (automatic when configured) | [`verifier/prm.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/prm.py), [paper #21](research/papers.md) |
| **TDD-reward signal** 🟢 | Numeric reward only when tests verify — KnowRL-shaped for coding | `/tdd-gate on` | [`verifier/tdd_reward.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/tdd_reward.py), [paper #4](research/papers.md) |
| **Diversity guard** 🟢 | Raises with a remediation hint pointing to arXiv:2604.18005 §5.2 when a tournament collapses to a monoculture | (automatic in tournament TTS) | [`tts/diversity_guard.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/tts), [paper #23](research/papers.md) |
| **TDD-anchor hook** 🟢 | Pre-commit hook ensures every diff has a corresponding test change | (automatic when TDD gate is on) | concept: [Verifier § TDD-anchor](concepts/verifier.md) |

## 9. Test-Time Scaling (TTS)

| Feature | Use case | How | Source |
|---|---|---|---|
| **Tournament-distilled TTS** 🟢 | Run N parallel coding attempts; eliminate via Recursive Tournament Voting; distill winners into the next round | `TournamentTts(...).run(task)` | [`tts/tournament.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/tts/tournament.py), [paper #1](research/papers.md) |
| **Parallel-Distill-Refine** 🟢 | Each attempt summarised into `{idea, what_worked, what_failed, why}`; next round seeded with distilled insight | (built into tournament) | same module |
| **MaTTS prefix injection** 🟢 | Each parallel slot gets a different ReasoningBank slice — diversifies the candidate pool | `matts_prefix_k=4` | same module + [`memory/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory) |
| **Family-disjoint judges** 🟢 | Tournament rounds judged by a different-family LLM than the one that generated — avoids monoculture grading | (automatic when 2+ provider families configured) | concept: [Subagents](concepts/subagents.md) |
| **Pareto-front filtering** 🟢 | Surfaces only attempts that aren't dominated on (score, length) | (built-in) | [`evolve/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/evolve) |

## 10. Plan mode + Org Mode

| Feature | Use case | How | Source |
|---|---|---|---|
| **Plan-mode artifact** 🟢 | Read-only design pass produces a structured `plan.md` you approve before execution | `/plan` then `/approve` · `lyra plan "task"` | [`plan/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/plan), concept: [Plan mode](concepts/plan-mode.md) |
| **Plan registry** 🟢 | Per-repo `.lyra/plans/` tracks every plan + outcome | (automatic) | same module |
| **Team roles + scheduler** 🟢 | PM / Architect / Engineer / Reviewer / QA + role-typed handoffs | `/team show \| plan \| run <task>` | [`teams/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/teams), [paper #15 MetaGPT](research/papers.md) |
| **Brains (curated bundles)** 🟢 | Personality + memory + skill presets: `default`, `tdd-strict`, `research`, `ship-fast` | `lyra brain install <name>` | [`brains/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/brains) |
| **GEPA-style evolver** 🟢 | Pareto-filtered prompt evolution (score↑ vs length↓) | `lyra evolve --task spec.yaml --generations N --population K` | [`evolve/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/evolve) |
| **Reflexion loop** 🟢 | When an attempt fails, generate a verbal lesson and inject into the next attempt | `/reflect on \| add \| tag \| clear` · `lyra_core.loop.reflexion` | [`loop/reflexion.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/loop), [paper #14](research/papers.md) |

## 11. Observability + HIR

| Feature | Use case | How | Source |
|---|---|---|---|
| **HIR (Harness Interaction Records)** 🟢 | Structured event log every external agent / replay tool can read | (automatic) | [`hir/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/hir), concept: [Observability](concepts/observability.md) |
| **OTel export** 🟢 | Standard tracing; ship spans to Jaeger / Honeycomb / Datadog | `LYRA_OTEL_EXPORTER=...` | [`observability/otel_export.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/observability/otel_export.py) |
| **JSONL trace per session** 🟢 | Every tool call / LLM hop / hook decision in `.lyra/sessions/<id>/trace.jsonl` | (automatic) | [`observability/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/observability) |
| **Replay (retro)** 🟢 | Re-run a past session deterministically; audit decisions | `lyra retro [<id>]` · `/why <tool-call-id>` | [`observability/retro.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/observability/retro.py) |
| **Trace viewer** 🟢 | In-REPL TUI: `/trace`, `/hir`, `/logs` | (automatic) | concept: [Observability](concepts/observability.md) |
| **Token observatory** 🟡 | Per-message token + cost breakdown (Phase M) | `/cost` · `lyra burn` | [`observability/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/observability) |
| **HUD `tracer_line` widget** 🟢 | Live indicator that OTel is exporting | (in `full` HUD preset) | [`hud/widgets.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/hud/widgets.py) |

## 12. Safety + permissions

| Feature | Use case | How | Source |
|---|---|---|---|
| **Permission bridge** 🟢 | Authorization is a runtime primitive — every tool call passes through a deterministic policy gate | (automatic) | [`permissions/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/permissions), concept: [Permission bridge](concepts/permission-bridge.md) |
| **Permission modes** 🟢 | `read-only` / `confirm-each-write` / `auto-execute` per session or per-tool | `/config set permission_mode=...` · per-mode defaults | reference: [Permission modes](reference/permission-modes.md) |
| **Destructive command detector** 🟢 | YAML-defined patterns (`rm -rf /`, `DROP TABLE`, …) require explicit confirm | edit `lyra_core/cron/destructive_patterns.yaml` | [`safety/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/safety) |
| **Safety monitor** 🟢 | Continuous cheap-model monitor running every N steps; raises on policy violation | (automatic) | [`safety/monitor.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/safety/monitor.py) |
| **Red-team patterns** 🟢 | Library of attack templates the safety monitor matches against | (automatic) | [`safety/redteam.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/safety/redteam.py) |
| **Worktree sandbox** 🟢 | Subagents can't touch the parent's working tree | (automatic on `/spawn`) | [`subagent/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/subagent) |

## 13. Sessions + persistence

| Feature | Use case | How | Source |
|---|---|---|---|
| **JSONL session persistence** 🟢 | Every turn appended to `<repo>/.lyra/sessions/<id>.jsonl`; resume across restarts | (automatic) | [`sessions/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/sessions), concept: [Sessions and state](concepts/sessions-and-state.md) |
| **Resume / continue / pin** 🟢 | `--resume <id>` · `--continue` (latest) · `--session <id>` (pin or create) | (CLI flags) | [`__main__.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/__main__.py) |
| **`/rewind` / `/redo`** 🟢 | Pop the last turn, restore state; re-apply with `/redo` | (in REPL) | [`interactive/session.py::rewind_one`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/interactive/session.py) |
| **JSONL migration** 🟢 | Auto-upgrade legacy session formats on resume | (automatic) | [`sessions/jsonl_migration.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/sessions/jsonl_migration.py) |
| **Session list + show** 🟢 | Browse persisted sessions; show metadata | `lyra session list \| show` | [`commands/session.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/session.py) |

## 14. Eval framework

| Feature | Use case | How | Source |
|---|---|---|---|
| **`pass@k` (Codex eq. 1)** 🟢 | Bias-corrected pass rate for N attempts | `lyra evals --passk N` | [`eval/passk.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/eval/passk.py), [paper #22](research/papers.md) |
| **`pass^k` (reliability metric)** 🟢 | Surfaces silent flakiness as `reliability_gap = pass@k − pass^k` | `lyra evals --passk N --json` | [`eval/passk.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/eval/passk.py), [paper #35](research/papers.md) |
| **Rubric scorer** 🟢 | Different-family LLM judges diff against prompt + acceptance tests | (automatic in `lyra evals`) | [`lyra_core/eval/rubrics/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/eval/rubrics) |
| **Drift-gate scorer** 🟢 | Compare today's eval output distribution to baseline; raise if drift | (automatic in `lyra evals`) | [`eval/drift_gate.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/eval/drift_gate.py) |
| **PRM scorer** 🟢 | Step-level correctness from a PRM model | (automatic when PRM configured) | [`eval/prm.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/eval/prm.py) |
| **τ-bench adapter** 🟢 | Run on τ-bench / τ³-bench (airline, retail, telecom, banking, voice) | `lyra evals --suite tau` | [`lyra-evals/adapters/tau_bench.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-evals/src/lyra_evals/adapters) |
| **Terminal-Bench 2.0 adapter** 🟢 | Run on the 89 hard CLI tasks; generate a submission file | `lyra evals --suite terminal-bench-2 --emit-submission` | [`lyra-evals/adapters/terminal_bench.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-evals/src/lyra_evals/adapters) |
| **SWE-bench-Pro adapter** 🟢 | Run on the SWE-bench-Pro corpus from a JSONL path you supply | `lyra evals --suite swe-bench-pro --tasks-path <jsonl>` | [`lyra-evals/adapters/swe_bench_pro.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-evals/src/lyra_evals/adapters) |
| **LoCoEval adapter** 🟢 | Long-horizon repo-conversation driver (50-turn, 64K–256K-token); set-based requirement-coverage scorer; bring your own LoCoEval JSONL | `lyra evals --suite loco-eval --tasks-path <jsonl>` | [`lyra-evals/adapters/loco_eval.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-evals/src/lyra_evals/adapters/loco_eval.py) |
| **Golden / red-team built-in suites** 🟢 | Ship-with-Lyra task corpora for smoke + drift checks | `lyra evals --suite golden \| red-team` | [`commands/evals.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/evals.py) |

How-to: [Run an eval](howto/run-eval.md).

## 15. Integration surfaces

| Feature | Use case | How | Source |
|---|---|---|---|
| **MCP client (stdio + HTTP)** 🟢 | Wrap any external tool as an MCP server; Lyra discovers + uses it | `/mcp add <name> --url <url>` · `lyra mcp save` | [`mcp/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/mcp), [`packages/lyra-mcp/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-mcp), how-to: [Add an MCP server](howto/add-mcp-server.md) |
| **MCP doctor** 🟢 | Health-check your MCP server config (auth, env, tools) | `lyra mcp doctor` | [`commands/mcp.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/mcp.py) |
| **ACP (Agent Client Protocol) host** 🟢 | Embed Lyra into an IDE / custom UI via stdio | `lyra acp` | [`acp/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/acp), [`commands/acp.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/acp.py) |
| **Plugins (pip-installable)** 🟢 | Third-party extensions distributed as pip packages | `pip install lyra-plugin-foo` · `/plugin enable foo` | [`plugins/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/plugins), how-to: [Write a plugin](howto/write-plugin.md) |
| **Cron skills** 🟢 | Scheduled, hands-off skill runs (e.g. nightly review) | `lyra_core/cron/` config | [`cron/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/cron), how-to: [Cron skills](howto/cron-skill.md) |
| **HTTP gateway / serve** 🟡 | Long-running daemon for inspector + remote control | `lyra serve --port 8080` | [`gateway/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/gateway), [`commands/serve.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/serve.py) |
| **LSP backend** 🟡 | Language-server-protocol surface for IDE integration | (config) | [`lsp_backend/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/lsp_backend), [`ide/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/ide) |
| **Terminal sandbox runner** 🟢 | Whitelisted shell command execution with audit | (automatic for shell tool) | [`terminal/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/terminal) |

## 16. Cost optimisation surface

Beyond two-tier routing, the following ship today:

| Feature | Saves you | How | Source |
|---|---|---|---|
| **Prompt-cache coordinator (PolyKV absorption)** 🟢 | One prefill, N-1 hits across sibling subagents reading the same shared document — 50–90 % discount on hosted-API providers that support prompt caching (Anthropic, OpenAI, DeepSeek, Gemini) | `coordinator.coordinate(provider="...", shared_text="...")` | [`providers/prompt_cache.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers/prompt_cache.py), concept: [Prompt-cache coordination](concepts/prompt-cache-coordination.md) |
| **NGC-style context compaction** 🟡 | 2–3× context-window compression with LLM-driven rerank | (automatic) | [`context/compactor.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/context/compactor.py), [paper #5](research/papers.md) |
| **Per-tool quotas** 🟢 | Cap LLM calls / shell commands / writes per turn | `/config set quotas.tools=...` | [`hooks/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/hooks), how-to: [Budgets and quotas](howto/budgets-and-quotas.md) |
| **Cost tracking (per-turn)** 🟢 | `/cost` command + bottom-toolbar `cost $X.XX` segment | (automatic) | [`agent/loop.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/agent/loop.py) |
| **Cost burn-down report** 🟢 | Per-day / per-repo / per-model breakdown | `lyra burn` | [`commands/burn.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/commands/burn.py) |

## 17. Internal subsystems (in `lyra-core`)

For exhaustive completeness — every directory under
`packages/lyra-core/src/lyra_core/`. The user-facing features are
indexed above; this is the underlying decomposition.

```text
acp        adapters    agent       arena       auth        brains
context    cron        diversity   eval        evolve      gateway
harnesses  hir         hooks       ide         klong       loop
lsp_backend  mcp       memory      meta        migrations  mock_llm
observability  org    permissions  plan        plugins     providers
retrieval  rl          routing     safety      sessions    skills
store      subagent    tdd         teams       terminal    tools
tts        verifier    wiki
```

Notes:

- `harnesses` is a deprecated alias for `adapters` — kept for one
  release for backward-compat imports.
- `arena`, `klong`, `meta`, `rl`, `wiki` ship as **importable Python
  APIs without a CLI surface yet**: real, tested code (Elo arena,
  schema-versioned checkpoint store, meta-harness outer loop, RL
  trajectory recorder, repo wiki + onboarding generator). They are
  reachable from your own scripts via `from lyra_core.<pkg> import
  …`; surfacing them through `lyra` subcommands is on the
  [v1.5 → v2 roadmap](roadmap-v1.5-v2.md).

## How to read this catalogue

Three angles:

1. **"What does Lyra do?"** → walk top to bottom; every shipped
   feature is here.
2. **"How do I invoke X?"** → find the row, read the *How* column
   (CLI flag, slash command, or Python API).
3. **"Where does the code live?"** → read the *Source* column;
   click through to read the implementation.

For task-driven recipes — *"I want to ship a feature with TDD"*,
*"I want to run on a budget"*, *"I want to evaluate against
benchmarks"* — see [Use cases](use-cases.md). For the research
provenance of every technique — *"where did Tournament TTS come
from?"* — see [Reference papers](research/papers.md). For the OSS
landscape — *"which Claude-Code repos do we vendor / pattern-mine
/ reject?"* — see [Reference repositories](research/repos.md).

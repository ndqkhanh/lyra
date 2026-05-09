# Full Parity & Frontier Convergence — Persistent Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement each wave's detailed plan.
> This roadmap is the parent index; per-wave plans live next to it under
> `docs/superpowers/plans/`.

**Date:** 2026-04-24
**Owner:** Lyra harness team
**Supersedes:** the wave-list section of
`docs/superpowers/specs/2026-04-24-full-parity-convergence-design.md`
(retains the §3 Phase-A detail for history; this roadmap takes over
ownership of all post-Phase-A waves).
**Status:** approved by user 2026-04-24 (option A: master roadmap +
detailed Wave-B plan up front; subsequent waves get their own
detailed plans when their predecessor ships).

---

## 1. Goal

Deliver every cell currently flagged as `NOW` / `v1.5` / `v1.7` / `v2`
/ stub in [`docs/feature-parity.md`](../../feature-parity.md) **plus**
the proposed net-new (★) and advanced frontier ideas — every claim in
the parity matrix backed by a verified code symbol and a passing
contract test, and every reference-repo capability either matched or
explicitly improved upon.

After this roadmap completes, the parity matrix should contain only
`✓ shipped` and `★ ✓ shipped` cells (no `NOW`, `v1.*`, `v2`, or
`stub` markers remain) and Lyra should be a strict superset of
claw-code, opencode, and hermes-agent on every feature axis.

## 2. Architecture

Five named waves landing as semver-tagged releases, each ~2–4 weeks of
focused work, each tested in isolation, each producing user-visible
value, and each gated on the previous wave's release.

```
v1.7.3 (shipped, Phase A) ──┐
                            │
                            ├─► v1.7.4 — Wave B — Local-First & Provider Polish ✓
                            │
                            ├─► v1.7.5 — Wave C — REPL Convergence ✓
                            │
                            ├─► v1.8   — Wave D — Agentic Backbone ✓
                            │
                            ├─► v1.9   — Wave E — Channels, Backends, Eval ✓
                            │
                            └─► v2.0   — Wave F — Frontier ✓
                                (15 frontier tasks shipped 2026-04-24;
                                 186 new RED/GREEN tests; whole-repo
                                 suite 1530 passed / 2 skipped / 0 failed)
```

**All six waves shipped 2026-04-24.** See the per-wave sections in §5 for
the shipped feature lists and the detailed plan docs cited in each.

## 3. Tech Stack

| layer | choice | rationale |
|---|---|---|
| language | Python 3.11+ | matches existing stack |
| async | `asyncio` (stdlib) + `httpx` for I/O | already in core; no new infra |
| testing | `pytest` + RED→GREEN discipline | matches existing 875-test suite |
| optional deps | `[project.optional-dependencies]` extras (`lyra[<area>]`) | preserves lean default install |
| degradation | `FeatureUnavailable("install lyra[<extra>]")` | user gets fix command, not stack trace |
| persistence | atomic JSON for state, SQLite + FTS5 for search | already adopted patterns |
| observability | OTel SDK (already shipped in v1.7.3) | every wave instruments its hot paths |

---

## 4. Invariants (apply to every wave)

These are inherited from the v1.7.3 master spec and are non-negotiable.

1. **TDD-first.** Every feature ships RED → GREEN → REFACTOR. Contract
   test file lands in the same commit as the implementation; the test
   is asserted to fail on the pre-implementation HEAD before the
   implementation lands.
2. **No breaking changes.** `make_*_tool(...)` signatures additive-only;
   JSON schemas additive-only; slash command names + aliases preserved.
3. **Evidence before assertion.** Every `✓ shipped` claim ends with a
   named code symbol + a verifiable test path.
4. **Optional deps.** Every net-new external package lands as an
   `[project.optional-dependencies]` extra (`lyra[oauth]`, `lyra[mcp]`,
   `lyra[bedrock]`, `lyra[vertex]`, `lyra[email]`, `lyra[slack]`,
   `lyra[matrix]`, `lyra[ssh]`, `lyra[modal]`, `lyra[daytona]`,
   `lyra[vision]`, `lyra[voice]`, `lyra[browser]`); a default
   `pip install lyra` must not pull any of them.
5. **Graceful degradation.** Missing optional dep → `FeatureUnavailable`
   with the exact `pip install lyra[<extra>]` fix command.
6. **Smoke vs unit.** Tests that touch network / system are marked
   `@pytest.mark.smoke` and skipped unless `LYRA_RUN_SMOKE=1`.
7. **Doc surface.** Each wave appends: (a) a `CHANGELOG.md` entry,
   (b) §5 / §5b / §5c / §5d / §5e / §5f delta-table rows in
   `docs/feature-parity.md` (one new section per wave), (c) cell flips
   from `NOW (stub)` / `v1.*` → `✓ shipped (vX.Y.Z)`, (d) snapshot
   version bump of the `Verification snapshot` section.
8. **Local-first stays local-first.** No wave is allowed to introduce a
   hard cloud dep on the auto cascade — Ollama + LM Studio + the
   pure-stdlib presets must remain a viable end-to-end path.
9. **Plan-mode-default-on stays default-on.** No wave is allowed to
   regress the Plan-mode auto-skip heuristic.
10. **Mock-LLM parity must keep passing.** Every wave that touches the
    agent loop ships a paired `ScriptedLLM` scenario in the parity
    harness so deterministic E2E tests stay green.

---

## 5. Wave catalogue

### Wave B — `v1.7.4 "Local-First & Provider Polish"`

**Detailed plan:** [`2026-04-24-v1.7.4-local-first-provider-polish.md`](./2026-04-24-v1.7.4-local-first-provider-polish.md)

**Theme:** make Lyra a strict superset of every ref repo on the
provider / local-model axis. User-asked-for-first.

**Features (12):**

1. `.env` parser for keys (`lyra_core/providers/dotenv.py`) —
   matches claw-code's `parse_dotenv` + `load_dotenv_file` semantics
   (export prefix, single/double quotes, comments).
2. Auth-sniffer hint (`lyra_core/providers/auth_hints.py`) —
   detects foreign provider creds when the requested provider is
   missing and recommends the model-prefix routing fix
   (claw-code's `anthropic_missing_credentials_hint` pattern,
   generalised across all providers).
3. Model alias registry (`lyra_core/providers/aliases.py`) —
   `opus` / `sonnet` / `haiku` / `grok` / `kimi` / `qwen-coder` /
   `llama-3.3` short names resolve to per-provider canonical slugs;
   adding an alias is a one-line registration.
4. Plugin `max_output_tokens` override (extend
   `lyra_core/providers/registry.py`) — `~/.lyra/settings.json`
   `plugins.maxOutputTokens` wins over the model default.
5. Context-window preflight (`lyra_core/providers/preflight.py`) —
   estimate input tokens (4 chars per token heuristic) + requested
   output; reject before the HTTP call when total exceeds the model's
   context window; raises `ContextWindowExceeded` with structured
   fields.
6. Provider routing (extend `lyra_cli/providers/openai_compatible.py`
   for the OpenRouter preset only) — `sort` (price / throughput /
   latency), `only`, `ignore`, `order`, `require_parameters`,
   `data_collection`; passed via `extra_body.provider`.
7. Fallback providers (`lyra_cli/providers/fallback.py`) —
   `FallbackChain([provider_a, provider_b, ...])` retries on classified
   transient failure (5xx, timeout, RateLimited); 4xx + auth failures
   short-circuit.
8. New presets bundle (extend `lyra_cli/providers/openai_compatible.py`):
   - **DashScope / Qwen / Kimi** (Alibaba) — `qwen-max`, `qwen-plus`,
     `qwen3-coder`, `kimi-k2.5`, `kimi-k1.5`.
   - **Bedrock** (Anthropic via AWS) — `lyra[bedrock]` extra installs
     `boto3`; uses SigV4 signing.
   - **Vertex AI** (Google Cloud Gemini + AnthropicVertex).
   - **GitHub Copilot** (`lyra[copilot]`) — uses GitHub OAuth token.
   - **Local presets**: vLLM, llama.cpp `server`, TextGenerationInference,
     Llamafile, MLX-LM (Apple Silicon) — all OpenAI-compatible, all
     `auth_scheme="none"`, all probe-based.
9. `/auth` slash command (`lyra_cli/interactive/auth.py`) — device-code
   OAuth flow for Copilot + Bedrock STS web-identity; persists tokens
   to `~/.lyra/auth.json` with `chmod 600`.
10. `/model list` real + Alt+P picker (extend
    `lyra_cli/interactive/session.py`) — flips the v1.7.2 toast-only
    placeholder to a real interactive picker over `iter_presets()` +
    `PROVIDER_REGISTRY`.
11. `/diff` real (`git diff --stat` + per-file unified diff) — flips the
    v1.7.2 stub.
12. Telemetry on the cascade — emits a `provider_selected` HIR event
    for every `build_llm` invocation so the OTel exporter (shipped in
    v1.7.3) records which backend handled each turn.

**Optional deps introduced:** `lyra[bedrock]` (boto3),
`lyra[vertex]` (`google-cloud-aiplatform`), `lyra[copilot]` (no extra
dep; uses `httpx` + stdlib OAuth), `lyra[oauth]` (umbrella for the
above).

**Test target:** ~80 new RED/GREEN contract tests across ~10 new
files. Full suite target: 875 → ~955 green.

**Success criteria:**
- `lyra run --llm auto` from a machine with `OLLAMA_HOST` set + no
  cloud keys still succeeds against `qwen2.5-coder:1.5b`.
- `lyra run --llm bedrock` against an AWS profile succeeds without
  any extra config beyond `AWS_PROFILE`.
- `lyra run --llm openrouter` with `provider_routing.sort = "price"`
  in `~/.lyra/config.yaml` routes to the cheapest provider.
- `lyra run --llm copilot` after `lyra /auth copilot` succeeds.
- `pip install lyra` (no extras) still launches REPL and uses
  Anthropic / Ollama / mock as available.

---

### Wave C — `v1.7.5 "REPL Convergence"`

**Detailed plan:** [`2026-04-24-v1.7.5-repl-convergence.md`](2026-04-24-v1.7.5-repl-convergence.md)
— task-by-task breakdown was authored alongside the v1.7.4 ship and
is ready for subagent-driven execution.

**Theme:** finish every slash command + keybind cell in §1.1–§1.3 of
the parity matrix.

**Features (~30):**

- **Slash commands flipped from NOW to ✓ shipped:**
  `/rewind`, `/resume`, `/fork`, `/rename`, `/sessions`, `/export`,
  `/diff` (already in Wave B), `/map`, `/blame`, `/trace`, `/self`,
  `/badges`, `/theme` (3 themes real), `/vim` (real toggle stored in
  session prefs), `/config` (read/write `~/.lyra/config.yaml`),
  `/mode` (full mode dispatcher), `/effort` (interactive slider with
  arrow-key UI), `/ultrareview` (multi-agent review fan-out),
  `/review` (post-turn verifier — TDD gate + safety + evidence),
  `/tdd-gate on|off` (state-machine toggle), `/red-proof` (asserts the
  next test fails before allowing implementation),
  `/tools` (lists registered tools with schemas), `/btw` (side-question
  context isolation), `/handoff` (markdown PR description from
  session summary), `/pair` (pair-programming dual-cursor stream),
  `/budget set` (cost / token hard cap with alert).
- **Keybinds flipped from NOW to ✓ shipped:**
  `Ctrl+T` (live task panel toggle real), `Ctrl+O` (verbose tool-call
  output), `Ctrl+F` (kill all background subagents — depends on
  Wave D's subagent registry, so guarded), `Esc Esc` (rewind last turn
  persistent), `Tab` (cycle modes 5-state), `Alt+T` (deep-think real
  toggle stored in session), `Alt+M` (permission mode toggle).
- **Modes flipped:** `build` real (tied to permission gate), `explore`
  real (read-only subagent dispatch), deep-think mode toggle real.
- **Paste-as-image placeholder:** stores image to
  `~/.lyra/sessions/<id>/attachments/` with placeholder
  `[Image #N]` in the prompt.

**Test target:** ~120 new RED/GREEN contract tests.

**Success criteria:**
- Every slash command in §1.3 of the parity matrix is `✓ shipped`.
- Every keybind in §1.2 is `✓ shipped`.
- `/diff` shows real `git diff --stat` + per-file diffs.
- `/handoff` produces a paste-able PR description.

**Risks & mitigations:**
- `/pair` needs a streaming subagent path that doesn't exist yet → ship
  as a "hold this terminal pane open while I run" UX in Wave C, true
  pair streaming lands in Wave D when the subagent backbone is real.
- `/red-proof` requires the TDD state machine, which is a Wave-F item
  → Wave-C ships the slash + a minimal "run pytest, assert
  red-result" loop; full state-machine integration in Wave F.

---

### Wave D — `v1.8 "Agentic Backbone"` — ✓ SHIPPED 2026-04-24

**Detailed plan:** [`2026-04-24-v1.8-agentic-backbone.md`](2026-04-24-v1.8-agentic-backbone.md)
— task-by-task breakdown landed alongside the Wave-C ship.

**Status:** all 15 tasks GREEN; 87 new contract tests; combined
pytest run **1143 passed**, 0 regressions (4 failures + 7 errors
are sandbox-only `git init` denials carried over from Wave-A/B).
See `CHANGELOG.md` v1.8.0 entry and `docs/feature-parity.md` §5e
for the row-by-row delta. Highlights:

- `SubagentRunner` + live `SubagentRegistry` + `Ctrl+F` re-focus.
- `~/.lyra/agents/<name>.yaml` user presets (3 built-ins).
- DAG scheduler (level-by-level, bounded parallelism, skip-on-failure).
- `run_variants` best-of-N with default-judge fallback.
- `PermissionStack` (destructive + secrets + injection) + per-session
  `ToolApprovalCache`.
- Real `ExecuteCode` (subprocess + AST allow-list), real `Browser`
  (Playwright + graceful "install lyra[browser]" fallback), custom
  `~/.lyra/tools/<name>.py` loader with `@tool` decorator.
- `LifecycleBus` (6 events), `MCPRegistry` + `trust_banner_for`,
  `BudgetMeter` (token-→-USD ledger + `gate()`), `PreflightPlugin`
  (Wave-B carry-over), `PairStream` (live-stream `/pair`).

**Theme:** the heaviest wave — the parts that make Lyra "agentic" at
parity with claw-code's `Task` tool, opencode's subagent system, and
hermes's plugin model.

**Features (~25):**

- **Subagent presets:** `Explore` (Haiku-class read-only), `General`
  (multi-step full-tool), `Plan` (research-only), `leaf` /
  `orchestrator` aliases for hermes muscle memory; user-defined
  subagents from `~/.lyra/agents/<name>.yaml`.
- **DAG scheduler:** `subagent.task(..., depends_on=[id, ...])` with a
  topological executor; supports fan-out + join.
- **Variant runs:** `subagent.task(..., variants=N)` runs N
  candidates in parallel (different model + temperature combos) and
  picks the winner with a Rubric PRM (depends on Wave F's PRM, so
  Wave-D ships the multi-candidate fan-out and a basic LLM-judge
  selector; full PRM integration is Wave F).
- **Memory subsystem (full):**
  - **Procedural** — skills already shipped; finalise the trigger
    matcher.
  - **Episodic** — trace digests per session; auto-ingested by the
    Title / Summary subagent (async).
  - **Semantic** — facts / wiki entries surfaced via `/wiki`.
  - **Vector / dense retrieval** — `lyra[vector]` extra installs
    `chromadb` or `qdrant-client`; pluggable backend.
  - **Agent-curated memory nudges** — agent emits structured
    "remember this" calls; user gets a one-tap accept/reject.
- **Hooks (real lifecycle):** `SessionStart`, `SessionEnd`,
  `UserPromptSubmit`, `PermissionRequest`, `SubagentStart`,
  `SubagentStop`, `FileChanged` (via `watchdog`), `WorktreeCreate`,
  `ErrorThrown`, `TurnRejected`. All wired into `PluginRuntime`.
- **Permissions stack (real):** mode-based gating, destructive command
  detector (regex pack + LLM-augmented), secrets scanner (regex pack
  for AWS / Stripe / GitHub / GCP / Azure / Twilio), prompt-injection
  guard on tool output (string-similarity to instruction-set + LLM
  classifier), MCP trust banner (first-use prompt), allowlist
  (`/less-permission-prompts`).
- **Tool-approval prompt** real (mode-gated, cached per session).
- **`ExecuteCode` (CodeAct sandbox)** — `lyra[codeact]` extra installs
  `pyodide` for Python; `firejail` / `nsjail` profile for native; tool
  surfaces stdout / stderr / return.
- **`Browser` tool (headless)** — `lyra[browser]` extra installs
  `playwright`; `browser_navigate`, `browser_screenshot`, `browser_click`,
  `browser_type`, `browser_evaluate` tools.
- **Custom user tools** — real registry under
  `~/.lyra/tools/<name>.py` with `@tool` decorator; lifecycle = lazy
  import on first invocation, sandbox via `multiprocessing` worker.
- **MCP** — full client (already partial) + full server (already partial);
  `/mcp` slash dispatcher; trust banner; manifest signing.
- **RL trainer binding** — `rl_start_training`, `rl_metrics`,
  `rl_results` real; pipes the existing `TrajectoryRecorder` JSONL into
  Tinker-Atropos via `lyra[rl]` extra.
- **Skill auto-extractor** — analyses session transcripts for repeated
  successful patterns; proposes a `~/.lyra/skills/<name>.md` PR.
- **Skill-Creator v2** — 4-agent loop (drafter → reviewer → tester →
  promoter) ships, uses subagent presets above.
- **Plugin runtime lifecycle** — install / enable / disable / uninstall
  + hook dispatch fully wired into `PluginRuntime`.
- **Wave-B carry-over: agent-loop preflight wiring.** Wave B shipped
  `lyra_core.providers.preflight` as a library helper; Wave D wires it
  into the actual call path so `lyra run` short-circuits oversized
  prompts *before* a billed round-trip (configurable via
  `~/.lyra/settings.json` → `preflight: { mode: "warn" | "raise" |
  "off" }`). Tests: 8 contract tests covering on/off/warn modes,
  stream-token estimation, tool-payload accounting, and the
  `/compact` suggestion banner.

**Test target:** ~150 new RED/GREEN contract tests.

**Success criteria:**
- A user can write `~/.lyra/agents/researcher.yaml`, run `/spawn
  researcher: investigate X`, and the subagent runs to completion with
  worktree isolation.
- A user can `/spawn` 5 variants in parallel and pick the winner.
- A user can install a third-party MCP server and the trust banner
  appears on first use.
- `lyra run --tool browser_navigate "..."` opens a headless Chromium
  and returns the rendered DOM.

---

### Wave E — `v1.9 "Channels, Backends, Eval"` — ✅ SHIPPED 2026-04-24

**Detailed plan:** [`2026-04-24-v1.9-channels-backends-eval.md`](2026-04-24-v1.9-channels-backends-eval.md) — completed 2026-04-24.

**Result:** 93 new RED/GREEN contract tests, all 15 wave tasks merged.
Channel substrate (`lyra_cli/channels/*`), 16 channel adapters
(Slack/Discord/Matrix/Email/SMS plus the 11 long-tail HTTP-shaped
ones via the shared `_HttpChannelAdapter` base), 4 remote terminal
backends (Modal/SSH/Daytona/Singularity) replacing the v1.7.2
stubs, the vision toolkit (`image_describe`/`image_ocr`), the
voice toolkit (STT/TTS + `/voice`), session replay (`/replay`),
the red-team corpus + scorer, the golden eval corpus + drift
gate, and the live `/wiki` + `/team-onboarding` generators.
Whole-repo regression: **1339 passed**, only pre-existing
git-sandbox worktree tests fail.

**Theme:** match hermes-agent on every channel adapter and remote
terminal backend; build the eval gates that Lyra's TDD-first identity
needs.

**Features (~35):**

- **Channel adapters real (replacing stubs / new):**
  - Slack (`lyra[slack]`, `slack-sdk`)
  - Discord (`lyra[discord]`, `discord.py`)
  - Matrix (`lyra[matrix]`, `matrix-nio`)
  - Email (`lyra[email]`, IMAP+SMTP via stdlib + `aioimaplib`)
  - SMS (`lyra[sms]`, Twilio + Vonage backends)
  - Feishu / Lark (`lyra[feishu]`)
  - WeCom (`lyra[wecom]`)
  - Mattermost (`lyra[mattermost]`)
  - BlueBubbles (`lyra[bluebubbles]`)
  - WhatsApp (`lyra[whatsapp]`, via Twilio)
  - Signal (`lyra[signal]`, signal-cli REST)
  - OpenWebUI (`lyra[openwebui]`)
  - HomeAssistant (`lyra[homeassistant]`)
  - QQBot (`lyra[qqbot]`)
  - DingTalk (`lyra[dingtalk]`)
  - Generic Webhooks (no extra dep)
- **Terminal backends real (replacing v1.7.2 stubs):**
  - `ModalBackend` (`lyra[modal]`, `modal`)
  - `SSHBackend` (`lyra[ssh]`, `paramiko` or `asyncssh`)
  - `DaytonaBackend` (`lyra[daytona]`)
  - `SingularityBackend` (`lyra[singularity]`, subprocess to
    `singularity` CLI)
- **Vision** (`lyra[vision]`, `opencv-python` + `pillow`):
  `image_describe`, `image_ocr`, paste-as-image hookup.
- **TTS / voice mode** (`lyra[voice]`, `openai-whisper` or `faster-whisper`
  for STT; `openai` `audio.speech` or `pyttsx3` for TTS).
- **Session list real** (already shipped in Wave C as `/sessions`)
  + **session replay** (event-by-event step with diff overlay).
- **Red-team corpus + safety monitor** —
  `tests/red_team/<category>/case_<id>.yaml`; safety monitor runs the
  corpus on a schedule and reports regressions.
- **Golden eval corpus + drift gate** — `tests/golden/<id>.yaml`;
  `lyra eval drift` produces a delta report against `main`.
- **SWE-bench Pro / LoCoEval adapters** — `lyra eval swe-bench-pro
  --instance <id>` runs against the adapter; CI integration optional.
- **`/wiki`** — Devin-Wiki-style repo wiki UI; pluggable backend
  (file-system markdown by default; Notion / Confluence via `lyra[wiki-*]`
  extras).
- **`/team-onboarding`** — generates a teammate-targeted
  `ONBOARDING.md` from skills + recent sessions.
- **`/less-permission-prompts`** — interactive allowlist editor.

**Test target:** ~200 new RED/GREEN contract tests.

**Success criteria:**
- `lyra gateway start --channel slack,discord,email` starts the
  daemon and three channel listeners.
- `lyra run --backend modal --image python:3.12 --task "..."` runs the
  agent loop on Modal with results streamed back.
- `lyra eval drift --baseline v1.8.0` produces a markdown drift
  report.

**Risks & mitigations:**
- Many channel APIs require live credentials → ship `FakeBackend`
  doubles for unit tests; smoke gated on `LYRA_CHANNEL_<NAME>_TOKEN`.
- Modal / Daytona costs real money in smoke → smoke gated on
  `LYRA_RUN_PAID_SMOKE=1` separately from `LYRA_RUN_SMOKE`.

---

### Wave F — `v2.0 "Frontier"` — ✓ SHIPPED 2026-04-24

**Detailed plan:** [`2026-04-24-v2.0-frontier.md`](2026-04-24-v2.0-frontier.md) — written 2026-04-24, executed 2026-04-24. Consolidated the 17 ★ net-new features and 14 frontier ideas into 15 task buckets (`f1`…`f15`); all 15 tasks shipped with contract tests (186 new RED/GREEN tests, whole-repo suite 1530 passed / 2 skipped / 0 failed, sandbox-bound git tests deselected).

**Theme:** every ★ net-new + frontier idea ships, plus the IDE
bridges. This is the wave that makes Lyra a frontier research harness
on top of the parity baseline.

**Features (~30):**

**Net-new (★) from §3 of the parity matrix:**

1. **TDD phase tracking as first-class state** —
   `IDLE → PLAN → RED → GREEN → REFACTOR → SHIP` state machine; cell
   advances on evidence (test result, diff applied, commit). Strict
   mode rejects the wrong transition. Sits in `lyra_core/tdd/state.py`.
2. **Cross-channel verifier** — for every assistant turn, compare
   trace claims (`I edited foo.py:34`) vs git diff vs filesystem
   snapshot; reject hallucinated file:line citations before the user
   sees them.
3. **Refute-or-Promote adversarial stage** (SWE-TRACE) — adversarial
   subagent attempts to refute the proposed solution; if the refute
   succeeds, the solution loops back to PLAN.
4. **Rubric Process Reward Model** — model-based subjective verifier;
   rubrics in `lyra_core/eval/rubrics/`; pluggable judge model.
5. **Neural Garbage Collection compactor** (NGC) — grow-then-evict
   compactor with outcome-logged training corpus
   (`compactor-outcomes.jsonl`). Replaces the v1.7.3 LLM-driven
   `/compact` for users who opt in.
6. **Reuse-first hybrid skill router** — BM25 + dense + description
   match with explicit `NO_MATCH` / `AMBIGUOUS` verdicts; replaces the
   current trigger-matcher.
7. **Trigger description auto-optimizer** — `lyra skills tune <name>`,
   5-iteration bounded loop on a 60/40 eval split; persists improved
   descriptions to the skill file.
8. **In-session skill synthesis** — repetition detector +
   bundled-script detector + `/creator` slash command + outcome
   attribution.
9. **Harness plugins as first-class** —
   `--harness=dag-teams|single-agent|three-agent|agentless|codeact|meta`;
   each is a registered `HarnessPlugin` with `plan` / `execute` /
   `verify` hooks.
10. **Meta-harness outer loop** — Lyra optimises its own harness
    against the user's repo via a meta-task that runs the parity
    harness corpus.
11. **Harness arena** — blind A/B tournament runner;
    `lyra arena --harnesses dag-teams,three-agent --task "..."`
    produces a winner + audit trail.
12. **Federated skill registry** with sigstore signing + policy
    admission; pluggable transports (HTTP, S3, IPFS).
13. **KLong-style checkpoint & resume across model generations** —
    snapshot every state at compaction boundaries so a new model can
    pick up where the old one left off.
14. **Multica team orchestration + federated retros** — multi-tenant
    team dashboards.
15. **`/review --auto` post-turn verifier** — TDD gate + safety monitor
    + evidence validator on a single button.
16. **`/eval-drift`** — already partially in Wave E; this wave wires
    it to the rubric PRM.
17. **`/golden add`** — already in Wave E; wired to reviewer approval
    here.
18. **`/handoff` — extended** — already shipped in Wave C as a stub →
    Wave F flips it to real (PR description + reviewer-friendly
    summary + open-questions list).

**Frontier ideas from §4 of the parity matrix:**

19. **`/split` + `/vote`** — fork session into N parallel candidates
    with different models, evaluator picks. Builds on Wave D's variant
    runs.
20. **Speculative agents** — dispatch an `explore` subagent ahead of
    the main loop to pre-compute likely context.
21. **Ambient budget meter** — small status-bar widget tracking $
    burn rate; alerts on > 3σ vs session median spikes.
22. **Skill diff** — when a proposed skill conflicts with an existing
    one, surface the semantic delta + the trajectories each was
    extracted from.
23. **Outcome-weighted memory retrieval** — episodic memory rank
    biased by downstream success of similar past turns.
24. **TDD mutation testing** — after `GREEN`, optionally run a
    mutation tester (`mutmut`); use survival rate as extra evidence
    for `/review`.
25. **Policy-as-code debugger** — when a permission denies a tool
    call, show the rule file + line that denied.
26. **`/observe` live panel** — Rich `Live` region streams tool calls,
    token deltas, hook fires.
27. **`/replay <session-id>`** — step through a past session
    event-by-event with diff/state overlays.
28. **Graph-of-sessions** — DAG view of `/fork` branches across a
    repo's Lyra history.
29. **Intent embeddings** — embed the user's goal once per session
    and use it to bias tool selection.
30. **Failure-first learning** — escalate post-hoc on sessions with
    rejected plans or reverted commits; feed into the skill extractor
    before successful ones.
31. **Dogfood-only features behind `/self`** — every new feature must
    be usable from `/self use` before graduating to user-facing.
32. **VS Code / Zed / JetBrains bridge** — on top of the v1.7.2 ACP
    scaffold; LSP-style integration.

**Optional deps introduced:** `lyra[vector]` (chromadb/qdrant),
`lyra[mutmut]`, `lyra[sigstore]`, `lyra[ide-bridge]`.

**Test target:** ~250 new RED/GREEN contract tests + the meta-harness
corpus (which is itself a test fixture).

**Success criteria:**
- A new feature added to Lyra triggers a meta-harness self-test that
  reproduces the feature's user story end-to-end before merge.
- `lyra arena` produces a publishable A/B comparison report.
- The federated skill registry can install a sigstore-signed skill
  pack from a third-party publisher with an audit trail.

---

## 6. Cross-wave dependencies

| dependency | from wave | to wave | resolution |
|---|---|---|---|
| Subagent registry (`SubagentRegistry`) | A (shipped) | C (`Ctrl+F` kill all subagents) | Wave C uses the registry; Wave A's API is stable. |
| Subagent presets | D | F (variant runs winner picker) | Wave D ships variants with LLM-judge fallback; Wave F flips to PRM. |
| TDD state machine | F | C (`/red-proof`, `/tdd-gate`) | Wave C ships minimal "run pytest assert red" path; Wave F flips to full state machine. |
| Plugin runtime lifecycle | D | F (harness plugins) | Wave D ships full lifecycle; Wave F adds `HarnessPlugin` shape on top. |
| Memory subsystem | D | F (outcome-weighted retrieval) | Wave D ships embeddings; Wave F adds outcome weighting. |
| Provider routing | B | F (cost-aware router per turn) | Wave B ships static config; Wave F flips to per-turn router based on PRM signals. |
| OAuth flow | B | E (Slack / Discord / etc.) | Wave B builds the device-code framework; Wave E reuses for channels. |
| `.env` parsing | B | every wave | Wave B's parser is reused for any new credential surface. |

---

## 7. Risk register (cross-wave)

| risk | mitigation |
|---|---|
| Vendor API breakage during long roadmap | Every wave ships `FakeBackend` doubles + smoke tests gated on `LYRA_RUN_SMOKE`. |
| Optional-dep matrix combinatorial explosion | `lyra[full]` umbrella that pulls every extra; CI matrix runs `[]`, `[bedrock,vertex,copilot]`, `[full]`. |
| Test-suite runtime grows past 5 min | Mark slow tests `@pytest.mark.slow`; default `pytest -q` excludes them; nightly runs full. |
| Sandboxed-CI git permission flakes | Already mitigated by deselecting in v1.7.2/v1.7.3; future wave plans must inherit the same `pytest.ini` deselect list. |
| User abandons mid-wave | Each wave is independently shippable; partial-completion still flips a coherent set of cells in the parity matrix. |
| Breaking change creeps in | Every wave plan ships a "compat audit" task that diff's exported symbols against the previous tag. |
| Local-model story regresses under cloud-feature pressure | Invariant 8: every wave plan must include an "Ollama auto-cascade still works" smoke test. |
| Frontier ideas balloon Wave F scope | Wave F is internally sub-divided into F.1 (core ★) and F.2 (frontier); F.1 ships first. |
| LLM cost during eval / arena scales linearly with feature count | Mock-LLM parity harness covers 95% of E2E paths; only nightly runs use real models. |
| Plugin sandbox escape (Wave D + F) | Plugins run in `multiprocessing` workers with `seccomp` profile on Linux; manifest signed via sigstore in Wave F. |

---

## 8. Sequencing & gates

### Gate to start each wave

1. **Previous wave's release tag pushed.**
2. **Previous wave's parity-matrix delta section appended.**
3. **Full test suite green at the previous wave's tag.**
4. **No `FIXME` or `TODO(wave-X)` strings remain in the previous
   wave's diff.**
5. **`pip install lyra[full]` from the previous tag boots `lyra repl`
   without error.**

### Gate to ship each wave

1. **Every detailed-plan task is checked off.**
2. **Full test suite green** (`python3 -m pytest -q` from
   `projects/lyra/`).
3. **Smoke suite green** for any feature that touches network / system
   when the relevant `LYRA_RUN_SMOKE=1` is set.
4. **Parity-matrix delta section appended** to
   `docs/feature-parity.md` with one row per feature, named code
   symbol + test path.
5. **Verification snapshot version bumped** at the top of the parity
   matrix.
6. **CHANGELOG.md updated** with feature list + test count delta.
7. **Mock-LLM parity harness green** — every new agent-loop touchpoint
   has a paired `ScriptedLLM` scenario.
8. **Adversarial-reviewer self-review pass run** on the diff (per the
   adversarial-reviewer skill in the workspace).
9. **Tag pushed** (`v1.7.4`, `v1.7.5`, `v1.8.0`, `v1.9.0`, `v2.0.0`).

### Wave-to-wave handoff

- The **last task of every wave** is "write the next wave's detailed
  plan based on this roadmap + any learnings from the just-finished
  wave". This keeps the roadmap a living document and prevents
  speculative over-planning.
- A **wave can be split** if a feature reveals more depth than
  expected: e.g. Wave D's RL trainer might split into v1.8.0 (subagents
  + memory + hooks + permissions) and v1.8.1 (RL + skill-creator
  v2 + plugin lifecycle), with the parity matrix advancing one column
  at a time.
- **No feature crosses wave boundaries silently.** If a Wave-C feature
  needs a Wave-D capability, it ships behind a feature flag in Wave C
  and the flag flips in Wave D.

---

## 9. Documentation surface (per wave)

Every wave appends:

1. **`CHANGELOG.md`** — a `vX.Y.Z "<theme>"` entry with feature list +
   test count delta + breaking-change note (always "none" per
   invariant 2).
2. **`docs/feature-parity.md` §5x delta table** — one row per feature
   shipped, with `area | ref-repo source | Lyra symbol | parity
   status | test file` columns; matches the §5 / §5b template.
3. **Cell flips** — every `NOW` / `v1.*` / `v2` / `stub` cell affected
   flips to `✓ shipped (vX.Y.Z)` with the symbol path appended.
4. **Verification snapshot bump** — `**Status**: living document, v0.X
   snapshot on YYYY-MM-DD (post vX.Y.Z "<theme>"; supersedes …)`.
5. **`README.md`** — feature list under "What's new" if the wave adds
   a marquee user-visible capability.
6. **`docs/system-design.md`** — diagram update if the wave changes
   architecture (adds a subsystem / removes one).
7. **`docs/threat-model.md`** — entry per new attack surface (new
   permission, new sandbox, new IPC).

---

## 10. Owner & Cadence

- **Owner:** Lyra harness team (single-maintainer mode currently).
- **Cadence:** one wave every 2–4 weeks; total roadmap ≈ 4 months
  end-to-end if done sequentially. Faster if waves are parallelised
  across contributors (waves are dependency-light enough that B + E
  could run concurrently, for instance).
- **Reporting:** at the end of every wave, a one-page `WAVE-X-REPORT.md`
  is committed to `docs/wave-reports/` summarising what shipped, what
  slipped, and what changed for the next wave. (This becomes the
  source of truth for the next wave's plan.)

---

## 11. What's NOT in this roadmap

- **Native mobile app.** Out of scope; Lyra is CLI-first.
- **Hosted cloud product.** Out of scope; Lyra is local-first.
- **Custom training infra (beyond Atropos)** — RL is Wave D scope but
  custom GPU orchestration is not.
- **Generic web UI.** The IDE bridges in Wave F cover the editor
  story; a separate web UI is not on the roadmap.
- **Multi-user collaboration server.** The Multica federated retros
  in Wave F are the limit; dedicated server hosting is out of scope.
- **Anything that breaks the local-first invariant.** Any cloud
  dependency must be optional and gracefully degrade.

---

## 12. Single source of truth

If this roadmap and the parity matrix disagree, **the parity matrix
wins** — it's the cell-level truth. This roadmap groups cells into
shippable waves and provides sequencing, but it does not invent new
features. Any feature added to a wave must first be added to the
parity matrix.

If this roadmap and a per-wave detailed plan disagree, **the
detailed plan wins** — it's the implementation truth. The roadmap is
strategic; the per-wave plans are tactical.

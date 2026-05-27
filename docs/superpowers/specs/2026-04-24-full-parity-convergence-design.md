# Full Parity Convergence — Multi-Phase Design

**Date**: 2026-04-24
**Supersedes**: none (complements `2026-04-24-ui-refs-fusion-design.md`
which was the v1.7.2 scoped spec)
**Owner**: Lyra harness team
**Status**: approved for execution 2026-04-24

---

## 1. Summary

After the v1.7.2 "Integrity + Fusion" pass the parity matrix still
carries **~50–60 distinct not-yet-real features** (grep-verified: 99
cells with `v1.5` / `v1.7` / `v2` / `stub` / `NOW` markers across
`docs/feature-parity.md`). The user has approved "implement all
missing features" with the caveat that each pass picks its own
named cadence and ships with TDD discipline.

This spec decomposes the full remaining backlog into **five named
phases** (`v1.7.3` through `v2`). Phase A (v1.7.3) is executed in
the current session with detailed per-feature design. Phases B–E
are enumerated as targeted passes with feature lists and
dependencies, and will each get their own focused spec before
execution.

## 2. Invariants (apply to every phase)

1. **TDD-first**. Every feature ships RED → GREEN → REFACTOR. A
   contract test file lands in the same commit as the implementation;
   the test is asserted to fail on the pre-implementation HEAD before
   the implementation lands.
2. **No breaking changes**. `make_*_tool(...)` signatures are
   additive-only; JSON schemas are additive-only; slash command
   names + aliases preserved.
3. **Evidence before assertion**. Every `✓ shipped` claim in the
   parity matrix ends with a named code symbol + a verifiable test
   path; re-running the suite must reproduce the claim.
4. **Optional deps**. Every net-new external package lands as an
   `[project.optional-dependencies]` extra (`lyra[lsp]`,
   `lyra[docker]`, `lyra[telegram]`, `lyra[otlp]`, `lyra[web]`); a
   default `pip install lyra` must not pull any of them.
5. **Graceful degradation**. When an optional dep is missing, the
   feature raises a clear `FeatureUnavailable("install lyra[<extra>]")`
   rather than `ImportError`, and the feature's contract tests use
   injectable fakes so they pass without the real dep installed.
6. **Smoke vs unit**. Tests that touch network/system (Docker, Telegram
   Bot API, OTLP collector) are marked `@pytest.mark.smoke` and skipped
   unless `LYRA_RUN_SMOKE=1` is set.
7. **Doc surface**. Each phase appends: (a) a `CHANGELOG.md` entry,
   (b) §5 delta-table rows in `docs/feature-parity.md`, (c) cell flips
   from `NOW (stub)` / `v1.*` → `✓ shipped (v1.X.Y)`, (d) snapshot
   version bump of the `Verification snapshot` section.

---

## 3. Phase A — v1.7.3 "Cross-Repo Convergence" (12 features)

Executed in this session. Detailed per-feature design below. Each
feature gets one sub-section with package target, contract, test
plan, and explicit RED assertion.

### A.1 `/compact` real — LLM-driven context summariser

- **Target**: `lyra_core/context/compactor.py` (new) +
  `lyra_cli/interactive/session.py::_cmd_compact` (edit)
- **Contract**:
  ```python
  def compact_messages(
      messages: list[dict],
      *,
      llm: Callable[..., dict],
      keep_last: int = 4,
      max_summary_tokens: int = 800,
  ) -> CompactResult
  ```
  where `CompactResult = dataclass(kept_raw: list, summary: str,
  dropped_count: int, summary_tokens: int)`.
- **Behaviour**: keep the last `keep_last` turns raw; summarise
  everything before into a single system-role message; return
  **both** so the caller can archive the raw turns before writing
  only the summary into live context (supports `/uncompact` rollback
  later).
- **Test file**: `lyra-core/tests/test_context_compactor_contract.py`
- **RED tests (5+)**:
  1. `test_keeps_last_n_turns_raw`
  2. `test_summarises_head_block_via_llm`
  3. `test_preserves_system_soul_messages`
  4. `test_returns_dropped_count_matches_summary_replacement`
  5. `test_compactresult_tokens_are_counted`

### A.2 `/context` real — token grid renderer

- **Target**: `lyra_core/context/grid.py` (new) +
  `lyra_cli/interactive/session.py::_cmd_context` (edit)
- **Contract**:
  ```python
  def render_context_grid(messages: list[dict], *, columns: int = 60) -> str
  ```
  Returns a monospaced grid of `█` / `▓` / `░` characters where each
  cell is one message weighted by its token count; a legend and totals
  line follow underneath.
- **Test file**: `lyra-core/tests/test_context_grid_contract.py`
- **RED tests (4+)**:
  1. `test_empty_conversation_renders_empty_grid_with_legend`
  2. `test_single_message_renders_single_cell_proportional_to_tokens`
  3. `test_totals_line_sums_all_messages`
  4. `test_wraps_to_columns_width`

### A.3 `/agents` + `/spawn` real — wire to task tool

- **Target**: `lyra_core/subagent/registry.py` (new) +
  `lyra_cli/interactive/session.py::_cmd_agents`, `_cmd_spawn` (edit)
- **Contract**: Replace stubbed handlers with a `SubagentRegistry`
  that tracks live children (id, description, state, started_at),
  backed by the existing `task` tool. `/spawn <desc>` returns the
  new child's id; `/agents` lists live and completed children.
- **Test file**: `lyra-cli/tests/test_slash_agents_and_spawn_real.py`
- **RED tests (5+)**:
  1. `test_agents_empty_registry_returns_friendly_empty_state`
  2. `test_spawn_registers_subagent_and_returns_id`
  3. `test_agents_lists_running_and_completed`
  4. `test_spawn_respects_subagent_type_kwarg`
  5. `test_spawn_bad_quoting_returns_friendly_error`

### A.4 `TodoWrite` real — bind to persistent task store

- **Target**: `lyra_core/tools/todo_write.py` (new) replacing stub +
  `lyra_core/store/todo_store.py` (new)
- **Contract**:
  ```python
  def make_todo_write_tool(*, store: TodoStore) -> Callable
  ```
  Tool takes `merge: bool` and `todos: list[{id, content, status}]`,
  persists atomically via `TodoStore`, returns current list.
- **Test file**: `lyra-core/tests/test_todo_write_tool_contract.py`
- **RED tests (6+)**: schema presence, merge semantics, replace
  semantics, unknown-id error, atomic write verified by kill-mid-write
  simulation, roundtrip across reopen.

### A.5 LSP backend — `multilspy` bridge + `MockLSPBackend`

- **Target**: `lyra_core/lsp_backend/multilspy_backend.py` (new) +
  `lyra_core/lsp_backend/mock.py` (new) + existing
  `lyra_core/tools/lsp.py` wired to the real backend.
- **Contract**: `MultilspyBackend(language: str, repo_root: Path)`
  implements the `LSPBackend` Protocol; raises `FeatureUnavailable`
  when `multilspy` missing.
- **Test file**: `lyra-core/tests/test_lsp_multilspy_backend_contract.py`
  (unit, with `MockLSPBackend`) + `@pytest.mark.smoke`
  `test_lsp_multilspy_python_smoke` that runs pyright against a
  scratch file when `LYRA_RUN_SMOKE=1`.
- **RED tests (4+)**: feature-unavailable error, mock backend returns
  canned diagnostics, tool delegates each op to backend, backend swap
  without code change.

### A.6 Plugin runtime loader — invoke manifest entry points

- **Target**: `lyra_core/plugins/runtime.py` (new)
- **Contract**:
  ```python
  class PluginRuntime:
      def load_from(self, root: Path) -> list[LoadedPlugin]
      def dispatch(self, event: str, ctx: dict) -> list[dict]
  ```
  Uses existing `PluginManifest` + `load_manifest`; resolves
  `entry_point` (`"pkg.mod:callable"`) via `importlib`; never imports
  `entry_point` modules at manifest load time (deferred to first
  dispatch).
- **Test file**: `lyra-core/tests/test_plugin_runtime_contract.py`
- **RED tests (6+)**: discovery walks a dir, lazy import, dispatch
  passes event ctx, exceptions contained per-plugin, manifest errors
  surfaced, `.lyra-plugin` + `.claude-plugin` parity.

### A.7 `DockerBackend` real — docker-py wrapper

- **Target**: `lyra_core/terminal/docker.py` (new) replacing
  `stubs.DockerBackend`; keep the stub registered as a fallback when
  docker isn't importable.
- **Contract**: `DockerBackend(image: str, network: str | None = None,
  volumes: dict | None = None)` implements `TerminalBackend.run(...)`
  via `docker.containers.run(... remove=True, detach=False)`.
- **Test file**: `lyra-core/tests/test_terminal_docker_backend_contract.py`
- **RED tests (5+)**: `FeatureUnavailable` when docker not installed,
  command exit code surfacing, timeout propagation, container cleanup
  on timeout, injection-safe argv handling. Unit tests use a
  `_FakeDockerClient`. Smoke test (`@pytest.mark.smoke`) executes
  `echo hello` in `alpine:3.20` when docker daemon reachable.

### A.8 `WebSearch` + `WebFetch` tools

- **Target**: `lyra_core/tools/web.py` (new)
- **Contract**:
  - `make_websearch_tool(*, http: Callable = httpx.Client) -> Callable`:
    calls DuckDuckGo's HTML endpoint, parses top N results with
    `beautifulsoup4`, returns structured hits.
  - `make_webfetch_tool(*, http, max_bytes: int = 2_000_000, allow_hosts:
    set[str] | None = None) -> Callable`: GET a URL, follow redirects
    within `max_bytes`, return markdown-like text via Readability-style
    extraction (or plain `soup.get_text()` fallback).
- **Test file**: `lyra-core/tests/test_web_tools_contract.py`
- **RED tests (6+)**: `WebSearch` returns structured hits (fake
  response), handles zero results, strips HTML to plain text;
  `WebFetch` respects `max_bytes` cut-off, handles 4xx gracefully,
  respects `allow_hosts` allowlist.

### A.9 Telegram adapter real — httpx + Bot API

- **Target**: `lyra_core/gateway/adapters/telegram.py` (edit — flip
  stub to real)
- **Contract**: `TelegramAdapter(token: str, http: httpx.Client =
  _default)` uses long-polling `getUpdates` and `sendMessage`; stores
  last offset in memory; raises `GatewayError` on 401/403.
- **Test file**: `lyra-core/tests/test_telegram_adapter_real_contract.py`
- **RED tests (6+)**: connect stores base URL + token; `poll` builds
  correct `offset` param; `send` marshals `chat_id` + `text`;
  auth-error raises; idempotent `disconnect`; real-network smoke test
  gated on `LYRA_TELEGRAM_TOKEN`.

### A.10 Cron daemon — background ticker on `CronStore`

- **Target**: `lyra_cli/interactive/cron_daemon.py` (new)
- **Contract**:
  ```python
  class CronDaemon:
      def __init__(self, store: CronStore, runner: Callable[[CronJob], None],
                   clock: Callable[[], datetime] = utcnow): ...
      def tick(self, *, now: datetime | None = None) -> list[str]  # job ids fired
      def run_forever(self, *, interval_s: float = 30.0) -> None     # non-blocking loop
  ```
- **Test file**: `lyra-core/tests/test_cron_daemon_contract.py`
- **RED tests (5+)**: tick fires only due jobs, paused jobs don't fire,
  one-shot jobs de-register after firing, run_forever yields to cancel
  signal, runner exception doesn't poison the loop.

### A.11 FTS5 search real slash UI

- **Target**: `lyra_cli/interactive/fts5_search.py` (new) +
  `session.py` command registration
- **Contract**: `/search <query>` runs BM25 over the existing
  `session_store_sqlite_fts5`, renders top-10 hits with session id +
  timestamp + snippet. Alias `/find`. Does not change the underlying
  store schema.
- **Test file**: `lyra-cli/tests/test_slash_search_fts5.py`
- **RED tests (5+)**: empty query → friendly message; search across
  turns; snippets highlight match; pagination with `--limit`; tombstoned
  sessions excluded.

### A.12 OpenTelemetry exporter on event bus

- **Target**: `lyra_core/observability/otlp.py` (new)
- **Contract**: `OtlpExporter(endpoint: str, service_name: str =
  "lyra") -> Exporter` subscribes to the existing event bus and emits
  one span per tool call + one span per turn; uses
  `opentelemetry-exporter-otlp-proto-grpc` when available;
  `FeatureUnavailable` otherwise.
- **Test file**: `lyra-core/tests/test_otlp_exporter_contract.py`
- **RED tests (5+)**: subscribes to the bus without double-fire,
  tool-call span has `tool.name` + `tool.duration_ms`, error spans
  carry `otel.status_code=ERROR`, exporter closed cleanly on shutdown,
  `FeatureUnavailable` when package missing.

### Phase A risk register

| risk | mitigation |
|---|---|
| `multilspy` fails to start pyright in sandboxed CI | `MockLSPBackend` for unit tests; smoke gated on env var |
| Docker daemon not available | Stub fallback; smoke gated on daemon ping |
| Telegram Bot API flakes | `FakeBotAPI` double for unit tests; no live network call by default |
| OTLP collector not running | In-memory `_SpanBuffer` default; OTLP only when `LYRA_OTLP_ENDPOINT` set |
| `/compact` summariser regression loses context | Two-step: keep raw turns archived side-channel, `/uncompact` rollback for last N turns |
| Plugin runtime loads malicious code | `entry_point` is `importlib`-resolved from a manifest directory; user gets a trust banner; manifest dir sandboxed to repo root |

### Phase A sequencing

1. **Day-1 bundle (fast wins, no deps)**: A.1, A.2, A.3, A.4, A.11, A.12.
2. **Day-2 bundle (opt-in deps)**: A.5, A.6, A.7, A.8, A.9, A.10.

Target test delta: **~65 new RED/GREEN pairs** (12 features × ~5-6
tests each).

---

## 4. Phase B — v1.7.4 "UX Completeness" (10 features)

Enumerated; detailed spec will be written at the start of that pass.

1. `/review` real — wire to existing verifier
2. `/map` real — repo file-symbol map (tree-sitter or ctags)
3. `/blame` real — `git blame` integration with `Read` cross-link
4. `/btw` real — sidecar question with isolated context
5. `/pair` real — `rich.Live` streaming region
6. `/ultrareview` real — multi-agent review wrapper
7. `/vim` real — bind to `prompt_toolkit` vim mode
8. Custom-tool registry real loader (`lyra_core/tools/registry.py`)
9. Subagent presets (Explore / General / Plan) — real via
   `SubagentDefinitions` config file
10. Paste-as-image placeholder → real extraction via `PIL`

**Dependencies**: Phase A items A.3, A.4, A.11 (registry + store + search).

---

## 5. Phase C — v1.8 "Channels + Remote Terminals + MCP" (15 features)

1. Slack adapter (`slack_sdk`)
2. Discord adapter (`discord.py`)
3. Matrix adapter (`matrix-nio`)
4. Email adapter (SMTP + IMAP)
5. SMS adapter (Twilio)
6. Feishu adapter
7. WeCom adapter
8. Mattermost adapter
9. BlueBubbles adapter
10. `ModalBackend` real (`modal` SDK)
11. `SSHBackend` real (`paramiko` / `fabric`)
12. `DaytonaBackend` real (HTTP API)
13. `SingularityBackend` real
14. MCP client (full JSON-RPC stdio)
15. ACP real method registry (`session.start`, `session.message`,
    `tool.execute`, `tool.result`)

**Dependencies**: Phase A A.6 (plugin runtime), A.9 (gateway pattern).

---

## 6. Phase D — v1.9 "Memory + Eval" (10 features)

1. Episodic memory rerank (scoring against outcome labels)
2. Semantic memory store (facts / wiki)
3. Prompt caching (Anthropic caching endpoint)
4. `Title` + `Summary` subagents (async, Haiku-class)
5. Skill auto-extractor (observe trajectories → extract skills)
6. Skill-Creator v2 (4-agent loop)
7. Session replay (not just list — step through events)
8. Red-team corpus + safety monitor
9. Golden eval corpus + `/eval-drift`
10. SWE-bench Pro / LoCoEval adapters

**Dependencies**: Phase A A.11 (FTS5), A.12 (OTLP for eval metrics).

---

## 7. Phase E — v2 "Advanced" (8 features)

1. `Browser` tool (Playwright headless)
2. RL trainer binding (Atropos GRPO + LoRA via Tinker)
3. Meta-harness outer loop (phase 24)
4. Harness arena A/B tournament (phase 25)
5. Federated skill registry (sigstore signing)
6. KLong checkpoint & resume across model generations
7. Multica team orchestration
8. Cost-aware router per turn

**Dependencies**: Phase D (eval corpus), Phase C (MCP client).

---

## 8. Testing strategy (all phases)

- Every new module has a contract test file; files are named
  `test_<feature>_contract.py`.
- Fakes live in the test file, not in `src/` — production code
  ships only real impls + the `FeatureUnavailable` guard.
- Smoke tests are gated by env var (`LYRA_RUN_SMOKE=1`) and by
  availability of the relevant daemon / token; never run in default
  CI.
- Per-phase target: total test count in the suite monotonically
  increases; `pytest -q` from `projects/lyra/` stays 100% green
  (outside `@pytest.mark.smoke`).

## 9. Dependency matrix

| extra | packages | used by |
|---|---|---|
| `lyra[lsp]` | `multilspy>=0.10` | A.5 |
| `lyra[docker]` | `docker>=7.0` | A.7 |
| `lyra[telegram]` | `httpx>=0.26` | A.9 |
| `lyra[otlp]` | `opentelemetry-sdk>=1.25`, `opentelemetry-exporter-otlp>=1.25` | A.12 |
| `lyra[web]` | `httpx>=0.26`, `beautifulsoup4>=4.12` | A.8 |
| `lyra[slack]` | `slack-sdk>=3.27` | C.1 |
| `lyra[discord]` | `discord.py>=2.3` | C.2 |
| `lyra[matrix]` | `matrix-nio>=0.24` | C.3 |
| `lyra[ssh]` | `paramiko>=3.4` | C.11 |
| `lyra[mcp]` | `mcp>=0.1` | C.14 |
| `lyra[browser]` | `playwright>=1.40` | E.1 |
| `lyra[all]` | union | everything |

## 10. Rollback & safety

- Every phase is additive — no feature flag required for rollback;
  deleting the new module + reverting the `session.py` / matrix
  edits cleanly removes it.
- `/compact` keeps raw turns archived; `/uncompact` rollback lands
  alongside the summariser.
- Plugin runtime refuses to load a manifest outside `repo_root` or a
  user-configured plugin root.
- Docker / SSH / remote terminal backends never run on `LocalBackend`
  machines by default — explicit opt-in per session.

## 11. Execution order for this session

Only **Phase A** is executed in this session. Phase B/C/D/E will
each get their own focused spec at the start of that pass.

**Within Phase A**, the execution order is the bundle order in
§3 ("Day-1 bundle" → "Day-2 bundle"), which surfaces the
no-new-deps features first so progress is locked in even if a dep
install fails later.

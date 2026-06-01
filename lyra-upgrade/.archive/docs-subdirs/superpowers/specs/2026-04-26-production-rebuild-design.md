# Production Rebuild — "Lyra v2.1 Claude-Code-Class" Design

**Date**: 2026-04-26
**Supersedes**: none (complements the Wave F roadmap shipped in v2.0.0)
**Owner**: Lyra harness team
**Status**: pending user approval (this spec)
**Approach**: B — in-place refactor with versioned module boundaries
**Reference repos**: `.ui-refs/claw-code` (Rust + rustyline), `.ui-refs/opencode` (Bun TUI)

---

## 1. Why this exists

After Waves B–F shipped 60+ features, the **basic user journey is still broken**:

- `lyra run "say hello"` plans then prints `"Phase 2 CLI currently stops here; execution loop ships in Phase 3"` and exits. The agent loop is **never** invoked from the CLI.
- The interactive REPL hard-defaults to the `mock` provider even when `DEEPSEEK_API_KEY` (or any other key) is set. Users see `Model mock` in the status bar despite a configured provider.
- Lyra's `_extract_plan_block` requires a literal `---\n` at the start of model output. Real-world models (DeepSeek V4, GPT-5, Claude Opus) reply in prose unless the prompt is engineered to enforce the fence — and Lyra's prompt does not.
- There is no first-run / no-config UX. If the user has no provider configured, Lyra silently falls back to `mock` instead of guiding them to connect.
- The flag surface is split: `lyra run --llm`, `lyra --model`. Two names for one concept.
- "Mock" leaks into every user-facing surface (help text, status bar, REPL banner) when it should be a private test fixture.

The user's directive: **"Production-ready best version of Claude Code"**, with first-class support for DeepSeek, OpenAI, Claude (Anthropic), Gemini, and Qwen, and an interactive picker that lets users pick a provider and paste a key without learning env-var names.

This spec rebuilds the CLI surface in place over **eight phases**, each TDD-first and each leaving the test suite green at HEAD. Approach B was approved: refactor in place with versioned module shims that get deleted at the end of the rebuild.

## 2. Invariants (apply to every phase)

1. **TDD-first**. Every phase ships RED → GREEN → REFACTOR. Contract tests land in the same commit as the implementation; pre-implementation HEAD must fail the new tests.
2. **No silent regressions**. The full Wave F regression target (`pytest -q`) must end every phase at the same pass count or higher. Skipped tests must not increase.
3. **No breaking changes for programmatic callers**. `harness_core.LLMProvider`, `lyra_core.plan.run_planner`, `harness_core.AgentLoop.run`, public CLI argument names — all stable. Internal modules can be reorganized freely.
4. **Mock is private**. After Phase 1, `MockLLM` is reachable only from within `harness_core.models` and from test fixtures. It is never returned by `build_llm("auto")`, never in the REPL banner, never in `--llm` help text, never the status-bar default. Tests that depend on it import it directly from `harness_core.models`.
5. **Two-tier secrets**. API keys persist in either `<repo>/.env` (project-local, claw-code-style cwd-walk discovery, already supported) or `~/.lyra/auth.json` (per-user, mode 0600, opencode-style). Picker writes the key to whichever the user selects. Keychain is YAGNI for this rebuild.
6. **Auto-cascade is the default**. Both `lyra run --llm <X>` and `lyra --model <X>` default to `auto`. The existing 13-provider cascade order in `llm_factory.py` is preserved (Anthropic → OpenAI → OpenAI-reasoning → DeepSeek → xAI → Groq → Cerebras → Mistral → OpenRouter → LM Studio → DashScope/Qwen → vLLM → Gemini → Ollama). **Only change: the trailing `mock` fallback is removed and replaced with `raise NoProviderConfigured`.** Users who want a deterministic provider should pick explicitly via `lyra connect` rather than relying on cascade order.
7. **No-provider state is friendly, not silent**. When `auto` resolves to nothing, the REPL opens the provider picker dialog; `lyra run` prints actionable guidance and exits non-zero. Neither path falls back to `mock`.
8. **Phase isolation**. Each phase is independently shippable. After phase N, HEAD is releasable.
9. **Doc surface per phase**. Each phase appends: (a) a `CHANGELOG.md` entry, (b) `feature-parity.md` row updates if relevant, (c) `README.md` updates only if user-visible behavior changes.

## 3. Cross-cutting decisions (locked)

- **Versioning during the rebuild**: This rebuild ships as **v2.1.0 "Claude-Code-Class"**. Each phase increments the patch (`v2.1.0` → `v2.1.7` across the 8 phases). The version bumps in `pyproject.toml` and `__init__.py.__version__` happen in the *first* commit of each phase.
- **Provider taxonomy**: 6 first-class providers (`anthropic`, `openai`, `gemini`, `deepseek`, `qwen`, `ollama`) + 7 secondary (`xai`, `groq`, `cerebras`, `mistral`, `openrouter`, `lmstudio`, `vllm`) + 2 specialized (`openai-reasoning`, `dashscope` as alias for `qwen`). The picker dialog surfaces first-class above the fold and secondary in an "Other providers" expand.
- **API key entry**: Read via `prompt_toolkit`'s prompt with `is_password=True` masking. (Lyra already depends on `prompt_toolkit`.) On confirm, do a lightweight preflight (`GET /v1/models` for OpenAI-compatible, equivalent for Anthropic/Gemini), and only write to disk if the preflight succeeds.
- **Auth file format** (`~/.lyra/auth.json`):
  ```json
  {
    "$schema": "https://lyra.dev/schema/auth.v1.json",
    "version": 1,
    "providers": {
      "deepseek": {"api_key": "sk-...", "model": "deepseek-v4-pro", "added_at": "2026-04-26T13:01:00Z"},
      "anthropic": {"api_key": "sk-ant-...", "model": "claude-opus-4.5"}
    }
  }
  ```
  The file is `chmod 0600` on first write. `lyra connect` is the only writer; the read path is `lyra_core.auth.load()`.
- **Status bar layout** (TTY mode):
  ```
   ◆ repo lyra · mode plan · model deepseek-v4-pro · turn 3 · tok 1.2k · cost $0.0042 · 2 perm · 1 LSP · 0 MCP
  ```
  When non-TTY, fall back to the existing plain-text status line.
- **First-run trigger logic**: REPL opens `DialogProviderList` iff `(auth.json absent OR has zero entries) AND no env-var-based provider is reachable AND --model not explicitly set on the command line`.
- **Slash command compatibility**: every existing slash continues to work (no renames, no removals). New slashes added: `/connect`, `/auth`, `/qwen`, `/claude`, `/gpt`, `/deepseek`, `/gemini` (the last six are convenience shortcuts that switch provider+model in one keystroke).

---

## 4. Phase 1 — Foundation (`v2.1.0`)

**Goal**: Wire the agent loop into `lyra run`. Default both `--llm` and `--model` to `auto`. Make `describe_selection()` the single source of truth for the status bar. Remove `mock` from the auto-cascade fallback.

### 4.1 Files

| Action | File | Purpose |
|---|---|---|
| Modify | `packages/lyra-cli/src/lyra_cli/commands/run.py` | After plan approval (or `--no-plan`), instantiate the harness loop and execute |
| Modify | `packages/lyra-cli/src/lyra_cli/__main__.py` | Default `--model` to `"auto"` (was `"mock"`) |
| Modify | `packages/lyra-cli/src/lyra_cli/llm_factory.py` | Remove `mock` from auto cascade; raise `NoProviderConfigured` instead of falling back |
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/session.py` | Default `model` field on `InteractiveSession` to `"auto"` (was `"mock"`); resolve at boot via `describe_selection()` |
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/store.py` | Update persisted-state default from `"mock"` to `"auto"` |
| Create | `packages/lyra-cli/tests/test_run_executes_agent_loop.py` | Contract: `lyra run --no-plan --llm <fake>` actually invokes `AgentLoop.run` |
| Create | `packages/lyra-cli/tests/test_repl_default_is_auto.py` | Contract: REPL with no args resolves real provider via auto, never shows `mock` when a key is configured |
| Create | `packages/lyra-cli/tests/test_no_provider_friendly_error.py` | Contract: `lyra run --llm auto` with zero env keys + no auth.json prints "no provider configured" and exits 2 |
| Modify | ~12 existing tests that hard-code `model="mock"` as the REPL default | Update to either set the model explicitly or assert against `"auto"` |

### 4.2 Contract: `run_command` after Phase 1

```python
def run_command(
    task: str,
    repo_root: Path = Path.cwd(),
    no_plan: bool = False,
    auto_approve: bool = False,
    llm: str = "auto",   # was "auto" already; doc clarification only
    max_steps: int = 25,  # NEW — caps the agent loop
) -> None:
    """Run a task end-to-end through the harness loop.
    
    Plan-then-execute when Plan Mode is enabled (default); execute-only
    when --no-plan. Always invokes the harness AgentLoop after plan
    approval.
    """
```

After plan approval (or skip), the new code path is (verified against `projects/orion-code/harness_core/src/harness_core/loop.py:39-75`, where `AgentLoop.run(task, initial_messages=None) -> LoopResult` already exists):

```python
from harness_core.loop import AgentLoop
from harness_core.tools import ToolRegistry
from harness_core.tracer import NoopTracer  # or wire OTel from lyra_core.otel
from lyra_core.tools import register_builtin_tools

tools = ToolRegistry()
register_builtin_tools(tools, repo_root=repo_root)
provider = build_llm(llm, task_hint=task, session_id=session_id)
loop = AgentLoop(
    llm=provider,
    tools=tools,
    max_steps=max_steps,
    tracer=NoopTracer(),
)
result = loop.run(task=task)
_render_run_result(result, console=_console)
raise typer.Exit(code=0 if result.completed else 1)
```

### 4.3 Contract: `build_llm("auto")` after Phase 1

- Cascade order unchanged for the configured providers.
- **Final step removed**: no `_build_mock(...)` fallback at line 417.
- Replace with: `raise NoProviderConfigured("no provider configured. Run \`lyra connect\` to add one.")`
- `build_llm("mock")` still works (explicit opt-in for tests).

### 4.4 Test plan

```python
# test_run_executes_agent_loop.py — RED, then GREEN
def test_lyra_run_invokes_agent_loop_after_no_plan(tmp_path, fake_llm):
    """`lyra run --no-plan` must call AgentLoop.run, not exit early."""
    result = runner.invoke(app, ["run", "--no-plan", "--llm", "fake", "say hi"])
    assert fake_llm.generate_calls == 1
    assert result.exit_code == 0

def test_lyra_run_invokes_agent_loop_after_plan_approval(tmp_path, fake_llm_plan_then_exec):
    result = runner.invoke(app, ["run", "--auto-approve", "--llm", "fake", "do thing"])
    assert fake_llm_plan_then_exec.plan_calls == 1
    assert fake_llm_plan_then_exec.exec_calls >= 1
    assert result.exit_code == 0

# test_repl_default_is_auto.py — RED, then GREEN
def test_repl_with_anthropic_key_shows_anthropic(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr("anthropic.Anthropic", FakeAnthropic)
    result = runner.invoke(app, [], input=":exit\n")
    assert "anthropic" in result.output
    assert "mock" not in result.output

# test_no_provider_friendly_error.py — RED, then GREEN
def test_no_provider_no_keys_no_authfile(monkeypatch, tmp_path):
    for var in PROVIDER_KEY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("lyra_core.auth.AUTH_FILE", tmp_path / "absent.json")
    result = runner.invoke(app, ["run", "--llm", "auto", "task"])
    assert result.exit_code == 2
    assert "no provider configured" in result.output
    assert "lyra connect" in result.output
```

### 4.5 Risk + mitigation

- **Risk**: tests that build a transient `InteractiveSession(model="mock", ...)` may break. **Mitigation**: keep `model="mock"` accepted as an explicit value; only the *default* changes. Bulk-update the ~12 tests that depended on the default.
- **Risk**: `AgentLoop.run` may not exist with the exact signature assumed. **Mitigation**: read `harness_core/loop.py:75` first (we already saw the call site exists) and adapt.

## 5. Phase 2 — Provider Registry v2 + Qwen first-class (`v2.1.1`)

**Goal**: Promote Qwen to a first-class name; add per-provider preflight; produce friendly diagnostics on auth failures.

### 5.1 Files

| Action | File | Purpose |
|---|---|---|
| Modify | `packages/lyra-cli/src/lyra_cli/providers/openai_compatible.py` | Add `qwen` preset (alias of `dashscope`); set `default_model="qwen-plus"` |
| Modify | `packages/lyra-cli/src/lyra_cli/llm_factory.py` | Add `qwen` to known names + auto cascade (after DeepSeek, before xAI) |
| Create | `packages/lyra-core/src/lyra_core/auth/preflight.py` | `preflight(provider, api_key) -> PreflightResult` |
| Create | `packages/lyra-core/src/lyra_core/auth/diagnostics.py` | Translate HTTP 401/403/429/500 → human-friendly error strings |
| Create | `packages/lyra-cli/tests/test_qwen_first_class.py` | Contract: `--llm qwen` resolves; `qwen` appears in `lyra connect` listing |
| Create | `packages/lyra-core/tests/test_preflight_contract.py` | Contract: preflight against fake server; 200 → ok, 401 → bad-key, 429 → rate-limited |

### 5.2 Contract: `preflight`

```python
@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    provider: str
    detail: str   # human readable, single line
    model_count: int | None  # None if endpoint doesn't list models

def preflight(provider: str, api_key: str, *, timeout: float = 5.0) -> PreflightResult:
    """Cheap auth check. Calls /v1/models for OpenAI-compatible,
    /v1/messages with empty body for Anthropic, equivalent for Gemini.
    Returns ok=True iff the call returned 200 (or 400 with a recognizable
    'no input' shape, which still proves auth worked)."""
```

### 5.3 First-class providers (final)

```python
FIRST_CLASS = ("anthropic", "openai", "gemini", "deepseek", "qwen", "ollama")
```

Picker shows these above the fold. `qwen` resolves to the `dashscope` preset (Alibaba's OpenAI-compatible endpoint serving Qwen + Kimi). `dashscope` remains as an alias.

## 6. Phase 3 — Connect Flow + Picker Dialog (`v2.1.2`)

**Goal**: `lyra connect [provider]` subcommand, `/connect` slash, auto-trigger when no provider configured. Opencode-style picker rendered with Rich panels.

### 6.1 Files

| Action | File | Purpose |
|---|---|---|
| Create | `packages/lyra-cli/src/lyra_cli/commands/connect.py` | `connect_command` Typer subcommand |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/dialog_provider.py` | Rich-Panel-rendered provider picker |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/dialog_apikey.py` | Masked API key prompt + preflight |
| Create | `packages/lyra-core/src/lyra_core/auth/store.py` | `load() / save() / list_providers()` for `~/.lyra/auth.json` |
| Modify | `packages/lyra-cli/src/lyra_cli/__main__.py` | Register `connect` subcommand |
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/session.py` | Add `_cmd_connect`; trigger picker on REPL start when no provider |
| Modify | `packages/lyra-cli/src/lyra_cli/llm_factory.py` | Read keys from `auth.json` as a fallback when env-vars empty |
| Create | `packages/lyra-cli/tests/test_connect_command.py` | Contract: `lyra connect deepseek` writes auth.json with the key |
| Create | `packages/lyra-cli/tests/test_dialog_provider.py` | Contract: dialog state machine (select → key entry → preflight → persist) |
| Create | `packages/lyra-core/tests/test_auth_store.py` | Contract: load/save/list, mode 0600 enforcement |

### 6.2 Connect flow (state machine)

```
START
  ├─ list providers (FIRST_CLASS above fold, others in "More providers")
  ├─ user picks → fetch preset metadata
  ├─ already authenticated? → ask "replace existing key? [y/N]"
  ├─ prompt for API key (masked)
  ├─ preflight → on fail: show diagnostic, offer retry / abort
  ├─ ask "save where?" → .env (project) | ~/.lyra/auth.json (user) | both
  ├─ on save: chmod 0600 if writing user-global
  └─ DONE → status: "anthropic · claude-opus-4.5 · ready"
```

### 6.3 Contract: `connect_command`

```python
def connect_command(
    provider: str | None = typer.Argument(None, help="Provider to connect (anthropic, openai, deepseek, qwen, …). If omitted, opens picker."),
    target: str = typer.Option("auto", "--target", help="Where to save: env, user, both, auto"),
    no_preflight: bool = typer.Option(False, help="Skip preflight (e.g. for offline setup)"),
) -> None:
    """Connect a provider — interactive."""
```

### 6.4 Auto-trigger logic in REPL

The function lives in `packages/lyra-cli/src/lyra_cli/interactive/driver.py` and is called from `run()` after the banner prints and before the prompt loop starts.

```python
def _maybe_open_connect_dialog(session: InteractiveSession, console: Console) -> None:
    """Open the provider picker on first run iff:
      - stdout is a TTY (we have UI to render), AND
      - the user didn't pass --model explicitly (session.model == 'auto'), AND
      - the auto-cascade resolves to nothing (no env keys + no auth.json entry)

    Blocking. On dialog completion, the user has either configured a provider
    (auth.json updated) or cancelled (session continues with model='auto'
    which will surface NoProviderConfigured on first agent call).
    """
    import sys
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return
    if session.model != "auto":
        return
    from lyra_core.auth.store import has_any_provider as _has_any_provider
    from lyra_cli.llm_factory import describe_selection
    if _has_any_provider() or describe_selection("auto") != "no provider":
        return
    from .dialog_provider import DialogProviderList
    DialogProviderList(console=console).run()
```

## 7. Phase 4 — Planner Robustness (`v2.1.3`)

**Goal**: Make `_extract_plan_block` tolerant. Strengthen the planner system prompt. Add prose-fallback synthesis.

### 7.1 Files

| Action | File | Purpose |
|---|---|---|
| Modify | `packages/lyra-core/src/lyra_core/plan/artifact.py` | Tolerant `_extract_plan_block`: search for fence anywhere, accept code-fenced YAML, accept fence-less response by synthesizing |
| Modify | `packages/lyra-core/src/lyra_core/plan/planner.py:32` | Strengthen `_PLANNER_SYSTEM_PROMPT`: explicit format example + "wrap your plan in `---` frontmatter" rule + structured-output flag for providers that support it |
| Create | `packages/lyra-core/src/lyra_core/plan/fallback_synth.py` | `synthesize_plan_from_prose(prose, task) -> Plan` — best-effort recovery |
| Create | `packages/lyra-core/tests/test_planner_tolerant_parser.py` | Contract: 8 forms of model output (fenced, code-fence, prose-prefix, missing-end-fence, …) all parse |
| Create | `packages/lyra-core/tests/test_planner_prose_fallback.py` | Contract: pure-prose response → minimal valid Plan with title from `task` |

### 7.2 Tolerance matrix (must all parse to a valid Plan)

| Input shape | Resolution |
|---|---|
| `---\nfm: x\n---\n# Plan: ...` (current contract) | Parse as today |
| `Some intro text.\n\n---\nfm: x\n---\n# Plan: ...` | Strip prose prefix, parse |
| ` ```yaml\nfm: x\n```\n# Plan: ...` | Treat code-fenced YAML as frontmatter |
| `# Plan: title\n## Acceptance tests\n- ...` (no frontmatter at all) | Synthesize empty frontmatter from defaults; parse rest |
| `Here is a plan: ...` (pure prose) | Synthesize minimal Plan with title from task and one feature item |
| `{"plan": {...}}` (JSON) | Detect JSON, transform to Plan via `Plan.from_json` |

### 7.3 Strengthened planner prompt skeleton

```
You are Lyra's planner. Output exactly one Markdown plan artifact wrapped
in YAML frontmatter. The first three characters of your response MUST be
"---" followed by a newline. Do not include any prose before the frontmatter.

Schema:
---
session_id: {{ session_id }}
created_at: {{ iso8601_now }}
planner_model: {{ model }}
estimated_cost_usd: <float>
goal_hash: {{ goal_hash }}
---

# Plan: <one-line title>

## Acceptance tests
- <pytest -k expression or test path>

## Expected files
- <relative path>

## Forbidden files
- <relative path>

## Feature items
1. **(skill_name)** description

## Open questions
## Notes
```

## 8. Phase 5 — Status Bar v2 + Banner (`v2.1.4`)

**Goal**: Adopt opencode's footer layout. Align Lyra's banner with claw-code's "Model / Permissions / Branch / Workspace / Directory / Session / Auto-save" block.

### 8.1 Files

| Action | File | Purpose |
|---|---|---|
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/banner.py` | Banner: ASCII Lyra logo + 7-field metadata block (claw-code style) |
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/status_source.py` | Add `permissions`, `lsp_count`, `mcp_count`, `cost_usd` fields |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/status_bar.py` | New v2 footer renderer (Rich) |
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/driver.py` | Replace existing status line with v2 renderer; preserve text fallback |
| Create | `packages/lyra-cli/tests/test_status_bar_v2.py` | Contract: each field renders; ANSI passthrough disabled in non-TTY |

### 8.2 Footer field schema

```
left:  cwd-relative path  (truncated middle if >60 cols)
right: △ N perms · ✦ N LSP · ⊙ N MCP · ◆ <model> · <mode> · t<turn> · <tokens> · $<cost>
```

Empty fields collapse rather than render as zero (so a fresh session shows just `cwd · ◆ deepseek-v4-pro · plan` initially).

## 9. Phase 6 — Tool-Call Rendering v2 (`v2.1.5`)

**Goal**: Per-tool renderers (Bash/Read/Write/Edit/Search/Shell). Collapse-on-success. Detail toggle. Approval prompt copy aligned with claw-code's.

### 9.1 Files

| Action | File | Purpose |
|---|---|---|
| Create | `packages/lyra-cli/src/lyra_cli/interactive/tool_renderers/__init__.py` | Renderer registry |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/tool_renderers/bash.py` | `render(tool_call) -> Renderable` for `bash` / `shell` |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/tool_renderers/file.py` | Renderers for `read_file`, `write_file`, `edit_file` |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/tool_renderers/search.py` | Renderers for `grep`, `glob` |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/tool_renderers/generic.py` | Fallback for unknown tools |
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/tool_card.py` | Use registry; existing inline renderer becomes `generic.py` |
| Create | `packages/lyra-cli/tests/test_tool_renderers.py` | Contract: each renderer produces stable text + Rich output |

### 9.2 Approval prompt copy (claw-code-aligned)

```
Permission approval required
  Tool             write_file
  Mode             workspace-write
  Reason           planner step 3 — create src/foo.py
  Input            {"path": "src/foo.py", "content": "<...>"}

Approve this tool call? [y/N]: 
```

`/permissions normal` (default), `strict` (always prompt, even read), `yolo` (never prompt) controlled via existing `permission_mode` field.

## 10. Phase 7 — Command Palette v2 (`v2.1.6`)

**Goal**: Slash command registry-of-records. Categories. Keybind palette (Ctrl+K) modeled on opencode. Backward-compatible.

### 10.1 Files

| Action | File | Purpose |
|---|---|---|
| Create | `packages/lyra-cli/src/lyra_cli/interactive/command_registry.py` | `CommandSpec` dataclass + `REGISTRY` constant |
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/session.py` | `dispatch()` consults registry; existing `COMMAND_REGISTRY` becomes a view over it |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/dialog_command.py` | Ctrl+K palette UI |
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/keybinds.py` | Bind Ctrl+K to palette |
| Create | `packages/lyra-cli/tests/test_command_registry.py` | Contract: every existing slash is registered; categories present; aliases work |

### 10.2 `CommandSpec` shape

```python
@dataclass(frozen=True)
class CommandSpec:
    name: str
    aliases: tuple[str, ...]
    summary: str
    category: str  # "agent" | "session" | "model" | "config" | "debug" | "ux" | "git"
    handler: Callable[[InteractiveSession, str], CommandResult]
    argument_hint: str | None = None
    keybind: str | None = None
    visible_in_palette: bool = True
```

### 10.3 Categories (initial assignment of existing 50+ slashes)

- **agent**: `/agents`, `/sub`, `/spawn`, `/observe`, `/handoff`
- **session**: `/sessions`, `/resume`, `/new`, `/clear`, `/rewind`, `/undo`, `/redo`, `/save`, `/export`, `/import`, `/share`, `/copy`, `/history`, `/timeline`, `/fork`
- **model**: `/model`, `/models`, `/connect`, `/auth`, `/qwen`, `/claude`, `/gpt`, `/deepseek`, `/gemini`
- **config**: `/config`, `/theme`, `/keybinds`, `/skin`, `/policy`, `/permissions`, `/skills`, `/soul`
- **debug**: `/doctor`, `/status`, `/cost`, `/usage`, `/stats`, `/trace`, `/blame`, `/debug-tool-call`
- **ux**: `/help`, `/exit`, `/quit`, `/q`, `/effort`, `/fast`, `/voice`, `/vim`, `/pair`, `/btw`, `/split`, `/vote`, `/ide`, `/catch-up`
- **git**: `/diff`, `/commit`, `/pr`, `/branch`
- **mode**: `/plan`, `/build`, `/run`, `/explore`, `/retro`, `/approve`, `/reject`, `/tdd-gate`, `/review`, `/phase`

## 11. Phase 8 — Onboarding + Welcome (`v2.1.7`)

**Goal**: First-run wizard. Welcome screen with rotating placeholders. Friendly no-provider error with actionable guidance.

### 11.1 Files

| Action | File | Purpose |
|---|---|---|
| Modify | `packages/lyra-cli/src/lyra_cli/interactive/banner.py` | If first-run AND no auth, show "Welcome to Lyra" with `/connect` hint |
| Create | `packages/lyra-cli/src/lyra_cli/interactive/welcome.py` | First-run UX: explain SOUL.md, Plan Mode, slash basics; offer to run `/connect` immediately |
| Modify | `packages/lyra-cli/src/lyra_cli/commands/run.py` | On `NoProviderConfigured`: print actionable guidance pointing to `lyra connect` |
| Create | `packages/lyra-cli/tests/test_first_run_welcome.py` | Contract: fresh tmp_home → welcome shown → `/connect` available |

### 11.2 First-run welcome content

```
╭─ Welcome to Lyra ────────────────────────────────────────────────╮
│                                                                  │
│  You're running Lyra for the first time in this directory.       │
│                                                                  │
│  To get started:                                                 │
│    • /connect    — pick a provider and add your API key          │
│    • /help       — see all slash commands                        │
│    • /soul       — explain how Lyra reads SOUL.md                │
│                                                                  │
│  Or just type your task and Lyra will guide you the rest of      │
│  the way.                                                        │
│                                                                  │
╰──────────────────────────────────────────────────────────────────╯
```

### 11.3 Rotating placeholders (opencode-style, in the prompt input)

Cycled every 4 seconds when the prompt is empty:

```python
PLACEHOLDERS = [
    "fix a TODO in this codebase",
    "add tests for the auth module",
    "explain what this file does",
    "find and fix the most likely cause of the failing test",
    "draft a release-notes section for the latest changes",
    "refactor this function to be more testable",
]
```

---

## 12. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `AgentLoop.run` signature differs from what Phase 1 assumes | Medium | Read `harness_core/loop.py` first; adapt the wiring; if signature is incompatible, add a thin adapter rather than refactoring `harness_core` |
| Test count drops below 1530 due to mock-default removal | High initially | Phase 1 explicitly fixes the dependent tests as part of its scope; track count after each phase |
| Picker dialog fights with prompt_toolkit's session | Medium | Use `prompt_toolkit.shortcuts.input_dialog` patterns we already use elsewhere; add a non-TTY fallback that takes flags (`lyra connect deepseek --key sk-...`) |
| Auth file becomes a key-leak surface | Medium | Mode 0600 enforced on every write; add a `lyra connect --revoke <provider>` to clear; never log the key |
| Planner tolerance hides real prompt-engineering bugs | Low | Emit a `planner.format_drift` HIR event when fallback synthesis kicks in; surface in `lyra doctor` |
| Rebuild ships 2.1.x patches that break user .lyra/sessions/ on disk | Low | All disk schemas are versioned (`version: 1`); migrations are explicit |

## 13. Out of scope (deliberate)

- Streaming UI for tool output (the harness loop returns batched results today; streaming is a separate vertical slice).
- Multi-provider parallel inference (vote/refute already exists in Wave F; not reworked here).
- Web UI / desktop app (opencode has these; Lyra remains CLI-first).
- macOS Keychain integration for auth storage.
- Real-time collaboration / multi-user sessions.

## 14. Success criteria

- [ ] `lyra run "say hello world"` with `DEEPSEEK_API_KEY` set produces a real DeepSeek response and exits 0.
- [ ] `lyra` (REPL) with `DEEPSEEK_API_KEY` set shows `Model deepseek-v4-pro` (or whatever `DEEPSEEK_MODEL` resolves to) in the status bar — never `mock`.
- [ ] `lyra` with no providers configured opens the picker dialog automatically.
- [ ] `lyra connect deepseek` walks user through paste → preflight → save → "ready".
- [ ] `lyra connect qwen` Just Works (Qwen is first-class, not buried in DashScope).
- [ ] `MockLLM` does not appear in `--llm` `--help`, the status bar, the banner, the connect dialog, or the auto cascade.
- [ ] `pytest -q` passes with ≥1530 tests, 0 failed, ≤2 skipped — same baseline as Wave F end-of-day.
- [ ] Planner tolerates 6 representative DeepSeek/V4-Pro/Claude/Gemini outputs from a recorded fixture.

---

## Appendix A — File touch summary across all 8 phases

```
packages/lyra-cli/src/lyra_cli/
├── __main__.py                                  [modify, P1]
├── commands/
│   ├── connect.py                               [create, P3]
│   ├── run.py                                   [modify, P1, P8]
│   └── doctor.py                                [modify, P2]
├── interactive/
│   ├── banner.py                                [modify, P5, P8]
│   ├── command_registry.py                      [create, P7]
│   ├── dialog_apikey.py                         [create, P3]
│   ├── dialog_command.py                        [create, P7]
│   ├── dialog_provider.py                       [create, P3]
│   ├── driver.py                                [modify, P1, P5]
│   ├── keybinds.py                              [modify, P7]
│   ├── session.py                               [modify, P1, P3, P7]
│   ├── status_bar.py                            [create, P5]
│   ├── status_source.py                         [modify, P5]
│   ├── store.py                                 [modify, P1]
│   ├── tool_card.py                             [modify, P6]
│   ├── tool_renderers/                          [create, P6]
│   │   ├── __init__.py
│   │   ├── bash.py
│   │   ├── file.py
│   │   ├── generic.py
│   │   └── search.py
│   └── welcome.py                               [create, P8]
├── llm_factory.py                               [modify, P1, P2, P3]
└── providers/
    └── openai_compatible.py                     [modify, P2]

packages/lyra-core/src/lyra_core/
├── auth/                                        [create, P2-P3]
│   ├── __init__.py
│   ├── diagnostics.py
│   ├── preflight.py
│   └── store.py
├── plan/
│   ├── artifact.py                              [modify, P4]
│   ├── fallback_synth.py                        [create, P4]
│   └── planner.py                               [modify, P4 — _PLANNER_SYSTEM_PROMPT at line 32]
└── ...

packages/lyra-cli/tests/
├── test_command_registry.py                     [create, P7]
├── test_connect_command.py                      [create, P3]
├── test_dialog_provider.py                      [create, P3]
├── test_first_run_welcome.py                    [create, P8]
├── test_no_provider_friendly_error.py           [create, P1]
├── test_qwen_first_class.py                     [create, P2]
├── test_repl_default_is_auto.py                 [create, P1]
├── test_run_executes_agent_loop.py              [create, P1]
├── test_status_bar_v2.py                        [create, P5]
└── test_tool_renderers.py                       [create, P6]

packages/lyra-core/tests/
├── test_auth_store.py                           [create, P3]
├── test_planner_prose_fallback.py               [create, P4]
├── test_planner_tolerant_parser.py              [create, P4]
└── test_preflight_contract.py                   [create, P2]

CHANGELOG.md                                     [modify, P1-P8]
docs/feature-parity.md                           [modify, P1, P3, P8]
README.md                                        [modify, P3, P8]
projects/lyra/pyproject.toml                     [modify, P1, P8] (version bumps)
```

**Total**: ~12 files modified, ~22 files created, ~14 contract test files added. Roughly 50 files touched across 8 phases.

---

*End of design spec.*

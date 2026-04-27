# lyra-core

The kernel of **Lyra** — provider-agnostic, no-Typer, no-REPL. Every
seam that the CLI, MCP server, evals harness, or external embedders
need to share lives here. Current as of **v3.0.0** (2026-04-27).

`lyra-core` extends `harness-core` with:

* the **`AgentLoop`** orchestrator (plan → tools → verify);
* an **opt-in TDD plugin** (the state machine `IDLE → PLAN → RED →
  GREEN → REFACTOR → SHIP`, the `tdd-gate` PreToolUse / Stop hook,
  and the RED-proof validator) — shipped but disabled by default in
  v3.0.0 to match `claw-code`, `opencode`, and `hermes-agent`;
* general-purpose **permission modes** (`plan` / `auto-edit` /
  `bypass-perms`) and the shipped hooks (`secrets-scan`,
  `destructive-pattern`, plus the optional `tdd-gate`);
* native **coding tools**: `Read`, `Glob`, `Grep`, `Edit`, `Write`,
  `Run`, `Patch` — all driven by a single `ToolKernel`;
* the **HIR (Harness IR) event emitter** writing JSONL to
  `.lyra/sessions/events.jsonl` (the source of truth every other
  package replays from);
* the **`LifecycleBus`** — fan-out for `chat.*`, `tool.*`, `plan.*`,
  `subagent.*`, `cron.*` events, with an optional OpenTelemetry
  collector mirror (`LYRA_OTEL_COLLECTOR=in-memory|otel`);
* the **`AliasRegistry`** — single source of truth for model name
  resolution.

See `../../docs/blocks/` for the full per-feature specifications and
`../../docs/architecture.md` for the topology.

## What's in here

```
src/lyra_core/
    agent_loop.py           # the plan→tools→verify orchestrator (provider-agnostic)
    state_machine.py        # IDLE → PLAN → RED → GREEN → REFACTOR → SHIP
    permissions.py          # plan / auto-edit / bypass-perms + hook engine
    tools/                  # Read, Glob, Grep, Edit, Write, Run, Patch, ...
    kernel.py               # ToolKernel — registry + dispatch + audit log
    hir/                    # Harness IR (events.jsonl writer + replayer)
    lifecycle.py            # LifecycleBus + opt-in OTel mirror
    providers/              # alias registry, capability metadata, dotenv loader,
                            #   preflight, auth hints — *no* provider clients
                            #   (those live in lyra-cli/providers/)
    subagents/              # SubagentRegistry + SubagentRunner contract
    plan/                   # Plan / PlanStep / PlannerProtocol
    review/                 # diff reviewer + verifier hooks
    memory/                 # recall window builder
    skills/                 # SKILL.md parser + injector
```

The deliberate split with `lyra-cli`:

* **`lyra-core`** owns *contracts* — interfaces, dataclasses, the
  state machine, the kernel — plus all functionality that does not
  reach out to the network.
* **`lyra-cli`** owns *implementations* — every provider client, the
  Typer surface, the REPL, all I/O channels — and depends on
  `lyra-core`.

This is what lets the same kernel power `lyra-mcp`, `lyra-evals`,
external CI runners, and any future SDK without dragging the entire
provider catalogue along.

## Alias registry — the single source of truth for model names

`lyra_core.providers.aliases.AliasRegistry` (and the module-level
`DEFAULT_ALIASES`) maps user-facing aliases to canonical API slugs
**and** the provider key responsible for them. Both `lyra-cli` (in
`build_llm`) and `lyra-core`'s subagent runner use the same registry,
so a slug typed in `--model`, `/model`, `~/.lyra/settings.json`, or
even an MCP `model` field always resolves the same way.

The registry is seeded with:

| Family        | User-facing aliases                                     | Resolves to                                                | Provider     |
|---------------|---------------------------------------------------------|------------------------------------------------------------|--------------|
| Anthropic     | `opus`, `sonnet`, `haiku` + canonical slugs             | `claude-opus-4.5` / `claude-sonnet-4.5` / `claude-haiku-4` | `anthropic`  |
| xAI Grok      | `grok`, `grok-mini`, `grok-3`, `grok-2`                 | `grok-4` / `grok-4-mini` / etc.                             | `xai`        |
| Moonshot Kimi | `kimi`, `kimi-k2.5`, `kimi-k1.5`                        | `kimi-k2.5` / `kimi-k1.5`                                  | `dashscope`  |
| Qwen          | `qwen-max`, `qwen-plus`, `qwen-turbo`, `qwen3-coder`    | identity                                                   | `dashscope`  |
| Llama (Groq)  | `llama-3.3`, `llama-3.3-70b`                            | `llama-3.3-70b-versatile`                                  | `groq`       |
| **DeepSeek (v2.7.1)** | `deepseek-v4-flash`, `deepseek-flash`, `deepseek-chat`, `deepseek-coder` | `deepseek-chat` (DeepSeek's general/V3.x model) | `deepseek` |
| **DeepSeek (v2.7.1)** | `deepseek-v4-pro`, `deepseek-pro`, `deepseek-reasoner` | `deepseek-reasoner` (DeepSeek's R1 chain-of-thought model) | `deepseek` |

The DeepSeek block backs Lyra's default **fast/smart split** — the
CLI defaults `fast_model = "deepseek-v4-flash"` and
`smart_model = "deepseek-v4-pro"`, and the role-based router in
`lyra-cli/interactive/session.py` resolves them through this registry
before each LLM call.

Public surface:

```python
from lyra_core.providers.aliases import DEFAULT_ALIASES, AliasRegistry

DEFAULT_ALIASES.resolve("deepseek-v4-pro")        # → "deepseek-reasoner"
DEFAULT_ALIASES.provider_for("deepseek-v4-pro")   # → "deepseek"
DEFAULT_ALIASES.resolve("unknown-model")          # → "unknown-model" (passthrough)

# Tests can build their own:
reg = AliasRegistry()
reg.register("local-test", "qwen2.5-coder-7b-instruct", provider="ollama")
```

`provider_for` returning `None` is a meaningful signal — it lets
`build_llm`'s cascade keep cycling through providers when the user
typed a generic slug; only when the registry is confident about the
backend does it short-circuit.

## ProviderSpec — capability metadata

`lyra_core.providers.PROVIDER_REGISTRY` is a separate
**capability-only** registry (not network code) that the planner and
the model picker consult to answer "does this backend support
reasoning mode? tools? what's its context window?". It mirrors
hermes-agent's `CANONICAL_PROVIDERS` shape:

```python
from lyra_core.providers import PROVIDER_REGISTRY, providers_by_capability

PROVIDER_REGISTRY["deepseek"].supports_reasoning   # → True (deepseek-reasoner)
PROVIDER_REGISTRY["deepseek"].context_window       # → 128_000
providers_by_capability(supports_tools=True)       # → ["anthropic", "openai", ...]
```

## AgentLoop — the orchestrator

```python
from lyra_core.agent_loop import AgentLoop
from lyra_core.kernel import ToolKernel
from lyra_core.permissions import PermissionMode

loop = AgentLoop(
    llm=my_llm_provider,                 # any object exposing .generate / .stream
    kernel=ToolKernel.with_default_tools(),
    permissions=PermissionMode.PLAN,     # plan-gated by default
    repo_root=Path.cwd(),
)
final = loop.run("ship tests for X")
```

`AgentLoop` is provider-agnostic — `lyra-cli`'s
`_LyraCoreLLMAdapter` (Message-in / dict-out shape) is the one
adapter that bridges the CLI's `LLMProvider` interface to the kernel.

## Testing

```bash
# from projects/lyra/packages/lyra-core/
uv run pytest -q             # 796 tests in v3.0.0
```

The contract tests live in `tests/`; the most load-bearing files are
`test_agent_loop_*.py`, `test_state_machine.py`, `test_kernel.py`,
`test_aliases.py`, `test_lifecycle_bus.py`, and
`test_providers_registry.py`.

## See also

* [`projects/lyra/README.md`](../../README.md)
* [`projects/lyra/docs/blocks/`](../../docs/blocks/) — per-feature design.
* [`projects/lyra/CHANGELOG.md`](../../CHANGELOG.md)

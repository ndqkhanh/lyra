# LYRA — v3.10 Model Provider Extension Plan

> **Living-knowledge supplement to Lyra's roadmap.** Adds phases
> **L310-1 through L310-9** that turn Lyra's already-mature provider
> abstraction into a *user-extensible plugin system*: any user (not
> just a Lyra contributor) can add a new model provider — DeepSeek
> direct, Moonshot/Kimi K2 direct (not via Groq), Z.ai GLM, Together AI,
> Fireworks AI, DeepInfra, custom on-prem endpoints, anything OpenAI-
> compatible — in **minutes, not days**, via CLI, config file, or pip-
> installable plugin. Capabilities auto-discovered; health-checked;
> fallback-chained; cost-aware routed.
>
> Read alongside [`LYRA_V3_7_CLAUDE_CODE_PARITY_PLAN.md`](LYRA_V3_7_CLAUDE_CODE_PARITY_PLAN.md),
> [`LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md`](LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md),
> [`LYRA_V3_9_RECURSIVE_CURATOR_PLAN.md`](LYRA_V3_9_RECURSIVE_CURATOR_PLAN.md) and
> [`CHANGELOG.md`](CHANGELOG.md).

---

## §0 — Why this supplement

**Surprising finding from the exploration.** Lyra's provider abstraction is *already mature*:

- Canonical `LLMProvider` Protocol (in `harness_core`); 13 providers shipped (`anthropic`, `openai`, `openai-reasoning`, `gemini`, `deepseek`, `xai`, `groq`, `cerebras`, `mistral`, `openrouter`, `lmstudio`, `ollama`, `mock`).
- `OpenAICompatibleLLM` base class with **15 presets** in `packages/lyra-cli/src/lyra_cli/providers/openai_compatible.py` covering DeepSeek, Groq (which hosts Kimi K2 + Qwen-3-*), xAI, Cerebras, Mistral, OpenRouter, etc.
- Two-tier `fast_model` / `smart_model` slots (defaults: `deepseek-v4-flash` / `deepseek-v4-pro`).
- Capability-aware `ProviderSpec` registry with `supports_tools`, `supports_reasoning`, `supports_vision`, `supports_streaming`, `context_window`, `models`.
- Provider-routing config in `~/.lyra/settings.json` for meta-providers (OpenRouter sort/only/ignore/order).
- Confidence-Cascade Router in `lyra-core/routing/cascade.py` (cost-ordered escalation; "smart" model on `<lyra:escalate>` token or low-logprob).
- Anthropic-style tool schema as canonical with translation adapters on egress/ingress.
- Hermetic mocked-network tests (`test_llm_providers.py`).
- DeepSeek alias `v4-flash` / `v4-pro`; Kimi alias `kimi-k2.5`; Qwen aliases `qwen-max` / `qwen-plus` / `qwen-turbo`.

**So the user's question is partly already answered:** DeepSeek is the *default* fast/smart provider; Kimi K2 ships via the Groq preset; Qwen ships native. The real gaps are:

1. **No `lyra model add` UX.** Users who want a *new* provider not in the 15 presets (e.g., direct Moonshot endpoint not via Groq, Z.ai GLM-4.6, Together AI, Fireworks AI, DeepInfra, on-prem vLLM, on-prem TGI) must edit Python code in `openai_compatible.py:PRESETS` — not user-friendly.
2. **No plugin format.** Third parties can't ship `pip install lyra-provider-moonshot` and have it light up automatically.
3. **No capability auto-discovery.** When a user adds a new model, Lyra doesn't probe its tool-use / context-length / vision support — defaults are guessed.
4. **No cost-aware routing.** The cascade is *order-fixed*; there's no per-model price feed driving routing decisions.
5. **No hot-reload.** Adding a provider requires restarting Lyra.
6. **Gap providers.** Direct Moonshot (`api.moonshot.cn/v1`), Z.ai GLM (`open.bigmodel.cn/api/paas/v4`), Together AI (`api.together.xyz/v1`), Fireworks AI (`api.fireworks.ai/inference/v1`), DeepInfra (`api.deepinfra.com/v1/openai`), Replicate (`api.replicate.com/v1`), Anyscale endpoints — none of these are shipped today, even though they're all OpenAI-compatible.

v3.10 closes all six gaps additively. Existing presets and `--llm` semantics keep working unchanged.

### Two themes

| Theme | Phases |
|---|---|
| **A. Extension UX** | L310-1 `lyra model add` CLI · L310-2 plugin schema + entry-points · L310-3 capability auto-discovery · L310-9 hot-reload |
| **B. Production hardening** | L310-4 gap-fill native providers · L310-5 per-provider observability · L310-6 health checks + smart fallback chains · L310-7 cost-aware routing · L310-8 multi-tenant key management |

### Identity — what does NOT change

The Lyra invariants stay verbatim. The 13 shipped providers + 15 presets + `LLMProvider` Protocol + cascade router + two-tier slots all continue to work *unchanged*. v3.10 only **adds** an extensibility layer on top.

---

## §1 — Architecture

```mermaid
flowchart TB
    subgraph Existing [v3.0–v3.9 — keep working unchanged]
        LLMP[LLMProvider Protocol<br/>harness_core.models]
        OACOMP[OpenAICompatibleLLM<br/>15 presets]
        REG[ProviderSpec registry<br/>13 providers]
        CASC[ConfidenceCascadeRouter]
        SLOTS[fast/smart slots]
    end

    subgraph New [v3.10 — extension layer]
        ADD["`lyra model add`<br/>CLI wizard"]
        PLUGIN[Plugin schema<br/>provider_plugin.py]
        ENTRY[Entry-point loading<br/>pyproject.toml]
        DISC[Capability auto-discovery<br/>probe on first use]
        HOTLD[Hot-reload<br/>SIGHUP / file watcher]
        OBS[Per-provider observability<br/>latency / cost / error]
        HEALTH[Health checks<br/>periodic probes]
        FALLBACK[Smart fallback chains<br/>health-aware]
        COSTRT[Cost-aware routing<br/>FrugalGPT-style]
        MTENANT[Multi-tenant<br/>per-tenant key store]
    end

    subgraph Native [v3.10 — gap-fill native providers]
        MOON[Moonshot direct<br/>Kimi K2 native]
        ZAI[Z.ai GLM<br/>GLM-4.6, GLM-5V-Turbo]
        TOG[Together AI]
        FW[Fireworks AI]
        DEEPINF[DeepInfra]
        REP[Replicate]
        ONPREM[Generic on-prem<br/>vLLM / TGI]
    end

    LLMP --> OACOMP
    LLMP --> REG
    OACOMP --> CASC

    ADD -. writes .-> PLUGIN
    PLUGIN -. registers via .-> ENTRY
    ENTRY -. extends .-> REG
    PLUGIN -. extends .-> OACOMP

    DISC -. probes .-> PLUGIN
    HOTLD -. reloads .-> ENTRY

    OBS -. observes .-> CASC
    HEALTH -. monitors .-> ENTRY
    FALLBACK -. uses .-> HEALTH
    COSTRT -. orders .-> CASC
    MTENANT -. scopes .-> ENTRY

    Native --> PLUGIN

    classDef new fill:#ffe0b2,stroke:#e65100,stroke-width:2px
    classDef existing fill:#c8e6c9,stroke:#2e7d32,stroke-width:1px
    class Existing existing
    class New,Native new
```

### Package map (deltas vs v3.9)

| Package | Status |
|---|---|
| `lyra-cli/providers/` | **Extended (L310-1, L310-2)** — `plugin.py`, `discovery.py`, `cli_add.py` |
| `lyra-core/providers/` | **Extended (L310-2, L310-7, L310-8)** — `plugin_loader.py`, `cost_router.py`, `tenant_keys.py` |
| `lyra-cli/providers/native/` | **NEW (L310-4)** — `moonshot.py`, `zai.py`, `together.py`, `fireworks.py`, `deepinfra.py`, `replicate.py`, `vllm_generic.py`, `tgi_generic.py` |
| `lyra-core/providers/health.py` | **NEW (L310-6)** — periodic health probes |
| `lyra-core/providers/observability.py` | **NEW (L310-5)** — per-provider latency/cost/error metrics |
| `lyra-core/providers/hotload.py` | **NEW (L310-9)** — file-watcher + SIGHUP reload |
| `lyra-cli/commands/model.py` | **Extended (L310-1, L310-5, L310-6)** — `lyra model add/list/test/health/observe` |
| `~/.lyra/providers/` | **NEW directory** — user-installed provider plugins |
| `pyproject.toml` | **Extended (L310-2)** — `[project.entry-points."lyra.providers"]` |

---

## §2 — Phases L310-1 through L310-9

### L310-1 — `lyra model add` interactive CLI wizard

**Why now.** The single most user-visible feature. A user types `lyra model add`, answers 5–8 questions, and a new provider is registered, validated, and ready to use — without editing any Python file.

**Concrete deliverables.**

```text
packages/lyra-cli/src/lyra_cli/commands/
  model.py                 # NEW (or EXTEND if exists) — top-level model command surface
                           # lyra model add                       # interactive wizard
                           # lyra model add --from-url <url>      # generate from OpenAI-compat probe
                           # lyra model add --preset <preset>     # bundled-preset shortcut
                           # lyra model list                      # all configured providers
                           # lyra model show <name>               # full ProviderSpec dump
                           # lyra model remove <name>
                           # lyra model test <name>               # round-trip ping with mock prompt
                           # lyra model health                    # health-check dashboard

packages/lyra-cli/src/lyra_cli/providers/
  cli_add.py               # NEW — interactive wizard
                           # questions:
                           #   1. Provider name (slug)             [e.g. "moonshot-direct"]
                           #   2. Display name                     [e.g. "Moonshot (Kimi)"]
                           #   3. Base URL                         [e.g. "https://api.moonshot.cn/v1"]
                           #   4. API key env var name             [e.g. "MOONSHOT_API_KEY"]
                           #   5. Default model                    [e.g. "moonshot-v1-128k"]
                           #   6. Available models (comma-sep)     [e.g. "moonshot-v1-8k,moonshot-v1-32k,moonshot-v1-128k,kimi-k2"]
                           #   7. Tool-use schema                  [openai|anthropic|none]
                           #   8. Streaming supported              [y/n] (default y)
                           #   9. Reasoning support                [y/n]
                           #  10. Vision support                   [y/n]
                           #  11. Run capability auto-discovery now? [y/n] (default y)
                           # writes ~/.lyra/providers/<slug>.toml
                           # registers with running session via hot-reload (L310-9)

  plugin_schema.py         # NEW — Pydantic schema for provider plugin TOML
                           # class ProviderPluginSchema(BaseModel):
                           #     name: str
                           #     display_name: str
                           #     base_url: str
                           #     env_vars: tuple[str, ...]
                           #     default_model: str
                           #     models: tuple[str, ...]
                           #     tool_schema: Literal["openai","anthropic","none"]
                           #     supports_streaming: bool = True
                           #     supports_reasoning: bool = False
                           #     supports_vision: bool = False
                           #     context_window: int = 32768
                           #     extra_headers: dict[str, str] = {}
                           #     extra_body: dict[str, Any] = {}            # provider-routing knobs
                           #     openai_compatible: bool = True             # if False, requires custom plugin module
                           #     plugin_module: str | None = None           # for non-OpenAI-compat providers
```

**TOML format** (`~/.lyra/providers/moonshot-direct.toml`):

```toml
[provider]
name = "moonshot-direct"
display_name = "Moonshot (Kimi K2 native)"
base_url = "https://api.moonshot.cn/v1"
env_vars = ["MOONSHOT_API_KEY"]
default_model = "kimi-k2"
models = ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "kimi-k2", "kimi-k2.5"]
tool_schema = "openai"
supports_streaming = true
supports_reasoning = false
supports_vision = false
context_window = 128000
openai_compatible = true

[provider.extra_headers]
# user-extensible: "X-Custom-Header" = "value"
```

**Tests.**

```text
packages/lyra-cli/tests/
  test_cli_model_add.py         # 20+ tests
                                # - wizard creates valid ~/.lyra/providers/<name>.toml
                                # - reject duplicate slug
                                # - validate base URL format
                                # - validate model slug format
                                # - --from-url flag probes /v1/models endpoint
                                # - --preset shortcut for known presets
                                # - test round-trip via `lyra model test`
```

**Acceptance.**

- ✅ `lyra model add` wizard registers a new provider in <2 minutes for OpenAI-compat backends.
- ✅ Provider becomes immediately available in `--llm <name>`.
- ✅ `lyra model list` shows the new provider with metadata.
- ✅ `lyra model test <name>` round-trips a `Hello, world` ping successfully.
- ✅ `lyra model remove <name>` deletes the TOML and unregisters.

**Effort.** ~1.5 weeks.

---

### L310-2 — Plugin schema + entry-point loading

**Why now.** TOML files are great for users; Python plugins are great for third parties shipping `pip install lyra-provider-moonshot`. Both should compose. Standard `pyproject.toml` entry-points are the canonical Python plugin pattern.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/providers/
  plugin_loader.py         # NEW — load provider plugins from three sources
                           # Source priority (highest to lowest):
                           #   1. ~/.lyra/providers/*.toml     (user-installed via L310-1 wizard)
                           #   2. .lyra/providers/*.toml       (project-local)
                           #   3. entry-point [lyra.providers] (pip-installed packages)
                           #
                           # class PluginLoader:
                           #     def load_all(self) -> list[ProviderSpec]
                           #     def reload(self) -> None
                           #     def watch(self, callback: Callable) -> None
```

**Entry-point declaration in user's `pyproject.toml`:**

```toml
[project.entry-points."lyra.providers"]
moonshot-direct = "lyra_provider_moonshot:make_provider"
```

The `make_provider` function returns a `ProviderSpec` and a callable factory that returns an `LLMProvider` instance. Lyra discovers it on startup (and on reload, L310-9).

**Plugin module template** (a third-party Python package would look like):

```python
# lyra_provider_moonshot/__init__.py
from lyra_core.providers.registry import ProviderSpec
from lyra_cli.providers.openai_compatible import OpenAICompatibleLLM, _Preset

def make_provider() -> tuple[ProviderSpec, Callable[..., OpenAICompatibleLLM]]:
    spec = ProviderSpec(
        key="moonshot-direct",
        display_name="Moonshot (Kimi K2 native)",
        env_vars=("MOONSHOT_API_KEY",),
        default_model="kimi-k2",
        context_window=128_000,
        supports_tools=True,
        supports_reasoning=False,
        supports_streaming=True,
        supports_vision=False,
        notes="Direct Moonshot endpoint, not via Groq",
        models=("moonshot-v1-8k","moonshot-v1-32k","moonshot-v1-128k","kimi-k2","kimi-k2.5"),
    )
    def factory(model: str = "kimi-k2", **kwargs) -> OpenAICompatibleLLM:
        return OpenAICompatibleLLM(
            preset=_Preset(
                base_url="https://api.moonshot.cn/v1",
                env_vars=("MOONSHOT_API_KEY",),
                default_model=model,
            ),
            **kwargs,
        )
    return spec, factory
```

**Custom-protocol plugins** (non-OpenAI-compatible) implement `LLMProvider` Protocol directly:

```python
# lyra_provider_custom/__init__.py
from harness_core.models import LLMProvider
from harness_core.messages import Message, ToolCall, StopReason

class CustomLLM(LLMProvider):
    def generate(self, messages, tools=None, max_tokens=2048, temperature=0.0) -> Message:
        ...  # custom protocol implementation
```

**Tests.**

```text
packages/lyra-core/tests/providers/
  test_plugin_loader.py         # 25+ tests
                                # - loads from ~/.lyra/providers/*.toml
                                # - loads from .lyra/providers/*.toml (project-local)
                                # - loads from entry-points
                                # - source priority: user > project > entry-point
                                # - duplicate slug across sources: user wins; warning logged
                                # - invalid TOML: skip + warning, don't crash
                                # - reload() picks up new files
```

**Acceptance.**

- ✅ A `pip install lyra-provider-moonshot` package gets auto-discovered on Lyra startup.
- ✅ A `~/.lyra/providers/*.toml` file overrides an entry-point of the same name.
- ✅ Project-local `.lyra/providers/*.toml` overrides system entry-points but not user.
- ✅ Invalid plugin file logs a warning, doesn't crash startup.

**Effort.** ~1.5 weeks.

---

### L310-3 — Capability auto-discovery (probe on first use)

**Why now.** When a user types `lyra model add` for an unfamiliar endpoint, they often don't know whether it supports tool-use, vision, or what its context window is. Lyra should probe.

**Concrete deliverables.**

```text
packages/lyra-cli/src/lyra_cli/providers/
  discovery.py             # NEW — capability auto-discovery
                           # class CapabilityProbe:
                           #     async def probe(provider: ProviderSpec, sample_model: str) -> ProbeResult
                           #
                           # @dataclass class ProbeResult:
                           #     supports_tools: bool
                           #     supports_streaming: bool
                           #     supports_vision: bool
                           #     supports_reasoning: bool
                           #     context_window_estimate: int
                           #     latency_p50_ms: float
                           #     errors: list[str]
                           #
                           # probe sequence:
                           #   1. GET /v1/models                  # if 200 OK: list of models
                           #   2. POST /v1/chat/completions       # plain message; check response
                           #   3. POST /v1/chat/completions       # with tool definition; check tool_calls
                           #   4. POST /v1/chat/completions       # with vision content; check support
                           #   5. POST /v1/chat/completions       # with stream=true; check SSE
                           #   6. send progressively longer prompts to estimate context window
                           # caches results in ~/.lyra/providers/<name>.discovery.json
```

**Discovery cache TTL.** 30 days default. `lyra model rediscover <name>` forces refresh.

**Tests.**

```text
packages/lyra-cli/tests/
  test_discovery.py            # 18 tests
                               # - probe identifies tool support correctly
                               # - probe identifies streaming support
                               # - context-window estimation lands within ±20% of declared
                               # - probe failure (offline) returns errors[] but no crash
                               # - cache hit on second probe within TTL
```

**Acceptance.**

- ✅ Probing a known endpoint (mocked) correctly identifies supported features.
- ✅ Probe latency < 30 seconds for a typical OpenAI-compat endpoint.
- ✅ Failed probe doesn't crash; user sees actionable error.
- ✅ `lyra model show <name>` shows discovered capabilities, marked as "discovered" vs "user-declared".

**Effort.** ~2 weeks.

---

### L310-4 — Gap-fill native providers (Moonshot direct, Z.ai GLM, Together AI, Fireworks AI, DeepInfra, Replicate, generic vLLM/TGI)

**Why now.** Even with the plugin system, having popular providers shipped out-of-the-box matters. These seven cover ~95% of the "I want to add a model" cases.

**Concrete deliverables.**

```text
packages/lyra-cli/src/lyra_cli/providers/native/
  __init__.py
  moonshot.py              # Direct Moonshot (Kimi K2, Kimi K2.5)
                           # Base URL: https://api.moonshot.cn/v1
                           # Env: MOONSHOT_API_KEY
                           # Models: kimi-k2, kimi-k2.5, moonshot-v1-{8k,32k,128k}

  zai.py                   # Z.ai (GLM-4.6, GLM-5V-Turbo) — see docs/104
                           # Base URL: https://open.bigmodel.cn/api/paas/v4
                           # Env: ZAI_API_KEY
                           # Models: glm-4.6, glm-4.6-air, glm-5v-turbo, glm-zero-preview
                           # Special: GLM-5V-Turbo has multimodal toolchain

  together.py              # Together AI
                           # Base URL: https://api.together.xyz/v1
                           # Env: TOGETHER_API_KEY
                           # Models: 100+ open-weights (Llama 3.3, Qwen 3, Mistral, etc.)

  fireworks.py             # Fireworks AI
                           # Base URL: https://api.fireworks.ai/inference/v1
                           # Env: FIREWORKS_API_KEY
                           # Models: accounts/fireworks/models/{deepseek-v3,llama-v3p3-70b,...}

  deepinfra.py             # DeepInfra
                           # Base URL: https://api.deepinfra.com/v1/openai
                           # Env: DEEPINFRA_API_KEY
                           # Models: meta-llama/*, deepseek-ai/*, Qwen/*, mistralai/*

  replicate.py             # Replicate (custom protocol — NOT OpenAI-compat)
                           # Endpoint: https://api.replicate.com/v1/predictions
                           # Env: REPLICATE_API_TOKEN
                           # Custom plugin module; webhook-based completion model

  vllm_generic.py          # Generic vLLM endpoint (on-prem)
                           # Base URL: user-supplied (e.g. http://localhost:8000/v1)
                           # No API key required by default; supports custom auth header
                           # Models: discovered via /v1/models endpoint

  tgi_generic.py           # Generic Text Generation Inference (HF) endpoint
                           # Base URL: user-supplied
                           # OpenAI-compat as of TGI 1.4+
```

**Capability annotations** (added to `lyra-core/providers/registry.py`):

```python
# Native gap-fill providers, registered alongside existing 13.
ProviderSpec(
    key="moonshot",
    display_name="Moonshot (Kimi K2 direct)",
    env_vars=("MOONSHOT_API_KEY",),
    default_model="kimi-k2",
    context_window=128_000,
    supports_tools=True, supports_reasoning=False, supports_streaming=True, supports_vision=False,
    notes="Direct Moonshot endpoint, not via Groq",
    models=("moonshot-v1-8k","moonshot-v1-32k","moonshot-v1-128k","kimi-k2","kimi-k2.5"),
),
ProviderSpec(
    key="zai",
    display_name="Z.ai (GLM)",
    env_vars=("ZAI_API_KEY",),
    default_model="glm-4.6",
    context_window=128_000,
    supports_tools=True, supports_reasoning=True, supports_streaming=True, supports_vision=True,
    notes="GLM-5V-Turbo: native multimodal foundation model (docs/104)",
    models=("glm-4.6","glm-4.6-air","glm-5v-turbo","glm-zero-preview"),
),
# ... and so on for together, fireworks, deepinfra, replicate, vllm-generic, tgi-generic
```

**Aliases** (added to `lyra-core/providers/aliases.py`):

```python
"glm-5v-turbo" -> ("zai", "glm-5v-turbo")
"moonshot-128k" -> ("moonshot", "moonshot-v1-128k")
"kimi-k2-direct" -> ("moonshot", "kimi-k2")  # disambiguates from Groq-hosted kimi-k2
"glm-4.6" -> ("zai", "glm-4.6")
```

**Tests.**

```text
packages/lyra-cli/tests/providers/native/
  test_moonshot.py             # 12 tests — round-trip, tool-call, streaming, error handling
  test_zai.py                  # 14 tests — including GLM-5V-Turbo multimodal
  test_together.py             # 10 tests
  test_fireworks.py            # 10 tests
  test_deepinfra.py            # 10 tests
  test_replicate.py            # 12 tests — webhook-based completion is more complex
  test_vllm_generic.py         # 8 tests — on-prem auth header support
  test_tgi_generic.py          # 8 tests
```

**Acceptance.**

- ✅ All 7 native providers shipped, registered, and discoverable via `lyra model list`.
- ✅ Each has hermetic mocked-network tests covering round-trip + tool-use + streaming + error handling.
- ✅ Z.ai's GLM-5V-Turbo multimodal lights up Lyra's vision pipeline (cross-references [104-glm-5v-turbo-native-multimodal-agents.md](docs/104-glm-5v-turbo-native-multimodal-agents.md)).
- ✅ Generic vLLM / TGI endpoints work with user-supplied base URL.

**Effort.** ~3 weeks (multiple providers; each is small but they add up).

---

### L310-5 — Per-provider observability

**Why now.** Once users add many providers, knowing which is fast / cheap / reliable matters. Today there's a `last_usage` dict per instance, but no aggregation or dashboard.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/providers/
  observability.py         # NEW — per-provider metrics aggregation
                           # class ProviderObservability:
                           #     def record_call(
                           #         self,
                           #         provider: str,
                           #         model: str,
                           #         tokens_in: int,
                           #         tokens_out: int,
                           #         latency_ms: float,
                           #         outcome: Literal["success","timeout","error","rate_limited"],
                           #         cost_usd: float | None,
                           #     ) -> None
                           #     def stats(self, window_hours: int = 24) -> dict[str, ProviderStats]
                           #
                           # @dataclass class ProviderStats:
                           #     calls: int
                           #     success_rate: float
                           #     latency_p50_ms: float
                           #     latency_p95_ms: float
                           #     total_tokens_in: int
                           #     total_tokens_out: int
                           #     total_cost_usd: float
                           #     errors_by_type: dict[str, int]
                           # persists to .lyra/observability/providers.jsonl

packages/lyra-cli/src/lyra_cli/commands/
  model.py                 # EXTEND
                           # lyra model observe                   # 24h dashboard
                           # lyra model observe <name>            # per-provider details
                           # lyra model observe --window 7d
```

**Cost feed** (optional): pluggable price catalog at `~/.lyra/providers/prices.json` with per-provider per-model `(input_per_1m, output_per_1m)` pairs. If absent, cost shows as `unknown`.

**Tests.**

```text
packages/lyra-core/tests/providers/
  test_observability.py        # 15 tests — aggregation correctness, percentile math, cost calc
```

**Acceptance.**

- ✅ Every provider call records latency, tokens, outcome.
- ✅ `lyra model observe` shows a 24h dashboard ranked by cost.
- ✅ Error breakdown by type (rate_limited / timeout / 500 / 401 / etc.).
- ✅ Cost is `unknown` if no price catalog provided; not a crash.

**Effort.** ~1.5 weeks.

---

### L310-6 — Health checks + smart fallback chains

**Why now.** A user-defined provider may go down. Today the cascade falls through silently to the next; users want visibility and explicit fallback.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/providers/
  health.py                # NEW — periodic health probes
                           # class HealthChecker:
                           #     interval_minutes: int = 5
                           #     timeout_seconds: int = 10
                           #     async def probe(self, provider_key: str) -> HealthStatus
                           #     def status(self, provider_key: str) -> HealthStatus
                           #     def all_status(self) -> dict[str, HealthStatus]
                           #
                           # @dataclass class HealthStatus:
                           #     state: Literal["healthy","degraded","unhealthy","unknown"]
                           #     last_probe_at: datetime
                           #     last_success_at: datetime | None
                           #     consecutive_failures: int
                           #     details: dict
                           # state-transition rules:
                           #   3 consecutive successes → healthy
                           #   3 consecutive failures → unhealthy
                           #   mixed → degraded

  smart_fallback.py        # NEW — health-aware fallback chains
                           # class SmartFallback(LLMProvider):
                           #     def __init__(self, primary: str, backups: tuple[str, ...]) -> None
                           #     def generate(self, ...) -> Message:
                           #         if self.health.status(self.primary).state != "unhealthy":
                           #             try: return self.providers[self.primary].generate(...)
                           #             except (HTTPError, RateLimitError, Timeout):
                           #                 self.health.record_failure(self.primary)
                           #         for backup in self.backups:
                           #             if self.health.status(backup).state != "unhealthy":
                           #                 try: return self.providers[backup].generate(...)
                           #                 except: continue
                           #         raise NoProviderAvailable

packages/lyra-cli/src/lyra_cli/commands/
  model.py                 # EXTEND
                           # lyra model health                    # all providers' health
                           # lyra model health <name>             # one provider details
                           # lyra model fallback <primary> <backup1> <backup2>   # configure chain
                           # lyra model fallback list             # show configured chains
```

**Configuration in `~/.lyra/config.toml`:**

```toml
[providers.fallback]
chat = ["moonshot", "deepseek", "groq"]      # primary, then backups in order
plan = ["anthropic", "openai-reasoning"]
```

**Tests.**

```text
packages/lyra-core/tests/providers/
  test_health.py               # 18 tests — state transitions, periodic probing
  test_smart_fallback.py       # 22 tests — chain progression, all-unhealthy raises, mixed states
```

**Acceptance.**

- ✅ Health probe runs every 5 minutes by default.
- ✅ A primary going down triggers fallback within one user-call.
- ✅ `lyra model health` shows all states.
- ✅ All-unhealthy chain raises `NoProviderAvailable` with diagnostic context.

**Effort.** ~2 weeks.

---

### L310-7 — Cost-aware routing (FrugalGPT-style)

**Why now.** Today the cascade is order-fixed. With observability (L310-5) Lyra has the data to *route by cost* — pick the cheapest provider that passes a quality bar for the current task class.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/providers/
  cost_router.py           # NEW — FrugalGPT-style cost-aware routing
                           # class CostAwareRouter:
                           #     def __init__(
                           #         self,
                           #         providers: list[str],
                           #         price_catalog: PriceCatalog,
                           #         quality_floor: float = 0.8,
                           #         confidence_estimator: ConfidenceEstimator,
                           #     ) -> None
                           #     def route(self, task: Task) -> str:
                           #         # cheapest first; escalate if confidence < quality_floor
                           #         for provider in self._sorted_by_cost(task):
                           #             response = self._call(provider, task)
                           #             if self.estimator(response) >= self.quality_floor:
                           #                 return response
                           #         return self._call(self._most_expensive(), task)
                           # cross-references docs/86-frugalgpt and docs/87-routellm

packages/lyra-cli/src/lyra_cli/commands/
  model.py                 # EXTEND
                           # lyra model cost-route on             # enable cost-aware routing
                           # lyra model cost-route off
                           # lyra model cost-route status
                           # lyra model cost-route quality-floor 0.85
```

**Quality bar** is the `ConfidenceEstimator` from `lyra-core/routing/cascade.py` — semantic-entropy / log-prob / surrogate-verifier (any of v3.8 L38-1's gating mechanisms).

**Tests.**

```text
packages/lyra-core/tests/providers/
  test_cost_router.py          # 20 tests
                               # - cheap-first ordering by price-per-1k tokens
                               # - escalates on low confidence
                               # - never picks unhealthy providers
                               # - falls back to most-expensive on all-low-confidence
```

**Acceptance.**

- ✅ Cost-aware routing produces total-cost reduction ≥30% on a synthetic mixed-task bench at matched quality.
- ✅ Quality floor configurable; default 0.8.
- ✅ Routing decisions auditable via witness lattice (v3.8 L38-3).

**Effort.** ~2 weeks.

---

### L310-8 — Multi-tenant key management

**Why now.** Production deployments serve multiple users / projects / programs; each may have its own API keys and per-program budget. Today everything reads `~/.lyra/auth.json` flat.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/providers/
  tenant_keys.py           # NEW — per-tenant key store
                           # class TenantKeyStore:
                           #     def get_key(
                           #         self,
                           #         tenant: str,
                           #         provider: str,
                           #         env_var: str,
                           #     ) -> str | None
                           # resolution order per-call:
                           #   1. process env vars (highest)
                           #   2. ~/.lyra/tenants/<tenant>/auth.json
                           #   3. ~/.lyra/auth.json (fallback global)
                           #   4. project-local .env

packages/lyra-cli/src/lyra_cli/commands/
  model.py                 # EXTEND
                           # lyra model tenant init <tenant>
                           # lyra model tenant connect <tenant> <provider>
                           # lyra model tenant list
                           # lyra model tenant remove <tenant>
                           # lyra model tenant budget <tenant> <usd_limit>
```

**Tenant isolation invariants** (mirroring v3.8 cross-tenant bright lines):

- A skill / curator activated under tenant A *must not* read tenant B's keys.
- Budget overrun in tenant A *must not* halt tenant B's work.
- Witness lattice records `tenant_id` per routing decision.

**Tests.**

```text
packages/lyra-core/tests/providers/
  test_tenant_keys.py          # 15 tests — isolation, resolution order, missing key fallback
```

**Acceptance.**

- ✅ Tenant A's session uses only tenant A's keys (verified by mocked-network test).
- ✅ Per-tenant budget overrun pauses tenant A only.
- ✅ Process env vars still win for backwards-compat / dev workflows.

**Effort.** ~1.5 weeks.

---

### L310-9 — Hot-reload providers without session restart

**Why now.** Adding a provider via `lyra model add` should make it usable *in the current session* — restarting Lyra to pick up a new provider is friction.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/providers/
  hotload.py               # NEW — file-watcher + SIGHUP reload
                           # class HotLoader:
                           #     def __init__(self, plugin_loader: PluginLoader) -> None
                           #     def start(self) -> None:
                           #         # watches:
                           #         #   ~/.lyra/providers/*.toml
                           #         #   .lyra/providers/*.toml
                           #         # also responds to SIGHUP for entry-point reload
                           #     def stop(self) -> None
                           #
                           # On change: re-runs PluginLoader.reload() → updates registry
                           # In-flight calls finish with old provider; new calls use new

packages/lyra-cli/src/lyra_cli/commands/
  model.py                 # EXTEND
                           # lyra model reload                    # explicit manual reload
```

**Concurrency model.** New providers register atomically. In-flight calls finish with whatever provider they started with. Removed providers are *kept alive* until in-flight calls complete (graceful drain).

**Tests.**

```text
packages/lyra-core/tests/providers/
  test_hotload.py              # 12 tests
                               # - new TOML in ~/.lyra/providers/ → discoverable within 2 seconds
                               # - removed TOML → drained, then unregistered
                               # - SIGHUP triggers entry-point re-scan
                               # - in-flight call survives provider removal
```

**Acceptance.**

- ✅ `lyra model add` followed by immediate `lyra model test <name>` works without restart.
- ✅ Concurrent modification of `~/.lyra/providers/` doesn't crash running session.
- ✅ Removed provider's in-flight calls drain gracefully (no truncated responses).

**Effort.** ~1.5 weeks.

---

## §3 — Phasing summary

| Phase | Title | Effort | Depends on | Stage |
|---|---|---|---|---|
| **L310-1** | `lyra model add` CLI wizard | ~1.5 wk | (none) | MVP |
| **L310-2** | Plugin schema + entry-point loading | ~1.5 wk | L310-1 | MVP |
| **L310-3** | Capability auto-discovery | ~2 wk | L310-1 | MVP |
| **L310-9** | Hot-reload providers | ~1.5 wk | L310-2 | MVP |
| **L310-4** | Gap-fill native providers (Moonshot, Z.ai, Together, Fireworks, DeepInfra, Replicate, vLLM, TGI) | ~3 wk | L310-2 | Stage 2 |
| **L310-5** | Per-provider observability | ~1.5 wk | (none) | Stage 2 |
| **L310-6** | Health checks + smart fallback chains | ~2 wk | L310-5 | Stage 3 |
| **L310-7** | Cost-aware routing (FrugalGPT) | ~2 wk | L310-5 | Stage 3 |
| **L310-8** | Multi-tenant key management | ~1.5 wk | (none) | Stage 3 |

**MVP (L310-1 + L310-2 + L310-3 + L310-9): ~6.5 weeks.** Delivers the user-facing extension experience: `lyra model add`, plugin loading, capability auto-discovery, hot-reload. After this, anyone can add a new provider in minutes.

**Stage 2 (L310-4 + L310-5): ~4.5 weeks.** Ships 7 native gap-fill providers + per-provider observability dashboard.

**Stage 3 (L310-6 + L310-7 + L310-8): ~5.5 weeks.** Production hardening: smart fallback, cost-aware routing, multi-tenant.

**Total: ~16.5 weeks** for full v3.10.

---

## §4 — Concrete file map

### What to add

```text
packages/lyra-core/src/lyra_core/providers/
├── plugin_loader.py            # NEW — L310-2
├── observability.py            # NEW — L310-5
├── health.py                   # NEW — L310-6
├── smart_fallback.py           # NEW — L310-6
├── cost_router.py              # NEW — L310-7
├── tenant_keys.py              # NEW — L310-8
└── hotload.py                  # NEW — L310-9

packages/lyra-cli/src/lyra_cli/providers/
├── plugin_schema.py            # NEW — L310-1
├── cli_add.py                  # NEW — L310-1
├── discovery.py                # NEW — L310-3
└── native/                     # NEW PACKAGE — L310-4
    ├── __init__.py
    ├── moonshot.py
    ├── zai.py
    ├── together.py
    ├── fireworks.py
    ├── deepinfra.py
    ├── replicate.py
    ├── vllm_generic.py
    └── tgi_generic.py

packages/lyra-cli/src/lyra_cli/commands/
└── model.py                    # NEW or EXTEND — L310-1, L310-5, L310-6, L310-7, L310-8, L310-9

~/.lyra/providers/              # NEW directory (created by L310-1)
.lyra/providers/                # NEW (project-local; created on demand)
```

### What to extend

- `lyra-core/providers/registry.py` — add 7 native `ProviderSpec` entries (L310-4); read entry-points at module load (L310-2).
- `lyra-core/providers/aliases.py` — add aliases for new natives (L310-4).
- `lyra-cli/llm_factory.py` — extend cascade order to include new natives at sensible priority (L310-4); read tenant keys instead of global keys when tenant context active (L310-8).
- `lyra-cli/providers/openai_compatible.py` — accept dynamic `_Preset` from plugin schema (L310-2).
- `pyproject.toml` (project root) — declare `[project.entry-points."lyra.providers"]` group so third-party packages can hook in (L310-2).

### What to leave alone

- `harness_core.models.LLMProvider` Protocol — the load-bearing contract; v3.10 builds on it.
- 13 existing providers — stay unchanged; v3.10 adds alongside.
- 15 existing presets in `openai_compatible.py:PRESETS` — stay unchanged; v3.10 adds dynamic-preset path alongside.
- Two-tier `fast` / `smart` slots — v3.10 doesn't change slot semantics.
- `ConfidenceCascadeRouter` — v3.10 wraps with cost-router, doesn't replace.

---

## §5 — Testing strategy

| Phase | Unit | Integration | Bench |
|---|---|---|---|
| L310-1 | wizard input validation; TOML schema; CLI smoke | `lyra model add` end-to-end with mocked-network | none |
| L310-2 | plugin loading from each source; priority resolution | end-to-end pip-install plugin → discovery | none |
| L310-3 | probe-result correctness on synthetic responses | live-mocked probes against synthetic OpenAI-compat server | probe-latency bench |
| L310-4 | per-provider round-trip + tool-use + streaming | each provider hermetic mock test | none |
| L310-5 | aggregation; percentile math; cost calc | observability dashboard integration | none |
| L310-6 | health state transitions; fallback progression | smart-fallback end-to-end | none |
| L310-7 | cost ordering; quality-floor escalation | end-to-end FrugalGPT-style | ≥30% cost reduction synthetic bench |
| L310-8 | tenant isolation; resolution order | multi-tenant end-to-end | none |
| L310-9 | file-watcher correctness; SIGHUP handling | add-then-test-without-restart | none |

All hermetic; no real-network calls in CI. Optional `tests/integration/live/` directory for opt-in live-network tests gated behind `LYRA_TEST_LIVE=1` env var.

---

## §6 — Open questions (decide before L310-1 begins)

1. **Plugin file format.** TOML (recommended; matches `pyproject.toml` familiarity), JSON (programmatic-friendly), YAML (more human-friendly). **Recommended:** TOML.
2. **Entry-point group name.** `"lyra.providers"` (recommended), `"lyra-providers"`, `"lyra-llm-providers"`. **Recommended:** `"lyra.providers"`.
3. **Auto-discovery TTL.** 7 days, 30 days, 90 days. **Recommended:** 30 days.
4. **Health-probe interval.** 1 min (aggressive), 5 min (recommended), 15 min (conservative). **Recommended:** 5 min.
5. **Cost-aware-routing default.** Off by default, opt-in via `lyra model cost-route on`; or on by default. **Recommended:** off by default; users opt in.
6. **Quality-floor threshold for cost-router.** 0.7, 0.8, 0.85, 0.9. **Recommended:** 0.8.
7. **Native providers in v3.10.0.** All 7 (Moonshot, Z.ai, Together, Fireworks, DeepInfra, Replicate, vLLM/TGI generic), or subset? **Recommended:** all 7; they're each small.
8. **Multi-tenant secret backend.** Filesystem (recommended for v3.10), HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault. **Recommended:** filesystem in v3.10.0; pluggable backend in v3.10.1+.
9. **Hot-reload concurrency.** Drain in-flight (recommended), kill in-flight, no in-flight protection. **Recommended:** graceful drain with 30s timeout.

---

## §7 — First-PR scope (smallest commit that ships value)

**PR #1 — Lyra v3.10.0 `lyra model add` MVP:**

```text
packages/lyra-cli/src/lyra_cli/commands/model.py          (new, ~200 LOC)
packages/lyra-cli/src/lyra_cli/providers/cli_add.py       (new, ~150 LOC)
packages/lyra-cli/src/lyra_cli/providers/plugin_schema.py (new, ~80 LOC)
packages/lyra-core/src/lyra_core/providers/plugin_loader.py (new, ~120 LOC; TOML-only path; entry-points deferred to PR #2)
packages/lyra-cli/tests/test_cli_model_add.py             (new, ~250 LOC, 20+ tests)
CHANGELOG.md                                              (entry)
```

**Acceptance for PR #1.**

- ✅ `lyra model add` interactive wizard works for OpenAI-compat backends.
- ✅ Created TOML loads on next `lyra` startup.
- ✅ `lyra model list` shows the new provider.
- ✅ `lyra model test <name>` round-trips a ping.
- ✅ All v3.9 tests pass.
- ✅ +20 new tests pass.

This PR gives users the *single most valuable* feature of v3.10 (add a provider in 2 minutes) without depending on entry-points (PR #2) or hot-reload (later PR). Restart-to-use is acceptable for MVP.

---

## §8 — One-paragraph summary

Lyra's provider abstraction is already mature — 13 providers shipped (`anthropic`, `openai`, `openai-reasoning`, `gemini`, `deepseek`, `xai`, `groq`, `cerebras`, `mistral`, `openrouter`, `lmstudio`, `ollama`, `mock`), 15 OpenAI-compatible presets in `openai_compatible.py`, two-tier `fast`/`smart` slots, capability-aware `ProviderSpec` registry, Anthropic-style canonical tool schema with provider-specific adapters, Confidence-Cascade Router, hermetic mocked-network tests. **DeepSeek is the default fast/smart provider; Kimi K2 ships via the Groq preset; Qwen ships native.** The user-facing gap is *not* "add DeepSeek/Kimi" (already there) but "add *any* provider in minutes without code changes." v3.10 closes that gap with nine phases: **L310-1** ships `lyra model add` interactive CLI wizard writing `~/.lyra/providers/<name>.toml`; **L310-2** adds plugin schema with three load sources (user TOML > project TOML > entry-points) so `pip install lyra-provider-moonshot` auto-lights-up; **L310-3** auto-discovers capabilities (tools / streaming / vision / context window) by probing a new endpoint; **L310-4** ships 7 native gap-fill providers (Moonshot direct, Z.ai GLM-4.6 + GLM-5V-Turbo, Together AI, Fireworks AI, DeepInfra, Replicate, generic vLLM/TGI) covering ~95% of "I want to add a model" cases; **L310-5** per-provider observability dashboard (latency / cost / errors); **L310-6** health checks + smart fallback chains; **L310-7** cost-aware routing FrugalGPT-style; **L310-8** multi-tenant per-tenant API key management; **L310-9** hot-reload providers without session restart. **MVP (L310-1 + L310-2 + L310-3 + L310-9) lands in ~6.5 weeks** and delivers the load-bearing user-facing experience: anyone adds a new provider in minutes, capability auto-discovered, hot-reloaded, no Python edit needed. **Full v3.10 lands in ~16.5 weeks**. **First PR is L310-1 only** — ~700 LOC, 20+ new tests, zero regressions, smallest commit that demonstrates the wizard. The plan is purely additive: existing 13 providers, 15 presets, Protocol, cascade router all continue working unchanged; v3.10 only *adds* an extensibility layer.

---

## §9 — Decision points

Three decisions before L310-1 begins:

1. **Approve the nine phases** (L310-1 through L310-9) and the additive-only constraint. Trim if too ambitious; expand if anything's missing.
2. **Pick MVP scope** — L310-1 only (~1.5 wk), L310-1+L310-2 (~3 wk), L310-1+L310-2+L310-3 (~5 wk), or full MVP L310-1 → L310-9 in MVP set (~6.5 wk).
3. **Approve open-question defaults** in §6 — TOML format, entry-point name `"lyra.providers"`, 30-day discovery TTL, 5-min health probe, cost-router off by default, quality floor 0.8, all 7 native providers in v3.10.0, filesystem secret backend, graceful-drain hot-reload.

When ready, say "go L310" or specify which phases to start with.

---

## §10 — References

**Lyra existing provider canon:**

- `packages/lyra-core/src/lyra_core/providers/registry.py` (13-provider `PROVIDER_REGISTRY`)
- `packages/lyra-core/src/lyra_core/providers/aliases.py` (slug normalization)
- `packages/lyra-cli/src/lyra_cli/providers/openai_compatible.py` (15 presets)
- `packages/lyra-cli/src/lyra_cli/llm_factory.py` (cascade ordering, env resolution)
- `packages/lyra-core/src/lyra_core/routing/cascade.py` (`ConfidenceCascadeRouter`)
- `packages/lyra-core/src/lyra_core/providers/prompt_cache.py` (per-provider cache adapters)

**Argus/cost/routing canon** (in `harness-engineering/docs/`):

- [86 — FrugalGPT](docs/86-frugalgpt.md) — cost-aware cascade routing (used in L310-7)
- [87 — RouteLLM](docs/87-routellm.md) — preference-trained routing
- [88 — Confidence-driven router](docs/88-confidence-driven-router.md) — semantic-entropy gating
- [104 — GLM-5V-Turbo](docs/104-glm-5v-turbo-native-multimodal-agents.md) — Z.ai's native multimodal foundation model (lights up via L310-4 zai.py)
- [147 — Vendor lock-in](docs/147-vendor-lock-in.md) — per-Container vendor decoupling rationale

**Lyra adjacent plans:**

- [LYRA_V3_7_CLAUDE_CODE_PARITY_PLAN.md](LYRA_V3_7_CLAUDE_CODE_PARITY_PLAN.md)
- [LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md](LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md)
- [LYRA_V3_9_RECURSIVE_CURATOR_PLAN.md](LYRA_V3_9_RECURSIVE_CURATOR_PLAN.md)

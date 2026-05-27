---
title: Configure providers
description: How Lyra picks an LLM provider, the canonical env vars, the legacy aliases, and how to switch on the fly.
---

<!-- lyra-legacy-aware: page documents the upgrade path from open-coding (v1.6) and open-harness, so the legacy brand names appear by design. -->


# Configure providers <span class="lyra-badge intermediate">intermediate</span>

Lyra speaks to **16 LLM providers** through a single factory:
`build_llm`. You configure which one(s) it uses with a few env vars
and one line of TOML.

## The factory

Source: [`lyra_cli/llm_factory.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/llm_factory.py).

```python
def build_llm(model_id: str | None = None, *, role: Literal["chat","plan","spawn","review","cron"] = "chat") -> BaseLLM: ...
```

`model_id` looks like `provider:model_name`, e.g.
`anthropic:claude-3-5-sonnet-latest`. If omitted, Lyra reads
`LYRA_LLM_MODEL` (or the legacy `HARNESS_LLM_MODEL`).

## The 16 providers

| Provider | `provider:` | Env var |
|---|---|---|
| Anthropic | `anthropic:` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai:` | `OPENAI_API_KEY` |
| DeepSeek | `deepseek:` | `DEEPSEEK_API_KEY` |
| Google Gemini | `gemini:` | `GEMINI_API_KEY` |
| xAI | `xai:` | `XAI_API_KEY` |
| Groq | `groq:` | `GROQ_API_KEY` |
| Cerebras | `cerebras:` | `CEREBRAS_API_KEY` |
| Mistral | `mistral:` | `MISTRAL_API_KEY` |
| Qwen / Alibaba | `qwen:` | `DASHSCOPE_API_KEY` |
| OpenRouter | `openrouter:` | `OPENROUTER_API_KEY` |
| AWS Bedrock | `bedrock:` | AWS env / IAM |
| GCP Vertex | `vertex:` | GCP creds (ADC) |
| GitHub Copilot | `copilot:` | `COPILOT_TOKEN` |
| LM Studio | `lmstudio:` | base URL only |
| Ollama | `ollama:` | base URL only |
| Generic OpenAI-compat | `openai-compat:` | `OPENAI_COMPAT_API_KEY` + base URL |

`lyra providers` lists them at runtime with the env var each one expects
and whether your environment satisfies it.

## The two slots

Lyra runs a **two-tier model split**: a **fast** slot for chat and a
**smart** slot for planning, spawning subagents, code review, and
cron. You can set them independently:

```toml title="~/.lyra/config.toml"
[llm]
fast  = "deepseek:deepseek-chat"
smart = "deepseek:deepseek-reasoner"
# `chat` falls back to fast; `plan`, `spawn`, `review`, `cron` fall back to smart.
```

Or via env:

```bash
export LYRA_FAST_MODEL=deepseek:deepseek-chat
export LYRA_SMART_MODEL=deepseek:deepseek-reasoner
```

## Switch on the fly

```
❯ /model openai:gpt-4o
✓ chat slot → openai:gpt-4o (was deepseek:deepseek-chat)

❯ /model smart anthropic:claude-3-5-sonnet-latest
✓ smart slot → anthropic:claude-3-5-sonnet-latest

❯ /model show
chat:  openai:gpt-4o
plan:  anthropic:claude-3-5-sonnet-latest
spawn: anthropic:claude-3-5-sonnet-latest
review: anthropic:claude-3-5-sonnet-latest
cron:  anthropic:claude-3-5-sonnet-latest
```

`/model` changes apply on the **next turn** — no session restart.

## Legacy env vars still work

If you're upgrading from `open-coding` (v1.6) or `open-harness`
(v1.7), the old names still work:

| Legacy | Canonical |
|---|---|
| `HARNESS_LLM_MODEL` | `LYRA_LLM_MODEL` |
| `HARNESS_REASONING_EFFORT` | `LYRA_REASONING_EFFORT` |
| `HARNESS_MAX_OUTPUT_TOKENS` | `LYRA_MAX_OUTPUT_TOKENS` |
| `OPEN_HARNESS_<PROVIDER>_MODEL` | `LYRA_<PROVIDER>_MODEL` |
| `OPEN_HARNESS_MODE` | `LYRA_MODE` |

The first read from a legacy name prints a one-shot deprecation
warning. Source: [`lyra_core/env_compat.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/env_compat.py).

## Quotas, retries, and timeouts

```toml title="~/.lyra/config.toml"
[llm.budgets]
max_cost_usd = 5.00      # per session
max_tokens   = 200_000    # per turn (transcript size)
max_steps    = 60         # per turn

[llm.retries]
max_attempts = 5
backoff_initial_s = 1.0
backoff_factor   = 2.0
retry_on = ["rate_limit", "5xx", "timeout"]

[llm.timeouts]
connect_s = 10
read_s    = 60
total_s   = 240
```

Defaults are conservative; bump for slower providers (Bedrock cold
starts can be 20s).

## Local models (Ollama)

```bash
# Run Ollama (separate terminal)
ollama serve
ollama pull llama3.1

# Configure Lyra
export LYRA_LLM_MODEL=ollama:llama3.1

lyra
```

Ollama costs nothing per token (it's local) so the cost meter shows
`$0.00` and only context-fill matters. The HUD will reflect this
automatically.

## Adding a new provider

If your provider speaks the OpenAI completions API, you don't need
new code:

```toml
[llm]
chat = "openai-compat:my-model"

[llm.openai-compat]
base_url = "https://api.example.com/v1"
api_key_env = "EXAMPLE_API_KEY"
```

For real new providers (different wire format), add a
`Provider` subclass in `lyra_cli/providers/`. See
`lyra_cli/providers/anthropic.py` for the canonical reference.

[← Write a slash command](write-slash-command.md){ .md-button }
[Turn on the TDD gate →](tdd-gate.md){ .md-button .md-button--primary }

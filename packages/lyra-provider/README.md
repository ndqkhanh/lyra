# lyra-provider — Multi-Provider Abstraction Layer

Canonical interface across Anthropic, DeepSeek, OpenAI, and Google.

| Component | Purpose |
|-----------|---------|
| `AbstractProvider` | Protocol all providers implement |
| `AnthropicProvider` | Claude models via Messages API |
| `DeepSeekProvider` | DeepSeek via OpenAI-compatible API |
| `OpenAIProvider` | GPT models via Chat Completions API |
| `GoogleProvider` | Gemini models (stub) |
| `CapabilityMatrix` | Single source of truth for provider features |

[Architecture: BREAKTHROUGH-ARCHITECTURE.md §4.5](../../lyra-upgrade/BREAKTHROUGH-ARCHITECTURE.md)

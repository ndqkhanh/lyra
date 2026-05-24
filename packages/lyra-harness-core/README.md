# lyra-harness-core

Shared harness primitives for the five agent systems in this monorepo.

## Modules

| Module | Purpose |
|---|---|
| `messages` | `Message`, `ToolCall`, `ToolResult` pydantic schemas |
| `models` | LLM provider abstraction (`LLMProvider`, `MockLLM`, `AnthropicLLM`) |
| `tools` | `Tool` ABC, `ToolRegistry`, typed-arg validation |
| `permissions` | `PermissionMode`, rule engine, decision resolver |
| `hooks` | Pre/post tool-use hooks with blocking semantics |
| `memory` | File-backed memory store with provenance |
| `observability` | Structured span logging + metrics |
| `loop` | The `AgentLoop` that composes everything |

## Install

From the monorepo root:

```bash
make install
```

Or standalone:

```bash
pip install -e packages/lyra-harness-core
pip install -e 'packages/lyra-harness-core[anthropic]'   # optional real-LLM deps
```

## Usage sketch

```python
from lyra_harness_core import AgentLoop, ToolRegistry, PermissionMode, MockLLM
from lyra_harness_core.tools_builtin import EchoTool

registry = ToolRegistry()
registry.register(EchoTool())

loop = AgentLoop(
    llm=MockLLM(scripted_outputs=["Hello world"]),
    tools=registry,
    permission_mode=PermissionMode.DEFAULT,
)

result = loop.run(task="Say hello")
print(result.final_text)
```

## Tests

```bash
pytest packages/lyra-harness-core/tests -v
```

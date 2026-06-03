# Lyra Quick Start Guide
*Get Lyra production-ready in 3 steps*

## Step 1: Install Core Dependencies (5 minutes)

```bash
# Core AI and TUI stack
pip install litellm rich textual alive-progress

# Production essentials
pip install structlog pydantic pydantic-settings tenacity python-dotenv

# Testing
pip install pytest pytest-asyncio pytest-mock pytest-cov

# Optional: MCP support
pip install mcp fastmcp
```

## Step 2: Configure API Keys (10 minutes)

Create `.env` file in your project root:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GEMINI_API_KEY=...

# DeepSeek
DEEPSEEK_API_KEY=...

# Moonshot (Kimi)
MOONSHOT_API_KEY=...

# Qwen (if using API)
QWEN_API_KEY=...

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
```

**Test each provider:**

```python
from litellm import completion

# Test OpenAI
response = completion(model="gpt-4o", messages=[{"role": "user", "content": "Hello"}])
print(response.choices[0].message.content)

# Test Anthropic
response = completion(model="claude-sonnet-4-6", messages=[{"role": "user", "content": "Hello"}])
print(response.choices[0].message.content)

# Test Gemini
response = completion(model="gemini/gemini-2.0-flash", messages=[{"role": "user", "content": "Hello"}])
print(response.choices[0].message.content)

# Test DeepSeek
response = completion(model="deepseek/deepseek-chat", messages=[{"role": "user", "content": "Hello"}])
print(response.choices[0].message.content)

# Test Ollama (local)
response = completion(model="ollama/llama3.2", messages=[{"role": "user", "content": "Hello"}])
print(response.choices[0].message.content)
```

## Step 3: Create Basic Project Structure (15 minutes)

```bash
mkdir -p lyra/{config,core,tui,tools,tests}
touch lyra/__init__.py
touch lyra/config/__init__.py
touch lyra/core/__init__.py
touch lyra/tui/__init__.py
touch lyra/tools/__init__.py
touch lyra/tests/__init__.py
```

### Create Configuration System

**`lyra/config/settings.py`:**

```python
from pydantic_settings import BaseSettings
from typing import Literal

class LyraConfig(BaseSettings):
    # API Keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    deepseek_api_key: str | None = None
    moonshot_api_key: str | None = None
    qwen_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    
    # Model Configuration
    fast_model: str = "claude-sonnet-4-6"
    reasoning_model: str = "claude-opus-4-7"
    coding_model: str = "deepseek/deepseek-chat"
    
    # Agent Configuration
    max_retries: int = 3
    timeout_seconds: int = 60
    max_turns: int = 10
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global config instance
config = LyraConfig()
```

### Create Basic Agent Loop

**`lyra/core/agent.py`:**

```python
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from litellm import acompletion
import structlog

logger = structlog.get_logger()

@dataclass
class AgentResult:
    messages: List[Dict[str, Any]]
    turns_used: int = 0
    finished_naturally: bool = False
    total_tokens: int = 0

class LyraAgent:
    def __init__(self, model: str, max_turns: int = 10):
        self.model = model
        self.max_turns = max_turns
    
    async def run(self, messages: List[Dict[str, Any]]) -> AgentResult:
        """Run agent loop with LLM."""
        logger.info("agent_started", model=self.model, max_turns=self.max_turns)
        
        conversation = messages.copy()
        turns = 0
        total_tokens = 0
        
        while turns < self.max_turns:
            turns += 1
            logger.debug("agent_turn", turn=turns, messages=len(conversation))
            
            try:
                response = await acompletion(
                    model=self.model,
                    messages=conversation
                )
                
                assistant_message = response.choices[0].message
                conversation.append({
                    "role": "assistant",
                    "content": assistant_message.content
                })
                
                total_tokens += response.usage.total_tokens
                
                # Check if finished (no tool calls, or explicit stop)
                if not hasattr(assistant_message, 'tool_calls') or not assistant_message.tool_calls:
                    logger.info("agent_finished", turns=turns, tokens=total_tokens)
                    return AgentResult(
                        messages=conversation,
                        turns_used=turns,
                        finished_naturally=True,
                        total_tokens=total_tokens
                    )
                
            except Exception as e:
                logger.error("agent_error", error=str(e), turn=turns)
                raise
        
        logger.warning("agent_max_turns", turns=turns, tokens=total_tokens)
        return AgentResult(
            messages=conversation,
            turns_used=turns,
            finished_naturally=False,
            total_tokens=total_tokens
        )
```

### Create Basic TUI

**`lyra/tui/renderer.py`:**

```python
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from alive_progress import alive_bar
import sys

console = Console()

class LyraTUI:
    def __init__(self):
        self.console = console
    
    def print(self, text: str, style: str = ""):
        """Print text with optional style."""
        self.console.print(text, style=style)
    
    def print_markdown(self, text: str):
        """Print markdown-formatted text."""
        self.console.print(Markdown(text))
    
    def stream_markdown(self, text_generator):
        """Stream markdown text with live updates."""
        with Live(console=self.console, refresh_per_second=10) as live:
            buffer = ""
            for chunk in text_generator:
                buffer += chunk
                live.update(Markdown(buffer))
    
    def progress_bar(self, total: int, description: str = "Processing"):
        """Create a progress bar context."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
    
    def spinner(self, total: int = 100, bar: str = 'smooth', spinner: str = 'dots_waves'):
        """Create an animated spinner (nyan-cat style)."""
        return alive_bar(total, bar=bar, spinner=spinner)
```

### Create Main Entry Point

**`lyra/main.py`:**

```python
import asyncio
from lyra.config.settings import config
from lyra.core.agent import LyraAgent
from lyra.tui.renderer import LyraTUI
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if config.log_format == "console" 
        else structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

async def main():
    tui = LyraTUI()
    
    tui.print("🚀 Lyra AI Agent", style="bold cyan")
    tui.print("=" * 50, style="cyan")
    
    # Get user input
    tui.print("\nEnter your query:", style="yellow")
    query = input("> ")
    
    # Create agent with user-configured model
    agent = LyraAgent(model=config.fast_model, max_turns=config.max_turns)
    
    # Run agent
    tui.print("\n🤖 Processing...\n", style="green")
    
    messages = [{"role": "user", "content": query}]
    result = await agent.run(messages)
    
    # Display result
    tui.print("\n📝 Response:\n", style="bold green")
    tui.print_markdown(result.messages[-1]["content"])
    
    # Display stats
    tui.print(f"\n📊 Stats: {result.turns_used} turns, {result.total_tokens} tokens", style="dim")

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 4: Test Your Setup (5 minutes)

```bash
# Run the basic agent
python -m lyra.main

# Run tests (after writing some)
pytest lyra/tests/ -v

# Check code quality
pip install ruff
ruff check lyra/
```

## Step 5: Add Production Features (Next Steps)

### Error Handling

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(config.max_retries),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def call_llm_with_retry(model: str, messages: List[Dict[str, Any]]):
    return await acompletion(model=model, messages=messages)
```

### Model Routing

```python
from litellm import Router

router = Router(
    model_list=[
        {
            "model_name": "fast",
            "litellm_params": {"model": config.fast_model}
        },
        {
            "model_name": "reasoning",
            "litellm_params": {"model": config.reasoning_model}
        },
        {
            "model_name": "coding",
            "litellm_params": {"model": config.coding_model}
        }
    ],
    fallbacks=[
        {"fast": ["gpt-4o-mini", "claude-haiku-4-5"]},
        {"reasoning": ["o1", "deepseek/deepseek-chat"]}
    ]
)

# Use router
response = await router.acompletion(
    model="fast",  # or "reasoning" or "coding"
    messages=[{"role": "user", "content": "Hello"}]
)
```

### Graceful Shutdown

```python
import signal

async def shutdown(signal, loop):
    logger.info("shutdown_initiated", signal=signal.name)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(
        sig, 
        lambda s=sig: asyncio.create_task(shutdown(s, loop))
    )
```

## Next Steps

1. **Add Tool Support** - Implement OpenAI-compatible tool calling
2. **Install MCP Servers** - Add filesystem, github, postgres MCPs
3. **Add Skills** - Install caveman, context-mode, gpt-researcher
4. **Write Tests** - Achieve 80%+ coverage
5. **Deploy** - Set up CI/CD and production environment

## Resources

- **Full Report:** `LYRA_PRODUCTION_READINESS_REPORT.md`
- **Production Checklist:** `PRODUCTION_READINESS_CHECKLIST.md`
- **TUI Guide:** `TUI_RESEARCH_REPORT.md`
- **Resources Catalog:** `PRODUCTION_READY_RESOURCES.md`

## Troubleshooting

**API Key Issues:**
```bash
# Verify .env is loaded
python -c "from lyra.config.settings import config; print(config.anthropic_api_key)"
```

**Import Errors:**
```bash
# Install in development mode
pip install -e .
```

**Ollama Not Running:**
```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.2
```

---

**Estimated Time to Production-Ready:** 6 weeks following the roadmap in the main report.

**Support:** See community links in `LYRA_PRODUCTION_READINESS_REPORT.md`

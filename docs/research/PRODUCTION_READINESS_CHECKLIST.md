# Lyra Production Readiness Checklist

Comprehensive production readiness patterns for Python TUI-based AI agent systems.

## Table of Contents

1. [Error Handling](#error-handling)
2. [Logging & Observability](#logging--observability)
3. [Configuration Management](#configuration-management)
4. [Testing](#testing)
5. [Production Operations](#production-operations)
6. [Security](#security)
7. [Documentation](#documentation)
8. [Implementation Examples](#implementation-examples)

---

## Error Handling

### Checklist

- [ ] **Global exception handler** for uncaught errors
- [ ] **LLM API failure retry logic** (3 attempts, exponential backoff with jitter)
- [ ] **Tool execution timeout and recovery**
- [ ] **User-friendly error messages** in TUI
- [ ] **Detailed error logging** for debugging
- [ ] **Graceful degradation** when optional features fail
- [ ] **Circuit breaker pattern** for repeated failures
- [ ] **Error classification** (transient vs permanent)

### Key Patterns

**Exponential Backoff with Jitter**
- Base delay: 1 second
- Max retries: 3
- Backoff multiplier: 2x
- Jitter: ±25% randomization
- Max delay cap: 60 seconds

**Error Classification**
- **Transient errors** (retry): Rate limits (429), timeouts, network errors (502, 503, 504)
- **Permanent errors** (fail fast): Authentication (401, 403), bad requests (400), not found (404)

**Libraries**
- `tenacity` - Retry logic with exponential backoff
- `circuitbreaker` - Circuit breaker pattern
- `aiohttp` - Async HTTP with built-in retry

### References
- [Mastering Retry Logic Agents: A Deep Dive into 2025 Best Practices](https://sparkco.ai/blog/mastering-retry-logic-agents-a-deep-dive-into-2025-best-practices)
- [How to Implement Retry Logic for LLM API Failures in 2025](https://markaicode.com/llm-api-retry-logic-implementation/)
- [Retry patterns for LLM API errors in production](https://www.learnwithparam.com/blog/retry-patterns-llm-api-errors-production)
- [AI Agent Error Handling: Best Practices & Patterns for 2025](https://about.fast.io/resources/ai-agent-error-handling/)
- [Backpressure Patterns for LLM Pipelines](https://tianpan.co/blog/2026-04-15-backpressure-llm-pipelines)

---

## Logging & Observability

### Checklist

- [ ] **Structured logging** with JSON format
- [ ] **Log rotation and retention** policy (7-30 days)
- [ ] **TUI-compatible logging** (separate log file, no stdout pollution)
- [ ] **Performance metrics** (latency, token usage, cost tracking)
- [ ] **Request tracing** with correlation IDs
- [ ] **Debug mode** for verbose logging
- [ ] **Log levels** properly configured (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [ ] **Sensitive data redaction** in logs (API keys, user data)

### Key Patterns

**TUI Logging Strategy**
- Use file-based logging (avoid stdout/stderr)
- Textual's `Log` widget for in-app display
- Separate debug log file for troubleshooting
- Structured JSON logs for production

**Metrics to Track**
- LLM API latency (p50, p95, p99)
- Token usage per request
- Cost per interaction
- Tool execution time
- Error rates by type
- Memory usage over time

**Libraries**
- `structlog` - Structured logging with context
- `loguru` - Simplified logging with rotation
- `python-json-logger` - JSON formatter for standard logging
- `opentelemetry` - Distributed tracing and metrics

### References
- [Textual Logger API](https://textual.textualize.io/api/logger/)
- [Textual Log Widget](https://textual.textualize.io/widgets/log/)
- [Python Logging Best Practices](https://signoz.io/guides/python-logging-best-practices/)
- [structlog on GitHub](https://github.com/hynek/structlog)

---

## Configuration Management

### Checklist

- [ ] **YAML/TOML config file** with validation
- [ ] **Environment variable support** (.env file)
- [ ] **Secure API key storage** (keyring or environment variables)
- [ ] **User preferences persistence** (~/.lyra/config.yaml)
- [ ] **Config schema validation** with Pydantic
- [ ] **Sensible defaults** for all settings
- [ ] **Layered configuration** (defaults → user → environment)
- [ ] **Config reload** without restart (where applicable)

### Key Patterns

**Configuration Hierarchy**
1. Built-in defaults (code)
2. System config (/etc/lyra/config.yaml)
3. User config (~/.lyra/config.yaml)
4. Environment variables (LYRA_*)
5. Command-line arguments

**Secret Management**
- API keys: Environment variables or OS keyring
- Never commit secrets to version control
- Validate required secrets at startup
- Rotate secrets regularly

**Libraries**
- `pydantic` - Config validation with type hints
- `pydantic-settings` - Environment variable integration
- `dynaconf` - Layered configuration management
- `python-dotenv` - .env file support
- `keyring` - Secure credential storage

### References
- [Pydantic BaseSettings vs. Dynaconf](https://leapcell.io/blog/pydantic-basesettings-vs-dynaconf-a-modern-guide-to-application-configuration)
- [Pydantic Settings and dynaconf](https://dasroot.net/posts/2026/01/python-configuration-management-pydantic-settings-dynaconf/)
- [Pydantic Settings Management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Secure Python Credentials with Keyring](https://openillumi.com/en/en-python-keyring-secure-credentials/)

---

## Testing

### Checklist

- [ ] **Unit tests** for core logic (>80% coverage)
- [ ] **Integration tests** for agent workflows
- [ ] **Mocked LLM API responses** for tests
- [ ] **TUI component tests** using Textual's test utilities
- [ ] **CI/CD pipeline** configured (GitHub Actions, GitLab CI)
- [ ] **Pre-commit hooks** for linting and formatting
- [ ] **Snapshot testing** for TUI output
- [ ] **Property-based testing** for complex logic
- [ ] **Performance regression tests**

### Key Patterns

**Testing Strategy**
- Unit tests: Pure functions, utilities, data models
- Integration tests: Agent loops, tool execution, API calls
- E2E tests: Full user workflows in TUI
- Snapshot tests: TUI layout and rendering

**Mocking LLM APIs**
- Use `pytest-mock` for function mocking
- Use `vcrpy` to record/replay HTTP interactions
- Create fixture responses for common scenarios
- Test error handling with mocked failures

**Libraries**
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Mocking utilities
- `pytest-cov` - Coverage reporting
- `vcrpy` - Record/replay HTTP interactions
- `hypothesis` - Property-based testing
- `textual[dev]` - Textual testing utilities

### References
- [Textual Testing Guide](https://textual.textualize.io/guide/testing/)
- [pytest-mock Tutorial](https://www.datacamp.com/tutorial/pytest-mock)
- [Python Testing 101](https://pytest-with-eric.com/introduction/python-testing-strategy/)
- [Mocking Vs. Patching Guide](https://pytest-with-eric.com/mocking/mocking-vs-patching/)

---

## Production Operations

### Checklist

- [ ] **Graceful shutdown** (SIGTERM/SIGINT handling)
- [ ] **Resource cleanup** on exit (file handles, connections, tasks)
- [ ] **Memory leak prevention** (bounded caches, proper cleanup)
- [ ] **Rate limiting** for API calls (respect provider limits)
- [ ] **Version compatibility checks** (Python version, dependencies)
- [ ] **Update notification** mechanism
- [ ] **Health check** endpoint (if applicable)
- [ ] **Crash recovery** (save state, resume on restart)
- [ ] **Background task management** (proper cancellation)

### Key Patterns

**Graceful Shutdown**
- Register signal handlers for SIGTERM and SIGINT
- Cancel all running asyncio tasks
- Wait for in-flight operations to complete (with timeout)
- Close connections and file handles
- Save state before exit

**Memory Management**
- Use bounded caches (LRU with max size)
- Profile memory usage regularly
- Monitor for memory leaks in long-running processes
- Clean up event listeners and callbacks
- Avoid circular references

**Rate Limiting**
- Track API usage per provider
- Implement token bucket or sliding window
- Queue requests when approaching limits
- Backoff when rate limited

### References
- [How to Build a Graceful Shutdown Handler in Python](https://oneuptime.com/blog/post/2025-01-06-python-graceful-shutdown-kubernetes/view)
- [Python Graceful Shutdown Example](https://github.com/wbenny/python-graceful-shutdown)
- [Graceful shutdown of asyncio coroutines](https://stackoverflow.com/questions/37417595/graceful-shutdown-of-asyncio-coroutines)
- [Engineering Strategic Forgetting at Scale](https://tianpan.co/blog/2026-04-14-agent-memory-garbage-collection)
- [Python Memory Profiling with memray](https://github.com/bloomberg/memray)
- [Diagnosing Memory Leaks in Python](https://thelinuxcode.com/diagnosing-and-fixing-memory-leaks-in-python-a-practical-playbook-for-real-services/)

---

## Security

### Checklist

- [ ] **No hardcoded secrets** (API keys, passwords, tokens)
- [ ] **API keys from environment** or keyring
- [ ] **Input validation** for user commands
- [ ] **Safe file system operations** (path traversal prevention)
- [ ] **Dependency vulnerability scanning** (pip-audit, safety)
- [ ] **Secure defaults** (HTTPS only, certificate validation)
- [ ] **Least privilege principle** (minimal permissions)
- [ ] **Audit logging** for sensitive operations

### Key Patterns

**Secret Management**
- Store in environment variables or OS keyring
- Never log secrets (redact in logs)
- Rotate secrets regularly
- Use separate secrets for dev/staging/prod

**Input Validation**
- Validate all user input before processing
- Sanitize file paths (prevent directory traversal)
- Limit input length and complexity
- Escape special characters in shell commands

**Dependency Security**
- Pin exact versions in requirements.txt
- Run `pip-audit` in CI/CD
- Monitor security advisories
- Update dependencies regularly

### References
- [How to Secure API Keys with Python](https://cloudproinc.com.au/index.php/2025/09/20/how-to-secure-api-keys-with-python/)
- [Secure Python Credentials for Automation](https://openillumi.com/en/en-python-keyring-secure-credentials/)

---

## Documentation

### Checklist

- [ ] **Installation guide** (dependencies, setup steps)
- [ ] **Configuration reference** (all settings documented)
- [ ] **Troubleshooting guide** (common issues and solutions)
- [ ] **API documentation** (if exposing APIs)
- [ ] **Contributing guidelines** (for open source)
- [ ] **Changelog** (version history)
- [ ] **Architecture documentation** (system design)
- [ ] **User guide** (how to use the TUI)

---

## Implementation Examples

### 1. Error Handling with Tenacity

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    reraise=True,
)
async def call_llm_api(prompt: str) -> str:
    """Call LLM API with automatic retry on transient errors."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/v1/chat",
            json={"prompt": prompt},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["response"]
```

### 2. Structured Logging with structlog

```python
import structlog
from pathlib import Path

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.WriteLoggerFactory(
        file=Path("~/.lyra/logs/lyra.log").expanduser().open("a")
    ),
)

log = structlog.get_logger()

# Usage
log.info("llm_api_call", prompt_length=len(prompt), model="gpt-4", tokens=150)
log.error("tool_execution_failed", tool="web_search", error=str(e))
```

### 3. Configuration with Pydantic Settings

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from pathlib import Path

class LyraConfig(BaseSettings):
    """Application configuration with validation."""
    
    model_config = SettingsConfigDict(
        env_prefix="LYRA_",
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    # API Keys (from environment or keyring)
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")
    anthropic_api_key: SecretStr = Field(..., description="Anthropic API key")
    
    # Application Settings
    log_level: str = Field("INFO", description="Logging level")
    max_retries: int = Field(3, ge=1, le=10, description="Max API retries")
    timeout: float = Field(30.0, gt=0, description="API timeout in seconds")
    
    # Paths
    config_dir: Path = Field(
        Path.home() / ".lyra",
        description="Configuration directory"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_dir.mkdir(parents=True, exist_ok=True)

# Usage
config = LyraConfig()
```

### 4. Graceful Shutdown Handler

```python
import asyncio
import signal
from typing import Set

class GracefulShutdown:
    """Handle graceful shutdown of async application."""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.tasks: Set[asyncio.Task] = set()
        
    def setup_signal_handlers(self):
        """Register signal handlers for SIGTERM and SIGINT."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.shutdown_event.set()
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()
    
    async def cleanup(self, timeout: float = 10.0):
        """Cancel all tasks and wait for cleanup."""
        # Cancel all running tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete (with timeout)
        if self.tasks:
            await asyncio.wait(self.tasks, timeout=timeout)

# Usage in main application
async def main():
    shutdown = GracefulShutdown()
    shutdown.setup_signal_handlers()
    
    # Start background tasks
    task1 = asyncio.create_task(agent_loop())
    task2 = asyncio.create_task(monitor_loop())
    shutdown.tasks.update([task1, task2])
    
    # Wait for shutdown signal
    await shutdown.wait_for_shutdown()
    
    # Cleanup
    await shutdown.cleanup()
    print("Shutdown complete")
```

### 5. Testing TUI Components with Textual

```python
import pytest
from textual.app import App
from lyra.ui import LyraApp

@pytest.mark.asyncio
async def test_app_startup():
    """Test that the app starts without errors."""
    app = LyraApp()
    async with app.run_test() as pilot:
        # App should be running
        assert app.is_running
        
        # Check initial screen
        assert pilot.app.screen.name == "main"

@pytest.mark.asyncio
async def test_user_input():
    """Test user input handling."""
    app = LyraApp()
    async with app.run_test() as pilot:
        # Type a command
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.press("enter")
        
        # Verify command was processed
        assert "hello" in app.command_history
```

### 6. Mocking LLM API Calls

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_llm_call_success():
    """Test successful LLM API call."""
    mock_response = {"response": "Hello, world!"}
    
    with patch("lyra.llm.call_llm_api", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_response["response"]
        
        result = await call_llm_api("test prompt")
        
        assert result == "Hello, world!"
        mock_call.assert_called_once_with("test prompt")

@pytest.mark.asyncio
async def test_llm_call_retry_on_timeout():
    """Test retry logic on timeout."""
    with patch("lyra.llm.call_llm_api") as mock_call:
        # First two calls timeout, third succeeds
        mock_call.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            "Success",
        ]
        
        result = await call_llm_api("test prompt")
        
        assert result == "Success"
        assert mock_call.call_count == 3
```

### 7. Memory Profiling with memray

```python
# Install: pip install memray

# Profile a function
import memray

with memray.Tracker("output.bin"):
    # Your code here
    result = run_agent_loop()

# Generate report
# memray flamegraph output.bin
```

### 8. Rate Limiting with Token Bucket

```python
import asyncio
import time
from collections import deque

class TokenBucket:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket."""
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # Wait for tokens to become available
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0
            return True

# Usage
rate_limiter = TokenBucket(rate=10, capacity=100)  # 10 requests/sec

async def call_api():
    await rate_limiter.acquire()
    # Make API call
    return await call_llm_api("prompt")
```

### 9. Secure Credential Storage with Keyring

```python
import keyring
from getpass import getpass

def store_api_key(service: str, username: str):
    """Store API key securely in OS keyring."""
    api_key = getpass(f"Enter API key for {service}: ")
    keyring.set_password(service, username, api_key)
    print(f"API key stored securely for {service}")

def get_api_key(service: str, username: str) -> str:
    """Retrieve API key from OS keyring."""
    api_key = keyring.get_password(service, username)
    if not api_key:
        raise ValueError(f"No API key found for {service}")
    return api_key

# Usage
store_api_key("openai", "default")
api_key = get_api_key("openai", "default")
```

### 10. CI/CD Pipeline Example (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    
    - name: Run linters
      run: |
        ruff check .
        mypy src/
    
    - name: Run tests with coverage
      run: |
        pytest --cov=lyra --cov-report=xml --cov-report=term
    
    - name: Check coverage threshold
      run: |
        coverage report --fail-under=80
    
    - name: Security scan
      run: |
        pip-audit
        bandit -r src/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
```

---

## Quick Start Checklist

Use this condensed checklist for rapid production readiness assessment:

### Critical (Must Have)
- [ ] Error handling with retry logic
- [ ] Structured logging to file
- [ ] Configuration validation
- [ ] Graceful shutdown
- [ ] No hardcoded secrets
- [ ] Unit tests (>80% coverage)

### Important (Should Have)
- [ ] Rate limiting
- [ ] Memory profiling
- [ ] Integration tests
- [ ] CI/CD pipeline
- [ ] Documentation

### Nice to Have
- [ ] Distributed tracing
- [ ] Performance metrics
- [ ] Snapshot testing
- [ ] Auto-update mechanism

---

## Additional Resources

### Tools
- **Linting**: `ruff`, `pylint`, `flake8`
- **Type Checking**: `mypy`, `pyright`
- **Formatting**: `black`, `isort`
- **Security**: `bandit`, `pip-audit`, `safety`
- **Profiling**: `memray`, `py-spy`, `scalene`

### Documentation
- [Textual Documentation](https://textual.textualize.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [structlog Documentation](https://www.structlog.org/)

### Production Guides
- [Going to production - LangChain](https://docs.langchain.com/oss/python/deepagents/going-to-production)
- [Python Logging Best Practices](https://signoz.io/guides/python-logging-best-practices/)
- [Unix Signals and Graceful Shutdown Patterns](https://www.iamraghuveer.com/posts/linux-signals-graceful-shutdown/)

---

## License

This checklist is provided as-is for production readiness assessment of Python TUI-based AI agent systems.


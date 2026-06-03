# Provider Abstraction System — Implementation Guide

## Executive Summary

This guide covers implementing new provider adapters, configuring existing providers, deployment strategies, integration patterns, and testing approaches. Implementation of a new adapter typically takes 10-16 hours for a developer familiar with the provider's API.

---

## Quick Start

### Using Existing Providers

**1. Configure API keys:**

```bash
# Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export DEEPSEEK_API_KEY="sk-..."
```

**2. Initialize provider:**

```python
from lyra_provider import AnthropicProvider, ProviderConfig

config = ProviderConfig(
    provider="anthropic",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_retries=3,
    timeout_seconds=120.0,
)

provider = AnthropicProvider(config)
```

**3. Send request:**

```python
from lyra_provider import ChatRequest, Message, MessageRole

request = ChatRequest(
    messages=[
        Message(role=MessageRole.USER, content="Hello, Claude!")
    ],
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
)

response = await provider.chat(request)
print(response.content)
```

### Basic Streaming

```python
request = ChatRequest(
    messages=[Message(role=MessageRole.USER, content="Count to 5")],
    model="claude-sonnet-4-20250514",
    stream=True,
)

async for event in provider.chat_stream(request):
    if event.type == "text_delta":
        print(event.content, end="", flush=True)
    elif event.type == "done":
        print(f"\n\nTokens: {event.usage.input_tokens} in, {event.usage.output_tokens} out")
```

---

## Implementing a New Provider Adapter

### Step 1: Understand Provider API

**Research checklist:**

```markdown
- [ ] API base URL
- [ ] Authentication method (API key, OAuth, IAM)
- [ ] Message format (roles, content structure)
- [ ] Tool calling format (if supported)
- [ ] Streaming protocol (SSE, WebSocket, HTTP chunks)
- [ ] Token accounting fields
- [ ] Error codes and retry semantics
- [ ] Rate limits and concurrency
- [ ] Context window sizes per model
```

**Example research for fictional "AcmeAI" provider:**

```python
# AcmeAI API research notes
BASE_URL = "https://api.acme.ai/v1"
AUTH = "Bearer token in Authorization header"

MESSAGE_FORMAT = {
    "role": "user" | "assistant" | "system",
    "content": "text string",
    # Tools: separate "function_calls" array
}

STREAMING = "Server-Sent Events (SSE)"
CONTEXT_WINDOW = 100_000  # tokens
RATE_LIMIT = 60  # requests per minute
```

### Step 2: Create Adapter File

**File structure:**

```python
# packages/lyra-provider/src/lyra_provider/adapters/acmeai.py

"""
AcmeAI provider adapter.

Handles:
- Message format: Lyra Message → AcmeAI format
- Tool schema: Lyra ToolSchema → AcmeAI function format
- Streaming: AcmeAI SSE → Lyra StreamEvent
- Usage: AcmeAI tokens → Lyra LLMUsage
- Errors: AcmeAI errors → Lyra ProviderError
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator

from ..interface import (
    AbstractProvider,
    ChatRequest,
    ChatResponse,
    ErrorCode,
    LLMUsage,
    Message,
    MessageRole,
    ProviderConfig,
    ProviderError,
    StreamEvent,
    ToolCall,
    ToolSchema,
)

logger = logging.getLogger(__name__)
```

### Step 3: Implement Translation Functions

**Message translation:**

```python
def _to_acmeai_message(msg: Message) -> dict[str, Any]:
    """Convert Lyra Message to AcmeAI format."""
    if msg.role == MessageRole.TOOL:
        # AcmeAI uses "function_result" role
        return {
            "role": "function_result",
            "function_id": msg.tool_result.tool_call_id if msg.tool_result else "",
            "content": msg.content,
        }
    
    if msg.role == MessageRole.ASSISTANT and msg.tool_calls:
        # Tool calls in separate array
        return {
            "role": "assistant",
            "content": msg.content or "",
            "function_calls": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments),
                }
                for tc in msg.tool_calls
            ],
        }
    
    # Standard message
    return {
        "role": msg.role.value,
        "content": msg.content,
    }


def _from_acmeai_message(acmeai_msg: dict[str, Any]) -> Message:
    """Convert AcmeAI response to Lyra format."""
    role = MessageRole.ASSISTANT  # AcmeAI only returns assistant messages
    content = acmeai_msg.get("content", "")
    
    # Extract tool calls if present
    tool_calls = None
    if "function_calls" in acmeai_msg:
        tool_calls = [
            ToolCall(
                id=fc["id"],
                name=fc["name"],
                arguments=json.loads(fc["arguments"]),
            )
            for fc in acmeai_msg["function_calls"]
        ]
    
    return Message(
        role=role,
        content=content,
        tool_calls=tool_calls,
    )
```

**Tool translation:**

```python
def _to_acmeai_tool(tool: ToolSchema) -> dict[str, Any]:
    """Convert Lyra ToolSchema to AcmeAI function format."""
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,  # AcmeAI uses JSON Schema directly
    }
```

**Usage translation:**

```python
def _from_acmeai_usage(usage_data: dict[str, Any]) -> LLMUsage:
    """Convert AcmeAI usage to Lyra format."""
    return LLMUsage(
        input_tokens=usage_data.get("prompt_tokens", 0),
        output_tokens=usage_data.get("completion_tokens", 0),
        # AcmeAI doesn't support caching
        cache_read_tokens=0,
        cache_write_tokens=0,
    )
```

### Step 4: Implement AbstractProvider

**Basic structure:**

```python
class AcmeAIProvider(AbstractProvider):
    """AcmeAI provider adapter."""
    
    _CONTEXT_WINDOWS = {
        "acme-fast": 50_000,
        "acme-smart": 100_000,
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = config.base_url or "https://api.acme.ai/v1"
    
    @property
    def provider_name(self) -> str:
        return "acmeai"
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send chat request to AcmeAI."""
        start = time.perf_counter()
        
        # Build request body
        body = {
            "model": request.model,
            "messages": [_to_acmeai_message(m) for m in request.messages],
            "max_tokens": request.max_tokens,
        }
        
        if request.tools:
            body["functions"] = [_to_acmeai_tool(t) for t in request.tools]
        
        if request.temperature is not None:
            body["temperature"] = request.temperature
        
        # Send HTTP request
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
        
        except Exception as e:
            raise self._translate_error(e)
        
        elapsed = (time.perf_counter() - start) * 1000
        
        # Parse response
        message = data["choices"][0]["message"]
        lyra_message = _from_acmeai_message(message)
        
        return ChatResponse(
            content=lyra_message.content,
            model=data.get("model", request.model),
            usage=_from_acmeai_usage(data.get("usage", {})),
            tool_calls=lyra_message.tool_calls,
            finish_reason=data["choices"][0].get("finish_reason", "stop"),
            latency_ms=elapsed,
            provider="acmeai",
            raw=data,
        )
    
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        """Stream chat response from AcmeAI."""
        # Implementation similar to chat() but with streaming
        # See Step 5 below
        ...
    
    async def validate_api_key(self) -> bool:
        """Validate API key by making lightweight request."""
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def list_models(self) -> list[str]:
        """Return known AcmeAI model IDs."""
        return list(self._CONTEXT_WINDOWS.keys())
    
    def supports_feature(self, feature: str) -> bool:
        """Check feature support."""
        return feature in {"tool_calling", "streaming"}
    
    def get_context_window(self, model: str) -> int:
        """Return context window for model."""
        return self._CONTEXT_WINDOWS.get(model, 50_000)
    
    @staticmethod
    def _translate_error(error: Exception) -> ProviderError:
        """Translate AcmeAI errors to Lyra taxonomy."""
        msg = str(error).lower()
        
        if "401" in msg or "unauthorized" in msg:
            return ProviderError(
                code=ErrorCode.AUTH_ERROR,
                message=str(error),
                provider="acmeai",
                retryable=False,
            )
        
        if "429" in msg:
            return ProviderError(
                code=ErrorCode.RATE_LIMIT,
                message=str(error),
                provider="acmeai",
                retryable=True,
            )
        
        return ProviderError(
            code=ErrorCode.UNKNOWN,
            message=str(error),
            provider="acmeai",
        )
```

### Step 5: Implement Streaming

**Streaming pattern:**

```python
async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
    """Stream chat response from AcmeAI."""
    body = {
        "model": request.model,
        "messages": [_to_acmeai_message(m) for m in request.messages],
        "max_tokens": request.max_tokens,
        "stream": True,
    }
    
    if request.tools:
        body["functions"] = [_to_acmeai_tool(t) for t in request.tools]
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=body,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            ) as response:
                response.raise_for_status()
                
                # Track tool call accumulation
                current_tool = None
                
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    
                    # Text content
                    if "content" in delta:
                        yield StreamEvent(
                            type="text_delta",
                            content=delta["content"],
                        )
                    
                    # Tool call start
                    if "function_call" in delta and "id" in delta["function_call"]:
                        current_tool = {
                            "id": delta["function_call"]["id"],
                            "name": delta["function_call"]["name"],
                            "arguments": "",
                        }
                        yield StreamEvent(
                            type="tool_call_start",
                            tool_call=ToolCall(
                                id=current_tool["id"],
                                name=current_tool["name"],
                                arguments={},
                            ),
                        )
                    
                    # Tool call arguments delta
                    if "function_call" in delta and "arguments" in delta["function_call"]:
                        if current_tool:
                            current_tool["arguments"] += delta["function_call"]["arguments"]
                    
                    # Tool call end (finish_reason signals completion)
                    finish_reason = chunk.get("choices", [{}])[0].get("finish_reason")
                    if finish_reason == "function_call" and current_tool:
                        try:
                            args = json.loads(current_tool["arguments"])
                        except json.JSONDecodeError:
                            args = 
                        
                        yield StreamEvent(
                            type="tool_call_end",
                            tool_call=ToolCall(
                                id=current_tool["id"],
                                name=current_tool["name"],
                                arguments=args,
                            ),
                        )
                        current_tool = None
                    
                    # Done (usage in final chunk)
                    if "usage" in chunk:
                        yield StreamEvent(
                            type="done",
                            usage=_from_acmeai_usage(chunk["usage"]),
                        )
    
    except Exception as e:
        yield StreamEvent(type="error", error=str(e))
```

### Step 6: Register in Package

**Update `__init__.py`:**

```python
# packages/lyra-provider/src/lyra_provider/adapters/__init__.py

from .acmeai import AcmeAIProvider
from .anthropic import AnthropicProvider
from .deepseek import DeepSeekProvider
from .google import GoogleProvider
from .openai import OpenAIProvider

__all__ = [
    "AcmeAIProvider",
    "AnthropicProvider",
    "DeepSeekProvider",
    "GoogleProvider",
    "OpenAIProvider",
]
```

### Step 7: Update Capability Matrix

```python
# packages/lyra-provider/src/lyra_provider/capability.py

def _register_builtins(self) -> None:
    # ... existing providers ...
    
    self._capabilities["acmeai"] = ProviderCapability(
        provider="acmeai",
        tool_calling=True,
        json_mode=False,
        vision=False,
        streaming=True,
        prompt_caching=False,
        reasoning_budget=False,
        max_context_tokens=100_000,
        concurrent_limit=60,
        notes="AcmeAI provider with 100K context window.",
    )
```

### Step 8: Write Tests

```python
# packages/lyra-provider/tests/test_acmeai.py

import pytest
from lyra_provider import (
    AcmeAIProvider,
    ChatRequest,
    Message,
    MessageRole,
    ProviderConfig,
)


@pytest.fixture
def provider():
    config = ProviderConfig(
        provider="acmeai",
        api_key="test-key",
        base_url="https://api.acme.ai/v1",
    )
    return AcmeAIProvider(config)


@pytest.mark.asyncio
async def test_chat_basic(provider, mock_httpx):
    """Test basic chat completion."""
    mock_httpx.post.return_value.json.return_value = {
        "choices": [{
            "message": {"role": "assistant", "content": "Hello!"},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "model": "acme-smart",
    }
    
    request = ChatRequest(
        messages=[Message(role=MessageRole.USER, content="Hi")],
        model="acme-smart",
    )
    
    response = await provider.chat(request)
    
    assert response.content == "Hello!"
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 5


@pytest.mark.asyncio
async def test_streaming(provider, mock_httpx):
    """Test streaming chat completion."""
    mock_httpx.stream.return_value.__aenter__.return_value.aiter_lines.return_value = [
        "data: {\"choices\": [{\"delta\": {\"content\": \"Hello\"}}]}",
        "data: {\"choices\": [{\"delta\": {\"content\": \" world\"}}]}",
        "data: {\"choices\": [{\"finish_reason\": \"stop\"}], \"usage\": {\"prompt_tokens\": 5, \"completion_tokens\": 2}}",
        "data: [DONE]",
    ]
    
    request = ChatRequest(
        messages=[Message(role=MessageRole.USER, content="Hi")],
        model="acme-smart",
        stream=True,
    )
    
    events = []
    async for event in provider.chat_stream(request):
        events.append(event)
    
    assert len(events) == 3
    assert events[0].type == "text_delta"
    assert events[0].content == "Hello"
    assert events[1].type == "text_delta"
    assert events[1].content == " world"
    assert events[2].type == "done"
```

---

## Configuration

### Environment Variables

**Standard configuration:**

```bash
# Required: API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export DEEPSEEK_API_KEY="sk-..."

# Optional: Custom endpoints
export ANTHROPIC_BASE_URL="https://custom.anthropic.com/v1"
export OPENAI_BASE_URL="https://custom.openai.com/v1"

# Optional: Timeouts
export LYRA_PROVIDER_TIMEOUT=120
export LYRA_PROVIDER_MAX_RETRIES=3
```

### Programmatic Configuration

```python
from lyra_provider import ProviderConfig, AnthropicProvider

# Basic configuration
config = ProviderConfig(
    provider="anthropic",
    api_key=os.environ["ANTHROPIC_API_KEY"],
)

# Advanced configuration
config = ProviderConfig(
    provider="anthropic",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    base_url="https://custom.anthropic.com/v1",
    max_retries=5,
    timeout_seconds=180.0,
    max_concurrent=100,
    extra={
        "anthropic_version": "2023-06-01",
        "custom_header": "value",
    },
)

provider = AnthropicProvider(config)
```

### Multi-Provider Configuration

```python
# Provider registry for routing
providers = {
    "anthropic": AnthropicProvider(ProviderConfig(
        provider="anthropic",
        api_key=os.environ["ANTHROPIC_API_KEY"],
    )),
    "openai": OpenAIProvider(ProviderConfig(
        provider="openai",
        api_key=os.environ["OPENAI_API_KEY"],
    )),
    "deepseek": DeepSeekProvider(ProviderConfig(
        provider="deepseek",
        api_key=os.environ["DEEPSEEK_API_KEY"],
    )),
}

# Route based on task
async def route_request(request: ChatRequest, task_type: str) -> ChatResponse:
    if task_type == "vision":
        # Use Anthropic for vision tasks
        provider = providers["anthropic"]
    elif task_type == "bulk":
        # Use DeepSeek for cost optimization
        provider = providers["deepseek"]
    else:
        # Default to OpenAI
        provider = providers["openai"]
    
    return await provider.chat(request)
```

---

## Integration Patterns

### 1. Router Integration

```python
from lyra_provider import get_capability_matrix

class ModelRouter:
    def __init__(self, providers: dict[str, AbstractProvider]):
        self.providers = providers
        self.matrix = get_capability_matrix()
    
    async def route(self, request: ChatRequest, requirements: list[str]) -> ChatResponse:
        """Route request to capable provider."""
        # Filter by capabilities
        capable = []
        for name, provider in self.providers.items():
            if all(self.matrix.supports(name, req) for req in requirements):
                capable.append((name, provider))
        
        if not capable:
            raise ValueError(f"No provider supports: {requirements}")
        
        # Try providers in order (first available)
        for name, provider in capable:
            try:
                return await provider.chat(request)
            except ProviderError as e:
                if not e.retryable:
                    raise
                # Try next provider
                continue
        
        raise RuntimeError("All providers failed")
```

### 2. Retry Logic

```python
import asyncio
import random

async def chat_with_exponential_backoff(
    provider: AbstractProvider,
    request: ChatRequest,
    max_retries: int = 3,
) -> ChatResponse:
    """Exponential backoff with jitter."""
    for attempt in range(max_retries):
        try:
            return await provider.chat(request)
        except ProviderError as e:
            if not e.retryable or attempt == max_retries - 1:
                raise
            
            # Exponential backoff: 1s, 2s, 4s with ±25% jitter
            base_delay = 2 ** attempt
            jitter = random.uniform(0.75, 1.25)
            delay = base_delay * jitter
            
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e}")
            await asyncio.sleep(delay)
    
    raise RuntimeError("Unreachable")
```

### 3. Circuit Breaker

```python
from datetime import datetime, timedelta

class CircuitBreaker:
    """Circuit breaker for provider health management."""
    
    def __init__(self, failure_threshold: int = 5, timeout: timedelta = timedelta(minutes=5)):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures: dict[str, list[datetime]] = {}
        self.open_until: dict[str, datetime] = {}
    
    def is_open(self, provider: str) -> bool:
        """Check if circuit is open (provider unhealthy)."""
        if provider in self.open_until:
            if datetime.now() < self.open_until[provider]:
                return True
            # Circuit closed, reset failures
            del self.open_until[provider]
            self.failures[provider] = []
        return False
    
    def record_failure(self, provider: str) -> None:
        """Record provider failure."""
        now = datetime.now()
        
        if provider not in self.failures:
            self.failures[provider] = []
        
        # Add failure
        self.failures[provider].append(now)
        
        # Remove old failures (outside window)
        cutoff = now - self.timeout
        self.failures[provider] = [f for f in self.failures[provider] if f > cutoff]
        
        # Open circuit if threshold exceeded
        if len(self.failures[provider]) >= self.failure_threshold:
            self.open_until[provider] = now + self.timeout
    
    def record_success(self, provider: str) -> None:
        """Record provider success (reset failures)."""
        if provider in self.failures:
            self.failures[provider] = []


# Usage
breaker = CircuitBreaker()

async def chat_with_circuit_breaker(
    provider: AbstractProvider,
    request: ChatRequest,
) -> ChatResponse:
    """Chat with circuit breaker protection."""
    if breaker.is_open(provider.provider_name):
        raise RuntimeError(f"Circuit open for {provider.provider_name}")
    
    try:
        response = await provider.chat(request)
        breaker.record_success(provider.provider_name)
        return response
    except ProviderError as e:
        breaker.record_failure(provider.provider_name)
        raise
```

### 4. Caching Layer

```python
import hashlib
import json
from typing import Optional

class ResponseCache:
    """LRU cache for provider responses."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: dict[str, ChatResponse] = {}
        self.max_size = max_size
    
    def _hash_request(self, request: ChatRequest) -> str:
        """Generate cache key from request."""
        key_data = {
            "messages": [(m.role.value, m.content) for m in request.messages],
            "model": request.model,
            "temperature": request.temperature,
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def get(self, request: ChatRequest) -> Optional[ChatResponse]:
        """Get cached response."""
        key = self._hash_request(request)
        return self.cache.get(key)
    
    def set(self, request: ChatRequest, response: ChatResponse) -> None:
        """Cache response."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (simplified LRU)
            self.cache.pop(next(iter(self.cache)))
        
        key = self._hash_request(request)
        self.cache[key] = response


# Usage
cache = ResponseCache()

async def chat_with_cache(
    provider: AbstractProvider,
    request: ChatRequest,
) -> ChatResponse:
    """Chat with response caching."""
    # Check cache
    cached = cache.get(request)
    if cached:
        return cached
    
    # Call provider
    response = await provider.chat(request)
    
    # Cache response
    cache.set(request, response)
    
    return response
```

---

## Testing Strategies

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, Mock
from lyra_provider import AnthropicProvider, ChatRequest, Message, MessageRole


@pytest.fixture
def mock_httpx(monkeypatch):
    """Mock httpx for testing."""
    mock_client = Mock()
    mock_post = AsyncMock()
    mock_client.post = mock_post
    
    async def async_client(*args, **kwargs):
        return mock_client
    
    monkeypatch.setattr("httpx.AsyncClient", async_client)
    return mock_post


@pytest.mark.asyncio
async def test_message_translation():
    """Test message translation accuracy."""
    from lyra_provider.adapters.anthropic import _to_anthropic_message
    
    # Test USER message
    msg = Message(role=MessageRole.USER, content="Hello")
    result = _to_anthropic_message(msg)
    assert result == {"role": "user", "content": "Hello"}
    
    # Test ASSISTANT message with tool calls
    msg = Message(
        role=MessageRole.ASSISTANT,
        content="",
        tool_calls=[ToolCall(id="1", name="search", arguments={"q": "test"})],
    )
    result = _to_anthropic_message(msg)
    assert result["role"] == "assistant"
    assert len(result["content"]) == 1
    assert result["content"][0]["type"] == "tool_use"
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_anthropic_real_api():
    """Test real Anthropic API (requires API key)."""
    config = ProviderConfig(
        provider="anthropic",
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
    
    if not config.api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    
    provider = AnthropicProvider(config)
    
    request = ChatRequest(
        messages=[Message(role=MessageRole.USER, content="Say 'test'")],
        model="claude-haiku-4-20250514",
        max_tokens=10,
    )
    
    response = await provider.chat(request)
    
    assert response.content
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
```

### Performance Tests

```python
import time

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_translation_performance():
    """Benchmark message translation overhead."""
    from lyra_provider.adapters.anthropic import _to_anthropic_message
    
    messages = [
        Message(role=MessageRole.USER, content=f"Message {i}")
        for i in range(100)
    ]
    
    start = time.perf_counter()
    for _ in range(1000):
        [_to_anthropic_message(m) for m in messages]
    elapsed = time.perf_counter() - start
    
    per_message = (elapsed / 1000 / 100) * 1_000_000  # μs
    assert per_message < 1.0, f"Translation too slow: {per_message:.2f}μs per message"
```

---

## Deployment

### Production Checklist

```markdown
- [ ] API keys stored securely (secrets manager, not env vars)
- [ ] Timeouts configured appropriately (120s default)
- [ ] Retry logic enabled (exponential backoff)
- [ ] Circuit breakers for each provider
- [ ] Monitoring and alerting set up
- [ ] Rate limit handling tested
- [ ] Error logging configured
- [ ] Cost tracking implemented
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY packages/lyra-provider /app/lyra-provider
RUN pip install -e /app/lyra-provider

# Run application
CMD ["python", "app.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      LYRA_PROVIDER_TIMEOUT: 120
      LYRA_PROVIDER_MAX_RETRIES: 3
    ports:
      - "8000:8000"
```

### Kubernetes Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lyra-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lyra
  template:
    metadata:
      labels:
        app: lyra
    spec:
      containers:
      - name: app
        image: lyra-app:latest
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: provider-secrets
              key: anthropic-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: provider-secrets
              key: openai-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
```

---

## Key Sources

**Implementation:**
- `packages/lyra-provider/src/lyra_provider/adapters/anthropic.py` — Reference implementation
- `packages/lyra-provider/tests/` — Test examples

**Documentation:**
- `lyra-upgrade/07-architecture-deep-dives/03-provider-abstraction.md` — Architecture details
- `docs/howto/configure-providers.md` — User guide

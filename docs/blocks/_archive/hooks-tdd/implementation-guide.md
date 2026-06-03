# Hooks and TDD Gate — Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing and extending the Hooks and TDD Gate system. It covers built-in hooks, custom hooks, configuration, testing, debugging, and common pitfalls.

## Getting Started

### Prerequisites

```bash
# Install Lyra with TDD support
pip install lyra-agent[tdd]

# Verify installation
lyra doctor --check-hooks
```

Expected output:
```
✓ Hook system: operational
✓ TDD gate: enabled
✓ Test runner: pytest detected
✓ Coverage: coverage.py installed
```

### Project Setup

Initialize TDD support in your project:

```bash
cd /path/to/project
lyra init --enable-tdd

# Creates:
# .lyra/
# ├── config.yaml          # Lyra configuration
# ├── coverage_baseline.json  # Coverage baseline (created on first run)
# └── hooks.yaml           # Custom hook configuration
```

Configuration file (`.lyra/config.yaml`):

```yaml
hooks:
  enabled: true
  
tdd:
  enabled: true
  strict_mode: true           # Block on missing RED proof
  coverage_delta_min: 0.0     # Allow no regression
  test_timeout_s: 300         # Full suite timeout
  
  # File patterns
  source_patterns:
    - "src/**/*.py"
    - "lib/**/*.py"
  
  test_patterns:
    - "tests/**/*.py"
    - "test_*.py"
  
  # Exclusions
  exclude_patterns:
    - "**/__init__.py"
    - "**/migrations/**"
```

## Implementing Built-In Hooks

### 1. TDD Gate Hook

The TDD gate is pre-installed. To customize behavior:

```python
# .lyra/user_hooks/tdd_custom.py
from lyra import Hook, HookEvent, HookContext, HookDecision

@Hook.register(
    HookEvent.PRE_TOOL_USE,
    name="tdd-gate-custom",
    priority=11,  # Run after built-in TDD gate
)
def custom_tdd_gate(context: HookContext) -> HookDecision:
    """
    Custom TDD rules for specific files.
    
    Example: Allow editing generated files without tests.
    """
    if not context.is_editing_source():
        return HookDecision.allow("tdd-gate-custom")
    
    file_path = context.get_tool_arg("file_path")
    
    # Allow generated files
    if "generated" in str(file_path) or "pb.py" in str(file_path):
        return HookDecision.allow(
            "tdd-gate-custom",
            reason="Generated file, no test required"
        )
    
    # Default: defer to built-in TDD gate
    return HookDecision.allow("tdd-gate-custom")
```

### 2. Secrets Scanner Hook

Pre-installed, but you can add project-specific patterns:

```yaml
# .lyra/secrets-allow.yaml
# Allowlist for known safe patterns
allowlist:
  - pattern: "EXAMPLE_API_KEY"
    reason: "Example key in documentation"
    files: ["docs/**/*.md"]
  
  - pattern: "test_key_12345"
    reason: "Test fixture"
    files: ["tests/fixtures/**"]

# Custom secret patterns
custom_patterns:
  - name: "internal-token"
    regex: "INT_[A-Z0-9]{32}"
    entropy_threshold: 4.0
```

### 3. Format-on-Edit Hook

Configure formatters for your project:

```yaml
# .lyra/hooks.yaml
- name: format-python
  event: post.tool.use
  run: |
    ruff format "$FILE_PATH"
    ruff check --fix "$FILE_PATH"
  match:
    tool: [Edit, Write]
    path_glob: "**/*.py"
  env:
    FILE_PATH: "{{file_path}}"
  timeout_s: 10
  non_blocking: true

- name: format-typescript
  event: post.tool.use
  run: prettier --write "$FILE_PATH"
  match:
    tool: [Edit, Write]
    path_glob: "**/*.{ts,tsx,js,jsx}"
  env:
    FILE_PATH: "{{file_path}}"
  timeout_s: 5
  non_blocking: true
```

## Creating Custom Hooks

### Step 1: Define Hook Function

```python
# .lyra/user_hooks/no_console_log.py
from lyra import Hook, HookEvent, HookContext, HookDecision
import re

@Hook.register(
    HookEvent.PRE_TOOL_USE,
    name="no-console-log",
    priority=200,
    timeout_s=5.0,
)
def block_console_log(context: HookContext) -> HookDecision:
    """
    Block console.log in production code.
    
    Rules:
    1. Allow console.log in test files
    2. Allow console.error/warn/info
    3. Block console.log in src/**
    """
    if context.tool_call.name != "Edit":
        return HookDecision.allow("no-console-log")
    
    new_string = context.get_tool_arg("new_string", "")
    file_path = context.get_tool_arg("file_path", "")
    
    # Allow in test files
    if "test" in file_path or "spec" in file_path:
        return HookDecision.allow("no-console-log")
    
    # Check for console.log (but not console.error, etc.)
    if re.search(r'\bconsole\.log\s*\(', new_string):
        return HookDecision.block_(
            "no-console-log",
            reason="console.log found in production code",
            suggestion=(
                "Use a proper logger instead:\n"
                "  import { logger } from '@/lib/logger'\n"
                "  logger.debug('message')"
            ),
        )
    
    return HookDecision.allow("no-console-log")
```

### Step 2: Test Your Hook

```python
# tests/hooks/test_no_console_log.py
import pytest
from lyra import HookContext, HookEvent, ToolCall, Session
from user_hooks.no_console_log import block_console_log

def make_context(file_path: str, new_string: str) -> HookContext:
    """Helper to create test context."""
    return HookContext(
        event=HookEvent.PRE_TOOL_USE,
        session_id="test-session",
        tool_call=ToolCall(
            name="Edit",
            args={
                "file_path": file_path,
                "new_string": new_string,
            },
        ),
        session=Session(project_root="/test"),
    )

def test_blocks_console_log_in_src():
    context = make_context(
        "src/api/users.py",
        "console.log('debug')",
    )
    
    result = block_console_log(context)
    
    assert result.block is True
    assert "console.log" in result.reason

def test_allows_console_error():
    context = make_context(
        "src/api/users.py",
        "console.error('error')",
    )
    
    result = block_console_log(context)
    
    assert result.block is False

def test_allows_console_log_in_tests():
    context = make_context(
        "tests/api/test_users.py",
        "console.log('test output')",
    )
    
    result = block_console_log(context)
    
    assert result.block is False
```

Run tests:

```bash
pytest tests/hooks/test_no_console_log.py -v
```

### Step 3: Register Hook

Hooks in `.lyra/user_hooks/` are auto-loaded. To manually register:

```python
# .lyra/user_hooks/__init__.py
from .no_console_log import block_console_log
from .custom_lint import custom_lint_check

__all__ = ["block_console_log", "custom_lint_check"]
```

### Step 4: Verify Hook Registration

```bash
lyra hooks list

# Output:
# Hooks registered for PRE_TOOL_USE:
#   [0] destructive-pattern (built-in)
#   [10] tdd-gate-pre (built-in)
#   [20] secrets-scan (built-in)
#   [200] no-console-log (user)
```

## Advanced Hook Patterns

### Async Hook with External Service

```python
import httpx
from lyra import Hook, HookEvent, HookContext, HookDecision

@Hook.register(
    HookEvent.POST_TOOL_USE,
    name="security-scan-api",
    priority=150,
    timeout_s=30.0,
    side_effects=["network"],
)
async def security_scan_api(context: HookContext) -> HookDecision:
    """
    Send code to external security scanning API.
    
    This is an async hook that calls an external service.
    """
    if context.tool_call.name not in {"Edit", "Write"}:
        return HookDecision.allow("security-scan-api")
    
    file_path = context.get_tool_arg("file_path")
    content = context.get_tool_arg("new_string") or context.get_tool_arg("content")
    
    if not content:
        return HookDecision.allow("security-scan-api")
    
    # Call external API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.security-scanner.example/scan",
                json={
                    "file_path": str(file_path),
                    "content": content,
                    "language": "python",
                },
                timeout=25.0,
            )
            
            result = response.json()
            
            if result["vulnerabilities"]:
                return HookDecision.warn(
                    "security-scan-api",
                    reason=f"Found {len(result['vulnerabilities'])} vulnerabilities",
                    annotation=format_vulnerabilities(result["vulnerabilities"]),
                )
            
            return HookDecision.allow("security-scan-api")
            
        except httpx.TimeoutException:
            return HookDecision.warn(
                "security-scan-api",
                "Security scan timed out",
            )
        except Exception as e:
            return HookDecision.warn(
                "security-scan-api",
                f"Security scan failed: {e}",
            )
```

### Stateful Hook with Cache

```python
from lyra import Hook, HookEvent, HookContext, HookDecision
from functools import lru_cache
import hashlib

class LintCache:
    """Cache lint results by file content hash."""
    
    def __init__(self):
        self._cache = {}
    
    def get(self, content_hash: str):
        return self._cache.get(content_hash)
    
    def set(self, content_hash: str, result):
        self._cache[content_hash] = result

# Global cache instance
_lint_cache = LintCache()

@Hook.register(
    HookEvent.POST_TOOL_USE,
    name="cached-lint",
    priority=45,
    timeout_s=30.0,
)
async def cached_lint(context: HookContext) -> HookDecision:
    """
    Run linter with caching.
    
    Cache lint results by file content hash to avoid
    redundant linting of unchanged content.
    """
    if context.tool_call.name not in {"Edit", "Write"}:
        return HookDecision.allow("cached-lint")
    
    file_path = context.get_tool_arg("file_path")
    content = context.get_tool_arg("new_string") or context.get_tool_arg("content")
    
    # Compute content hash
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    
    # Check cache
    cached_result = _lint_cache.get(content_hash)
    if cached_result:
        return cached_result
    
    # Run linter
    result = await run_linter(file_path, content)
    
    # Build decision
    if result.errors:
        decision = HookDecision.warn(
            "cached-lint",
            reason=f"Found {len(result.errors)} lint errors",
            annotation=format_lint_errors(result.errors),
        )
    else:
        decision = HookDecision.allow("cached-lint")
    
    # Cache result
    _lint_cache.set(content_hash, decision)
    
    return decision
```

### Hook with Session State

```python
from lyra import Hook, HookEvent, HookContext, HookDecision

@Hook.register(
    HookEvent.POST_TOOL_USE,
    name="track-file-edits",
    priority=250,
)
def track_file_edits(context: HookContext) -> HookDecision:
    """
    Track which files have been edited in this session.
    
    Use session metadata to maintain state.
    """
    if context.tool_call.name not in {"Edit", "Write"}:
        return HookDecision.allow("track-file-edits")
    
    file_path = context.get_tool_arg("file_path")
    
    # Get or initialize tracking set
    edited_files = context.session.metadata.get("edited_files", set())
    edited_files.add(str(file_path))
    context.session.metadata["edited_files"] = edited_files
    
    # Warn if too many files edited
    if len(edited_files) > 20:
        return HookDecision.warn(
            "track-file-edits",
            reason=f"Edited {len(edited_files)} files in this session",
            suggestion="Consider splitting this into multiple smaller sessions",
        )
    
    return HookDecision.allow("track-file-edits")
```

## Configuration

### Hook Priority Planning

| Priority Range | Purpose | Examples |
|----------------|---------|----------|
| 0-9 | Critical safety | Destructive patterns |
| 10-19 | Quality gates | TDD gate |
| 20-39 | Security | Secrets, injection detection |
| 40-59 | Code quality | Format, lint, typecheck |
| 60-99 | Observability | Metrics, tracing |
| 100-199 | User hooks (blocking) | Project-specific rules |
| 200+ | User hooks (advisory) | Warnings, suggestions |

### Timeout Configuration

```yaml
# .lyra/config.yaml
hooks:
  default_timeout_s: 10
  
  timeouts:
    # Override per hook
    tdd-gate-pre: 5
    tdd-gate-post: 30
    tdd-gate-stop: 300
    security-scan-api: 30
    format-on-edit: 10
```

### Environment Variables

```bash
# Disable all hooks (emergency escape hatch)
export LYRA_HOOKS_DISABLED=1

# Disable specific hooks
export LYRA_HOOKS_DISABLED_LIST="no-console-log,security-scan-api"

# Enable hook debug logging
export LYRA_HOOKS_DEBUG=1

# Increase TDD timeout for large projects
export LYRA_TDD_STOP_TIMEOUT=600
```

## Testing

### Unit Testing Hooks

```python
# tests/hooks/test_hook_example.py
import pytest
from lyra import HookContext, HookEvent, ToolCall, Session
from user_hooks.my_hook import my_hook_function

@pytest.fixture
def mock_session():
    """Create mock session for testing."""
    return Session(
        session_id="test-session",
        project_root="/test/project",
        metadata={},
    )

@pytest.fixture
def edit_context(mock_session):
    """Create context for Edit tool call."""
    return lambda file_path, content: HookContext(
        event=HookEvent.PRE_TOOL_USE,
        session_id="test-session",
        tool_call=ToolCall(
            name="Edit",
            args={
                "file_path": file_path,
                "new_string": content,
            },
        ),
        session=mock_session,
    )

def test_hook_blocks_invalid_content(edit_context):
    context = edit_context("src/api.py", "invalid content")
    result = my_hook_function(context)
    
    assert result.block is True
    assert "invalid" in result.reason.lower()

def test_hook_allows_valid_content(edit_context):
    context = edit_context("src/api.py", "valid content")
    result = my_hook_function(context)
    
    assert result.block is False
```

### Integration Testing

```python
# tests/integration/test_hooks_e2e.py
import pytest
from lyra import Lyra, Session

@pytest.mark.integration
async def test_tdd_gate_workflow():
    """
    Test complete TDD workflow with hooks.
    
    1. Try to edit without test → blocked
    2. Write failing test → allowed
    3. Edit implementation → allowed
    4. Tests pass → complete session
    """
    lyra = Lyra(project_root="/test/project")
    session = await lyra.start_session()
    
    # Try to edit without test (should block)
    result = await session.execute_tool({
        "name": "Edit",
        "args": {
            "file_path": "src/api.py",
            "old_string": "def old():\n    pass",
            "new_string": "def new():\n    return 42",
        },
    })
    
    assert result.success is False
    assert "failing test" in result.error.lower()
    
    # Write failing test (should succeed)
    result = await session.execute_tool({
        "name": "Write",
        "args": {
            "file_path": "tests/test_api.py",
            "content": "def test_new():\n    assert new() == 42",
        },
    })
    
    assert result.success is True
    
    # Run test (should fail - RED)
    result = await session.execute_tool({
        "name": "Bash",
        "args": {"command": "pytest tests/test_api.py -v"},
    })
    
    assert result.exit_code != 0
    
    # Now edit implementation (should succeed)
    result = await session.execute_tool({
        "name": "Edit",
        "args": {
            "file_path": "src/api.py",
            "old_string": "def old():\n    pass",
            "new_string": "def new():\n    return 42",
        },
    })
    
    assert result.success is True
    
    # Complete session (should pass STOP gate)
    result = await session.complete()
    
    assert result.success is True
```

## Debugging

### Enable Hook Debug Logging

```bash
export LYRA_HOOKS_DEBUG=1
lyra start

# Output includes:
# [hook] Dispatching PRE_TOOL_USE for Edit
# [hook] Executing tdd-gate-pre (priority=10)
# [hook] Result: block=True, reason="No failing test found"
```

### Hook Execution Trace

```bash
# View hook execution history
lyra trace --filter=hooks --last=10

# Output:
# 12:00:01 hook:tdd-gate-pre         BLOCK  8ms   "No failing test"
# 12:00:15 hook:tdd-gate-pre         ALLOW  5ms   "RED proof found"
# 12:00:16 hook:tdd-gate-post        ALLOW  2.3s  "Tests passed"
```

### Common Issues

#### Issue 1: Hook Not Executing

**Symptom**: Hook defined but not running.

**Debug**:
```bash
# Check registration
lyra hooks list | grep my-hook

# Check for import errors
python -c "from user_hooks.my_hook import *"

# Check priority conflicts
lyra hooks list --verbose
```

**Solution**:
- Ensure hook file is in `.lyra/user_hooks/`
- Verify `@Hook.register` decorator syntax
- Check for Python import errors
- Ensure unique hook name

#### Issue 2: Hook Timeout

**Symptom**: Hook times out repeatedly.

**Debug**:
```bash
# Check timeout value
lyra hooks describe my-hook

# Test hook in isolation
python -m lyra.test_hook user_hooks.my_hook --timeout=60
```

**Solution**:
```python
# Increase timeout
@Hook.register(
    HookEvent.POST_TOOL_USE,
    name="my-slow-hook",
    timeout_s=60.0,  # Increase from default 10s
)
async def my_slow_hook(context):
    ...
```

#### Issue 3: Hook False Positives

**Symptom**: Hook blocks valid operations.

**Debug**:
```bash
# Check last hook decision
lyra hooks last-decision my-hook

# Test hook with specific input
lyra hooks test my-hook --input=test_case.json
```

**Solution**:
- Add allowlist patterns
- Refine detection logic
- Lower priority or make advisory (non-blocking)

#### Issue 4: TDD Gate Too Strict

**Symptom**: Blocked when editing non-test-worthy files.

**Solution**:
```yaml
# .lyra/config.yaml
tdd:
  exclude_patterns:
    - "**/migrations/**"
    - "**/__init__.py"
    - "**/generated/**"
    - "**/proto/**"
```

## Common Pitfalls

### ❌ Pitfall 1: Mutating Context

```python
# WRONG: Mutating context
def bad_hook(context: HookContext) -> HookDecision:
    context.session.metadata["foo"] = "bar"  # ❌ Mutates frozen object
    return HookDecision.allow("bad-hook")
```

```python
# CORRECT: Use session methods
def good_hook(context: HookContext) -> HookDecision:
    context.session.set_metadata("foo", "bar")  # ✅ Proper mutation
    return HookDecision.allow("good-hook")
```

### ❌ Pitfall 2: Blocking Too Aggressively

```python
# WRONG: Block on warnings
def bad_hook(context: HookContext) -> HookDecision:
    if minor_style_issue(context):
        return HookDecision.block_("bad-hook", "Style issue")  # ❌ Too strict
```

```python
# CORRECT: Warn instead of block
def good_hook(context: HookContext) -> HookDecision:
    if minor_style_issue(context):
        return HookDecision.warn("good-hook", "Style issue")  # ✅ Advisory
```

### ❌ Pitfall 3: Expensive Sync Operations

```python
# WRONG: Blocking operation in sync hook
def bad_hook(context: HookContext) -> HookDecision:
    result = requests.get("https://api.example.com/check")  # ❌ Blocks event loop
    return HookDecision.allow("bad-hook")
```

```python
# CORRECT: Use async hook
async def good_hook(context: HookContext) -> HookDecision:
    async with httpx.AsyncClient() as client:
        result = await client.get("https://api.example.com/check")  # ✅ Non-blocking
    return HookDecision.allow("good-hook")
```

### ❌ Pitfall 4: No Error Handling

```python
# WRONG: Unhandled exceptions
def bad_hook(context: HookContext) -> HookDecision:
    data = parse_json(context.get_tool_arg("content"))  # ❌ May throw
    return HookDecision.allow("bad-hook")
```

```python
# CORRECT: Handle errors gracefully
def good_hook(context: HookContext) -> HookDecision:
    try:
        data = parse_json(context.get_tool_arg("content"))
    except json.JSONDecodeError as e:
        return HookDecision.warn("good-hook", f"Invalid JSON: {e}")
    return HookDecision.allow("good-hook")
```

### ❌ Pitfall 5: Ignoring Tool Type

```python
# WRONG: Assuming tool is always Edit
def bad_hook(context: HookContext) -> HookDecision:
    file_path = context.get_tool_arg("file_path")  # ❌ May be None for other tools
    if "test" in file_path:  # ❌ Crashes if file_path is None
        ...
```

```python
# CORRECT: Check tool type first
def good_hook(context: HookContext) -> HookDecision:
    if context.tool_call.name not in {"Edit", "Write"}:
        return HookDecision.allow("good-hook")
    
    file_path = context.get_tool_arg("file_path")
    if file_path and "test" in str(file_path):
        ...
```

## Performance Optimization

### Benchmark Your Hook

```python
# tests/benchmarks/bench_hook.py
import pytest
from lyra import HookContext
from user_hooks.my_hook import my_hook

@pytest.mark.benchmark
def test_hook_performance(benchmark):
    context = make_test_context()
    result = benchmark(my_hook, context)
    
    assert result.block is False

# Run benchmark
pytest tests/benchmarks/bench_hook.py --benchmark-only

# Target: <10ms for simple hooks, <100ms for complex hooks
```

### Optimization Techniques

1. **Cache expensive computations**:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_check(content_hash: str) -> bool:
    # Expensive operation
    return result
```

2. **Early returns**:
```python
def optimized_hook(context: HookContext) -> HookDecision:
    # Fast path: allow non-Edit tools immediately
    if context.tool_call.name != "Edit":
        return HookDecision.allow("optimized-hook")
    
    # Only do expensive checks if necessary
    ...
```

3. **Async for I/O**:
```python
async def optimized_hook(context: HookContext) -> HookDecision:
    # Use async for I/O operations
    async with aiofiles.open(file_path) as f:
        content = await f.read()
```

## Next Steps

- **[Deep Dive](deep-dive.md)**: Advanced patterns and optimizations
- **[Architecture](architecture.md)**: System internals
- **[System Design](system-design.md)**: API contracts and abstractions

# Agent Loop Implementation Guide

**Block:** 01 — Agent Loop  
**Status:** Production  
**Version:** 2.7.1

---

## Overview

This guide provides step-by-step instructions for implementing, configuring, testing, and debugging the agent loop. Includes code examples, configuration patterns, common pitfalls, and troubleshooting strategies.

## Getting Started

### Prerequisites

```bash
# Python 3.11+ required
python --version

# Install dependencies
pip install lyra-core>=2.7.0

# Verify installation
python -c "from lyra_core.loop import agent_loop; print('OK')"
```

### Basic Setup

```python
from lyra_core.loop import agent_loop
from lyra_core.session import Session, SessionConfig, Budgets
from lyra_core.permission import PermissionMode

# 1. Create session
session = Session(
    id="demo-session",
    task="Add unit tests for user authentication",
    model_selection=ModelSelection(
        fast="deepseek-v4-flash",
        smart="deepseek-v4-pro",
    ),
    permission_mode=PermissionMode.AUTO_EDIT,
    budgets=Budgets(
        max_tokens=100_000,
        max_cost_usd=5.0,
        max_steps=1000,
    ),
    config=SessionConfig(
        tdd_enabled=True,
        safety_checks=True,
        hooks_enabled=True,
    ),
)

# 2. Run loop
result = agent_loop(session, task="Add unit tests for user authentication")

# 3. Handle result
if result.status == TerminationStatus.COMPLETED:
    print(f"✓ Task completed in {result.step} steps")
    print(f"  Cost: ${result.session.cost_usd:.2f}")
else:
    print(f"✗ Task ended: {result.status}")
    print(f"  Reason: {result.reason}")
```

---

## Step-by-Step Implementation

### Step 1: Session Configuration

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SessionConfig:
    """Session-level configuration."""
    
    # TDD settings
    tdd_enabled: bool = False
    tdd_phase: str = "IDLE"  # IDLE | PLAN | RED | GREEN | REFACTOR | SHIP
    
    # Safety settings
    safety_checks: bool = True
    safety_check_interval: int = 10  # Check every N steps
    
    # Hook settings
    hooks_enabled: bool = True
    hook_timeout_ms: int = 5000  # Max hook execution time
    
    # Context settings
    compaction_threshold: float = 0.85  # Trigger at 85% capacity
    keep_window: int = 5  # Preserve recent N turns
    
    # Persistence settings
    persist_every_step: bool = True
    session_dir: Path = Path(".lyra/sessions")
    
    # Retry settings
    max_tool_retries: int = 3
    retry_backoff_ms: int = 100  # Base backoff time

# Example configurations

# Development mode (fast iteration)
dev_config = SessionConfig(
    tdd_enabled=False,
    safety_checks=False,  # Disable for speed
    compaction_threshold=0.90,  # Less aggressive
)

# Production mode (safe, thorough)
prod_config = SessionConfig(
    tdd_enabled=True,
    safety_checks=True,
    safety_check_interval=5,  # More frequent
    compaction_threshold=0.80,  # More aggressive
)

# Testing mode (reproducible)
test_config = SessionConfig(
    tdd_enabled=True,
    safety_checks=False,  # Use mock safety
    persist_every_step=False,  # In-memory only
)
```

### Step 2: Context Engine Integration

```python
from lyra_core.context import ContextEngine
from lyra_core.transcript import Transcript, Message

class SimpleContextEngine(ContextEngine):
    """Minimal context engine implementation."""
    
    def assemble(
        self,
        session: Session,
        task: str,
        plan: Plan | None = None,
    ) -> Transcript:
        """Build initial transcript."""
        
        messages = []
        
        # 1. System prompt
        system = self._build_system_prompt(session)
        messages.append(Message(role="system", content=system))
        
        # 2. Load SOUL.md if exists
        soul_path = Path("SOUL.md")
        if soul_path.exists():
            soul = soul_path.read_text()
            messages.append(Message(role="system", content=f"# Project Persona\n{soul}"))
        
        # 3. Include plan if provided
        if plan:
            plan_summary = self._summarize_plan(plan)
            messages.append(Message(role="system", content=f"# Plan\n{plan_summary}"))
        
        # 4. User task
        messages.append(Message(role="user", content=task))
        
        return Transcript(messages=messages)
    
    def compact(
        self,
        transcript: Transcript,
        session: Session,
    ) -> Transcript:
        """Summarize old turns, preserve recent."""
        
        keep = session.config.keep_window
        
        # Split into old and recent
        old_messages = transcript.messages[:-keep]
        recent_messages = transcript.messages[-keep:]
        
        # Summarize old messages via LLM
        summary = self._summarize_messages(old_messages, session)
        summary_msg = Message(
            role="system",
            content=f"# Previous conversation summary\n{summary}",
        )
        
        # Rebuild transcript
        system_msg = transcript.messages[0]  # Preserve system prompt
        return Transcript(messages=[system_msg, summary_msg] + recent_messages)
    
    def reduce(
        self,
        result: ToolResult,
        session: Session,
    ) -> Observation:
        """Truncate large outputs."""
        
        content = result.content
        max_tokens = 2000
        
        if self._estimate_tokens(content) <= max_tokens:
            return Observation(content=content)
        
        # Truncate: head + tail + middle marker
        lines = content.splitlines()
        head = lines[:50]
        tail = lines[-20:]
        
        truncated = (
            "\n".join(head) +
            f"\n\n... {len(lines) - 70} lines elided ...\n\n" +
            "\n".join(tail)
        )
        
        # Offload full content to artifact
        artifact_path = self._save_artifact(content, result.call_id)
        
        return Observation(
            content=truncated,
            artifact_ref=str(artifact_path),
        )
    
    def _build_system_prompt(self, session: Session) -> str:
        """Build system prompt with role and tools."""
        return f"""You are a helpful coding assistant.

Permission mode: {session.permission_mode.value}
TDD enabled: {session.config.tdd_enabled}

Follow the plan carefully and ask for clarification when needed."""
    
    def _summarize_messages(self, messages: list[Message], session: Session) -> str:
        """Summarize messages via LLM."""
        # Call LLM with summarization prompt
        # (Implementation depends on model provider)
        pass
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token count estimate."""
        return len(text) // 4  # Rough heuristic
    
    def _save_artifact(self, content: str, call_id: str) -> Path:
        """Save large content to artifact."""
        artifact_dir = Path(".lyra/sessions") / session.id / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_path = artifact_dir / f"{call_id}.txt"
        artifact_path.write_text(content)
        
        return artifact_path
```

### Step 3: Permission Bridge Integration

```python
from lyra_core.permission import PermissionBridge, Decision, PermissionMode

class SimplePermissionBridge(PermissionBridge):
    """Rule-based permission bridge."""
    
    def decide(
        self,
        call: ToolCall,
        session: Session,
    ) -> Decision:
        """Authorize tool execution."""
        
        mode = session.permission_mode
        
        # Bypass mode: allow everything
        if mode == PermissionMode.BYPASS:
            return Decision.allow()
        
        # Plan mode: ask for everything
        if mode == PermissionMode.PLAN:
            return Decision.ask()
        
        # Auto-edit mode: rule-based
        if mode == PermissionMode.AUTO_EDIT:
            return self._auto_edit_rules(call)
        
        # Default: deny
        return Decision.deny("Unknown permission mode")
    
    def _auto_edit_rules(self, call: ToolCall) -> Decision:
        """Apply auto-edit rules."""
        
        # Read operations: always allow
        if call.name in {"read", "grep", "ls", "git_diff"}:
            return Decision.allow()
        
        # Write operations: allow for code/docs
        if call.name == "write":
            path = Path(call.arguments.get("path", ""))
            if path.suffix in {".py", ".ts", ".md", ".json"}:
                return Decision.allow()
            return Decision.ask()  # Ask for other file types
        
        # Destructive operations: always ask
        if call.name in {"bash", "delete", "git_reset"}:
            return Decision.ask()
        
        # Default: allow
        return Decision.allow()
```

### Step 4: Hook System Integration

```python
from lyra_core.hooks import HookSystem, HookEvent, HookResult

class SimpleHookSystem(HookSystem):
    """Simple hook system with pre/post handlers."""
    
    def __init__(self):
        self.handlers = {
            HookEvent.PRE_TOOL_USE: [
                self.secret_scanner,
                self.path_validator,
            ],
            HookEvent.POST_TOOL_USE: [
                self.cost_tracker,
                self.format_checker,
            ],
            HookEvent.STOP: [
                self.test_runner,
            ],
        }
    
    def run(
        self,
        event: HookEvent,
        *args,
        session: Session,
    ) -> HookResult:
        """Execute registered hooks."""
        
        handlers = self.handlers.get(event, [])
        
        for handler in handlers:
            result = handler(*args, session=session)
            
            if result.block:
                return result  # Stop on first block
        
        return HookResult(block=False)
    
    # Pre-tool hooks
    
    def secret_scanner(self, call: ToolCall, session: Session) -> HookResult:
        """Scan for hardcoded secrets."""
        
        if call.name != "write":
            return HookResult(block=False)
        
        content = call.arguments.get("content", "")
        
        # Simple pattern matching
        patterns = [
            r"api[_-]?key\s*=\s*['\"][a-zA-Z0-9]+['\"]",
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"secret\s*=\s*['\"][^'\"]+['\"]",
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return HookResult(
                    block=True,
                    reason="Detected potential hardcoded secret. Use environment variables instead.",
                )
        
        return HookResult(block=False)
    
    def path_validator(self, call: ToolCall, session: Session) -> HookResult:
        """Validate file paths are within workspace."""
        
        if "path" not in call.arguments:
            return HookResult(block=False)
        
        path = Path(call.arguments["path"]).resolve()
        workspace = Path.cwd().resolve()
        
        if not path.is_relative_to(workspace):
            return HookResult(
                block=True,
                reason=f"Path {path} is outside workspace {workspace}",
            )
        
        return HookResult(block=False)
    
    # Post-tool hooks
    
    def cost_tracker(self, call: ToolCall, result: ToolResult, session: Session) -> HookResult:
        """Track tool execution cost."""
        
        cost = result.metadata.get("cost_usd", 0.0)
        session.cost_usd += cost
        
        return HookResult(
            block=False,
            annotation=f"Cost: ${cost:.4f}" if cost > 0 else None,
        )
    
    def format_checker(self, call: ToolCall, result: ToolResult, session: Session) -> HookResult:
        """Auto-format code after write."""
        
        if call.name != "write" or result.is_error:
            return HookResult(block=False)
        
        path = Path(call.arguments["path"])
        
        # Run formatter based on file type
        if path.suffix == ".py":
            subprocess.run(["black", str(path)], check=False)
        elif path.suffix in {".ts", ".js"}:
            subprocess.run(["prettier", "--write", str(path)], check=False)
        
        return HookResult(block=False)
    
    # Stop hooks
    
    def test_runner(self, session: Session) -> HookResult:
        """Run tests before session end."""
        
        if not session.config.tdd_enabled:
            return HookResult(block=False)
        
        # Run test suite
        result = subprocess.run(
            ["pytest", "-xvs"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return HookResult(
                block=True,
                reason=f"Tests failed:\n{result.stdout}\n{result.stderr}",
            )
        
        return HookResult(block=False)
```

### Step 5: Main Loop Implementation

```python
from lyra_core.loop import LoopResult, TerminationStatus
from lyra_core.repeat import RepeatDetector

def agent_loop(
    session: Session,
    task: str,
    *,
    plan: Plan | None = None,
) -> LoopResult:
    """Execute agent loop."""
    
    # Initialize components
    context_engine = SimpleContextEngine()
    permission_bridge = SimplePermissionBridge()
    hook_system = SimpleHookSystem()
    tool_layer = ToolLayer()
    
    # Build initial transcript
    transcript = context_engine.assemble(session, task, plan)
    
    # Repeat detection
    repeat_guard = RepeatDetector(window=16, threshold=3)
    
    # Main loop
    for step in range(session.budgets.max_steps):
        
        # ── Preflight ─────────────────────────────────────
        
        # Check compaction trigger
        if transcript.tokens > session.budgets.max_tokens * session.config.compaction_threshold:
            transcript = context_engine.compact(transcript, session)
        
        # Check budget
        if session.cost_usd >= session.budgets.max_cost_usd:
            return LoopResult.cost_exhausted(session, transcript, step)
        
        # Check interrupt
        if session.interrupted:
            return LoopResult.user_interrupt(session, transcript, step)
        
        # ── Think ─────────────────────────────────────────
        
        # Call model
        response = model_provider.chat(
            transcript,
            tools=tool_layer.schemas(session.permission_mode),
        )
        
        # Update cost
        session.cost_usd += response.cost_usd
        
        # Append to transcript
        transcript.append(response)
        
        # Check termination
        if not response.tool_calls or response.is_end_of_turn:
            # Run STOP hooks
            stop_result = hook_system.run(HookEvent.STOP, session=session)
            
            if stop_result.block:
                # STOP hook blocked (e.g., tests failed)
                transcript.append(Message(
                    role="system",
                    content=f"Cannot complete session: {stop_result.reason}",
                ))
                continue  # Give model another chance
            
            return LoopResult.complete(session, transcript, step)
        
        # ── Act ───────────────────────────────────────────
        
        for call in response.tool_calls:
            
            # Repeat detection
            if repeat_guard.is_repeat(call):
                transcript.append_tool_result(
                    call.id,
                    "You've tried this before without success. Try a different approach.",
                )
                continue
            
            # Permission check
            decision = permission_bridge.decide(call, session)
            
            if decision.is_deny():
                transcript.append_tool_result(call.id, f"Blocked: {decision.reason}")
                continue
            
            if decision.is_ask():
                approved = prompt_user(call)
                if not approved:
                    transcript.append_tool_result(call.id, "User rejected this action")
                    continue
            
            if decision.is_park():
                session.parked_calls.append(call)
                transcript.append_tool_result(call.id, "Parked for later review")
                continue
            
            # Pre-tool hooks
            pre_result = hook_system.run(HookEvent.PRE_TOOL_USE, call, session=session)
            
            if pre_result.block:
                transcript.append_tool_result(call.id, f"Blocked by hook: {pre_result.reason}")
                continue
            
            # Execute tool
            result = tool_layer.execute(call, session)
            
            # Post-tool hooks
            post_result = hook_system.run(HookEvent.POST_TOOL_USE, call, result, session=session)
            
            if post_result.annotation:
                result = result.with_annotation(post_result.annotation)
            
            # Reduce observation
            observation = context_engine.reduce(result, session)
            
            # Append to transcript
            transcript.append_tool_result(call.id, observation.content)
        
        # ── Persist ───────────────────────────────────────
        
        if session.config.persist_every_step:
            session.persist_recent(transcript.tail(8))
    
    return LoopResult.steps_exhausted(session, transcript, step)
```

---

## Configuration Examples

### Example 1: Fast Development Iteration

```python
# Minimal safety, fast feedback
fast_session = Session(
    id="dev-fast",
    task="Add logging to API endpoints",
    model_selection=ModelSelection(
        fast="deepseek-v4-flash",  # Fast for everything
        smart="deepseek-v4-flash",
    ),
    permission_mode=PermissionMode.BYPASS,  # No prompts
    budgets=Budgets(
        max_cost_usd=1.0,  # Low budget
        max_steps=100,     # Quick iteration
    ),
    config=SessionConfig(
        tdd_enabled=False,
        safety_checks=False,
        compaction_threshold=0.95,  # Rarely compact
    ),
)
```

### Example 2: Production-Safe Deployment

```python
# Maximum safety, thorough validation
safe_session = Session(
    id="prod-deploy",
    task="Deploy authentication service to production",
    model_selection=ModelSelection(
        fast="deepseek-v4-flash",
        smart="deepseek-v4-pro",  # Smart for critical decisions
    ),
    permission_mode=PermissionMode.PLAN,  # Approve everything
    budgets=Budgets(
        max_cost_usd=20.0,  # Higher budget
        max_steps=500,
    ),
    config=SessionConfig(
        tdd_enabled=True,
        safety_checks=True,
        safety_check_interval=5,  # Frequent checks
        hooks_enabled=True,
    ),
)
```

### Example 3: Long-Running Research

```python
# Extended session, balanced safety
research_session = Session(
    id="research-cache-layer",
    task="Research and implement distributed caching strategy",
    model_selection=ModelSelection(
        fast="deepseek-v4-flash",
        smart="deepseek-v4-pro",
    ),
    permission_mode=PermissionMode.AUTO_EDIT,
    budgets=Budgets(
        max_cost_usd=50.0,  # Large budget
        max_steps=2000,     # Many steps
        max_tokens=500_000, # Large context
    ),
    config=SessionConfig(
        tdd_enabled=True,
        safety_checks=True,
        compaction_threshold=0.80,  # Aggressive compaction
        keep_window=10,  # More context preserved
    ),
)
```

---

## Testing

### Unit Testing the Loop

```python
import pytest
from unittest.mock import Mock, MagicMock

def test_loop_completes_on_end_of_turn():
    """Test normal completion."""
    
    # Mock components
    session = Mock(spec=Session)
    session.cost_usd = 0.0
    session.interrupted = False
    session.budgets.max_steps = 1000
    session.budgets.max_cost_usd = 10.0
    
    model = Mock()
    model.chat.return_value = Mock(
        tool_calls=[],
        is_end_of_turn=True,
        cost_usd=0.10,
    )
    
    # Run loop
    result = agent_loop(session, "test task")
    
    # Assertions
    assert result.status == TerminationStatus.COMPLETED
    assert session.cost_usd == 0.10
    assert result.step < 1000

def test_loop_respects_cost_budget():
    """Test cost budget enforcement."""
    
    session = Mock(spec=Session)
    session.cost_usd = 0.0
    session.budgets.max_cost_usd = 1.0  # Low budget
    session.budgets.max_steps = 1000
    
    model = Mock()
    model.chat.return_value = Mock(
        tool_calls=[Mock(name="expensive_tool")],
        cost_usd=0.50,  # Each call costs $0.50
    )
    
    # Run loop (should stop after 2 steps)
    result = agent_loop(session, "test task")
    
    assert result.status == TerminationStatus.COST_EXHAUSTED
    assert session.cost_usd >= 1.0

def test_repeat_detector_triggers_stalemate():
    """Test repeat detection."""
    
    session = Mock(spec=Session)
    session.budgets.max_steps = 1000
    
    # Model returns same tool call repeatedly
    model = Mock()
    model.chat.return_value = Mock(
        tool_calls=[
            Mock(name="read", arguments={"path": "same_file.py"}),
        ],
        is_end_of_turn=False,
    )
    
    result = agent_loop(session, "test task")
    
    # Should detect stalemate after 3 repeats
    assert result.status == TerminationStatus.STALEMATE
    assert result.step <= 20  # Within 16-call window
```

### Integration Testing

```python
def test_full_loop_with_real_filesystem(tmp_path):
    """Integration test with real filesystem."""
    
    # Setup test workspace
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "src").mkdir()
    
    # Create session
    session = Session(
        id="integration-test",
        task="Create a simple Python function",
        model_selection=ModelSelection(
            fast="mock-model",  # Use mock for testing
            smart="mock-model",
        ),
        permission_mode=PermissionMode.BYPASS,
        budgets=Budgets(
            max_cost_usd=1.0,
            max_steps=10,
        ),
        config=SessionConfig(
            session_dir=tmp_path / ".lyra/sessions",
        ),
    )
    
    # Run loop
    result = agent_loop(session, session.task)
    
    # Verify outcomes
    assert result.status == TerminationStatus.COMPLETED
    assert (workspace / "src" / "main.py").exists()
    assert (tmp_path / ".lyra/sessions" / session.id / "recent.jsonl").exists()
```

---

## Debugging

### Enable Debug Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Enable loop debug logs
logger = logging.getLogger("lyra_core.loop")
logger.setLevel(logging.DEBUG)
```

### Trace Analysis

```python
def analyze_session_trace(session_id: str) -> None:
    """Analyze session trace for debugging."""
    
    trace_path = Path(f".lyra/sessions/{session_id}/trace.jsonl")
    
    events = []
    with open(trace_path) as f:
        for line in f:
            events.append(json.loads(line))
    
    # Analyze patterns
    print(f"Total events: {len(events)}")
    print(f"Total steps: {len([e for e in events if e['event'] == 'agent.step'])}")
    print(f"Tool calls: {len([e for e in events if e['event'].startswith('tool.')])}")
    print(f"Permission denials: {len([e for e in events if e.get('decision') == 'deny'])}")
    
    # Find bottlenecks
    step_durations = [e['duration_ms'] for e in events if 'duration_ms' in e]
    if step_durations:
        print(f"Avg step duration: {sum(step_durations) / len(step_durations):.0f}ms")
        print(f"Max step duration: {max(step_durations):.0f}ms")
    
    # Cost breakdown
    total_cost = sum(e.get('cost_usd', 0) for e in events)
    print(f"Total cost: ${total_cost:.2f}")
```

### Common Issues

**Issue: Session runs out of budget quickly**

```python
# Solution 1: Increase budget
session.budgets.max_cost_usd = 10.0  # Increase from default

# Solution 2: Use cheaper model for fast slot
session.model_selection.fast = "deepseek-v4-flash"  # Cheaper

# Solution 3: Enable aggressive compaction
session.config.compaction_threshold = 0.75  # Compact earlier
```

**Issue: Loop stuck in infinite retry**

```python
# Check repeat detector settings
repeat_guard = RepeatDetector(
    window=16,      # Increase if legitimate retries needed
    threshold=3,    # Decrease to catch loops faster
)

# Check trace for patterns
analyze_session_trace(session.id)
```

**Issue: Tool calls blocked unexpectedly**

```python
# Enable permission debug logs
logging.getLogger("lyra_core.permission").setLevel(logging.DEBUG)

# Check permission mode
print(f"Permission mode: {session.permission_mode}")

# Review recent denials in trace
denials = [e for e in events if e.get('decision') == 'deny']
for d in denials:
    print(f"Denied: {d['tool_name']} - {d['reason']}")
```

---

## Common Pitfalls

### Pitfall 1: Not Handling Tool Errors

❌ **Wrong:**

```python
result = tool_layer.execute(call, session)
transcript.append_tool_result(call.id, result.content)
```

✅ **Correct:**

```python
result = tool_layer.execute(call, session)

if result.is_error:
    # Let model see error and recover
    observation = f"Tool failed: {result.content}"
else:
    observation = result.content

transcript.append_tool_result(call.id, observation)
```

### Pitfall 2: Forgetting to Persist State

❌ **Wrong:**

```python
for step in range(max_steps):
    # ... execute step ...
    pass  # No persistence
```

✅ **Correct:**

```python
for step in range(max_steps):
    # ... execute step ...
    
    # Persist after each step
    session.persist_recent(transcript.tail(8))
    state_store.update_state_md(session, transcript)
```

### Pitfall 3: Blocking Forever on User Prompt

❌ **Wrong:**

```python
def prompt_user(call: ToolCall) -> bool:
    # Blocks indefinitely
    return input(f"Approve {call.name}? (y/n): ").lower() == "y"
```

✅ **Correct:**

```python
def prompt_user(call: ToolCall, timeout: int = 60) -> bool:
    """Prompt with timeout."""
    try:
        with timeout_context(timeout):
            return input(f"Approve {call.name}? (y/n): ").lower() == "y"
    except TimeoutError:
        # Auto-deny on timeout
        return False
```

### Pitfall 4: Memory Leaks in Long Sessions

❌ **Wrong:**

```python
# Transcript grows unbounded
transcript.messages.append(message)  # Never prunes
```

✅ **Correct:**

```python
# Trigger compaction
if transcript.tokens > threshold:
    transcript = context_engine.compact(transcript, session)
```

---

## Related Documentation

- [Architecture](./architecture.md)
- [Architecture Tradeoffs](./architecture-tradeoffs.md)
- [System Design](./system-design.md)
- [Deep Dive](./deep-dive.md)

---

**Next:** [Deep Dive](./deep-dive.md)

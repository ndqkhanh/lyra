# Context Engine Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing the Context Engine, with practical code examples, configuration, testing strategies, debugging techniques, and common pitfalls to avoid.

## Prerequisites

```bash
# Required dependencies
pip install tiktoken>=0.5.0          # Token counting
pip install jinja2>=3.1.0            # Template rendering
pip install pydantic>=2.0.0          # Data validation
pip install opentelemetry-api>=1.20  # Observability

# Optional but recommended
pip install pytest-asyncio>=0.21.0   # Async testing
pip install hypothesis>=6.80.0       # Property-based testing
```

## Step 1: Implement Core Data Structures

### 1.1 Message and Transcript

```python
# lyra_core/context/types.py

from dataclasses import dataclass, field
from typing import Literal, Optional, Tuple, List, Dict, Any
from enum import Enum

@dataclass(frozen=True)
class Message:
    """Immutable conversation message."""
    
    role: Literal["system", "user", "assistant"]
    content: str
    cache_control: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def system(content: str, **metadata) -> 'Message':
        return Message(role="system", content=content, metadata=metadata)
    
    @staticmethod
    def user(content: str) -> 'Message':
        return Message(role="user", content=content)
    
    @staticmethod
    def assistant(content: str) -> 'Message':
        return Message(role="assistant", content=content)
    
    def with_cache_control(self, cache_type: str = "ephemeral") -> 'Message':
        """Return new message with cache control marker."""
        return Message(
            role=self.role,
            content=self.content,
            cache_control={"type": cache_type},
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class Transcript:
    """Immutable conversation transcript."""
    
    messages: Tuple[Message, ...]
    cache_breakpoints: Tuple[int, ...] = field(default_factory=tuple)
    
    def count_tokens(self, model: str) -> int:
        """Count total tokens using tiktoken."""
        import tiktoken
        
        encoder = tiktoken.encoding_for_model(model)
        total = 0
        
        for msg in self.messages:
            # Account for role tokens
            total += len(encoder.encode(msg.role))
            # Account for content tokens
            total += len(encoder.encode(msg.content))
            # Account for message formatting (approximately 4 tokens per message)
            total += 4
        
        return total
    
    def with_message(self, message: Message) -> 'Transcript':
        """Return new transcript with message appended."""
        return Transcript(
            messages=self.messages + (message,),
            cache_breakpoints=self.cache_breakpoints,
        )
    
    def slice(self, start: int, end: Optional[int] = None) -> Tuple[Message, ...]:
        """Get a slice of messages."""
        return self.messages[start:end]
```

**Common Pitfall**: Mutating messages in place. Always create new instances.

```python
# ❌ WRONG - mutates existing message
message.cache_control = {"type": "ephemeral"}

# ✅ CORRECT - creates new message
message = message.with_cache_control("ephemeral")
```

## Step 2: Implement Context Assembler

### 2.1 Basic Assembler

```python
# lyra_core/context/assemble.py

from pathlib import Path
from typing import Optional

class ContextAssembler:
    """Assembles five-layer context structure."""
    
    def __init__(self, session: 'Session'):
        self.session = session
        self.project_root = session.project_root
    
    def assemble(
        self,
        task: str,
        plan: Optional['Plan'] = None,
    ) -> Transcript:
        """Assemble complete transcript with all layers."""
        messages = []
        
        # L1: Cached prefix
        messages.extend(self._build_l1_prefix())
        l1_end = len(messages) - 1
        
        # L2: Cached mid
        messages.extend(self._build_l2_mid(plan))
        l2_end = len(messages) - 1
        
        # L3: Dynamic
        messages.extend(self._build_l3_dynamic(task))
        
        # Create transcript with cache breakpoints
        transcript = Transcript(
            messages=tuple(messages),
            cache_breakpoints=(l1_end, l2_end),
        )
        
        # Apply provider-specific cache markers
        return self._apply_cache_markers(transcript)
    
    def _build_l1_prefix(self) -> List[Message]:
        """Build L1: system prompt and tool schemas."""
        system_prompt = self._load_system_prompt()
        tool_schemas = self._render_tool_schemas()
        
        return [
            Message.system(system_prompt, layer="L1"),
            Message.system(tool_schemas, layer="L1"),
        ]
    
    def _build_l2_mid(self, plan: Optional['Plan']) -> List[Message]:
        """Build L2: SOUL, plan, todos, skills."""
        messages = []
        
        # SOUL (always present)
        soul_content = self._load_soul()
        messages.append(Message.system(soul_content, layer="L2", component="soul"))
        
        # Plan (optional)
        if plan:
            plan_summary = plan.summary_for_context()
            messages.append(Message.system(plan_summary, layer="L2", component="plan"))
        
        # TODOs (derived from plan)
        todo_content = self._render_todos()
        messages.append(Message.system(todo_content, layer="L2", component="todos"))
        
        # Skills in scope
        skills_content = self._render_skills()
        messages.append(Message.system(skills_content, layer="L2", component="skills"))
        
        return messages
    
    def _build_l3_dynamic(self, task: str) -> List[Message]:
        """Build L3: recent turns and current task."""
        messages = []
        
        # Add recent conversation history
        history = self.session.get_recent_turns(limit=50)
        messages.extend(history)
        
        # Add current user task
        messages.append(Message.user(task))
        
        return messages
    
    def _load_soul(self) -> str:
        """Load SOUL.md from project."""
        soul_path = self.project_root / ".lyra" / "SOUL.md"
        
        if soul_path.exists():
            return soul_path.read_text()
        
        # Return default SOUL if not found
        return self._default_soul()
    
    def _render_todos(self) -> str:
        """Render TODO list from current plan."""
        # Implementation depends on your plan structure
        return "# TODO\n\n- [ ] Task 1\n- [ ] Task 2"
    
    def _render_skills(self) -> str:
        """Render available skills."""
        skills = self.session.active_skills
        return "\n\n".join(
            f"## {skill.name}\n{skill.description}"
            for skill in skills
        )
    
    def _apply_cache_markers(self, transcript: Transcript) -> Transcript:
        """Apply provider-specific cache control markers."""
        provider = self.session.provider
        
        if provider == "anthropic":
            return self._apply_anthropic_cache(transcript)
        elif provider == "openai":
            # OpenAI uses implicit caching, no markers needed
            return transcript
        elif provider == "gemini":
            return self._apply_gemini_cache(transcript)
        
        return transcript
    
    def _apply_anthropic_cache(self, transcript: Transcript) -> Transcript:
        """Apply Anthropic cache_control blocks."""
        messages = list(transcript.messages)
        
        # Mark breakpoint messages for caching
        for idx in transcript.cache_breakpoints:
            if idx < len(messages):
                messages[idx] = messages[idx].with_cache_control("ephemeral")
        
        return Transcript(
            messages=tuple(messages),
            cache_breakpoints=transcript.cache_breakpoints,
        )
```

### 2.2 Testing the Assembler

```python
# tests/test_context_assembler.py

import pytest
from lyra_core.context.assemble import ContextAssembler
from lyra_core.context.types import Message

@pytest.fixture
def mock_session(tmp_path):
    """Create a mock session for testing."""
    # Create test SOUL.md
    soul_path = tmp_path / ".lyra" / "SOUL.md"
    soul_path.parent.mkdir(parents=True)
    soul_path.write_text("# Test Agent\n\nI am a test agent.")
    
    class MockSession:
        project_root = tmp_path
        provider = "anthropic"
        active_skills = []
        
        def get_recent_turns(self, limit):
            return []
    
    return MockSession()


def test_assembly_produces_five_layers(mock_session):
    """Verify assembly creates all five layers."""
    assembler = ContextAssembler(mock_session)
    transcript = assembler.assemble("Test task", plan=None)
    
    # Should have messages from L1, L2, and L3
    assert len(transcript.messages) > 0
    
    # Should have two cache breakpoints (after L1, after L2)
    assert len(transcript.cache_breakpoints) == 2


def test_assembly_is_deterministic(mock_session):
    """Verify same inputs produce identical transcripts."""
    assembler = ContextAssembler(mock_session)
    
    t1 = assembler.assemble("Test task", plan=None)
    t2 = assembler.assemble("Test task", plan=None)
    
    # Same task should produce identical transcripts
    assert len(t1.messages) == len(t2.messages)
    for m1, m2 in zip(t1.messages, t2.messages):
        assert m1.content == m2.content


def test_soul_is_in_l2(mock_session):
    """Verify SOUL appears in L2 layer."""
    assembler = ContextAssembler(mock_session)
    transcript = assembler.assemble("Test", plan=None)
    
    # L2 is between first and second breakpoint
    l2_start = transcript.cache_breakpoints[0] + 1
    l2_end = transcript.cache_breakpoints[1] + 1
    l2_messages = transcript.messages[l2_start:l2_end]
    
    # SOUL should be in L2
    soul_content = "".join(m.content for m in l2_messages)
    assert "Test Agent" in soul_content
```

## Step 3: Implement Compactor

### 3.1 Basic Compaction

```python
# lyra_core/context/compact.py

from typing import Tuple
from dataclasses import dataclass

@dataclass
class CompactionConfig:
    """Configuration for compaction."""
    threshold: float = 0.85
    keep_window_size: int = 10
    target_ratio: float = 0.2  # Target 20% of original size


class Compactor:
    """Handles context compaction."""
    
    def __init__(self, session: 'Session', llm_client: 'LLMClient'):
        self.session = session
        self.llm = llm_client
        self.config = CompactionConfig()
    
    def should_compact(self, transcript: Transcript) -> bool:
        """Check if compaction is needed."""
        max_tokens = self.session.max_tokens
        current_tokens = transcript.count_tokens(self.session.model)
        
        threshold_tokens = max_tokens * self.config.threshold
        return current_tokens > threshold_tokens
    
    def compact(self, transcript: Transcript) -> Transcript:
        """Compact transcript by summarizing older turns."""
        # Identify windows
        keep_window, compact_window = self._identify_windows(transcript)
        
        if not compact_window:
            # Nothing to compact, use emergency truncation
            return self._emergency_truncate(transcript)
        
        # Generate summary
        summary_text = self._generate_summary(compact_window)
        
        # Build new transcript
        messages = list(transcript.messages)
        
        # Keep L1 and L2
        l2_end = transcript.cache_breakpoints[1] + 1
        new_messages = messages[:l2_end]
        
        # Add compaction summary
        new_messages.append(
            Message.system(
                summary_text,
                compaction=True,
                original_turns=len(compact_window),
            )
        )
        
        # Add keep window
        new_messages.extend(keep_window)
        
        return Transcript(
            messages=tuple(new_messages),
            cache_breakpoints=transcript.cache_breakpoints,
        )
    
    def _identify_windows(
        self,
        transcript: Transcript,
    ) -> Tuple[List[Message], List[Message]]:
        """Identify keep and compact windows."""
        l3_start = transcript.cache_breakpoints[1] + 1
        l3_messages = list(transcript.messages[l3_start:])
        
        # Keep last N turns
        keep_size = self.config.keep_window_size
        keep_window = l3_messages[-keep_size:] if len(l3_messages) > keep_size else []
        
        # Compact everything else
        compact_window = l3_messages[:-keep_size] if len(l3_messages) > keep_size else []
        
        return keep_window, compact_window
    
    def _generate_summary(self, messages: List[Message]) -> str:
        """Generate narrative summary using LLM."""
        # Format messages for summarization
        conversation_text = self._format_for_summary(messages)
        
        prompt = f"""Summarize this conversation history concisely.

PRESERVE:
- File paths and line numbers (e.g., src/auth.py:42)
- Error messages and test failures
- Permission denials and their reasons
- Unresolved questions
- Key decisions made

DISCARD:
- Verbose logs
- Repetitive confirmations
- Full code blocks (mention files modified instead)

Conversation to summarize:
{conversation_text}

Provide a narrative summary (target: 20% of original length):"""
        
        response = self.llm.generate(
            prompt,
            model="claude-3-haiku-20240307",  # Cheap model for summaries
            temperature=0.3,
            max_tokens=2000,
        )
        
        return response.text
    
    def _format_for_summary(self, messages: List[Message]) -> str:
        """Format messages for summarization prompt."""
        lines = []
        for i, msg in enumerate(messages, 1):
            lines.append(f"[{i}] {msg.role.upper()}: {msg.content[:500]}")
        return "\n\n".join(lines)
    
    def _emergency_truncate(self, transcript: Transcript) -> Transcript:
        """Emergency fallback: drop middle third of L3."""
        l3_start = transcript.cache_breakpoints[1] + 1
        l3_messages = list(transcript.messages[l3_start:])
        
        third = len(l3_messages) // 3
        truncated = l3_messages[:third] + l3_messages[-third:]
        
        new_messages = list(transcript.messages[:l3_start])
        new_messages.append(
            Message.system("[Compaction failed: middle third removed]")
        )
        new_messages.extend(truncated)
        
        return Transcript(
            messages=tuple(new_messages),
            cache_breakpoints=transcript.cache_breakpoints,
        )
```

### 3.2 Testing Compaction

```python
# tests/test_compactor.py

def test_compaction_reduces_token_count():
    """Verify compaction reduces transcript size."""
    # Create large transcript
    messages = [
        Message.system("System prompt"),
        Message.system("SOUL"),
    ]
    
    # Add 50 verbose turns
    for i in range(50):
        messages.append(Message.user(f"Request {i}" * 100))
        messages.append(Message.assistant(f"Response {i}" * 100))
    
    transcript = Transcript(
        messages=tuple(messages),
        cache_breakpoints=(0, 1),
    )
    
    # Compact
    compactor = Compactor(mock_session, mock_llm)
    compacted = compactor.compact(transcript)
    
    # Should be significantly smaller
    original_tokens = transcript.count_tokens("gpt-4")
    compacted_tokens = compacted.count_tokens("gpt-4")
    
    assert compacted_tokens < original_tokens * 0.5


def test_compaction_preserves_file_anchors():
    """Verify compaction preserves critical information."""
    messages = [
        Message.system("System"),
        Message.system("SOUL"),
        Message.user("Fix the bug"),
        Message.assistant("Found issue in src/auth.py:42"),
        Message.user("Test it"),
        Message.assistant("Test failed: AssertionError in test_login"),
    ]
    
    transcript = Transcript(messages=tuple(messages), cache_breakpoints=(0, 1))
    
    compactor = Compactor(mock_session, mock_llm)
    compacted = compactor.compact(transcript)
    
    # Critical info should be preserved
    full_text = " ".join(m.content for m in compacted.messages)
    assert "src/auth.py:42" in full_text
    assert "test_login" in full_text
```

## Step 4: Implement Observation Reducer

### 4.1 Reducer Implementation

```python
# lyra_core/context/reduce.py

from dataclasses import dataclass
from typing import Optional, Dict, Callable
import hashlib

@dataclass
class Observation:
    """Reduced tool observation."""
    text: str
    artifact_ref: Optional[str] = None


class ObservationReducer:
    """Reduces tool outputs to transcript-friendly sizes."""
    
    def __init__(self, artifact_store: 'ArtifactStore'):
        self.artifact_store = artifact_store
        self.reducers = self._build_reducers()
    
    def reduce(self, tool_name: str, output: str) -> Observation:
        """Reduce tool output based on tool type."""
        reducer = self.reducers.get(tool_name, self._default_reducer)
        return reducer(output)
    
    def _build_reducers(self) -> Dict[str, Callable]:
        """Map tool names to reduction functions."""
        return {
            "read": self._reduce_read,
            "bash": self._reduce_bash,
            "grep": self._reduce_grep,
        }
    
    def _reduce_read(self, output: str) -> Observation:
        """Reduce file read output."""
        lines = output.splitlines()
        
        if len(lines) <= 100:
            return Observation(output)  # Small enough
        
        # Take head and tail
        head = "\n".join(lines[:50])
        tail = "\n".join(lines[-20:])
        
        # Save full content to artifacts
        artifact_hash = self.artifact_store.save(output)
        
        reduced = f"""{head}

... {len(lines) - 70} lines elided ...
[Full content: view {artifact_hash}]

{tail}"""
        
        return Observation(reduced, artifact_ref=artifact_hash)
    
    def _reduce_bash(self, output: str) -> Observation:
        """Reduce bash command output."""
        if len(output) <= 4096:
            return Observation(output)
        
        lines = output.splitlines()
        tail = "\n".join(lines[-80:])
        
        artifact_hash = self.artifact_store.save(output)
        
        reduced = f"""[Output: {len(lines)} lines, {len(output)} bytes]
[Full output: view {artifact_hash}]

Last 80 lines:
{tail}"""
        
        return Observation(reduced, artifact_ref=artifact_hash)
    
    def _reduce_grep(self, output: str) -> Observation:
        """Reduce grep results."""
        lines = output.splitlines()
        
        if len(lines) <= 20:
            return Observation(output)
        
        head = "\n".join(lines[:20])
        artifact_hash = self.artifact_store.save(output)
        
        reduced = f"""{head}

... {len(lines) - 20} more matches ...
[Full results: view {artifact_hash}]"""
        
        return Observation(reduced, artifact_ref=artifact_hash)
    
    def _default_reducer(self, output: str) -> Observation:
        """Default reducer for unknown tools."""
        if len(output) <= 4096:
            return Observation(output)
        
        artifact_hash = self.artifact_store.save(output)
        preview = output[:2000]
        
        return Observation(
            f"{preview}\n\n[Truncated. Full output: view {artifact_hash}]",
            artifact_ref=artifact_hash,
        )
```

## Step 5: Configuration

### 5.1 Context Engine Config

```yaml
# .lyra/config/context.yaml

context_engine:
  # Compaction settings
  compaction:
    threshold: 0.85              # Compact at 85% of max_tokens
    keep_window_size: 10         # Keep last 10 turns uncompacted
    target_ratio: 0.2            # Target 20% of original size
    model: "claude-3-haiku-20240307"  # Cheap model for summaries
  
  # Reduction settings
  reduction:
    read_max_lines: 100          # Max lines before reducing file reads
    bash_max_bytes: 4096         # Max bytes before reducing bash output
    grep_max_matches: 20         # Max matches before reducing grep results
  
  # Cache settings
  cache:
    enabled: true
    l1_breakpoint: true          # Enable L1 cache breakpoint
    l2_breakpoint: true          # Enable L2 cache breakpoint
  
  # Layer sizes (reserved tokens)
  layers:
    l1_reserved: 12000
    l2_reserved: 8000
```

### 5.2 Loading Config

```python
# lyra_core/context/config.py

from pathlib import Path
import yaml
from dataclasses import dataclass

@dataclass
class ContextConfig:
    """Context engine configuration."""
    compaction_threshold: float = 0.85
    keep_window_size: int = 10
    compaction_model: str = "claude-3-haiku-20240307"
    
    @classmethod
    def load(cls, project_root: Path) -> 'ContextConfig':
        """Load config from project."""
        config_path = project_root / ".lyra" / "config" / "context.yaml"
        
        if not config_path.exists():
            return cls()  # Use defaults
        
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        ce_config = data.get("context_engine", {})
        compaction = ce_config.get("compaction", {})
        
        return cls(
            compaction_threshold=compaction.get("threshold", 0.85),
            keep_window_size=compaction.get("keep_window_size", 10),
            compaction_model=compaction.get("model", "claude-3-haiku-20240307"),
        )
```

## Step 6: Debugging

### 6.1 Debug Logging

```python
# lyra_core/context/debug.py

import logging
from typing import Dict, Any

logger = logging.getLogger("lyra.context")

def log_assembly(transcript: Transcript, metadata: Dict[str, Any]):
    """Log transcript assembly details."""
    logger.debug(
        "Assembled transcript",
        extra={
            "message_count": len(transcript.messages),
            "token_count": transcript.count_tokens(metadata["model"]),
            "cache_breakpoints": transcript.cache_breakpoints,
            "layers": {
                "l1": metadata.get("l1_size", 0),
                "l2": metadata.get("l2_size", 0),
                "l3": metadata.get("l3_size", 0),
            },
        },
    )

def log_compaction(before: int, after: int, duration_ms: float):
    """Log compaction results."""
    reduction_pct = ((before - after) / before) * 100
    
    logger.info(
        "Compaction completed",
        extra={
            "tokens_before": before,
            "tokens_after": after,
            "reduction_pct": reduction_pct,
            "duration_ms": duration_ms,
        },
    )
```

### 6.2 Debug CLI Commands

```bash
# View current transcript structure
lyra context show

# Show token breakdown by layer
lyra context tokens

# Test compaction without applying
lyra context compact --dry-run

# View cache hit rate
lyra context cache-stats
```

## Common Pitfalls

### Pitfall 1: Token Count Mismatch

**Problem**: Your token count doesn't match provider's actual usage.

```python
# ❌ WRONG - using wrong encoder
encoder = tiktoken.get_encoding("cl100k_base")  # Generic encoding

# ✅ CORRECT - using model-specific encoder
encoder = tiktoken.encoding_for_model("claude-3-opus-20240229")
```

### Pitfall 2: Cache Invalidation

**Problem**: Cache hit rate is low despite stable layers.

```python
# ❌ WRONG - changing L2 order
messages = [soul, todos, plan]  # Different order each time

# ✅ CORRECT - fixed order
messages = [soul, plan, todos]  # Same order always
```

### Pitfall 3: Over-Reduction

**Problem**: Reduced observations lose critical information.

```python
# ❌ WRONG - too aggressive
reduced = output[:100]  # First 100 chars only

# ✅ CORRECT - balanced reduction
reduced = output[:1000] + "\n...\n" + output[-500:]  # Head + tail
```

### Pitfall 4: Compaction Timing

**Problem**: Compacting too early or too late.

```python
# ❌ WRONG - fixed turn count
if turn_count == 50:
    compact()

# ✅ CORRECT - token-based threshold
if transcript.count_tokens() > max_tokens * 0.85:
    compact()
```

## Performance Tips

1. **Cache token counts**: Token counting is expensive, cache results per message
2. **Async reduction**: Process tool outputs in parallel
3. **Lazy artifact loading**: Don't load artifacts unless explicitly requested
4. **Batch compaction**: If multiple sessions need compaction, batch the summarization calls

## Next Steps

- Implement [memory integration](./deep-dive.md#memory-integration)
- Add [observability spans](./deep-dive.md#observability)
- Configure [provider-specific optimizations](./architecture-tradeoffs.md#decision-7)

## References

- [Architecture Overview](./architecture.md)
- [System Design](./system-design.md)
- [Architecture Tradeoffs](./architecture-tradeoffs.md)

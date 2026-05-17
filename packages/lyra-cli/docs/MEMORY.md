# Memory & Session Persistence

The memory and session system provides persistent storage for conversation history, project context, and session state.

## Architecture

### Memory System

- **MemoryMetadata**: Dataclass for memory entries
- **MemoryStorage**: Persists memories to disk
- **MemoryManager**: High-level interface for managing memories
- **MemoryType**: Enum for memory categories (conversation, project, preference)

### Session System

- **SessionState**: Dataclass for session state
- **SessionStorage**: Persists sessions to disk
- **SessionManager**: High-level interface for managing sessions

## Usage

### Memory Management

```python
from lyra_cli.core.memory_storage import MemoryStorage
from lyra_cli.core.memory_manager import MemoryManager
from lyra_cli.core.memory_metadata import MemoryType
from pathlib import Path

# Initialize
storage = MemoryStorage(Path(".lyra/memory"))
manager = MemoryManager(storage)

# Add memory
memory = manager.add(
    content="User prefers TypeScript",
    memory_type=MemoryType.PREFERENCE,
    tags=["typescript", "preference"]
)

# Search memories
results = manager.search("typescript")

# Filter by type
preferences = manager.filter_by_type(MemoryType.PREFERENCE)
```

### Session Management

```python
from lyra_cli.core.session_storage import SessionStorage
from lyra_cli.core.session_manager import SessionManager
from pathlib import Path

# Initialize
storage = SessionStorage(Path(".lyra/sessions"))
manager = SessionManager(storage)

# Create session
session = manager.create()

# Update session
session.conversation_history.append("User message")
session.context["key"] = "value"
manager.save(session)

# Load session
loaded = manager.load(session.session_id)

# List all sessions
session_ids = manager.list_all()
```

## API Reference

### MemoryType

```python
class MemoryType(Enum):
    CONVERSATION = "conversation"
    PROJECT = "project"
    PREFERENCE = "preference"
```

### MemoryMetadata

```python
@dataclass
class MemoryMetadata:
    id: str
    content: str
    memory_type: MemoryType
    timestamp: datetime
    tags: List[str]
    metadata: Optional[Dict[str, Any]] = None
```

### MemoryManager

```python
class MemoryManager:
    def add(self, content: str, memory_type: MemoryType, tags: List[str]) -> MemoryMetadata
    def get(self, memory_id: str) -> Optional[MemoryMetadata]
    def search(self, query: str) -> List[MemoryMetadata]
    def filter_by_type(self, memory_type: MemoryType) -> List[MemoryMetadata]
    def delete(self, memory_id: str) -> bool
    def list_all(self) -> List[MemoryMetadata]
```

### SessionState

```python
@dataclass
class SessionState:
    session_id: str
    created_at: datetime
    last_updated: datetime
    conversation_history: list
    context: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
```

### SessionManager

```python
class SessionManager:
    def create(self) -> SessionState
    def save(self, session: SessionState) -> None
    def load(self, session_id: str) -> Optional[SessionState]
    def delete(self, session_id: str) -> bool
    def list_all(self) -> list
```

## Best Practices

1. **Regular Saves**: Save session state after significant changes
2. **Tag Memories**: Use descriptive tags for easy retrieval
3. **Type Organization**: Use appropriate memory types for categorization
4. **Cleanup**: Periodically delete old sessions and memories
5. **Backup**: Keep backups of important session data

## Integration

### With Hooks
Session state can be saved/loaded via SessionStart and SessionEnd hooks.

### With Commands
Commands can access session context for stateful operations.

### With Agents
Agents can store learnings in memory for future reference.

## See Also

- [AGENTS.md](AGENTS.md) - Agent system documentation
- [HOOKS.md](HOOKS.md) - Hooks system documentation
- [LYRA_ECC_INTEGRATION_ULTRA_PLAN.md](../LYRA_ECC_INTEGRATION_ULTRA_PLAN.md) - Full integration plan

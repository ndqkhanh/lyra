# Sessions Guide — Checkpointing, Replay, and Persistence

> How Lyra persists session state, checkpoints progress, and enables resumption across crashes.

## Quickstart

Sessions are SQLite-backed and checkpoint automatically:

```python
from lyra.sessions import SessionManager

manager = SessionManager()
session = manager.create(name="my-research-task")
# ... agent runs ...
manager.checkpoint(session.id)  # explicit checkpoint
# ... crash ...
resumed = manager.resume(session.id)  # resumes from last checkpoint
```

## Key Concepts

- **Checkpointing**: Agent state serialized to SQLite at logical breakpoints (tool call boundaries, turn ends)
- **Replay**: Rewind to any turn and resume from that point
- **Export/Import**: Full session serialization for sharing or archival
- **Two-axis state**: Task-state (Working/NeedsInput/Completed/Failed) × Process-liveness (Alive/ExitedResumable/LoopSleeping)
- **Fleet view**: All sessions visible in supervisor fleet view with status badges

## Session Lifecycle

```
Created → Working → [NeedsInput] → Working → Completed
                   ↘ Failed → [Retry] → Working
                   ↘ Stopped
```

## → Dive Deeper

- [Sessions Concept](../concepts/08-sessions-and-state.md)
- [Fleet Architecture](../architecture/04-fleet-supervisor.md)
- [Autonomy Plan](../lyra-upgrade/plans/14-autonomy.md)

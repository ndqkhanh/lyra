# Phase 2 — Dual-Pane TUI

Modules: `app.py`, `widgets.py`

## Textual App (`app.py`)

Full TUI application with dual-pane layout.

```python
from lyra_ui import LyraApp

app = LyraApp()
app.run()
```

**Features**

- Split-screen layout (70% conversation, 30% status)
- Conversation pane with message history
- Status panel with real-time indicators
- Keyboard shortcuts (`q` quit, `Ctrl+W` switch pane, `Ctrl+N` new chat)
- CSS-like styling

## Custom Widgets (`widgets.py`)

Rich widgets for UI components.

```python
from lyra_ui import (
    MessageBubble,
    TokenUsageIndicator,
    AgentStatusIndicator,
    ContextUsageRing,
)

bubble = MessageBubble("user", "Hello world")

token_indicator = TokenUsageIndicator(used=50000, total=200000)
token_indicator.update_usage(75000)

agent_status = AgentStatusIndicator("working")
agent_status.update_status("success")

context_ring = ContextUsageRing(45.0)
context_ring.update_percentage(60.0)
```

**Widgets**

- `MessageBubble` — user/assistant messages with timestamps
- `TokenUsageIndicator` — visual token usage bar with color coding
- `AgentStatusIndicator` — agent status (idle / working / success / error)
- `ContextUsageRing` — context window usage percentage

## Adding messages to the conversation

```python
from lyra_ui import ConversationPane

pane = ConversationPane()
pane.add_message("user", "What is Python?")
pane.add_message("assistant", "Python is a programming language...")
```

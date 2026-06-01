# Session Multiplexer Architecture

**Status:** Proposed  
**Version:** 1.0  
**Date:** 2026-05-29  
**Related:** US-011 Terminal Multiplexer Enhancement

---

## Overview

This document proposes a session multiplexer architecture for Lyra, inspired by tmux, cmux, and rmux. The multiplexer enables visual management of multiple concurrent agents, session persistence, and real-time status monitoring.

### Goals

1. **Multi-Agent Visualization** - Display multiple agents running in parallel with split-pane layout
2. **Session Persistence** - Sessions survive crashes and can be resumed
3. **Real-Time Monitoring** - Live status updates and notifications
4. **Efficient I/O** - Non-blocking multiplexing of agent outputs
5. **Intuitive UX** - Familiar tmux-style keybindings and navigation

### Non-Goals

- Replace existing CLI interface (multiplexer is additive)
- Implement full terminal emulator (delegate to existing terminals)
- Support remote sessions (future enhancement)

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Lyra CLI                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Standard CLI │  │ Daemon Mode  │  │  TUI Mode    │     │
│  │   (current)  │  │   (new)      │  │   (new)      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Lyra Daemon (new)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Session Manager                         │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │  │
│  │  │ Session 1  │  │ Session 2  │  │ Session 3  │    │  │
│  │  └────────────┘  └────────────┘  └────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Event Loop                              │  │
│  │  - I/O multiplexing                                  │  │
│  │  - Agent process management                          │  │
│  │  - Client connection handling                        │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Persistence Layer                       │  │
│  │  - Session state serialization                       │  │
│  │  - Auto-save on changes                              │  │
│  │  - Restore on startup                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Processes                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Planner  │  │ Executor │  │ Reviewer │  │ Research │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Data Model

```python
# Core hierarchy
AgentSession
├── workspaces: Dict[str, AgentWorkspace]
├── active_workspace: Optional[str]
├── environment: Dict[str, str]
└── metadata: Dict[str, Any]

AgentWorkspace
├── panes: Dict[str, AgentPane]
├── active_pane: Optional[str]
├── layout: LayoutTree
└── status: WorkspaceStatus

AgentPane
├── agent_type: str
├── process: AgentProcess
├── output_buffer: RingBuffer
├── status: PaneStatus
├── size: Tuple[int, int]
└── notifications: List[Notification]
```

---

## Component Details

### 1. Session Manager

**Responsibilities:**
- Create/destroy sessions
- Manage session lifecycle
- Handle client attachments
- Coordinate persistence

**API:**

```python
class SessionManager:
    async def create_session(self, name: str, env: dict) -> str:
        """Create new session, return session ID"""
    
    async def attach_session(self, session_id: str, client: Client):
        """Attach client to session"""
    
    async def detach_session(self, session_id: str, client: Client):
        """Detach client from session"""
    
    async def destroy_session(self, session_id: str):
        """Destroy session and cleanup resources"""
    
    def list_sessions(self) -> List[SessionInfo]:
        """List all active sessions"""
```

### 2. Layout Manager

**Responsibilities:**
- Manage pane layout tree
- Handle split operations
- Resize panes automatically
- Serialize/deserialize layouts

**Layout Tree Structure:**

```
Window (100x50)
├─ HORIZONTAL (100x50)
   ├─ VERTICAL (50x50)
   │  ├─ Pane[planner] (50x25)
   │  └─ Pane[executor] (50x25)
   └─ Pane[reviewer] (50x50)
```

**Operations:**

```python
class LayoutManager:
    def split_horizontal(self, pane_id: str, ratio: float = 0.5) -> str:
        """Split pane horizontally, return new pane ID"""
    
    def split_vertical(self, pane_id: str, ratio: float = 0.5) -> str:
        """Split pane vertically, return new pane ID"""
    
    def resize_pane(self, pane_id: str, delta_w: int, delta_h: int):
        """Resize pane, redistribute space"""
    
    def close_pane(self, pane_id: str):
        """Close pane, redistribute space to siblings"""
    
    def serialize(self) -> str:
        """Serialize layout to string"""
    
    @staticmethod
    def deserialize(layout_str: str) -> LayoutTree:
        """Deserialize layout from string"""
```

### 3. Event Loop

**Responsibilities:**
- Non-blocking I/O multiplexing
- Agent process management
- Client connection handling
- Notification dispatch

**Architecture:**

```python
class EventLoop:
    def __init__(self):
        self.selector = selectors.DefaultSelector()
        self.handlers: Dict[int, IOHandler] = {}
        self.running = False
    
    def register_pane(self, pane: AgentPane):
        """Register pane for I/O events"""
    
    def unregister_pane(self, pane: AgentPane):
        """Unregister pane from event loop"""
    
    async def run(self):
        """Main event loop"""
        while self.running:
            events = self.selector.select(timeout=0.1)
            for key, mask in events:
                handler = key.data
                if mask & selectors.EVENT_READ:
                    handler.read_callback()
```

### 4. Status Bar

**Responsibilities:**
- Display session/workspace/pane metadata
- Show notifications
- Update in real-time
- Support format strings

**Format Variables:**

```
{session_name}       - Session name
{workspace_name}     - Workspace name
{pane_status}        - Pane status (idle/running/error)
{agent_type}         - Agent type (planner/executor/etc)
{notifications}      - Notification indicator
{time}               - Current time
{git_branch}         - Git branch (if available)
```

**Example Status Bars:**

```
# Default format
[research-session] main | planner:ready | 14:23:45 | ✓

# With notifications
[research-session] main | executor:running | 14:24:12 | 🔔 2

# Error state
[research-session] main | reviewer:failed | 14:25:03 | ❌
```

### 5. Notification System

**Responsibilities:**
- Collect notifications from agents
- Display visual indicators
- Manage notification panel
- Support priority levels

**Priority Levels:**

```python
class NotificationPriority(Enum):
    INFO = "info"        # Blue indicator
    WARNING = "warning"  # Yellow indicator
    ERROR = "error"      # Red indicator
    URGENT = "urgent"    # Magenta indicator, requires attention
```

**Visual Indicators:**

```
┌─ planner:ready ──────────────────────────────────────────┐
│ Output...                                                 │
│                                                           │
└───────────────────────────────────────────────────────────┘

┌─ executor:running ─────────────────────────────── 🔔 2 ──┐
│ Output...                                                 │
│                                                           │
└───────────────────────────────────────────────────────────┘

┌─ reviewer:failed ──────────────────────────────── ❌ ────┐
│ Error: Test failed                                        │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 6. Persistence Layer

**Responsibilities:**
- Serialize session state to disk
- Auto-save on changes
- Restore sessions on startup
- Handle migration

**State Format:**

```json
{
  "version": "1.0",
  "session": {
    "id": "sess_abc123",
    "name": "research-session",
    "created_at": "2026-05-29T14:23:45Z",
    "environment": {"LYRA_MODE": "research"},
    "metadata": {}
  },
  "workspaces": {
    "ws_main": {
      "id": "ws_main",
      "name": "main",
      "active_pane": "pane_1",
      "layout": "100x50,0,0[h:50x50,0,0[v:50x25,0,0,50x25,0,25],50x50,50,0]",
      "panes": {
        "pane_1": {
          "id": "pane_1",
          "agent_type": "planner",
          "status": "idle",
          "size": [50, 25],
          "working_directory": "/path/to/project"
        }
      }
    }
  }
}
```


---

## TUI Design

### Layout Examples

**Single Pane:**

```
┌─────────────────────────────────────────────────────────────┐
│ [research-session] main | planner:ready | 14:23:45 | ✓     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Planner Agent Output                                       │
│  > Analyzing requirements...                                │
│  > Creating implementation plan...                          │
│  > Plan complete                                            │
│                                                             │
│                                                             │
│                                                             │
│                                                             │
│                                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Horizontal Split:**

```
┌─────────────────────────────────────────────────────────────┐
│ [research-session] main | 2 panes | 14:23:45 | 🔔 1        │
├──────────────────────────────┬──────────────────────────────┤
│ planner:ready                │ executor:running       🔔 1  │
├──────────────────────────────┼──────────────────────────────┤
│                              │                              │
│ Planner Output               │ Executor Output              │
│ > Plan complete              │ > Running tests...           │
│                              │ > Test 1: PASS               │
│                              │ > Test 2: FAIL               │
│                              │ > Notification: Test failed  │
│                              │                              │
│                              │                              │
│                              │                              │
└──────────────────────────────┴──────────────────────────────┘
```

**Complex Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│ [research-session] main | 3 panes | 14:23:45 | 🔔 2        │
├──────────────────────────────┬──────────────────────────────┤
│ planner:ready                │ executor:running       🔔 1  │
├──────────────────────────────┼──────────────────────────────┤
│                              │                              │
│ Planner Output               │ Executor Output              │
│                              │                              │
├──────────────────────────────┴──────────────────────────────┤
│ reviewer:idle                                         🔔 1  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Reviewer Output                                             │
│ > Waiting for code to review...                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Notification Panel:**

```
┌─────────────────────────────────────────────────────────────┐
│ Notifications (2 unread)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ● 🔔 [14:24:12] executor: Test failed                      │
│    → Action: Review test output                             │
│                                                             │
│ ● ⚠ [14:23:58] reviewer: Code quality warning              │
│    → Action: Fix linting issues                             │
│                                                             │
│   ✓ [14:23:45] planner: Plan complete                      │
│                                                             │
│                                                             │
│ [Enter] Jump to notification  [c] Clear  [q] Close         │
└─────────────────────────────────────────────────────────────┘
```

### Keybindings

**Prefix Key:** `Ctrl+b` (configurable)

**Session Management:**
- `Ctrl+b s` - List sessions
- `Ctrl+b d` - Detach from session
- `Ctrl+b $` - Rename session

**Workspace Management:**
- `Ctrl+b c` - Create workspace
- `Ctrl+b n` - Next workspace
- `Ctrl+b p` - Previous workspace
- `Ctrl+b ,` - Rename workspace
- `Ctrl+b &` - Close workspace

**Pane Management:**
- `Ctrl+b %` - Split horizontally
- `Ctrl+b "` - Split vertically
- `Ctrl+b x` - Close pane
- `Ctrl+b o` - Next pane
- `Ctrl+b z` - Zoom pane (fullscreen toggle)
- `Ctrl+b {` - Swap with previous pane
- `Ctrl+b }` - Swap with next pane

**Navigation:**
- `Ctrl+b ↑/↓/←/→` - Focus pane in direction
- `Alt+↑/↓/←/→` - Resize pane (no prefix)

**Notifications:**
- `Ctrl+b !` - Show notification panel
- `Ctrl+b @` - Jump to next notification
- `Ctrl+b #` - Clear all notifications

**Other:**
- `Ctrl+b ?` - Show help
- `Ctrl+b :` - Command prompt

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1-2)

**Deliverables:**
- Session-Workspace-Pane data model
- Layout tree implementation
- Basic daemon with Unix socket
- Session persistence

**Files to Create:**
```
lyra-core/src/lyra_core/session/
├── __init__.py
├── models.py           # Session, Workspace, Pane classes
├── layout.py           # Layout tree implementation
├── manager.py          # SessionManager
└── persistence.py      # State serialization

lyra-core/src/lyra_core/daemon/
├── __init__.py
├── server.py           # Daemon server
├── client.py           # Client library
└── protocol.py         # IPC protocol
```

**Tests:**
- Layout tree operations (split, resize, close)
- Session persistence (save, restore)
- Daemon lifecycle (start, stop, restart)

### Phase 2: I/O and Display (Week 3-4)

**Deliverables:**
- Event loop with I/O multiplexing
- Status bar system
- Basic TUI rendering
- Agent process management

**Files to Create:**
```
lyra-core/src/lyra_core/daemon/
└── event_loop.py       # Event loop implementation

lyra-core/src/lyra_core/session/
└── status.py           # Status bar formatting

lyra-core/src/lyra_core/tui/
├── __init__.py
├── app.py              # Main TUI application
├── renderer.py         # Pane rendering
└── keybindings.py      # Keybinding manager
```

**Tests:**
- Event loop with multiple panes
- Status bar formatting
- TUI rendering

### Phase 3: Notifications and UX (Week 5-6)

**Deliverables:**
- Notification system
- Notification panel UI
- Complete keybinding framework
- Documentation

**Files to Create:**
```
lyra-core/src/lyra_core/session/
└── notifications.py    # Notification manager

lyra-core/src/lyra_core/tui/
├── notification_panel.py  # Notification UI
└── help_panel.py          # Help UI
```

**Tests:**
- Notification priority handling
- Visual indicators
- Keybinding dispatch

### Phase 4: Integration (Week 7-8)

**Deliverables:**
- Integrate with existing agent system
- CLI commands for daemon/TUI
- Migration guide
- User documentation

**CLI Commands:**
```bash
# Start daemon
lyra daemon start

# Attach to session
lyra attach [session-name]

# Create new session
lyra new-session [name]

# List sessions
lyra list-sessions

# Kill daemon
lyra daemon stop
```

---

## Migration Strategy

### Backward Compatibility

**Existing CLI remains unchanged:**
```bash
# Current usage still works
lyra research "topic"
lyra plan "feature"
lyra execute "task"
```

**New multiplexer is opt-in:**
```bash
# Start daemon mode
lyra daemon start

# Use TUI
lyra attach
```

### Gradual Adoption

**Phase 1:** Daemon mode optional, CLI works standalone
**Phase 2:** Encourage daemon for long-running tasks
**Phase 3:** Make daemon default, CLI auto-starts if needed

### Configuration

**New config options:**
```yaml
# ~/.lyra/config.yaml
multiplexer:
  enabled: true
  daemon:
    socket_path: ~/.lyra/daemon.sock
    auto_start: true
    auto_save_interval: 30
  
  tui:
    prefix_key: "ctrl+b"
    status_format:
      left: "{session_name} | {workspace_name}"
      center: "{pane_status} | {agent_type}"
      right: "{time} | {notifications}"
    
  persistence:
    state_dir: ~/.lyra/sessions
    auto_restore: true
```

---

## Performance Considerations

### Memory Usage

**Per Session:**
- Session metadata: ~1 KB
- Per workspace: ~500 bytes
- Per pane: ~2 KB + output buffer (10 KB default)

**Example:** 3 sessions × 2 workspaces × 3 panes = 18 panes
- Total: ~216 KB + 180 KB buffers = ~400 KB

### CPU Usage

**Event Loop:**
- Idle: <1% CPU (select() with timeout)
- Active: 2-5% CPU per active pane
- Status updates: <0.1% CPU (1 Hz)

**Optimization:**
- Use ring buffers for output (bounded memory)
- Lazy rendering (only redraw changed panes)
- Debounce status updates

### I/O Performance

**Non-blocking I/O:**
- No blocking on agent output
- Buffered writes to clients
- Efficient multiplexing with selectors

**Benchmarks (target):**
- Handle 50+ concurrent panes
- <10ms latency for output display
- <100ms for layout operations

---

## Security Considerations

### Unix Socket Permissions

**Socket file permissions:** 0700 (owner only)
**Socket directory:** `~/.lyra/` (user-owned)

### Process Isolation

**Agent processes:**
- Run as same user as daemon
- Inherit environment from session
- No privilege escalation

### State File Security

**Session state files:**
- Stored in `~/.lyra/sessions/`
- Permissions: 0600 (owner read/write only)
- No sensitive data in state (env vars only)

---

## Testing Strategy

### Unit Tests

**Layout Tree:**
- Split operations
- Resize with constraints
- Serialization/deserialization

**Session Management:**
- Create/destroy sessions
- Attach/detach clients
- Persistence

**Event Loop:**
- I/O multiplexing
- Handler registration
- Error handling

### Integration Tests

**End-to-End:**
- Start daemon, create session, attach client
- Split panes, run agents, verify output
- Detach, reattach, verify state
- Stop daemon, restart, restore sessions

**Performance:**
- 50 concurrent panes
- Rapid split/close operations
- Large output volumes

### Manual Testing

**UX Testing:**
- Keybinding responsiveness
- Visual layout correctness
- Notification visibility
- Status bar updates

---

## Future Enhancements

### Phase 2 Features

1. **Remote Sessions** - Attach to daemon over SSH
2. **Session Sharing** - Multiple users attach to same session
3. **Recording/Playback** - Record agent sessions for replay
4. **Custom Layouts** - Save/restore layout templates
5. **Floating Panes** - Overlay panes (like tmux popup)
6. **Tabbed Workspaces** - Alternative to split panes
7. **Browser Panes** - Embed browser like cmux
8. **Git Integration** - Show branch/PR status like cmux

### Advanced Features

1. **Distributed Sessions** - Agents run on different machines
2. **GPU Monitoring** - Show GPU usage in status bar
3. **Log Aggregation** - Centralized logging across panes
4. **Metrics Dashboard** - Real-time performance metrics
5. **Plugin System** - Custom pane types and layouts

---

## References

### Source Code Analysis

- **tmux:** https://github.com/tmux/tmux
  - `session.c` - Session management with reference counting
  - `window.c` - Window/pane hierarchy
  - `layout.c` - Recursive layout tree
  - `server.c` - Event loop and client handling
  - `status.c` - Status bar formatting

- **cmux:** https://github.com/manaflow-ai/cmux
  - AI-focused notification system
  - Vertical tabs with metadata
  - Claude Code Teams integration

- **rmux:** https://github.com/Helvesec/rmux
  - Modern Rust implementation
  - Async/await with Tokio
  - Type-safe architecture

### Related Documents

- `.omc/research/US-011-multiplexer-analysis.md` - Detailed pattern analysis
- `docs/architecture/agent-swarm.md` - Multi-agent coordination
- `docs/architecture/system-overview.md` - Overall Lyra architecture

---

## Appendix: API Reference

### Session Manager API

```python
class SessionManager:
    async def create_session(
        self, 
        name: str, 
        env: Dict[str, str] = None
    ) -> str:
        """Create new session, return session ID"""
    
    async def attach_session(
        self, 
        session_id: str, 
        client: Client
    ) -> AgentSession:
        """Attach client to session, return session object"""
    
    async def detach_session(
        self, 
        session_id: str, 
        client: Client
    ):
        """Detach client from session"""
    
    async def destroy_session(self, session_id: str):
        """Destroy session and cleanup resources"""
    
    def list_sessions(self) -> List[SessionInfo]:
        """List all active sessions"""
    
    async def create_workspace(
        self, 
        session_id: str, 
        name: str
    ) -> str:
        """Create workspace in session, return workspace ID"""
    
    async def split_pane(
        self,
        session_id: str,
        workspace_id: str,
        pane_id: str,
        direction: str,  # 'horizontal' or 'vertical'
        agent_type: str
    ) -> str:
        """Split pane, return new pane ID"""
```

### Layout Manager API

```python
class LayoutManager:
    def split_horizontal(
        self, 
        pane_id: str, 
        ratio: float = 0.5
    ) -> str:
        """Split pane horizontally, return new pane ID"""
    
    def split_vertical(
        self, 
        pane_id: str, 
        ratio: float = 0.5
    ) -> str:
        """Split pane vertically, return new pane ID"""
    
    def resize_pane(
        self, 
        pane_id: str, 
        delta_width: int, 
        delta_height: int
    ):
        """Resize pane, redistribute space"""
    
    def close_pane(self, pane_id: str):
        """Close pane, redistribute space to siblings"""
    
    def get_pane_geometry(self, pane_id: str) -> Tuple[int, int, int, int]:
        """Get pane geometry (x, y, width, height)"""
    
    def serialize(self) -> str:
        """Serialize layout to string"""
    
    @staticmethod
    def deserialize(layout_str: str) -> LayoutTree:
        """Deserialize layout from string"""
```

### Notification Manager API

```python
class NotificationManager:
    def add_notification(
        self,
        pane_id: str,
        priority: NotificationPriority,
        message: str,
        source: str,
        action: Optional[str] = None
    ):
        """Add notification for pane"""
    
    def get_unread(
        self, 
        pane_id: Optional[str] = None
    ) -> List[Notification]:
        """Get unread notifications"""
    
    def mark_read(self, notification_id: str):
        """Mark notification as read"""
    
    def clear_pane(self, pane_id: str):
        """Clear all notifications for pane"""
    
    def on_notification(self, handler: Callable):
        """Register notification handler"""
```


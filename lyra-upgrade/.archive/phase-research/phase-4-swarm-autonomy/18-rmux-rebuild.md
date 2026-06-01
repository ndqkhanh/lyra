# §5.1 Implementation Plan: rmux Rebuild for Lyra

**Status**: PLAN  
**Priority**: MED×HIGH (P2)  
**Effort**: 3-4 weeks  
**Dependencies**: lyra-core architecture

---

## 1. Overview

Clean-room rebuild of rmux capabilities for Lyra, providing:
- **Persistent sessions** that survive disconnection
- **Typed SDK** for programmatic terminal control
- **Cross-platform support** (Linux, macOS, Windows)
- **Terminal automation** with structured snapshots
- **Agent coordination** primitives

**Key Differences from rmux**:
- TypeScript/Node.js instead of Rust (align with Lyra stack)
- Integrated with Lyra's agent system (not standalone)
- Built-in channel communication (§4.13 integration)
- Optimized for AI agent workflows (not general terminal multiplexing)

**Design Philosophy**: "Primitives for agent coordination" — provide low-level building blocks for terminal control, session management, and agent communication without prescribing high-level workflows.

---

## 2. Architecture

### 2.1 Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Lyra Terminal Daemon                      │
│  - Session management                                        │
│  - PTY lifecycle                                             │
│  - IPC server (Unix sockets / Named Pipes)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─────────────────┬──────────────┐
                              ▼                 ▼              ▼
                    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
                    │  Session 1   │  │  Session 2   │  │  Session N   │
                    │  - Panes     │  │  - Panes     │  │  - Panes     │
                    │  - Layout    │  │  - Layout    │  │  - Layout    │
                    └──────────────┘  └──────────────┘  └──────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Lyra SDK       │
                    │  - TypeScript    │
                    │  - Type-safe     │
                    │  - Promise-based │
                    └──────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Agent 1 │  │  Agent 2 │  │  Agent N │
        │  (CLI)   │  │  (SDK)   │  │  (SDK)   │
        └──────────┘  └──────────┘  └──────────┘
```

### 2.2 Session Model

**Hierarchy**:
- **Daemon**: Single persistent process managing all sessions
- **Session**: Named container for panes (e.g., "research-task-1")
- **Pane**: Individual PTY with running process
- **Layout**: Arrangement of panes (horizontal/vertical splits)

**Session Lifecycle**:
1. Create session (detached or attached)
2. Add panes to session
3. Send commands to panes
4. Read output from panes
5. Detach from session (session continues running)
6. Reattach to session later
7. Destroy session when done

### 2.3 IPC Protocol

**Transport**:
- Linux/macOS: Unix domain sockets (`/tmp/lyra-terminal.sock`)
- Windows: Named Pipes (`\\.\pipe\lyra-terminal`)

**Message Format** (JSON-RPC 2.0):
```typescript
interface RPCRequest {
  jsonrpc: '2.0';
  id: string | number;
  method: string;
  params?: unknown;
}

interface RPCResponse {
  jsonrpc: '2.0';
  id: string | number;
  result?: unknown;
  error?: RPCError;
}

interface RPCError {
  code: number;
  message: string;
  data?: unknown;
}
```

**Methods**:
- `session.create` - Create new session
- `session.list` - List all sessions
- `session.get` - Get session details
- `session.destroy` - Destroy session
- `pane.create` - Create pane in session
- `pane.send` - Send text to pane
- `pane.snapshot` - Get current pane content
- `pane.waitFor` - Wait for text to appear
- `pane.resize` - Resize pane
- `pane.destroy` - Destroy pane

---

## 3. Implementation Phases

### Phase 1: Daemon Core (Week 1)

**Tasks**:
1. Implement daemon process with IPC server
2. Add session management (create, list, get, destroy)
3. Add PTY lifecycle management (spawn, resize, kill)
4. Implement Unix socket server (Linux/macOS)
5. Implement Named Pipe server (Windows)
6. Write unit tests

**Deliverables**:
- `packages/lyra-terminal/src/daemon/`
- `packages/lyra-terminal/src/daemon/server.ts`
- `packages/lyra-terminal/src/daemon/session-manager.ts`
- `packages/lyra-terminal/src/daemon/pty-manager.ts`
- Unit tests

**Acceptance Criteria**:
- Daemon starts and listens on IPC socket
- Sessions can be created and destroyed
- PTYs spawn correctly on all platforms
- IPC communication works bidirectionally

### Phase 2: SDK Implementation (Week 1-2)

**Tasks**:
1. Implement TypeScript SDK with typed API
2. Add session operations (create, list, get, destroy)
3. Add pane operations (create, send, snapshot, waitFor, resize, destroy)
4. Add connection pooling and reconnection logic
5. Write SDK tests

**Deliverables**:
- `packages/lyra-terminal/src/sdk/`
- `packages/lyra-terminal/src/sdk/client.ts`
- `packages/lyra-terminal/src/sdk/session.ts`
- `packages/lyra-terminal/src/sdk/pane.ts`
- SDK tests

**Acceptance Criteria**:
- SDK connects to daemon successfully
- All operations work with type safety
- Reconnection logic handles daemon restarts
- Promise-based API is ergonomic

### Phase 3: Terminal Automation (Week 2-3)

**Tasks**:
1. Implement structured snapshot format
2. Add text matching and waiting
3. Add cursor position tracking
4. Add scrollback buffer management
5. Write automation tests

**Deliverables**:
- `packages/lyra-terminal/src/automation/`
- `packages/lyra-terminal/src/automation/snapshot.ts`
- `packages/lyra-terminal/src/automation/matcher.ts`
- Automation tests

**Acceptance Criteria**:
- Snapshots capture full terminal state
- Text matching works with regex and fuzzy matching
- Wait operations timeout correctly
- Scrollback buffer preserves history

### Phase 4: Agent Integration (Week 3-4)

**Tasks**:
1. Integrate with Lyra's agent system
2. Add channel communication for terminal events
3. Implement agent-to-terminal bindings
4. Add terminal session persistence
5. Write integration tests

**Deliverables**:
- `packages/lyra-terminal/src/agent-integration/`
- Integration with §4.13 channel system
- Integration tests

**Acceptance Criteria**:
- Agents can control terminals via SDK
- Terminal events published to channels
- Agent-to-terminal bindings work
- Sessions persist across agent restarts

---

## 4. API Design

### 4.1 Daemon Management

```typescript
import { TerminalDaemon } from '@lyra/terminal/daemon';

// Start daemon
const daemon = new TerminalDaemon({
  socketPath: '/tmp/lyra-terminal.sock', // Unix socket
  // or
  pipeName: '\\\\.\\pipe\\lyra-terminal', // Windows Named Pipe
});

await daemon.start();

// Stop daemon
await daemon.stop();
```

### 4.2 SDK Usage

```typescript
import { TerminalClient } from '@lyra/terminal/sdk';

// Connect to daemon
const client = new TerminalClient({
  socketPath: '/tmp/lyra-terminal.sock',
});

await client.connect();

// Create session
const session = await client.createSession({
  name: 'research-task-1',
  detached: true,
});

// Create pane
const pane = await session.createPane({
  command: '/bin/bash',
  cwd: '/home/user/project',
  env: { TERM: 'xterm-256color' },
});

// Send command
await pane.send('npm install\n');

// Wait for completion
await pane.waitFor('added', { timeout: 30000 });

// Get snapshot
const snapshot = await pane.snapshot();
console.log(snapshot.text);

// Destroy pane
await pane.destroy();

// Destroy session
await session.destroy();

// Disconnect
await client.disconnect();
```

### 4.3 Structured Snapshots

```typescript
interface PaneSnapshot {
  // Raw content
  text: string;           // Plain text content
  lines: string[];        // Array of lines
  
  // Cursor state
  cursor: {
    row: number;
    col: number;
  };
  
  // Dimensions
  rows: number;
  cols: number;
  
  // Scrollback
  scrollback: string[];   // Lines above viewport
  
  // Metadata
  timestamp: number;
  paneId: string;
}

// Usage
const snapshot = await pane.snapshot();

// Check if text appears
if (snapshot.text.includes('Build successful')) {
  console.log('Build completed!');
}

// Get specific line
const lastLine = snapshot.lines[snapshot.lines.length - 1];

// Check cursor position
if (snapshot.cursor.row === snapshot.rows - 1) {
  console.log('Cursor at bottom');
}
```

### 4.4 Text Matching and Waiting

```typescript
// Wait for exact text
await pane.waitFor('Build successful', { timeout: 60000 });

// Wait for regex match
await pane.waitFor(/Tests: \d+ passed/, { timeout: 30000 });

// Wait for multiple conditions (OR)
await pane.waitFor(['Success', 'Complete', 'Done'], { timeout: 10000 });

// Wait with custom matcher
await pane.waitFor((snapshot) => {
  return snapshot.text.includes('ready') && snapshot.cursor.row > 10;
}, { timeout: 5000 });

// Wait with polling interval
await pane.waitFor('ready', { 
  timeout: 10000,
  pollInterval: 100, // Check every 100ms
});
```

### 4.5 Session Persistence

```typescript
// Create session with persistence
const session = await client.createSession({
  name: 'long-running-task',
  detached: true,
  persist: true, // Save state to disk
});

// Later, reconnect to session
const sessions = await client.listSessions();
const existingSession = sessions.find(s => s.name === 'long-running-task');

if (existingSession) {
  const session = await client.getSession(existingSession.id);
  const panes = await session.listPanes();
  
  // Reattach to existing pane
  const pane = panes[0];
  const snapshot = await pane.snapshot();
  console.log('Resumed session:', snapshot.text);
}
```

---

## 5. Agent Integration

### 5.1 Agent-to-Terminal Binding

```typescript
import { bindAgentToTerminal } from '@lyra/terminal/agent-integration';

// Bind agent to terminal session
const binding = await bindAgentToTerminal({
  agentId: 'agent-123',
  sessionName: 'agent-123-terminal',
  channelSystem: channelSystem, // From §4.13
});

// Agent sends command via channel
await channelSystem.publish({
  channel: 'terminal-commands',
  sender: 'agent-123',
  type: 'command',
  payload: { command: 'npm test' },
});

// Terminal publishes output to channel
binding.on('output', async (output) => {
  await channelSystem.publish({
    channel: 'terminal-output',
    sender: 'terminal-daemon',
    type: 'output',
    payload: { agentId: 'agent-123', text: output },
  });
});

// Terminal publishes events to channel
binding.on('command-complete', async (result) => {
  await channelSystem.publish({
    channel: 'terminal-events',
    sender: 'terminal-daemon',
    type: 'event',
    payload: { 
      agentId: 'agent-123',
      event: 'command-complete',
      exitCode: result.exitCode,
    },
  });
});
```

### 5.2 Multi-Agent Coordination

```typescript
// Orchestrator spawns multiple agents with terminals
const agents = await Promise.all([
  spawnAgentWithTerminal('agent-1', 'npm run build'),
  spawnAgentWithTerminal('agent-2', 'npm run test'),
  spawnAgentWithTerminal('agent-3', 'npm run lint'),
]);

// Wait for all to complete
const results = await Promise.all(
  agents.map(agent => agent.waitForCompletion())
);

// Aggregate results
const allSucceeded = results.every(r => r.exitCode === 0);
console.log('All tasks succeeded:', allSucceeded);
```

---

## 6. Cross-Platform Considerations

### 6.1 PTY Implementation

**Linux/macOS**: Use `node-pty` package
```typescript
import * as pty from 'node-pty';

const ptyProcess = pty.spawn('/bin/bash', [], {
  name: 'xterm-256color',
  cols: 80,
  rows: 24,
  cwd: process.cwd(),
  env: process.env,
});
```

**Windows**: Use `node-pty` with ConPTY
```typescript
const ptyProcess = pty.spawn('powershell.exe', [], {
  name: 'xterm-256color',
  cols: 80,
  rows: 24,
  cwd: process.cwd(),
  env: process.env,
  useConpty: true, // Use Windows ConPTY
});
```

### 6.2 IPC Transport

**Unix Sockets** (Linux/macOS):
```typescript
import * as net from 'net';

const server = net.createServer((socket) => {
  socket.on('data', (data) => {
    const request = JSON.parse(data.toString());
    const response = handleRequest(request);
    socket.write(JSON.stringify(response));
  });
});

server.listen('/tmp/lyra-terminal.sock');
```

**Named Pipes** (Windows):
```typescript
import * as net from 'net';

const server = net.createServer((socket) => {
  socket.on('data', (data) => {
    const request = JSON.parse(data.toString());
    const response = handleRequest(request);
    socket.write(JSON.stringify(response));
  });
});

server.listen('\\\\.\\pipe\\lyra-terminal');
```

### 6.3 Shell Detection

```typescript
function getDefaultShell(): string {
  if (process.platform === 'win32') {
    return process.env.COMSPEC || 'cmd.exe';
  } else {
    return process.env.SHELL || '/bin/bash';
  }
}
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

- Daemon lifecycle (start, stop, restart)
- Session management (create, list, get, destroy)
- PTY lifecycle (spawn, resize, kill)
- IPC protocol (request/response, error handling)
- SDK operations (all methods)

### 7.2 Integration Tests

- End-to-end session creation and command execution
- Multi-pane coordination
- Session persistence across daemon restarts
- Agent-to-terminal binding
- Cross-platform compatibility (Linux, macOS, Windows)

### 7.3 Automation Tests

- Text matching with various patterns
- Wait operations with timeouts
- Snapshot accuracy
- Scrollback buffer management

### 7.4 Performance Tests

- Session creation latency (<100ms)
- Command execution overhead (<10ms)
- Snapshot generation time (<50ms)
- IPC throughput (1000+ requests/sec)
- Memory usage (<50MB per session)

---

## 8. Security Considerations

1. **Socket permissions**: Unix socket restricted to user (chmod 600)
2. **Command injection**: Validate all commands before execution
3. **Resource limits**: Limit number of sessions/panes per user
4. **Sandbox execution**: PTYs run with restricted permissions
5. **Audit trail**: Log all terminal commands for forensic analysis

---

## 9. Monitoring & Observability

**Metrics**:
- Active sessions count
- Active panes count
- Command execution rate (commands/sec)
- IPC request rate (requests/sec)
- Memory usage per session
- PTY spawn failures

**Logging**:
- Session lifecycle events (info)
- Command executions (debug)
- IPC errors (error)
- PTY failures (error)

**Tracing**:
- Distributed tracing for agent-to-terminal operations
- Trace ID propagated through IPC messages

---

## 10. Comparison with rmux

| Feature | rmux | Lyra Terminal |
|---------|------|---------------|
| Language | Rust | TypeScript/Node.js |
| Platform | Linux, macOS, Windows | Linux, macOS, Windows |
| IPC | Unix sockets, Named Pipes | Unix sockets, Named Pipes |
| SDK | Rust SDK | TypeScript SDK |
| Integration | Standalone | Integrated with Lyra |
| Channel System | No | Yes (§4.13) |
| Agent Coordination | Manual | Built-in |
| Graphics Passthrough | Kitty, SIXEL | Not yet (future) |
| License | MIT/Apache-2.0 | MIT |

**Key Advantages of Lyra Terminal**:
1. Native TypeScript integration with Lyra ecosystem
2. Built-in channel communication for agent coordination
3. Optimized for AI agent workflows
4. Integrated with Lyra's swarm and autonomy systems

**Trade-offs**:
- Rust performance vs TypeScript ecosystem fit
- Standalone tool vs integrated component
- General terminal multiplexing vs agent-specific primitives

---

## 11. Future Enhancements

1. **Graphics passthrough**: Support Kitty graphics and SIXEL protocols
2. **Terminal recording**: Record and replay terminal sessions
3. **Collaborative terminals**: Multiple agents share same terminal
4. **Terminal streaming**: Stream terminal output to web UI
5. **Terminal snapshots**: Save/restore terminal state
6. **Terminal search**: Search through scrollback history
7. **Terminal themes**: Customizable color schemes

---

## 12. Success Criteria

- [ ] Daemon starts and manages sessions successfully
- [ ] SDK provides type-safe API for all operations
- [ ] Sessions persist across daemon restarts
- [ ] Text matching and waiting work correctly
- [ ] Agent-to-terminal binding works
- [ ] Cross-platform support (Linux, macOS, Windows)
- [ ] Performance targets met (<100ms session creation, 1000+ req/sec)
- [ ] Integration tests pass on all platforms
- [ ] Documentation complete with examples

---

## 13. References

- rmux: Rust multiplexer, typed SDK, persistent sessions, terminal automation
- tmux: Client-server model, session hierarchy, IPC patterns
- node-pty: Cross-platform PTY implementation for Node.js
- JSON-RPC 2.0: IPC protocol specification

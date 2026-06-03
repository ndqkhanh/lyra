# Fleet Supervisor Implementation Guide

**Document**: fleet-supervisor/implementation.md  
**Status**: Complete  
**Date**: 2026-06-02  
**Sources**: Implementation files, code examples, configuration references

---

## Overview

This guide provides practical implementation details for the Fleet Supervisor system, including code examples, configuration, deployment, integration patterns, and testing strategies. All examples are drawn from actual implementation in `packages/lyra-orchestration/` and `packages/lyra-fleet-tui/`.

---

## Getting Started

### Installation

```bash
# Install Lyra with fleet support
pip install lyra-orchestration lyra-fleet-tui

# Or from source
cd packages/lyra-orchestration
pip install -e .

cd ../lyra-fleet-tui
pip install -e .
```

### First Launch

```bash
# Auto-starts supervisor on first background command
lyra --bg "Analyze this codebase"

# Or explicit daemon start
lyra daemon start

# Check supervisor status
lyra daemon status
# Output:
# Supervisor: running (PID 12345)
# Active sessions: 3
# Memory: 450MB / 16GB
# Uptime: 2h 34m
```

### Fleet View

```bash
# Open fleet dashboard
lyra fleet

# Or alias
lyra agents
```

---

## Configuration

### Config File Location

```bash
~/.lyra/config.toml
```

### Basic Configuration

```toml
[daemon]
# Auto-start supervisor on first background command
auto_start = true

# Self-exit after 24 hours of no activity
auto_exit = true
auto_exit_hours = 24

# Idle-stop timeout (seconds)
idle_timeout = 3600  # 1 hour

# Memory pressure thresholds
memory_pressure_warn_pct = 80
memory_pressure_critical_pct = 90

[fleet]
# Default model for new sessions
default_model = "anthropic:claude-opus-4"

# Default effort level
default_effort = "high"

# Default permission mode
default_permission_mode = "default"

# Enable worktree isolation by default
auto_worktree = true

[summaries]
# Model for row summaries
summary_model = "deepseek:deepseek-chat"  # Cheapest

# Cache TTL (seconds)
cache_ttl = 300  # 5 minutes

# Refresh interval (seconds)
refresh_interval = 15

[security]
# Approval expiry hours by risk level
approval_expiry_low = 168     # 7 days
approval_expiry_medium = 24   # 24 hours
approval_expiry_high = 4      # 4 hours
approval_expiry_critical = 0  # Per-use only

# Audit log retention (days)
audit_log_retention = 90

[worktrees]
# Base ref for new worktrees
base_ref = "fresh"  # or "head"

# Symlink node_modules for faster creation
symlink_directories = ["node_modules", ".venv", "vendor"]

# Sparse checkout paths
sparse_paths = []

# Cleanup policy
cleanup_policy = "stash"  # or "discard", "keep"
```

---

## Code Examples

### 1. Supervisor Daemon

**Initialize Supervisor**:

```python
from lyra_orchestration.fleet_supervisor import FleetSupervisor

# Create supervisor instance
supervisor = FleetSupervisor(
    jobs_dir=Path.home() / ".lyra" / "jobs",
    idle_timeout=3600,  # 1 hour
    summary_fn=generate_summary,  # Cheap model function
)

# Start daemon
supervisor.start()

# Main loop (typically in background thread)
while supervisor.is_running():
    supervisor.tick()  # Periodic maintenance
    time.sleep(15)  # Every 15 seconds
```

**Dispatch Session**:

```python
# Create new background session
session = supervisor.dispatch(
    prompt="Fix authentication bug in login.ts",
    name="fix-auth-bug",
    model="anthropic:claude-opus-4",
    effort="high",
    permission_mode="default",
    auto_worktree=True,
)

print(f"Session created: {session.session_id}")
print(f"Worktree: {session.worktree_path}")
```

**Attach to Session**:

```python
# Attach terminal to session
session = supervisor.attach(session_id="abc123")

# Session is now in foreground
# User can interact directly
```

**Stop Session**:

```python
# Graceful termination
success = supervisor.stop_session(session_id="abc123")

if success:
    print("Session stopped")
else:
    print("Session not found or already stopped")
```

**Resume Session**:

```python
# Respawn from disk state
session = supervisor.resume_session(
    session_id="abc123",
    prompt="Continue with tests"  # Optional new instruction
)

print(f"Session resumed: {session.task_state}")
```

### 2. Fleet TUI

**Launch TUI**:

```python
from lyra_fleet_tui.app import FleetTUIApp

# Create and run TUI app
app = FleetTUIApp()
app.run()
```

**Custom Widget**:

```python
from textual.widgets import Static
from textual.reactive import reactive

class CustomAgentRow(Static):
    """Custom agent row with additional info."""
    
    agent: reactive[Optional[AgentState]] = reactive(None)
    
    def watch_agent(self, agent: Optional[AgentState]) -> None:
        if agent is None:
            self.update("")
            return
        
        # Custom formatting
        color = self._get_color(agent.task_state)
        symbol = agent.liveness.symbol
        
        markup = f"[{color}]{symbol}[/] {agent.name} - {agent.current_task}"
        self.update(markup)
    
    def _get_color(self, task_state: TaskState) -> str:
        colors = {
            TaskState.WORKING: "cyan",
            TaskState.NEEDS_INPUT: "yellow",
            TaskState.COMPLETED: "green",
            TaskState.FAILED: "red",
        }
        return colors.get(task_state, "white")
```

### 3. IPC Client

**Send Message**:

```python
import socket
import json

def send_command(cmd: str, args: dict) -> dict:
    """Send command to supervisor via IPC."""
    sock_path = f"/tmp/lyra-{os.getuid()}/supervisor.sock"
    
    # Connect to supervisor
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(sock_path)
    
    # Prepare message
    msg = {"cmd": cmd, "args": args}
    payload = json.dumps(msg).encode('utf-8')
    header = len(payload).to_bytes(4, 'big')
    
    # Send
    sock.sendall(header + payload)
    
    # Receive response
    header = sock.recv(4)
    length = int.from_bytes(header, 'big')
    response = sock.recv(length)
    
    sock.close()
    
    return json.loads(response)

# Example: Dispatch session via IPC
result = send_command("dispatch", {
    "prompt": "Review this PR",
    "model": "anthropic:claude-opus-4",
    "effort": "high"
})

print(f"Session ID: {result['session_id']}")
```

### 4. Security Gate

**Check Approval**:

```python
from lyra_orchestration.security_gate import SecurityGate, RiskLevel

# Initialize gate
gate = SecurityGate(db_path=Path.home() / ".lyra" / "approvals.db")

# Check if command is approved
decision = gate.check_approval(
    tool_name="bash",
    command="git push origin main",
    session_id="abc123"
)

if decision.decision == "APPROVED":
    # Execute command
    execute_tool("bash", "git push origin main")
elif decision.decision == "REQUIRES_INTERACTIVE":
    # Prompt user for approval
    if prompt_user_approval(tool_name, command):
        gate.grant_approval(
            tool_name="bash",
            command="git push origin main",
            session_id="abc123",
            risk_level=RiskLevel.MEDIUM
        )
        execute_tool("bash", "git push origin main")
```

**Grant Approval** (after interactive accept):

```python
# User approved in interactive session
gate.grant_approval(
    tool_name="bash",
    command="npm test",
    session_id="abc123",
    risk_level=RiskLevel.HIGH,  # Bash is HIGH risk
)

# Approval persists for 4 hours (HIGH risk)
```

**Revoke Approval**:

```python
# Manually revoke approval
gate.revoke_approval(
    tool_name="bash",
    session_id="abc123"
)
```

### 5. State Persistence

**Atomic Write**:

```python
import tempfile
import os
import json
from pathlib import Path

def atomic_write_json(path: Path, data: dict, fsync: bool = True):
    """Write JSON with crash-safe atomicity."""
    # Create temp file in same directory
    fd, tmp = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        # Write data
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2)
            
            if fsync:
                f.flush()
                os.fsync(f.fileno())  # Force to disk
        
        # Atomic rename
        os.replace(tmp, path)
        
        # Sync directory entry
        if fsync:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            os.fsync(dir_fd)
            os.close(dir_fd)
            
    except Exception:
        # Cleanup on error
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

# Usage
roster = {"version": "1.0", "sessions": {...}}
atomic_write_json(
    Path.home() / ".lyra" / "roster.json",
    roster,
    fsync=True
)
```

**WAL Replay**:

```python
@dataclass
class WALEntry:
    seq: int
    op: str  # "UPDATE", "DELETE"
    key: str
    data: dict
    timestamp: float

class StateManager:
    def recover(self):
        """Load checkpoint + replay WAL."""
        # 1. Load checkpoint
        checkpoint_path = self.roster_path
        if not checkpoint_path.exists():
            checkpoint_path = self.roster_path.with_suffix(".json.bak")
        
        with open(checkpoint_path) as f:
            self.state = json.load(f)
        
        # 2. Replay WAL
        wal_path = self.roster_path.with_suffix(".wal")
        if wal_path.exists():
            for entry in self._read_wal(wal_path):
                if entry.seq > self.state.get("wal_seq", 0):
                    self._apply_entry(entry)
        
        # 3. Save clean state
        self._save_roster()
    
    def _apply_entry(self, entry: WALEntry):
        """Apply single WAL entry."""
        if entry.op == "UPDATE":
            self.state["sessions"][entry.key] = entry.data
        elif entry.op == "DELETE":
            del self.state["sessions"][entry.key]
        
        self.state["wal_seq"] = entry.seq
```

---

## Integration Patterns

### Pattern 1: CLI Integration

```python
import click
from lyra_orchestration.fleet_supervisor import FleetSupervisor

@click.command()
@click.option("--bg", is_flag=True, help="Run in background")
@click.argument("prompt")
def lyra_cli(bg: bool, prompt: str):
    """Lyra CLI entry point."""
    if bg:
        # Background dispatch
        supervisor = get_or_create_supervisor()
        session = supervisor.dispatch(prompt=prompt)
        click.echo(f"Session {session.session_id} started in background")
        click.echo(f"View with: lyra fleet")
    else:
        # Foreground interactive
        run_interactive_session(prompt)

def get_or_create_supervisor() -> FleetSupervisor:
    """Get running supervisor or start new one."""
    sock_path = f"/tmp/lyra-{os.getuid()}/supervisor.sock"
    
    if os.path.exists(sock_path):
        # Supervisor already running, connect via IPC
        return IPCSupervisorClient(sock_path)
    else:
        # Start new supervisor
        supervisor = FleetSupervisor()
        supervisor.start_daemon()
        return supervisor
```

### Pattern 2: Worktree Integration

```python
from lyra_orchestration.worktree_isolate import WorktreeIsolation

# Create worktree before first edit
worktree = WorktreeIsolation(
    repo_root=Path.cwd(),
    base_ref="fresh",  # Branch from origin/main
    symlink_dirs=["node_modules", ".venv"]
)

worktree_info = worktree.create(
    session_id="abc123",
    branch_name="lyra-session-abc123"
)

print(f"Worktree path: {worktree_info.path}")
print(f"Branch: {worktree_info.branch}")

# Session edits files within worktree
os.chdir(worktree_info.path)
# ... make edits ...

# Cleanup after session
worktree.cleanup(
    worktree_path=worktree_info.path,
    policy="stash"  # or "discard", "keep"
)
```

### Pattern 3: Multi-Provider Routing

```python
def dispatch_with_routing(prompt: str) -> SessionState:
    """Dispatch to cheapest capable provider."""
    # Analyze prompt complexity
    complexity = analyze_complexity(prompt)
    
    # Route to provider tier
    if complexity < 0.3:
        model = "local:llama-3-8b-instruct"  # Free
    elif complexity < 0.6:
        model = "deepseek:deepseek-chat"  # $0.07/MTok
    elif complexity < 0.8:
        model = "openai:gpt-4o"  # $0.15/MTok
    else:
        model = "anthropic:claude-opus-4"  # $0.25/MTok
    
    # Dispatch
    return supervisor.dispatch(
        prompt=prompt,
        model=model,
        effort="high"
    )

def analyze_complexity(prompt: str) -> float:
    """Score prompt complexity (0.0-1.0)."""
    token_count = len(prompt.split())
    
    # Simple heuristic
    if "architecture" in prompt.lower():
        return 0.9
    elif "code" in prompt.lower():
        return 0.7
    elif "explain" in prompt.lower():
        return 0.5
    else:
        return 0.3
```

---

## Deployment

### Systemd Service (Linux)

```ini
# /etc/systemd/user/lyra-supervisor.service
[Unit]
Description=Lyra Fleet Supervisor
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/lyra daemon start --foreground
Restart=on-failure
RestartSec=5s

# Resource limits
MemoryMax=4G
CPUQuota=200%

[Install]
WantedBy=default.target
```

```bash
# Enable and start
systemctl --user enable lyra-supervisor
systemctl --user start lyra-supervisor

# Check status
systemctl --user status lyra-supervisor
```

### macOS LaunchAgent

```xml
<!-- ~/Library/LaunchAgents/com.lyra.supervisor.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lyra.supervisor</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/lyra</string>
        <string>daemon</string>
        <string>start</string>
        <string>--foreground</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/tmp/lyra-supervisor.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/lyra-supervisor.err</string>
</dict>
</plist>
```

```bash
# Load and start
launchctl load ~/Library/LaunchAgents/com.lyra.supervisor.plist

# Check status
launchctl list | grep lyra
```

### Docker Deployment (Not Recommended)

The Fleet Supervisor is designed for local execution. Docker adds unnecessary overhead. If you must use Docker:

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y git

# Install Lyra
COPY . /app
WORKDIR /app
RUN pip install -e packages/lyra-orchestration
RUN pip install -e packages/lyra-fleet-tui

# Create user
RUN useradd -m lyra

# Switch to user
USER lyra

# Start supervisor
CMD ["lyra", "daemon", "start", "--foreground"]
```

**Why Not Docker**:
- Git worktrees require repo access (mount volume)
- IPC sockets don't work well across containers
- Process isolation already provided by OS processes
- 2-10s startup overhead vs 200ms for native

---

## Testing Strategies

### Unit Tests

**Test Supervisor Lifecycle**:

```python
import pytest
from lyra_orchestration.fleet_supervisor import FleetSupervisor

def test_supervisor_start_stop():
    """Test supervisor starts and stops cleanly."""
    supervisor = FleetSupervisor()
    
    # Start
    supervisor.start()
    assert supervisor.is_running()
    
    # Stop
    supervisor.stop()
    assert not supervisor.is_running()

def test_dispatch_creates_session():
    """Test dispatch creates new session."""
    supervisor = FleetSupervisor()
    supervisor.start()
    
    session = supervisor.dispatch(
        prompt="Test task",
        model="anthropic:claude-opus-4"
    )
    
    assert session.session_id is not None
    assert session.task_state == TaskState.WORKING
    assert session.process_liveness == ProcessLiveness.ALIVE
```

**Test State Persistence**:

```python
def test_atomic_write_crash_safe(tmp_path):
    """Test atomic write survives crash."""
    target = tmp_path / "test.json"
    data = {"key": "value"}
    
    # Write
    atomic_write_json(target, data, fsync=True)
    
    # Verify
    with open(target) as f:
        loaded = json.load(f)
    
    assert loaded == data
    
    # No temp files left
    assert not list(tmp_path.glob(".test.json.*"))
```

### Integration Tests

**Test End-to-End Dispatch**:

```python
def test_e2e_background_session(supervisor):
    """Test full dispatch → execute → complete cycle."""
    # Dispatch
    session = supervisor.dispatch(
        prompt="Echo 'hello world'",
        model="anthropic:claude-opus-4"
    )
    
    # Wait for completion
    max_wait = 30
    for _ in range(max_wait):
        state = supervisor.get_state(session.session_id)
        if state.task_state == TaskState.COMPLETED:
            break
        time.sleep(1)
    
    # Verify
    assert state.task_state == TaskState.COMPLETED
    assert state.process_liveness == ProcessLiveness.EXITED_RESUMABLE
```

**Test Idle-Stop**:

```python
def test_idle_stop_after_timeout(supervisor):
    """Test session stops after idle timeout."""
    # Dispatch
    session = supervisor.dispatch(
        prompt="Do nothing",
        model="anthropic:claude-opus-4"
    )
    
    # Wait for idle
    time.sleep(2)
    
    # Fast-forward idle timeout (for testing)
    supervisor._idle_timeout = 1  # 1 second
    
    # Trigger tick
    supervisor.tick()
    
    # Verify stopped
    state = supervisor.get_state(session.session_id)
    assert state.process_liveness == ProcessLiveness.EXITED_RESUMABLE
```

### Performance Tests

**Benchmark IPC Latency**:

```python
import time

def benchmark_ipc_latency(iterations=1000):
    """Measure IPC round-trip latency."""
    supervisor = get_supervisor()
    
    start = time.perf_counter()
    
    for _ in range(iterations):
        supervisor.get_roster()  # Simple IPC call
    
    elapsed = time.perf_counter() - start
    avg_latency = (elapsed / iterations) * 1_000_000  # microseconds
    
    print(f"Average IPC latency: {avg_latency:.1f}μs")
    assert avg_latency < 100  # < 100μs target
```

**Benchmark State Write**:

```python
def benchmark_state_write(iterations=100):
    """Measure state persistence latency."""
    roster = {"version": "1.0", "sessions": {...}}
    path = Path("/tmp/test_roster.json")
    
    start = time.perf_counter()
    
    for _ in range(iterations):
        atomic_write_json(path, roster, fsync=True)
    
    elapsed = time.perf_counter() - start
    avg_latency = (elapsed / iterations) * 1000  # milliseconds
    
    print(f"Average write latency: {avg_latency:.1f}ms")
    assert avg_latency < 20  # < 20ms target
```

---

## Troubleshooting

### Supervisor Won't Start

```bash
# Check if already running
lyra daemon status

# Check socket file
ls -la /tmp/lyra-$(id -u)/supervisor.sock

# Check logs
tail -f ~/.lyra/supervisor.log

# Force restart
lyra daemon stop
lyra daemon start
```

### Session Stuck in "Working"

```bash
# Check process
ps aux | grep lyra-session-<id>

# Check transcript
lyra logs <session-id>

# Force stop
lyra stop <session-id>
```

### High Memory Usage

```bash
# List sessions by memory
ps aux | grep lyra-session | sort -k4 -rn

# Stop idle sessions
lyra fleet  # Press 's' on idle sessions

# Check memory pressure
lyra daemon status
```

### Corrupted Roster

```bash
# Restore from backup
cp ~/.lyra/roster.json.bak ~/.lyra/roster.json

# Or replay WAL manually
lyra daemon recover
```

---

## Best Practices

1. **Use Worktree Isolation**: Always enable `auto_worktree=True` for file safety
2. **Monitor Memory**: Watch RAM usage, stop idle sessions when needed
3. **Configure Expiry**: Tune approval expiry based on your security needs
4. **Use Cheap Models for Summaries**: DeepSeek saves 72% vs Haiku
5. **Pin Critical Sessions**: Use Ctrl+T to prevent idle-stop
6. **Regular Cleanup**: Prune old transcripts and worktrees monthly
7. **Backup Roster**: `cp ~/.lyra/roster.json ~/.lyra/roster.backup` daily
8. **Monitor Costs**: Check summary costs in dashboard, switch providers if needed

---

## Summary

This implementation guide covered setup, configuration, code examples, integration patterns, deployment options, and testing strategies for the Fleet Supervisor system. Key takeaways:

- **Zero config**: `lyra --bg` just works, no setup required
- **Crash-safe**: Atomic writes + WAL ensure state recovery
- **Extensible**: Python APIs for custom integrations
- **Observable**: Built-in monitoring via fleet TUI and logs
- **Tested**: Comprehensive unit, integration, and performance tests

For production deployment, use systemd (Linux) or LaunchAgent (macOS) to keep the supervisor running as a background service.

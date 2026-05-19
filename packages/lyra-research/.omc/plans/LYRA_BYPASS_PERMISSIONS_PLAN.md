# Lyra Bypass Permissions Mode - Implementation Plan

**Goal**: Add a bypass permissions mode to Lyra (similar to Claude Code's shift+tab cycle feature) that allows users to skip permission prompts for trusted operations.

**Status**: Planning
**Created**: 2026-05-19
**Estimated Duration**: 2-3 days

---

## Overview

Implement a permission bypass system that:
1. Allows users to toggle bypass mode on/off
2. Maintains security by requiring explicit opt-in
3. Logs all bypassed operations for audit trail
4. Provides visual feedback when bypass mode is active
5. Integrates with Lyra's existing hook system

---

## Architecture

### Core Components

```
lyra_research/
├── permissions/
│   ├── __init__.py
│   ├── bypass_manager.py      # Core bypass logic
│   ├── permission_gate.py     # Permission checkpoint
│   ├── audit_logger.py        # Audit trail for bypassed ops
│   └── config.py              # Bypass configuration
├── ui/
│   ├── status_line.py         # Status line integration
│   └── indicators.py          # Visual feedback
└── hooks/
    └── permission_hooks.py    # Hook integration
```

---

## Phase 0: Foundation (Day 1, Morning)

### 0.1 Permission Gate System

**File**: `src/lyra_research/permissions/permission_gate.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Any

class PermissionLevel(Enum):
    """Permission levels for operations"""
    SAFE = "safe"           # Always allowed (read-only)
    STANDARD = "standard"   # Requires confirmation
    DANGEROUS = "dangerous" # Always requires confirmation (cannot bypass)
    CRITICAL = "critical"   # Requires multi-factor confirmation

@dataclass
class PermissionRequest:
    """Request for permission to perform operation"""
    operation: str
    level: PermissionLevel
    description: str
    context: dict
    can_bypass: bool = True  # Some operations cannot be bypassed

class PermissionGate:
    """
    Permission checkpoint for operations
    
    Checks if operation should be allowed based on:
    - Permission level
    - Bypass mode status
    - Operation type
    """
    
    def __init__(self, bypass_manager):
        self.bypass_manager = bypass_manager
        
    def check_permission(self, request: PermissionRequest) -> bool:
        """
        Check if operation is permitted
        
        Returns:
            True if allowed, False if denied
        """
        # SAFE operations always allowed
        if request.level == PermissionLevel.SAFE:
            return True
            
        # CRITICAL operations always require confirmation
        if request.level == PermissionLevel.CRITICAL:
            return self._request_confirmation(request)
            
        # Check bypass mode
        if self.bypass_manager.is_bypass_enabled() and request.can_bypass:
            self.bypass_manager.log_bypass(request)
            return True
            
        # Standard flow: request confirmation
        return self._request_confirmation(request)
        
    def _request_confirmation(self, request: PermissionRequest) -> bool:
        """Request user confirmation for operation"""
        # In production, this would show UI prompt
        # For now, return True for testing
        return True
```

**Tests**: `tests/test_permission_gate.py`
- Test SAFE operations always allowed
- Test CRITICAL operations always require confirmation
- Test bypass mode allows STANDARD operations
- Test bypass mode respects can_bypass flag
- Test confirmation flow

---

### 0.2 Bypass Manager

**File**: `src/lyra_research/permissions/bypass_manager.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import json
from pathlib import Path

@dataclass
class BypassConfig:
    """Configuration for bypass mode"""
    enabled: bool = False
    auto_disable_after_minutes: Optional[int] = 30  # Auto-disable after 30 min
    allowed_operations: List[str] = None  # None = all, or specific list
    
    def __post_init__(self):
        if self.allowed_operations is None:
            self.allowed_operations = []

class BypassManager:
    """
    Manages bypass permissions mode
    
    Features:
    - Toggle bypass on/off
    - Auto-disable after timeout
    - Whitelist specific operations
    - Audit logging
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".lyra" / "bypass_config.json"
        self.config = self._load_config()
        self.enabled_at: Optional[datetime] = None
        
    def _load_config(self) -> BypassConfig:
        """Load bypass configuration from file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                data = json.load(f)
                return BypassConfig(**data)
        return BypassConfig()
        
    def _save_config(self):
        """Save bypass configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump({
                'enabled': self.config.enabled,
                'auto_disable_after_minutes': self.config.auto_disable_after_minutes,
                'allowed_operations': self.config.allowed_operations
            }, f, indent=2)
            
    def enable_bypass(self):
        """Enable bypass mode"""
        self.config.enabled = True
        self.enabled_at = datetime.now()
        self._save_config()
        
    def disable_bypass(self):
        """Disable bypass mode"""
        self.config.enabled = False
        self.enabled_at = None
        self._save_config()
        
    def toggle_bypass(self) -> bool:
        """
        Toggle bypass mode on/off
        
        Returns:
            New bypass state (True = enabled)
        """
        if self.config.enabled:
            self.disable_bypass()
        else:
            self.enable_bypass()
        return self.config.enabled
        
    def is_bypass_enabled(self) -> bool:
        """Check if bypass mode is currently enabled"""
        if not self.config.enabled:
            return False
            
        # Check auto-disable timeout
        if self.config.auto_disable_after_minutes and self.enabled_at:
            elapsed = (datetime.now() - self.enabled_at).total_seconds() / 60
            if elapsed > self.config.auto_disable_after_minutes:
                self.disable_bypass()
                return False
                
        return True
        
    def is_operation_allowed(self, operation: str) -> bool:
        """Check if specific operation is allowed in bypass mode"""
        if not self.config.allowed_operations:
            return True  # Empty list = all operations allowed
        return operation in self.config.allowed_operations
        
    def log_bypass(self, request):
        """Log bypassed operation for audit trail"""
        # Delegate to audit logger
        from .audit_logger import AuditLogger
        logger = AuditLogger()
        logger.log_bypass(request)
```

**Tests**: `tests/test_bypass_manager.py`
- Test enable/disable bypass
- Test toggle bypass
- Test auto-disable timeout
- Test operation whitelist
- Test config persistence

---

### 0.3 Audit Logger

**File**: `src/lyra_research/permissions/audit_logger.py`

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from typing import List

@dataclass
class AuditEntry:
    """Single audit log entry"""
    timestamp: str
    operation: str
    level: str
    description: str
    context: dict
    bypassed: bool

class AuditLogger:
    """
    Logs all bypassed operations for security audit
    
    Features:
    - Append-only log file
    - JSON format for easy parsing
    - Rotation after size limit
    """
    
    def __init__(self, log_path: Path = None):
        self.log_path = log_path or Path.home() / ".lyra" / "bypass_audit.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
    def log_bypass(self, request):
        """Log a bypassed permission request"""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            operation=request.operation,
            level=request.level.value,
            description=request.description,
            context=request.context,
            bypassed=True
        )
        
        # Append to JSONL file
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry.__dict__) + '\n')
            
    def get_recent_bypasses(self, limit: int = 100) -> List[AuditEntry]:
        """Get recent bypassed operations"""
        if not self.log_path.exists():
            return []
            
        entries = []
        with open(self.log_path) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    entries.append(AuditEntry(**data))
                    
        return entries[-limit:]
        
    def clear_log(self):
        """Clear audit log (use with caution)"""
        if self.log_path.exists():
            self.log_path.unlink()
```

**Tests**: `tests/test_audit_logger.py`
- Test log bypass operation
- Test get recent bypasses
- Test JSONL format
- Test log persistence

---

## Phase 1: UI Integration (Day 1, Afternoon)

### 1.1 Status Line Integration

**File**: `src/lyra_research/ui/status_line.py`

```python
from ..permissions.bypass_manager import BypassManager

class StatusLine:
    """
    Status line display for Lyra
    
    Shows:
    - Bypass mode status
    - Current operation
    - Keyboard shortcuts
    """
    
    def __init__(self, bypass_manager: BypassManager):
        self.bypass_manager = bypass_manager
        
    def render(self) -> str:
        """
        Render status line
        
        Returns:
            Formatted status line string
        """
        parts = []
        
        # Bypass status
        if self.bypass_manager.is_bypass_enabled():
            parts.append("⏵⏵ bypass permissions on")
        else:
            parts.append("⏵⏵ bypass permissions off")
            
        # Keyboard shortcuts
        parts.append("(shift+tab to cycle)")
        parts.append("· esc to interrupt")
        
        return " ".join(parts)
        
    def get_bypass_indicator(self) -> str:
        """Get bypass mode indicator symbol"""
        return "⏺" if self.bypass_manager.is_bypass_enabled() else "◯"
```

**Tests**: `tests/test_status_line.py`
- Test render with bypass on
- Test render with bypass off
- Test indicator symbols

---

### 1.2 Visual Indicators

**File**: `src/lyra_research/ui/indicators.py`

```python
from enum import Enum

class IndicatorStyle(Enum):
    """Visual indicator styles"""
    ENABLED = "⏺"   # Filled circle
    DISABLED = "◯"  # Empty circle
    WARNING = "⚠"   # Warning triangle
    CRITICAL = "🔴" # Red circle

class VisualIndicator:
    """Visual feedback for bypass mode"""
    
    @staticmethod
    def get_bypass_indicator(enabled: bool, has_warnings: bool = False) -> str:
        """
        Get indicator for bypass mode
        
        Args:
            enabled: Whether bypass is enabled
            has_warnings: Whether there are security warnings
            
        Returns:
            Indicator symbol
        """
        if has_warnings:
            return IndicatorStyle.WARNING.value
        return IndicatorStyle.ENABLED.value if enabled else IndicatorStyle.DISABLED.value
        
    @staticmethod
    def format_status_message(enabled: bool, operation_count: int = 0) -> str:
        """Format status message for bypass mode"""
        if enabled:
            msg = "Bypass mode ENABLED"
            if operation_count > 0:
                msg += f" ({operation_count} operations bypassed)"
            return msg
        return "Bypass mode disabled"
```

**Tests**: `tests/test_indicators.py`
- Test indicator symbols
- Test status message formatting
- Test warning indicators

---

## Phase 2: Hook Integration (Day 2, Morning)

### 2.1 Permission Hooks

**File**: `src/lyra_research/hooks/permission_hooks.py`

```python
from typing import Callable, Dict, Any
from ..permissions.bypass_manager import BypassManager
from ..permissions.permission_gate import PermissionGate, PermissionRequest, PermissionLevel

class PermissionHooks:
    """
    Hook integration for permission system
    
    Provides hooks for:
    - Pre-operation permission check
    - Post-operation audit logging
    - Bypass mode toggle
    """
    
    def __init__(self, bypass_manager: BypassManager):
        self.bypass_manager = bypass_manager
        self.permission_gate = PermissionGate(bypass_manager)
        
    def pre_operation_hook(self, operation: str, level: PermissionLevel, 
                          description: str, context: Dict[str, Any]) -> bool:
        """
        Hook called before operation execution
        
        Returns:
            True if operation should proceed
        """
        request = PermissionRequest(
            operation=operation,
            level=level,
            description=description,
            context=context
        )
        
        return self.permission_gate.check_permission(request)
        
    def post_operation_hook(self, operation: str, success: bool, result: Any):
        """Hook called after operation execution"""
        # Log operation result
        pass
        
    def toggle_bypass_hook(self) -> bool:
        """
        Hook for toggling bypass mode (e.g., via keyboard shortcut)
        
        Returns:
            New bypass state
        """
        return self.bypass_manager.toggle_bypass()
```

**Tests**: `tests/test_permission_hooks.py`
- Test pre-operation hook
- Test post-operation hook
- Test toggle bypass hook
- Test hook integration with bypass manager

---

## Phase 3: CLI Integration (Day 2, Afternoon)

### 3.1 CLI Commands

**File**: `src/lyra_research/cli/bypass_commands.py`

```python
import click
from ..permissions.bypass_manager import BypassManager
from ..permissions.audit_logger import AuditLogger

@click.group()
def bypass():
    """Bypass permissions management"""
    pass

@bypass.command()
def enable():
    """Enable bypass mode"""
    manager = BypassManager()
    manager.enable_bypass()
    click.echo("✓ Bypass mode ENABLED")
    click.echo("  All standard operations will proceed without confirmation")
    click.echo("  Use 'lyra bypass disable' to turn off")

@bypass.command()
def disable():
    """Disable bypass mode"""
    manager = BypassManager()
    manager.disable_bypass()
    click.echo("✓ Bypass mode disabled")

@bypass.command()
def toggle():
    """Toggle bypass mode on/off"""
    manager = BypassManager()
    enabled = manager.toggle_bypass()
    if enabled:
        click.echo("✓ Bypass mode ENABLED")
    else:
        click.echo("✓ Bypass mode disabled")

@bypass.command()
def status():
    """Show bypass mode status"""
    manager = BypassManager()
    enabled = manager.is_bypass_enabled()
    
    click.echo(f"Bypass mode: {'ENABLED' if enabled else 'disabled'}")
    
    if enabled and manager.enabled_at:
        click.echo(f"Enabled at: {manager.enabled_at.isoformat()}")
        
    if manager.config.auto_disable_after_minutes:
        click.echo(f"Auto-disable: {manager.config.auto_disable_after_minutes} minutes")

@bypass.command()
@click.option('--limit', default=20, help='Number of entries to show')
def audit(limit):
    """Show recent bypassed operations"""
    logger = AuditLogger()
    entries = logger.get_recent_bypasses(limit)
    
    if not entries:
        click.echo("No bypassed operations logged")
        return
        
    click.echo(f"\nRecent bypassed operations ({len(entries)}):\n")
    for entry in entries:
        click.echo(f"  [{entry.timestamp}] {entry.operation}")
        click.echo(f"    Level: {entry.level}")
        click.echo(f"    {entry.description}\n")
```

**Tests**: `tests/test_bypass_commands.py`
- Test enable command
- Test disable command
- Test toggle command
- Test status command
- Test audit command

---

## Phase 4: Security & Testing (Day 3)

### 4.1 Security Considerations

**Critical Operations (Cannot Bypass)**:
- File deletion (rm, unlink)
- Database drops
- Production deployments
- Credential modifications
- System configuration changes

**Standard Operations (Can Bypass)**:
- File reads
- API calls (non-destructive)
- Report generation
- Data analysis
- Test execution

**Implementation**:
```python
# In permission_gate.py
CRITICAL_OPERATIONS = {
    'file_delete',
    'database_drop',
    'production_deploy',
    'credential_modify',
    'system_config_change'
}

def check_permission(self, request: PermissionRequest) -> bool:
    # Critical operations cannot be bypassed
    if request.operation in CRITICAL_OPERATIONS:
        request.can_bypass = False
        return self._request_confirmation(request)
    # ... rest of logic
```

### 4.2 Integration Tests

**File**: `tests/test_bypass_integration.py`

```python
def test_full_bypass_workflow():
    """Test complete bypass workflow"""
    manager = BypassManager()
    gate = PermissionGate(manager)
    
    # Start with bypass disabled
    assert not manager.is_bypass_enabled()
    
    # Standard operation requires confirmation
    request = PermissionRequest(
        operation="file_read",
        level=PermissionLevel.STANDARD,
        description="Read config file",
        context={}
    )
    # Would require confirmation (mocked as True)
    
    # Enable bypass
    manager.enable_bypass()
    assert manager.is_bypass_enabled()
    
    # Same operation now bypasses
    allowed = gate.check_permission(request)
    assert allowed
    
    # Critical operation still requires confirmation
    critical_request = PermissionRequest(
        operation="file_delete",
        level=PermissionLevel.CRITICAL,
        description="Delete production data",
        context={}
    )
    # Would still require confirmation even with bypass enabled

def test_bypass_with_audit_trail():
    """Test that bypassed operations are logged"""
    manager = BypassManager()
    gate = PermissionGate(manager)
    logger = AuditLogger()
    
    # Clear previous logs
    logger.clear_log()
    
    # Enable bypass
    manager.enable_bypass()
    
    # Perform bypassed operation
    request = PermissionRequest(
        operation="api_call",
        level=PermissionLevel.STANDARD,
        description="Call external API",
        context={"endpoint": "/api/data"}
    )
    gate.check_permission(request)
    
    # Check audit log
    entries = logger.get_recent_bypasses(limit=10)
    assert len(entries) == 1
    assert entries[0].operation == "api_call"
    assert entries[0].bypassed is True

def test_auto_disable_timeout():
    """Test auto-disable after timeout"""
    import time
    
    manager = BypassManager()
    manager.config.auto_disable_after_minutes = 0.01  # 0.6 seconds for testing
    
    # Enable bypass
    manager.enable_bypass()
    assert manager.is_bypass_enabled()
    
    # Wait for timeout
    time.sleep(1)
    
    # Should be auto-disabled
    assert not manager.is_bypass_enabled()
```

---

## Phase 5: Documentation (Day 3, Afternoon)

### 5.1 User Documentation

**File**: `docs/BYPASS_PERMISSIONS.md`

```markdown
# Bypass Permissions Mode

## Overview

Bypass permissions mode allows you to skip confirmation prompts for trusted operations, streamlining your workflow when you're confident about the actions Lyra will take.

## Usage

### Enable/Disable via CLI

```bash
# Enable bypass mode
lyra bypass enable

# Disable bypass mode
lyra bypass disable

# Toggle bypass mode
lyra bypass toggle

# Check status
lyra bypass status
```

### Keyboard Shortcut

Press `Shift+Tab` to cycle bypass mode on/off (when integrated with UI).

### Status Line

The status line shows current bypass mode:
- `⏵⏵ bypass permissions on` - Bypass enabled
- `⏵⏵ bypass permissions off` - Bypass disabled

## Security

### Operations That Can Be Bypassed

- File reads
- API calls (non-destructive)
- Report generation
- Data analysis
- Test execution

### Operations That CANNOT Be Bypassed

- File deletion
- Database drops
- Production deployments
- Credential modifications
- System configuration changes

### Audit Trail

All bypassed operations are logged to `~/.lyra/bypass_audit.jsonl`:

```bash
# View recent bypassed operations
lyra bypass audit --limit 20
```

### Auto-Disable

Bypass mode automatically disables after 30 minutes (configurable).

## Configuration

Edit `~/.lyra/bypass_config.json`:

```json
{
  "enabled": false,
  "auto_disable_after_minutes": 30,
  "allowed_operations": []
}
```

- `enabled`: Current bypass state
- `auto_disable_after_minutes`: Auto-disable timeout (null = never)
- `allowed_operations`: Whitelist of operations (empty = all allowed)

## Best Practices

1. **Use for trusted workflows**: Enable bypass when you're confident about the operations
2. **Review audit logs**: Periodically check `lyra bypass audit` to review bypassed operations
3. **Disable when done**: Turn off bypass mode when switching to exploratory work
4. **Never bypass critical operations**: The system prevents bypassing dangerous operations

## Examples

### Trusted Research Workflow

```bash
# Enable bypass for batch processing
lyra bypass enable

# Run multiple research tasks without prompts
lyra research --query "AI safety" --depth 3
lyra research --query "alignment" --depth 3
lyra research --query "interpretability" --depth 3

# Disable when done
lyra bypass disable
```

### Check What Was Bypassed

```bash
# View recent bypassed operations
lyra bypass audit --limit 10
```
```

---

## Testing Strategy

### Unit Tests (60 tests total)

1. **PermissionGate** (10 tests)
   - SAFE operations always allowed
   - CRITICAL operations always require confirmation
   - Bypass mode allows STANDARD operations
   - Bypass respects can_bypass flag
   - Confirmation flow

2. **BypassManager** (15 tests)
   - Enable/disable bypass
   - Toggle bypass
   - Auto-disable timeout
   - Operation whitelist
   - Config persistence
   - Multiple toggle cycles
   - Timeout edge cases

3. **AuditLogger** (8 tests)
   - Log bypass operation
   - Get recent bypasses
   - JSONL format
   - Log persistence
   - Log rotation
   - Clear log

4. **StatusLine** (5 tests)
   - Render with bypass on
   - Render with bypass off
   - Indicator symbols
   - Keyboard shortcuts display

5. **VisualIndicator** (5 tests)
   - Indicator symbols
   - Status message formatting
   - Warning indicators

6. **PermissionHooks** (7 tests)
   - Pre-operation hook
   - Post-operation hook
   - Toggle bypass hook
   - Hook integration

7. **CLI Commands** (10 tests)
   - Enable command
   - Disable command
   - Toggle command
   - Status command
   - Audit command
   - Command output formatting

### Integration Tests (10 tests)

1. Full bypass workflow
2. Bypass with audit trail
3. Auto-disable timeout
4. Critical operation blocking
5. Status line integration
6. CLI integration
7. Config persistence across restarts
8. Multiple concurrent operations
9. Whitelist enforcement
10. Security boundary testing

---

## Success Criteria

- [ ] All 70 tests passing
- [ ] Bypass mode toggles correctly
- [ ] Critical operations cannot be bypassed
- [ ] Audit trail captures all bypassed operations
- [ ] Auto-disable timeout works
- [ ] Status line shows correct state
- [ ] CLI commands work as expected
- [ ] Configuration persists across restarts
- [ ] Documentation complete
- [ ] Security review passed

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Accidental bypass of critical operations | HIGH | Hard-code critical operations list, cannot be overridden |
| Audit log tampering | MEDIUM | Use append-only JSONL format, warn on missing logs |
| Bypass mode left enabled | MEDIUM | Auto-disable after 30 minutes |
| UI confusion about bypass state | LOW | Clear visual indicators, status line |
| Config file corruption | LOW | Validate config on load, use defaults if invalid |

---

## Future Enhancements

1. **Multi-level bypass**: Different bypass levels for different operation types
2. **Time-based bypass**: Enable bypass for specific time windows
3. **Context-aware bypass**: Auto-enable for specific workflows
4. **Team bypass policies**: Shared bypass rules for teams
5. **Bypass analytics**: Dashboard showing bypass patterns
6. **Integration with CI/CD**: Bypass mode for automated pipelines

---

## References

- Claude Code bypass permissions: https://docs.anthropic.com/claude-code/permissions
- Security best practices: https://owasp.org/www-project-top-ten/
- Audit logging standards: https://www.sans.org/reading-room/whitepapers/logging/

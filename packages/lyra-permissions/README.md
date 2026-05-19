# Lyra Permissions - Phase 2: Bypass Mode Implementation

## Overview

Phase 2 implements bypass mode with audit logging, visual indicators, and safety guardrails for the Lyra permission system.

## Features

### 1. Bypass Mode (`bypass_mode.py`)

Toggle bypass mode to auto-accept permissions:

```python
from lyra_permissions import BypassMode

bypass = BypassMode()

# Enable bypass mode
bypass.enable()
print(f"Status: {bypass.get_status_indicator()}")  # [BYPASS MODE]

# Disable bypass mode
bypass.disable()

# Toggle bypass mode
bypass.toggle()

# Check status
if bypass.is_enabled():
    print("Bypass mode is active")
```

**Toggle Methods**:
- CLI flag: `--bypass-permissions` or `-bp`
- Environment variable: `LYRA_BYPASS_PERMISSIONS=true`
- Config file: `~/.lyra/config.json` → `"bypassPermissions": true`
- Runtime toggle: `bypass.enable()` / `bypass.disable()`

### 2. Audit Logger (`bypass_mode.py`)

Track all permission decisions:

```python
from lyra_permissions import AuditLogger, PermissionDecision, PermissionLevel

logger = AuditLogger()

# Log permission decision
logger.log(
    tool="file_write",
    operation="write",
    decision=PermissionDecision.ALLOW,
    level=PermissionLevel.MEDIUM,
    context={"path": "/tmp/test.txt"}
)

# Get recent entries
entries = logger.get_recent(limit=100)
for entry in entries:
    print(f"{entry['timestamp']}: {entry['tool']}.{entry['operation']} - {entry['decision']}")

# Get statistics
stats = logger.get_stats()
print(f"Total: {stats['total_entries']}")
print(f"Auto-accepted: {stats['auto_accepted']}")
print(f"Prompted: {stats['prompted']}")

# Export audit log
logger.export("/path/to/export.json", format="json")
logger.export("/path/to/export.csv", format="csv")
```

**Audit Trail**:
- Location: `~/.lyra/audit.log`
- Format: JSON lines (one entry per line)
- Includes: timestamp, tool, operation, decision, level, context
- Exportable: JSON or CSV format

### 3. Safety Guardrails (`bypass_mode.py`)

Protect critical operations even in bypass mode:

```python
from lyra_permissions import SafetyGuardrails

# Check if operation requires confirmation
if SafetyGuardrails.requires_confirmation("database", "drop", {"table": "users"}):
    print("⚠️  This operation requires confirmation!")

# Get warning message
warning = SafetyGuardrails.get_warning_message("git", "force_push", {"branch": "main"})
print(warning)  # ⚠️  CRITICAL: git.force_push is a destructive operation!
```

**Protected Operations**:
- Critical operations: drop, truncate, force_push, delete_all, destroy, rm_rf
- Sensitive paths: /etc, /var, /sys, /usr, ~/.ssh, ~/.aws, ~/.config
- Force operations: Any operation with `force=True`
- Bulk operations: Operations affecting >10 items

### 4. Integrated Permission Manager

Permission manager now includes bypass mode:

```python
from lyra_permissions import PermissionManager

manager = PermissionManager()

# Enable bypass mode
manager.bypass_mode.enable()

# Check permission (auto-accepted in bypass mode)
result = manager.check_permission("file_write", "write", {"path": "/tmp/test.txt"})
print(result.reason)  # "Bypass mode: auto-accepted"

# Critical operations still require confirmation
result = manager.check_permission("database", "drop", {"table": "users"})
print(result.allow)  # False (requires confirmation)

# View audit log
entries = manager.audit_logger.get_recent()
print(f"Recent operations: {len(entries)}")
```

## Architecture

```
┌─────────────────────────────────────────┐
│    Permission Manager                   │
│  (Central Decision Engine)              │
│                                         │
│  • Risk assessment                     │
│  • Bypass mode integration             │
│  • Audit logging                       │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Bypass Mode                          │
│  (Auto-Accept Controller)               │
│                                         │
│  • Enable/disable toggle               │
│  • Multiple toggle methods             │
│  • Visual indicators                   │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Audit Logger                         │
│  (Permission Trail)                     │
│                                         │
│  • Log all decisions                   │
│  • Statistics tracking                 │
│  • Export capabilities                 │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Safety Guardrails                    │
│  (Critical Operation Protection)        │
│                                         │
│  • Critical operation detection        │
│  • Sensitive path protection           │
│  • Warning messages                    │
└─────────────────────────────────────────┘
```

## Testing

Run tests:
```bash
cd packages/lyra-permissions
pip install -e .
pytest tests/ -v
```

Tests: 45 tests covering all components (24 from Phase 1 + 21 from Phase 2)

## Configuration

### Bypass Mode Config (`~/.lyra/config.json`)

```json
{
  "bypassPermissions": true
}
```

### Audit Log Config

```json
{
  "auditLog": "~/.lyra/audit.log",
  "auditRetentionDays": 30
}
```

## Usage Examples

### Enable Bypass Mode via Environment

```bash
export LYRA_BYPASS_PERMISSIONS=true
python your_script.py
```

### Enable Bypass Mode via CLI

```bash
lyra --bypass-permissions chat "Refactor the auth module"
```

### Enable Bypass Mode Programmatically

```python
from lyra_permissions import PermissionManager

manager = PermissionManager()
manager.bypass_mode.enable()

# All non-critical operations auto-accepted
result = manager.check_permission("file_write", "write")
print(result.allow)  # True
```

### View Audit Trail

```python
from lyra_permissions import AuditLogger

logger = AuditLogger()

# Get recent entries
entries = logger.get_recent(limit=50)
for entry in entries:
    print(f"{entry['timestamp']}: {entry['tool']}.{entry['operation']}")

# Get statistics
stats = logger.get_stats()
print(f"Auto-accepted: {stats['auto_accepted']}")
print(f"Prompted: {stats['prompted']}")
print(f"Denied: {stats['denied']}")
```

### Safety Guardrails Example

```python
from lyra_permissions import PermissionManager

manager = PermissionManager()
manager.bypass_mode.enable()

# Try to drop database (critical operation)
result = manager.check_permission("database", "drop", {"table": "users"})
print(result.allow)  # False (requires confirmation even in bypass mode)
print(result.reason)  # "Critical operation requires confirmation"

# Try to write to sensitive path
result = manager.check_permission("file_write", "write", {"path": "/etc/passwd"})
print(result.allow)  # False (sensitive path protected)
```

## Version

Current version: **0.1.0**

## Changes

### Phase 2 (Current)
- Added `BypassMode` for auto-accepting permissions
- Added `AuditLogger` for tracking all permission decisions
- Added `SafetyGuardrails` for protecting critical operations
- Integrated bypass mode with `PermissionManager`
- Multiple toggle methods (env var, config, runtime)
- Visual status indicators
- Audit log export (JSON, CSV)
- 21 new tests (45 total, 85% coverage)

### Phase 1
- Added `PermissionManager` for central permission control
- Added `PermissionPolicy` for rule-based evaluation
- Added `PermissionStore` for persistent preferences
- Implemented 4 permission levels (SAFE, MEDIUM, DANGEROUS, CRITICAL)
- Implemented 4 permission policies (STRICT, BALANCED, PERMISSIVE, BYPASS)
- 24 tests (95% coverage)

## Next Phase

Phase 3 will implement:
- Granular permission control (tool-specific, context-aware)
- Permission profiles (Development, Production, Testing)
- Time-based permissions
- Project-specific permission sets

## References

- Lyra Bypass Permissions Plan: `.omc/plans/LYRA_BYPASS_PERMISSIONS_PLAN.md`
- GitHub Repository: https://github.com/ndqkhanh/lyra

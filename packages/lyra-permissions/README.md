# Lyra Permissions - Phase 1: Permission System Foundation

## Overview

Phase 1 implements the foundational permission management system for Lyra, enabling fine-grained control over tool permissions and laying the groundwork for bypass mode.

## Features

### 1. Permission Manager (`permission_manager.py`)

Central permission registry and decision engine:

```python
from lyra_permissions import PermissionManager, PermissionLevel

manager = PermissionManager()

# Check permission
decision = manager.check_permission(
    tool="file_write",
    operation="write",
    context={"path": "/tmp/test.txt"}
)

# Assess risk level
risk = manager.assess_risk("file_delete", "delete", {"path": "/etc/passwd"})
print(f"Risk level: {risk}")  # CRITICAL
```

**Permission Levels**:
- `SAFE`: Always allow (Read, List, Search)
- `MEDIUM`: Prompt once per session (Edit, Write)
- `DANGEROUS`: Always prompt (Delete, Execute, Deploy)
- `CRITICAL`: Require explicit confirmation (Drop DB, Force Push)

### 2. Permission Policy (`permission_policy.py`)

Policy definitions and rule-based evaluation:

```python
from lyra_permissions import PermissionPolicy, PolicyEngine

# Set policy
engine = PolicyEngine(policy=PermissionPolicy.BALANCED)

# Apply policy
decision = engine.apply_policy(PermissionLevel.DANGEROUS)
print(f"Decision: {decision}")  # PROMPT

# Change policy
engine.set_policy(PermissionPolicy.BYPASS)
```

**Permission Policies**:
- `STRICT`: Prompt for everything except SAFE
- `BALANCED`: Prompt for DANGEROUS and CRITICAL (default)
- `PERMISSIVE`: Only prompt for CRITICAL
- `BYPASS`: Auto-accept all (with audit log)

### 3. Permission Store (`permission_store.py`)

Persistent permission preferences:

```python
from lyra_permissions import PermissionStore

store = PermissionStore()

# Save preference
store.allow("file_write", "write")
store.deny("file_delete", "delete")

# Check preference
if store.is_allowed("file_write", "write"):
    print("Write operation allowed")

# Get all preferences
prefs = store.get_all_preferences()
```

**Storage**:
- Location: `~/.lyra/permissions.json`
- Format: JSON
- Session cache for performance
- Automatic backup

## Architecture

```
┌─────────────────────────────────────────┐
│    Permission Manager                   │
│  (Central Decision Engine)              │
│                                         │
│  • Risk assessment                     │
│  • Permission checking                 │
│  • Policy application                  │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Permission Policy                    │
│  (Rule-Based Evaluation)                │
│                                         │
│  • STRICT / BALANCED / PERMISSIVE      │
│  • BYPASS mode                         │
│  • Policy enforcement                  │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Permission Store                     │
│  (Persistent Preferences)               │
│                                         │
│  • Allow/deny lists                    │
│  • Session cache                       │
│  • JSON storage                        │
└─────────────────────────────────────────┘
```

## Testing

Run tests:
```bash
cd packages/lyra-permissions
pip install -e .
pytest tests/ -v
```

Tests: 15 tests covering all components

## Usage Examples

### Basic Permission Check

```python
from lyra_permissions import PermissionManager, PermissionLevel

manager = PermissionManager()

# Check if operation is allowed
decision = manager.check_permission(
    tool="git",
    operation="push",
    context={"branch": "main", "force": False}
)

if decision.allow:
    print("Operation allowed")
else:
    print(f"Operation denied: {decision.reason}")
```

### Risk Assessment

```python
# Assess risk of different operations
operations = [
    ("file_read", "read", {"path": "/tmp/data.txt"}),
    ("file_write", "write", {"path": "/tmp/output.txt"}),
    ("file_delete", "delete", {"path": "/var/log/app.log"}),
    ("database", "drop", {"table": "users"}),
]

for tool, op, ctx in operations:
    risk = manager.assess_risk(tool, op, ctx)
    print(f"{tool}.{op}: {risk.value}")
```

### Policy Management

```python
from lyra_permissions import PolicyEngine, PermissionPolicy

# Create engine with strict policy
engine = PolicyEngine(policy=PermissionPolicy.STRICT)

# Check what policy would do
for level in [PermissionLevel.SAFE, PermissionLevel.MEDIUM, 
              PermissionLevel.DANGEROUS, PermissionLevel.CRITICAL]:
    decision = engine.apply_policy(level)
    print(f"{level.value}: {decision.value}")

# Switch to permissive mode
engine.set_policy(PermissionPolicy.PERMISSIVE)
```

### Persistent Preferences

```python
from lyra_permissions import PermissionStore

store = PermissionStore()

# Allow specific operations
store.allow("file_read", "read")
store.allow("file_write", "write")

# Deny dangerous operations
store.deny("file_delete", "delete")
store.deny("database", "drop")

# Check preferences
if store.is_allowed("file_write", "write"):
    # Perform write operation
    pass

# Clear all preferences
store.clear()
```

## Configuration

Default configuration (`~/.lyra/permissions.json`):

```json
{
  "policy": "balanced",
  "allowList": [],
  "denyList": [],
  "sessionCache": {}
}
```

## Version

Current version: **0.1.0**

## Changes

- Added `PermissionManager` for central permission control
- Added `PermissionPolicy` for rule-based evaluation
- Added `PermissionStore` for persistent preferences
- Implemented 4 permission levels (SAFE, MEDIUM, DANGEROUS, CRITICAL)
- Implemented 4 permission policies (STRICT, BALANCED, PERMISSIVE, BYPASS)
- Comprehensive test coverage (15 tests)

## Next Phase

Phase 2 will implement:
- Bypass mode toggle (CLI, env var, config)
- Visual indicators for bypass mode
- Audit trail logging
- Safety guardrails for critical operations

## References

- Lyra Bypass Permissions Plan: `.omc/plans/LYRA_BYPASS_PERMISSIONS_PLAN.md`
- GitHub Repository: https://github.com/ndqkhanh/lyra

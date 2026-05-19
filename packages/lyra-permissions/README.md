# Lyra Permissions - Phase 3: Granular Permission Control

## Overview

Phase 3 implements granular permission control with tool-specific permissions, context-aware rules, permission profiles, and time-based permissions.

## Features

### 1. Tool-Specific Permissions

Configure permissions for specific tools and operations:

```python
from lyra_permissions import GranularController, ToolPermission

controller = GranularController()

# Add tool-specific permission
controller.add_tool_permission(
    tool="file_write",
    operation="write",
    permission=ToolPermission.ALWAYS_ALLOW
)

# Add wildcard permission for all operations
controller.add_tool_permission(
    tool="file_read",
    operation="*",
    permission=ToolPermission.ALWAYS_ALLOW
)
```

**Permission Types**:
- `ALWAYS_ALLOW`: Always allow without prompting
- `PROMPT_ONCE`: Prompt once per session
- `ALWAYS_PROMPT`: Always prompt
- `BYPASS_IF_SAFE`: Bypass only if risk level is SAFE

### 2. Context-Aware Rules

Create rules based on operation context:

```python
from lyra_permissions import GranularController

controller = GranularController()

# Allow operations in /tmp directory
controller.add_context_rule(
    name="Allow temp directory",
    condition={"path": {"startswith": "/tmp"}},
    decision="allow",
    priority=10
)

# Deny operations on sensitive paths
controller.add_context_rule(
    name="Deny sensitive paths",
    condition={"path": {"startswith": "/etc"}},
    decision="prompt",
    priority=100  # Higher priority
)
```

**Condition Types**:
- `startswith`: String starts with value
- `contains`: String contains value
- `equals`: Exact match

### 3. Permission Profiles

Switch between pre-configured permission sets:

```python
from lyra_permissions import GranularController

controller = GranularController()

# List available profiles
profiles = controller.list_profiles()
print(profiles)  # ['default', 'development', 'production']

# Switch to development profile
controller.set_profile("development")

# Switch to production profile
controller.set_profile("production")
```

**Built-in Profiles**:

**Development Profile**:
- File read: Always allow
- File write: Bypass if safe
- File delete: Always prompt
- Git push: Prompt once
- Allow /tmp directory operations

**Production Profile**:
- File read: Always allow
- File write: Always prompt
- File delete: Always prompt
- Database operations: Always prompt
- Deny /var directory operations

### 4. Time-Based Permissions

Control permissions based on time of day:

```python
from datetime import time
from lyra_permissions import TimeBasedController, PermissionDecision

controller = TimeBasedController()

# Allow operations during work hours (9 AM - 5 PM, Mon-Fri)
controller.add_time_rule(
    start_time=time(9, 0),
    end_time=time(17, 0),
    decision=PermissionDecision.ALLOW,
    days=[0, 1, 2, 3, 4]  # Monday-Friday
)

# Check if currently work hours
if controller.is_work_hours():
    print("Work hours - operations allowed")
```

### 5. Integrated Permission Manager

All granular controls are integrated into the permission manager:

```python
from lyra_permissions import PermissionManager

manager = PermissionManager()

# Set profile
manager.granular_controller.set_profile("development")

# Add custom rule
manager.granular_controller.add_context_rule(
    name="Allow project directory",
    condition={"path": {"startswith": "/home/user/project"}},
    decision="allow",
    priority=5
)

# Check permission (granular rules take priority)
result = manager.check_permission(
    "file_write",
    "write",
    {"path": "/home/user/project/file.txt"}
)

print(result.reason)  # "Context rule: allow"
```

## Architecture

```
┌─────────────────────────────────────────┐
│    Permission Manager                   │
│  (Central Decision Engine)              │
│                                         │
│  Priority Order:                       │
│  1. Critical operations                │
│  2. Time-based rules                   │
│  3. Context rules                      │
│  4. Tool permissions                   │
│  5. Bypass mode                        │
│  6. User preferences                   │
│  7. Policy                             │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Granular Controller                  │
│  (Tool & Context Rules)                 │
│                                         │
│  • Tool-specific permissions           │
│  • Context-aware rules                 │
│  • Permission profiles                 │
│  • Rule priority system                │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Time-Based Controller                │
│  (Temporal Rules)                       │
│                                         │
│  • Time-of-day rules                   │
│  • Day-of-week rules                   │
│  • Work hours detection                │
└─────────────────────────────────────────┘
```

## Configuration

### Granular Permissions Config (`~/.lyra/granular_permissions.json`)

```json
{
  "currentProfile": "development",
  "profiles": {
    "development": {
      "name": "Development",
      "toolPermissions": {
        "file_read:*": "always_allow",
        "file_write:*": "bypass_if_safe",
        "git:push": "prompt_once"
      },
      "contextRules": [
        {
          "name": "Allow temp directory",
          "condition": {"path": {"startswith": "/tmp"}},
          "decision": "allow",
          "priority": 10
        }
      ]
    },
    "production": {
      "name": "Production",
      "toolPermissions": {
        "file_read:*": "always_allow",
        "file_write:*": "always_prompt",
        "database:*": "always_prompt"
      },
      "contextRules": [
        {
          "name": "Deny production paths",
          "condition": {"path": {"startswith": "/var"}},
          "decision": "prompt",
          "priority": 100
        }
      ]
    }
  }
}
```

## Testing

Run tests:
```bash
cd packages/lyra-permissions
pip install -e .
pytest tests/ -v
```

Tests: 61 tests covering all components (24 Phase 1 + 21 Phase 2 + 16 Phase 3)

## Usage Examples

### Tool-Specific Permissions

```python
from lyra_permissions import PermissionManager, ToolPermission

manager = PermissionManager()

# Always allow file reads
manager.granular_controller.add_tool_permission(
    "file_read", "*", ToolPermission.ALWAYS_ALLOW
)

# Always prompt for database operations
manager.granular_controller.add_tool_permission(
    "database", "*", ToolPermission.ALWAYS_PROMPT
)

# Check permission
result = manager.check_permission("file_read", "read", {"path": "/data/file.txt"})
print(result.allow)  # True
```

### Context-Aware Rules

```python
from lyra_permissions import PermissionManager

manager = PermissionManager()

# Allow operations in project directory
manager.granular_controller.add_context_rule(
    name="Allow project dir",
    condition={"path": {"startswith": "/home/user/project"}},
    decision="allow",
    priority=10
)

# Deny operations on config files
manager.granular_controller.add_context_rule(
    name="Protect config",
    condition={"path": {"contains": ".config"}},
    decision="prompt",
    priority=20  # Higher priority
)

# Check permission
result = manager.check_permission(
    "file_write",
    "write",
    {"path": "/home/user/project/.config/settings.json"}
)
print(result.reason)  # "Context rule: prompt" (higher priority wins)
```

### Permission Profiles

```python
from lyra_permissions import PermissionManager

manager = PermissionManager()

# Development mode - more permissive
manager.granular_controller.set_profile("development")
result1 = manager.check_permission("file_write", "write", {"path": "/tmp/test.txt"})
print(result1.allow)  # True

# Production mode - more restrictive
manager.granular_controller.set_profile("production")
result2 = manager.check_permission("file_write", "write", {"path": "/var/data.txt"})
print(result2.allow)  # False (requires prompt)
```

### Time-Based Permissions

```python
from datetime import time
from lyra_permissions import PermissionManager, PermissionDecision

manager = PermissionManager()

# Allow deployments only during maintenance window (2 AM - 4 AM)
manager.time_controller.add_time_rule(
    start_time=time(2, 0),
    end_time=time(4, 0),
    decision=PermissionDecision.ALLOW,
    days=None  # All days
)

# Check if work hours
if manager.time_controller.is_work_hours():
    print("Work hours: 9 AM - 5 PM, Monday-Friday")
```

## Version

Current version: **0.1.0**

## Changes

### Phase 3 (Current)
- Added `GranularController` for tool-specific and context-aware permissions
- Added `PermissionProfile` for environment-specific permission sets
- Added `TimeBasedController` for time-of-day permissions
- Integrated granular control with `PermissionManager`
- Built-in profiles: default, development, production
- Context rule priority system
- 16 new tests (61 total, 83% coverage)

### Phase 2
- Added `BypassMode` for auto-accepting permissions
- Added `AuditLogger` for tracking all permission decisions
- Added `SafetyGuardrails` for protecting critical operations
- 21 tests (45 total, 85% coverage)

### Phase 1
- Added `PermissionManager` for central permission control
- Added `PermissionPolicy` for rule-based evaluation
- Added `PermissionStore` for persistent preferences
- 24 tests (95% coverage)

## Next Phase

Phase 4 will implement:
- CLI integration (`lyra permissions` commands)
- Desktop app UI for permission management
- Real-time permission monitoring
- Permission analytics and reporting

## References

- Lyra Bypass Permissions Plan: `.omc/plans/LYRA_BYPASS_PERMISSIONS_PLAN.md`
- GitHub Repository: https://github.com/ndqkhanh/lyra

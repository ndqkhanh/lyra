# Lyra Permissions - Complete Implementation

## Overview

Complete permission management system for Lyra with bypass mode, granular control, and CLI interface.

## Features

### 1. Permission System Foundation (Phase 1)
- 4 permission levels: SAFE, MEDIUM, DANGEROUS, CRITICAL
- 4 permission policies: STRICT, BALANCED, PERMISSIVE, BYPASS
- Persistent permission storage
- Risk assessment engine

### 2. Bypass Mode (Phase 2)
- Auto-accept permissions with audit logging
- Multiple toggle methods (CLI, env var, config, runtime)
- Safety guardrails for critical operations
- Audit trail with export capabilities

### 3. Granular Control (Phase 3)
- Tool-specific permissions
- Context-aware rules with priority system
- Permission profiles (default, development, production)
- Time-based permissions

### 4. CLI Interface (Phase 4)
- Complete command-line interface
- Profile management
- Audit log viewing and export
- Permission configuration

## Installation

```bash
pip install lyra-permissions
```

## Quick Start

### CLI Usage

```bash
# Enable bypass mode
lyra-permissions bypass-on

# Set profile
lyra-permissions profile-set development

# View status
lyra-permissions status

# View audit log
lyra-permissions audit-log --limit 20

# Allow/deny operations
lyra-permissions allow file_write write
lyra-permissions deny file_delete delete

# Export audit log
lyra-permissions audit-export audit.json --format json
```

### Python API

```python
from lyra_permissions import PermissionManager

# Initialize manager
manager = PermissionManager()

# Enable bypass mode
manager.bypass_mode.enable()

# Set profile
manager.granular_controller.set_profile("development")

# Check permission
result = manager.check_permission(
    tool="file_write",
    operation="write",
    context={"path": "/tmp/test.txt"}
)

print(f"Allowed: {result.allow}")
print(f"Reason: {result.reason}")

# View audit log
entries = manager.audit_logger.get_recent(limit=10)
for entry in entries:
    print(f"{entry['timestamp']}: {entry['tool']}.{entry['operation']}")
```

## CLI Commands

### Bypass Mode
- `bypass-on` - Enable bypass mode
- `bypass-off` - Disable bypass mode
- `bypass-toggle` - Toggle bypass mode
- `bypass-status` - Show bypass mode status

### Profiles
- `profile-list` - List available profiles
- `profile-set <profile>` - Set current profile
- `profile-show` - Show current profile details

### Audit Log
- `audit-log [--limit N]` - Show recent audit entries
- `audit-stats` - Show audit statistics
- `audit-export <file> [--format json|csv]` - Export audit log
- `audit-clear [--confirm]` - Clear audit log

### Permissions
- `allow <tool> <operation>` - Allow tool operation
- `deny <tool> <operation>` - Deny tool operation
- `remove <tool> <operation>` - Remove permission preference
- `list` - List all permission preferences

### Status
- `status` - Show complete permission system status

## Architecture

```
┌─────────────────────────────────────────┐
│    CLI Interface                        │
│  (Command-line Management)              │
│                                         │
│  • Bypass mode commands                │
│  • Profile management                  │
│  • Audit log viewing                   │
│  • Permission configuration            │
└─────────────────────────────────────────┘
           │
           ↓
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
           ├─→ Bypass Mode (auto-accept)
           ├─→ Granular Control (rules)
           ├─→ Audit Logger (tracking)
           ├─→ Permission Store (preferences)
           └─→ Policy Engine (evaluation)
```

## Configuration Files

### Bypass Mode (`~/.lyra/config.json`)
```json
{
  "bypassPermissions": true
}
```

### Granular Permissions (`~/.lyra/granular_permissions.json`)
```json
{
  "currentProfile": "development",
  "profiles": {
    "development": {
      "toolPermissions": {
        "file_read:*": "always_allow",
        "file_write:*": "bypass_if_safe"
      },
      "contextRules": [
        {
          "name": "Allow temp directory",
          "condition": {"path": {"startswith": "/tmp"}},
          "decision": "allow",
          "priority": 10
        }
      ]
    }
  }
}
```

### User Preferences (`~/.lyra/permissions.json`)
```json
{
  "policy": "balanced",
  "allowList": ["file_read:read"],
  "denyList": ["file_delete:delete"]
}
```

### Audit Log (`~/.lyra/audit.log`)
```json
{"timestamp": "2026-05-19T...", "tool": "file_write", "operation": "write", "decision": "allow", "level": "medium"}
```

## Testing

Run tests:
```bash
cd packages/lyra-permissions
pip install -e .
pytest tests/ -v
```

**Test Results**: 78 tests, 86% coverage

## Version

Current version: **0.1.0**

## Complete Feature List

### Phase 1: Permission System Foundation
- ✅ PermissionManager with risk assessment
- ✅ 4 permission levels (SAFE, MEDIUM, DANGEROUS, CRITICAL)
- ✅ 4 permission policies (STRICT, BALANCED, PERMISSIVE, BYPASS)
- ✅ PermissionStore with persistent preferences
- ✅ PolicyEngine for rule-based evaluation
- ✅ 24 tests, 95% coverage

### Phase 2: Bypass Mode Implementation
- ✅ BypassMode with multiple toggle methods
- ✅ AuditLogger with export capabilities (JSON, CSV)
- ✅ SafetyGuardrails for critical operation protection
- ✅ Visual status indicators
- ✅ Audit statistics tracking
- ✅ 21 tests (45 total), 85% coverage

### Phase 3: Granular Permission Control
- ✅ GranularController with tool-specific permissions
- ✅ Context-aware rules with priority system
- ✅ PermissionProfile for environment-specific settings
- ✅ TimeBasedController for temporal permissions
- ✅ Built-in profiles (default, development, production)
- ✅ 16 tests (61 total), 83% coverage

### Phase 4: Integration & UI
- ✅ Complete CLI interface (PermissionCLI)
- ✅ 20+ CLI commands
- ✅ Profile management commands
- ✅ Audit log viewing and export
- ✅ Permission configuration commands
- ✅ Status reporting
- ✅ 17 tests (78 total), 86% coverage

## Usage Examples

### Example 1: Development Workflow

```bash
# Set development profile
lyra-permissions profile-set development

# Enable bypass mode for faster iteration
lyra-permissions bypass-on

# Check status
lyra-permissions status

# Work on your project...
# All non-critical operations auto-accepted

# View what was auto-accepted
lyra-permissions audit-log --limit 50

# Disable bypass mode when done
lyra-permissions bypass-off
```

### Example 2: Production Deployment

```bash
# Set production profile
lyra-permissions profile-set production

# Ensure bypass mode is off
lyra-permissions bypass-off

# All operations will require confirmation
# Critical operations always prompt

# Export audit log for compliance
lyra-permissions audit-export /var/log/lyra-audit.json
```

### Example 3: Custom Permissions

```python
from lyra_permissions import PermissionManager, ToolPermission

manager = PermissionManager()

# Allow all file reads
manager.granular_controller.add_tool_permission(
    "file_read", "*", ToolPermission.ALWAYS_ALLOW
)

# Prompt for database operations
manager.granular_controller.add_tool_permission(
    "database", "*", ToolPermission.ALWAYS_PROMPT
)

# Allow operations in project directory
manager.granular_controller.add_context_rule(
    name="Allow project dir",
    condition={"path": {"startswith": "/home/user/project"}},
    decision="allow",
    priority=10
)
```

## Next Steps

The permission system is now complete and ready for integration into Lyra! 

Potential future enhancements:
- Desktop app UI for visual permission management
- Real-time permission monitoring dashboard
- Permission analytics and reporting
- Machine learning for permission pattern detection
- Team-based permission sharing
- Cloud sync for permission preferences

## References

- Lyra Bypass Permissions Plan: `.omc/plans/LYRA_BYPASS_PERMISSIONS_PLAN.md`
- GitHub Repository: https://github.com/ndqkhanh/lyra

---

**Status**: ✅ All 4 phases complete! Ready for production use.

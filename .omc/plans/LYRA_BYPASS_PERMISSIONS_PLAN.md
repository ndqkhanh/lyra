# Lyra Bypass Permissions Mode - Implementation Plan

## Overview

Add a bypass permissions mode to Lyra that allows auto-accepting tool permissions, similar to Claude Code's permission system. This feature will enable faster development workflows while maintaining safety guardrails.

## Goals

1. **Seamless Development**: Enable rapid iteration without permission prompts
2. **Safety First**: Maintain security boundaries for destructive operations
3. **Flexible Control**: Allow granular permission configuration
4. **User Experience**: Provide clear visual feedback when bypass mode is active

## Architecture

### Phase 1: Permission System Foundation (Week 1)

**Package**: `lyra-permissions`

**Components**:
1. **Permission Manager** (`permission_manager.py`)
   - Central permission registry
   - Permission level definitions (SAFE, MEDIUM, DANGEROUS)
   - Tool categorization by risk level
   - Permission decision engine

2. **Permission Policy** (`permission_policy.py`)
   - Policy definitions (STRICT, BALANCED, PERMISSIVE, BYPASS)
   - Rule-based permission evaluation
   - Context-aware permission decisions
   - Audit logging

3. **Permission Store** (`permission_store.py`)
   - Persistent permission preferences
   - User-defined allow/deny lists
   - Session-based permission cache
   - JSON-based configuration storage

**Risk Levels**:
```python
class PermissionLevel(Enum):
    SAFE = "safe"           # Always allow (Read, List, Search)
    MEDIUM = "medium"       # Prompt once per session (Edit, Write)
    DANGEROUS = "dangerous" # Always prompt (Delete, Execute, Deploy)
    CRITICAL = "critical"   # Require explicit confirmation (Drop DB, Force Push)
```

**Permission Policies**:
```python
class PermissionPolicy(Enum):
    STRICT = "strict"         # Prompt for everything except SAFE
    BALANCED = "balanced"     # Prompt for DANGEROUS and CRITICAL
    PERMISSIVE = "permissive" # Only prompt for CRITICAL
    BYPASS = "bypass"         # Auto-accept all (with audit log)
```

### Phase 2: Bypass Mode Implementation (Week 2)

**Features**:
1. **Bypass Mode Toggle**
   - CLI flag: `--bypass-permissions` or `-bp`
   - Environment variable: `LYRA_BYPASS_PERMISSIONS=true`
   - Config file: `~/.lyra/config.json` → `"bypassPermissions": true`
   - Runtime toggle: `/bypass on` or `/bypass off`

2. **Visual Indicators**
   - Banner notification when bypass mode is active
   - Status bar indicator: `[BYPASS MODE]` in red/yellow
   - Tool execution logs show "AUTO-ACCEPTED" tag
   - Session summary shows bypass mode usage stats

3. **Audit Trail**
   - Log all auto-accepted permissions to `~/.lyra/audit.log`
   - Include: timestamp, tool, operation, risk level, context
   - Exportable audit reports (JSON, CSV)
   - Retention policy (default: 30 days)

4. **Safety Guardrails**
   - Even in bypass mode, CRITICAL operations require confirmation
   - Destructive operations show preview before execution
   - Rollback capability for file operations
   - Emergency stop mechanism (Ctrl+C)

### Phase 3: Granular Permission Control (Week 3)

**Features**:
1. **Tool-Specific Permissions**
   ```json
   {
     "permissions": {
       "read": "always_allow",
       "write": "prompt_once",
       "delete": "always_prompt",
       "execute": "bypass_if_safe"
     }
   }
   ```

2. **Context-Aware Permissions**
   - Allow bypass for specific directories (e.g., `/tmp`, `~/.lyra/cache`)
   - Deny bypass for sensitive paths (e.g., `/etc`, `~/.ssh`)
   - Time-based permissions (e.g., bypass during work hours)
   - Project-specific permission profiles

3. **Permission Profiles**
   - **Development Profile**: Bypass most operations, prompt for deployments
   - **Production Profile**: Strict mode, prompt for everything
   - **Testing Profile**: Bypass file operations, prompt for network calls
   - **Custom Profiles**: User-defined permission sets

### Phase 4: Integration & UI (Week 4)

**Features**:
1. **CLI Integration**
   ```bash
   lyra --bypass-permissions chat "Refactor the auth module"
   lyra --permission-policy=permissive research "AI agents"
   lyra --audit-log=/path/to/audit.log
   ```

2. **Interactive Mode**
   - `/bypass on` - Enable bypass mode
   - `/bypass off` - Disable bypass mode
   - `/bypass status` - Show current permission policy
   - `/bypass audit` - View recent auto-accepted permissions
   - `/bypass reset` - Reset to default policy

3. **Configuration UI**
   ```bash
   lyra config permissions
   # Interactive menu:
   # 1. Set permission policy (STRICT/BALANCED/PERMISSIVE/BYPASS)
   # 2. Configure tool-specific permissions
   # 3. Manage allow/deny lists
   # 4. View audit logs
   # 5. Export configuration
   ```

4. **Desktop App Integration**
   - Settings panel for permission configuration
   - Real-time permission activity monitor
   - Visual permission policy selector
   - Audit log viewer with filtering

## Implementation Details

### Permission Manager

```python
class PermissionManager:
    def __init__(self):
        self.policy = PermissionPolicy.BALANCED
        self.store = PermissionStore()
        self.audit_logger = AuditLogger()
    
    def check_permission(
        self,
        tool: str,
        operation: str,
        context: Dict[str, Any]
    ) -> PermissionDecision:
        """Check if operation is allowed."""
        risk_level = self._assess_risk(tool, operation, context)
        
        # CRITICAL operations always require confirmation
        if risk_level == PermissionLevel.CRITICAL:
            return PermissionDecision.PROMPT
        
        # Check policy
        if self.policy == PermissionPolicy.BYPASS:
            self.audit_logger.log(tool, operation, "AUTO_ACCEPTED")
            return PermissionDecision.ALLOW
        
        # Check user preferences
        if self.store.is_allowed(tool, operation):
            return PermissionDecision.ALLOW
        
        if self.store.is_denied(tool, operation):
            return PermissionDecision.DENY
        
        # Apply policy rules
        return self._apply_policy(risk_level)
    
    def _assess_risk(
        self,
        tool: str,
        operation: str,
        context: Dict[str, Any]
    ) -> PermissionLevel:
        """Assess risk level of operation."""
        # Check operation type
        if operation in ["delete", "drop", "force_push"]:
            return PermissionLevel.CRITICAL
        
        if operation in ["execute", "deploy", "modify"]:
            return PermissionLevel.DANGEROUS
        
        if operation in ["write", "create", "update"]:
            return PermissionLevel.MEDIUM
        
        # Default to SAFE for read operations
        return PermissionLevel.SAFE
```

### Audit Logger

```python
class AuditLogger:
    def __init__(self, log_path: str = "~/.lyra/audit.log"):
        self.log_path = Path(log_path).expanduser()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log(
        self,
        tool: str,
        operation: str,
        decision: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log permission decision."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "operation": operation,
            "decision": decision,
            "context": context or ,
            "session_id": self._get_session_id()
        }
        
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit entries."""
        entries = []
        with open(self.log_path, "r") as f:
            for line in f:
                entries.append(json.loads(line))
        return entries[-limit:]
```

## Safety Considerations

### 1. Critical Operations Protection
Even in bypass mode, these operations ALWAYS require confirmation:
- Database drops/truncates
- Force push to main/master
- Deletion of multiple files (>10)
- System-level operations (sudo, rm -rf)
- Production deployments
- Secret/credential modifications

### 2. Rollback Capability
- File operations create automatic backups
- Git operations preserve reflog
- Database operations use transactions
- Rollback command: `/rollback` or `lyra rollback`

### 3. Emergency Stop
- Ctrl+C immediately halts execution
- `/stop` command cancels pending operations
- Automatic rollback on error

### 4. Audit Trail
- All auto-accepted permissions logged
- Exportable for compliance/review
- Retention policy configurable
- Searchable audit logs

## Testing Strategy

### Unit Tests
- Permission policy evaluation
- Risk level assessment
- Audit logging
- Configuration management

### Integration Tests
- CLI flag handling
- Environment variable parsing
- Config file loading
- Runtime toggle

### E2E Tests
- Full bypass mode workflow
- Permission prompt scenarios
- Audit log generation
- Rollback functionality

### Security Tests
- Critical operation protection
- Malicious input handling
- Path traversal prevention
- Privilege escalation checks

## Configuration Examples

### Strict Mode (Default)
```json
{
  "permissionPolicy": "strict",
  "bypassPermissions": false,
  "auditLog": "~/.lyra/audit.log",
  "allowList": [],
  "denyList": []
}
```

### Development Mode
```json
{
  "permissionPolicy": "permissive",
  "bypassPermissions": true,
  "auditLog": "~/.lyra/audit.log",
  "allowList": ["read", "write", "execute"],
  "denyList": ["delete", "deploy"],
  "contextRules": {
    "allowPaths": ["/tmp", "~/.lyra/cache", "./test"],
    "denyPaths": ["/etc", "~/.ssh", "/var"]
  }
}
```

### Production Mode
```json
{
  "permissionPolicy": "strict",
  "bypassPermissions": false,
  "auditLog": "/var/log/lyra/audit.log",
  "allowList": ["read"],
  "denyList": ["delete", "execute", "deploy", "modify"],
  "requireConfirmation": true
}
```

## Success Metrics

1. **Performance**: Permission checks add <10ms latency
2. **Usability**: 90% reduction in permission prompts in bypass mode
3. **Safety**: Zero critical operations auto-accepted
4. **Audit**: 100% of auto-accepted permissions logged
5. **Adoption**: 70% of users enable bypass mode for development

## Timeline

- **Week 1**: Permission system foundation (Phase 1)
- **Week 2**: Bypass mode implementation (Phase 2)
- **Week 3**: Granular permission control (Phase 3)
- **Week 4**: Integration & UI (Phase 4)
- **Week 5**: Testing & documentation
- **Week 6**: Beta release & feedback

## Future Enhancements

1. **Machine Learning**: Learn user permission patterns
2. **Team Policies**: Shared permission profiles for teams
3. **Cloud Sync**: Sync permission preferences across devices
4. **Advanced Audit**: Real-time audit dashboard
5. **Compliance**: GDPR/SOC2 audit report generation

## References

- Claude Code permission system
- VS Code extension permissions
- GitHub Actions permissions model
- AWS IAM policy structure

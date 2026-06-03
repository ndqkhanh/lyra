# Multi-Tenant Architecture Design for Lyra

**Date:** 2026-05-29  
**Status:** Proposed Design  
**Prerequisites:** Read [MULTI-TENANT-EVALUATION.md](./MULTI-TENANT-EVALUATION.md) first

---

## Design Principles

1. **Incremental Adoption:** Multi-tenancy is opt-in, not forced on CLI users
2. **Backward Compatibility:** Existing single-user code continues to work
3. **Security First:** Tenant isolation enforced at every layer
4. **Performance Conscious:** Minimize overhead for single-tenant deployments
5. **Operational Simplicity:** Avoid unnecessary infrastructure dependencies

---

## Architecture Overview

### Dual-Mode Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Lyra Core Library                        │
│  ├── AgentProtocol (unchanged)                             │
│  ├── AgentSession (add optional tenant_context)            │
│  ├── AgentDaemon (add optional tenant_context)             │
│  └── TenantBridge (existing, enhanced)                     │
└─────────────────────────────────────────────────────────────┘
                    ↓                    ↓
        ┌───────────────────┐  ┌───────────────────────┐
        │   CLI Mode        │  │   Hosted Mode         │
        │   (Single-User)   │  │   (Multi-Tenant)      │
        └───────────────────┘  └───────────────────────┘
                ↓                          ↓
        ┌───────────────────┐  ┌───────────────────────┐
        │ Local Daemon      │  │ API Server            │
        │ Unix Socket       │  │ FastAPI + PostgreSQL  │
        │ No DB Required    │  │ Tenant Middleware     │
        └───────────────────┘  └───────────────────────┘
```

---

## Component Design

### 1. Enhanced TenantContext

**File:** `lyra_core/multi_tenant/__init__.py`

**Current Implementation:**
```python
@dataclass
class TenantContext:
    tenant_id: str
    tier: TenantTier = TenantTier.FREE
    metadata: TenantMetadata = field(default_factory=TenantMetadata)
    created_at: float = field(default_factory=time.time)
```

**Proposed Enhancement:**
```python
@dataclass
class TenantContext:
    tenant_id: str
    tier: TenantTier = TenantTier.FREE
    metadata: TenantMetadata = field(default_factory=TenantMetadata)
    created_at: float = field(default_factory=time.time)
    
    # New fields for hosted mode
    user_id: str | None = None
    user_role: str = "member"  # owner, admin, member
    organization_id: int | None = None  # DB primary key (hosted mode only)
    
    @property
    def is_owner(self) -> bool:
        return self.user_role == "owner"
    
    @property
    def is_admin(self) -> bool:
        return self.user_role in ("owner", "admin")
    
    def can_spawn_agents(self) -> bool:
        return self.is_admin or self.tier != TenantTier.FREE
    
    def can_terminate_agents(self, agent_owner_id: str) -> bool:
        return self.is_admin or self.user_id == agent_owner_id
```

**Rationale:** Extend existing `TenantContext` with RBAC fields, but keep them optional for CLI mode.

---

### 2. Tenant-Aware AgentSession

**File:** `lyra_core/agent/session.py`

**Current Implementation:**
```python
class AgentSession:
    def __init__(
        self,
        agent: AgentProtocol,
        *,
        session_id: str | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._agent = agent
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
        # ...
```

**Proposed Enhancement:**
```python
class AgentSession:
    def __init__(
        self,
        agent: AgentProtocol,
        *,
        session_id: str | None = None,
        bus: EventBus | None = None,
        tenant_context: TenantContext | None = None,  # NEW
    ) -> None:
        self._agent = agent
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
        self._tenant_context = tenant_context  # NEW
        # ...
    
    @property
    def tenant_context(self) -> TenantContext | None:
        return self._tenant_context
    
    def snapshot(self) -> SessionSnapshot:
        snap = SessionSnapshot(
            session_id=self.session_id,
            agent_id=self._agent.identity.agent_id,
            # ... existing fields
        )
        if self._tenant_context:
            snap.metadata["tenant_id"] = self._tenant_context.tenant_id
            snap.metadata["user_id"] = self._tenant_context.user_id or ""
        return snap
```

**Rationale:** Sessions optionally carry tenant context, but remain functional without it (CLI mode).

---

### 3. Tenant-Aware AgentDaemon

**File:** `lyra_core/agent/daemon.py`

**Current Implementation:**
```python
class AgentDaemon:
    def __init__(
        self,
        config: DaemonConfig | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self.config = config or DaemonConfig()
        self._sessions: dict[str, AgentSession] = {}
        # ...
```

**Proposed Enhancement:**
```python
class AgentDaemon:
    def __init__(
        self,
        config: DaemonConfig | None = None,
        bus: EventBus | None = None,
        tenant_bridge: TenantBridge | None = None,  # NEW
    ) -> None:
        self.config = config or DaemonConfig()
        self._sessions: dict[str, AgentSession] = {}
        self._tenant_bridge = tenant_bridge  # NEW
        # ...
    
    async def spawn(
        self,
        agent,
        *,
        session_id: str | None = None,
        metadata: dict[str, str] | None = None,
        tenant_context: TenantContext | None = None,  # NEW
    ) -> AgentSession:
        # Validate tenant permissions
        if tenant_context and not tenant_context.can_spawn_agents():
            raise PermissionError(
                f"Tenant {tenant_context.tenant_id} cannot spawn agents"
            )
        
        # Enforce per-tenant session limits
        if tenant_context:
            tenant_sessions = [
                s for s in self._sessions.values()
                if s.tenant_context and s.tenant_context.tenant_id == tenant_context.tenant_id
            ]
            if len(tenant_sessions) >= self._get_tenant_limit(tenant_context):
                raise RuntimeError(
                    f"Tenant {tenant_context.tenant_id} has reached max sessions"
                )
        
        session = AgentSession(
            agent,
            session_id=session_id,
            bus=self._bus,
            tenant_context=tenant_context,  # NEW
        )
        # ... rest of spawn logic
    
    def _get_tenant_limit(self, ctx: TenantContext) -> int:
        """Return max sessions for tenant tier."""
        return {
            TenantTier.FREE: 2,
            TenantTier.PRO: 10,
            TenantTier.ENTERPRISE: 50,
            TenantTier.INTERNAL: 1000,
        }.get(ctx.tier, 2)
    
    def list_sessions(
        self,
        status: SessionStatus | None = None,
        tenant_id: str | None = None,  # NEW
    ) -> list[AgentSession]:
        sessions = list(self._sessions.values())
        if status:
            sessions = [s for s in sessions if s.status == status]
        if tenant_id:
            sessions = [
                s for s in sessions
                if s.tenant_context and s.tenant_context.tenant_id == tenant_id
            ]
        return sessions
```

**Rationale:** Daemon enforces per-tenant resource limits, but remains functional without tenant context (CLI mode).

---

### 4. API Server (Hosted Mode Only)

**File:** `lyra_api/server.py` (new package)

```python
from fastapi import FastAPI, Depends, HTTPException
from lyra_core.agent import AgentDaemon
from lyra_core.multi_tenant import TenantBridge, TenantContext

app = FastAPI()
daemon = AgentDaemon(tenant_bridge=TenantBridge())

# Middleware: Extract tenant context from request
async def get_tenant_context(
    tenant_id: str,
    user_id: str = Depends(get_current_user),
) -> TenantContext:
    bridge = daemon._tenant_bridge
    ctx = bridge.resolve(tenant_id)
    if not ctx:
        raise HTTPException(404, "Tenant not found")
    
    # Verify user is a member of this tenant
    if not ctx.metadata.get(f"member:{user_id}"):
        raise HTTPException(403, "Not a member of this tenant")
    
    # Inject user_id and role
    ctx.user_id = user_id
    ctx.user_role = ctx.metadata.get(f"role:{user_id}", "member")
    return ctx

# Endpoint: Spawn agent
@app.post("/api/v1/tenants/{tenant_id}/agents/spawn")
async def spawn_agent(
    tenant_id: str,
    agent_config: dict,
    ctx: TenantContext = Depends(get_tenant_context),
):
    agent = create_agent_from_config(agent_config)
    session = await daemon.spawn(agent, tenant_context=ctx)
    return {"session_id": session.session_id, "status": session.status.value}

# Endpoint: List sessions
@app.get("/api/v1/tenants/{tenant_id}/sessions")
async def list_sessions(
    tenant_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
):
    sessions = daemon.list_sessions(tenant_id=tenant_id)
    return [s.summary() for s in sessions]
```

**Rationale:** FastAPI server wraps `AgentDaemon` with tenant middleware, but core logic remains in `lyra_core`.

---

### 5. Database Schema (Hosted Mode Only)

**File:** `lyra_api/migrations/001_multi_tenant.sql`

```sql
-- Organizations (Tenants)
CREATE TABLE organizations (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL UNIQUE,  -- Maps to TenantContext.tenant_id
    name VARCHAR(255) NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_organizations_tenant_id ON organizations(tenant_id);

-- Users
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,  -- Maps to TenantContext.user_id
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Organization Members
CREATE TABLE organization_members (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',  -- owner, admin, member
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

CREATE INDEX idx_org_members_org ON organization_members(organization_id);
CREATE INDEX idx_org_members_user ON organization_members(user_id);

-- Agent Sessions (persistent snapshots)
CREATE TABLE agent_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    snapshot JSONB  -- SessionSnapshot serialized
);

CREATE INDEX idx_sessions_org ON agent_sessions(organization_id);
CREATE INDEX idx_sessions_user ON agent_sessions(user_id);
CREATE INDEX idx_sessions_status ON agent_sessions(status);
```

**Rationale:** Minimal schema for tenant metadata and session persistence. Core agent logic remains in-memory (no DB dependency for CLI mode).

---

## Security Architecture

### 1. Tenant Isolation Enforcement

**Layer 1: Middleware (API Server)**
```python
async def get_tenant_context(tenant_id: str, user_id: str) -> TenantContext:
    # Verify user is a member of tenant
    if not is_member(tenant_id, user_id):
        raise HTTPException(403, "Not a member")
    return resolve_tenant(tenant_id)
```

**Layer 2: Daemon (Resource Limits)**
```python
async def spawn(self, agent, tenant_context: TenantContext):
    # Enforce per-tenant session limits
    if len(tenant_sessions) >= limit:
        raise RuntimeError("Max sessions reached")
```

**Layer 3: Database (Row-Level Security)**
```sql
-- Every query scoped to organization_id
SELECT * FROM agent_sessions 
WHERE organization_id = $1 AND session_id = $2;
```

---

### 2. Credential Isolation

**Per-Tenant Vaults:**
```
~/.lyra/tenants/
├── acme-corp/
│   ├── auth.json (encrypted)
│   └── metadata.json
└── other-corp/
    ├── auth.json (encrypted)
    └── metadata.json
```

**Resolution Order:**
1. Environment variable (global override)
2. Tenant vault (`~/.lyra/tenants/{tenant_id}/auth.json`)
3. Global fallback (`~/.lyra/auth.json`)

**Encryption:** Use `cryptography.fernet` for at-rest encryption.

```python
from cryptography.fernet import Fernet

class TenantVault:
    def save_credential(self, provider: str, api_key: str) -> None:
        key = self._get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(api_key.encode())
        
        auth_data = json.loads(self.auth_path.read_text() or "{}")
        auth_data[provider] = encrypted.decode()
        self.auth_path.write_text(json.dumps(auth_data, indent=2))
    
    def load_credential(self, provider: str) -> str | None:
        auth_data = json.loads(self.auth_path.read_text() or "{}")
        encrypted = auth_data.get(provider)
        if not encrypted:
            return None
        
        key = self._get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
    
    def _get_encryption_key(self) -> bytes:
        # Derive key from tenant_id + system secret
        secret = os.environ.get("LYRA_ENCRYPTION_SECRET", "default-secret")
        return Fernet.generate_key()  # In production, use PBKDF2
```

---

### 3. Audit Logging

**File:** `lyra_core/multi_tenant/audit.py`

```python
from dataclasses import dataclass
import time

@dataclass
class AuditEvent:
    tenant_id: str
    user_id: str
    action: str  # "agent.spawned", "session.terminated"
    resource_type: str
    resource_id: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, str] = field(default_factory=dict)

class AuditLogger:
    def __init__(self, storage: AuditStorage):
        self._storage = storage
    
    def log(self, event: AuditEvent) -> None:
        self._storage.append(event)
    
    def query(
        self,
        tenant_id: str,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> list[AuditEvent]:
        return self._storage.query(tenant_id, start_time, end_time)
```

**Integration:**
```python
# In AgentDaemon.spawn()
if tenant_context:
    audit_logger.log(AuditEvent(
        tenant_id=tenant_context.tenant_id,
        user_id=tenant_context.user_id,
        action="agent.spawned",
        resource_type="agent_session",
        resource_id=session.session_id,
    ))
```

---

## Performance Optimization

### 1. Tenant Context Caching

**Problem:** Middleware queries DB 3 times per request (org lookup, membership check, role lookup).

**Solution:** Cache tenant context in Redis (TTL: 5 minutes).

```python
import redis

class TenantContextCache:
    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client
    
    def get(self, tenant_id: str, user_id: str) -> TenantContext | None:
        key = f"tenant:{tenant_id}:user:{user_id}"
        data = self._redis.get(key)
        if data:
            return TenantContext(**json.loads(data))
        return None
    
    def set(self, ctx: TenantContext, ttl: int = 300) -> None:
        key = f"tenant:{ctx.tenant_id}:user:{ctx.user_id}"
        self._redis.setex(key, ttl, json.dumps(ctx.__dict__))
```

**Impact:** Reduce middleware latency from 20ms → 2ms (10x improvement).

---

### 2. Credential Caching

**Problem:** Loading credentials from disk on every agent spawn (10-25ms).

**Solution:** In-memory LRU cache with TTL.

```python
from functools import lru_cache
import time

class TenantVault:
    _cache: dict[str, tuple[str, float]] = {}  # {key: (value, expiry)}
    _cache_ttl = 300  # 5 minutes
    
    def load_credential(self, provider: str) -> str | None:
        cache_key = f"{self.tenant_id}:{provider}"
        if cache_key in self._cache:
            value, expiry = self._cache[cache_key]
            if time.time() < expiry:
                return value
        
        # Cache miss — load from disk
        value = self._load_from_disk(provider)
        if value:
            self._cache[cache_key] = (value, time.time() + self._cache_ttl)
        return value
```

**Impact:** Reduce credential load time from 10ms → <1ms (10x improvement).

---

### 3. Database Query Optimization

**Problem:** Listing sessions requires full table scan.

**Solution:** Composite indexes on `(organization_id, status)`.

```sql
CREATE INDEX idx_sessions_org_status 
ON agent_sessions(organization_id, status);

-- Query becomes index-only scan
SELECT * FROM agent_sessions 
WHERE organization_id = $1 AND status = 'running';
```

**Impact:** Reduce query time from 50ms → 5ms (10x improvement).

---

## Migration Path

### Phase 1: Foundation (Week 1-2)

**Goal:** Extend existing components with optional tenant context.

**Tasks:**
- [x] `TenantContext`, `TenantVault`, `TenantBridge` (already implemented)
- [ ] Add `tenant_context` parameter to `AgentSession.__init__()`
- [ ] Add `tenant_context` parameter to `AgentDaemon.spawn()`
- [ ] Add `tenant_id` filter to `AgentDaemon.list_sessions()`
- [ ] Write unit tests for tenant-aware session management

**Deliverable:** CLI mode continues to work, hosted mode can inject tenant context.

---

### Phase 2: API Server (Week 3-4)

**Goal:** Build FastAPI server with tenant middleware.

**Tasks:**
- [ ] Create `lyra_api` package
- [ ] Implement tenant middleware (`get_tenant_context`)
- [ ] Implement endpoints: `/tenants/{id}/agents/spawn`, `/tenants/{id}/sessions`
- [ ] Add PostgreSQL schema migration
- [ ] Write integration tests for API endpoints

**Deliverable:** Hosted mode functional, but no authentication yet.

---

### Phase 3: Security (Week 5-6)

**Goal:** Add authentication, RBAC, and audit logging.

**Tasks:**
- [ ] Implement OAuth integration (GitHub, GitLab)
- [ ] Add RBAC decorators (`@require_role`)
- [ ] Implement audit logging (`AuditLogger`)
- [ ] Encrypt tenant vault credentials (`cryptography.fernet`)
- [ ] Write security tests (tenant isolation, permission checks)

**Deliverable:** Production-ready security posture.

---

### Phase 4: Performance (Week 7-8)

**Goal:** Optimize for production load.

**Tasks:**
- [ ] Add Redis caching for tenant context
- [ ] Add in-memory credential cache
- [ ] Add database indexes for common queries
- [ ] Load testing (1000 concurrent sessions)
- [ ] Performance profiling and optimization

**Deliverable:** <50ms p99 latency for API endpoints.

---

## Testing Strategy

### 1. Unit Tests

**Tenant Isolation:**
```python
def test_daemon_enforces_tenant_session_limits():
    bridge = TenantBridge()
    ctx = bridge.register("acme", tier=TenantTier.FREE)
    daemon = AgentDaemon(tenant_bridge=bridge)
    
    # FREE tier allows 2 sessions
    await daemon.spawn(agent1, tenant_context=ctx)
    await daemon.spawn(agent2, tenant_context=ctx)
    
    # Third spawn should fail
    with pytest.raises(RuntimeError, match="Max sessions reached"):
        await daemon.spawn(agent3, tenant_context=ctx)
```

**Permission Checks:**
```python
def test_member_cannot_terminate_other_users_sessions():
    ctx = TenantContext(
        tenant_id="acme",
        user_id="alice",
        user_role="member",
    )
    session = AgentSession(agent, tenant_context=ctx)
    
    # Bob (member) tries to terminate Alice's session
    bob_ctx = TenantContext(tenant_id="acme", user_id="bob", user_role="member")
    assert not bob_ctx.can_terminate_agents(session.tenant_context.user_id)
```

---

### 2. Integration Tests

**Cross-Tenant Isolation:**
```python
async def test_tenant_cannot_access_other_tenant_sessions():
    daemon = AgentDaemon(tenant_bridge=TenantBridge())
    
    # Tenant A spawns session
    ctx_a = TenantContext(tenant_id="acme")
    session_a = await daemon.spawn(agent, tenant_context=ctx_a)
    
    # Tenant B tries to list sessions
    ctx_b = TenantContext(tenant_id="other")
    sessions = daemon.list_sessions(tenant_id="other")
    
    # Should not see Tenant A's session
    assert session_a not in sessions
```

---

### 3. Security Tests

**SQL Injection:**
```python
async def test_tenant_id_sql_injection():
    # Attempt SQL injection via tenant_id
    malicious_tenant_id = "acme'; DROP TABLE agent_sessions; --"
    
    with pytest.raises(ValueError, match="Invalid tenant_id"):
        bridge.register(malicious_tenant_id)
```

**Credential Leakage:**
```python
def test_tenant_vault_isolation():
    vault_a = TenantVault("acme")
    vault_a.save_credential("anthropic", "sk-ant-acme-key")
    
    vault_b = TenantVault("other")
    key = vault_b.load_credential("anthropic")
    
    # Should not leak Tenant A's key
    assert key != "sk-ant-acme-key"
```

---

## Operational Considerations

### 1. Deployment

**CLI Mode (No Changes):**
```bash
# Existing workflow continues to work
lyra agent spawn --agent-type claude-code
```

**Hosted Mode (New):**
```bash
# Start API server
lyra-api serve --host 0.0.0.0 --port 8000

# Start agent runners (distributed)
lyra-runner start --api-url https://api.lyra.ai
```

---

### 2. Monitoring

**Metrics to Track:**
- Sessions per tenant (gauge)
- API latency per endpoint (histogram)
- Tenant context cache hit rate (counter)
- Credential load time (histogram)
- Audit log volume per tenant (counter)

**Alerting:**
- Tenant exceeds session limit (warning)
- API p99 latency > 100ms (critical)
- Cache hit rate < 80% (warning)
- Credential load failures (critical)

---

### 3. Backup and Recovery

**Data to Back Up:**
- PostgreSQL database (organizations, users, sessions)
- Tenant vaults (`~/.lyra/tenants/`)
- Audit logs

**Recovery Procedure:**
1. Restore PostgreSQL from backup
2. Restore tenant vaults from backup
3. Restart API server and runners
4. Verify tenant isolation (run security tests)

---

## References

- [US-015-agentsmesh-analysis.md](../../.omc/research/US-015-agentsmesh-analysis.md) — AgentsMesh patterns
- [MULTI-TENANT-EVALUATION.md](./MULTI-TENANT-EVALUATION.md) — Pros/cons analysis
- AgentsMesh source: https://github.com/AgentsMesh/AgentsMesh
- Lyra existing implementation: `packages/lyra-core/src/lyra_core/multi_tenant/`

---

## Conclusion

This design provides a **pragmatic path** to multi-tenancy for Lyra:

1. **Incremental:** Extend existing components, don't rewrite
2. **Backward Compatible:** CLI mode unaffected
3. **Secure:** Tenant isolation at every layer
4. **Performant:** Caching reduces overhead to <5ms
5. **Testable:** Comprehensive test coverage for isolation and permissions

**Next Step:** Gather stakeholder feedback on deployment model (CLI-only vs hosted service) before proceeding with Phase 1 implementation.

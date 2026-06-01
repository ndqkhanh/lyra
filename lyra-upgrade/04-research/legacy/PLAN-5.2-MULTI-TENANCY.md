# Investigation 5.2: Multi-Tenancy Evaluation for Lyra

> **Based on:** STREAM-8 (Terminal Multiplexers), AgentsMesh deep analysis
> **Status:** RECOMMENDATION — Adapt, don't adopt

---

## 1. What Multi-Tenancy Means in This Context

**AgentsMesh** (BSL-1.1 licensed) implements a multi-tenant architecture with:
```
Organization
├── Team: "Backend"
│   ├── Alice (owner) — spawn/terminate all agents
│   ├── Bob (admin) — spawn agents, view logs
│   └── Charlie (member) — view agent status
├── Team: "Frontend"
│   └── ...
└── Shared Agent Pool
    ├── Agent 1: "API refactor" (spawned by Alice)
    ├── Agent 2: "Database migration" (spawned by Bob)
    └── Agent 3: "Test coverage" (spawned by Charlie)
```

Key mechanism: Row-level database isolation (`organization_id` in every query), per-tenant credential vaults, role-based access control.

---

## 2. Pros

### 2.1 Team Collaboration
Multiple developers share agent sessions, task queues, and research artifacts with centralized visibility.

### 2.2 Resource Isolation
In hosted/cloud deployments, tenants cannot access each other's data or credentials. SOC2/GDPR compliance-ready.

### 2.3 Cost Allocation
Per-department usage tracking for AI API costs. Enterprise billing models possible.

### 2.4 Security
Permission boundaries between teams. Agent actions are scoped to tenant workspace.

---

## 3. Cons

### 3.1 Massive Complexity Increase
- Database schema becomes tenant-aware (every table gets `organization_id` FOREIGN KEY)
- Authentication system needs organization/team/role hierarchy
- Session management needs tenant scoping
- Cache invalidation becomes tenant-aware
- Testing complexity multiplies (need tenant isolation tests, cross-tenant leakage tests)

### 3.2 Premature for Lyra's Current Stage
- Lyra is a single-user, local-first system
- No enterprise customers requesting multi-tenancy
- Building multi-tenancy before single-user is stable = architecture risk

### 3.3 Coordination Challenges
- Shared agent pools across tenants require sophisticated scheduling
- Resource contention between tenants (API rate limits, compute)
- Cross-team agent visibility needs careful access control design

### 3.4 Overhead
- Every query adds `WHERE organization_id = $1`
- Tenant context propagation through deeply nested agent call stacks
- Credential vault management per tenant

---

## 4. Recommendation: ADAPT (Not Adopt)

**Skip full multi-tenancy for now.** Instead, implement lightweight **WorkspaceContext** that can evolve into TenantContext later:

### Phase 1: Workspace Isolation (Now)
```python
@dataclass
class WorkspaceContext:
    """Lightweight scoping — single user, multiple workspaces."""
    workspace_id: str          # UUID
    workspace_path: Path       # Filesystem root
    credential_vault: Path     # Per-workspace .env / secrets
    agent_pool: list[str]      # Agents active in this workspace
    task_queue: Path           # Shared task file (JSONL)
    research_artifacts: Path   # Output directory
    
    # Future-proof: this extends naturally to TenantContext
```

### Phase 2: AgentPod Sandboxing (Later)
Each agent gets its own sandboxed workspace, isolated from other agents. This is a natural stepping stone to multi-tenancy.

### Phase 3: Full Multi-Tenancy (Future — only if demanded)
When enterprise customers need `Organization > Team > User` hierarchy, evolve WorkspaceContext into TenantContext.

### Why This Approach:
1. **Immediate value:** Workspace isolation is useful for single users (separate projects don't contaminate each other)
2. **No complexity tax:** No tenant-aware database, no role hierarchy, no cross-tenant leaks to test
3. **Evolution path:** WorkspaceContext → TenantContext is a natural extension, not a rewrite
4. **AgentsMesh lessons learned without BSL-1.1 restrictions:** The design is sound; the timing is wrong

---

## 5. Reference

| Source | License | Key Insight |
|--------|---------|-------------|
| [AgentsMesh](https://github.com/AgentsMesh/AgentsMesh) | BSL-1.1 | `TenantContext` with row-level isolation, role-based access |
| Lyra [MULTI-TENANT-EVALUATION.md](../architecture/MULTI-TENANT-EVALUATION.md) | Internal | Existing evaluation with similar conclusion |
| Lyra [MULTI-TENANT-DESIGN.md](../architecture/MULTI-TENANT-DESIGN.md) | Internal | Existing design spec |

# Brainstorm: AgentsMesh Multi-Tenancy Evaluation (§5.2)

## Sources Reviewed

### AgentsMesh (§3.8)
- Multi-tenant agent coordination platform
- Tenant isolation: per-tenant agent pools, separate context
- Shared infrastructure with isolated execution
- Message bus for cross-agent communication within tenant
- Authentication + authorization per tenant

### Comparable Patterns
- **Kilo Code Cloud**: Multi-user agent service with per-user isolation
- **Goose Recipes**: Shared workflows but single-user
- **DeerFlow 2.0**: SuperAgent harness, single-tenant by default
- **OpenHands**: Hosted version is multi-tenant

### Lyra's Current Architecture (§0 Reference)
- MIT-licensed, terminal-based, multi-agent
- Targets individual developers (single-tenant by design)
- No current multi-user concerns

### Security/Safety Research (§3.16)
- LlamaFirewall + CaMeL: Important for multi-tenant safety
- Progent: Per-tenant tool capability gates
- "Your Agent May Misevolve": Cross-tenant contamination risks

### Permissions (§4.12)
- Already-designed permission system for single-user
- Would need extension for multi-tenant scoping

---

## Cross-Source Breakthrough Ideas

### Idea 1: **Optional Multi-Tenant Profile System (No Forced Tenancy)**

**Sources Combined**:
- AgentsMesh tenant isolation
- Permissions system (§4.12)
- Memory architecture (§4.2 — namespaced memory)
- Sessions (§4.11 — session = tenant context)

**Mechanism**:
Lyra remains **single-user by default** (preserving its terminal-native nature) but supports **opt-in tenant profiles** for shared environments (teams, classrooms, agencies):

```yaml
# ~/.lyra/profiles.yaml
profiles:
  - name: personal
    memory_namespace: personal
    tools_allowed: [all]
    cost_budget: unlimited
    default: true

  - name: client-acme
    memory_namespace: client-acme
    tools_allowed: [Read, Write, Edit, Bash:safe]
    cost_budget: $50/month
    skills_allowed: [eng-*]
    network_restricted: ["api.acme.com", "github.com/acme"]

  - name: client-beta
    memory_namespace: client-beta
    tools_allowed: [Read, Write, Edit]
    cost_budget: $20/month
    skills_allowed: [research-*, writing-*]
```

**Switching**:
- `lyra --profile client-acme` for one session
- `lyra profile switch client-acme` to persist
- Status line shows active profile
- Tools/memory/cost auto-scope to profile

**Key Insight**: Don't force multi-tenancy on solo developers. Make it **opt-in capability** for users who actually need it.

**Why It Beats Individual Sources**:
- AgentsMesh: Forces multi-tenant complexity on everyone
- Goose: No tenant concept at all
- DeerFlow: Single-tenant only
- **Fusion**: Profile-based optional tenancy that scales from solo dev → team → agency without changing core architecture

**Impact × Effort**: 4×3 = HIGH

**Failure Modes**:
- Profile isolation could leak via shared filesystem
- Cost tracking complexity
- User confusion about "which profile am I in?"

---

### Idea 2: **Federated Memory Across Tenant Profiles**

**Sources Combined**:
- AgentsMesh per-tenant isolation
- Memory architecture (§4.2 — namespaced)
- Mem0 cross-session memory
- Zep/Graphiti temporal knowledge graphs

**Mechanism**:
Each tenant profile has **isolated primary memory** but agents can **opt-in publish** specific learnings to a **federated knowledge layer** (with redaction):

```
Profile: client-acme
├── Private memory (isolated)
│   ├── client_credentials, code_internals, ...
└── Published learnings (opt-in)
    ├── "API rate limits in REST design" (generic)
    ├── "Python async patterns" (generic)
    └── (filtered: no client-specific info)

Federated layer (cross-profile):
├── Pattern: "API rate limits in REST design"
│   ├── Sources: [client-acme, personal, client-beta]
│   └── Confidence: 0.95 (3 confirmations)
```

**Federated Layer Rules**:
- Auto-redact: secrets, file paths, specific names → generic patterns
- LLM gate: "Is this learning safe to share across tenants?"
- User approval for first publish (then auto-publish similar)
- Cross-tenant queries hit federated layer first, then private

**Use Case**: Developer at agency learns React patterns at Client A; those patterns benefit Client B's project without leaking client-specific info.

**Why It Beats Individual Sources**:
- AgentsMesh: Hard isolation, no cross-learning
- Mem0: Single-tenant cross-session, not cross-tenant
- Graphiti: Single-graph, not federated
- **Fusion**: Privacy-preserving knowledge sharing across tenants — unique capability

**Impact × Effort**: 5×5 = BREAKTHROUGH (high impact, high effort due to safety concerns)

**Failure Modes**:
- Auto-redaction might miss subtle leaks
- LLM-gated publishing could be wrong
- Federated layer could become "noise" if quality control fails
- Liability if leaks happen

---

### Idea 3: **Tenant Cost Attribution with Real-Time Budget Enforcement**

**Sources Combined**:
- AgentsMesh per-tenant resource limits
- Model router (§4.5 — cost-aware routing)
- Reliability/observability (§4.16 — tracing)
- Permissions (§4.12 — capability gates)

**Mechanism**:
**Per-tenant cost tracking + budget enforcement** with real-time controls:

```yaml
profile: client-acme
budgets:
  monthly:
    limit: $50
    warn_at: 0.8  # warn at $40
    soft_block_at: 0.95  # require approval at $47.50
    hard_block_at: 1.0  # halt at $50

  daily:
    limit: $5
    cooldown_on_exceed: 1h  # block for 1 hour after hitting daily cap

  per_request:
    max_cost: $0.50  # require approval if single request exceeds

routing:
  prefer: cheap_models  # haiku before sonnet before opus
  escalate_only_if: ["explicit_user_request", "task_failed_on_cheap"]
```

**Real-Time Tracking**:
- Statusline shows: `[client-acme] $12.45/$50 monthly`
- Pre-flight estimate before expensive operations: "Estimated $0.80, approve?"
- Audit log of all spend with attribution
- Auto-summary at month end

**Why It Beats Individual Sources**:
- AgentsMesh: Limits but no real-time UX
- Model router: Cost-aware routing but per-session, not per-tenant
- Observability: Logging only, not enforcement
- **Fusion**: Tenant-scoped cost with proactive enforcement and clear UX

**Impact × Effort**: 4×3 = HIGH

**Failure Modes**:
- Cost prediction is unreliable (token counting)
- Budget enforcement could block urgent work
- Cross-tenant cost shifting if profile switching is gamed

---

## Recommendation: Should Lyra Adopt Multi-Tenancy?

### Verdict: **CONDITIONAL ADOPTION — Profile System Only**

**Adopt** (Idea 1: Profile System):
- ✅ Low complexity if implemented as profile switching
- ✅ Real demand from agencies, teams, classrooms
- ✅ Aligns with permission system (§4.12) already planned
- ✅ Preserves solo-dev simplicity (opt-in)

**Defer** (Ideas 2 & 3 for later):
- ⏸️ Federated memory: Too risky for v1 (privacy/safety concerns)
- ⏸️ Real-time budget enforcement: Useful but can layer on top of profiles later

**Reject** (Full AgentsMesh model):
- ❌ Server-deployment model contradicts Lyra's terminal-native identity
- ❌ Adds operational complexity (auth servers, databases, mTLS)
- ❌ Solo developers (Lyra's primary users) don't need it
- ❌ Multi-tenant SaaS is a different product

### Implementation Path
1. **Phase 1 (Run 4)**: Profile system as opt-in (no breaking changes for solo users)
2. **Phase 2**: Budget tracking per profile
3. **Phase 3**: Real-time enforcement and statusline integration
4. **Phase 4 (research only)**: Federated memory feasibility study with safety team

---

## Parked Ideas (Future Runs)

### Idea 4: **Tenant-Aware Skill Distribution**
Skills could be tenant-scoped: "this skill only available for client-acme profile". Could enable client-specific skill libraries.

### Idea 5: **Cross-Tenant Pair Programming**
Two users on different profiles could share a session for collaboration. Complex permissions but enables team workflows.

### Idea 6: **Tenant Audit & Compliance**
Generate audit logs per tenant for compliance (SOC2, HIPAA-like requirements for sensitive client work).

---

## Promoted to Plan (B) Breakthrough Tier

**Primary**: Idea 1 (Optional Profile System) — Pragmatic, preserves Lyra's identity, enables team use cases without complexity

**Secondary**: Idea 3 (Tenant Cost Attribution) — Critical for agency/team adoption, builds on profile foundation

**Parked**: Idea 2 (Federated Memory) — Too risky for v1, revisit after safety system matures

The breakthrough is **NOT** adopting full multi-tenancy — it's recognizing Lyra should remain primarily single-user with optional tenant capabilities, unlike platforms that force everyone into a multi-tenant model.

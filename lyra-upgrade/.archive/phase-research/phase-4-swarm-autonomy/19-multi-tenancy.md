# §5.2 Implementation Plan: Multi-Tenancy Evaluation

**Status**: PLAN  
**Priority**: MED×MED (P3)  
**Effort**: 2 weeks (evaluation + recommendation)  
**Dependencies**: §4.13 (Swarm Fleet), §5.1 (Terminal System)

---

## 1. Overview

Evaluate AgentsMesh architecture for Lyra's multi-tenancy requirements and provide recommendation on:
- **Adopt**: Use AgentsMesh as-is or fork
- **Adapt**: Extract patterns and rebuild for Lyra
- **Avoid**: Build custom solution from scratch

**Evaluation Criteria**:
1. **Architecture fit**: Does it align with Lyra's design?
2. **License compatibility**: BSL-1.1 until 2030, then GPL-2.0
3. **Feature completeness**: Does it meet Lyra's requirements?
4. **Integration complexity**: How hard to integrate?
5. **Maintenance burden**: Can we maintain it long-term?
6. **Performance**: Does it meet our targets?
7. **Security**: Does it provide adequate isolation?

---

## 2. AgentsMesh Architecture Analysis

### 2.1 Core Components

**Backend** (Go + Gin + GORM):
- Authentication and authorization
- Organization/team/user management
- Pod lifecycle management
- Task management (kanban)
- Git provider integration (GitLab, GitHub, Gitee)

**Web** (Next.js):
- Dashboard and web terminal
- Kanban board
- Topology visualization
- Real-time updates

**Relay** (WebSocket cluster):
- Terminal I/O streaming
- Low-latency pub/sub
- Horizontal scaling

**Runner** (Go daemon):
- Self-hosted on user infrastructure
- Connects via gRPC+mTLS and WebSocket
- Runs agents in isolated PTY sandboxes
- Git worktree isolation per pod

**Infrastructure**:
- PostgreSQL (relational data)
- Redis (caching, pub/sub)
- MinIO (S3-compatible storage)

### 2.2 Multi-Tenancy Model

**Hierarchy**: Organization > Team > User

**Isolation Mechanisms**:
1. **Row-level security**: Database queries filtered by org/team/user
2. **Runner isolation**: Self-hosted runners on user infrastructure
3. **PTY sandboxes**: Each agent runs in isolated PTY
4. **Git worktrees**: Each pod gets isolated worktree
5. **mTLS**: Secure runner-backend communication
6. **BYOK**: Users provide their own AI API keys

**Security**:
- JWT for web authentication
- mTLS for runner-backend connections
- API keys never leave user infrastructure
- Code never leaves user environment

### 2.3 Agent Coordination

**AgentPod System**:
- Remote AI workstations with web terminal access
- Multiple concurrent pods per user
- Real-time streaming of agent output

**Collaboration Mechanisms**:
- Channels for agent communication
- Pod bindings to coordinate multi-agent workflows
- Real-time topology visualization

**Task Integration**:
- Kanban board with ticket-pod binding
- Progress tracking across agent activities
- MR/PR integration with Git providers

### 2.4 Supported Agents

- Claude Code
- Codex CLI
- Gemini CLI
- Aider
- OpenCode
- Any custom terminal-based agent

---

## 3. Evaluation Matrix

### 3.1 Architecture Fit

| Aspect | AgentsMesh | Lyra Requirements | Fit Score |
|--------|------------|-------------------|-----------|
| Control/data plane separation | ✅ gRPC + WebSocket | ✅ Required | 10/10 |
| Multi-tenancy hierarchy | ✅ Org > Team > User | ✅ Required | 10/10 |
| Runner isolation | ✅ Self-hosted runners | ✅ Required | 10/10 |
| Channel communication | ✅ Built-in | ✅ Required (§4.13) | 10/10 |
| Terminal multiplexing | ✅ PTY sandboxes | ✅ Required (§5.1) | 9/10 |
| Agent coordination | ✅ Pod bindings | ✅ Required (§4.13) | 8/10 |
| Task management | ✅ Kanban board | ⚠️ Nice-to-have | 7/10 |
| Git integration | ✅ GitLab/GitHub/Gitee | ✅ Required | 9/10 |
| Web UI | ✅ Next.js dashboard | ⚠️ Nice-to-have | 7/10 |
| **Overall Architecture Fit** | | | **8.9/10** |

**Analysis**:
- Excellent fit for core multi-tenancy requirements
- Control/data plane separation aligns with Lyra's design
- Runner isolation model matches Lyra's security requirements
- Channel communication compatible with §4.13
- Task management and Web UI are bonus features

### 3.2 License Compatibility

**AgentsMesh License**: BSL-1.1 until 2030-02-28, then GPL-2.0-or-later

**Implications**:
- ❌ **Non-production use allowed**: Free for development/testing
- ❌ **Production requires commercial license**: Until 2030-02-28
- ✅ **Becomes GPL-2.0 in 2030**: Free for all use after change date
- ⚠️ **GPL-2.0 copyleft**: Derivative works must be GPL-2.0

**Lyra License**: MIT (permissive)

**Compatibility Analysis**:
- ❌ **BSL-1.1 incompatible with MIT**: Cannot distribute together before 2030
- ❌ **GPL-2.0 incompatible with MIT**: Cannot distribute together after 2030
- ✅ **Can use as separate service**: Lyra calls AgentsMesh API (no distribution)
- ⚠️ **Fork would inherit license**: Any fork must be BSL-1.1 → GPL-2.0

**License Fit Score**: **3/10** (major blocker for distribution)

### 3.3 Feature Completeness

| Feature | AgentsMesh | Lyra Requirements | Status |
|---------|------------|-------------------|--------|
| Persistent sessions | ✅ | ✅ Required | ✅ |
| Multi-agent coordination | ✅ | ✅ Required | ✅ |
| Channel communication | ✅ | ✅ Required | ✅ |
| Terminal automation | ⚠️ Basic | ✅ Advanced (§5.1) | ⚠️ |
| Swarm coordination | ❌ | ✅ Required (§4.13) | ❌ |
| Autonomy mode | ❌ | ✅ Required (§4.14) | ❌ |
| Deep research | ❌ | ✅ Required (§4.15) | ❌ |
| Shared context store | ❌ | ✅ Required (§4.13) | ❌ |
| Adversarial validation | ❌ | ✅ Required (§4.15) | ❌ |
| Self-organizing teams | ❌ | ✅ Required (§4.15) | ❌ |
| **Feature Completeness** | | | **40%** |

**Analysis**:
- Provides solid foundation for multi-tenancy and basic coordination
- Missing advanced features required by Lyra (swarm, autonomy, deep research)
- Would require significant extensions to meet Lyra's requirements

**Feature Fit Score**: **4/10** (foundation only, major gaps)

### 3.4 Integration Complexity

**Integration Approaches**:

**Option A: Use as External Service**
- Deploy AgentsMesh separately
- Lyra calls AgentsMesh API for pod management
- Complexity: **Low** (API integration only)
- Coupling: **Loose** (separate services)
- License: **Compatible** (no distribution)

**Option B: Fork and Extend**
- Fork AgentsMesh repository
- Add Lyra-specific features (swarm, autonomy, deep research)
- Complexity: **High** (Go + Next.js + Lyra TypeScript)
- Coupling: **Tight** (maintain fork)
- License: **Incompatible** (BSL-1.1 → GPL-2.0)

**Option C: Extract Patterns and Rebuild**
- Study AgentsMesh architecture
- Rebuild in TypeScript for Lyra
- Implement only needed features
- Complexity: **Medium** (TypeScript only)
- Coupling: **None** (independent implementation)
- License: **Compatible** (MIT)

**Integration Complexity Score**:
- Option A: **8/10** (easy integration)
- Option B: **3/10** (high complexity + license issues)
- Option C: **6/10** (medium complexity, clean slate)

### 3.5 Maintenance Burden

**Option A: External Service**
- ✅ AgentsMesh team maintains core
- ✅ Lyra only maintains API integration
- ❌ Dependent on AgentsMesh release cycle
- ❌ Breaking changes require Lyra updates
- **Maintenance Score**: **7/10**

**Option B: Fork**
- ❌ Lyra maintains Go + Next.js + TypeScript
- ❌ Must merge upstream changes
- ❌ Divergence increases over time
- ❌ Multiple language ecosystems
- **Maintenance Score**: **2/10**

**Option C: Rebuild**
- ✅ Lyra controls entire codebase
- ✅ Single language ecosystem (TypeScript)
- ✅ No upstream dependencies
- ⚠️ Full maintenance responsibility
- **Maintenance Score**: **8/10**

### 3.6 Performance

**AgentsMesh Performance** (based on architecture):
- WebSocket relay cluster: Low-latency streaming
- gRPC+mTLS: Efficient control plane
- PostgreSQL: Proven scalability
- Redis: Fast caching and pub/sub
- Horizontal scaling: Relay cluster scales independently

**Estimated Performance**:
- Pod creation: <2 seconds
- Terminal I/O latency: <50ms
- Channel message latency: <100ms
- Concurrent pods per runner: 10-50
- Concurrent users per backend: 1000+

**Performance Score**: **8/10** (good, but not benchmarked)

### 3.7 Security

**AgentsMesh Security**:
- ✅ mTLS for runner-backend communication
- ✅ JWT for web authentication
- ✅ Row-level security in database
- ✅ PTY sandboxes for agent isolation
- ✅ Git worktree isolation
- ✅ BYOK model (keys never leave user infrastructure)
- ✅ Self-hosted runners (code never leaves user environment)
- ⚠️ No mention of input validation or adversarial validation
- ⚠️ No mention of rate limiting or DDoS protection

**Security Score**: **7/10** (good foundation, missing advanced features)

---

## 4. Overall Evaluation Summary

| Criterion | Score | Weight | Weighted Score |
|-----------|-------|--------|----------------|
| Architecture Fit | 8.9/10 | 25% | 2.23 |
| License Compatibility | 3/10 | 20% | 0.60 |
| Feature Completeness | 4/10 | 20% | 0.80 |
| Integration Complexity | 6/10 | 15% | 0.90 |
| Maintenance Burden | 8/10 | 10% | 0.80 |
| Performance | 8/10 | 5% | 0.40 |
| Security | 7/10 | 5% | 0.35 |
| **Total** | | | **6.08/10** |

---

## 5. Recommendation

### 5.1 Recommended Approach: **Option C - Extract Patterns and Rebuild**

**Rationale**:
1. **License compatibility**: MIT license allows distribution with Lyra
2. **Feature control**: Can implement exactly what Lyra needs (swarm, autonomy, deep research)
3. **Single ecosystem**: TypeScript only, no Go or Next.js
4. **Maintenance**: Full control, no upstream dependencies
5. **Integration**: Native integration with Lyra's architecture

**Trade-offs**:
- ❌ More upfront development effort (2-3 months)
- ❌ No existing Web UI (can build later if needed)
- ❌ No existing task management (can build later if needed)
- ✅ Clean slate, optimized for Lyra's use case
- ✅ No license restrictions
- ✅ Single language ecosystem

### 5.2 What to Extract from AgentsMesh

**Architecture Patterns** (study and adapt):
1. **Control/data plane separation**: gRPC for control, WebSocket for data
2. **Runner isolation model**: Self-hosted runners on user infrastructure
3. **Multi-tenancy hierarchy**: Organization > Team > User
4. **PTY sandboxes**: Isolated agent execution
5. **Git worktree isolation**: Per-pod worktrees
6. **Channel communication**: Agent-to-agent messaging
7. **mTLS security**: Secure runner-backend communication

**What NOT to Extract**:
- Web UI (Next.js) — build later if needed
- Task management (kanban) — build later if needed
- Specific Git provider integrations — use generic Git API
- Relay cluster — start with single relay, scale later

### 5.3 Implementation Plan

**Phase 1: Core Multi-Tenancy** (3 weeks)
- Organization/team/user hierarchy
- Row-level security in database
- Authentication and authorization
- Runner registration and lifecycle

**Phase 2: Control Plane** (2 weeks)
- gRPC server for control commands
- Pod lifecycle management
- Runner health monitoring
- mTLS security

**Phase 3: Data Plane** (2 weeks)
- WebSocket relay for terminal I/O
- Channel communication system
- Real-time event streaming
- Message persistence

**Phase 4: Runner Implementation** (3 weeks)
- Self-hosted runner daemon
- PTY sandbox management
- Git worktree isolation
- Agent spawning and monitoring

**Phase 5: Integration** (2 weeks)
- Integrate with §4.13 (Swarm Fleet)
- Integrate with §5.1 (Terminal System)
- Add swarm coordination features
- Add autonomy mode support

**Total Effort**: 12 weeks (3 months)

### 5.4 Alternative: Option A (External Service)

**When to Consider**:
- Need multi-tenancy quickly (weeks, not months)
- Don't need advanced features (swarm, autonomy, deep research) immediately
- Willing to pay for commercial license (production use)
- Can tolerate dependency on external service

**Implementation**:
1. Deploy AgentsMesh (hosted or self-hosted)
2. Integrate Lyra with AgentsMesh API
3. Use AgentsMesh for basic pod management
4. Build advanced features (swarm, autonomy, deep research) in Lyra
5. Migrate to Option C later if needed

**Effort**: 2-3 weeks (API integration only)

---

## 6. Detailed Comparison: Option A vs Option C

| Aspect | Option A (External Service) | Option C (Rebuild) |
|--------|----------------------------|-------------------|
| **Time to MVP** | 2-3 weeks | 12 weeks |
| **License** | BSL-1.1 (commercial required) | MIT (permissive) |
| **Distribution** | Cannot distribute together | Can distribute together |
| **Feature Control** | Limited to AgentsMesh features | Full control |
| **Maintenance** | Dependent on AgentsMesh | Full control |
| **Integration** | API calls (loose coupling) | Native (tight integration) |
| **Language** | Go + Next.js + TypeScript | TypeScript only |
| **Customization** | Limited | Unlimited |
| **Scaling** | AgentsMesh handles | Lyra handles |
| **Cost** | Commercial license fee | Development time |
| **Risk** | Vendor lock-in | Development risk |

---

## 7. Pros and Cons

### 7.1 Option A: External Service

**Pros**:
- ✅ Fast time to market (2-3 weeks)
- ✅ Proven architecture and implementation
- ✅ AgentsMesh team maintains core
- ✅ Web UI and task management included
- ✅ Horizontal scaling built-in

**Cons**:
- ❌ Commercial license required for production
- ❌ Cannot distribute with Lyra
- ❌ Dependent on AgentsMesh release cycle
- ❌ Limited customization
- ❌ Vendor lock-in
- ❌ Missing advanced features (swarm, autonomy, deep research)
- ❌ Multiple language ecosystems (Go + Next.js + TypeScript)

### 7.2 Option C: Rebuild

**Pros**:
- ✅ MIT license (permissive, can distribute)
- ✅ Full feature control (swarm, autonomy, deep research)
- ✅ Single language ecosystem (TypeScript)
- ✅ Native integration with Lyra
- ✅ No vendor lock-in
- ✅ Optimized for Lyra's use case
- ✅ Full maintenance control

**Cons**:
- ❌ Longer time to market (12 weeks)
- ❌ More upfront development effort
- ❌ No existing Web UI (build later if needed)
- ❌ No existing task management (build later if needed)
- ❌ Full maintenance responsibility

---

## 8. Migration Path (Option A → Option C)

If starting with Option A and migrating to Option C later:

**Phase 1: Use AgentsMesh** (Months 1-6)
- Deploy AgentsMesh for basic multi-tenancy
- Integrate Lyra with AgentsMesh API
- Build advanced features (swarm, autonomy, deep research) in Lyra
- Gather requirements and learnings

**Phase 2: Build Lyra Multi-Tenancy** (Months 7-9)
- Implement Option C (rebuild) based on learnings
- Run both systems in parallel
- Migrate users gradually

**Phase 3: Deprecate AgentsMesh** (Month 10+)
- Complete migration to Lyra multi-tenancy
- Deprecate AgentsMesh integration
- Remove AgentsMesh dependency

**Total Timeline**: 10+ months

---

## 9. Final Recommendation

**Recommended**: **Option C - Extract Patterns and Rebuild**

**Justification**:
1. **License compatibility**: MIT allows distribution with Lyra
2. **Long-term control**: Full control over features and maintenance
3. **Feature completeness**: Can implement all required features (swarm, autonomy, deep research)
4. **Single ecosystem**: TypeScript only, easier maintenance
5. **Native integration**: Tight integration with Lyra's architecture
6. **No vendor lock-in**: Independent implementation

**Timeline**: 12 weeks (3 months)

**Alternative**: Start with **Option A** if need multi-tenancy urgently (2-3 weeks), then migrate to **Option C** later (10+ months total).

---

## 10. Implementation Roadmap (Option C)

### Week 1-3: Core Multi-Tenancy
- [ ] Organization/team/user hierarchy
- [ ] Row-level security in PostgreSQL
- [ ] JWT authentication
- [ ] Runner registration API

### Week 4-5: Control Plane
- [ ] gRPC server implementation
- [ ] Pod lifecycle management
- [ ] Runner health monitoring
- [ ] mTLS security

### Week 6-7: Data Plane
- [ ] WebSocket relay server
- [ ] Channel communication system
- [ ] Real-time event streaming
- [ ] Message persistence (Redis)

### Week 8-10: Runner Implementation
- [ ] Self-hosted runner daemon (TypeScript)
- [ ] PTY sandbox management (node-pty)
- [ ] Git worktree isolation
- [ ] Agent spawning and monitoring

### Week 11-12: Integration
- [ ] Integrate with §4.13 (Swarm Fleet)
- [ ] Integrate with §5.1 (Terminal System)
- [ ] Add swarm coordination features
- [ ] Add autonomy mode support
- [ ] Documentation and examples

---

## 11. Success Criteria

- [ ] Multi-tenancy hierarchy (org/team/user) implemented
- [ ] Runner isolation with PTY sandboxes working
- [ ] Control plane (gRPC) and data plane (WebSocket) operational
- [ ] Channel communication integrated with §4.13
- [ ] Terminal system integrated with §5.1
- [ ] mTLS security for runner-backend communication
- [ ] Git worktree isolation per pod
- [ ] Performance targets met (pod creation <2s, I/O latency <50ms)
- [ ] Integration tests pass
- [ ] Documentation complete

---

## 12. References

- AgentsMesh: Multi-tenancy architecture, control/data plane separation, runner isolation
- §4.13: Swarm Fleet with channel-based communication
- §5.1: Terminal system (rmux rebuild)
- §4.14: Full autonomy mode
- §4.15: Deep research system

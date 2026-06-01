# Brainstorm: Context Optimization & Auto-Compaction (§4.3)

**Workstream**: §4.3 Context Optimization & Auto-Compaction  
**Date**: 2026-05-31  
**Status**: Breakthrough ideas generated

---

## Sources Gathered

### Context Compression
1. **Norm-Guided KV-Cache Eviction** — Gradient-free compression scoring tokens by ℓ2-norm
2. **R-KVHash** — SimHash/LSH-based KV-cache compression, ~2× decoding throughput
3. **ACON** — Adaptive agent context compression, 26–54% memory cut
4. **Anthropic Context Engineering** — Compaction + memory tool patterns
5. **IterResearch** — Report-as-memory, periodic insight synthesis to avoid context suffocation

### Memory & Retrieval
6. **MemSearcher** — Compact question-relevant memory across turns
7. **Agentic Memory Should Localize Compression** (KAIST) — Compress within modular units
8. **Lyra's memory architecture** (§4.2) — Cross-session recall, episodic/semantic layers

---

## Novel Breakthrough Ideas (≥3 Required)

### Idea 1: **Hierarchical Context with Semantic Compression**

**Sources Combined**:
- ACON adaptive compression (26–54% reduction)
- IterResearch report-as-memory + insight synthesis
- Lyra's memory (§4.2 episodic/semantic layers)
- KAIST localized compression

**Mechanism**:
Organize context into **3 tiers** with different compression strategies:

**Tier 1: Active Context (No Compression)**
- Current task details
- Recent 5-10 messages
- Active file contents
- ~10-20% of context window

**Tier 2: Working Memory (Semantic Compression)**
- Task history from current session
- Compress via insight synthesis (IterResearch)
- Extract key decisions, blockers, outcomes
- ~30-40% of context window

**Tier 3: Long-Term Memory (Aggressive Compression)**
- Cross-session knowledge
- Compress via semantic embeddings + retrieval
- Only load relevant memories on-demand
- ~50-70% of context window (or external storage)

**Compression example**:
```
Original (Tier 1 → Tier 2 transition):
[500 lines of code review discussion]
→ Compressed: "Code review identified 3 critical issues: auth bypass, SQL injection, missing tests. All fixed. Approved."

Original (Tier 2 → Tier 3 transition):
[10 task summaries from session]
→ Compressed: "Session focused on authentication system. Key decisions: JWT tokens, bcrypt hashing, Redis sessions. Blockers: None. Status: Complete."
```

**Localized compression** (KAIST):
- Compress within logical units (per-task, per-file, per-conversation)
- Prevents compression artifacts from bleeding across contexts

**Why It Beats Individual Sources**:
- ACON alone: Single-tier compression
- IterResearch alone: Report-as-memory but no hierarchical tiers
- **Fusion**: 3-tier hierarchy, semantic compression, localized to prevent interference

**Expected Impact**: 60-70% context reduction, 100% critical info retention

**Rough Effort**: HIGH (10-12 weeks) — 3-tier system + semantic compression + localized compression

**Failure Modes**:
- Compression loses critical details → incorrect decisions
- Tier boundaries unclear → wrong compression level
- Localization too aggressive → can't connect across contexts

---

### Idea 2: **Adaptive Compression with Importance Scoring**

**Sources Combined**:
- Norm-Guided KV-Cache Eviction (ℓ2-norm scoring)
- R-KVHash (SimHash/LSH redundancy detection)
- MemSearcher (question-relevant memory)
- Lyra's model router (§4.5 cost optimization)

**Mechanism**:
Compress based on **importance scores**, not just recency:

**Importance factors**:
1. **Recency**: Recent messages more important (exponential decay)
2. **Relevance**: Similarity to current task (cosine similarity)
3. **Uniqueness**: Novel information more important (SimHash)
4. **User-flagged**: User explicitly marked as important
5. **Decision points**: Key decisions, blockers, outcomes

**Scoring formula**:
```
importance = 0.3 * recency + 0.3 * relevance + 0.2 * uniqueness + 0.1 * user_flagged + 0.1 * is_decision
```

**Compression strategy**:
- High importance (>0.8): Keep verbatim
- Medium importance (0.5-0.8): Semantic compression
- Low importance (<0.5): Aggressive compression or discard

**Example**:
```
Message 1: "Let's use JWT for auth" (decision point)
→ Importance: 0.9 (high) → Keep verbatim

Message 2: "I agree" (low information)
→ Importance: 0.2 (low) → Discard

Message 3: "Here's the JWT implementation [500 lines]"
→ Importance: 0.7 (medium) → Compress to "JWT implementation added with HS256 signing"
```

**Adaptive threshold**:
- If context window filling up → lower threshold (compress more)
- If context window has space → higher threshold (compress less)

**Why It Beats Individual Sources**:
- Norm-Guided alone: KV-cache compression, not semantic
- R-KVHash alone: Redundancy detection but no importance scoring
- **Fusion**: Multi-factor importance, adaptive threshold, preserves critical info

**Expected Impact**: 50-60% context reduction, 95%+ critical info retention

**Rough Effort**: MEDIUM-HIGH (8-10 weeks) — importance scoring + adaptive threshold + compression

**Failure Modes**:
- Importance scoring inaccurate → compresses critical info
- Threshold too aggressive → loses too much
- Threshold too conservative → doesn't compress enough

---

### Idea 3: **Incremental Compression with Rollback**

**Sources Combined**:
- Anthropic Context Engineering (compaction patterns)
- Lyra's memory (§4.2 trajectory logging)
- Lyra's verification (§4.16 rollback on failure)
- IterResearch insight synthesis

**Mechanism**:
Compress **incrementally** with ability to rollback:

**Compression checkpoints**:
1. **Every N messages**: Create compression checkpoint
2. **Compress**: Apply semantic compression to old messages
3. **Verify**: Check if agent can still answer questions about compressed content
4. **Rollback**: If verification fails, rollback to previous checkpoint

**Verification example**:
```
Before compression:
[Detailed discussion about auth implementation]

After compression:
"Auth implemented with JWT + bcrypt"

Verification questions:
Q: "What hashing algorithm did we use?"
A: "bcrypt" ✓

Q: "What was the token expiry time?"
A: "I don't have that information" ✗

→ Verification failed → Rollback compression
→ Retry with less aggressive compression
```

**Incremental compression**:
- Compress oldest messages first
- Gradually increase compression ratio
- Stop when verification starts failing

**Why It Beats Individual Sources**:
- Anthropic alone: Compaction patterns but no verification
- Lyra verification alone: Rollback but not for compression
- **Fusion**: Safe compression, verifies before committing, rollback on failure

**Expected Impact**: 40-50% context reduction, 100% verified info retention

**Rough Effort**: MEDIUM-HIGH (8-10 weeks) — incremental compression + verification + rollback

**Failure Modes**:
- Verification questions incomplete → misses lost info
- Rollback too frequent → compression too slow
- Checkpoints too sparse → loses too much on rollback

---

### Idea 4: **Context Streaming with External Storage**

**Sources Combined**:
- Lyra's memory (§4.2 external storage)
- MemSearcher compact memory
- KAIST localized compression
- Anthropic Context Engineering

**Mechanism**:
Stream old context to **external storage**, load on-demand:

**Storage tiers**:
1. **Hot storage** (in-context): Current task, recent messages
2. **Warm storage** (compressed in-context): Recent session history
3. **Cold storage** (external): Old sessions, archived tasks

**Streaming protocol**:
- When context >80% full → stream oldest 20% to cold storage
- When agent needs old info → retrieve from cold storage
- Retrieval via semantic search (embeddings)

**Example flow**:
```
Context window: 200K tokens
Current usage: 170K tokens (85% full)

→ Stream oldest 40K tokens to cold storage
→ Compress to 10K token summary in warm storage
→ Current usage: 140K tokens (70% full)

Later: Agent asks "What did we decide about auth?"
→ Semantic search in cold storage
→ Retrieve relevant 5K tokens
→ Load into context
```

**Why It Beats Individual Sources**:
- Lyra memory alone: External storage but not streaming
- MemSearcher alone: Compact memory but no external storage
- **Fusion**: Unlimited context via streaming, on-demand retrieval

**Expected Impact**: Unlimited effective context, 90% reduction in active context

**Rough Effort**: VERY HIGH (12-14 weeks) — streaming + external storage + retrieval

**Failure Modes**:
- Retrieval too slow → latency spikes
- Semantic search misses relevant info → incomplete context
- External storage fails → data loss

---

## Parked Ideas (For Future Runs)

1. **Context visualization**: Show context usage, compression ratio, tier distribution
2. **Context templates**: Pre-defined compression strategies for common tasks
3. **Context metrics**: Track compression ratio, info retention, retrieval accuracy
4. **Context replay**: Reconstruct full context from compressed version
5. **Context sharing**: Share compressed context across agents

---

## Promoted to Plan (B) Breakthrough Tier

**Selected**: Idea 1 (Hierarchical Context) + Idea 2 (Adaptive Compression)

**Rationale**:
- Idea 1: Highest reduction (60-70%), 3-tier hierarchy, localized compression
- Idea 2: Highest retention (95%+), multi-factor importance, adaptive threshold
- Idea 3: Good but overlaps with verification system (§4.16)
- Idea 4: Interesting but very high complexity, defer to v2

---

**END OF BRAINSTORM**

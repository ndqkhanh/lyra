# Lyra Ultra — Comprehensive Test Plan

> **Date:** 2026-05-30 | **Status:** PLAN
> **Covers:** All deep research, auto research, scientist research, AI-research-research, and workflow flows

---

## 1. Memory System Tests

### 1.1 Temporal Knowledge Graph
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| TKG-001 | Insert entity with temporal edge | Edge stored with valid_from/valid_until | Future dates, null valid_until | Edge queryable by time range |
| TKG-002 | Query "what did we know at time T" | Returns facts valid at T, not later revisions | T outside any validity range → empty result | Correct temporal filtering |
| TKG-003 | Update fact (newer version) | Old edge marked valid_until, new edge created | Concurrent updates → version conflict | No data loss; version chain intact |
| TKG-004 | Cross-session temporal recall | Facts from prior session queryable | Session with no prior data → empty result | Prior session facts returned correctly |
| TKG-005 | Bi-temporal edge conflict | Two contradictory edges, different valid_from | 3+ conflicting edges → confidence-weighted | Highest-confidence edge returned |

### 1.2 RecMem Subconscious Monitor
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| RCM-001 | Single occurrence of concept | Skip LLM extraction | Concept at embedding boundary | No LLM call made (<1% false negative) |
| RCM-002 | 3+ recurrences of concept | Trigger LLM extraction to semantic memory | Recurrence across different sessions | Concept extracted to T2 |
| RCM-003 | Noise/spam recurrence | Skip extraction (low semantic weight) | High-frequency low-quality tokens | Token savings ≥80% vs always-extract |
| RCM-004 | Cross-agent recurrence | Concept appears across different agents | Multi-agent, same concept, different phrasing | Shared concept detected despite phrasing |

### 1.3 RRF Hybrid Search
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| RRF-001 | Exact keyword match | BM25 rank 1, vector rank >1 | Keyword not in vector vocabulary | Recall@5 ≥96% |
| RRF-002 | Semantic similarity only (no keywords) | Vector rank 1, BM25 rank >1 | Cross-language query | Correct semantic match returned |
| RRF-003 | Zero API calls for retrieval | No LLM API cost in retrieval path | Large corpus (100K+ memories) | Retrieval latency <100ms |
| RRF-004 | Combined BM25+vector fusion | Fusion score >max(individual) | α parameter sweep 0.0-1.0 | Fusion outperforms either alone |

---

## 2. Research Engine Tests

### 2.1 AutoScientists Research Loop
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| ASC-001 | Hypothesis generation from data | Falsifiable hypothesis with prediction | Empty data → no hypothesis | Hypothesis includes prediction + falsification criteria |
| ASC-002 | Critique-before-spend gate | Proposal requires ≥1 peer comment | No peers available → auto-timeout 15min | Rejected proposals logged with reason |
| ASC-003 | Dead-end registry | 3+ DISCARDs, 0 KEEPs → marked dead | Cross-team visibility | Other teams don't explore dead axis |
| ASC-004 | Noise-aware champion validation | Multi-seed gate (2-sigma margin) | Single seed, high variance | No phantom champion promotion |
| ASC-005 | Post-KEEP inductive reasoning | After breakthrough, analyze mechanism | Multiple breakthroughs simultaneously | ≥1 follow-up from different angle |
| ASC-006 | Team reorganization on stagnation | DIMENSION-NEW/MERGE/SPLIT/REGROUP | Empty roster → cold start discussion | New teams form, dead teams dissolve |
| ASC-007 | Canonical JSONL logging | All experiments logged, write-once | Concurrent writes from multiple agents | No data loss, no overwrite |

### 2.2 Multi-Hop Research
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| MHR-001 | 3-hop research query | Each hop refines based on prior results | Circular references → detect and break | Final synthesis cites all hop sources |
| MHR-002 | Knowledge graph construction | Entities + relationships extracted | Duplicate entities → merge | Graph has no orphan nodes |
| MHR-003 | Source credibility scoring | Score assigned per source | Unknown source → default low confidence | High-credibility sources ranked first |
| MHR-004 | Research strategy selection | Breadth-first for overview, depth-first for detail | Ambiguous query → iterative refinement | Appropriate strategy auto-selected |

---

## 3. Agent Swarm Tests

### 3.1 Dynamic Workflows
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| DWF-001 | Parallel agent dispatch | N agents explore independently | N=0 → single agent fallback | All results collected |
| DWF-002 | Adversarial verification | Agents try to break each answer | 100% agreement → no adversarial value | Disagreement rate >0% |
| DWF-003 | Convergence detection | Iterate until answers converge | Never converges → timeout + escalation | Convergence correctly detected |
| DWF-004 | Checkpoint recovery | Resume interrupted workflow | Empty checkpoint → fresh start | Restored state matches pre-interruption |
| DWF-005 | Token budget guard | 80% warning, 95% hard stop | Burst token usage → throttle | Never exceeds 95% budget |

### 3.2 Catfish Contrarian Agent
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| CTF-001 | Wrong consensus forming | Contrarian agent flags it | Correct consensus → contrarian agrees | Wrong consensus correctly blocked |
| CTF-002 | Contrarian itself wrong | Other agents overrule | Split decision → human escalation | False positive rate <5% |
| CTF-003 | Multi-turn debate | Contrarian maintains skepticism | Contrarian convinced → switches | Debate terminates with clear outcome |

### 3.3 AdaptOrch Topology Routing
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| ADO-001 | Independent subtasks | Parallel topology selected | Mixed dependencies → hybrid topology | 12-23% improvement over static |
| ADO-002 | Sequential dependency chain | Sequential topology | Circular dependency → error | Correct dependency ordering |
| ADO-003 | Hierarchical task structure | Hierarchical topology | Flat task with no hierarchy → flat topology | Appropriate topology per task DAG |

---

## 4. Skills System Tests

### 4.1 Skill Evolution
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| SKL-001 | Skill creation from trace | Trace pattern → candidate skill | No discernible pattern → no skill | Skill passes validation gate |
| SKL-002 | Validation gate (SkillOpt) | Candidate skill evaluated | Regression detected → rejected | No regression accepted |
| SKL-003 | Self-evolution cycle | Mutation → evaluation → selection | All mutations worse → keep original | Fitness monotonically non-decreasing |
| SKL-004 | Progressive withdrawal (Skill0) | Scaffolding gradually removed | Agent fails without scaffolding → reinforce | Skill internalized after curriculum |

### 4.2 Skill Loading
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| SKL-005 | Lazy skill loading | Skill loaded on first use | All skills needed at once → batch load | Startup time reduced ≥29% |
| SKL-006 | Predictive preloading | ML predicts next skill needed | Wrong prediction → load correct skill | 40% cache hit rate target |
| SKL-007 | Hot reload | Updated SKILL.md loaded without restart | Malformed SKILL.md → reject, keep current | Zero-downtime skill updates |

---

## 5. Model Routing Tests

### 5.1 NeuralUCB Router
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| RTR-001 | Reasoning-heavy task | Routes to Opus/strongest model | Budget exhausted → fallback chain | Task completed at target quality |
| RTR-002 | Simple execution task | Routes to Haiku/fastest model | Haiku fails → escalate to Sonnet | Cost reduced ≥70% vs always-Opus |
| RTR-003 | Multi-turn routing (MTRouter) | Optimizes across conversation turns | Context shift mid-conversation → re-route | 58.7% cost reduction target |
| RTR-004 | Cold start (no history) | Auto-learns routing preferences | All models equally uncertain → uniform explore | Converges within 50 requests |
| RTR-005 | Provider fallback | Primary fails → secondary provider | All providers fail → graceful degradation | No request dropped |

---

## 6. Safety & Alignment Tests

### 6.1 Parallax Cognitive-Executive Separation
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| SAF-001 | Injection attack on reasoning context | Attack blocked at Layer 0 | Multi-turn injection → cumulative detection | Block rate ≥99.5% |
| SAF-002 | Reasoning proposes dangerous action | Executive validator blocks it | Reasoning context compromised → validator independent | No dangerous action executed |
| SAF-003 | Cross-model adversarial review | 3 models vote on action | 2-1 split → escalate | Verdict logged immutably |

### 6.2 Behavioral Fingerprint Regression
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| SAF-004 | Known-good behavior | Baseline fingerprint recorded | First run → create baseline | Fingerprint stored |
| SAF-005 | Regression detected | Fingerprint deviates from baseline | Legitimate behavior change → update baseline | Regression detection rate ≥86% |
| SAF-006 | Binary pass/fail comparison | Fingerprint catches what binary misses | Edge behavior → borderline | Fingerprint more sensitive than binary |

---

## 7. Context Engineering Tests

### 7.1 Filesystem-as-Context
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| CTX-001 | Tool output exposed as file | Agent reads via grep/find/read | Large output (10MB+) → truncated with summary | Agent accesses data via filesystem ops |
| CTX-002 | Mermaid symbolic compression | Tool output compressed 61% | Non-compressible output → pass through | Token reduction ≥50% |
| CTX-003 | Append-only context log | Never modifies prior messages | Forced trim by system → log warning | KV-cache validity maintained |

### 7.2 Auto-Compaction
| Test ID | Scenario | Expected Output | Edge Cases | Pass/Fail Criteria |
|---------|----------|----------------|------------|-------------------|
| CTX-004 | Autonomous compaction trigger | Agent decides when to compact | Mid-task → deferred to task boundary | Compaction only between tasks |
| CTX-005 | Compaction preserves critical info | CLAUDE.md/IRON RULES survive | All info critical → minimal compaction | No task-critical info lost |
| CTX-006 | Dual-threshold offloading | 50%: offload tool outputs; 85%: aggressive compress | Rapid context growth → early trigger | Context window <80% utilized |

---

## 8. MCP Integration Tests

| Test ID | Scenario | Expected Output | Pass/Fail Criteria |
|---------|----------|----------------|-------------------|
| MCP-001 | Gateway starts bundled servers | 20 servers registered | All servers healthy on startup |
| MCP-002 | Progressive tool disclosure | ToolSearch → ToolDescribe → ToolCall | Core tools always available |
| MCP-003 | Server crash recovery | Auto-restart failed server | Max 3 restarts, then disable |
| MCP-004 | Cross-server query | Results from multiple servers merged | Deduplicated results |

---

## 9. Voice/Sound UX Tests

| Test ID | Scenario | Expected Output | Pass/Fail Criteria |
|---------|----------|----------------|-------------------|
| VOX-001 | Session start sound plays | "Work, work" (Peon pack) | Sound plays within 500ms |
| VOX-002 | Task complete sound plays | "Job's done!" | Sound plays on task completion |
| VOX-003 | Theme switching | `/sound theme sci-fi` | All subsequent sounds from Sci-Fi pack |
| VOX-004 | Cross-platform playback | macOS, Linux tested | Sound plays on each platform |
| VOX-005 | Disable sounds | `/sound off` | No sounds played |

---

## 10. Full Autonomy Tests

| Test ID | Scenario | Expected Output | Pass/Fail Criteria |
|---------|----------|----------------|-------------------|
| AUT-001 | Continuous loop (8h) | Self-directs, handles interruptions | No manual intervention needed |
| AUT-002 | Task resumption after crash | Resumes from last checkpoint | State consistent, no duplicate work |
| AUT-003 | Idle loop efficiency | Sleeps appropriately | <5% token waste on idle polling |
| AUT-004 | Self-directed task selection | Picks next task from queue | Picks highest-priority unblocked task |
| AUT-005 | Budget awareness | Stays within daily token budget | Never exceeds budget without escalation |

---

## 11. End-to-End Integration Tests

| Test ID | Scenario | Expected Output |
|---------|----------|----------------|
| E2E-001 | Full research loop | Query → Multi-hop → Knowledge graph → Synthesis → Citation → Output |
| E2E-002 | AutoScientists-style experiment | Hypothesis → Proposal gate → Execute → Log → Champion update |
| E2E-003 | Swarm debate convergence | 5 agents debate → Adversarial verify → Converge → Output |
| E2E-004 | Cross-session recall | Session 1: learn fact → Session 2: recall fact correctly |
| E2E-005 | Skill evolution cycle | Trace → Learn → Create → Validate → Deploy → Monitor regression |

---

## 12. Benchmark Targets

| Benchmark | Metric | Target | Timeline |
|-----------|--------|--------|----------|
| LongMemEval | Recall@5 | ≥96.6% | Phase G |
| BioML-Bench | Leaderboard percentile | ≥74.4% | Phase H |
| SWE-bench (Codex equivalent) | Resolution rate | ≥26% | Phase I |
| MemoryAgentBench | Multi-hop conflict resolution | ≥15% (from 7% baseline) | Phase I |
| AgentAssay | Regression detection | ≥86% | Phase I |
| AgentTrace | Root cause accuracy | ≥93% | Phase I |

---

*Test plan covers all flows from §4 workstreams. Implementation in parallel with feature development. DEEPSEEK_API_KEY configured for test execution.*

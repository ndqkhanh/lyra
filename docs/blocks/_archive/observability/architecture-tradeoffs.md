# Observability Architecture Tradeoffs

## Design Decisions

This document explains **why** Lyra's observability system is designed the way it is, what alternatives were considered, and what tradeoffs were accepted.

## Decision 1: Dual Protocol (HIR + OTel)

### The Choice
Emit both HIR (Harness Intermediate Representation) and OpenTelemetry formats in parallel.

### Alternatives Considered

| Alternative | Why Not Chosen |
|-------------|----------------|
| **OTel-only** | Agent-specific tooling (HAFC, SHP, autogenesis) would require adapters; loses agent semantics |
| **HIR-only** | Cannot leverage existing OTel ecosystem (Jaeger, Honeycomb, Datadog, Grafana) |
| **Convert HIR→OTel on-demand** | Adds latency to export path; complicates real-time streaming |
| **Single unified format** | No standard exists; would fragment ecosystem |

### Tradeoffs Accepted

**Cost**: ~20% more storage (both formats written)
- **Mitigation**: JSONL compression (gzip) reduces overhead to ~5%
- **Justification**: Storage is cheap; flexibility is valuable

**Complexity**: Two encoders to maintain
- **Mitigation**: Shared event bus; encoders are stateless transformers
- **Justification**: Each format serves distinct audiences (agents vs. platform teams)

**Why This Won**:
- HIR enables agent-specific analysis (test harness profiling, failure classification, curriculum mining)
- OTel enables integration with enterprise observability stacks
- Both formats from single event stream = zero duplicate instrumentation

---

## Decision 2: Local-First Storage (JSONL Files)

### The Choice
Store traces as append-only JSONL files in `.lyra/sessions/`, not in a database.

### Alternatives Considered

| Alternative | Why Not Chosen |
|-------------|----------------|
| **SQLite** | Requires schema migrations; slower append (locks); harder to grep/pipe |
| **PostgreSQL** | Heavyweight dependency; requires service management; overkill for local dev |
| **ClickHouse / TimescaleDB** | Excellent for production but too heavy for local development |
| **Cloud vendor (Honeycomb, Datadog)** | Privacy concerns; requires network; costs money; not available offline |

### Tradeoffs Accepted

**Query Performance**: Full-table scans for complex queries
- **Mitigation**: Most queries are single-session; streaming parser keeps memory low
- **Mitigation**: Index file (`.lyra/sessions/index.jsonl`) for session-level queries
- **Justification**: Local dev prioritizes simplicity over query speed

**No Transactions**: JSONL append is not atomic across files
- **Mitigation**: Each session writes to isolated directory
- **Mitigation**: Buffered writes flushed on crash via atexit handler
- **Justification**: Session isolation makes multi-file transactions unnecessary

**No Schema Enforcement**: JSONL doesn't validate event shape
- **Mitigation**: Pydantic models validate at write time
- **Mitigation**: `lyra doctor --validate-traces` runs schema checks
- **Justification**: Development velocity > rigid schema enforcement

**Why This Won**:
- Zero setup: no database to install/configure
- Human-readable: `cat trace.jsonl | jq` works out of the box
- Privacy-first: data never leaves machine unless explicitly configured
- Grepable: standard Unix tools work (`grep`, `awk`, `jq`)
- Portable: copy entire `.lyra/` directory to share session

---

## Decision 3: Content-Addressed Artifact Storage

### The Choice
Store large payloads (tool outputs, diffs, verdicts) as separate files named by SHA-256 hash.

### Alternatives Considered

| Alternative | Why Not Chosen |
|-------------|----------------|
| **Inline in events** | Bloats trace.jsonl; makes streaming parser memory-intensive |
| **Separate DB table** | Requires DB; loses content deduplication across sessions |
| **Cloud blob storage (S3)** | Requires network; costs money; not available offline |
| **Sequential IDs** | Loses deduplication; collision risk across sessions |

### Tradeoffs Accepted

**Indirection**: Events contain hash references, not content
- **Mitigation**: `retro.py` automatically resolves hashes on replay
- **Justification**: Keeps event stream compact and fast to parse

**Hash Collisions (SHA-256)**: Theoretical risk of two artifacts with same hash
- **Mitigation**: SHA-256 collision probability is negligible (< 10^-60)
- **Justification**: No practical collision risk for artifact sizes we handle

**Orphaned Artifacts**: Artifacts may outlive their referencing sessions
- **Mitigation**: `lyra gc --artifacts` runs reference counting cleanup
- **Justification**: Disk space is cheap; better safe than sorry

**Why This Won**:
- Deduplication: Same tool output stored once across sessions
- Immutability: Content never changes after write (enables caching)
- Simplicity: No database or blob store required
- Grepability: `grep -r "pattern" .lyra/sessions/*/artifacts/`

---

## Decision 4: Best-Effort OTLP Export

### The Choice
OTLP export runs in parallel but does not block agent loop on failure.

### Alternatives Considered

| Alternative | Why Not Chosen |
|-------------|----------------|
| **Blocking export** | Network latency blocks agent; unacceptable for dev UX |
| **No export (file-only)** | Loses integration with enterprise observability platforms |
| **Queue to disk, export async** | Complex; requires background worker; overkill for v1 |

### Tradeoffs Accepted

**Data Loss on Crash**: Buffered OTLP spans may be lost if process crashes
- **Mitigation**: File export (trace.jsonl) is always written first
- **Mitigation**: OTLP batch size kept small (100 spans) to limit loss
- **Justification**: Local file is source of truth; OTLP is convenience

**No Delivery Guarantee**: Network failures may drop spans
- **Mitigation**: Circuit breaker logs warnings on consecutive failures
- **Mitigation**: `lyra trace export --format otlp` can re-export from file
- **Justification**: Real-time export is best-effort; file is durable

**Eventual Consistency**: OTLP backend may lag behind file
- **Mitigation**: Clearly document that file is source of truth
- **Justification**: Acceptable for debugging; production systems use durable exporters

**Why This Won**:
- Zero latency impact on agent loop (async export)
- Graceful degradation on network issues
- File remains fully functional without network

---

## Decision 5: In-Memory Event Bus (No External Queue)

### The Choice
Use Python `asyncio.Queue` for event distribution, not Redis/Kafka/RabbitMQ.

### Alternatives Considered

| Alternative | Why Not Chosen |
|-------------|----------------|
| **Redis Streams** | Requires Redis running; overkill for single-process agent |
| **Kafka** | Far too heavy for local dev; designed for distributed systems |
| **RabbitMQ** | Requires service management; unnecessary complexity |
| **ZeroMQ** | Adds dependency; in-memory queue sufficient for local workloads |

### Tradeoffs Accepted

**No Cross-Process Observability**: Events lost if process crashes before flush
- **Mitigation**: Buffered writes flushed every 5 seconds and on exit
- **Mitigation**: `lyra doctor --check-sessions` detects incomplete traces
- **Justification**: Single-process agent is primary use case

**No Pub/Sub Across Machines**: Cannot stream events to remote dashboard
- **Mitigation**: OTLP export handles remote streaming
- **Justification**: Local dashboard sufficient for dev; OTLP for production

**Bounded Buffer**: Ring buffer evicts oldest events under extreme load
- **Mitigation**: Buffer size configurable (default 10K events)
- **Mitigation**: Warning logged when buffer overflows
- **Justification**: 10K events ~= 200-step session; overflow is rare

**Why This Won**:
- Zero dependencies: no external service required
- Low latency: < 10 µs to publish event
- Simple: standard library primitives
- Sufficient: handles 100K+ events/sec

---

## Decision 6: Secret Masking at Write Time (Not Read Time)

### The Choice
Apply regex-based secret masking when writing events, not when reading them.

### Alternatives Considered

| Alternative | Why Not Chosen |
|-------------|----------------|
| **Mask on read** | Secrets persist in trace files; violates privacy-by-default |
| **Encrypt traces** | Requires key management; makes traces unreadable with standard tools |
| **No masking** | Unacceptable security risk; secrets leak into traces |

### Tradeoffs Accepted

**False Positives**: Aggressive regex may mask non-secrets
- **Mitigation**: Configurable patterns in `~/.lyra/secrets-patterns.yaml`
- **Mitigation**: `--no-mask` flag for trusted sessions
- **Justification**: Better safe than leaking credentials

**False Negatives**: Novel secret formats may not be detected
- **Mitigation**: Regularly update patterns from `secrets-scan` project
- **Mitigation**: `lyra doctor --check-secrets` scans existing traces
- **Justification**: Best-effort protection; user responsibility for sensitive data

**Performance Cost**: Regex matching on every event write
- **Mitigation**: Compiled regex patterns cached
- **Mitigation**: Masking only applied to string fields (not numbers/booleans)
- **Justification**: < 10 µs overhead acceptable for security

**Why This Won**:
- Privacy-by-default: secrets never written to disk
- No key management: no encryption keys to lose
- Grepable: masked traces still readable with standard tools

---

## Cost vs. Benefit Analysis

### Performance Budget

| Component | Overhead | Justification |
|-----------|----------|---------------|
| Event publish | < 10 µs | Amortized cost: 1 publish per tool call (~1 second duration) = 0.001% overhead |
| Secret masking | < 10 µs | Security requirement; acceptable for < 0.001% total runtime |
| JSONL write | < 100 µs | Async buffered; non-blocking on agent loop |
| OTLP export | 0 µs (async) | Fully parallel; zero impact on agent latency |
| **Total hot path** | **< 20 µs** | **< 0.002% overhead** for typical agent workload |

### Storage Costs

| Component | Size (200-step session) | Mitigation |
|-----------|-------------------------|------------|
| trace.jsonl | ~500 KB | gzip reduces to ~50 KB |
| metrics.jsonl | ~50 KB | Rolling aggregation every 10 steps |
| artifacts/ | ~5 MB | Content deduplication across sessions |
| **Total** | **~5.5 MB** | **< $0.01/month on cloud storage** |

### Maintenance Costs

| Component | Lines of Code | Complexity |
|-----------|---------------|------------|
| Event bus | ~200 LOC | Low (standard library) |
| HIR encoder | ~300 LOC | Low (dataclass transforms) |
| OTel encoder | ~250 LOC | Medium (semantic conventions) |
| Trace writer | ~200 LOC | Low (file I/O) |
| Retro engine | ~400 LOC | Medium (streaming JSON parser) |
| **Total** | **~1,350 LOC** | **Manageable; well-isolated** |

---

## Future Evolution Paths

### Path 1: Opt-In Distributed Tracing
**When**: Multi-machine agent swarms become common
**How**: Add `lyra-trace-server` (gRPC service) that aggregates traces from multiple agents
**Tradeoff**: Adds deployment complexity; only enable when needed

### Path 2: Structured Query Language
**When**: Complex trace queries become frequent (percentile latencies, multi-session aggregations)
**How**: Import traces into DuckDB; run SQL queries
**Tradeoff**: Requires indexing step; use for batch analysis, not real-time

### Path 3: PII Auto-Detection
**When**: Enterprise customers require compliance (GDPR, HIPAA)
**How**: Integrate Presidio or similar for NER-based PII detection
**Tradeoff**: Slower masking (NLP inference); offer as opt-in feature

---

## Lessons from Alternatives

### What We Learned from LangSmith
**Good**: Central trace aggregation simplifies multi-agent debugging
**Bad**: Network dependency breaks offline development
**Our Approach**: Local-first with optional cloud export

### What We Learned from LangGraph Studio
**Good**: Visual trace inspector reduces cognitive load
**Bad**: Requires Electron app; not CLI-friendly
**Our Approach**: Terminal UI + optional HTML export

### What We Learned from AutoGen
**Good**: Logs are just Python dicts; easy to extend
**Bad**: No standardized schema; hard to compare across runs
**Our Approach**: HIR standard for cross-framework compatibility

---

## References

- [OpenTelemetry Design Principles](https://opentelemetry.io/docs/specs/otel/overview/)
- [Gnomon HIR Rationale](https://github.com/lyra-contributors/gnomon-hir/blob/main/docs/rationale.md)
- [Jaeger Architecture](https://www.jaegertracing.io/docs/architecture/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)

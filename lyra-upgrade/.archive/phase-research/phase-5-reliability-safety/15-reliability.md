# §4.16 Reliability & Intelligent Verifier - Implementation Plan

**Status**: Planning  
**Priority**: P0 (Foundation for production readiness)  
**Dependencies**: §4.2 Memory, §4.6 Tools, §4.8 MCP  
**Estimated Effort**: 4-6 weeks

---

## 1. Overview

This plan implements a comprehensive reliability system for Lyra combining:

1. **Mutation-Gated Verification** (SABER): Selective verification at high-impact decision points
2. **pass^k Reliability Metrics** (τ-bench): Consistency tracking across multiple attempts
3. **Adversarial Testing** (AgentDojo): Security validation against prompt injection
4. **Observability Infrastructure** (Phoenix + Langfuse): Tracing, evaluation, monitoring

**Breakthrough**: Target verification at mutating actions (environment-changing) where errors have 92-96% impact on success, avoiding blanket overhead while maximizing reliability gains.

---

## 2. Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Lyra Agent Runtime                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   Planning   │─────▶│ Verification │─────▶│ Execution │ │
│  │    Layer     │      │    Layer     │      │   Layer   │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│         │                      │                     │       │
│         │                      │                     │       │
│         ▼                      ▼                     ▼       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Observability & Tracing (Phoenix)          │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Evaluation Engine   │
                    │    (Langfuse)        │
                    └──────────────────────┘
```

### 2.2 Verification Flow

```
Action Proposed
  │
  ├─▶ Mutation Classifier (SABER)
  │     │
  │     ├─▶ Non-Mutating → Execute (fast path)
  │     │
  │     └─▶ Mutating → Verification Pipeline
  │           │
  │           ├─▶ Historical pass^k Check
  │           │     │
  │           │     ├─▶ pass^k ≥ threshold → Light verification
  │           │     └─▶ pass^k < threshold → Full verification
  │           │
  │           ├─▶ Adversarial Pattern Check (AgentDojo)
  │           │
  │           ├─▶ Alignment Audit (LlamaFirewall)
  │           │
  │           ├─▶ Code Safety (CodeShield if applicable)
  │           │
  │           └─▶ Decision: Approve / Reject / Human Review
  │
  └─▶ Execute with Tracing
        │
        └─▶ Update pass^k Metrics
```

---

## 3. Implementation Phases

### Phase 1: Observability Foundation (Week 1-2)

**Goal**: Establish tracing and monitoring infrastructure.

#### 1.1 Phoenix Integration

**Tasks**:
- Install `arize-phoenix` and `arize-phoenix-otel` packages
- Configure OpenTelemetry instrumentation for Lyra runtime
- Set up trace collection for tool calls, LLM interactions, agent actions
- Implement semantic conventions for agent-specific spans
- Deploy Phoenix server (local dev + production options)

**Deliverables**:
- `packages/lyra-observability/phoenix/` module
- Configuration in `lyra.config.ts`
- Environment variables: `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_PROJECT_NAME`
- Documentation: Phoenix setup guide

**Acceptance Criteria**:
- All tool calls traced with OpenTelemetry spans
- Traces viewable in Phoenix UI
- Latency and error metrics captured
- Zero performance degradation (<5ms overhead per span)

#### 1.2 Langfuse Integration

**Tasks**:
- Install `langfuse` SDK
- Configure Langfuse client with API keys
- Implement prompt versioning for agent system prompts
- Set up dataset management for evaluation
- Create evaluation workflows for regression testing

**Deliverables**:
- `packages/lyra-observability/langfuse/` module
- Prompt management API
- Dataset creation utilities
- Evaluation runner

**Acceptance Criteria**:
- System prompts versioned in Langfuse
- Datasets created from production traces
- Evaluation runs tracked with results
- A/B testing support via metadata tags

#### 1.3 Trace Enrichment

**Tasks**:
- Add custom attributes to spans: `action.is_mutating`, `action.type`, `verification.triggered`
- Implement trace context propagation across async boundaries
- Add pass^k tracking metadata
- Link traces to evaluation results

**Deliverables**:
- `TraceEnricher` class with attribute injection
- Context propagation utilities
- Metadata schema documentation

**Acceptance Criteria**:
- All actions tagged with mutability classification
- Verification decisions recorded in traces
- pass^k metrics queryable from trace data
- Traces linked to benchmark results

---

### Phase 2: Mutation-Gated Verification (Week 2-3)

**Goal**: Implement SABER-inspired mutation detection and selective verification.

#### 2.1 Mutation Classifier

**Tasks**:
- Implement action classification: mutating vs. non-mutating
- Define mutation taxonomy: file writes, API calls with side effects, database updates, system commands
- Create classifier using LLM-based analysis + rule-based heuristics
- Cache classification results for common action patterns

**Deliverables**:
- `packages/lyra-verifier/mutation-classifier.ts`
- Mutation taxonomy documentation
- Classification cache with TTL

**Implementation**:
```typescript
interface ActionClassification {
  isMutating: boolean;
  mutationType?: 'file_write' | 'api_call' | 'db_update' | 'system_command';
  confidence: number;
  reasoning: string;
}

class MutationClassifier {
  async classify(action: AgentAction): Promise<ActionClassification> {
    // Rule-based fast path
    const ruleResult = this.applyRules(action);
    if (ruleResult.confidence > 0.95) return ruleResult;
    
    // LLM-based classification for ambiguous cases
    return this.llmClassify(action);
  }
}
```

**Acceptance Criteria**:
- 95%+ accuracy on hand-labeled test set
- <10ms latency for rule-based classification
- <200ms latency for LLM-based classification
- Cache hit rate >80% in production

#### 2.2 Verification Pipeline

**Tasks**:
- Implement verification orchestrator
- Add targeted reflection prompts before mutating actions
- Implement block-based context cleaning (SABER)
- Create verification decision logic with confidence thresholds

**Deliverables**:
- `packages/lyra-verifier/verification-pipeline.ts`
- Reflection prompt templates
- Context cleaning utilities

**Implementation**:
```typescript
interface VerificationResult {
  decision: 'approve' | 'reject' | 'human_review';
  confidence: number;
  reasoning: string;
  checks: VerificationCheck[];
}

class VerificationPipeline {
  async verify(action: AgentAction, context: AgentContext): Promise<VerificationResult> {
    const checks: VerificationCheck[] = [];
    
    // Targeted reflection
    checks.push(await this.reflectionCheck(action, context));
    
    // Adversarial pattern check
    checks.push(await this.adversarialCheck(action));
    
    // Alignment audit
    checks.push(await this.alignmentCheck(action, context));
    
    // Code safety (if applicable)
    if (action.type === 'code_generation') {
      checks.push(await this.codeShieldCheck(action));
    }
    
    return this.makeDecision(checks);
  }
}
```

**Acceptance Criteria**:
- Verification triggered only for mutating actions
- Reflection reduces error rate by 10%+ (SABER baseline)
- Context cleaning prevents stale constraint violations
- Decision confidence calibrated (90% confidence → 90% accuracy)

---

### Phase 3: pass^k Reliability Metrics (Week 3-4)

**Goal**: Implement consistency tracking across multiple attempts.

#### 3.1 Metrics Collection

**Tasks**:
- Implement pass^k calculation for task types
- Track success/failure across attempts (k=1,2,3,4,8)
- Store historical performance by domain, task, model
- Create metrics aggregation pipeline

**Deliverables**:
- `packages/lyra-metrics/pass-k-tracker.ts`
- Metrics storage schema (PostgreSQL or ClickHouse)
- Aggregation queries

**Implementation**:
```typescript
interface PassKMetrics {
  taskType: string;
  domain: string;
  model: string;
  pass1: number;  // Success rate on first attempt
  pass2: number;  // Success rate within 2 attempts
  pass4: number;
  pass8: number;
  totalAttempts: number;
  lastUpdated: Date;
}

class PassKTracker {
  async recordAttempt(taskId: string, attempt: number, success: boolean): Promise<void> {
    // Record attempt result
    await this.storage.recordAttempt(taskId, attempt, success);
    
    // Update aggregated metrics
    await this.updateMetrics(taskId);
  }
  
  async getMetrics(filters: MetricFilters): Promise<PassKMetrics> {
    return this.storage.getAggregatedMetrics(filters);
  }
}
```

**Acceptance Criteria**:
- pass^k calculated for all task types
- Metrics updated in real-time (<1s latency)
- Historical trends queryable by time range
- Dashboard displays pass^k by domain/model

#### 3.2 Adaptive Verification

**Tasks**:
- Implement threshold-based verification triggering
- Use pass^k < 0.5 as trigger for full verification
- Use pass^k ≥ 0.7 for light verification
- Dynamic threshold adjustment based on task criticality

**Deliverables**:
- `packages/lyra-verifier/adaptive-verifier.ts`
- Threshold configuration
- Criticality scoring system

**Implementation**:
```typescript
class AdaptiveVerifier {
  async shouldVerify(action: AgentAction): Promise<VerificationLevel> {
    const metrics = await this.passKTracker.getMetrics({
      taskType: action.taskType,
      domain: action.domain,
      model: action.model
    });
    
    const criticality = this.scoreCriticality(action);
    
    if (metrics.pass1 < 0.5 || criticality === 'high') {
      return 'full';
    } else if (metrics.pass1 < 0.7 || criticality === 'medium') {
      return 'light';
    } else {
      return 'none';
    }
  }
}
```

**Acceptance Criteria**:
- Verification level adapts to historical performance
- High-criticality actions always verified
- Low-pass^k tasks trigger full verification
- Verification overhead reduced by 40% vs. blanket approach

---

### Phase 4: Adversarial Testing Integration (Week 4-5)

**Goal**: Integrate prompt injection detection and adversarial validation.

#### 4.1 AgentDojo Pattern Library

**Tasks**:
- Extract prompt injection patterns from AgentDojo benchmark
- Implement pattern matching for tool outputs
- Create adversarial test case generator
- Build pattern database with severity scoring

**Deliverables**:
- `packages/lyra-security/adversarial-patterns.ts`
- Pattern database (JSON/YAML)
- Test case generator

**Implementation**:
```typescript
interface AdversarialPattern {
  id: string;
  name: string;
  pattern: RegExp | string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  mitigation: string;
}

class AdversarialChecker {
  async checkAction(action: AgentAction): Promise<AdversarialCheckResult> {
    const matches: PatternMatch[] = [];
    
    // Check tool outputs for injection patterns
    for (const output of action.toolOutputs) {
      matches.push(...this.scanForPatterns(output));
    }
    
    // Check action parameters
    matches.push(...this.scanForPatterns(action.parameters));
    
    return {
      hasThreats: matches.length > 0,
      matches,
      maxSeverity: this.getMaxSeverity(matches)
    };
  }
}
```

**Acceptance Criteria**:
- 95%+ detection rate on AgentDojo test cases
- <5% false positive rate
- <50ms latency per check
- Severity scoring aligns with security impact

#### 4.2 LlamaFirewall Integration

**Tasks**:
- Integrate PromptGuard 2 for jailbreak detection
- Implement AlignmentCheck for goal hijacking
- Add CodeShield for code generation safety
- Configure scanner orchestration

**Deliverables**:
- `packages/lyra-security/llamafirewall-adapter.ts`
- Scanner configuration
- Integration tests

**Implementation**:
```typescript
class LlamaFirewallAdapter {
  private firewall: LlamaFirewall;
  
  async scanInput(userMessage: string): Promise<ScanResult> {
    return this.firewall.scan(userMessage, {
      scanners: [ScannerType.PROMPT_GUARD]
    });
  }
  
  async scanPlan(agentPlan: AgentPlan, context: AgentContext): Promise<ScanResult> {
    return this.firewall.scan_replay(context.conversationTrace, {
      scanners: [ScannerType.AGENT_ALIGNMENT]
    });
  }
  
  async scanCode(generatedCode: string, language: string): Promise<ScanResult> {
    return this.firewall.scan(generatedCode, {
      scanners: [ScannerType.CODE_SHIELD],
      language
    });
  }
}
```

**Acceptance Criteria**:
- PromptGuard 2 blocks 95%+ jailbreak attempts
- AlignmentCheck detects goal hijacking with 90%+ accuracy
- CodeShield prevents insecure code patterns
- Integration adds <100ms latency per scan

---

### Phase 5: Benchmark Integration & SDLC (Week 5-6)

**Goal**: Integrate benchmarks into development lifecycle and CI/CD.

#### 5.1 Benchmark Runners

**Tasks**:
- Implement τ-bench runner with pass^k calculation
- Implement Terminal-Bench runner for CLI tasks
- Implement SWE-bench Verified runner for code generation
- Create benchmark result aggregation and reporting

**Deliverables**:
- `packages/lyra-benchmarks/tau-bench-runner.ts`
- `packages/lyra-benchmarks/terminal-bench-runner.ts`
- `packages/lyra-benchmarks/swe-bench-runner.ts`
- Benchmark result schema and storage

**Implementation**:
```typescript
interface BenchmarkResult {
  benchmarkName: string;
  version: string;
  timestamp: Date;
  model: string;
  metrics: {
    pass1?: number;
    pass2?: number;
    pass4?: number;
    pass8?: number;
    accuracy?: number;
    taskCompletionRate?: number;
  };
  taskResults: TaskResult[];
}

class TauBenchRunner {
  async run(config: BenchmarkConfig): Promise<BenchmarkResult> {
    const results: TaskResult[] = [];
    
    for (const task of this.loadTasks(config.domain)) {
      const attempts = await this.runTaskWithRetries(task, config.maxAttempts);
      results.push(this.calculateTaskResult(attempts));
    }
    
    return {
      benchmarkName: 'tau-bench',
      metrics: this.calculatePassK(results),
      taskResults: results
    };
  }
}
```

**Acceptance Criteria**:
- All benchmarks runnable via CLI
- Results stored with full traceability
- pass^k calculated correctly for τ-bench
- Benchmark runs complete in <30min for subset

#### 5.2 CI/CD Integration

**Tasks**:
- Add pre-commit hooks for unit tests + static analysis
- Add pre-merge checks for integration tests + benchmark subset
- Add pre-release full benchmark suite
- Configure alerts for pass^k degradation

**Deliverables**:
- `.github/workflows/reliability-checks.yml`
- Pre-commit hook configuration
- Benchmark subset selection (fast-running tasks)
- Alert configuration

**Implementation**:
```yaml
# .github/workflows/reliability-checks.yml
name: Reliability Checks

on:
  pull_request:
    branches: [main, develop]

jobs:
  benchmark-subset:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run benchmark subset
        run: |
          npm run benchmark:subset
      - name: Check pass^k threshold
        run: |
          npm run benchmark:check-threshold --threshold=0.7
```

**Acceptance Criteria**:
- Pre-commit runs in <30s
- Pre-merge runs in <10min
- Full benchmark suite runs nightly
- Alerts triggered on >5% pass^k degradation

---

## 4. Technical Specifications

### 4.1 Module Structure

```
packages/lyra-observability/
├── phoenix/
│   ├── tracer.ts              # OpenTelemetry instrumentation
│   ├── span-enricher.ts       # Custom attribute injection
│   └── exporter.ts            # Phoenix OTLP exporter
├── langfuse/
│   ├── client.ts              # Langfuse SDK wrapper
│   ├── prompt-manager.ts      # Prompt versioning
│   ├── dataset-manager.ts     # Dataset CRUD
│   └── evaluator.ts           # Evaluation runner
└── index.ts

packages/lyra-verifier/
├── mutation-classifier.ts     # Action classification
├── verification-pipeline.ts   # Orchestration
├── reflection-prompts.ts      # Targeted reflection
├── context-cleaner.ts         # Block-based cleaning
└── index.ts

packages/lyra-metrics/
├── pass-k-tracker.ts          # pass^k calculation
├── storage/
│   ├── postgres-adapter.ts    # PostgreSQL storage
│   └── clickhouse-adapter.ts  # ClickHouse storage
└── index.ts

packages/lyra-security/
├── adversarial-patterns.ts    # Pattern library
├── llamafirewall-adapter.ts   # LlamaFirewall integration
└── index.ts

packages/lyra-benchmarks/
├── tau-bench-runner.ts
├── terminal-bench-runner.ts
├── swe-bench-runner.ts
└── index.ts
```

### 4.2 Configuration Schema

```typescript
interface ReliabilityConfig {
  observability: {
    phoenix: {
      enabled: boolean;
      endpoint: string;
      projectName: string;
      samplingRate: number;
    };
    langfuse: {
      enabled: boolean;
      publicKey: string;
      secretKey: string;
      baseUrl: string;
    };
  };
  
  verification: {
    enabled: boolean;
    mutationClassifier: {
      llmModel: string;
      cacheEnabled: boolean;
      cacheTTL: number;
    };
    adaptiveThresholds: {
      fullVerification: number;  // pass^k threshold
      lightVerification: number;
    };
  };
  
  security: {
    llamaFirewall: {
      enabled: boolean;
      scanners: {
        promptGuard: boolean;
        alignmentCheck: boolean;
        codeShield: boolean;
      };
    };
    adversarialPatterns: {
      enabled: boolean;
      severityThreshold: 'low' | 'medium' | 'high' | 'critical';
    };
  };
  
  benchmarks: {
    tauBench: {
      enabled: boolean;
      domains: string[];
      maxAttempts: number;
    };
    terminalBench: {
      enabled: boolean;
      taskSubset?: string[];
    };
    sweBench: {
      enabled: boolean;
      verified: boolean;
    };
  };
}
```

### 4.3 Database Schema

```sql
-- pass^k metrics storage
CREATE TABLE pass_k_metrics (
  id SERIAL PRIMARY KEY,
  task_type VARCHAR(255) NOT NULL,
  domain VARCHAR(255) NOT NULL,
  model VARCHAR(255) NOT NULL,
  pass_1 DECIMAL(5,4),
  pass_2 DECIMAL(5,4),
  pass_4 DECIMAL(5,4),
  pass_8 DECIMAL(5,4),
  total_attempts INTEGER,
  last_updated TIMESTAMP DEFAULT NOW(),
  UNIQUE(task_type, domain, model)
);

-- Individual attempt records
CREATE TABLE task_attempts (
  id SERIAL PRIMARY KEY,
  task_id VARCHAR(255) NOT NULL,
  attempt_number INTEGER NOT NULL,
  success BOOLEAN NOT NULL,
  trace_id VARCHAR(255),
  error_type VARCHAR(255),
  timestamp TIMESTAMP DEFAULT NOW(),
  INDEX idx_task_id (task_id),
  INDEX idx_timestamp (timestamp)
);

-- Verification decisions
CREATE TABLE verification_decisions (
  id SERIAL PRIMARY KEY,
  action_id VARCHAR(255) NOT NULL,
  decision VARCHAR(50) NOT NULL,
  confidence DECIMAL(5,4),
  reasoning TEXT,
  checks JSONB,
  timestamp TIMESTAMP DEFAULT NOW(),
  INDEX idx_action_id (action_id)
);

-- Benchmark results
CREATE TABLE benchmark_results (
  id SERIAL PRIMARY KEY,
  benchmark_name VARCHAR(255) NOT NULL,
  version VARCHAR(50),
  model VARCHAR(255) NOT NULL,
  metrics JSONB,
  task_results JSONB,
  timestamp TIMESTAMP DEFAULT NOW(),
  INDEX idx_benchmark_model (benchmark_name, model),
  INDEX idx_timestamp (timestamp)
);
```

---

## 5. Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Trace overhead | <5ms per span | P95 latency |
| Mutation classification | <10ms (rule-based) | P95 latency |
| Mutation classification | <200ms (LLM-based) | P95 latency |
| Verification pipeline | <500ms (light) | P95 latency |
| Verification pipeline | <2s (full) | P95 latency |
| Adversarial check | <50ms | P95 latency |
| LlamaFirewall scan | <100ms | P95 latency |
| pass^k update | <1s | P95 latency |
| Benchmark subset | <10min | Total runtime |
| Benchmark full suite | <30min | Total runtime |

---

## 6. Success Metrics

### 6.1 Reliability Improvements

- **pass^k increase**: +10% on τ-bench (SABER baseline)
- **Error reduction**: 20% fewer mutating action errors
- **Consistency**: pass^8 / pass^1 ratio > 0.8

### 6.2 Security Improvements

- **Jailbreak detection**: 95%+ detection rate, <5% FP
- **Prompt injection**: 90%+ detection rate, <10% FP
- **Code safety**: Zero critical vulnerabilities in generated code

### 6.3 Operational Metrics

- **Verification overhead**: <10% latency increase vs. no verification
- **False positive rate**: <5% (actions incorrectly rejected)
- **Human review rate**: <2% of actions escalated
- **Benchmark coverage**: 100% of critical paths tested

---

## 7. Testing Strategy

### 7.1 Unit Tests

- Mutation classifier accuracy on labeled dataset
- pass^k calculation correctness
- Adversarial pattern matching precision/recall
- Verification decision logic

### 7.2 Integration Tests

- End-to-end verification flow
- Phoenix trace collection and enrichment
- Langfuse dataset creation and evaluation
- LlamaFirewall scanner orchestration

### 7.3 Benchmark Tests

- τ-bench pass^k calculation
- Terminal-Bench task execution
- SWE-bench Verified evaluation
- AgentDojo adversarial robustness

### 7.4 Performance Tests

- Trace overhead measurement
- Verification latency profiling
- Concurrent verification load testing
- Database query performance

---

## 8. Rollout Plan

### 8.1 Phase 1: Observability (Week 1-2)

- Deploy Phoenix in dev environment
- Enable tracing for 10% of production traffic
- Validate trace collection and UI
- Ramp to 100% over 1 week

### 8.2 Phase 2: Verification (Week 2-3)

- Deploy mutation classifier in shadow mode
- Collect classification accuracy metrics
- Enable verification in dev environment
- A/B test verification in production (10% traffic)

### 8.3 Phase 3: Metrics (Week 3-4)

- Deploy pass^k tracking
- Backfill historical data from traces
- Enable adaptive verification thresholds
- Monitor verification overhead

### 8.4 Phase 4: Security (Week 4-5)

- Deploy LlamaFirewall in shadow mode
- Tune detection thresholds
- Enable blocking for critical severity
- Ramp to full enforcement

### 8.5 Phase 5: Benchmarks (Week 5-6)

- Run baseline benchmarks
- Integrate into CI/CD
- Enable nightly full suite
- Configure alerting

---

## 9. Monitoring & Alerting

### 9.1 Key Metrics

- **pass^k trends**: Alert on >5% degradation
- **Verification latency**: Alert on P95 >2s
- **False positive rate**: Alert on >5%
- **Security detections**: Alert on critical severity
- **Benchmark failures**: Alert on <70% pass rate

### 9.2 Dashboards

- **Reliability Dashboard**: pass^k by domain/model, error taxonomy
- **Verification Dashboard**: Decision distribution, latency, confidence
- **Security Dashboard**: Detection counts by severity, false positive trends
- **Benchmark Dashboard**: Historical trends, comparison across models

---

## 10. Documentation Requirements

- Architecture overview with diagrams
- Configuration guide with examples
- API reference for all modules
- Benchmark runner usage guide
- Troubleshooting guide
- Performance tuning guide

---

## 11. Dependencies

### 11.1 External Packages

- `arize-phoenix` (^4.0.0)
- `arize-phoenix-otel` (^1.0.0)
- `langfuse` (^3.0.0)
- `@opentelemetry/api` (^1.8.0)
- `@opentelemetry/sdk-node` (^0.50.0)

### 11.2 Internal Dependencies

- `lyra-core` (agent runtime)
- `lyra-memory` (context management)
- `lyra-tools` (tool execution)

### 11.3 Infrastructure

- PostgreSQL 15+ or ClickHouse 23+ (metrics storage)
- Phoenix server (observability)
- Langfuse server (optional, can use cloud)

---

## 12. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Verification latency too high | High | Medium | Adaptive thresholds, caching, async verification |
| False positive rate too high | High | Medium | Confidence calibration, human review escalation |
| LlamaFirewall integration issues | Medium | Low | Fallback to pattern-based detection |
| Benchmark infrastructure costs | Medium | Medium | Subset selection, spot instances, caching |
| pass^k metric gaming | Low | Low | Multiple benchmark coverage, adversarial testing |

---

## 13. Future Enhancements

- **Multi-agent verification**: Consensus-based verification across agent swarm
- **Learned classifiers**: Train mutation classifier on production data
- **Automated threshold tuning**: Reinforcement learning for adaptive thresholds
- **Causal analysis**: Root cause analysis for verification failures
- **Federated benchmarking**: Distributed benchmark execution across fleet

---

**End of §4.16 Reliability Plan**


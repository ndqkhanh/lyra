# §4.13 Implementation Plan: Swarm Fleet with Channel-Based Communication

**Status**: PLAN  
**Priority**: HIGH×HIGH (P0)  
**Effort**: 3-4 weeks  
**Dependencies**: §4.12 (Agent Swarm basics), lyra-core message bus

---

## 1. Overview

Implement swarm fleet coordination combining:
- **Claude Code teams** for native parallel execution
- **Channel-based communication** (AgentsMesh pattern) for agent-to-agent messaging
- **Shared context store** (AutoScientists pattern) for cross-agent knowledge sharing
- **Orchestrator-worker pattern** (Anthropic pattern) for coordinated execution

**Target Performance**:
- 90% time reduction through parallel execution (Anthropic benchmark)
- Support 3-10 concurrent agents per swarm
- Sub-100ms channel message latency
- Persistent shared state across agent restarts

---

## 2. Architecture

### 2.1 Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Swarm Orchestrator                        │
│  - Task decomposition                                        │
│  - Agent spawning/lifecycle                                  │
│  - Result aggregation                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─────────────────┬──────────────┐
                              ▼                 ▼              ▼
                    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
                    │   Agent 1    │  │   Agent 2    │  │   Agent N    │
                    │  (Worker)    │  │  (Worker)    │  │  (Worker)    │
                    └──────────────┘  └──────────────┘  └──────────────┘
                              │                 │              │
                              └─────────────────┴──────────────┘
                                              │
                              ┌───────────────────────────────┐
                              │      Channel System           │
                              │  - Pub/Sub messaging          │
                              │  - Topic-based routing        │
                              │  - Message persistence        │
                              └───────────────────────────────┘
                                              │
                              ┌───────────────────────────────┐
                              │    Shared Context Store       │
                              │  - Champion solutions         │
                              │  - Experiment logs            │
                              │  - Discussion forums          │
                              │  - Proposal queues            │
                              │  - Dead-end registries        │
                              └───────────────────────────────┘
```

### 2.2 Channel System Design

**Channel Types**:
1. **Broadcast channels**: Orchestrator → all workers (task assignments, shutdown signals)
2. **Direct channels**: Worker → orchestrator (results, status updates)
3. **Peer channels**: Worker ↔ worker (collaboration, critique)
4. **Topic channels**: Filtered by research direction or task type

**Message Format**:
```typescript
interface ChannelMessage {
  id: string;                    // Unique message ID
  channel: string;               // Channel name
  sender: string;                // Agent ID
  timestamp: number;             // Unix timestamp
  type: 'task' | 'result' | 'critique' | 'status' | 'broadcast';
  payload: unknown;              // Type-specific payload
  replyTo?: string;              // For threaded conversations
  ttl?: number;                  // Time-to-live in seconds
}
```

**Implementation** (lyra-core):
```typescript
// packages/lyra-core/src/swarm/channel-system.ts
export class ChannelSystem {
  private channels: Map<string, Channel>;
  private subscribers: Map<string, Set<AgentSubscriber>>;
  
  async publish(message: ChannelMessage): Promise<void>;
  async subscribe(channel: string, handler: MessageHandler): Promise<Unsubscribe>;
  async createChannel(name: string, type: ChannelType): Promise<Channel>;
  async getHistory(channel: string, limit?: number): Promise<ChannelMessage[]>;
}
```

### 2.3 Shared Context Store

**Schema** (inspired by AutoScientists):
```typescript
interface SharedContext {
  // Champion solutions
  champions: Map<string, ChampionSolution>;
  
  // Experiment logs
  experiments: ExperimentLog[];
  
  // Discussion forums (threaded)
  discussions: Map<string, DiscussionThread>;
  
  // Proposal queues (per team/direction)
  proposals: Map<string, ProposalQueue>;
  
  // Dead-end registries (prevent redundant exploration)
  deadEnds: Map<string, DeadEndEntry>;
}

interface ChampionSolution {
  id: string;
  score: number;
  approach: string;
  code?: string;
  metrics: Record<string, number>;
  timestamp: number;
  author: string;
}

interface ExperimentLog {
  id: string;
  proposal: string;
  result: 'success' | 'failure' | 'inconclusive';
  metrics: Record<string, number>;
  insights: string;
  timestamp: number;
  author: string;
}
```

**Implementation**:
```typescript
// packages/lyra-core/src/swarm/shared-context.ts
export class SharedContextStore {
  private context: SharedContext;
  private persistence: PersistenceLayer;
  
  // Champion management
  async updateChampion(solution: ChampionSolution): Promise<void>;
  async getChampion(id: string): Promise<ChampionSolution | null>;
  
  // Experiment logging
  async logExperiment(log: ExperimentLog): Promise<void>;
  async getExperiments(filter?: ExperimentFilter): Promise<ExperimentLog[]>;
  
  // Discussion forums
  async postDiscussion(thread: string, message: DiscussionMessage): Promise<void>;
  async getDiscussion(thread: string): Promise<DiscussionThread>;
  
  // Proposal queues
  async submitProposal(queue: string, proposal: Proposal): Promise<void>;
  async claimProposal(queue: string, agentId: string): Promise<Proposal | null>;
  
  // Dead-end registry
  async registerDeadEnd(entry: DeadEndEntry): Promise<void>;
  async isDeadEnd(approach: string): Promise<boolean>;
}
```

---

## 3. Implementation Phases

### Phase 1: Channel System (Week 1)

**Tasks**:
1. Implement `ChannelSystem` class with pub/sub messaging
2. Add SQLite persistence for message history
3. Implement topic-based routing and filtering
4. Add TTL-based message expiration
5. Write unit tests for channel operations

**Deliverables**:
- `packages/lyra-core/src/swarm/channel-system.ts`
- `packages/lyra-core/src/swarm/channel-system.test.ts`
- SQLite schema for message persistence

**Acceptance Criteria**:
- Publish/subscribe with <100ms latency
- Message persistence survives process restart
- Topic filtering works correctly
- TTL expiration removes old messages

### Phase 2: Shared Context Store (Week 1-2)

**Tasks**:
1. Implement `SharedContextStore` class
2. Add SQLite persistence for all context types
3. Implement champion promotion logic
4. Add dead-end detection to prevent redundant work
5. Write unit tests for context operations

**Deliverables**:
- `packages/lyra-core/src/swarm/shared-context.ts`
- `packages/lyra-core/src/swarm/shared-context.test.ts`
- SQLite schema for shared context

**Acceptance Criteria**:
- Context persists across agent restarts
- Champion promotion updates correctly
- Dead-end registry prevents redundant exploration
- Concurrent access is thread-safe

### Phase 3: Swarm Orchestrator (Week 2-3)

**Tasks**:
1. Implement `SwarmOrchestrator` class
2. Add task decomposition logic
3. Implement agent spawning via Claude Code teams
4. Add result aggregation and synthesis
5. Implement orchestrator-worker communication via channels
6. Write integration tests

**Deliverables**:
- `packages/lyra-core/src/swarm/orchestrator.ts`
- `packages/lyra-core/src/swarm/orchestrator.test.ts`
- Integration with Claude Code teams API

**Acceptance Criteria**:
- Orchestrator spawns 3-10 workers successfully
- Task decomposition produces balanced workload
- Result aggregation synthesizes worker outputs
- Orchestrator handles worker failures gracefully

### Phase 4: Worker Agent Implementation (Week 3-4)

**Tasks**:
1. Implement `WorkerAgent` class
2. Add channel subscription for task assignments
3. Implement shared context read/write
4. Add peer-to-peer critique via channels
5. Implement status reporting to orchestrator
6. Write integration tests

**Deliverables**:
- `packages/lyra-core/src/swarm/worker-agent.ts`
- `packages/lyra-core/src/swarm/worker-agent.test.ts`
- Example swarm workflows

**Acceptance Criteria**:
- Workers receive and execute tasks from orchestrator
- Workers read/write shared context correctly
- Workers critique each other's proposals
- Workers report status and results to orchestrator

---

## 4. API Design

### 4.1 Swarm Creation

```typescript
import { SwarmOrchestrator } from '@lyra/core/swarm';

const swarm = new SwarmOrchestrator({
  name: 'research-swarm',
  maxWorkers: 5,
  channelSystem: channelSystem,
  sharedContext: sharedContext,
  model: 'claude-sonnet-4.6',
});

await swarm.start();
```

### 4.2 Task Execution

```typescript
const result = await swarm.execute({
  task: 'Optimize database query performance',
  decomposition: 'auto', // or 'manual' with explicit subtasks
  validation: 'adversarial', // require peer critique
  timeout: 3600000, // 1 hour
});

console.log(result.champion); // Best solution
console.log(result.experiments); // All attempts
console.log(result.insights); // Learned patterns
```

### 4.3 Channel Communication

```typescript
// Worker subscribes to task channel
await channelSystem.subscribe('tasks', async (message) => {
  if (message.type === 'task') {
    const result = await executeTask(message.payload);
    await channelSystem.publish({
      channel: 'results',
      sender: workerId,
      type: 'result',
      payload: result,
      replyTo: message.id,
    });
  }
});

// Orchestrator broadcasts task
await channelSystem.publish({
  channel: 'tasks',
  sender: 'orchestrator',
  type: 'task',
  payload: { subtask: 'analyze-query-plan', query: '...' },
});
```

### 4.4 Shared Context Access

```typescript
// Worker logs experiment
await sharedContext.logExperiment({
  id: generateId(),
  proposal: 'Add index on user_id column',
  result: 'success',
  metrics: { queryTime: 45, improvement: 0.82 },
  insights: 'Index reduced query time by 82%',
  timestamp: Date.now(),
  author: workerId,
});

// Worker checks dead-ends before proposing
if (await sharedContext.isDeadEnd('full-table-scan-optimization')) {
  console.log('Approach already tried and failed, skipping');
  return;
}

// Worker updates champion
await sharedContext.updateChampion({
  id: generateId(),
  score: 0.95,
  approach: 'Composite index on (user_id, created_at)',
  metrics: { queryTime: 12, improvement: 0.95 },
  timestamp: Date.now(),
  author: workerId,
});
```

---

## 5. Integration with Claude Code Teams

**Approach**: Use Claude Code's native teams feature for worker spawning.

```typescript
// packages/lyra-core/src/swarm/claude-teams-adapter.ts
export class ClaudeTeamsAdapter {
  async spawnWorker(config: WorkerConfig): Promise<WorkerHandle> {
    // Use Claude Code CLI to spawn teammate
    const process = spawn('claude', [
      'teams',
      'spawn',
      '--role', config.role,
      '--model', config.model,
      '--context', JSON.stringify(config.context),
    ]);
    
    return new WorkerHandle(process, config.id);
  }
  
  async terminateWorker(handle: WorkerHandle): Promise<void> {
    // Graceful shutdown via channel message
    await channelSystem.publish({
      channel: `worker-${handle.id}`,
      type: 'broadcast',
      payload: { command: 'shutdown' },
    });
    
    // Force kill after timeout
    setTimeout(() => handle.process.kill(), 5000);
  }
}
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

- Channel system: publish/subscribe, filtering, persistence
- Shared context: CRUD operations, concurrency, dead-end detection
- Orchestrator: task decomposition, agent spawning, result aggregation
- Worker: task execution, context access, peer communication

### 6.2 Integration Tests

- End-to-end swarm execution with 3 workers
- Adversarial validation: workers critique each other
- Shared context synchronization across workers
- Orchestrator failure recovery

### 6.3 Performance Tests

- Channel latency: <100ms for publish/subscribe
- Shared context throughput: 1000+ ops/sec
- Swarm scaling: 3-10 workers without degradation
- Memory usage: <500MB per worker

---

## 7. Security Considerations

1. **Channel isolation**: Workers can only publish to authorized channels
2. **Context access control**: Workers can only modify their own experiments
3. **Input validation**: All channel messages validated before processing
4. **Rate limiting**: Prevent workers from flooding channels
5. **Audit trail**: All channel messages and context changes logged

---

## 8. Monitoring & Observability

**Metrics**:
- Active workers count
- Channel message rate (messages/sec)
- Shared context operations (reads/writes per sec)
- Task completion rate
- Worker failure rate
- Average task duration

**Logging**:
- All channel messages (debug level)
- Shared context changes (info level)
- Worker lifecycle events (info level)
- Errors and failures (error level)

**Tracing**:
- Distributed tracing for task execution across workers
- Trace ID propagated through channel messages
- Span for each worker operation

---

## 9. Future Enhancements

1. **Dynamic team reorganization**: Workers form/dissolve teams based on progress (AutoScientists pattern)
2. **Hierarchical swarms**: Swarms of swarms for massive parallelism
3. **Cross-swarm communication**: Multiple swarms collaborate on related tasks
4. **Adaptive worker count**: Scale workers based on task complexity
5. **Persistent swarms**: Long-running swarms that survive process restarts

---

## 10. Success Criteria

- [ ] Channel system supports pub/sub with <100ms latency
- [ ] Shared context persists across agent restarts
- [ ] Orchestrator spawns 3-10 workers successfully
- [ ] Workers communicate via channels without orchestrator mediation
- [ ] Adversarial validation: workers critique proposals before execution
- [ ] Dead-end registry prevents redundant exploration
- [ ] Integration tests pass with 3-worker swarm
- [ ] Performance tests meet latency/throughput targets
- [ ] Documentation complete with examples

---

## 11. References

- AutoScientists: Decentralized coordination with shared state
- Anthropic multi-agent research: Orchestrator-worker pattern, 90.2% improvement
- AgentsMesh: Channel-based communication, control/data plane separation
- Claude Code dynamic workflows: Native teams integration

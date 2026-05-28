---
name: "system-designer"
description: System design and architecture expertise covering distributed systems, scalability, reliability, and architectural patterns. Use when designing large-scale systems, evaluating trade-offs, or solving architectural challenges.
tags: ["design", "architecture", "system-design", "scalability", "distributed-systems"]
triggers: ["system design", "architecture", "scalability", "distributed system", "design patterns"]
model: "opus"
tools: ["Read", "Write", "Edit", "Bash"]
---

# System Designer

Large-scale system design and architectural decision-making.

## Core Competencies

### 1. Distributed Systems
- CAP theorem (Consistency, Availability, Partition tolerance)
- Eventual consistency vs strong consistency
- Distributed transactions (2PC, Saga pattern)
- Consensus algorithms (Raft, Paxos)
- Service discovery and load balancing

### 2. Scalability Patterns
- Horizontal vs vertical scaling
- Database sharding and partitioning
- Caching strategies (CDN, application, database)
- Asynchronous processing (message queues)
- Read replicas and write-through caching

### 3. Reliability & Resilience
- Fault tolerance and redundancy
- Circuit breakers and retries
- Rate limiting and backpressure
- Graceful degradation
- Disaster recovery and backup strategies

### 4. Performance Optimization
- Latency vs throughput trade-offs
- Database indexing and query optimization
- Connection pooling
- Batch processing
- Content delivery networks (CDN)

### 5. Security Architecture
- Authentication and authorization
- Encryption (at rest and in transit)
- API security (rate limiting, API keys)
- Network security (VPC, security groups)
- Compliance (GDPR, HIPAA, SOC 2)

## System Design Framework

### 1. Requirements Gathering
**Functional Requirements**
- What features does the system need?
- What are the core use cases?
- What are the user flows?

**Non-Functional Requirements**
- Scale: How many users? Requests per second?
- Performance: Latency requirements? (p50, p95, p99)
- Availability: Uptime SLA? (99.9%, 99.99%)
- Consistency: Strong or eventual?
- Durability: Data retention requirements?

### 2. Capacity Estimation
```
Example: Design Twitter

Users: 500M daily active users
Tweets: 200M tweets/day = 2,300 tweets/sec
Reads: 10B timeline views/day = 115K reads/sec
Storage: 200M tweets * 280 chars * 2 bytes = 112 GB/day
Images: 50% tweets have image (5MB avg) = 500 TB/day
```

### 3. High-Level Design
- Draw system components (clients, servers, databases, caches)
- Define APIs (REST, GraphQL, gRPC)
- Identify data flow
- Choose database types (SQL, NoSQL, cache)

### 4. Detailed Design
- Database schema design
- Caching strategy
- Load balancing approach
- Replication and sharding
- Monitoring and alerting

### 5. Trade-offs & Bottlenecks
- Identify single points of failure
- Discuss consistency vs availability
- Address scalability bottlenecks
- Consider cost implications

## Common Architectural Patterns

### Microservices Architecture
```
API Gateway
    ↓
┌─────────┬─────────┬─────────┬─────────┐
│ User    │ Auth    │ Payment │ Notif   │
│ Service │ Service │ Service │ Service │
└─────────┴─────────┴─────────┴─────────┘
    ↓         ↓         ↓         ↓
┌─────────┬─────────┬─────────┬─────────┐
│ User DB │ Auth DB │ Pay DB  │ Queue   │
└─────────┴─────────┴─────────┴─────────┘
```

**Pros**: Independent deployment, technology diversity, fault isolation
**Cons**: Complexity, distributed transactions, network latency

### Event-Driven Architecture
```
Service A → Event Bus → Service B
                ↓
            Service C
```

**Pros**: Loose coupling, scalability, async processing
**Cons**: Eventual consistency, debugging complexity

### CQRS (Command Query Responsibility Segregation)
```
Write Model (Commands) → Write DB
                           ↓
                      Event Stream
                           ↓
Read Model (Queries) ← Read DB (denormalized)
```

**Pros**: Optimized reads and writes, scalability
**Cons**: Complexity, eventual consistency

### Layered Architecture
```
Presentation Layer (UI)
    ↓
Business Logic Layer (Services)
    ↓
Data Access Layer (Repositories)
    ↓
Database
```

**Pros**: Separation of concerns, testability
**Cons**: Can become monolithic, layer violations

## Scalability Patterns

### Database Scaling

**Vertical Scaling**
- Increase CPU, RAM, disk
- Limit: Hardware constraints
- Cost: Exponential

**Horizontal Scaling (Sharding)**
```
User ID 0-999     → Shard 1
User ID 1000-1999 → Shard 2
User ID 2000-2999 → Shard 3
```

**Read Replicas**
```
Primary (writes) → Replica 1 (reads)
                 → Replica 2 (reads)
                 → Replica 3 (reads)
```

### Caching Strategies

**Cache-Aside (Lazy Loading)**
```
1. Check cache
2. If miss, fetch from DB
3. Store in cache
4. Return data
```

**Write-Through**
```
1. Write to cache
2. Write to DB
3. Return success
```

**Write-Behind (Write-Back)**
```
1. Write to cache
2. Async write to DB
3. Return success immediately
```

### Load Balancing

**Algorithms**
- Round Robin: Distribute evenly
- Least Connections: Send to least busy server
- IP Hash: Same client → same server (sticky sessions)
- Weighted: Distribute based on server capacity

**Layers**
- DNS load balancing (Route 53, Cloudflare)
- L4 load balancing (TCP/UDP, AWS NLB)
- L7 load balancing (HTTP, AWS ALB, NGINX)

## Reliability Patterns

### Circuit Breaker
```
Closed → Normal operation
    ↓ (failures exceed threshold)
Open → Reject requests immediately
    ↓ (after timeout)
Half-Open → Try one request
    ↓ (success)
Closed
```

### Retry with Exponential Backoff
```
Attempt 1: Immediate
Attempt 2: Wait 1s
Attempt 3: Wait 2s
Attempt 4: Wait 4s
Attempt 5: Wait 8s
Give up after 5 attempts
```

### Rate Limiting

**Token Bucket**
```
Bucket capacity: 100 tokens
Refill rate: 10 tokens/second
Request consumes 1 token
If bucket empty, reject request
```

**Sliding Window**
```
Track requests in last N seconds
If count > limit, reject
```

## Design Examples

### URL Shortener (like bit.ly)

**Requirements**
- Shorten long URLs to 7-character codes
- Redirect short URL to original
- 100M URLs created per month
- 10:1 read:write ratio

**Design**
```
API:
  POST /shorten { url: "..." } → { short: "abc123" }
  GET /abc123 → Redirect to original URL

Database:
  Table: urls
    - id (bigint, auto-increment)
    - short_code (varchar(7), unique, indexed)
    - original_url (text)
    - created_at (timestamp)

Short Code Generation:
  Base62 encode(id) → 7 characters
  Example: id=12345 → "dnh"

Caching:
  Redis: short_code → original_url (TTL: 1 hour)
  Cache hit rate: ~90% (popular URLs)

Scaling:
  - Read replicas for redirects
  - CDN for static assets
  - Sharding by short_code hash
```

### News Feed (like Twitter/Facebook)

**Requirements**
- User posts updates
- User sees feed of posts from followed users
- 500M daily active users
- 200M posts per day

**Design**
```
Write Path (Post Creation):
  1. User creates post
  2. Store in Posts DB
  3. Fanout to followers' feeds (async)
  4. Store in Feed Cache (Redis)

Read Path (View Feed):
  1. Fetch from Feed Cache (Redis)
  2. If miss, fetch from Posts DB + merge
  3. Return paginated results

Database:
  Posts: { id, user_id, content, created_at }
  Follows: { follower_id, followee_id }
  
Feed Cache (Redis):
  Key: user:{id}:feed
  Value: List of post IDs (sorted by time)
  TTL: 1 hour

Optimization:
  - Fanout on write for users with <1M followers
  - Fanout on read for celebrities (>1M followers)
  - Hybrid approach for medium accounts
```

## Quick Reference

### CAP Theorem
```
Choose 2 of 3:
- Consistency: All nodes see same data
- Availability: Every request gets response
- Partition Tolerance: System works despite network failures

CP: Strong consistency (PostgreSQL, MongoDB)
AP: High availability (Cassandra, DynamoDB)
```

### Database Selection
```
SQL (PostgreSQL, MySQL):
  - Structured data with relationships
  - ACID transactions
  - Complex queries (JOINs)

NoSQL Document (MongoDB):
  - Flexible schema
  - Nested documents
  - Horizontal scaling

NoSQL Key-Value (Redis, DynamoDB):
  - Simple lookups
  - High throughput
  - Caching

NoSQL Wide-Column (Cassandra):
  - Time-series data
  - Write-heavy workloads
  - Multi-datacenter replication
```

### Latency Numbers
```
L1 cache:           0.5 ns
L2 cache:           7 ns
RAM:                100 ns
SSD:                150 μs
Network (same DC):  0.5 ms
Disk:               10 ms
Network (cross-DC): 150 ms
```

## When to Escalate

- Global distribution → Consider multi-region active-active
- Real-time collaboration → Consider CRDTs or Operational Transform
- Complex event processing → Consider Apache Kafka or Flink
- Machine learning at scale → Consider feature stores and model serving
- Blockchain requirements → Consider consensus mechanisms and smart contracts

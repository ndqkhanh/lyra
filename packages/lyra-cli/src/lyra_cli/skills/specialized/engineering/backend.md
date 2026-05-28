---
name: "backend-engineer"
description: Backend development expertise covering API design, database optimization, microservices, authentication, caching, and scalability. Use when building APIs, optimizing database queries, implementing authentication, or designing distributed systems.
tags: ["engineering", "backend", "api", "database", "microservices", "scalability"]
triggers: ["backend", "api", "database", "microservices", "authentication", "rest", "graphql"]
model: "sonnet"
tools: ["Read", "Write", "Edit", "Bash", "Grep"]
---

# Backend Engineer

Expert backend development guidance for scalable, secure, and maintainable systems.

## Core Competencies

### 1. API Design
- **REST**: Resource modeling, HTTP methods, status codes
- **GraphQL**: Schema design, resolvers, DataLoader
- **gRPC**: Protocol buffers, streaming, service definitions
- **WebSocket**: Real-time bidirectional communication
- **Webhooks**: Event-driven integrations

### 2. Database Expertise
- **SQL**: PostgreSQL, MySQL, query optimization, indexing
- **NoSQL**: MongoDB, Redis, DynamoDB, Cassandra
- **ORMs**: Prisma, TypeORM, SQLAlchemy, GORM
- **Migrations**: Schema versioning, zero-downtime deployments
- **Transactions**: ACID properties, isolation levels

### 3. Authentication & Authorization
- **JWT**: Token-based auth, refresh tokens
- **OAuth 2.0**: Authorization code flow, PKCE
- **RBAC**: Role-based access control
- **ABAC**: Attribute-based access control
- **Session management**: Redis-backed sessions

### 4. Caching Strategies
- **Application cache**: In-memory (Node-cache, Caffeine)
- **Distributed cache**: Redis, Memcached
- **CDN**: CloudFront, Cloudflare
- **Database cache**: Query result caching
- **HTTP cache**: ETag, Cache-Control headers

### 5. Scalability Patterns
- **Horizontal scaling**: Load balancing, stateless services
- **Vertical scaling**: Resource optimization
- **Database scaling**: Read replicas, sharding
- **Async processing**: Message queues (RabbitMQ, SQS)
- **Rate limiting**: Token bucket, sliding window

## Architecture Patterns

### Layered Architecture
```
controllers/    # HTTP handlers, request validation
services/       # Business logic, orchestration
repositories/   # Data access, query building
models/         # Domain entities, DTOs
middleware/     # Auth, logging, error handling
```

### Microservices Boundaries
```
User Service       → User management, profiles
Auth Service       → Authentication, authorization
Payment Service    → Billing, subscriptions
Notification Service → Email, SMS, push
Analytics Service  → Events, metrics, reporting
```

### Database Per Service
```
User Service    → PostgreSQL (relational user data)
Auth Service    → Redis (sessions, tokens)
Payment Service → PostgreSQL (transactions, ACID)
Analytics Service → ClickHouse (time-series events)
```

## Common Patterns

### Repository Pattern
```typescript
interface UserRepository {
  findById(id: string): Promise<User | null>
  findByEmail(email: string): Promise<User | null>
  create(data: CreateUserDTO): Promise<User>
  update(id: string, data: UpdateUserDTO): Promise<User>
  delete(id: string): Promise<void>
}

class PostgresUserRepository implements UserRepository {
  constructor(private db: Database) {}
  
  async findById(id: string): Promise<User | null> {
    return this.db.query('SELECT * FROM users WHERE id = $1', [id])
  }
  // ... other methods
}
```

### Service Layer Pattern
```typescript
class UserService {
  constructor(
    private userRepo: UserRepository,
    private emailService: EmailService,
    private eventBus: EventBus
  ) {}
  
  async createUser(data: CreateUserDTO): Promise<User> {
    // Validate
    await this.validateEmail(data.email)
    
    // Create user
    const user = await this.userRepo.create(data)
    
    // Side effects
    await this.emailService.sendWelcome(user.email)
    await this.eventBus.publish('user.created', user)
    
    return user
  }
}
```

### API Response Envelope
```typescript
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: unknown
  }
  meta?: {
    page?: number
    limit?: number
    total?: number
  }
}
```

## Workflows

### API Development Workflow
1. **Design**: Define OpenAPI/GraphQL schema
2. **Validate**: Review with frontend team
3. **Implement**: Controllers → Services → Repositories
4. **Test**: Unit tests + integration tests
5. **Document**: Generate API docs (Swagger/GraphQL Playground)
6. **Deploy**: Staging → Production with feature flags

### Database Optimization Workflow
1. **Identify**: Slow query log, APM tools
2. **Analyze**: EXPLAIN ANALYZE query plan
3. **Index**: Add indexes on filtered/joined columns
4. **Refactor**: Optimize N+1 queries, use JOINs
5. **Cache**: Add query result caching
6. **Monitor**: Track query performance over time

### Authentication Implementation
1. **Choose strategy**: JWT vs session-based
2. **Implement registration**: Hash passwords (bcrypt/argon2)
3. **Implement login**: Verify credentials, issue token
4. **Implement refresh**: Rotate tokens securely
5. **Implement logout**: Invalidate tokens/sessions
6. **Add middleware**: Protect routes, extract user context

## Tech Stack Recommendations

### Node.js Stack
```
Runtime: Node.js 20 LTS
Framework: Express or Fastify
Language: TypeScript
Database: PostgreSQL + Prisma
Cache: Redis
Queue: BullMQ
Testing: Vitest + Supertest
```

### Python Stack
```
Runtime: Python 3.11+
Framework: FastAPI
Database: PostgreSQL + SQLAlchemy
Cache: Redis
Queue: Celery + Redis
Testing: pytest + httpx
```

### Go Stack
```
Runtime: Go 1.21+
Framework: Gin or Echo
Database: PostgreSQL + sqlx
Cache: Redis (go-redis)
Queue: NATS or RabbitMQ
Testing: testify + httptest
```

## Performance Optimization

### Database Query Optimization
```sql
-- Bad: N+1 query
SELECT * FROM users;
-- Then for each user:
SELECT * FROM posts WHERE user_id = ?;

-- Good: Single query with JOIN
SELECT u.*, p.*
FROM users u
LEFT JOIN posts p ON p.user_id = u.id;

-- Better: Pagination + index
SELECT u.*, p.*
FROM users u
LEFT JOIN posts p ON p.user_id = u.id
WHERE u.created_at > $1
ORDER BY u.created_at DESC
LIMIT 20;
-- Index: CREATE INDEX idx_users_created ON users(created_at DESC);
```

### Caching Strategy
```typescript
// Cache-aside pattern
async function getUser(id: string): Promise<User> {
  // Try cache first
  const cached = await redis.get(`user:${id}`)
  if (cached) return JSON.parse(cached)
  
  // Cache miss: fetch from DB
  const user = await db.users.findById(id)
  
  // Store in cache (TTL: 1 hour)
  await redis.setex(`user:${id}`, 3600, JSON.stringify(user))
  
  return user
}
```

### Rate Limiting
```typescript
// Token bucket algorithm
const rateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // 100 requests per window
  standardHeaders: true,
  legacyHeaders: false,
})

app.use('/api/', rateLimiter)
```

## Security Best Practices

### Input Validation
```typescript
import { z } from 'zod'

const CreateUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(100),
  name: z.string().min(1).max(100),
})

app.post('/users', async (req, res) => {
  const result = CreateUserSchema.safeParse(req.body)
  if (!result.success) {
    return res.status(400).json({ error: result.error })
  }
  // ... create user
})
```

### SQL Injection Prevention
```typescript
// Bad: String concatenation
const query = `SELECT * FROM users WHERE email = '${email}'`

// Good: Parameterized query
const query = 'SELECT * FROM users WHERE email = $1'
const result = await db.query(query, [email])
```

### Password Hashing
```typescript
import bcrypt from 'bcrypt'

// Hash password (cost factor: 12)
const hash = await bcrypt.hash(password, 12)

// Verify password
const isValid = await bcrypt.compare(password, hash)
```

## Common Issues & Solutions

### Issue: N+1 Query Problem
**Symptoms**: Slow API responses, high database load
**Solution**: Use JOINs or DataLoader pattern

### Issue: Memory Leak
**Symptoms**: Increasing memory usage, eventual crash
**Solution**: Profile with `node --inspect`, check for event listener leaks

### Issue: Slow API Response
**Symptoms**: High latency, timeout errors
**Solution**: Add caching, optimize queries, use async processing

### Issue: Database Connection Pool Exhausted
**Symptoms**: "Too many connections" error
**Solution**: Tune pool size, fix connection leaks, use connection pooler (PgBouncer)

## Monitoring & Observability

### Key Metrics
- **Latency**: p50, p95, p99 response times
- **Throughput**: Requests per second
- **Error rate**: 4xx and 5xx responses
- **Database**: Query time, connection pool usage
- **Cache**: Hit rate, eviction rate

### Logging Best Practices
```typescript
import pino from 'pino'

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label }),
  },
})

// Structured logging
logger.info({ userId, action: 'login' }, 'User logged in')
logger.error({ err, userId }, 'Failed to create user')
```

## Quick Commands

```bash
# Database migrations
npx prisma migrate dev
npx prisma migrate deploy

# Run tests
npm run test
npm run test:integration

# Database query analysis
psql -d mydb -c "EXPLAIN ANALYZE SELECT ..."

# Redis CLI
redis-cli
> GET user:123
> KEYS user:*

# Load testing
npx autocannon -c 100 -d 30 http://localhost:3000/api/users

# Docker compose
docker-compose up -d postgres redis
docker-compose logs -f api
```

## When to Escalate

- Complex distributed transactions → Consider Saga pattern or event sourcing
- Real-time requirements → Consider WebSocket or Server-Sent Events
- High throughput (>10K RPS) → Consider Go or Rust
- Complex search → Consider Elasticsearch or Typesense
- Analytics workload → Consider ClickHouse or BigQuery

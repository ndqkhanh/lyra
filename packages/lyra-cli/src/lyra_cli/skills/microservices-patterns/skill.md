---
name: microservices-patterns
description: Microservices architecture patterns and best practices
origin: ECC
tags: [microservices, architecture, distributed-systems]
triggers: [microservices, service-mesh, api-gateway]
---

# Microservices Patterns

## Overview

Architectural patterns for building scalable microservices systems.

## Communication Patterns

### API Gateway

```yaml
# Kong Gateway
services:
  - name: user-service
    url: http://user-service:8080
    routes:
      - name: users
        paths:
          - /api/users
```

### Service Mesh

```yaml
# Istio VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: user-service
spec:
  hosts:
    - user-service
  http:
    - route:
        - destination:
            host: user-service
            subset: v1
          weight: 90
        - destination:
            host: user-service
            subset: v2
          weight: 10
```

## Data Patterns

### Database per Service

```
Service A → Database A
Service B → Database B
Service C → Database C
```

### Event Sourcing

```typescript
interface Event {
  type: string;
  timestamp: Date;
  data: any;
}

class UserAggregate {
  private events: Event[] = [];
  
  apply(event: Event) {
    this.events.push(event);
    this.applyEvent(event);
  }
  
  private applyEvent(event: Event) {
    switch (event.type) {
      case 'UserCreated':
        this.id = event.data.id;
        break;
      case 'UserUpdated':
        this.name = event.data.name;
        break;
    }
  }
}
```

### CQRS

```typescript
// Command side
class CreateUserCommand {
  execute(data: UserData) {
    const user = new User(data);
    this.repository.save(user);
    this.eventBus.publish(new UserCreated(user));
  }
}

// Query side
class UserQueryService {
  async getUser(id: string) {
    return this.readModel.findById(id);
  }
}
```

## Resilience Patterns

### Circuit Breaker

```typescript
class CircuitBreaker {
  private failures = 0;
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  
  async call<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      throw new Error('Circuit breaker is open');
    }
    
    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }
  
  private onFailure() {
    this.failures++;
    if (this.failures >= 5) {
      this.state = 'open';
      setTimeout(() => this.state = 'half-open', 60000);
    }
  }
  
  private onSuccess() {
    this.failures = 0;
    this.state = 'closed';
  }
}
```

### Retry with Backoff

```typescript
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries = 3
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(Math.pow(2, i) * 1000);
    }
  }
  throw new Error('Max retries exceeded');
}
```

## Best Practices

1. **Design for failure** - assume services will fail
2. **Use API gateway** for routing and auth
3. **Implement circuit breakers** for resilience
4. **Use async messaging** for loose coupling
5. **Monitor everything** - distributed tracing
6. **Automate deployment** - CI/CD pipelines
7. **Version APIs** for backward compatibility
8. **Implement health checks** for all services

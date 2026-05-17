---
name: database-patterns
description: Database design patterns and best practices
origin: ECC
tags: [database, sql, design, patterns]
triggers: [database, sql, query]
---

# Database Patterns

## Schema Design

- **Normalization**: Reduce redundancy
- **Denormalization**: Optimize for reads
- **Indexes**: Speed up queries
- **Foreign Keys**: Maintain referential integrity
- **Constraints**: Enforce data rules

## Query Optimization

- Use indexes effectively
- Avoid N+1 queries
- Use EXPLAIN to analyze
- Batch operations
- Implement pagination

## Patterns

### Repository Pattern
```python
class UserRepository:
    def find_by_id(self, user_id):
        return User.objects.get(id=user_id)
    
    def find_all(self):
        return User.objects.all()
```

### Unit of Work
- Group related operations
- Commit as single transaction
- Rollback on failure

## Best Practices

- Use parameterized queries
- Implement connection pooling
- Handle transactions properly
- Monitor query performance
- Regular backups

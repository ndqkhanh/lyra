---
name: database-engineering
description: Schema design, migration strategies, and query optimization
origin: Plan 13
tags: [database, schema, migration, optimization]
triggers: [database, schema, migration, query, index, SQL]
---

# Database Engineering

## Schema Design Principles

- **Normalize by default**: 3NF until you hit a measurable performance problem. Denormalization is a trade-off, not a goal.
- **Denormalize for reads**: When a query joins 5+ tables and is read-heavy, consider computed columns or materialized views.
- **Choose keys wisely**: Natural keys for lookup tables, surrogate keys for high-traffic transactional tables.
- **Avoid EAV (Entity-Attribute-Value)**: Use JSON columns or separate tables instead. EAV kills queryability.

## Migration Strategies

- **Expand-Contract**: Add the new schema alongside the old, dual-write, backfill, then drop the old column/table. Zero-downtime.
- **Blue-Green**: Maintain two database schemas, switch traffic atomically. Works well with feature flags.
- **Backward-compatible migrations only**: Adding columns is safe. Renaming or removing columns requires expand-contract.
- **Test rollbacks**: Every migration must have a corresponding down migration. Test it in staging.

## Query Optimization

- **EXPLAIN ANALYZE** before adding any index. Look for sequential scans on large tables.
- **Index selection**: B-tree for equality and range queries. Hash for exact lookups only. GIN/BRIN for full-text or time-series.
- **Covering indexes**: Include all columns needed by the query in the index itself. Avoids heap lookups entirely.
- **Composite index order**: Put high-cardinality columns first (most selective). Order matters for prefix matching.

## Connection Pooling

- Set `max_connections` to (app instances * pool per instance) + buffer. Oversubscribing causes queuing under load.
- Monitor `idle_in_transaction` time — stuck transactions hold connections.
- Use prepared statements with pooling to avoid repeated query planning.

## Backup Strategies

- Full daily + WAL archiving (point-in-time recovery). Test restores monthly.
- Consider `pg_dump` for logical backups, snapshots for fast recovery.
- Retention: 30 days daily, 12 monthly, 7 yearly (adjust per compliance needs).

## Partitioning Approaches

- **Range**: Time-series data by date (most common). Enables partition pruning for date-filtered queries.
- **List**: Categorical splits (region, tenant). Useful for multi-tenant isolation.
- **Hash**: Even distribution when no natural range or list fits. Good for write scaling.
- Partition before you need it — migrating data into partitions later is expensive.

---
id: query-opt
name: Query Optimization
description: Analyse and optimise database queries using EXPLAIN and index strategies.
keywords:
  - query
  - sql
  - slow query
  - explain
  - index
  - database
  - n+1
---

1. Run EXPLAIN ANALYZE on the slow query.
2. Identify: sequential scans, hash joins on large tables, missing indexes.
3. Propose indexes; estimate the improvement from the planner cost.
4. Check for N+1 patterns in application code.
5. Recommend query rewriting (subquery → JOIN, UNION → UNION ALL, etc.).

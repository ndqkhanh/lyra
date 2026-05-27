---
id: query-builder
name: Query Builder
description: Build type-safe, composable database queries with ORM or query builder patterns.
keywords:
  - query
  - query builder
  - orm
  - sqlalchemy
  - prisma
  - knex
  - drizzle
  - type safe
---

1. Use the project's query builder or ORM; avoid raw SQL unless necessary.
2. Build queries incrementally (filter → sort → paginate); never concatenate user input into SQL.
3. Select only needed columns; avoid SELECT *.
4. Eager-load associations to avoid N+1; use batch loading for collections.
5. Add query logging in development to surface slow or repeated queries.

---
id: schema-migration
name: Schema Migration
description: Write safe, reversible database schema migrations with rollback plans.
keywords:
  - schema
  - migration
  - alembic
  - flyway
  - database migration
  - ddl
  - alter table
---

1. Write the forward migration: add columns/tables with safe defaults, never drop columns first.
2. Write the reverse (downgrade) migration and test it.
3. For risky operations (column rename, type change): use an expansion-contraction pattern across two deploys.
4. Test the migration against a copy of production data.
5. Ensure migrations are idempotent and transaction-safe.

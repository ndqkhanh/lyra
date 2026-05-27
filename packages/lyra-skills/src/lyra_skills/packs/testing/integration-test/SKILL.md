---
id: integration-test
name: Integration Test
description: Write tests that verify multiple components work together correctly.
keywords:
  - integration test
  - integration testing
  - api test
  - component test
  - e2e test
---

1. Identify the integration boundary (API endpoint, database layer, service mesh).
2. Set up realistic test fixtures; prefer test containers over mocks.
3. Test the full request/response cycle including serialization and error handling.
4. Verify state changes in downstream systems (database rows, emitted events).
5. Clean up test data; ensure tests are independently repeatable.

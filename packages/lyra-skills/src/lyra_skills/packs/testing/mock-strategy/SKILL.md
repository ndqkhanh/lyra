---
id: mock-strategy
name: Mock Strategy
description: "Choose the right mocking approach: stubs, fakes, mocks, or real implementations."
keywords:
  - mock
  - mocking
  - stub
  - fake
  - test double
  - unittest mock
  - pytest mock
---

1. Classify each dependency: deterministic (pure function), external (API, DB), expensive (GPU, network).
2. Pure functions: no mock needed. External: prefer fake (in-memory DB) over mock.
3. Expensive: mock at the boundary. Shared state: use a real instance if cheap.
4. Avoid mocking types you don't own; wrap them in an adapter first.
5. If a test requires more than 3 mocks, reconsider the design.

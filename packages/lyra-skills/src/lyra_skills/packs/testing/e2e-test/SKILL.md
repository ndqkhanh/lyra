---
id: e2e-test
name: E2E Test
description: Write end-to-end tests that simulate real user journeys through the application.
keywords:
  - e2e
  - end to end
  - playwright
  - cypress
  - selenium
  - user journey
  - browser test
---

1. Identify the critical user journey (signup, purchase, search, etc.).
2. Use a browser automation framework to drive the flow.
3. Assert on visible UI state, not internal implementation details.
4. Use data-testid attributes for stable selectors; avoid CSS class selectors.
5. Run in CI; keep the suite under 10 minutes with parallelisation.

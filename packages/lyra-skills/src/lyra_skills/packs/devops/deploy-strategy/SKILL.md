---
id: deploy-strategy
name: Deploy Strategy
description: "Choose and implement a deployment strategy: rolling, blue-green, or canary."
keywords:
  - deploy
  - deployment
  - blue green
  - canary
  - rolling
  - release
  - rollback
---

1. Assess requirements: zero-downtime? gradual rollout? instant rollback?
2. Rolling: update instances one at a time. Blue-green: swap entire environments. Canary: percentage-based traffic shift.
3. Implement automated health checks that gate promotion to the next stage.
4. Define rollback triggers (error rate, latency p99, saturation) and automate the rollback.
5. Run a smoke test after deployment; monitor for 15 minutes before declaring success.

---
id: deployment-strategy
name: Deployment Strategy
description: Choose and implement deployment strategies: blue-green, canary, rolling, feature flags.
keywords:
  - deploy
  - deployment
  - blue-green
  - canary
  - rolling
  - CI/CD
  - pipeline
---

1. Assess risk: how bad is a bad deploy? User-facing? Data corruption? Revenue loss? This determines strategy.
2. For high-risk: blue-green (deploy to idle environment, switch traffic, keep old for instant rollback).
3. For moderate-risk: canary (deploy to 5% → 25% → 100% with automated health checks at each stage).
4. For low-risk: rolling (update instances one at a time, health check between each).
5. Always: deploy via CI/CD pipeline (never manual), automated rollback on health check failure, deployment logs.
6. Decouple deploy from release: use feature flags to turn features on/off independently of code deployment.
7. Post-deploy: monitor error rates, latency, and business metrics for 30 minutes minimum.

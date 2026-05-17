---
name: deployment-strategies
description: Deployment strategies and patterns
origin: ECC
tags: [deployment, devops, strategies]
triggers: [deployment, deploy, release]
---

# Deployment Strategies

## Strategies

### Blue-Green Deployment
- Two identical environments
- Switch traffic instantly
- Easy rollback
- Zero downtime

### Canary Deployment
- Gradual rollout to subset
- Monitor metrics
- Rollback if issues
- Reduced risk

### Rolling Deployment
- Update instances sequentially
- Maintain availability
- Slower rollout
- Partial rollback possible

### Feature Flags
- Deploy code, enable features separately
- A/B testing
- Gradual rollout
- Quick disable

## Best Practices

- Automate deployments
- Test in staging first
- Monitor after deployment
- Have rollback plan
- Document process

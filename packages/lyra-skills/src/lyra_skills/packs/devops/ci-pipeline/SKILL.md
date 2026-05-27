---
id: ci-pipeline
name: CI Pipeline
description: Set up or optimise a CI/CD pipeline for fast, reliable builds and deployments.
keywords:
  - ci
  - cd
  - pipeline
  - github actions
  - gitlab ci
  - jenkins
  - workflow
---

1. Define pipeline stages: lint → test → build → deploy.
2. Cache dependencies between runs; use a lockfile for deterministic installs.
3. Run tests in parallel by splitting the test suite (by file, by marker, or by timing).
4. Fail fast: run the fastest checks (lint, type-check) before slower tests.
5. Report results: test summary, coverage diff, bundle size change.

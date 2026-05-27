---
id: env-config
name: Env Config
description: Manage environment-specific configuration with validation and safe defaults.
keywords:
  - env
  - environment
  - config
  - configuration
  - .env
  - 12 factor
  - secret
---

1. Define all configuration keys in a typed schema (Pydantic, zod, etc.).
2. Validate on startup; fail immediately with a clear message if config is invalid.
3. Use different sources for secrets (vault, secrets manager) vs non-secrets (env vars, config files).
4. Never commit .env files; provide a .env.example with documented defaults.
5. Per-environment overrides: default < staging < production.

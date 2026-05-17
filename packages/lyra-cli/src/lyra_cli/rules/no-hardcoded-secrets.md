---
name: no-hardcoded-secrets
description: Never hardcode secrets in source code
category: Security
severity: critical
enabled: true
---

# No Hardcoded Secrets

Never hardcode secrets (API keys, passwords, tokens) in source code.

## Rule

- NEVER hardcode secrets in source code
- ALWAYS use environment variables or secret manager
- Validate required secrets at startup
- Rotate any exposed secrets immediately

## Rationale

Hardcoded secrets in source code can be exposed through version control, logs, or error messages.

## Examples

```python
# Wrong
API_KEY = "sk-1234567890abcdef"

# Correct
import os
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable required")
```

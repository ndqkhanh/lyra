---
id: auth-review
name: Auth Review
description: Audit authentication and authorization flows for security vulnerabilities.
keywords:
  - auth
  - authentication
  - authorization
  - oauth
  - jwt
  - session
  - login
---

1. Map all auth entry points (login, register, password reset, OAuth callback).
2. Verify: rate limiting on auth endpoints, secure session cookies (HttpOnly, Secure, SameSite).
3. Check JWT validation: algorithm pinning, expiry, signature verification.
4. Audit authorization: every endpoint checks the principal's permissions.
5. Test for: session fixation, IDOR, privilege escalation.

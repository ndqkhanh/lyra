---
id: rate-limit
name: Rate Limit
description: Implement and verify rate limiting on all public-facing endpoints.
keywords:
  - rate limit
  - rate limiting
  - throttle
  - dos
  - brute force
  - "429"
---

1. Identify endpoints needing rate limits (auth, search, API, file upload).
2. Choose a rate limit strategy: fixed window, sliding window, token bucket.
3. Set limits based on expected legitimate traffic plus headroom.
4. Return 429 with Retry-After header; log rate limit hits.
5. Test with a load generator; verify the limit kicks in and recovers.

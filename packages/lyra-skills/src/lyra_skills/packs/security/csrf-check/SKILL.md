---
id: csrf-check
name: CSRF Check
description: Verify CSRF protection is in place for all state-changing requests.
keywords:
  - csrf
  - xsrf
  - cross-site
  - forgery
  - token
  - same-origin
---

1. List all state-changing endpoints (POST, PUT, PATCH, DELETE).
2. Verify each endpoint requires a CSRF token or uses SameSite=Strict/Lax cookies.
3. Check that the token is unique per session and validated server-side.
4. Test with a cross-origin request; confirm rejection.
5. Ensure AJAX clients include the CSRF token header.

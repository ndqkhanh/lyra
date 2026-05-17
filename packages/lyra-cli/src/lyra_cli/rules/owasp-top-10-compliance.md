---
name: owasp-top-10-compliance
description: Follow OWASP Top 10 security guidelines
category: Security
severity: critical
enabled: true
---

# OWASP Top 10 Compliance

Follow OWASP Top 10 security guidelines for all code.

## Rule

Before ANY commit:
- [ ] No hardcoded secrets
- [ ] All user inputs validated
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitized HTML)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on endpoints
- [ ] Error messages don't leak sensitive data

## Rationale

OWASP Top 10 represents the most critical security risks to web applications.

## Resources

- https://owasp.org/www-project-top-ten/

---
name: code-review-checklist
description: Comprehensive code review checklist for quality and maintainability
origin: ECC
tags: [code-review, quality, checklist, best-practices]
triggers: [code-review, review, quality-check]
---

# Code Review Checklist

## Overview

A comprehensive checklist for conducting thorough code reviews that catch issues before they reach production.

## When to Use

- Before committing code
- During pull request reviews
- After implementing new features
- When refactoring existing code

## Code Quality Checks

### Readability

- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Clear, descriptive naming
- [ ] Consistent formatting

### Error Handling

- [ ] All errors handled explicitly
- [ ] User-friendly error messages
- [ ] Detailed server-side logging
- [ ] No silent error swallowing
- [ ] Proper exception types used

### Testing

- [ ] Tests exist for new functionality
- [ ] Coverage meets 80% minimum
- [ ] Tests are independent
- [ ] Tests are deterministic
- [ ] Edge cases covered

## Security Checks

- [ ] No hardcoded secrets
- [ ] All user inputs validated
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on endpoints
- [ ] Error messages don't leak sensitive data

## Performance Checks

- [ ] No N+1 queries
- [ ] Pagination implemented
- [ ] Caching where appropriate
- [ ] Efficient algorithms used
- [ ] No unnecessary computations

## Severity Levels

- **CRITICAL**: Must fix before merge
- **HIGH**: Should fix before merge
- **MEDIUM**: Consider fixing
- **LOW**: Optional improvement

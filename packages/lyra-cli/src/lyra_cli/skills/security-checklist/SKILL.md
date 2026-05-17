---
name: security-checklist
description: Security validation checklist for preventing vulnerabilities
origin: ECC
tags: [security, checklist, owasp, vulnerabilities]
triggers: [security, security-check, vulnerability]
---

# Security Checklist

## Overview

Security validation checklist based on OWASP Top 10 and common security best practices.

## When to Use

- Before any commit
- When handling user input
- When working with authentication
- When accessing databases
- When making external API calls

## OWASP Top 10 Checks

### 1. Injection

- [ ] All SQL queries use parameterized statements
- [ ] No string concatenation in queries
- [ ] Input validation on all user data
- [ ] ORM used correctly

### 2. Broken Authentication

- [ ] Strong password requirements
- [ ] Multi-factor authentication available
- [ ] Session management secure
- [ ] Password hashing (bcrypt, Argon2)
- [ ] Account lockout after failed attempts

### 3. Sensitive Data Exposure

- [ ] No secrets in code
- [ ] HTTPS enforced
- [ ] Sensitive data encrypted at rest
- [ ] Secure key management
- [ ] No sensitive data in logs

### 4. XML External Entities (XXE)

- [ ] XML parsing configured securely
- [ ] External entity processing disabled
- [ ] Input validation on XML

### 5. Broken Access Control

- [ ] Authorization checks on all endpoints
- [ ] Principle of least privilege
- [ ] No direct object references
- [ ] CORS configured properly

### 6. Security Misconfiguration

- [ ] DEBUG=False in production
- [ ] Default credentials changed
- [ ] Unnecessary features disabled
- [ ] Security headers configured
- [ ] Error messages don't leak info

### 7. Cross-Site Scripting (XSS)

- [ ] All output escaped
- [ ] Content Security Policy set
- [ ] Input sanitization
- [ ] No innerHTML with user data

### 8. Insecure Deserialization

- [ ] Deserialization from trusted sources only
- [ ] Input validation before deserialization
- [ ] Type checking on deserialized data

### 9. Using Components with Known Vulnerabilities

- [ ] Dependencies up to date
- [ ] Security scanning enabled
- [ ] No known CVEs in dependencies

### 10. Insufficient Logging & Monitoring

- [ ] Security events logged
- [ ] Failed login attempts tracked
- [ ] Anomaly detection enabled
- [ ] Audit trail maintained

## Secret Management

- [ ] No API keys in code
- [ ] No passwords in code
- [ ] No tokens in code
- [ ] Environment variables used
- [ ] Secret rotation implemented

## Input Validation

- [ ] Whitelist validation
- [ ] Type checking
- [ ] Length limits
- [ ] Format validation
- [ ] Sanitization applied

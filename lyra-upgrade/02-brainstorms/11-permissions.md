# Brainstorm: Permissions & Credentials (§4.12)

## Sources Reviewed

### Claude Code Permissions
- Permission modes (default, acceptEdits, plan, auto, dontAsk, bypassPermissions)
- Fine-grained permission rules
- Tool-specific patterns
- Hooks for permission evaluation

### Claude Code Credentials
- Environment variables
- Credential storage
- OAuth 2.0 support
- Secret management

### Security Research
- Progent (programmable least-privilege control)
- LlamaFirewall (agent guardrails)
- AgentDojo (prompt injection benchmark)
- CaMeL (control/data-flow separation)

---

## Cross-Source Breakthrough Ideas

### Idea 1: Context-Aware Dynamic Permissions
**Sources Combined**:
- Claude Code permissions (fine-grained rules)
- Progent (least-privilege control)
- SABER (mutation-gated verification)
- A-MAC (adaptive admission control)

**Mechanism**:
**Permissions that adapt based on context** rather than static rules:

**Risk-based permissions**:
```yaml
permissions:
  - tool: Bash
    risk_factors:
      - command_contains: ["rm -rf", "sudo", "curl | bash"]
        risk: HIGH
        action: require_approval
      
      - command_contains: ["git push", "npm publish"]
        risk: MEDIUM
        action: require_approval_if_cost > $5
      
      - command_contains: ["ls", "cat", "grep"]
        risk: LOW
        action: auto_approve

  - tool: Write
    risk_factors:
      - file_pattern: "*.env"
        risk: HIGH
        action: require_approval + warn_secrets
      
      - file_pattern: "src/**/*.ts"
        risk: LOW
        action: auto_approve_if_tests_pass
```

**Adaptive thresholds**:
```yaml
permissions:
  - tool: Agent
    adaptive:
      - if: session.cost < $1
        model: [haiku, sonnet, opus]  # Allow all
      
      - if: session.cost >= $1 && session.cost < $5
        model: [haiku, sonnet]  # Block opus
        notify: "Cost limit approaching, opus disabled"
      
      - if: session.cost >= $5
        model: [haiku]  # Only haiku
        notify: "Cost limit reached, only haiku available"
```

**Learning from outcomes**:
```yaml
permissions:
  - tool: Bash
    learning:
      - track: command_success_rate
      - if: command_success_rate < 0.8
        action: require_approval  # More scrutiny if failing often
      - if: command_success_rate > 0.95
        action: auto_approve  # Trust if succeeding consistently
```

**Why It Beats Individual Sources**:
- Claude Code permissions are static; this makes them **adaptive**
- Progent controls privileges; this adapts **based on context**
- SABER gates mutations; this gates **based on risk**
- A-MAC adapts memory; this adapts **permissions**

**Impact × Effort**: 5×4 = BREAKTHROUGH impact, HIGH effort

**Failure Modes**:
- Risk assessment could be wrong
- Adaptive thresholds might be too aggressive/lenient
- Learning from outcomes requires tracking
- Complexity makes debugging harder

---

### Idea 2: Credential Capability Negotiation
**Sources Combined**:
- Claude Code credentials (env vars, OAuth)
- Multi-provider router (§4.5)
- Plugin capability negotiation (§4.7)
- MCP authentication

**Mechanism**:
**Credentials that declare capabilities** and negotiate with tools:

```yaml
credentials:
  - name: github_token
    type: oauth
    scopes: [repo, read:user, write:issues]
    capabilities:
      - read_repos
      - create_issues
      - create_prs
    
  - name: openai_key
    type: api_key
    capabilities:
      - gpt-4
      - gpt-4-turbo
      - embeddings
    rate_limits:
      requests_per_minute: 60
      tokens_per_minute: 90000
    
  - name: anthropic_key
    type: api_key
    capabilities:
      - claude-opus-4
      - claude-sonnet-4
      - claude-haiku-4
    rate_limits:
      requests_per_minute: 50
      tokens_per_minute: 100000
```

**Tool requests capabilities**:
```typescript
// Tool: github-pr-creator
required_capabilities: [read_repos, create_prs]
optional_capabilities: [write:issues]

// Runtime checks credentials
if (github_token.has_capability('create_prs')) {
  // Full functionality
} else {
  // Graceful degradation: suggest PR manually
}
```

**Credential rotation**:
```yaml
credentials:
  - name: openai_key
    primary: sk-abc123
    fallback: sk-def456
    rotation:
      - if: rate_limit_exceeded
        switch_to: fallback
      - if: primary_restored
        switch_to: primary
```

**Why It Beats Individual Sources**:
- Claude Code credentials are opaque; this makes them **capability-aware**
- Multi-provider router routes models; this routes **credentials**
- Plugin negotiation is for plugins; this is for **credentials**
- MCP auth is per-server; this is **cross-tool**

**Impact × Effort**: 4×4 = HIGH impact, HIGH effort

**Failure Modes**:
- Capability detection might be inaccurate
- Credential rotation adds complexity
- Rate limit tracking requires state
- Security concerns with fallback credentials

---

### Idea 3: Zero-Trust Permission Verification
**Sources Combined**:
- Claude Code permissions (trust-based)
- Progent (least-privilege)
- SABER (verification for mutations)
- LlamaFirewall (guardrails)

**Mechanism**:
**Verify every action** rather than trusting based on rules:

**Pre-execution verification**:
```yaml
verification:
  - tool: Bash
    verify_before_execute:
      - check: command_is_safe
        method: llm_analysis
        prompt: "Is this command safe to run? {command}"
      
      - check: no_secrets_in_command
        method: regex_scan
        patterns: [api_key, password, token]
      
      - check: files_exist
        method: filesystem_check
        for: all referenced files

  - tool: Write
    verify_before_execute:
      - check: no_secrets_in_content
        method: llm_analysis + regex
      
      - check: valid_syntax
        method: language_parser
        for: code files
      
      - check: no_destructive_changes
        method: diff_analysis
        warn_if: lines_deleted > 100
```

**Post-execution verification**:
```yaml
verification:
  - tool: Bash
    verify_after_execute:
      - check: exit_code == 0
        else: rollback_if_possible
      
      - check: no_unexpected_files_created
        method: filesystem_diff
      
      - check: no_network_calls
        method: network_monitor
        unless: explicitly_allowed

  - tool: Agent
    verify_after_execute:
      - check: agent_completed_task
        method: llm_verification
        prompt: "Did the agent complete the task? {task} {result}"
      
      - check: no_hallucinations
        method: fact_check
        against: source_documents
```

**Why It Beats Individual Sources**:
- Claude Code trusts after approval; this **verifies execution**
- Progent controls privileges; this **verifies outcomes**
- SABER verifies mutations; this verifies **all actions**
- LlamaFirewall guards inputs; this guards **inputs and outputs**

**Impact × Effort**: 5×5 = BREAKTHROUGH impact, VERY HIGH effort

**Failure Modes**:
- Verification overhead (latency, cost)
- False positives block legitimate actions
- Verification logic could be wrong
- Rollback might not be possible

---

## Parked Ideas

### Idea 4: Biometric Authentication
Use fingerprint/face recognition for high-risk operations.

**Why Parked**: Platform-specific; focus on cross-platform solutions.

### Idea 5: Permission Audit Log
Detailed log of all permission decisions for compliance.

**Why Parked**: Nice-to-have but not critical for initial permission system.

### Idea 6: Permission Templates
Pre-configured permission sets for common workflows (research, coding, deployment).

**Why Parked**: Can be built on top of base permission system later.

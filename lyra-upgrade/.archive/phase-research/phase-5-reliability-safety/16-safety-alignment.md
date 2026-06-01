# §4.17 Safety & Alignment - Implementation Plan

**Status**: Planning  
**Priority**: P0 (Critical for production deployment)  
**Dependencies**: §4.16 Reliability, §4.6 Tools, §4.8 MCP  
**Estimated Effort**: 3-5 weeks

---

## 1. Overview

This plan implements comprehensive safety and alignment mechanisms for Lyra addressing:

1. **Input Safety**: Prompt injection and jailbreak detection
2. **Planning Safety**: Goal alignment and privilege control
3. **Execution Safety**: Code security and action validation
4. **Output Safety**: Content moderation and response filtering
5. **Agentic Misalignment**: Strategic reasoning and self-modification risks

**Breakthrough**: Multi-layer defense combining deterministic policy enforcement (Progent) with probabilistic detection (LlamaFirewall) and runtime guardrails (NeMo), preventing both adversarial attacks and emergent misalignment.

---

## 2. Architecture

### 2.1 Defense-in-Depth Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      User Input                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Input Safety                                       │
│  ├─ PromptGuard 2 (jailbreak detection)                     │
│  ├─ NeMo Input Rails (masking, rejection)                   │
│  └─ Content Moderation (Llama Guard)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Planning Safety                                    │
│  ├─ AlignmentCheck (goal hijacking detection)               │
│  ├─ Progent (symbolic policy enforcement)                   │
│  └─ NeMo Dialog Rails (conversation flow control)           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Execution Safety                                   │
│  ├─ CodeShield (insecure code detection)                    │
│  ├─ Privilege Validation (monotonic confinement)            │
│  ├─ Tool Output Scanning (indirect injection)               │
│  └─ NeMo Execution Rails (action governance)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Output Safety                                      │
│  ├─ Llama Guard (response classification)                   │
│  ├─ Fact Checking (hallucination detection)                 │
│  ├─ PII Filtering (sensitive data removal)                  │
│  └─ NeMo Output Rails (response validation)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Safe Response                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Safety Decision Flow

```
Action Proposed
  │
  ├─▶ Input Safety Check
  │     ├─ Jailbreak? → BLOCK
  │     ├─ Harmful content? → BLOCK
  │     └─ Pass → Continue
  │
  ├─▶ Planning Safety Check
  │     ├─ Goal misalignment? → BLOCK
  │     ├─ Policy violation? → BLOCK
  │     ├─ Privilege escalation? → REQUIRE_APPROVAL
  │     └─ Pass → Continue
  │
  ├─▶ Execution Safety Check
  │     ├─ Insecure code? → BLOCK
  │     ├─ Dangerous operation? → REQUIRE_APPROVAL
  │     ├─ Indirect injection? → BLOCK
  │     └─ Pass → Continue
  │
  ├─▶ Execute Action
  │
  └─▶ Output Safety Check
        ├─ Harmful response? → FILTER
        ├─ Hallucination? → WARN
        ├─ PII leak? → REDACT
        └─ Pass → Return
```

---

## 3. Implementation Phases

### Phase 1: Input Safety Layer (Week 1)

**Goal**: Prevent adversarial inputs from reaching the agent.

#### 1.1 PromptGuard 2 Integration

**Tasks**:
- Install LlamaFirewall with PromptGuard 2
- Configure jailbreak detection thresholds
- Implement input scanning pipeline
- Add telemetry for detection rates

**Deliverables**:
- `packages/lyra-safety/input/promptguard.ts`
- Configuration schema
- Detection metrics

**Implementation**:
```typescript
interface InputSafetyResult {
  safe: boolean;
  threats: Threat[];
  confidence: number;
  action: 'allow' | 'block' | 'sanitize';
}

class InputSafetyLayer {
  async checkInput(userInput: string): Promise<InputSafetyResult> {
    // PromptGuard 2 jailbreak detection
    const jailbreakResult = await this.promptGuard.scan(userInput);
    
    if (jailbreakResult.decision === 'BLOCK') {
      return {
        safe: false,
        threats: [{ type: 'jailbreak', severity: 'high' }],
        confidence: jailbreakResult.score,
        action: 'block'
      };
    }
    
    // Llama Guard content moderation
    const moderationResult = await this.llamaGuard.classify(userInput);
    
    if (moderationResult.unsafe) {
      return {
        safe: false,
        threats: [{ type: 'harmful_content', severity: moderationResult.severity }],
        confidence: moderationResult.confidence,
        action: 'block'
      };
    }
    
    return { safe: true, threats: [], confidence: 1.0, action: 'allow' };
  }
}
```

**Acceptance Criteria**:
- 95%+ jailbreak detection rate (AgentDojo benchmark)
- <5% false positive rate
- <50ms P95 latency
- Telemetry integrated with observability

#### 1.2 NeMo Input Rails

**Tasks**:
- Install NeMo Guardrails
- Define input rail flows in Colang
- Implement sensitive data masking
- Configure topic restrictions

**Deliverables**:
- `config/nemo-guardrails/input-rails.co`
- Masking utilities
- Topic configuration

**Colang Configuration**:
```colang
define user asks about harmful topics
  "how to hack"
  "how to make weapons"
  "illegal activities"

define flow input safety
  user ...
  
  # Check for harmful topics
  if user asks about harmful topics
    bot refuse harmful request
    stop
  
  # Mask sensitive data
  $masked_input = execute mask_sensitive_data(input=$user_message)
  
  # Continue with masked input
  bot respond to $masked_input
```

**Acceptance Criteria**:
- Harmful topics blocked with appropriate refusal
- PII masked before processing (SSN, credit cards, etc.)
- Topic restrictions configurable per deployment
- <100ms overhead per input

---

### Phase 2: Planning Safety Layer (Week 2)

**Goal**: Ensure agent plans align with user goals and security policies.

#### 2.1 AlignmentCheck Integration

**Tasks**:
- Integrate LlamaFirewall AlignmentCheck
- Implement chain-of-thought auditing
- Configure goal hijacking detection
- Add conversation trace analysis

**Deliverables**:
- `packages/lyra-safety/planning/alignment-checker.ts`
- Audit configuration
- Trace analysis utilities

**Implementation**:
```typescript
interface AlignmentCheckResult {
  aligned: boolean;
  issues: AlignmentIssue[];
  reasoning: string;
  confidence: number;
}

class PlanningAlignmentChecker {
  async checkPlan(
    plan: AgentPlan,
    userGoal: string,
    conversationTrace: Message[]
  ): Promise<AlignmentCheckResult> {
    // Run AlignmentCheck on conversation trace
    const result = await this.llamaFirewall.scan_replay(conversationTrace, {
      scanners: [ScannerType.AGENT_ALIGNMENT]
    });
    
    if (result.decision === 'BLOCK') {
      return {
        aligned: false,
        issues: this.parseIssues(result.reason),
        reasoning: result.reason,
        confidence: result.score
      };
    }
    
    // Additional goal alignment check
    const goalCheck = await this.checkGoalAlignment(plan, userGoal);
    
    return {
      aligned: goalCheck.aligned,
      issues: goalCheck.issues,
      reasoning: goalCheck.reasoning,
      confidence: goalCheck.confidence
    };
  }
}
```

**Acceptance Criteria**:
- 90%+ goal hijacking detection (AgentDojo)
- <10% false positive rate
- <200ms P95 latency
- Reasoning explanations provided

#### 2.2 Progent Symbolic Policies

**Tasks**:
- Implement symbolic security policy engine
- Define privilege rules over tool names/arguments
- Implement monotonic confinement (narrowing vs. expansion)
- Add SMT solver for policy classification

**Deliverables**:
- `packages/lyra-safety/planning/policy-engine.ts`
- Policy DSL and parser
- SMT solver integration

**Implementation**:
```typescript
interface SecurityPolicy {
  rules: PolicyRule[];
  version: number;
  lastUpdated: Date;
}

interface PolicyRule {
  toolName: string;
  allowedArguments?: Record<string, any>;
  conditions?: Condition[];
  action: 'allow' | 'deny' | 'require_approval';
}

class SymbolicPolicyEngine {
  async validateAction(
    action: AgentAction,
    currentPolicy: SecurityPolicy
  ): Promise<PolicyValidationResult> {
    // Check if action matches any rule
    const matchingRules = this.findMatchingRules(action, currentPolicy);
    
    if (matchingRules.length === 0) {
      // No explicit rule - default deny
      return { allowed: false, reason: 'No matching policy rule' };
    }
    
    // Evaluate conditions
    for (const rule of matchingRules) {
      if (rule.action === 'deny') {
        return { allowed: false, reason: `Denied by rule: ${rule.toolName}` };
      }
      
      if (rule.action === 'require_approval') {
        return { allowed: false, requiresApproval: true, reason: 'Requires human approval' };
      }
    }
    
    return { allowed: true };
  }
  
  async updatePolicy(
    currentPolicy: SecurityPolicy,
    proposedUpdate: PolicyUpdate
  ): Promise<PolicyUpdateResult> {
    // Classify update as narrowing or expansion
    const classification = await this.smtSolver.classify(
      currentPolicy,
      proposedUpdate
    );
    
    if (classification === 'narrowing') {
      // Auto-apply narrowing updates
      return {
        applied: true,
        newPolicy: this.applyUpdate(currentPolicy, proposedUpdate),
        requiresApproval: false
      };
    } else {
      // Expansion requires approval
      return {
        applied: false,
        requiresApproval: true,
        reason: 'Policy expansion requires human approval'
      };
    }
  }
}
```

**Acceptance Criteria**:
- Deterministic policy enforcement (no probabilistic failures)
- Monotonic confinement prevents silent privilege escalation
- Policy updates classified correctly (narrowing vs. expansion)
- <10ms validation latency

---

### Phase 3: Execution Safety Layer (Week 3)

**Goal**: Prevent execution of dangerous or insecure operations.

#### 3.1 CodeShield Integration

**Tasks**:
- Integrate LlamaFirewall CodeShield
- Configure Semgrep rules for 8 languages
- Add custom security patterns
- Implement code scanning pipeline

**Deliverables**:
- `packages/lyra-safety/execution/codeshield.ts`
- Custom Semgrep rules
- Language-specific configurations

**Implementation**:
```typescript
interface CodeSafetyResult {
  safe: boolean;
  vulnerabilities: Vulnerability[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  action: 'allow' | 'block' | 'warn';
}

class CodeShieldScanner {
  async scanCode(
    code: string,
    language: string
  ): Promise<CodeSafetyResult> {
    // Run CodeShield static analysis
    const result = await this.llamaFirewall.scan(code, {
      scanners: [ScannerType.CODE_SHIELD],
      language
    });
    
    if (result.decision === 'BLOCK') {
      return {
        safe: false,
        vulnerabilities: this.parseVulnerabilities(result.reason),
        severity: this.getSeverity(result.score),
        action: 'block'
      };
    }
    
    // Additional custom pattern checks
    const customChecks = await this.runCustomPatterns(code, language);
    
    return {
      safe: customChecks.safe,
      vulnerabilities: customChecks.vulnerabilities,
      severity: customChecks.severity,
      action: customChecks.action
    };
  }
}
```

**Acceptance Criteria**:
- Zero critical vulnerabilities in generated code
- 95%+ detection of OWASP Top 10 patterns
- <500ms scanning latency
- Support for TypeScript, Python, JavaScript, Go, Rust, Java, C++, C#

#### 3.2 Tool Output Scanning

**Tasks**:
- Implement indirect prompt injection detection
- Scan tool outputs for adversarial instructions
- Add pattern matching for common injection vectors
- Configure severity-based responses

**Deliverables**:
- `packages/lyra-safety/execution/tool-output-scanner.ts`
- Injection pattern library
- Response configuration

**Implementation**:
```typescript
class ToolOutputScanner {
  async scanOutput(
    toolName: string,
    output: any
  ): Promise<OutputSafetyResult> {
    // Convert output to scannable text
    const text = this.extractText(output);
    
    // Check for indirect injection patterns
    const injectionCheck = await this.adversarialChecker.checkForInjection(text);
    
    if (injectionCheck.detected) {
      return {
        safe: false,
        threat: 'indirect_injection',
        severity: injectionCheck.severity,
        action: 'block',
        sanitized: this.sanitizeOutput(output, injectionCheck.matches)
      };
    }
    
    return { safe: true, action: 'allow' };
  }
}
```

**Acceptance Criteria**:
- 90%+ indirect injection detection (AgentDojo)
- <100ms scanning latency
- Sanitization preserves legitimate content
- Configurable severity thresholds

---

### Phase 4: Output Safety Layer (Week 4)

**Goal**: Ensure agent responses are safe, accurate, and appropriate.

#### 4.1 Llama Guard Response Classification

**Tasks**:
- Integrate Llama Guard for response moderation
- Configure safety taxonomy
- Implement response filtering
- Add telemetry for moderation decisions

**Deliverables**:
- `packages/lyra-safety/output/response-moderator.ts`
- Safety taxonomy configuration
- Filtering utilities

**Implementation**:
```typescript
class ResponseModerator {
  async moderateResponse(
    response: string,
    context: ConversationContext
  ): Promise<ModerationResult> {
    // Classify response with Llama Guard
    const result = await this.llamaGuard.classifyResponse(response, context);
    
    if (result.unsafe) {
      return {
        safe: false,
        categories: result.violatedCategories,
        action: 'filter',
        filtered: this.filterResponse(response, result.categories)
      };
    }
    
    return { safe: true, action: 'allow', original: response };
  }
}
```

**Acceptance Criteria**:
- Matches OpenAI Moderation API performance
- <100ms classification latency
- Configurable taxonomy per deployment
- Filtered responses maintain coherence

#### 4.2 Hallucination Detection

**Tasks**:
- Implement fact-checking pipeline
- Add source attribution validation
- Configure confidence thresholds
- Implement warning injection for low-confidence responses

**Deliverables**:
- `packages/lyra-safety/output/hallucination-detector.ts`
- Fact-checking configuration
- Warning templates

**Implementation**:
```typescript
class HallucinationDetector {
  async checkResponse(
    response: string,
    sources: Source[]
  ): Promise<HallucinationCheckResult> {
    // Extract factual claims
    const claims = await this.extractClaims(response);
    
    // Verify against sources
    const verifications = await Promise.all(
      claims.map(claim => this.verifyClaim(claim, sources))
    );
    
    const unverifiedClaims = verifications.filter(v => !v.verified);
    
    if (unverifiedClaims.length > 0) {
      return {
        hasHallucinations: true,
        unverifiedClaims,
        confidence: this.calculateConfidence(verifications),
        action: 'warn',
        warning: this.generateWarning(unverifiedClaims)
      };
    }
    
    return { hasHallucinations: false, confidence: 1.0, action: 'allow' };
  }
}
```

**Acceptance Criteria**:
- 85%+ hallucination detection accuracy
- <500ms checking latency
- Warnings injected for low-confidence responses
- Source attribution validated

---

### Phase 5: Agentic Misalignment Defense (Week 5)

**Goal**: Prevent strategic misalignment and self-modification risks.

#### 5.1 Immutable Safety Constraints

**Tasks**:
- Define core safety constraints that cannot be modified
- Implement constraint validation at runtime
- Add tamper detection for constraint violations
- Configure rollback mechanisms

**Deliverables**:
- `packages/lyra-safety/alignment/immutable-constraints.ts`
- Constraint schema
- Validation utilities
- Rollback mechanisms

**Implementation**:
```typescript
interface ImmutableConstraint {
  id: string;
  description: string;
  validator: (state: AgentState) => boolean;
  severity: 'critical' | 'high';
}

class ImmutableConstraintEnforcer {
  private constraints: ImmutableConstraint[] = [
    {
      id: 'no_self_modification',
      description: 'Agent cannot modify its own core code',
      validator: (state) => !state.actions.some(a => a.modifiesCoreCode),
      severity: 'critical'
    },
    {
      id: 'human_oversight_required',
      description: 'Irreversible actions require human approval',
      validator: (state) => state.irreversibleActions.every(a => a.approved),
      severity: 'critical'
    },
    {
      id: 'goal_alignment',
      description: 'Agent goals must align with user goals',
      validator: (state) => this.checkGoalAlignment(state),
      severity: 'high'
    }
  ];
  
  async enforceConstraints(state: AgentState): Promise<ConstraintCheckResult> {
    const violations: ConstraintViolation[] = [];
    
    for (const constraint of this.constraints) {
      if (!constraint.validator(state)) {
        violations.push({
          constraintId: constraint.id,
          description: constraint.description,
          severity: constraint.severity
        });
      }
    }
    
    if (violations.some(v => v.severity === 'critical')) {
      // Critical violation - halt execution and rollback
      await this.rollback(state);
      return { passed: false, violations, action: 'halt' };
    }
    
    return { passed: violations.length === 0, violations };
  }
}
```

**Acceptance Criteria**:
- Core constraints cannot be bypassed
- Tamper detection triggers immediate halt
- Rollback restores safe state
- Violations logged and alerted

#### 5.2 Self-Modification Safeguards

**Tasks**:
- Implement sandboxed testing for code changes
- Add multi-stage approval for self-modifications
- Configure behavioral testing suite
- Implement version control and rollback

**Deliverables**:
- `packages/lyra-safety/alignment/self-modification-guard.ts`
- Sandbox environment
- Approval workflow
- Behavioral test suite

**Implementation**:
```typescript
class SelfModificationGuard {
  async validateModification(
    proposedCode: string,
    modifiedComponent: string
  ): Promise<ModificationValidationResult> {
    // Stage 1: Static analysis
    const staticCheck = await this.codeShield.scan(proposedCode);
    if (!staticCheck.safe) {
      return { approved: false, reason: 'Failed static analysis', stage: 1 };
    }
    
    // Stage 2: Sandboxed testing
    const sandboxResult = await this.runInSandbox(proposedCode);
    if (!sandboxResult.passed) {
      return { approved: false, reason: 'Failed sandbox tests', stage: 2 };
    }
    
    // Stage 3: Behavioral testing
    const behavioralResult = await this.runBehavioralTests(proposedCode);
    if (!behavioralResult.passed) {
      return { approved: false, reason: 'Failed behavioral tests', stage: 3 };
    }
    
    // Stage 4: Human approval for critical components
    if (this.isCriticalComponent(modifiedComponent)) {
      return {
        approved: false,
        requiresHumanApproval: true,
        reason: 'Critical component modification requires human approval',
        stage: 4
      };
    }
    
    return { approved: true, stage: 4 };
  }
}
```

**Acceptance Criteria**:
- All self-modifications pass 4-stage validation
- Critical components require human approval
- Sandbox prevents unsafe code execution
- Behavioral tests detect alignment drift

---

## 4. NeMo Guardrails Integration

### 4.1 Colang Flow Definitions

**Complete Safety Flow**:
```colang
# Input safety
define flow input_safety
  user ...
  
  # Jailbreak detection
  $jailbreak_check = execute check_jailbreak(input=$user_message)
  if $jailbreak_check.detected
    bot refuse jailbreak attempt
    stop
  
  # Content moderation
  $moderation_check = execute moderate_input(input=$user_message)
  if $moderation_check.unsafe
    bot refuse harmful content
    stop
  
  # Mask sensitive data
  $masked_input = execute mask_sensitive_data(input=$user_message)
  continue with $masked_input

# Planning safety
define flow planning_safety
  bot plans action
  
  # Alignment check
  $alignment_check = execute check_alignment(
    plan=$bot_plan,
    user_goal=$user_goal,
    trace=$conversation_trace
  )
  if not $alignment_check.aligned
    bot request clarification
    stop
  
  # Policy validation
  $policy_check = execute validate_policy(
    action=$bot_plan.action,
    policy=$current_policy
  )
  if not $policy_check.allowed
    if $policy_check.requires_approval
      bot request human approval
      wait for approval
    else
      bot refuse policy violation
      stop

# Execution safety
define flow execution_safety
  bot executes action
  
  # Code safety (if applicable)
  if $action.type == "code_generation"
    $code_check = execute scan_code(
      code=$action.code,
      language=$action.language
    )
    if not $code_check.safe
      bot refuse insecure code
      stop
  
  # Tool output scanning
  $output = execute tool($action.tool_name, $action.arguments)
  $output_check = execute scan_tool_output(
    tool=$action.tool_name,
    output=$output
  )
  if not $output_check.safe
    bot warn about suspicious output
    $output = $output_check.sanitized

# Output safety
define flow output_safety
  bot responds
  
  # Response moderation
  $moderation_check = execute moderate_response(
    response=$bot_response,
    context=$conversation_context
  )
  if not $moderation_check.safe
    $bot_response = $moderation_check.filtered
  
  # Hallucination detection
  $hallucination_check = execute check_hallucinations(
    response=$bot_response,
    sources=$sources
  )
  if $hallucination_check.has_hallucinations
    bot add warning($hallucination_check.warning)
  
  # PII filtering
  $bot_response = execute filter_pii($bot_response)
  
  return $bot_response
```

### 4.2 Configuration

```yaml
# config/nemo-guardrails/config.yml
models:
  - type: main
    engine: anthropic
    model: claude-opus-4-8

rails:
  input:
    flows:
      - input_safety
  
  dialog:
    flows:
      - planning_safety
  
  execution:
    flows:
      - execution_safety
  
  output:
    flows:
      - output_safety

actions:
  - name: check_jailbreak
    module: lyra_safety.input.promptguard
  - name: moderate_input
    module: lyra_safety.input.llama_guard
  - name: check_alignment
    module: lyra_safety.planning.alignment_checker
  - name: validate_policy
    module: lyra_safety.planning.policy_engine
  - name: scan_code
    module: lyra_safety.execution.codeshield
  - name: scan_tool_output
    module: lyra_safety.execution.tool_output_scanner
  - name: moderate_response
    module: lyra_safety.output.response_moderator
  - name: check_hallucinations
    module: lyra_safety.output.hallucination_detector
```

---

## 5. Testing Strategy

### 5.1 Adversarial Testing

**AgentDojo Benchmark**:
- 97 realistic tasks
- 629 security test cases
- Prompt injection attacks
- Goal hijacking scenarios

**Target Metrics**:
- Task utility: >75% (vs. 84% undefended)
- Security: 95%+ attack detection
- False positive rate: <5%

### 5.2 Misalignment Testing

**Anthropic Scenarios**:
- Threat to autonomy (replacement scenarios)
- Goal conflicts (company vs. agent objectives)
- Strategic reasoning tests

**Target Metrics**:
- Zero harmful behaviors (blackmail, espionage, lethal action)
- 100% human oversight for irreversible actions
- Goal alignment maintained across scenarios

### 5.3 Self-Modification Testing

**Validation Suite**:
- Static analysis (CodeShield)
- Sandboxed execution
- Behavioral testing
- Alignment drift detection

**Target Metrics**:
- Zero critical vulnerabilities in self-generated code
- 100% sandbox containment
- Behavioral tests detect 95%+ alignment drift

---

## 6. Performance Targets

| Layer | Latency Target | Throughput |
|-------|----------------|------------|
| Input Safety | <100ms P95 | 1000 req/s |
| Planning Safety | <200ms P95 | 500 req/s |
| Execution Safety | <500ms P95 | 200 req/s |
| Output Safety | <200ms P95 | 500 req/s |
| End-to-End | <1s P95 | 100 req/s |

---

## 7. Success Metrics

### 7.1 Security Metrics

- **Jailbreak detection**: 95%+ detection, <5% FP
- **Prompt injection**: 90%+ detection, <10% FP
- **Goal hijacking**: 90%+ detection, <10% FP
- **Code vulnerabilities**: Zero critical in production

### 7.2 Alignment Metrics

- **Goal alignment**: 95%+ alignment with user intent
- **Policy compliance**: 100% enforcement of security policies
- **Privilege escalation**: Zero unauthorized escalations
- **Self-modification**: 100% validation pass rate

### 7.3 Operational Metrics

- **False positive rate**: <5% across all layers
- **Human review rate**: <2% of actions
- **Latency overhead**: <20% vs. undefended
- **Availability**: 99.9% uptime

---

## 8. Rollout Plan

### Week 1: Input Safety
- Deploy PromptGuard 2 in shadow mode
- Enable Llama Guard content moderation
- Configure NeMo input rails
- Validate detection rates

### Week 2: Planning Safety
- Deploy AlignmentCheck in shadow mode
- Enable Progent policy engine
- Configure NeMo dialog rails
- Tune thresholds

### Week 3: Execution Safety
- Deploy CodeShield for code generation
- Enable tool output scanning
- Configure NeMo execution rails
- Validate vulnerability detection

### Week 4: Output Safety
- Deploy response moderation
- Enable hallucination detection
- Configure NeMo output rails
- Validate filtering quality

### Week 5: Agentic Misalignment
- Deploy immutable constraints
- Enable self-modification guards
- Run misalignment test suite
- Validate rollback mechanisms

---

## 9. Monitoring & Alerting

### 9.1 Security Dashboards

- **Threat Detection**: Counts by type/severity, trends
- **Policy Violations**: Violation types, enforcement actions
- **False Positives**: Rate trends, user feedback
- **Attack Patterns**: New patterns, evolution tracking

### 9.2 Alerts

- **Critical**: Jailbreak detected, policy violation, alignment drift
- **High**: Code vulnerability, goal hijacking, privilege escalation
- **Medium**: High false positive rate, latency degradation
- **Low**: New attack patterns, configuration drift

---

## 10. Documentation

- Safety architecture overview
- Threat model and attack vectors
- Configuration guide for all layers
- Colang flow reference
- Incident response playbook
- Compliance mapping (SOC2, GDPR, etc.)

---

**End of §4.17 Safety & Alignment Plan**
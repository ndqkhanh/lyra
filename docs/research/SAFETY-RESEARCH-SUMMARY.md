# Safety & Alignment Research Summary (§3.16)

**Research Date**: 2026-05-31  
**Sources Researched**: 12/12 (100% complete)  
**Status**: All sources from source-ledger rows 236-247 researched and documented

---

## Executive Summary

Researched 12 production-ready safety systems and academic papers addressing agent security threats. Key findings:

**5 BREAKTHROUGH-tier patterns** for immediate adoption:
1. **Multi-layer defense architecture** (LlamaFirewall, NeMo Guardrails)
2. **Privilege control with monotonic confinement** (ProgEnt)
3. **Control/data plane separation** (CaMeL)
4. **Adversarial testing framework** (AgentDojo)
5. **Self-evolution safety monitoring**

**Critical insight**: No single defense suffices. Production agent safety requires layered approaches combining:
- Input/output validation
- Privilege control with formal verification
- Architectural separation of trusted control flow from untrusted data
- Continuous adversarial testing
- Real-time reasoning inspection

---

## Key Threats Addressed

### 1. Prompt Injection Attacks
**Sources**: AgentDojo, CaMeL, ProgEnt, LlamaFirewall

**Attack Vector**: Malicious instructions embedded in external data (tool outputs, file contents, web results) hijack agent behavior to execute unintended actions.

**Defense Patterns**:
- **Control/data separation** (CaMeL): User queries = trusted control, external content = untrusted data that cannot alter execution paths. 77% task success with provable security vs 84% undefended (7pp tradeoff).
- **Privilege control** (ProgEnt): Symbolic policies with SMT solver verification. LLM proposes updates, formal verifier classifies as narrowing (auto-apply) or expansion (requires approval). Significantly reduces attack success on AgentDojo/ASB benchmarks.
- **Multi-property testing** (AgentDojo): 97 realistic tasks, 629 security test cases. SOTA LLMs fail many tasks even without attacks.

### 2. Goal Hijacking & Misalignment
**Sources**: LlamaFirewall, Self-Evolving Agent Safety

**Attack Vector**: Subtle misalignment over multi-turn interactions where agent reasoning diverges from user intent.

**Defense Patterns**:
- **Reasoning inspection** (LlamaFirewall AlignmentCheck): Chain-of-thought auditor inspects agent reasoning in real-time. Stronger indirect injection prevention than prior approaches (experimental).
- **Trace-level analysis**: Analyze conversation sequences, not just individual messages, to detect emergent threats.
- **Self-evolution monitoring**: Track alignment metrics across autonomous improvement cycles. Safety degradation observed on HarmBench/SALAD-Bench when agents fine-tune on self-generated data.

### 3. Insecure Code Generation
**Sources**: LlamaFirewall CodeShield

**Attack Vector**: LLM-generated code contains vulnerabilities, exploits, or malicious logic.

**Defense Patterns**:
- **Static analysis** (CodeShield): Semgrep + regex rules across 8 languages. Fast, extensible, production-ready.
- **Pre-execution validation**: Scan generated code before execution.

### 4. Jailbreaks & Direct Attacks
**Sources**: PromptGuard 2, Llama Guard, NeMo Guardrails

**Attack Vector**: Direct attempts to bypass safety controls through adversarial prompts.

**Defense Patterns**:
- **Lightweight ML detection** (PromptGuard 2): BERT-based classifier, SOTA performance, low latency for synchronous filtering.
- **Dual-stage classification** (Llama Guard): Classify both inputs and outputs. Taxonomy-driven risk categorization. Matches/exceeds current moderation tools on OpenAI Moderation Evaluation and ToxicChat.
- **Programmable guardrails** (NeMo Guardrails): Five-layer protection (input, dialog, retrieval, execution, output rails). Colang DSL for safety rules. Model-agnostic.

---

## Production-Ready Systems

### Tier 1: Immediate Adoption (High Impact, Proven)

#### 1. LlamaFirewall (Meta)
- **Repo**: https://github.com/meta-llama/PurpleLlama/tree/main/LlamaFirewall
- **Components**: PromptGuard 2 (jailbreak), AlignmentCheck (misalignment), CodeShield (insecure code)
- **Architecture**: Modular policy engine with role-based scanners
- **Key Feature**: Trace-level analysis across conversation history
- **Status**: Production-ready, AlignmentCheck experimental
- **Impact**: 5 | **Effort**: 4 | **Tier**: BREAKTHROUGH

#### 2. ProgEnt (UC Berkeley)
- **Repo**: https://github.com/sunblaze-ucb/progent
- **Paper**: https://arxiv.org/abs/2504.11703
- **Mechanism**: Symbolic security policies with SMT solver verification
- **Key Feature**: Monotonic confinement prevents silent privilege escalation
- **Validation**: LangChain, OpenAI Agents SDK
- **Benchmarks**: Significantly reduces attack success on AgentDojo/ASB
- **Impact**: 5 | **Effort**: 4 | **Tier**: BREAKTHROUGH

#### 3. NeMo Guardrails (NVIDIA)
- **Repo**: https://github.com/NVIDIA-NeMo/Guardrails
- **Paper**: https://arxiv.org/abs/2310.10501 (EMNLP 2023 Demo)
- **Architecture**: Five-layer rails (input, dialog, retrieval, execution, output)
- **Key Feature**: Colang DSL for declarative safety rules
- **Status**: Production-ready, async-first design
- **Impact**: 4 | **Effort**: 3 | **Tier**: HIGH

### Tier 2: Research Prototypes (High Potential)

#### 4. CaMeL (Google Research)
- **Repo**: https://github.com/google-research/camel-prompt-injection
- **Paper**: https://arxiv.org/abs/2503.18813
- **Mechanism**: Control/data flow separation with capability-based access control
- **Benchmark**: 77% task success with provable security vs 84% undefended (AgentDojo)
- **Status**: Research artifact, "likely contains bugs", not production-ready
- **Impact**: 5 | **Effort**: 4 | **Tier**: BREAKTHROUGH (concept)

#### 5. AgentDojo (ETH Zurich)
- **Repo**: https://github.com/ethz-spylab/agentdojo
- **Paper**: https://arxiv.org/abs/2406.13352 (NeurIPS 2024)
- **Purpose**: Evaluation framework, not defense system
- **Coverage**: 97 tasks, 629 security test cases
- **Key Finding**: SOTA LLMs fail many tasks even without attacks
- **Impact**: 5 | **Effort**: 3 | **Tier**: BREAKTHROUGH (testing)

---

## Transferable Patterns for Lyra §4.17

### Pattern 1: Multi-Layer Defense Architecture
**Sources**: LlamaFirewall, NeMo Guardrails

```typescript
interface SafetyLayer {
  inputRails: InputValidator[];      // Validate user prompts
  executionRails: PrivilegeControl;  // Secure tool invocation
  outputRails: OutputValidator[];    // Validate agent responses
  reasoningRails: AlignmentCheck[];  // Audit chain-of-thought
}
```

**Implementation**:
- Composable scanner pipeline
- Role-based filtering (user/assistant/tool)
- Trace-level analysis across multi-turn conversations
- Workflow-specific risk profiles

### Pattern 2: Privilege Control with Monotonic Confinement
**Source**: ProgEnt

**Mechanism**:
1. Start with least privilege
2. LLM proposes policy updates
3. SMT solver classifies as narrowing (auto-apply) or expansion (requires approval)
4. Symbolic policies over tool names and arguments
5. State-aware adaptation during execution

**Key Insight**: Deterministic enforcement independent of LLM behavior. Non-probabilistic security checks.

### Pattern 3: Control/Data Plane Separation
**Source**: CaMeL

**Architecture**:
- User queries = trusted control flow
- External content (tool outputs, file reads, web results) = untrusted data
- Untrusted data cannot alter execution paths
- Capability-based access control for tool invocations
- Provable security boundaries

**Implementation**: Explicit flow extraction with capability gates

### Pattern 4: Adversarial Testing Framework
**Source**: AgentDojo

**Components**:
- 97 realistic tasks across domains
- 629 security test cases
- Multi-property evaluation: task utility + security resistance
- Extensible for new attack vectors

**Integration**: Continuous security testing in CI/CD pipeline

### Pattern 5: Dual-Stage Classification
**Source**: Llama Guard

**Mechanism**:
- Classify both inputs (user prompts) and outputs (agent responses)
- Taxonomy-driven risk categorization
- Multi-class classification for granular risk levels
- Customizable taxonomies per use case

**Implementation**: LLM-based classifier (Llama2-7b fine-tuned)

### Pattern 6: Trace-Level Pattern Detection
**Source**: LlamaFirewall

**Mechanism**:
- Analyze conversation sequences, not just individual messages
- Detect emergent threats across multi-turn interactions
- Goal hijacking detection through reasoning inspection

**Implementation**: Stateful scanner with conversation history analysis

### Pattern 7: Self-Evolution Safety Monitoring
**Source**: Self-Evolving Agent Safety paper

**Mechanism**:
- Track alignment metrics across autonomous improvement cycles
- Sandbox and validate agent-generated training data
- Alignment preservation constraints during self-modification
- Reversibility mechanisms for rollback when degradation detected

**Key Finding**: Fine-tuning on agent-generated data compromises alignment even from aligned base models (Llama 3, Qwen 2.5 tested).

---

## Priority Implementation Order for Lyra

### P0: Core Guardrails (Immediate)
1. **Control/data separation** (CaMeL pattern)
   - Separate trusted control flow from untrusted external data
   - Capability-based tool access control
   - Effort: 4 weeks

2. **Privilege control** (ProgEnt pattern)
   - Symbolic policies with SMT solver verification
   - Monotonic confinement for privilege escalation prevention
   - Effort: 4 weeks

### P1: Input/Output Validation (Next Sprint)
3. **Input/output rails** (Llama Guard pattern)
   - Dual-stage classification
   - Taxonomy-driven risk categorization
   - Effort: 3 weeks

4. **Jailbreak detection** (PromptGuard 2)
   - Lightweight BERT-based classifier
   - Low-latency synchronous filtering
   - Effort: 2 weeks

### P2: Testing Infrastructure (Month 2)
5. **Security test suite** (AgentDojo pattern)
   - Realistic task scenarios
   - Multi-property evaluation
   - CI/CD integration
   - Effort: 3 weeks

### P3: Advanced Mechanisms (Month 3)
6. **Trace-level analysis** (LlamaFirewall pattern)
   - Multi-turn conversation monitoring
   - Goal hijacking detection
   - Effort: 3 weeks

7. **Code generation safety** (CodeShield)
   - Static analysis for generated code
   - Pre-execution validation
   - Effort: 2 weeks

### P4: Future (If/When Self-Improvement Added)
8. **Self-evolution monitoring**
   - Alignment metrics tracking
   - Training data sandboxing
   - Rollback mechanisms
   - Effort: 4 weeks

---

## Key Insights

### 1. No Single Defense Suffices
All sources emphasize defense-in-depth. AgentDojo shows "no single defense/attack dominates across all scenarios."

### 2. Architectural Solutions > Prompt Engineering
CaMeL demonstrates provable security through architectural separation. ProgEnt uses formal verification (SMT solver) for deterministic enforcement.

### 3. External Data is Adversarial
Treat all tool outputs, file contents, web results as potentially adversarial. NeMo Guardrails explicitly guards against "instructions directed at you" embedded in data.

### 4. Baseline Task Performance is Challenging
AgentDojo: "SOTA LLMs fail at many tasks even without attacks." Security measures must preserve utility.

### 5. Self-Evolution Introduces New Risks
Fine-tuning on agent-generated data can compromise alignment. Requires explicit monitoring and sandboxing.

### 6. Probabilistic vs Deterministic Protection
- Probabilistic: LLM-based classifiers (Llama Guard, PromptGuard 2)
- Deterministic: Formal verification (ProgEnt SMT solver), architectural separation (CaMeL)
- Both needed: Probabilistic for nuanced detection, deterministic for guaranteed enforcement

### 7. Real-Time Reasoning Inspection
LlamaFirewall AlignmentCheck audits chain-of-thought in real-time. Catches misalignment before action execution.

---

## Benchmarks & Metrics

| System | Benchmark | Result | Tradeoff |
|--------|-----------|--------|----------|
| CaMeL | AgentDojo | 77% task success with provable security | 7pp vs 84% undefended |
| ProgEnt | AgentDojo, ASB | Significantly reduces attack success | Maintains high utility |
| Llama Guard | OpenAI Moderation, ToxicChat | Matches/exceeds current tools | Low-volume training data |
| AgentDojo | 97 tasks, 629 tests | SOTA LLMs fail many tasks | Baseline challenging |

---

## Limitations & Gaps

### Production Readiness
- **CaMeL**: Research prototype, "likely contains bugs"
- **LlamaFirewall AlignmentCheck**: Experimental
- **NeMo Guardrails**: No quantitative benchmarks (demo paper)

### Performance Overhead
- Multi-scanner orchestration (LlamaFirewall)
- SMT solver checking (ProgEnt)
- Computational cost not quantified for most systems

### Coverage Gaps
- AgentDojo: "Current attacks don't comprehensively break all properties"
- Continuous evolution required as attack vectors advance

### Evaluation Challenges
- Self-evolving agent safety: "Requires manual testing for full validation"
- WCAG compliance: "Full validation requires manual testing with assistive technologies"

---

## Recommended Reading Order

1. **Start**: AgentDojo paper (threat landscape overview)
2. **Architecture**: CaMeL paper (control/data separation)
3. **Enforcement**: ProgEnt paper (privilege control)
4. **Detection**: LlamaFirewall repo (multi-layer defense)
5. **Testing**: AgentDojo repo (evaluation framework)
6. **Classification**: Llama Guard paper (input/output validation)

---

## Source Coverage

**§3.16 Safety / Alignment / Agent Security**: 12/12 sources researched (100%)

| Row | Source | Status | Tier |
|-----|--------|--------|------|
| 236 | LlamaFirewall | read | BREAKTHROUGH |
| 237 | PromptGuard 2 Paper | read | HIGH |
| 238 | Llama Guard | read | HIGH |
| 239 | NeMo Guardrails | read | HIGH |
| 240 | NeMo Guardrails Paper | read | MEDIUM |
| 241 | AgentDojo | read | BREAKTHROUGH |
| 242 | AgentDojo Paper | read | BREAKTHROUGH |
| 243 | CaMeL | read | BREAKTHROUGH |
| 244 | CaMeL Paper | read | HIGH |
| 245 | ProgEnt | read | BREAKTHROUGH |
| 246 | ProgEnt Paper | read | BREAKTHROUGH |
| 247 | Self-Evolving Agent Safety | read | BREAKTHROUGH |

**BREAKTHROUGH**: 7/12 (58%)  
**HIGH**: 4/12 (33%)  
**MEDIUM**: 1/12 (8%)

---

## Next Steps

1. **Review findings** with Lyra architecture team
2. **Prioritize P0 patterns** for immediate implementation
3. **Design safety layer interface** based on multi-layer defense pattern
4. **Prototype privilege control** with symbolic policies
5. **Set up AgentDojo-style testing** in CI/CD pipeline
6. **Evaluate LlamaFirewall** for production integration
7. **Monitor self-evolution safety** if/when self-improvement capabilities added

---

**Research Complete**: 2026-05-31  
**Findings Location**: `/findings.md` (Safety & Alignment Research section)  
**Source Ledger**: `/source-ledger.md` (§3.16 rows 236-247 marked 'read')

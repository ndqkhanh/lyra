# Guide: Research and Verification

> 📖 Guide — Walk through deep research (fan-out, fetch, cross-check, vote, report) and the verification pipeline (anonymize, verify, challenge, triangulate, gate). Learn how Lyra builds trust in its outputs.

This guide covers two complementary systems: the deep research engine for investigating questions and the verification pipeline for validating execution quality.

---

## Deep Research Workflow

The `/deep-research` command triggers a multi-stage investigation:

### Step 1: Query Expansion

The research question is decomposed into sub-questions. A broad query like "What are the best practices for LLM agent memory?" becomes 3-5 focused sub-questions covering specific memory architectures, benchmarks, and implementation patterns.

### Step 2: Fan-Out Search

Multiple parallel web searches execute across sub-questions. Each search returns 5-10 results. Promising URLs are then fetched for full content. This parallel fan-out is the speed advantage -- instead of sequential searches, Lyra explores 5+ angles simultaneously.

### Step 3: Source Fetching

Full content is retrieved from each promising URL. The system extracts claims and evidence from each source, tagging them with the source URL and extraction confidence.

### Step 4: Adversarial Cross-Check

This is the key step that separates deep research from simple search. Claims are cross-verified against multiple sources. Contradictions trigger follow-up searches. The system actively tries to find disconfirming evidence -- if a claim is only supported by one source, it's flagged as low confidence.

### Step 5: Multi-Agent Vote

Multiple agent models vote on the synthesized findings. By default, three independent model families (e.g., Claude, DeepSeek, Gemini) evaluate the evidence. If consensus is reached (majority, weighted, or threshold), the result is promoted.

### Step 6: Report Synthesis

Verified findings are compiled into a cited report. Each factual claim has at least one source citation. The report includes confidence levels per section and flags unresolved contradictions.

---

## Verification Pipeline

The verifier runs after every completed task to catch issues a single agent would miss:

### Stage 1: Evidence Integrity

The validator checks: Are the claimed facts actually present in the data? For a code change, this means verifying the stated changes match the actual diff. For a research answer, this means checking cited sources actually contain the referenced claims.

### Stage 2: Result-to-Claim Mapping

Does the evidence logically support the conclusion? The critic agent audits the reasoning chain, flagging logical leaps, omitted steps, and circular reasoning.

### Stage 3: Claim Auditing

Is the final output consistent with all intermediate claims? This catches contradictions that emerge during execution -- for example, claiming "all test pass" when one intermediate step introduced a regression.

### The Refute/Promote Loop

```python
verification = refute_or_promote(executor_output, validator, critic)
if verification.promoted:
    # All verifiers agreed: high confidence
elif verification.refuted:
    # Verifiers found issues -- continue loop with feedback
else:
    # Inconclusive -- request human review
```

Performance: false positive rate drops from 8.3% (single agent) to 0.7% (multi-agent), a 91.6% reduction. Latency overhead: +4.7s.

---

## The TDD Gate

For code changes, verification includes automated test execution. The plan artifact specifies acceptance tests; the verifier runs them and confirms they pass. This is the "gate" -- if tests fail, the output is refuted regardless of other checks.

---

## Related Docs

- [Architecture: Verifier](../blocks/10-verifier.md) -- ARIS 3-stage pipeline, adversarial panel
- [Architecture: Observability](../blocks/11-observability.md) -- HIR event stream, trace analysis
- [Concept: Verifier](../concepts/12-verifier.md) -- refute/promote loop, plan-based verification
- [Concept: Observability](../concepts/13-observability.md) -- session-level metrics, Prometheus
- [Guide: Agent Execution](01-agent-execution.md) -- how verification integrates with the agent loop
- [Guide: Safety and Permissions](05-safety-and-permissions.md) -- ARIS integration
- [Guide: Memory and Context](02-memory-and-context.md) -- Reflexion lesson storage

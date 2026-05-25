---
name: prd-writing
description: Product Requirements Document writing patterns and best practices
origin: Plan 13
tags: [product, prd, requirements, planning]
triggers: [PRD, product requirement, spec, feature spec, requirements document]
---

# PRD Writing

## PRD Template

```yaml
## Problem Statement
[One-paragraph description of the problem being solved]

## User Personas
| Persona | Archetype | Goals | Pain Points |
|---------|-----------|-------|-------------|
| Name    | Role      | What they want | What blocks them |

## Success Metrics
- [Metric 1]: [Target value] by [timeframe]
- [Metric 2]: [Target value] by [timeframe]

## Functional Requirements
[FR-001]: [Description]
[FR-002]: [Description]

## Non-Functional Requirements
- Performance: [e.g., <200ms p95 latency]
- Security: [e.g., SOC2, encryption at rest]
- Availability: [e.g., 99.9% uptime]

## Out of Scope
- [Clearly listed items deferred to future phases]
```

## User Story Mapping

1. Identify the backbone (major user activities)
2. Break each activity into detailed tasks
3. Prioritize with MoSCoW
4. Slice MVP by walking the backbone left-to-right

## Acceptance Criteria (Given-When-Then)

```
Given [context/precondition]
When  [action is performed]
Then  [expected outcome]
```

## Prioritization Frameworks

| Framework | Formula / Dimensions | Best For |
|-----------|---------------------|----------|
| **RICE** | Reach x Impact x Confidence / Effort | Quantitative scoring |
| **MoSCoW** | Must / Should / Could / Won't | Stakeholder alignment |
| **Kano** | Basic / Performance / Delight | Feature categorization |

## Stakeholder Review Checklist

- [ ] Problem statement validated against user research
- [ ] Success metrics measurable and unambiguous
- [ ] Requirements scoped for a single deliverable phase
- [ ] Out-of-scope items acknowledged by stakeholders
- [ ] Technical feasibility reviewed with engineering

## PRD Anti-Patterns

- Solution-first writing (describing implementation instead of the problem)
- Scope creep disguised as "future considerations"
- Unmeasurable success criteria (e.g., "better user experience")
- Ignoring non-functional requirements until late in development
- Over-specification that removes engineering autonomy

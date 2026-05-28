# Specialized Skills for Lyra

This directory contains 14 specialized skills across 9 domains, providing expert guidance for various roles and disciplines.

## Overview

Specialized skills are comprehensive knowledge bases that provide:
- Domain-specific expertise and best practices
- Practical examples and code snippets
- Decision-making frameworks
- Common patterns and anti-patterns
- Quick reference guides
- Escalation criteria

## Skills by Domain

### Engineering (5 skills)

#### 1. Backend Engineer (`backend.md`)
**Triggers**: backend, api, database, microservices, authentication, rest, graphql

Expert backend development guidance covering:
- API design (REST, GraphQL, gRPC, WebSocket)
- Database expertise (SQL, NoSQL, ORMs, migrations)
- Authentication & authorization (JWT, OAuth, RBAC)
- Caching strategies (application, distributed, CDN)
- Scalability patterns (horizontal/vertical scaling, sharding)

**Use when**: Building APIs, optimizing database queries, implementing authentication, or designing distributed systems.

#### 2. Frontend Engineer (`frontend.md`)
**Triggers**: frontend, react, vue, ui component, state management, responsive design

Modern frontend development expertise covering:
- React development (hooks, performance, server components)
- Modern frameworks (Next.js, Vue 3, Angular, Svelte)
- Styling solutions (Tailwind, CSS-in-JS, CSS Modules)
- Performance optimization (code splitting, Web Vitals)
- Accessibility (WCAG 2.1 AA compliance)

**Use when**: Building user interfaces, optimizing frontend performance, implementing responsive designs, or debugging UI issues.

#### 3. Testing Engineer (`testing.md`)
**Triggers**: testing, test, tdd, unit test, integration test, e2e

Comprehensive testing strategies covering:
- Test types (unit, integration, E2E, contract, performance)
- Testing frameworks (Jest, Vitest, Playwright, pytest)
- Test-Driven Development (TDD) workflow
- Test automation and CI/CD integration
- Coverage metrics and quality gates

**Use when**: Writing tests, debugging test failures, or implementing testing strategies.

#### 4. DevOps Engineer (`devops.md`)
**Triggers**: devops, ci/cd, docker, kubernetes, deployment, infrastructure

Infrastructure and deployment automation covering:
- CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins)
- Containerization (Docker, multi-stage builds)
- Orchestration (Kubernetes, Helm, ArgoCD)
- Infrastructure as Code (Terraform, Pulumi, CloudFormation)
- Monitoring & observability (Prometheus, Grafana, ELK)

**Use when**: Setting up pipelines, deploying applications, or managing infrastructure.

#### 5. Full-Stack Engineer (`fullstack.md`)
**Triggers**: fullstack, full stack, end-to-end, complete feature

End-to-end development expertise covering:
- Full-stack architecture (monorepo, API contracts)
- Modern frameworks (Next.js, Remix, SvelteKit)
- End-to-end type safety (tRPC, GraphQL Code Generator)
- Development workflow (local environment, hot reload)

**Use when**: Building complete features end-to-end, integrating APIs with UIs, or architecting full-stack applications.

### Design (2 skills)

#### 6. UI/UX Designer (`ui_ux.md`)
**Triggers**: ui design, ux design, user interface, wireframe, prototype, design system

User-centered design covering:
- User research (interviews, personas, journey mapping)
- Information architecture (site mapping, navigation)
- Interaction design (wireframing, prototyping)
- Visual design (typography, color, layout)
- Design systems (component libraries, design tokens)

**Use when**: Designing interfaces, creating user flows, or establishing design patterns.

#### 7. System Designer (`system_design.md`)
**Triggers**: system design, architecture, scalability, distributed system, design patterns

Large-scale system design covering:
- Distributed systems (CAP theorem, consistency, consensus)
- Scalability patterns (sharding, caching, load balancing)
- Reliability & resilience (fault tolerance, circuit breakers)
- Performance optimization (latency vs throughput)
- Security architecture (authentication, encryption, compliance)

**Use when**: Designing large-scale systems, evaluating trade-offs, or solving architectural challenges.

### SRE (1 skill)

#### 8. SRE Engineer (`reliability.md`)
**Triggers**: sre, reliability, monitoring, incident, observability, slo, sli

Site Reliability Engineering covering:
- Observability (metrics, logs, traces, dashboards)
- Incident management (on-call, response, postmortems)
- Service Level Objectives (SLI, SLO, error budgets)
- Capacity planning (forecasting, resource planning)
- Automation (runbooks, self-healing, chaos engineering)

**Use when**: Setting up observability, responding to incidents, or improving system reliability.

### AI Research (1 skill)

#### 9. AI Researcher (`research_methodology.md`)
**Triggers**: ai research, ml research, paper analysis, experiment design, model evaluation

Research methodology covering:
- Paper analysis (literature review, critical analysis)
- Experiment design (hypothesis, baselines, ablations)
- Model evaluation (metrics, statistical significance)
- Research communication (paper writing, visualization)

**Use when**: Analyzing papers, designing experiments, or evaluating ML models.

### Solution Architecture (1 skill)

#### 10. Solution Architect (`solution_design.md`)
**Triggers**: solution architecture, technology selection, vendor evaluation, build vs buy

Technology selection and solution design covering:
- Requirements analysis (functional, non-functional, constraints)
- Technology selection (evaluation criteria, POC, TCO)
- System integration (API design, data sync, legacy integration)
- Architecture Decision Records (ADRs)
- Risk management (identification, mitigation, contingency)

**Use when**: Evaluating technologies, designing solutions, or making build vs buy decisions.

### Cloud Engineering (1 skill)

#### 11. Cloud Architect (`cloud_architecture.md`)
**Triggers**: cloud, aws, gcp, azure, kubernetes, terraform, cloud architecture

Cloud infrastructure design covering:
- Cloud platforms (AWS, GCP, Azure services)
- Infrastructure as Code (Terraform, Pulumi, CloudFormation)
- Container orchestration (Kubernetes, Helm, ArgoCD)
- Networking (VPC, load balancing, DNS, CDN)
- Security (IAM, secrets management, compliance)

**Use when**: Designing cloud infrastructure, migrating to cloud, or optimizing cloud costs.

### Product Management (1 skill)

#### 12. Product Manager (`product_strategy.md`)
**Triggers**: product management, roadmap, prioritization, user story, product strategy

Product strategy and roadmap planning covering:
- Product strategy (vision, market analysis, value proposition)
- Roadmap planning (RICE, MoSCoW, Kano prioritization)
- Requirements definition (user stories, acceptance criteria)
- Stakeholder management (communication, alignment)
- Metrics & analytics (KPIs, A/B testing, funnel optimization)

**Use when**: Planning features, prioritizing work, or defining product requirements.

### Business Analysis (1 skill)

#### 13. Business Analyst (`requirements_analysis.md`)
**Triggers**: business analysis, requirements gathering, user stories, process flow, acceptance criteria

Requirements gathering and process analysis covering:
- Requirements elicitation (interviews, workshops, observation)
- Requirements analysis (functional vs non-functional, prioritization)
- Process modeling (As-Is, To-Be, swimlane diagrams)
- Documentation (BRD, use cases, data flow diagrams)
- Stakeholder management (power/interest analysis, communication)

**Use when**: Gathering requirements, analyzing business processes, or creating specifications.

### Brainstorming (1 skill)

#### 14. Brainstorming Facilitator (`creative_thinking.md`)
**Triggers**: brainstorm, ideation, creative thinking, problem solving, generate ideas

Creative problem-solving and structured ideation covering:
- Ideation techniques (brainstorming, mind mapping, SCAMPER)
- Problem decomposition (5 Whys, Fishbone, first principles)
- Creative thinking (lateral thinking, analogical reasoning)
- Decision frameworks (decision matrix, pros/cons, cost-benefit)
- Facilitation skills (session planning, group dynamics)

**Use when**: Generating ideas, solving complex problems, or facilitating creative sessions.

## Usage

### Programmatic Access

```python
from lyra_cli.skills.specialized import (
    get_registry,
    list_all_skills,
    get_skill_by_name,
    search_skills,
)

# List all skills
skills = list_all_skills()
print(f"Available skills: {skills}")

# Get specific skill
skill = get_skill_by_name("backend-engineer")
print(f"Skill: {skill.name}")
print(f"Domain: {skill.domain}")
print(f"Tags: {skill.tags}")

# Search by trigger
results = search_skills("backend")
for skill in results:
    print(f"- {skill.name}: {skill.description}")

# Get skill content
registry = get_registry()
content = registry.get_skill_content("backend-engineer")
print(content)
```

### Integration with Skill Curator

Specialized skills are automatically discovered by the skill curator:

```python
from lyra_cli.skills.skill_curator import SkillCurator, SelectionContext

curator = SkillCurator()
curator.discover_skills()

# Select skills based on context
context = SelectionContext(
    current_file="api.py",
    recent_tools=("Read", "Write", "Bash"),
    task_description="implement REST API endpoint",
    active_skills=(),
    error_history=(),
)

result = curator.select_skills(context, max_skills=3)
for match in result.selected_skills:
    print(f"Selected: {match.skill_name} (score: {match.relevance_score:.2f})")
    print(f"Reason: {match.match_reason}")
```

## Skill Structure

Each skill follows a consistent structure:

```markdown
---
name: "skill-name"
description: Brief description of the skill
tags: ["tag1", "tag2", "tag3"]
triggers: ["trigger1", "trigger2", "trigger3"]
model: "sonnet"  # or "opus" for complex reasoning
tools: ["Read", "Write", "Edit", "Bash"]
---

# Skill Title

Brief introduction

## Core Competencies

### 1. Competency Area
- Sub-topic 1
- Sub-topic 2

### 2. Another Area
- Sub-topic 1
- Sub-topic 2

## Common Patterns

[Code examples and patterns]

## Workflows

[Step-by-step workflows]

## Quick Reference

[Quick commands and checklists]

## When to Escalate

[Criteria for escalating to specialists]
```

## Model Selection

Skills use different Claude models based on complexity:

- **Haiku**: Quick lookups, simple tasks (not used in specialized skills)
- **Sonnet**: Standard complexity, most skills (12 skills)
- **Opus**: Deep reasoning, complex decisions (2 skills: system-designer, ai-researcher)

## Testing

Run tests to verify skill integrity:

```bash
# Run all tests
pytest tests/test_specialized_skills.py -v

# Run specific test
pytest tests/test_specialized_skills.py::TestSpecializedSkills::test_list_all_skills -v

# Check coverage
pytest tests/test_specialized_skills.py --cov=lyra_cli.skills.specialized --cov-report=term-missing
```

## Contributing

When adding new specialized skills:

1. Create a new markdown file in the appropriate domain directory
2. Follow the skill structure template
3. Include YAML frontmatter with metadata
4. Add comprehensive content with examples
5. Update the `__init__.py` to include the new skill
6. Add tests for the new skill
7. Update this README

## Skill Quality Checklist

- [ ] YAML frontmatter with all required fields
- [ ] Clear and concise description
- [ ] Relevant tags and triggers
- [ ] Core competencies section
- [ ] Practical examples and code snippets
- [ ] Common patterns and anti-patterns
- [ ] Step-by-step workflows
- [ ] Quick reference guide
- [ ] Escalation criteria
- [ ] Proper markdown formatting
- [ ] No hardcoded secrets or sensitive data

## License

These skills are part of the Lyra project and follow the project's license.

---
name: "product-manager"
description: Product management expertise covering roadmap planning, prioritization, user stories, stakeholder management, and product strategy. Use when planning features, prioritizing work, or defining product requirements.
tags: ["product", "pm", "roadmap", "prioritization", "user-stories"]
triggers: ["product management", "roadmap", "prioritization", "user story", "product strategy"]
model: "sonnet"
tools: ["Read", "Write", "Edit"]
---

# Product Manager

Product strategy, roadmap planning, and stakeholder management.

## Core Competencies

### 1. Product Strategy
- Vision and mission definition
- Market analysis and competitive research
- Value proposition design
- Go-to-market strategy
- Product-market fit validation

### 2. Roadmap Planning
- Feature prioritization (RICE, MoSCoW, Kano)
- Quarterly planning (OKRs)
- Release planning
- Dependency management
- Stakeholder alignment

### 3. Requirements Definition
- User stories and acceptance criteria
- Use case documentation
- Wireframes and mockups
- Technical specifications
- API contracts

### 4. Stakeholder Management
- Executive communication
- Cross-functional collaboration
- Customer feedback loops
- Vendor relationships
- Team alignment

### 5. Metrics & Analytics
- KPI definition and tracking
- A/B testing and experimentation
- User behavior analysis
- Funnel optimization
- Retention and churn analysis

## Product Development Lifecycle

### 1. Discovery
```
Activities:
- User research and interviews
- Market analysis
- Competitive analysis
- Problem validation
- Opportunity sizing

Outputs:
- Problem statement
- User personas
- Market size estimate
- Competitive landscape
```

### 2. Definition
```
Activities:
- Solution ideation
- Feature prioritization
- Requirements documentation
- Technical feasibility assessment
- Design mockups

Outputs:
- Product requirements document (PRD)
- User stories
- Wireframes/mockups
- Success metrics
```

### 3. Development
```
Activities:
- Sprint planning
- Daily standups
- Design reviews
- Progress tracking
- Scope management

Outputs:
- Working software
- Test coverage
- Documentation
- Release notes
```

### 4. Launch
```
Activities:
- Beta testing
- Marketing preparation
- Sales enablement
- Support training
- Launch execution

Outputs:
- Launch plan
- Marketing materials
- Training documentation
- Success metrics baseline
```

### 5. Iteration
```
Activities:
- Metrics monitoring
- User feedback collection
- A/B testing
- Feature refinement
- Bug fixing

Outputs:
- Performance reports
- Iteration backlog
- Improvement roadmap
```

## Prioritization Frameworks

### RICE Scoring
```
RICE = (Reach × Impact × Confidence) / Effort

Reach: How many users affected per quarter?
Impact: How much does it improve their experience?
  - 3 = Massive impact
  - 2 = High impact
  - 1 = Medium impact
  - 0.5 = Low impact
  - 0.25 = Minimal impact

Confidence: How confident are we?
  - 100% = High confidence
  - 80% = Medium confidence
  - 50% = Low confidence

Effort: How many person-months?

Example:
Feature A: (1000 × 2 × 0.8) / 2 = 800
Feature B: (500 × 3 × 1.0) / 1 = 1500
Feature C: (2000 × 1 × 0.5) / 3 = 333

Priority: B > A > C
```

### MoSCoW Method
```
Must Have:
- Critical for launch
- Non-negotiable
- Legal/compliance requirements

Should Have:
- Important but not critical
- Can be delayed if needed
- Significant value

Could Have:
- Nice to have
- Low impact if missing
- Easy to implement

Won't Have (this time):
- Out of scope
- Future consideration
- Low priority
```

### Kano Model
```
Basic Needs (Must-haves):
- Expected by users
- Dissatisfaction if missing
- No delight if present
- Example: Login functionality

Performance Needs (Linear):
- More is better
- Satisfaction increases with quality
- Example: Page load speed

Excitement Needs (Delighters):
- Unexpected features
- High satisfaction if present
- No dissatisfaction if missing
- Example: AI-powered suggestions
```

## User Story Template

### Format
```
As a [user type],
I want to [action],
So that [benefit].

Acceptance Criteria:
- Given [context]
- When [action]
- Then [outcome]

Example:
As a customer,
I want to save items to a wishlist,
So that I can purchase them later.

Acceptance Criteria:
- Given I am logged in
- When I click the "Add to Wishlist" button
- Then the item is saved to my wishlist
- And I see a confirmation message
- And the wishlist count increases by 1
```

### INVEST Criteria
```
Independent: Can be developed separately
Negotiable: Details can be discussed
Valuable: Provides value to users
Estimable: Can be estimated by team
Small: Can be completed in one sprint
Testable: Has clear acceptance criteria
```

## Product Requirements Document (PRD)

### Template
```markdown
# Feature: User Wishlist

## Overview
Allow users to save products for later purchase.

## Problem Statement
Users often browse products but aren't ready to buy immediately. They need a way to save items for future reference without adding them to cart.

## Goals
- Increase user engagement (time on site)
- Improve conversion rate (wishlist → purchase)
- Reduce cart abandonment

## Success Metrics
- 30% of active users create a wishlist
- 15% conversion rate from wishlist to purchase
- 20% increase in repeat visits

## User Stories
1. As a customer, I want to add items to my wishlist
2. As a customer, I want to view my wishlist
3. As a customer, I want to remove items from my wishlist
4. As a customer, I want to move items from wishlist to cart

## Requirements

### Functional
- Add to wishlist button on product pages
- Wishlist page showing all saved items
- Remove from wishlist functionality
- Move to cart functionality
- Wishlist count in header
- Email notifications for price drops

### Non-Functional
- Page load time < 2 seconds
- Support 10,000 concurrent users
- 99.9% uptime
- Mobile responsive

## Design
[Link to Figma mockups]

## Technical Approach
- New `wishlists` table in database
- REST API endpoints: GET, POST, DELETE /api/wishlists
- Frontend: React components
- Backend: Node.js + PostgreSQL

## Dependencies
- User authentication system
- Product catalog API
- Email notification service

## Risks
- Database performance with large wishlists
- Email deliverability
- Mobile UX complexity

## Timeline
- Design: 1 week
- Development: 3 weeks
- Testing: 1 week
- Launch: Week of 2024-02-15

## Open Questions
- Should wishlists be shareable?
- Should we support multiple wishlists?
- Should we sync across devices?
```

## OKR Framework

### Structure
```
Objective: Qualitative goal
Key Results: Quantitative metrics (3-5)

Example:
Objective: Become the leading e-commerce platform for sustainable products

Key Results:
1. Increase monthly active users from 100K to 500K
2. Achieve 4.5+ star rating on app stores
3. Reach $10M in monthly revenue
4. Reduce cart abandonment rate from 70% to 50%
```

### Quarterly Planning
```
Q1 2024 OKRs:

Objective: Improve user engagement
KR1: Increase daily active users from 50K to 75K
KR2: Increase average session duration from 5 min to 8 min
KR3: Increase repeat visit rate from 30% to 45%

Initiatives:
- Launch personalized recommendations
- Implement wishlist feature
- Add social sharing
- Optimize mobile performance
```

## Stakeholder Communication

### Executive Updates
```
Format: Weekly email

Subject: Product Update - Week of Jan 15

Highlights:
✅ Launched wishlist feature (on time)
✅ Achieved 25% user adoption in first week
⚠️ Mobile performance below target (investigating)

Metrics:
- MAU: 120K (+20% MoM)
- Conversion: 3.2% (+0.5% MoM)
- Revenue: $2.1M (+15% MoM)

Next Week:
- Launch email notifications for wishlists
- Begin A/B test for checkout flow
- User research for Q2 features
```

### Team Standups
```
Format: Daily 15-minute meeting

Yesterday:
- Reviewed design mockups for feature X
- Prioritized bugs for next sprint
- Met with customer success team

Today:
- Sprint planning for next iteration
- Review PRD with engineering
- Customer interview at 2pm

Blockers:
- Waiting on legal approval for terms update
```

## Metrics & Analytics

### Key Metrics by Stage

**Acquisition**
```
- Traffic sources
- Cost per acquisition (CPA)
- Conversion rate (visitor → signup)
```

**Activation**
```
- Time to first value
- Onboarding completion rate
- Feature adoption rate
```

**Retention**
```
- Daily/Monthly active users (DAU/MAU)
- Churn rate
- Cohort retention curves
```

**Revenue**
```
- Monthly recurring revenue (MRR)
- Average revenue per user (ARPU)
- Customer lifetime value (LTV)
- LTV:CAC ratio
```

**Referral**
```
- Net Promoter Score (NPS)
- Viral coefficient
- Referral conversion rate
```

### A/B Testing
```
Hypothesis:
Changing CTA button from "Buy Now" to "Add to Cart" will increase conversion rate

Test Setup:
- Control (A): "Buy Now" button
- Variant (B): "Add to Cart" button
- Traffic split: 50/50
- Duration: 2 weeks
- Sample size: 10,000 users per variant

Success Criteria:
- Statistical significance: p < 0.05
- Minimum detectable effect: 10% improvement

Results:
- Control: 3.2% conversion
- Variant: 3.8% conversion
- Lift: +18.75%
- p-value: 0.003 (significant)

Decision: Ship variant B
```

## Customer Research

### User Interview Guide
```
Introduction (5 min):
- Thank you for participating
- Purpose of interview
- Recording consent

Background (10 min):
- Tell me about your role
- How do you currently solve [problem]?
- What tools do you use?

Problem Exploration (20 min):
- Walk me through your workflow
- What are the biggest pain points?
- How often does this problem occur?
- What have you tried to solve it?

Solution Validation (15 min):
- [Show prototype]
- What are your first impressions?
- How would you use this?
- What's missing?

Wrap-up (10 min):
- Any other feedback?
- Can we follow up?
- Thank you
```

### Survey Design
```
Goal: Understand feature priorities

Questions:
1. How often do you use [product]?
   - Daily
   - Weekly
   - Monthly
   - Rarely

2. Which feature would be most valuable? (rank 1-5)
   - Feature A
   - Feature B
   - Feature C
   - Feature D
   - Feature E

3. How likely are you to recommend [product]? (0-10)
   [NPS question]

4. What's the biggest improvement we could make?
   [Open-ended]
```

## Quick Reference

### Product Launch Checklist
- [ ] PRD approved by stakeholders
- [ ] Design mockups finalized
- [ ] Engineering estimates confirmed
- [ ] Success metrics defined
- [ ] Beta testing completed
- [ ] Marketing materials prepared
- [ ] Sales team trained
- [ ] Support documentation ready
- [ ] Analytics tracking implemented
- [ ] Launch communication sent

### Sprint Planning Checklist
- [ ] Backlog groomed and prioritized
- [ ] User stories have acceptance criteria
- [ ] Dependencies identified
- [ ] Team capacity confirmed
- [ ] Sprint goal defined
- [ ] Stories estimated
- [ ] Sprint committed

## When to Escalate

- Strategic direction unclear → Engage executive team
- Cross-functional conflict → Engage department heads
- Technical feasibility concerns → Engage engineering leadership
- Legal/compliance issues → Engage legal team
- Budget constraints → Engage finance team

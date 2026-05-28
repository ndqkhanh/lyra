---
name: "business-analyst"
description: Business analysis expertise covering requirements gathering, process modeling, stakeholder analysis, and documentation. Use when gathering requirements, analyzing business processes, or creating specifications.
tags: ["business-analysis", "requirements", "process-modeling", "documentation"]
triggers: ["business analysis", "requirements gathering", "user stories", "process flow", "acceptance criteria"]
model: "sonnet"
tools: ["Read", "Write", "Edit"]
---

# Business Analyst

Requirements gathering, process analysis, and business documentation.

## Core Competencies

### 1. Requirements Elicitation
- Stakeholder interviews
- Workshops and brainstorming
- Document analysis
- Observation and job shadowing
- Surveys and questionnaires

### 2. Requirements Analysis
- Functional vs non-functional requirements
- Requirements prioritization
- Gap analysis
- Feasibility assessment
- Impact analysis

### 3. Process Modeling
- Current state (As-Is) analysis
- Future state (To-Be) design
- Process flow diagrams
- Swimlane diagrams
- BPMN notation

### 4. Documentation
- Business requirements document (BRD)
- Functional specifications
- Use cases and scenarios
- Data flow diagrams
- Entity relationship diagrams

### 5. Stakeholder Management
- Stakeholder identification
- Power/interest analysis
- Communication planning
- Conflict resolution
- Change management

## Requirements Gathering Process

### 1. Preparation
```
Activities:
- Identify stakeholders
- Review existing documentation
- Prepare interview questions
- Schedule sessions
- Set objectives

Outputs:
- Stakeholder list
- Interview guide
- Meeting schedule
```

### 2. Elicitation
```
Techniques:
- One-on-one interviews
- Focus groups
- Workshops
- Observation
- Prototyping

Questions to ask:
- What problem are you trying to solve?
- Who are the users?
- What are the current pain points?
- What does success look like?
- What are the constraints?
```

### 3. Analysis
```
Activities:
- Categorize requirements
- Identify dependencies
- Assess feasibility
- Prioritize requirements
- Resolve conflicts

Outputs:
- Requirements list
- Priority matrix
- Dependency map
```

### 4. Specification
```
Activities:
- Document requirements
- Create use cases
- Design process flows
- Define acceptance criteria
- Review with stakeholders

Outputs:
- BRD or FSD
- Use case diagrams
- Process flows
- Acceptance criteria
```

### 5. Validation
```
Activities:
- Review with stakeholders
- Walkthrough sessions
- Prototype validation
- Sign-off

Outputs:
- Approved requirements
- Sign-off document
```

## Requirements Types

### Functional Requirements
```
Definition: What the system should do

Examples:
- The system shall allow users to create an account
- The system shall send email notifications
- The system shall generate monthly reports
- The system shall validate credit card numbers

Format:
- The system shall [action] [object] [condition]
- Must be specific, measurable, testable
```

### Non-Functional Requirements
```
Performance:
- Response time < 2 seconds
- Support 10,000 concurrent users
- Process 1 million transactions per day

Scalability:
- Handle 10x traffic growth
- Support horizontal scaling
- Auto-scale based on load

Security:
- Encrypt data at rest and in transit
- Support multi-factor authentication
- Comply with GDPR, HIPAA

Usability:
- Mobile responsive design
- Accessible (WCAG 2.1 AA)
- Support multiple languages

Reliability:
- 99.9% uptime
- Automated backups every 6 hours
- Disaster recovery plan

Maintainability:
- Modular architecture
- Comprehensive documentation
- Automated testing
```

## Use Case Template

### Format
```
Use Case: Create User Account

ID: UC-001
Priority: High
Actor: New User
Preconditions: User has valid email address
Postconditions: User account created and activated

Main Flow:
1. User navigates to registration page
2. System displays registration form
3. User enters email, password, name
4. User clicks "Create Account"
5. System validates input
6. System creates account
7. System sends verification email
8. User clicks verification link
9. System activates account
10. System displays success message

Alternative Flows:
3a. Email already exists
    1. System displays error message
    2. User enters different email
    3. Resume at step 4

5a. Validation fails
    1. System displays validation errors
    2. User corrects input
    3. Resume at step 4

Exception Flows:
6a. Database error
    1. System logs error
    2. System displays generic error message
    3. User retries later
```

## Process Modeling

### As-Is Process (Current State)
```
Purpose: Document current process
Goal: Identify inefficiencies and pain points

Example: Order Fulfillment (Manual)
1. Customer places order via phone
2. Sales rep writes order on paper
3. Sales rep enters order into system (end of day)
4. Warehouse receives printed order (next day)
5. Warehouse picks and packs items
6. Warehouse updates system manually
7. Shipping creates label manually
8. Customer receives order (3-5 days)

Pain Points:
- Manual data entry (errors, delays)
- No real-time inventory visibility
- Slow order processing
- No order tracking for customers
```

### To-Be Process (Future State)
```
Purpose: Design improved process
Goal: Eliminate inefficiencies, automate steps

Example: Order Fulfillment (Automated)
1. Customer places order online
2. System validates inventory in real-time
3. System creates order automatically
4. System notifies warehouse immediately
5. Warehouse picks and packs items
6. System generates shipping label automatically
7. System sends tracking info to customer
8. Customer receives order (1-2 days)

Improvements:
- Automated data entry (no errors)
- Real-time inventory visibility
- Faster order processing
- Customer self-service tracking
```

### Swimlane Diagram
```
Customer | Sales | Warehouse | System
---------|-------|-----------|--------
Place    |       |           |
order    |       |           |
  |      |       |           |
  +----->|       |           |
         | Enter |           |
         | order |           |
         |   |   |           |
         |   +-------------->|
         |       |           | Validate
         |       |           | inventory
         |       |           |   |
         |       |<----------+   |
         |       | Notify    |   |
         |       |   |       |   |
         |       |   +------>|   |
         |       |           | Pick
         |       |           | items
         |       |           |   |
         |       |           |<--+
         |       |           | Ship
         |<------+           |
         | Track |           |
         | order |           |
```

## Business Requirements Document (BRD)

### Template
```markdown
# Business Requirements Document

## Executive Summary
[Brief overview of project, objectives, and expected benefits]

## Business Objectives
1. Increase online sales by 30%
2. Reduce order processing time by 50%
3. Improve customer satisfaction (NPS > 50)

## Scope
### In Scope
- Online ordering system
- Inventory management
- Order tracking
- Customer notifications

### Out of Scope
- Point of sale system
- Accounting integration
- Supplier management

## Stakeholders
| Name | Role | Interest | Influence |
|------|------|----------|-----------|
| John Smith | CEO | High | High |
| Jane Doe | Sales Director | High | Medium |
| Bob Johnson | IT Manager | Medium | High |
| Mary Williams | Customer Service | High | Low |

## Current State Analysis
### Problems
- Manual order entry causes errors and delays
- No real-time inventory visibility
- Customers cannot track orders
- High operational costs

### Impact
- Lost sales due to stockouts
- Customer complaints about delays
- High labor costs for manual processing

## Requirements

### Functional Requirements
FR-001: System shall allow customers to browse products
FR-002: System shall display real-time inventory levels
FR-003: System shall process credit card payments
FR-004: System shall send order confirmation emails
FR-005: System shall provide order tracking

### Non-Functional Requirements
NFR-001: System shall support 1,000 concurrent users
NFR-002: Page load time shall be < 2 seconds
NFR-003: System shall have 99.9% uptime
NFR-004: System shall be PCI-DSS compliant
NFR-005: System shall be mobile responsive

## Use Cases
[Link to detailed use cases]

## Process Flows
[Link to process diagrams]

## Data Requirements
### Entities
- Customer (name, email, address, phone)
- Product (SKU, name, description, price, inventory)
- Order (order_id, customer_id, items, total, status)
- Payment (payment_id, order_id, amount, method, status)

### Data Volume
- 10,000 customers
- 1,000 products
- 500 orders per day
- 5 years data retention

## Assumptions
- Customers have internet access
- Customers have valid payment methods
- Warehouse has barcode scanners
- Staff will receive training

## Constraints
- Budget: $200,000
- Timeline: 6 months
- Technology: Must integrate with existing ERP
- Compliance: PCI-DSS, GDPR

## Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Integration complexity | High | High | POC with ERP vendor |
| User adoption | Medium | High | Training and change management |
| Budget overrun | Medium | Medium | Phased implementation |

## Success Criteria
- 80% of orders placed online within 6 months
- Order processing time reduced from 24 hours to 2 hours
- Customer satisfaction score > 4.5/5
- ROI achieved within 18 months

## Timeline
- Requirements: 4 weeks
- Design: 6 weeks
- Development: 12 weeks
- Testing: 4 weeks
- Deployment: 2 weeks
- Total: 28 weeks

## Approval
[Signature section for stakeholders]
```

## Stakeholder Analysis

### Power/Interest Grid
```
High Power, High Interest (Manage Closely):
- CEO
- Sales Director
- IT Manager

High Power, Low Interest (Keep Satisfied):
- CFO
- Legal Counsel

Low Power, High Interest (Keep Informed):
- Customer Service Team
- Warehouse Staff

Low Power, Low Interest (Monitor):
- External Vendors
```

### Communication Plan
```
| Stakeholder | Frequency | Method | Content |
|-------------|-----------|--------|---------|
| CEO | Monthly | Email | Executive summary |
| Sales Director | Weekly | Meeting | Progress update |
| IT Manager | Daily | Slack | Technical details |
| Customer Service | Bi-weekly | Email | Feature updates |
```

## Gap Analysis

### Template
```
| Capability | Current State | Desired State | Gap | Priority |
|------------|---------------|---------------|-----|----------|
| Order Entry | Manual, phone | Online, automated | High | High |
| Inventory | End-of-day batch | Real-time | High | High |
| Tracking | None | Customer self-service | High | Medium |
| Reporting | Manual Excel | Automated dashboards | Medium | Low |
```

## Acceptance Criteria

### Format
```
Given [precondition]
When [action]
Then [expected result]

Example:
Given I am a registered user
When I add an item to cart and proceed to checkout
Then I should see the checkout page with order summary
And I should be able to enter payment information
And I should receive order confirmation after payment
```

### Checklist
```
- [ ] Specific and unambiguous
- [ ] Testable
- [ ] Measurable
- [ ] Achievable
- [ ] Relevant to requirement
- [ ] Complete (covers all scenarios)
```

## Data Flow Diagram

### Level 0 (Context Diagram)
```
Customer → [Order System] → Warehouse
              ↓
           Database
```

### Level 1 (Process Diagram)
```
Customer → [1. Browse Products] → Product Catalog
Customer → [2. Place Order] → Order Database
Order Database → [3. Process Payment] → Payment Gateway
Order Database → [4. Fulfill Order] → Warehouse
Warehouse → [5. Ship Order] → Customer
```

## Requirements Traceability Matrix

```
| Req ID | Requirement | Use Case | Test Case | Status |
|--------|-------------|----------|-----------|--------|
| FR-001 | Browse products | UC-001 | TC-001 | Complete |
| FR-002 | Add to cart | UC-002 | TC-002 | In Progress |
| FR-003 | Checkout | UC-003 | TC-003 | Not Started |
| NFR-001 | Performance | - | TC-100 | Complete |
```

## Change Management

### Change Request Template
```
Change Request ID: CR-001
Date: 2024-01-15
Requested By: Jane Doe
Priority: High

Description:
Add ability to save items for later (wishlist feature)

Business Justification:
Customers frequently browse but don't purchase immediately. A wishlist feature would increase engagement and conversion.

Impact Analysis:
- Development effort: 3 weeks
- Cost: $15,000
- Dependencies: User authentication
- Risks: Scope creep, timeline delay

Recommendation: Approve for next phase

Approval:
[ ] Approved  [ ] Rejected  [ ] Deferred
```

## Quick Reference

### Requirements Gathering Checklist
- [ ] Stakeholders identified
- [ ] Interview questions prepared
- [ ] Sessions scheduled
- [ ] Current state documented
- [ ] Pain points identified
- [ ] Requirements elicited
- [ ] Requirements prioritized
- [ ] Requirements documented
- [ ] Stakeholders reviewed
- [ ] Sign-off obtained

### BRD Review Checklist
- [ ] Business objectives clear
- [ ] Scope well-defined
- [ ] Stakeholders identified
- [ ] Requirements complete
- [ ] Acceptance criteria defined
- [ ] Assumptions documented
- [ ] Constraints identified
- [ ] Risks assessed
- [ ] Timeline realistic
- [ ] Approval obtained

## When to Escalate

- Conflicting requirements → Facilitate stakeholder meeting
- Scope creep → Engage project manager
- Technical feasibility concerns → Engage technical architect
- Budget constraints → Engage project sponsor
- Timeline risks → Engage project manager

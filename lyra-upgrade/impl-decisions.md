# Implementation Decisions Log

**Purpose**: Record every non-obvious design decision made during implementation.
Each entry must include: date, workstream, the decision, the alternatives considered,
and why this choice was made.

---

## 2026-05-31 — Tier 1 Kickoff

### DEC-001: Effort Scale as standalone package vs. extending existing router

**Decision**: Create a new `lyra-effort` package for the effort scale module.
**Alternatives considered**:
- (A) Add effort fields directly to `lyra-router`'s `ModelTier` enum
- (B) Create standalone `lyra-effort` package
**Rationale**: (B) chosen because:
1. `ModelTier` represents model capability (haiku/standard/premium); effort represents
   reasoning budget (low→ultracode). These are orthogonal dimensions — a "standard" model
   can run at "xhigh" effort, and a "premium" model can run at "low" effort.
2. The effort scale is used by the CLI (`/effort` command), the router, and the workflow
   engine — it's a cross-cutting concern that shouldn't be coupled to any one package.
3. Keeping it separate avoids circular dependencies (router→effort→workflow→router).

### DEC-002: Python dataclasses vs Pydantic for effort models

**Decision**: Use frozen dataclasses (matching existing `lyra-router` convention).
**Alternatives considered**:
- (A) Pydantic BaseModel with validation
- (B) Python frozen dataclass
**Rationale**: (B) chosen because the existing `lyra-router` package already uses frozen
dataclasses for `ModelAssignment`, `RoutingDecision`, `Provider` etc. Consistency with
existing codebase conventions outweighs Pydantic's validation features for these simple
data objects. We add manual validation in the `EffortManager` class instead.

---

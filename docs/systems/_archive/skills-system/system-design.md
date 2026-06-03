# Skills System Design

**Version:** 2.0  
**Status:** Production  
**Last Updated:** 2026-06-02

## Overview

This document provides detailed design specifications for the skills system, including data models, algorithms, APIs, state management, and scalability considerations.

## Data Models

### 1. SkillManifest

Core data structure representing a loaded skill.

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SkillManifest:
    """
    Immutable representation of a parsed SKILL.md file.
    
    All fields are read-only after loading. Modifications require
    creating a new instance via the optimizer or extractor.
    """
    id: str                     # Stable identifier (default: parent dir name)
    name: str                   # Human-readable display name
    description: str            # One-liner for router matching
    body: str                   # Full Markdown content
    version: str                # Semver string (e.g., "1.2.3")
    keywords: list[str]         # Trigger phrases for activation
    applies_to: list[str]       # File glob patterns (e.g., "**/*.py")
    requires: list[str]         # Python package dependencies
    progressive: bool           # True = load body on activation only
    allowed_tools: list[str]    # Tool permission allowlist
    path: Path | None           # Source file path
    extras: dict[str, Any]      # Forward-compatible unknown fields
    
    def matches_file(self, file_path: str) -> bool:
        """Check if skill applies to given file via glob matching."""
        if not self.applies_to:
            return True  # No restriction = applies to all
        return any(Path(file_path).match(pattern) for pattern in self.applies_to)
```

**Field Constraints:**
- `id`: 1-64 chars, alphanumeric + hyphen/underscore/dot
- `name`: 1-200 chars
- `description`: 1-500 chars (optimal: 50-150 for routing)
- `body`: 1-50,000 chars (optimal: <10,000 for token efficiency)
- `version`: Valid semver or empty string
- `keywords`: 0-20 items, each 1-100 chars
- `applies_to`: 0-50 glob patterns
- `requires`: 0-20 package names
- `allowed_tools`: 0-50 tool names

### 2. SkillStats

Runtime statistics tracked in the ledger.

```python
@dataclass
class SkillStats:
    """
    Outcome tracking for quality scoring and curation.
    
    Written to skill_ledger.json on every outcome recording.
    """
    skill_id: str
    successes: int              # Count of successful activations
    failures: int               # Count of failed activations
    last_used_at: float         # Unix timestamp of most recent use
    history: list[SkillOutcome] # Last 50 outcomes (FIFO)
    
    @property
    def total_activations(self) -> int:
        return self.successes + self.failures
    
    @property
    def success_rate(self) -> float:
        if self.total_activations == 0:
            return 0.0
        return self.successes / self.total_activations
    
    @property
    def failure_rate(self) -> float:
        return 1.0 - self.success_rate

@dataclass
class SkillOutcome:
    """Individual outcome record."""
    timestamp: float            # Unix timestamp
    success: bool               # True = success, False = failure
    error_kind: str | None      # Error category (e.g., "timeout", "parse_error")
    latency_ms: float | None    # Execution time in milliseconds
    context: dict[str, Any]     # Additional metadata
```

**History Management:**
- Circular buffer: Last 50 outcomes preserved
- Oldest entries dropped when limit exceeded
- Used for trend analysis and drift detection

### 3. CuratorResult

Output from the curator's grading process.

```python
from enum import Enum

class CuratorTier(Enum):
    PROMOTE = "promote"    # High quality, feature prominently
    KEEP = "keep"          # Healthy, no action needed
    WATCH = "watch"        # Marginal, monitor closely
    REWRITE = "rewrite"    # Low quality, needs improvement
    RETIRE = "retire"      # Stale or harmful, remove

@dataclass
class SkillReport:
    """Per-skill curation analysis."""
    skill_id: str
    tier: CuratorTier
    utility_score: float        # -1.1 to +1.1
    activations: int
    success_rate: float
    stale_days: int | None
    size_lines: int
    rationale: str              # Human-readable explanation
    suggested_action: str       # CLI command or "no action"

@dataclass
class CuratorReport:
    """Full catalog analysis."""
    timestamp: float
    total_skills: int
    reports: list[SkillReport]
    summary: dict[CuratorTier, int]  # Count per tier
```

### 4. ExtractorInput & Output

Skill extraction data structures.

```python
@dataclass
class ExtractorInput:
    """Input to skill extraction from trajectory."""
    task_description: str
    tool_sequence: list[str]     # Tool names in order
    step_descriptions: list[str] # Human-readable step summaries
    success: bool
    duration_ms: float
    tokens_used: int
    existing_skill_ids: set[str] # For collision detection
    
@dataclass
class RubricResult:
    """Individual rubric criterion result."""
    criterion: str
    passed: bool
    severity: str               # "HARD" | "SOFT"
    message: str
    
@dataclass
class ExtractorOutput:
    """Skill proposal from extractor."""
    requires_user_review: bool = True
    proposal_type: str          # "new" | "refinement" | "feedback_only"
    slug: str
    proposed_body: str
    rubric_results: list[RubricResult]
    confidence: float           # 0.0-1.0
```

## Core Algorithms

### 1. Utility Scoring Algorithm

**Purpose:** Compute single scalar quality metric from outcome history.

**Formula:**
```
base_score = (successes - failures) / (successes + failures)

age_days = (now - last_used_at) / 86400

if age_days >= 60:
    return base_score

decay_factor = max(0.0, 1.0 - age_days / 60)
recency_boost = 0.10 * (1.0 if age_days < 7 else decay_factor)

utility = base_score + copysign(recency_boost, base_score)
```

**Properties:**
- Range: [-1.1, +1.1]
- Monotonic in success rate
- Time-aware: Recent activity boosted
- Sign-preserving: Bad skills don't get positive boost

**Example Values:**

| Successes | Failures | Age (days) | Utility |
|-----------|----------|------------|---------|
| 10 | 0 | 3 | +1.10 |
| 8 | 2 | 3 | +0.70 |
| 5 | 5 | 3 | +0.05 |
| 2 | 8 | 3 | -0.65 |
| 10 | 0 | 65 | +1.00 |
| 5 | 5 | 65 | 0.00 |

### 2. Token Overlap Routing Algorithm

**Purpose:** Fast deterministic skill selection using lexical similarity.

**Steps:**

1. **Tokenization:**
```python
def tokenize(text: str) -> set[str]:
    """
    Lowercase, split on whitespace, filter stopwords,
    apply stemming, expand synonyms.
    """
    tokens = text.lower().split()
    tokens = [t for t in tokens if t not in STOPWORDS]
    tokens = [stem(t) for t in tokens]
    tokens = [SYNONYMS.get(t, t) for t in tokens]
    return set(tokens)

STOPWORDS = {"i", "to", "the", "a", "an", "of", "in", "on", "at", 
             "for", "and", "or", "with", "from", "by", "is", "this", 
             "that", "be", "need", "want", "please", "it", "into"}

SYNONYMS = {
    "change": "edit", "modify": "edit", "update": "edit",
    "fix": "edit", "patch": "edit", "refactor": "edit",
    "check": "review", "audit": "review",
    "find": "localize", "search": "localize",
    "test": "test-gen", "tests": "test-gen",
}

def stem(word: str) -> str:
    """Remove common suffixes."""
    for suffix in ["ing", "ed", "s"]:
        if word.endswith(suffix):
            return word[:-len(suffix)]
    return word
```

2. **Scoring:**
```python
def score_skill(query_tokens: set[str], skill: SkillManifest) -> float:
    """
    Intersection size between query and skill tokens.
    Skill tokens = description + name + keywords.
    """
    skill_text = f"{skill.description} {skill.name} {' '.join(skill.keywords)}"
    skill_tokens = tokenize(skill_text)
    
    overlap = query_tokens & skill_tokens
    return len(overlap)
```

3. **Ranking:**
```python
def route(query: str, skills: list[SkillManifest], top_k: int = 5) -> list[SkillManifest]:
    """Return top-k skills by overlap score."""
    query_tokens = tokenize(query)
    scored = [(score_skill(query_tokens, s), s) for s in skills]
    scored.sort(reverse=True, key=lambda x: x[0])
    return [s for score, s in scored[:top_k] if score > 0]
```

**Complexity:**
- Tokenization: O(n) where n = text length
- Scoring: O(m) where m = number of skills
- Total: O(n + m) – linear in catalog size

**Performance:** 5ms for 100 skills, 50ms for 500 skills

### 3. Skill Activation Algorithm

**Purpose:** Select which skills to inject into current turn's system prompt.

**Priority Order:**
1. Force-activated (explicit CLI flags)
2. Explicit invocations (`USE SKILL: <id>`)
3. Keyword matches (substring in prompt)

**Implementation:**
```python
def select_active_skills(
    prompt: str,
    all_skills: list[SkillManifest],
    force_ids: set[str],
    ledger: SkillLedger,
    max_active: int = 6,
    max_body_chars: int = 4096,
) -> list[ActiveSkill]:
    """
    Select skills to inject into system prompt.
    Returns at most max_active skills.
    """
    active = []
    used_ids = set()
    
    # Priority 1: Force-activated
    for skill_id in force_ids:
        skill = get_skill_by_id(skill_id, all_skills)
        if skill and skill_id not in used_ids:
            active.append(ActiveSkill(skill, "force-activated"))
            used_ids.add(skill_id)
    
    # Priority 2: Explicit invocations
    explicit_pattern = r"USE\s+SKILL\s*:\s*([A-Za-z0-9_\-./]+)"
    for match in re.finditer(explicit_pattern, prompt, re.IGNORECASE):
        skill_id = match.group(1)
        skill = get_skill_by_id(skill_id, all_skills)
        if skill and skill_id not in used_ids:
            active.append(ActiveSkill(skill, f"explicit: {match.group(0)}"))
            used_ids.add(skill_id)
    
    # Priority 3: Keyword matches
    keyword_matches = []
    for skill in all_skills:
        if skill.id in used_ids:
            continue
        for keyword in skill.keywords:
            if keyword.lower() in prompt.lower():
                utility = ledger.utility_score(skill.id)
                keyword_matches.append((utility, skill, keyword))
                break
    
    # Sort by utility, add until limit reached
    keyword_matches.sort(reverse=True, key=lambda x: x[0])
    for utility, skill, keyword in keyword_matches:
        if len(active) >= max_active:
            break
        active.append(ActiveSkill(skill, f"keyword: {keyword}"))
        used_ids.add(skill.id)
    
    # Load bodies for progressive skills
    for item in active:
        if item.manifest.progressive:
            item.body = load_skill_body(item.manifest.path)
        else:
            item.body = item.manifest.body
        
        # Truncate if needed
        if len(item.body) > max_body_chars:
            item.body = item.body[:max_body_chars] + "\n\n[... truncated]"
    
    return active
```

**Complexity:** O(n + k log k) where n = catalog size, k = keyword matches

### 4. Bounded Mutation Algorithm

**Purpose:** Apply constrained edits to skill bodies during optimization.

**Mutation Types:**
```python
class MutationStrategy(Enum):
    ADD_EXAMPLE = "add_example"         # Insert worked example
    ADD_CONSTRAINT = "add_constraint"   # Add guardrail
    RESTRUCTURE = "restructure"         # Reorder sections
    ADD_EDGE_CASE = "add_edge_case"     # Cover failure mode

@dataclass
class Mutation:
    strategy: MutationStrategy
    old_text: str          # Must appear exactly once
    new_text: str          # Replacement
    target_section: str    # Which section modified
    reasoning: str         # Why this helps
```

**Application:**
```python
def apply_mutation(skill_body: str, mutation: Mutation) -> tuple[str, bool]:
    """
    Apply mutation via single string replacement.
    Returns (new_body, success).
    """
    # Count occurrences
    count = skill_body.count(mutation.old_text)
    
    if count == 0:
        return skill_body, False  # Text not found
    
    if count > 1:
        return skill_body, False  # Ambiguous match
    
    # Exactly one match - apply replacement
    new_body = skill_body.replace(mutation.old_text, mutation.new_text)
    return new_body, True
```

**Constraints:**
- Maximum 50 tokens changed per mutation
- Must preserve frontmatter structure
- Cannot remove section headers
- Cannot change skill ID or name

## APIs

### 1. Loader API

```python
from lyra_skills import load_skills, SkillManifest
from pathlib import Path

# Load from multiple roots
skills = load_skills([
    Path.cwd() / ".lyra/skills",      # Project-local
    Path.home() / ".lyra/skills",     # User-global
    Path(__file__).parent / "packs",  # Shipped packs
])

# Access by ID
skill = next((s for s in skills if s.id == "test-gen"), None)

# Filter by file applicability
python_skills = [s for s in skills if s.matches_file("app.py")]

# Filter by keyword
review_skills = [s for s in skills if "review" in s.keywords]
```

### 2. Router API

```python
from lyra_skills import SkillRouter

# Default token overlap router
router = SkillRouter(skills)
matches = router.route("write unit tests for this function", top_k=5)

# With Argus cascade (optional)
from lyra_skills import LyraArgusCascade

cascade = LyraArgusCascade(mode="auto")
router = router.with_argus(cascade)
matches = router.route("write unit tests", top_k=5)

# Get system prompt index
index_text = router.system_prompt_index(limit=10)
# Returns: "Available skills:\n- test-gen: Generate unit tests...\n..."
```

### 3. Activator API

```python
from lyra_skills import select_active_skills, render_active_block

# Select skills for current turn
active = select_active_skills(
    prompt="write tests for auth.py",
    all_skills=skills,
    force_ids=set(),
    ledger=ledger,
    max_active=6,
)

# Render for system prompt injection
prompt_block = render_active_block(active)
```

### 4. Ledger API

```python
from lyra_skills import SkillLedger, SkillOutcome

ledger = SkillLedger.load()

# Record outcome
ledger.record_outcome(
    skill_id="test-gen",
    success=True,
    error_kind=None,
    latency_ms=250.0,
)

# Get stats
stats = ledger.get_stats("test-gen")
print(f"Success rate: {stats.success_rate:.2%}")

# Compute utility
utility = ledger.utility_score("test-gen")
print(f"Utility: {utility:+.2f}")

# Get top performers
top_10 = ledger.top_n(n=10)

# Save to disk
ledger.save()
```

### 5. Curator API

```python
from lyra_skills import curate, CuratorTier

# Run curation analysis
report = curate(skills, ledger)

# Filter by tier
to_retire = [r for r in report.reports if r.tier == CuratorTier.RETIRE]
to_rewrite = [r for r in report.reports if r.tier == CuratorTier.REWRITE]

# Generate markdown report
markdown = report.to_markdown()
with open("curator-report.md", "w") as f:
    f.write(markdown)
```

### 6. Extractor API

```python
from lyra_skills import extract_candidate, ExtractorInput

# Prepare input from trajectory
input_data = ExtractorInput(
    task_description="Write unit tests for auth module",
    tool_sequence=["Read", "Grep", "Write", "Bash", "Read"],
    step_descriptions=[
        "Read auth.py to understand functions",
        "Search for existing tests",
        "Write test_auth.py with 5 test cases",
        "Run pytest on new tests",
        "Verify all tests passed",
    ],
    success=True,
    duration_ms=12500.0,
    tokens_used=3500,
    existing_skill_ids={"test-gen", "code-review"},
)

# Extract candidate
output = extract_candidate(input_data)

if output.proposal_type == "new":
    print(f"New skill proposed: {output.slug}")
    print(f"Confidence: {output.confidence:.2%}")
elif output.proposal_type == "refinement":
    print(f"Refinement for existing skill: {output.slug}")
else:
    print("Feedback only - did not meet rubric criteria")
```

### 7. Optimizer API

```python
from lyra_skills import optimize_skill, OptimizeResult

# Define evaluation scenarios
scenarios = [
    ("write tests for login function", "Must generate pytest tests"),
    ("add unit tests", "Must use correct test framework"),
    ("test edge cases", "Must cover null inputs and boundaries"),
]

# Run optimization
result = optimize_skill(
    skill_id="test-gen",
    current_md=skill.body,
    scenarios=scenarios,
    llm=llm_provider,
    max_rounds=20,
    target_pass_rate=1.0,
)

print(f"Initial score: {result.initial_score:.2%}")
print(f"Final score: {result.final_score:.2%}")
print(f"Rounds taken: {result.rounds_taken}")
print(f"Mutations accepted: {result.mutations_accepted}")

if result.final_score >= 0.8:
    # Deploy optimized version
    skill_manager.update_skill("test-gen", result.final_md)
```

## State Management

### 1. Ledger Persistence

**File Format:** JSON
**Path:** `$LYRA_HOME/skill_ledger.json`

**Structure:**
```json
{
  "version": "2.0",
  "skills": {
    "test-gen": {
      "skill_id": "test-gen",
      "successes": 22,
      "failures": 3,
      "last_used_at": 1717329600.0,
      "history": [
        {
          "timestamp": 1717329600.0,
          "success": true,
          "error_kind": null,
          "latency_ms": 250.0,
          "context": {}
        }
      ]
    }
  }
}
```

**Write Strategy:**
1. Serialize to JSON string
2. Write to temporary file (`skill_ledger.json.tmp`)
3. Atomic rename via `os.replace()` (crash-safe)
4. Delete temporary file on error

**Concurrency:** Not thread-safe. Use file locking if multiple processes write.

### 2. Mutation Log Persistence

**File Format:** JSONL (JSON Lines)
**Path:** `$LYRA_HOME/skill_mutations.jsonl`

**Line Format:**
```json
{"timestamp": 1717329600.0, "skill_id": "test-gen", "round": 5, "strategy": "add_example", "pre_score": 0.75, "post_score": 0.82, "accepted": true, "reasoning": "Added example for async tests"}
```

**Append-Only:** Each optimization round appends one line.

**Rotation:** When file exceeds 10MB, rotate to `skill_mutations.jsonl.1` and start fresh.

### 3. Skill State Overrides

**File Format:** JSON
**Path:** `$LYRA_HOME/skill_state.json`

**Structure:**
```json
{
  "version": "1.0",
  "disabled": ["old-skill-v1", "experimental-feature"],
  "enabled": [],
  "locked": ["atomic-skills", "tdd-sprint"]
}
```

**Semantics:**
- `disabled`: Skills excluded from system prompt
- `enabled`: Forward-compat (currently unused)
- `locked`: Shipped packs, always active

**Update Pattern:**
```python
state = SkillState.load()
state.disabled.add("skill-to-disable")
state.save()
```

## Scalability Considerations

### 1. Catalog Size Scaling

**Current:** 100-200 skills
**Tested:** 1,000 skills
**Theoretical Maximum:** 10,000+ skills

**Bottlenecks at Scale:**

| Catalog Size | Load Time | Route Time | Memory |
|--------------|-----------|------------|--------|
| 100 | 50ms | 5ms | 200 KB |
| 500 | 200ms | 25ms | 1 MB |
| 1,000 | 400ms | 50ms | 2 MB |
| 5,000 | 2s | 250ms | 10 MB |
| 10,000 | 4s | 500ms | 20 MB |

**Mitigation Strategies:**

1. **Lazy Loading:**
   - Load frontmatter only (5-10 KB per skill)
   - Load body on activation (50-200 KB per skill)
   - Current implementation already uses this

2. **Indexing:**
   - Pre-compute token sets during discovery
   - Cache routing results for common queries
   - Implemented in token overlap router

3. **Sharding:**
   - Split catalog by domain (e.g., language-specific)
   - Load only relevant shards based on context
   - Not yet implemented

### 2. Outcome History Scaling

**Current:** 50 outcomes per skill
**Total Storage:** 50 × 200 skills × 200 bytes = 2 MB

**At Scale (10K skills):** 100 MB

**Mitigation:**
- Compress old outcomes to summary statistics
- Keep only last 7 days at full resolution
- Archive older data to separate files

### 3. Optimization Cost Scaling

**Per Round Cost:** `len(scenarios) + 2` LLM calls

| Scenarios | Rounds | Total Calls | Cost (GPT-4) |
|-----------|--------|-------------|--------------|
| 5 | 10 | 70 | $0.21 |
| 5 | 20 | 110 | $0.33 |
| 10 | 20 | 220 | $0.66 |
| 20 | 50 | 1,050 | $3.15 |

**Mitigation:**
- Use cheaper models for executor (Haiku, GPT-3.5-turbo)
- Cache scenario evaluations
- Early termination on convergence

### 4. Concurrent Access Patterns

**Read-Heavy:** 1000:1 read-to-write ratio

**Strategies:**
- In-memory caching of skill manifests (already implemented)
- Read-through cache for routing results
- No locking needed for reads

**Write Contention:**
- Ledger updates: ~1-10 per turn (low contention)
- Mutation log: Append-only (no contention)
- Skill installations: Rare (~1 per day)

### 5. Argus Cascade Scaling

**With Embeddings:**
- Model loading: 50 MB (one-time)
- Encoding: 10ms per skill (one-time on catalog change)
- Search: 20ms + 5ms per skill

**At 10K Skills:**
- Initial encoding: 100 seconds (cacheable)
- Per-query: 20ms + 50ms = 70ms (still acceptable)

**Mitigation:**
- Pre-encode catalog offline
- Use quantized embeddings (8-bit vs 32-bit = 4× compression)
- Implement approximate nearest neighbors (HNSW, FAISS)

## Caching Strategy

### 1. Manifest Cache

**When:** After load_skills()
**TTL:** Session lifetime
**Invalidation:** Manual catalog refresh

**Implementation:**
```python
_MANIFEST_CACHE: dict[Path, list[SkillManifest]] = {}

def load_skills(roots: list[Path]) -> list[SkillManifest]:
    cache_key = tuple(sorted(roots))
    if cache_key in _MANIFEST_CACHE:
        return _MANIFEST_CACHE[cache_key]
    
    manifests = _discover_and_parse(roots)
    _MANIFEST_CACHE[cache_key] = manifests
    return manifests
```

### 2. Routing Cache

**When:** After expensive routing (Argus cascade)
**TTL:** 5 minutes
**Invalidation:** Time-based expiry

**Implementation:**
```python
@lru_cache(maxsize=128)
def route_cached(query: str, timestamp_5min: int) -> list[SkillManifest]:
    return route(query)

# Usage
bucket = int(time.time() / 300)  # 5-minute buckets
results = route_cached(query, bucket)
```

### 3. Utility Score Cache

**When:** After utility_score() computation
**TTL:** Until next outcome recorded
**Invalidation:** Explicit on ledger.record_outcome()

---

**Document Status:** Complete  
**Implementation Status:** Production (lyra-skills v2.0)  
**Last Review:** 2026-06-02

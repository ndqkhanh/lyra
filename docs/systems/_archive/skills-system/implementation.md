# Skills System Implementation Guide

**Version:** 2.0  
**Status:** Production  
**Last Updated:** 2026-06-02

## Overview

This guide provides practical implementation instructions for integrating and using the skills system, including code examples, configuration, deployment, integration patterns, and testing strategies.

## Quick Start

### Installation

```bash
# Install lyra-skills package
pip install lyra-skills

# Optional: Install Argus cascade dependencies
pip install lyra-skills[argus]

# Verify installation
python -c "from lyra_skills import load_skills; print('✓ Skills system ready')"
```

### Basic Usage

```python
from lyra_skills import load_skills, SkillRouter, select_active_skills
from pathlib import Path

# 1. Load skills from multiple sources
skills = load_skills([
    Path.cwd() / ".lyra/skills",      # Project-local
    Path.home() / ".lyra/skills",     # User-global
    Path(__file__).parent / "packs",  # Shipped packs
])

print(f"Loaded {len(skills)} skills")

# 2. Create router
router = SkillRouter(skills)

# 3. Route user query to relevant skills
user_prompt = "write unit tests for the authentication module"
matches = router.route(user_prompt, top_k=5)

print(f"Top matches: {[s.id for s in matches]}")

# 4. Select skills to activate
from lyra_skills import SkillLedger

ledger = SkillLedger.load()
active = select_active_skills(
    prompt=user_prompt,
    all_skills=skills,
    force_ids=set(),
    ledger=ledger,
    max_active=6,
)

print(f"Activated {len(active)} skills")

# 5. Render for system prompt
from lyra_skills import render_active_block

prompt_block = render_active_block(active)
print(prompt_block)
```

## Configuration

### Directory Structure Setup

```bash
# Create standard directory layout
mkdir -p ~/.lyra/skills
mkdir -p ~/.lyra/skill-curator
mkdir -p .lyra/skills

# Initialize ledger
python -c "
from lyra_skills import SkillLedger
ledger = SkillLedger()
ledger.save()
print('✓ Ledger initialized')
"
```

### Environment Variables

```bash
# Optional: Override default paths
export LYRA_HOME="$HOME/.lyra"
export LYRA_SKILLS_PATH=".lyra/skills:$HOME/.lyra/skills"
export LYRA_ARGUS_MODE="auto"  # auto | keyword | semantic
```

### Configuration File

Create `~/.lyra/config.yaml`:

```yaml
skills:
  # Discovery paths (searched in order)
  paths:
    - .lyra/skills          # Project-local (highest priority)
    - ~/.lyra/skills        # User-global
    - ~/.claude/skills      # Claude Code compatibility
  
  # Activation limits
  max_active: 6             # Max skills per turn
  max_body_chars: 4096      # Max chars per skill body
  
  # Router configuration
  router:
    default: "token_overlap"  # token_overlap | argus
    argus_mode: "auto"        # auto | keyword | semantic
    top_k: 5                  # Max results from router
  
  # Curator configuration
  curator:
    run_on_start: false
    schedule: "0 3 * * *"     # Daily at 3am (cron format)
    thresholds:
      promote: 0.85
      keep: 0.65
      watch: 0.40
      rewrite: 0.40
      retire: 0.20
  
  # Optimizer configuration
  optimizer:
    max_rounds: 20
    target_pass_rate: 1.0
    scenario_count: 5
```

## Creating Skills

### Skill Template

```bash
# Create new skill directory
mkdir -p ~/.lyra/skills/my-skill

# Create SKILL.md
cat > ~/.lyra/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: Brief one-line description for routing
version: 1.0.0
keywords:
  - keyword one
  - keyword two
  - keyword three
applies_to:
  - "**/*.py"
  - "**/*.ts"
progressive: false
allowed_tools: [Read, Write, Grep, Bash]
---

# My Skill

## When to Use

Use this skill when the user asks to [describe scenario].

## Steps

1. First step with clear action
2. Second step with expected outcome
3. Third step with validation

## Examples

### Example 1: Basic Usage

```python
# Show concrete example code
def example_function():
    pass
```

### Example 2: Edge Case

```python
# Show how to handle edge cases
def handle_edge_case():
    pass
```

## Anti-Patterns

- ❌ Don't do this (explain why)
- ❌ Avoid this pattern (explain alternative)

## Success Criteria

- [ ] Criterion 1 met
- [ ] Criterion 2 met
- [ ] Tests pass
EOF
```

### Skill Best Practices

**1. Clear Description (Critical for Routing):**

```yaml
# ❌ Bad: Too vague
description: "Help with code"

# ✅ Good: Specific and actionable
description: "Generate unit tests using pytest with fixtures, mocks, and parametrize"
```

**2. Focused Keywords (3-7 recommended):**

```yaml
# ❌ Bad: Too generic or too many
keywords: [code, programming, help, fix, write, read, test, debug, ...]

# ✅ Good: Specific trigger phrases
keywords:
  - write tests
  - generate unit tests
  - test coverage
  - pytest
```

**3. Progressive Loading for Large Skills:**

```yaml
# Use progressive: true for skills >2KB
progressive: true  # Body loaded only when activated
```

**4. Tool Restrictions for Safety:**

```yaml
# Limit to minimal required tools
allowed_tools: [Read, Grep, Write]  # No Bash, no network tools
```

## Integration Patterns

### Pattern 1: Standalone CLI Tool

```python
#!/usr/bin/env python3
"""Standalone skills-powered CLI."""

import sys
from pathlib import Path
from lyra_skills import load_skills, SkillRouter, select_active_skills
from lyra_skills import SkillLedger, render_active_block

def main():
    # Load skills
    skills = load_skills([
        Path.cwd() / ".lyra/skills",
        Path.home() / ".lyra/skills",
    ])
    
    # Get user query
    query = " ".join(sys.argv[1:])
    if not query:
        print("Usage: ./skill-cli.py <query>")
        sys.exit(1)
    
    # Route and activate
    router = SkillRouter(skills)
    matches = router.route(query, top_k=5)
    
    ledger = SkillLedger.load()
    active = select_active_skills(
        prompt=query,
        all_skills=matches,
        force_ids=set(),
        ledger=ledger,
        max_active=3,
    )
    
    # Print active skills
    print(render_active_block(active))
    
    # Record usage
    for skill_entry in active:
        ledger.record_outcome(
            skill_id=skill_entry.manifest.id,
            success=True,  # Set based on actual outcome
        )
    ledger.save()

if __name__ == "__main__":
    main()
```

### Pattern 2: LLM Integration

```python
from anthropic import Anthropic
from lyra_skills import load_skills, SkillRouter, select_active_skills
from lyra_skills import SkillLedger, render_active_block

class SkillAugmentedAgent:
    def __init__(self, anthropic_api_key: str):
        self.client = Anthropic(api_key=anthropic_api_key)
        self.skills = load_skills([...])
        self.router = SkillRouter(self.skills)
        self.ledger = SkillLedger.load()
    
    def chat(self, user_message: str) -> str:
        # Route skills
        matches = self.router.route(user_message, top_k=5)
        
        # Activate skills
        active = select_active_skills(
            prompt=user_message,
            all_skills=matches,
            force_ids=set(),
            ledger=self.ledger,
            max_active=6,
        )
        
        # Build system prompt
        skill_block = render_active_block(active)
        system_prompt = f"""You are a helpful AI assistant with specialized skills.

{skill_block}

When using a skill, follow its instructions precisely."""
        
        # Call LLM
        response = self.client.messages.create(
            model="claude-opus-4-20240229",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        
        # Record outcomes
        success = self._evaluate_response(response)
        for skill_entry in active:
            self.ledger.record_outcome(
                skill_id=skill_entry.manifest.id,
                success=success,
            )
        self.ledger.save()
        
        return response.content[0].text
    
    def _evaluate_response(self, response) -> bool:
        """Evaluate if response successfully used skills."""
        # Implement your evaluation logic
        return True  # Placeholder

# Usage
agent = SkillAugmentedAgent(api_key="...")
response = agent.chat("write unit tests for auth.py")
print(response)
```

### Pattern 3: FastAPI Service

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from lyra_skills import load_skills, SkillRouter, select_active_skills
from lyra_skills import SkillLedger

app = FastAPI(title="Skills API")

# Load skills on startup
skills = load_skills([...])
router = SkillRouter(skills)
ledger = SkillLedger.load()

class SkillQuery(BaseModel):
    query: str
    max_active: int = 6
    force_ids: list[str] = []

class SkillResponse(BaseModel):
    active_skills: list[dict]
    system_prompt: str

@app.post("/skills/activate", response_model=SkillResponse)
async def activate_skills(query: SkillQuery):
    """Activate skills for a given query."""
    try:
        # Route
        matches = router.route(query.query, top_k=10)
        
        # Activate
        active = select_active_skills(
            prompt=query.query,
            all_skills=matches,
            force_ids=set(query.force_ids),
            ledger=ledger,
            max_active=query.max_active,
        )
        
        # Format response
        from lyra_skills import render_active_block
        prompt_block = render_active_block(active)
        
        return SkillResponse(
            active_skills=[
                {
                    "id": e.manifest.id,
                    "name": e.manifest.name,
                    "reason": e.reason,
                }
                for e in active
            ],
            system_prompt=prompt_block,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/skills/record-outcome")
async def record_outcome(skill_id: str, success: bool):
    """Record skill usage outcome."""
    ledger.record_outcome(skill_id, success=success)
    ledger.save()
    return {"status": "recorded"}

# Run with: uvicorn api:app --reload
```

### Pattern 4: Periodic Curation

```python
import schedule
import time
from lyra_skills import load_skills, SkillLedger, curate

def run_curation():
    """Run curator and save report."""
    print("Running curator...")
    skills = load_skills([...])
    ledger = SkillLedger.load()
    
    report = curate(skills, ledger)
    
    # Save report
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    report_path = f"~/.lyra/skill-curator/{timestamp}-report.md"
    
    with open(report_path, "w") as f:
        f.write(report.to_markdown())
    
    print(f"Report saved to {report_path}")
    
    # Act on retire recommendations
    from lyra_skills import CuratorTier
    to_retire = [r for r in report.reports if r.tier == CuratorTier.RETIRE]
    
    if to_retire:
        print(f"Retire recommendations: {[r.skill_id for r in to_retire]}")
        # Optionally: Auto-archive retired skills

# Schedule daily at 3am
schedule.every().day.at("03:00").do(run_curation)

# Run forever
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy skills
COPY .lyra/ /root/.lyra/
COPY skills/ /app/skills/

# Copy application
COPY app.py .

# Environment
ENV LYRA_HOME=/root/.lyra
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
```

**requirements.txt:**
```
lyra-skills>=2.0
anthropic>=0.18
fastapi>=0.109
uvicorn>=0.27
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  skills-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./skills:/app/skills
      - skill-data:/root/.lyra
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LYRA_ARGUS_MODE=auto
    command: uvicorn api:app --host 0.0.0.0 --port 8000

volumes:
  skill-data:
```

### Kubernetes Deployment

```yaml
# skills-deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: skills-config
data:
  config.yaml: |
    skills:
      max_active: 6
      router:
        default: "token_overlap"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: skills-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: skills-api
  template:
    metadata:
      labels:
        app: skills-api
    spec:
      containers:
      - name: api
        image: myorg/skills-api:2.0
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: anthropic-key
        volumeMounts:
        - name: config
          mountPath: /root/.lyra/config.yaml
          subPath: config.yaml
        - name: skills-data
          mountPath: /root/.lyra
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: skills-config
      - name: skills-data
        persistentVolumeClaim:
          claimName: skills-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: skills-api
spec:
  selector:
    app: skills-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Testing Strategies

### Unit Tests

```python
import pytest
from pathlib import Path
from lyra_skills import load_skills, SkillRouter
from lyra_skills import SkillLedger, utility_score

class TestSkillLoading:
    """Test skill discovery and parsing."""
    
    def test_load_skills_from_directory(self, tmp_path):
        """Test loading skills from a directory."""
        # Create test skill
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: Test skill for unit tests
keywords: [test, unit test]
---

# Test Skill

Test content.
""")
        
        # Load
        skills = load_skills([tmp_path])
        
        assert len(skills) == 1
        assert skills[0].id == "test-skill"
        assert skills[0].name == "test-skill"
        assert "test" in skills[0].keywords
    
    def test_duplicate_skill_resolution(self, tmp_path):
        """Test that later root wins on ID collision."""
        # Create two roots with same skill ID
        root1 = tmp_path / "root1" / "my-skill"
        root2 = tmp_path / "root2" / "my-skill"
        root1.mkdir(parents=True)
        root2.mkdir(parents=True)
        
        (root1 / "SKILL.md").write_text("---\nname: skill-v1\n---\nVersion 1")
        (root2 / "SKILL.md").write_text("---\nname: skill-v2\n---\nVersion 2")
        
        skills = load_skills([tmp_path / "root1", tmp_path / "root2"])
        
        assert len(skills) == 1
        assert skills[0].name == "skill-v2"  # Later root wins

class TestSkillRouting:
    """Test skill routing logic."""
    
    @pytest.fixture
    def test_skills(self):
        """Create test skills."""
        from lyra_skills import SkillManifest
        return [
            SkillManifest(
                id="test-gen",
                name="Test Generator",
                description="Generate unit tests using pytest",
                body="...",
                keywords=["test", "unit test", "pytest"],
                version="1.0.0",
                applies_to=[],
                requires=[],
                progressive=False,
                allowed_tools=[],
                path=None,
                extras={},
            ),
            SkillManifest(
                id="code-review",
                name="Code Review",
                description="Review code for bugs and issues",
                body="...",
                keywords=["review", "audit", "check code"],
                version="1.0.0",
                applies_to=[],
                requires=[],
                progressive=False,
                allowed_tools=[],
                path=None,
                extras={},
            ),
        ]
    
    def test_route_exact_keyword_match(self, test_skills):
        """Test routing with exact keyword match."""
        router = SkillRouter(test_skills)
        matches = router.route("write unit tests", top_k=5)
        
        assert len(matches) >= 1
        assert matches[0].id == "test-gen"
    
    def test_route_synonym_expansion(self, test_skills):
        """Test routing with synonym expansion."""
        router = SkillRouter(test_skills)
        # "check" should expand to "review"
        matches = router.route("check this code", top_k=5)
        
        assert any(m.id == "code-review" for m in matches)

class TestSkillLedger:
    """Test ledger operations."""
    
    def test_record_outcome(self, tmp_path):
        """Test recording skill outcome."""
        ledger = SkillLedger()
        
        ledger.record_outcome("test-skill", success=True)
        stats = ledger.get_stats("test-skill")
        
        assert stats.successes == 1
        assert stats.failures == 0
    
    def test_utility_score_calculation(self, tmp_path):
        """Test utility score formula."""
        ledger = SkillLedger()
        
        # Record outcomes
        ledger.record_outcome("test-skill", success=True)
        ledger.record_outcome("test-skill", success=True)
        ledger.record_outcome("test-skill", success=False)
        
        stats = ledger.get_stats("test-skill")
        utility = utility_score(stats)
        
        # (2 - 1) / (2 + 1) = 0.333...
        assert 0.3 < utility < 0.4

### Integration Tests

```python
import pytest
from lyra_skills import load_skills, SkillRouter, select_active_skills
from lyra_skills import SkillLedger, render_active_block

class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_skill_activation_flow(self, tmp_path):
        """Test complete flow from load to activation."""
        # Setup: Create test skill
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: Test skill
keywords: [test keyword]
---
# Test Skill Body
""")
        
        # 1. Load
        skills = load_skills([tmp_path])
        assert len(skills) == 1
        
        # 2. Route
        router = SkillRouter(skills)
        matches = router.route("use test keyword", top_k=5)
        assert len(matches) >= 1
        
        # 3. Activate
        ledger = SkillLedger()
        active = select_active_skills(
            prompt="use test keyword",
            all_skills=matches,
            force_ids=set(),
            ledger=ledger,
            max_active=6,
        )
        assert len(active) >= 1
        
        # 4. Render
        prompt_block = render_active_block(active)
        assert "test-skill" in prompt_block
        assert "Test Skill Body" in prompt_block
        
        # 5. Record outcome
        ledger.record_outcome("test-skill", success=True)
        stats = ledger.get_stats("test-skill")
        assert stats.successes == 1

### Performance Tests

```python
import time
import pytest
from lyra_skills import load_skills, SkillRouter

class TestPerformance:
    """Performance benchmarks."""
    
    @pytest.mark.benchmark
    def test_load_performance(self, benchmark_skills_dir):
        """Benchmark skill loading."""
        start = time.time()
        skills = load_skills([benchmark_skills_dir])
        duration = time.time() - start
        
        # Should load 100 skills in <200ms
        assert len(skills) == 100
        assert duration < 0.2
    
    @pytest.mark.benchmark
    def test_routing_performance(self, benchmark_skills):
        """Benchmark routing speed."""
        router = SkillRouter(benchmark_skills)
        
        start = time.time()
        for _ in range(100):
            router.route("test query", top_k=5)
        duration = time.time() - start
        
        # Should route 100 queries in <1s (10ms per query)
        assert duration < 1.0
    
    @pytest.mark.benchmark
    def test_memory_footprint(self, benchmark_skills):
        """Measure memory usage."""
        import sys
        
        initial = sys.getsizeof(benchmark_skills)
        router = SkillRouter(benchmark_skills)
        total = sys.getsizeof(router)
        
        # Should be <2MB for 100 skills
        assert total < 2_000_000

## Troubleshooting

### Common Issues

**Issue 1: Skills not loading**

```python
# Debug: Print discovered paths
from lyra_skills.loader import _discover_skill_paths

paths = _discover_skill_paths([Path("~/.lyra/skills")])
print(f"Found {len(paths)} SKILL.md files")
for p in paths:
    print(f"  {p}")
```

**Solution:** Verify SKILL.md files exist and have correct frontmatter.

**Issue 2: Skills not routing correctly**

```python
# Debug: Check token overlap
from lyra_skills.router import _tokens

query = "write unit tests"
query_tokens = _tokens(query)
print(f"Query tokens: {query_tokens}")

for skill in skills:
    skill_text = f"{skill.description} {' '.join(skill.keywords)}"
    skill_tokens = _tokens(skill_text)
    overlap = query_tokens & skill_tokens
    print(f"{skill.id}: {overlap}")
```

**Solution:** Add more keywords or use Argus cascade for semantic matching.

**Issue 3: Ledger corruption**

```python
# Recover from backup
import json
import shutil

ledger_path = Path.home() / ".lyra/skill_ledger.json"
backup_path = ledger_path.with_suffix(".json.bak")

if not ledger_path.exists() and backup_path.exists():
    shutil.copy(backup_path, ledger_path)
    print("Restored from backup")

# Validate
try:
    with open(ledger_path) as f:
        data = json.load(f)
    print(f"Ledger OK: {len(data.get('skills', {}))} skills")
except json.JSONDecodeError as e:
    print(f"Ledger corrupted: {e}")
    # Reinitialize
    from lyra_skills import SkillLedger
    ledger = SkillLedger()
    ledger.save()
```

### Debugging Tools

**1. Skill Inspector:**

```python
from lyra_skills import load_skills

skills = load_skills([...])

# Inspect specific skill
skill = next((s for s in skills if s.id == "test-gen"), None)
if skill:
    print(f"ID: {skill.id}")
    print(f"Name: {skill.name}")
    print(f"Description: {skill.description}")
    print(f"Keywords: {skill.keywords}")
    print(f"Progressive: {skill.progressive}")
    print(f"Body length: {len(skill.body)} chars")
```

**2. Router Debugger:**

```python
from lyra_skills import SkillRouter

router = SkillRouter(skills)

# Enable debug mode
router._debug = True

# Route with scoring details
matches = router.route("write tests", top_k=5)
for skill in matches:
    print(f"{skill.id}: score={skill._debug_score}")
```

**3. Ledger Inspector:**

```python
from lyra_skills import SkillLedger

ledger = SkillLedger.load()

# Top performers
top = ledger.top_n(n=10)
for stats in top:
    utility = ledger.utility_score(stats.skill_id)
    print(f"{stats.skill_id}: {utility:+.2f} ({stats.successes}/{stats.total_activations})")

# Bottom performers
all_stats = list(ledger.skills.values())
all_stats.sort(key=lambda s: ledger.utility_score(s.skill_id))
for stats in all_stats[:10]:
    utility = ledger.utility_score(stats.skill_id)
    print(f"{stats.skill_id}: {utility:+.2f} ({stats.successes}/{stats.total_activations})")
```

## Migration Guide

### From Legacy Skills System

**Step 1: Convert Old Format to New Format**

```python
# convert_skills.py
import yaml
from pathlib import Path

def convert_legacy_skill(old_path: Path) -> dict:
    """Convert old skill format to new format."""
    with open(old_path) as f:
        content = f.read()
    
    # Parse old frontmatter (different fields)
    # Old: trigger_patterns, tags, category
    # New: keywords, applies_to
    
    # ... conversion logic ...
    
    return new_frontmatter

# Run conversion
old_skills = Path("src/skills")
new_skills = Path(".lyra/skills")

for old_skill in old_skills.glob("*/SKILL.md"):
    new_frontmatter = convert_legacy_skill(old_skill)
    
    target_dir = new_skills / old_skill.parent.name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    with open(target_dir / "SKILL.md", "w") as f:
        f.write("---\n")
        yaml.dump(new_frontmatter, f)
        f.write("---\n\n")
        # Copy body...
```

**Step 2: Migrate Ledger Data**

```python
# migrate_ledger.py
from lyra_skills import SkillLedger

# Load old registry data
old_registry_path = Path("src/skills/registry.json")
with open(old_registry_path) as f:
    old_data = json.load(f)

# Create new ledger
new_ledger = SkillLedger()

for skill_id, old_stats in old_data.items():
    # Map old fields to new fields
    for _ in range(old_stats["successes"]):
        new_ledger.record_outcome(skill_id, success=True)
    for _ in range(old_stats["failures"]):
        new_ledger.record_outcome(skill_id, success=False)

new_ledger.save()
print(f"Migrated {len(old_data)} skills to new ledger")
```

## Best Practices Summary

### Do's ✅

1. **Use progressive loading** for skills >2KB
2. **Limit keywords** to 3-7 most relevant phrases
3. **Write specific descriptions** (50-150 chars optimal)
4. **Test skills** before deploying to production
5. **Monitor ledger** and run curator monthly
6. **Version skills** using semver
7. **Document anti-patterns** in skill body
8. **Use allowed_tools** to restrict permissions
9. **Run optimizer** on low-performing skills
10. **Keep skills focused** (<500 lines body)

### Don'ts ❌

1. **Don't use generic keywords** ("code", "help")
2. **Don't mix multiple capabilities** in one skill
3. **Don't hardcode paths** or secrets in skills
4. **Don't skip testing** after skill changes
5. **Don't ignore curator recommendations**
6. **Don't activate >6 skills** per turn (token waste)
7. **Don't bypass allowed_tools** restrictions
8. **Don't edit introspection fields** manually
9. **Don't skip validation** before publishing
10. **Don't ignore ledger growth** (archive old data)

---

**Document Status:** Complete  
**Implementation Status:** Production (lyra-skills v2.0)  
**Last Review:** 2026-06-02
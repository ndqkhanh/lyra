# Lyra v4.0 Migration Guide

**Version**: 1.0  
**Status**: 🚧 Draft  
**Last Updated**: 2026-05-21

---

## Overview

Complete guide for migrating from Lyra v3.x to v4.0. This document covers breaking changes, migration strategies, and step-by-step procedures to ensure a smooth transition.

---

## Table of Contents

1. [What's New in v4.0](#whats-new-in-v40)
2. [Breaking Changes](#breaking-changes)
3. [Migration Strategy](#migration-strategy)
4. [Step-by-Step Migration](#step-by-step-migration)
5. [Data Migration](#data-migration)
6. [Code Migration](#code-migration)
7. [Testing Migration](#testing-migration)
8. [Rollback Plan](#rollback-plan)

---

## What's New in v4.0

### Major Features

1. **5-Network Memory System**
   - Beliefs, Episodes, Entities, Procedures, Strategies
   - Replaces single-network v3.x memory
   - Better organization and recall

2. **Multi-Agent Architecture**
   - Primary, Specialist, Worker agents
   - Parallel execution
   - Specialized capabilities

3. **Advanced Planning**
   - Strategic decomposition
   - Multi-step reasoning
   - Adaptive execution

4. **Enhanced Safety**
   - Multi-layer validation
   - Budget management
   - Comprehensive auditing

5. **Improved Performance**
   - 3x faster memory recall
   - 2x faster agent response
   - Better resource utilization

### Improvements

- **Better Memory**: More organized, faster recall
- **Smarter Planning**: Strategic decomposition
- **Safer Execution**: Multi-layer validation
- **Faster Performance**: Optimized operations
- **Better Monitoring**: Comprehensive metrics

---

## Breaking Changes

### API Changes

#### Memory System

**v3.x**:
```python
# Single memory store
memory.store("content", importance=0.8)
memories = memory.recall("query")
```

**v4.0**:
```python
# Network-specific storage
memory.beliefs.store("content", importance=0.8)
memories = memory.beliefs.recall("query")
```

**Migration**: Update all memory operations to use specific networks.

#### Agent System

**v3.x**:
```python
# Single agent
agent = Agent()
result = agent.execute(task)
```

**v4.0**:
```python
# Agent hierarchy
primary = PrimaryAgent()
result = await primary.execute(task)  # Now async
```

**Migration**: Update to async/await pattern and use PrimaryAgent.

#### Configuration

**v3.x**:
```python
# Simple config
config = {
    "api_key": "...",
    "max_cost": 10.0
}
```

**v4.0**:
```python
# Structured config
from lyra.core.config import LyraConfig

config = LyraConfig(
    anthropic_api_key="...",
    default_max_cost_usd=10.0
)
```

**Migration**: Use LyraConfig class instead of dict.

### Database Schema Changes

**v3.x Schema**:
```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    content TEXT,
    importance REAL
);
```

**v4.0 Schema**:
```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    network TEXT NOT NULL,  -- NEW
    content TEXT NOT NULL,
    embedding BLOB,         -- NEW
    importance REAL DEFAULT 0.5,
    created_at REAL NOT NULL,
    accessed_at REAL NOT NULL,
    access_count INTEGER DEFAULT 0,
    metadata TEXT
);
```

**Migration**: Database migration script required.

### Removed Features

1. **Synchronous API**: All operations now async
2. **Global Memory**: Must specify network
3. **Simple Config**: Must use LyraConfig
4. **Direct Tool Access**: Must go through agents

---

## Migration Strategy

### Recommended Approach

```
Phase 1: Preparation (Week 1)
├── Backup existing data
├── Review breaking changes
├── Update dependencies
└── Test in development

Phase 2: Migration (Week 2)
├── Migrate database schema
├── Update code
├── Migrate data
└── Test thoroughly

Phase 3: Deployment (Week 3)
├── Deploy to staging
├── Validate functionality
├── Deploy to production
└── Monitor closely

Phase 4: Cleanup (Week 4)
├── Remove v3.x code
├── Update documentation
└── Train team
```

### Migration Options

#### Option 1: Big Bang (Recommended for Small Deployments)

- Migrate everything at once
- Shorter migration period
- Higher risk
- Best for: <1000 users, simple setup

#### Option 2: Gradual (Recommended for Large Deployments)

- Migrate in phases
- Run v3.x and v4.0 in parallel
- Lower risk
- Best for: >1000 users, complex setup

#### Option 3: Blue-Green

- Deploy v4.0 alongside v3.x
- Switch traffic gradually
- Easy rollback
- Best for: Critical systems

---

## Step-by-Step Migration

### Phase 1: Preparation

#### Step 1: Backup Everything

```bash
# Backup v3.x data
mkdir -p ~/lyra-migration/backups

# Backup database
cp ~/.lyra/v3/memory.db ~/lyra-migration/backups/memory.db.backup

# Backup configuration
cp ~/.lyra/v3/config.json ~/lyra-migration/backups/config.json.backup

# Backup logs
cp -r ~/.lyra/v3/logs ~/lyra-migration/backups/logs

# Create archive
tar -czf ~/lyra-migration/backups/v3-backup-$(date +%Y%m%d).tar.gz \
    ~/lyra-migration/backups/
```

#### Step 2: Install v4.0 (Parallel)

```bash
# Clone v4.0
git clone https://github.com/your-org/lyra.git ~/lyra-v4
cd ~/lyra-v4
git checkout v4.0

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Verify installation
lyra --version  # Should show v4.0.0
```

#### Step 3: Review Code Changes

```bash
# Generate diff report
cd ~/lyra-migration
git clone https://github.com/your-org/lyra.git v3
cd v3
git checkout v3.x

cd ..
git clone https://github.com/your-org/lyra.git v4
cd v4
git checkout v4.0

# Compare
diff -r ../v3/src ../v4/src > code-changes.diff
```

### Phase 2: Database Migration

#### Step 1: Create Migration Script

**File**: `scripts/migrate_v3_to_v4.py`

```python
"""Migrate Lyra v3.x to v4.0"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime


def migrate_database(v3_db_path: Path, v4_db_path: Path):
    """Migrate database from v3 to v4"""
    
    print("Starting database migration...")
    
    # Connect to databases
    v3_conn = sqlite3.connect(v3_db_path)
    v3_conn.row_factory = sqlite3.Row
    v4_conn = sqlite3.connect(v4_db_path)
    
    # Initialize v4 schema
    v4_conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            network TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB,
            importance REAL DEFAULT 0.5,
            created_at REAL NOT NULL,
            accessed_at REAL NOT NULL,
            access_count INTEGER DEFAULT 0,
            metadata TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_network ON memories(network);
        CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance DESC);
        CREATE INDEX IF NOT EXISTS idx_accessed ON memories(accessed_at DESC);
    """)
    
    # Migrate memories
    cursor = v3_conn.execute("SELECT * FROM memories")
    migrated = 0
    
    for row in cursor:
        # Classify into network
        network = classify_memory(row["content"])
        
        # Insert into v4
        v4_conn.execute(
            """
            INSERT INTO memories 
                (id, network, content, importance, created_at, accessed_at, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                network,
                row["content"],
                row.get("importance", 0.5),
                datetime.now().timestamp(),
                datetime.now().timestamp(),
                0
            )
        )
        migrated += 1
        
        if migrated % 100 == 0:
            print(f"Migrated {migrated} memories...")
    
    v4_conn.commit()
    
    print(f"Migration complete! Migrated {migrated} memories.")
    
    # Close connections
    v3_conn.close()
    v4_conn.close()


def classify_memory(content: str) -> str:
    """Classify memory into network"""
    
    # Simple classification logic
    content_lower = content.lower()
    
    # Beliefs: facts, knowledge
    if any(word in content_lower for word in ["is", "are", "means", "definition"]):
        return "beliefs"
    
    # Episodes: events, actions
    if any(word in content_lower for word in ["did", "happened", "asked", "told"]):
        return "episodes"
    
    # Procedures: how-to, steps
    if any(word in content_lower for word in ["how to", "step", "first", "then"]):
        return "procedures"
    
    # Strategies: approaches, patterns
    if any(word in content_lower for word in ["strategy", "approach", "pattern"]):
        return "strategies"
    
    # Default to beliefs
    return "beliefs"


def migrate_config(v3_config_path: Path, v4_config_path: Path):
    """Migrate configuration"""
    
    print("Migrating configuration...")
    
    # Load v3 config
    with open(v3_config_path) as f:
        v3_config = json.load(f)
    
    # Convert to v4 format
    v4_config = {
        "ANTHROPIC_API_KEY": v3_config.get("api_key"),
        "LYRA_DEFAULT_MAX_COST_USD": v3_config.get("max_cost", 10.0),
        "LYRA_DEFAULT_MAX_TIME_SECONDS": v3_config.get("max_time", 3600),
        "LYRA_MAX_CONCURRENT_AGENTS": 5,
        "LYRA_REQUIRE_APPROVAL_FOR_DESTRUCTIVE": True,
        "LYRA_ENABLE_AUDIT_LOGGING": True
    }
    
    # Write v4 config
    with open(v4_config_path, "w") as f:
        for key, value in v4_config.items():
            f.write(f"{key}={value}\n")
    
    print("Configuration migrated!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python migrate_v3_to_v4.py <v3_db_path> <v4_db_path>")
        sys.exit(1)
    
    v3_db = Path(sys.argv[1])
    v4_db = Path(sys.argv[2])
    
    if not v3_db.exists():
        print(f"Error: v3 database not found: {v3_db}")
        sys.exit(1)
    
    # Migrate
    migrate_database(v3_db, v4_db)
    
    # Migrate config if exists
    v3_config = v3_db.parent / "config.json"
    v4_config = v4_db.parent / ".env"
    
    if v3_config.exists():
        migrate_config(v3_config, v4_config)
```

#### Step 2: Run Migration

```bash
# Activate v4 environment
cd ~/lyra-v4
source venv/bin/activate

# Run migration script
python scripts/migrate_v3_to_v4.py \
    ~/.lyra/v3/memory.db \
    ~/.lyra/v4/data/memory.db

# Verify migration
sqlite3 ~/.lyra/v4/data/memory.db "SELECT network, COUNT(*) FROM memories GROUP BY network;"
```

#### Step 3: Validate Data

```bash
# Check record counts
echo "v3 count:"
sqlite3 ~/.lyra/v3/memory.db "SELECT COUNT(*) FROM memories;"

echo "v4 count:"
sqlite3 ~/.lyra/v4/data/memory.db "SELECT COUNT(*) FROM memories;"

# Check sample records
sqlite3 ~/.lyra/v4/data/memory.db "SELECT * FROM memories LIMIT 5;"
```

### Phase 3: Code Migration

#### Step 1: Update Imports

**Before (v3.x)**:
```python
from lyra import Lyra
from lyra.memory import Memory
from lyra.agent import Agent
```

**After (v4.0)**:
```python
from lyra import Lyra
from lyra.memory.networks import MemorySystem
from lyra.agents.primary import PrimaryAgent
```

#### Step 2: Update Memory Operations

**Before (v3.x)**:
```python
# Store memory
memory.store("Python is a language", importance=0.9)

# Recall memories
memories = memory.recall("Python")
```

**After (v4.0)**:
```python
# Store in appropriate network
memory.beliefs.store("Python is a language", importance=0.9)

# Recall from network
memories = memory.beliefs.recall("Python")
```

#### Step 3: Update Agent Usage

**Before (v3.x)**:
```python
# Synchronous execution
agent = Agent()
result = agent.execute(task)
```

**After (v4.0)**:
```python
# Async execution
agent = PrimaryAgent()
result = await agent.execute(task)

# Or use high-level API
lyra = Lyra()
response = await lyra.handle_request("Create a function")
```

#### Step 4: Update Configuration

**Before (v3.x)**:
```python
config = {
    "api_key": "...",
    "max_cost": 10.0
}
lyra = Lyra(config)
```

**After (v4.0)**:
```python
from lyra.core.config import LyraConfig

config = LyraConfig(
    anthropic_api_key="...",
    default_max_cost_usd=10.0
)
lyra = Lyra(config)
```

### Phase 4: Testing

#### Step 1: Unit Tests

```bash
# Run v4 unit tests
cd ~/lyra-v4
pytest tests/unit -v

# Check coverage
pytest tests/unit --cov=lyra --cov-report=html
```

#### Step 2: Integration Tests

```bash
# Run integration tests
pytest tests/integration -v

# Test memory migration
pytest tests/integration/test_migration.py -v
```

#### Step 3: End-to-End Tests

```bash
# Run e2e tests
pytest tests/e2e -v -m e2e

# Test real workflows
python scripts/test_migration_workflows.py
```

**File**: `scripts/test_migration_workflows.py`

```python
"""Test migrated workflows"""
import asyncio
from lyra import Lyra
from lyra.core.config import LyraConfig


async def test_basic_workflow():
    """Test basic workflow"""
    config = LyraConfig()
    lyra = Lyra(config)
    
    # Test request
    response = await lyra.handle_request("What is 2 + 2?")
    assert "4" in response
    print("✓ Basic workflow works")


async def test_memory_workflow():
    """Test memory workflow"""
    config = LyraConfig()
    lyra = Lyra(config)
    
    # Store memory
    await lyra.handle_request("Remember that my name is Alice")
    
    # Recall memory
    response = await lyra.handle_request("What is my name?")
    assert "Alice" in response
    print("✓ Memory workflow works")


async def test_code_generation():
    """Test code generation"""
    config = LyraConfig()
    lyra = Lyra(config)
    
    response = await lyra.handle_request(
        "Create a Python function to calculate fibonacci"
    )
    assert "def" in response
    assert "fibonacci" in response.lower()
    print("✓ Code generation works")


async def main():
    """Run all tests"""
    print("Testing migrated workflows...\n")
    
    await test_basic_workflow()
    await test_memory_workflow()
    await test_code_generation()
    
    print("\n✓ All workflows passed!")


if __name__ == "__main__":
    asyncio.run(main())
```

### Phase 5: Deployment

#### Step 1: Deploy to Staging

```bash
# SSH to staging server
ssh user@staging-server

# Stop v3.x service
sudo systemctl stop lyra-v3

# Deploy v4.0
cd /home/lyra
git clone https://github.com/your-org/lyra.git lyra-v4
cd lyra-v4
git checkout v4.0

# Install
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Migrate data
python scripts/migrate_v3_to_v4.py \
    /home/lyra/.lyra/v3/memory.db \
    /home/lyra/.lyra/v4/data/memory.db

# Configure systemd
sudo cp scripts/lyra-v4.service /etc/systemd/system/lyra.service
sudo systemctl daemon-reload
sudo systemctl enable lyra
sudo systemctl start lyra

# Verify
sudo systemctl status lyra
curl http://localhost:8000/health
```

#### Step 2: Validate Staging

```bash
# Run smoke tests
pytest tests/e2e -v -m smoke

# Test API endpoints
curl http://staging.lyra.example.com/health
curl http://staging.lyra.example.com/version

# Monitor logs
sudo journalctl -u lyra -f
```

#### Step 3: Deploy to Production

```bash
# Create deployment plan
cat > deployment-plan.md << EOF
# Lyra v4.0 Production Deployment

## Pre-Deployment
- [ ] Backup all data
- [ ] Notify users of maintenance
- [ ] Prepare rollback plan

## Deployment
- [ ] Stop v3.x service
- [ ] Migrate database
- [ ] Deploy v4.0
- [ ] Start v4.0 service
- [ ] Verify health

## Post-Deployment
- [ ] Monitor metrics
- [ ] Check logs
- [ ] Validate functionality
- [ ] Notify users

## Rollback (if needed)
- [ ] Stop v4.0
- [ ] Restore v3.x database
- [ ] Start v3.x service
EOF

# Execute deployment
./scripts/deploy-production.sh
```

**File**: `scripts/deploy-production.sh`

```bash
#!/bin/bash
set -e

echo "Starting Lyra v4.0 production deployment..."

# Backup
echo "Creating backup..."
./scripts/backup-production.sh

# Notify users
echo "Notifying users..."
curl -X POST https://status.example.com/api/incidents \
    -d '{"message": "Lyra maintenance in progress"}'

# Stop v3.x
echo "Stopping v3.x..."
sudo systemctl stop lyra-v3

# Migrate database
echo "Migrating database..."
python scripts/migrate_v3_to_v4.py \
    /var/lib/lyra/v3/memory.db \
    /var/lib/lyra/v4/data/memory.db

# Deploy v4.0
echo "Deploying v4.0..."
cd /opt/lyra-v4
git pull origin v4.0
source venv/bin/activate
pip install -r requirements.txt

# Start v4.0
echo "Starting v4.0..."
sudo systemctl start lyra

# Wait for startup
sleep 10

# Verify
echo "Verifying deployment..."
curl -f http://localhost:8000/health || {
    echo "Health check failed! Rolling back..."
    ./scripts/rollback.sh
    exit 1
}

# Success
echo "Deployment successful!"
curl -X POST https://status.example.com/api/incidents/resolve \
    -d '{"message": "Lyra v4.0 deployed successfully"}'
```

---

## Data Migration

### Memory Classification

The migration script classifies v3.x memories into v4.0 networks:

| v3.x Memory Type | v4.0 Network | Criteria |
|------------------|--------------|----------|
| Facts | Beliefs | Contains "is", "are", "means" |
| Events | Episodes | Contains "did", "happened", "asked" |
| How-to | Procedures | Contains "how to", "step", "first" |
| Patterns | Strategies | Contains "strategy", "approach" |
| Other | Beliefs | Default |

### Manual Classification

For better accuracy, manually classify important memories:

```python
# Review and reclassify
from lyra.memory.networks import MemorySystem

memory = MemorySystem()

# Get all memories
all_memories = memory.beliefs.recall("", limit=1000)

# Reclassify
for mem in all_memories:
    if should_be_episode(mem.content):
        # Move to episodes
        memory.episodes.store(mem.content, importance=mem.importance)
        memory.beliefs.forget(mem.id)
```

---

## Code Migration

### Automated Code Migration

**File**: `scripts/migrate_code.py`

```python
"""Automated code migration tool"""
import re
from pathlib import Path


def migrate_file(file_path: Path):
    """Migrate a single file"""
    
    with open(file_path) as f:
        content = f.read()
    
    # Update imports
    content = content.replace(
        "from lyra.memory import Memory",
        "from lyra.memory.networks import MemorySystem"
    )
    content = content.replace(
        "from lyra.agent import Agent",
        "from lyra.agents.primary import PrimaryAgent"
    )
    
    # Update memory operations
    content = re.sub(
        r'memory\.store\((.*?)\)',
        r'memory.beliefs.store(\1)',
        content
    )
    content = re.sub(
        r'memory\.recall\((.*?)\)',
        r'memory.beliefs.recall(\1)',
        content
    )
    
    # Update agent operations
    content = re.sub(
        r'agent\.execute\((.*?)\)',
        r'await agent.execute(\1)',
        content
    )
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Migrated: {file_path}")


def migrate_project(project_dir: Path):
    """Migrate entire project"""
    
    for py_file in project_dir.rglob("*.py"):
        if "venv" not in str(py_file):
            migrate_file(py_file)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python migrate_code.py <project_dir>")
        sys.exit(1)
    
    project_dir = Path(sys.argv[1])
    migrate_project(project_dir)
    
    print("\nCode migration complete!")
    print("Please review changes and test thoroughly.")
```

---

## Testing Migration

### Migration Test Suite

**File**: `tests/migration/test_v3_to_v4.py`

```python
"""Test v3 to v4 migration"""
import pytest
from pathlib import Path
from scripts.migrate_v3_to_v4 import migrate_database, classify_memory


class TestMigration:
    """Test migration"""
    
    def test_classify_beliefs(self):
        """Test belief classification"""
        assert classify_memory("Python is a language") == "beliefs"
        assert classify_memory("The sky is blue") == "beliefs"
    
    def test_classify_episodes(self):
        """Test episode classification"""
        assert classify_memory("User asked about Python") == "episodes"
        assert classify_memory("I did something") == "episodes"
    
    def test_classify_procedures(self):
        """Test procedure classification"""
        assert classify_memory("How to install Python") == "procedures"
        assert classify_memory("First, do this") == "procedures"
    
    def test_database_migration(self, tmp_path):
        """Test database migration"""
        v3_db = tmp_path / "v3.db"
        v4_db = tmp_path / "v4.db"
        
        # Create v3 database
        import sqlite3
        conn = sqlite3.connect(v3_db)
        conn.execute("""
            CREATE TABLE memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                importance REAL
            )
        """)
        conn.execute(
            "INSERT INTO memories VALUES (?, ?, ?)",
            ("mem1", "Python is a language", 0.9)
        )
        conn.commit()
        conn.close()
        
        # Migrate
        migrate_database(v3_db, v4_db)
        
        # Verify
        conn = sqlite3.connect(v4_db)
        cursor = conn.execute("SELECT * FROM memories")
        row = cursor.fetchone()
        
        assert row is not None
        assert row[1] == "beliefs"  # network
        assert row[2] == "Python is a language"  # content
```

---

## Rollback Plan

### Automated Rollback

**File**: `scripts/rollback.sh`

```bash
#!/bin/bash
set -e

echo "Starting rollback to v3.x..."

# Stop v4.0
echo "Stopping v4.0..."
sudo systemctl stop lyra

# Restore v3.x database
echo "Restoring v3.x database..."
cp /var/backups/lyra/v3-backup-latest/memory.db \
   /var/lib/lyra/v3/memory.db

# Start v3.x
echo "Starting v3.x..."
sudo systemctl start lyra-v3

# Verify
echo "Verifying v3.x..."
sleep 5
curl -f http://localhost:8000/health || {
    echo "Rollback failed!"
    exit 1
}

echo "Rollback successful!"
```

### Manual Rollback Steps

1. **Stop v4.0**:
   ```bash
   sudo systemctl stop lyra
   ```

2. **Restore v3.x database**:
   ```bash
   cp ~/lyra-migration/backups/memory.db.backup ~/.lyra/v3/memory.db
   ```

3. **Start v3.x**:
   ```bash
   sudo systemctl start lyra-v3
   ```

4. **Verify**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Summary

This migration guide provides:
- ✅ Complete migration strategy
- ✅ Step-by-step procedures
- ✅ Automated migration scripts
- ✅ Testing procedures
- ✅ Rollback plan

**Key Steps**:
1. Backup everything
2. Install v4.0 in parallel
3. Migrate database
4. Update code
5. Test thoroughly
6. Deploy gradually
7. Monitor closely

**Timeline**: 3-4 weeks for complete migration

**Risk Level**: Medium (with proper testing and rollback plan)

---

**Related Documents**:
- `06-IMPLEMENTATION_GUIDE.md`: Implementation details
- `08-TESTING_STRATEGY.md`: Testing procedures
- `09-DEPLOYMENT_GUIDE.md`: Deployment instructions

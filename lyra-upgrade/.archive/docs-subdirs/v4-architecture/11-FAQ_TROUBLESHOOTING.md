# Lyra v4.0 FAQ & Troubleshooting

**Version**: 1.0  
**Status**: 🚧 Draft  
**Last Updated**: 2026-05-21

---

## Overview

Frequently asked questions and troubleshooting guide for Lyra v4.0. This document provides quick answers to common questions and solutions to common problems.

---

## Table of Contents

1. [General Questions](#general-questions)
2. [Architecture Questions](#architecture-questions)
3. [Memory System](#memory-system)
4. [Agent System](#agent-system)
5. [Planning & Reasoning](#planning--reasoning)
6. [Safety & Security](#safety--security)
7. [Performance](#performance)
8. [Troubleshooting](#troubleshooting)

---

## General Questions

### What is Lyra v4.0?

Lyra v4.0 is an advanced AI assistant with persistent memory, multi-agent orchestration, strategic planning, and comprehensive safety features. It's designed to handle complex, multi-step tasks while maintaining context across sessions.

### What's new in v4.0?

- **5-Network Memory System**: Better organization (Beliefs, Episodes, Entities, Procedures, Strategies)
- **Multi-Agent Architecture**: Specialized agents for different tasks
- **Advanced Planning**: Strategic decomposition and adaptive execution
- **Enhanced Safety**: Multi-layer validation and budget management
- **Improved Performance**: 3x faster memory recall, 2x faster responses

### Is v4.0 backward compatible with v3.x?

No, v4.0 has breaking changes. However, we provide a comprehensive migration guide and automated migration tools. See `10-MIGRATION_GUIDE.md`.

### What are the system requirements?

**Minimum**:
- Python 3.11+
- 8GB RAM
- 10GB disk space
- Linux/macOS/Windows

**Recommended**:
- Python 3.11+
- 16GB RAM
- 50GB SSD
- Linux/macOS

### How much does it cost to run?

Costs depend on usage:
- **Light usage**: $5-10/month
- **Medium usage**: $20-50/month
- **Heavy usage**: $100+/month

You can set budget limits to control costs.

---

## Architecture Questions

### Why 5 memory networks?

Different types of information require different storage and recall strategies:

- **Beliefs**: Facts and knowledge (semantic memory)
- **Episodes**: Events and experiences (episodic memory)
- **Entities**: People, places, things (entity memory)
- **Procedures**: How-to knowledge (procedural memory)
- **Strategies**: Approaches and patterns (strategic memory)

This organization improves recall accuracy and speed.

### Why multi-agent architecture?

Multi-agent architecture provides:
- **Specialization**: Each agent excels at specific tasks
- **Parallelism**: Multiple tasks execute simultaneously
- **Efficiency**: Right agent for the right job
- **Scalability**: Easy to add new specialist agents

### How does planning work?

Planning uses a 4-stage process:

1. **Decomposition**: Break goal into steps
2. **Dependency Analysis**: Identify step dependencies
3. **Resource Estimation**: Estimate time and cost
4. **Optimization**: Optimize execution order

Plans adapt during execution based on results.

### What safety mechanisms are in place?

Multiple layers:

1. **Input Validation**: Check user input for issues
2. **Action Validation**: Validate actions before execution
3. **Risk Assessment**: Assess action risk level
4. **Budget Management**: Enforce resource limits
5. **Audit Logging**: Log all operations

---

## Memory System

### How do I choose which network to use?

**Guidelines**:

- **Beliefs**: Use for facts, definitions, knowledge
  - Example: "Python is a programming language"
  
- **Episodes**: Use for events, actions, experiences
  - Example: "User asked about Python yesterday"
  
- **Entities**: Use for people, places, things
  - Example: "John Smith, Software Engineer at Acme Corp"
  
- **Procedures**: Use for how-to, steps, instructions
  - Example: "How to deploy to production: 1. Run tests..."
  
- **Strategies**: Use for approaches, patterns, best practices
  - Example: "When debugging, start with logs, then use debugger"

### Can I search across all networks?

Yes, but it's more efficient to search specific networks:

```python
# Search specific network (fast)
memories = memory.beliefs.recall("Python", limit=10)

# Search all networks (slower)
all_memories = []
for network in [memory.beliefs, memory.episodes, memory.procedures]:
    all_memories.extend(network.recall("Python", limit=10))
```

### How is memory importance calculated?

Importance is a score from 0.0 to 1.0:

- **0.0-0.3**: Low importance (temporary, context-specific)
- **0.4-0.6**: Medium importance (useful, but not critical)
- **0.7-0.9**: High importance (critical, frequently used)
- **1.0**: Maximum importance (core knowledge)

Importance affects recall priority and retention.

### How long are memories retained?

Memories are retained based on:
- **Importance**: Higher importance = longer retention
- **Access frequency**: Frequently accessed = longer retention
- **Recency**: Recently accessed = longer retention

Low-importance, rarely-accessed memories may be pruned.

### Can I manually manage memories?

Yes:

```python
# Store with specific importance
memory_id = memory.beliefs.store(
    "Important fact",
    importance=0.9
)

# Update importance
memory.beliefs.update_importance(memory_id, 0.95)

# Delete memory
memory.beliefs.forget(memory_id)

# Export memories
memories = memory.beliefs.recall("", limit=1000)
with open("backup.json", "w") as f:
    json.dump([m.to_dict() for m in memories], f)
```

---

## Agent System

### What's the difference between agent types?

**Primary Agent**:
- Orchestrates overall workflow
- Handles user interaction
- Delegates to specialists
- Makes high-level decisions

**Specialist Agents**:
- Code Agent: Writing and reviewing code
- Research Agent: Information gathering
- Test Agent: Testing and validation
- Review Agent: Quality assurance

**Worker Agents**:
- Execute specific tasks
- No decision-making
- Fast and efficient

### How do I choose which agent to use?

Usually you don't need to choose—the Primary Agent automatically delegates to the right specialist. But you can request specific agents:

```python
# Automatic delegation (recommended)
response = await lyra.handle_request("Create a Python function")

# Manual delegation
from lyra.agents.specialists import CodeAgent

code_agent = CodeAgent()
result = await code_agent.execute(task)
```

### Can agents run in parallel?

Yes, the Primary Agent can delegate multiple tasks to specialists simultaneously:

```python
# Sequential (slower)
result1 = await agent1.execute(task1)
result2 = await agent2.execute(task2)

# Parallel (faster)
results = await asyncio.gather(
    agent1.execute(task1),
    agent2.execute(task2)
)
```

### How many agents can run concurrently?

Default: 5 concurrent agents

Configure via:
```bash
LYRA_MAX_CONCURRENT_AGENTS=10
```

More agents = more parallelism but higher resource usage.

### What happens if an agent fails?

Agents have built-in error handling:

1. **Retry**: Automatic retry with exponential backoff
2. **Fallback**: Try alternative approach
3. **Escalation**: Report to Primary Agent
4. **Recovery**: Attempt to recover partial results

---

## Planning & Reasoning

### When should I use planning?

Use planning for:
- Multi-step tasks
- Complex workflows
- Tasks with dependencies
- Tasks requiring coordination

Simple, single-step tasks don't need planning.

### How accurate are plans?

Plan accuracy depends on:
- **Task complexity**: Simpler tasks = more accurate
- **Context**: More context = better plans
- **Experience**: More similar past tasks = better plans

Typical accuracy: 70-90% for well-defined tasks.

### Can plans adapt during execution?

Yes, plans are adaptive:

1. **Monitor**: Track execution progress
2. **Detect**: Identify deviations from plan
3. **Replan**: Adjust plan if needed
4. **Continue**: Execute updated plan

### What reasoning strategies are available?

Four types:

1. **Logical**: Deductive reasoning from premises
2. **Causal**: Identify cause-effect relationships
3. **Analogical**: Find similar situations
4. **Abductive**: Infer best explanation

The system automatically chooses the appropriate strategy.

### How do I debug planning issues?

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export LYRA_LOG_LEVEL=DEBUG
```

Check plan details:
```python
plan = await planner.create_plan(goal)
print(f"Steps: {len(plan.steps)}")
for step in plan.steps:
    print(f"  {step.order}: {step.description}")
    print(f"    Depends on: {step.depends_on}")
    print(f"    Estimated: {step.estimated_duration}s")
```

---

## Safety & Security

### How does input validation work?

Multi-layer validation:

1. **Length check**: Reject overly long input
2. **Injection detection**: Detect prompt injection attempts
3. **Content filtering**: Check for harmful content
4. **Rate limiting**: Prevent abuse

### What actions require approval?

High-risk actions:
- Deleting files/directories
- Modifying system configuration
- Executing shell commands
- Accessing sensitive data
- Making external API calls

Configure via:
```bash
LYRA_REQUIRE_APPROVAL_FOR_DESTRUCTIVE=true
```

### How do budget limits work?

Set limits on:
- **Cost**: Maximum USD spend
- **Time**: Maximum execution time
- **Tokens**: Maximum token usage
- **Turns**: Maximum conversation turns

```python
from lyra.safety.budget import Budget

budget = Budget(
    max_cost_usd=10.0,
    max_time_seconds=3600,
    max_tokens=100000,
    max_turns=50
)
```

System stops when any limit is reached.

### Are operations logged?

Yes, comprehensive audit logging:
- All user inputs
- All agent actions
- All decisions
- All errors
- Resource usage

Logs are stored in `~/.lyra/logs/audit.log`.

### How do I review audit logs?

```bash
# View recent logs
tail -f ~/.lyra/logs/audit.log

# Search logs
grep "error" ~/.lyra/logs/audit.log

# Query via API
from lyra.safety.audit import AuditLogger

logger = AuditLogger()
logs = await logger.query_logs(
    {"level": "error"},
    limit=100
)
```

---

## Performance

### Why is the first request slow?

First request includes:
- Model initialization
- Memory system loading
- Agent initialization
- Cache warming

Subsequent requests are much faster.

### How can I improve performance?

**Memory System**:
- Use specific networks (not all)
- Set appropriate importance thresholds
- Limit recall results
- Enable caching

**Agent System**:
- Use appropriate agent types
- Enable parallel execution
- Reuse agent instances

**Planning**:
- Provide clear goals
- Include relevant context
- Use simpler plans when possible

### What's the expected response time?

**Typical response times**:
- Simple queries: 1-3 seconds
- Code generation: 5-15 seconds
- Complex planning: 10-30 seconds
- Multi-step tasks: 30-300 seconds

### How much memory does Lyra use?

**Memory usage**:
- Base: ~200MB
- Per agent: ~50MB
- Memory system: ~100MB + data size
- Peak: ~500MB-1GB

### Can I run Lyra on limited resources?

Yes, configure for lower resource usage:

```bash
# Reduce concurrent agents
LYRA_MAX_CONCURRENT_AGENTS=2

# Limit memory size
LYRA_MEMORY_MAX_SIZE_MB=100

# Reduce worker threads
LYRA_WORKER_THREADS=1
```

---

## Troubleshooting

### Installation Issues

#### Issue: `pip install` fails

**Solution**:
```bash
# Update pip
pip install --upgrade pip

# Install with verbose output
pip install -v -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

#### Issue: Import errors

**Solution**:
```bash
# Install in editable mode
pip install -e .

# Verify installation
python -c "import lyra; print(lyra.__version__)"
```

### Runtime Issues

#### Issue: "API key not found"

**Solution**:
```bash
# Set API key
export ANTHROPIC_API_KEY="your-key"

# Or in .env file
echo "ANTHROPIC_API_KEY=your-key" >> .env
```

#### Issue: "Database locked"

**Solution**:
```bash
# Check for other processes
ps aux | grep lyra

# Kill stale processes
pkill -f lyra

# Remove lock file
rm ~/.lyra/data/memory.db-lock
```

#### Issue: "Out of memory"

**Solution**:
```bash
# Clear cache
lyra cache clear

# Reduce memory limit
export LYRA_MEMORY_MAX_SIZE_MB=100

# Restart service
sudo systemctl restart lyra
```

#### Issue: "Agent timeout"

**Solution**:
```bash
# Increase timeout
export LYRA_AGENT_TIMEOUT_SECONDS=600

# Check agent status
lyra agents status

# Kill stuck agents
lyra agents kill <agent-id>
```

### Performance Issues

#### Issue: Slow responses

**Diagnosis**:
```bash
# Enable profiling
lyra serve --profile

# Check metrics
curl http://localhost:8000/metrics

# View logs
tail -f ~/.lyra/logs/lyra.log
```

**Solutions**:
- Reduce concurrent agents
- Clear cache
- Optimize memory queries
- Check network latency

#### Issue: High memory usage

**Diagnosis**:
```bash
# Check memory usage
ps aux | grep lyra

# Check memory system size
lyra memory stats
```

**Solutions**:
```bash
# Clear old memories
lyra memory prune --older-than 30d

# Reduce memory limit
export LYRA_MEMORY_MAX_SIZE_MB=200

# Restart service
sudo systemctl restart lyra
```

### Data Issues

#### Issue: Lost memories

**Solution**:
```bash
# Check database
sqlite3 ~/.lyra/data/memory.db "SELECT COUNT(*) FROM memories;"

# Restore from backup
cp ~/backups/memory.db ~/.lyra/data/memory.db

# Verify restoration
lyra memory stats
```

#### Issue: Corrupted database

**Solution**:
```bash
# Check integrity
sqlite3 ~/.lyra/data/memory.db "PRAGMA integrity_check;"

# Repair database
sqlite3 ~/.lyra/data/memory.db "VACUUM;"

# If repair fails, restore from backup
cp ~/backups/memory.db ~/.lyra/data/memory.db
```

### Network Issues

#### Issue: API connection failed

**Diagnosis**:
```bash
# Test connectivity
curl https://api.anthropic.com/v1/messages

# Check DNS
nslookup api.anthropic.com

# Check firewall
sudo iptables -L
```

**Solutions**:
- Check internet connection
- Verify API key
- Check firewall rules
- Use proxy if needed

#### Issue: Timeout errors

**Solutions**:
```bash
# Increase timeout
export LYRA_API_TIMEOUT_SECONDS=120

# Check network latency
ping api.anthropic.com

# Use retry logic
export LYRA_MAX_RETRIES=5
```

---

## Getting Help

### Documentation

- **Architecture**: `01-ARCHITECTURE_OVERVIEW.md`
- **Implementation**: `06-IMPLEMENTATION_GUIDE.md`
- **API Reference**: `07-API_REFERENCE.md`
- **Deployment**: `09-DEPLOYMENT_GUIDE.md`
- **Migration**: `10-MIGRATION_GUIDE.md`

### Support Channels

- **GitHub Issues**: https://github.com/your-org/lyra/issues
- **Discord**: https://discord.gg/lyra
- **Email**: support@lyra.example.com
- **Documentation**: https://docs.lyra.example.com

### Reporting Bugs

When reporting bugs, include:

1. **Version**: `lyra --version`
2. **Environment**: OS, Python version
3. **Error message**: Full error output
4. **Steps to reproduce**: Minimal example
5. **Logs**: Relevant log excerpts

**Template**:
```markdown
## Bug Report

**Version**: 4.0.0
**OS**: Ubuntu 22.04
**Python**: 3.11.5

**Description**:
Brief description of the issue

**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior**:
What should happen

**Actual Behavior**:
What actually happens

**Error Message**:
```
Full error output
```

**Logs**:
```
Relevant log excerpts
```
```

### Feature Requests

Submit feature requests via GitHub Issues with:
- Clear description
- Use case
- Expected behavior
- Alternatives considered

---

## Summary

This FAQ covers:
- ✅ Common questions
- ✅ Architecture explanations
- ✅ Usage guidelines
- ✅ Troubleshooting steps
- ✅ Support resources

**Quick Tips**:
- Check logs first
- Use debug mode for issues
- Keep backups
- Monitor resource usage
- Update regularly

For more help, see documentation or contact support.

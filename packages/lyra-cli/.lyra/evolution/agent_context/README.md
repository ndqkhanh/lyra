# Agent Context

This directory contains agent context files that can be edited by the meta-agent in **Agent Mode**.

## Purpose

Agent mode enables the meta-agent to edit the agent's context and configuration, allowing it to:
- Update skills and capabilities
- Modify goals and objectives
- Adjust validators and constraints
- Update memory and learned patterns

## Structure

```
agent_context/
├── skills.md       # Agent skills and capabilities
├── goal.md         # Current goals and objectives
├── validators/     # Validation rules
└── memory.json     # Agent memory
```

## Meta-Agent Edits

The meta-agent can:
- Read existing context files
- Propose updates based on evolution results
- Write new context configurations
- Log all edits to `archive/meta_edits/`

## Safety

- All edits are logged to the archive
- Context changes are applied before the next evolution segment
- The harness controls when context is loaded

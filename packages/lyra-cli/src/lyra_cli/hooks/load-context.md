---
name: load-context
description: Load project context when session starts
type: SessionStart
script: load_context.py
enabled: true
---

# Load Context Hook

Loads project context when session starts.

## Context Loading

- Load project memory
- Load user preferences
- Initialize agent registry
- Load skill library

## Usage

This hook runs automatically when a new session starts.

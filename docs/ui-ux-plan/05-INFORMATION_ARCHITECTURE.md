# 05. Information Architecture - Lyra UI/UX Plan

**Version**: 1.0  
**Status**: ✅ Complete  
**Last Updated**: 2026-05-21

---

## Overview

This document defines the information architecture (IA) for Lyra's terminal interface. IA organizes content, defines navigation patterns, and establishes content hierarchy to help users find what they need quickly.

---

## IA Principles

### 1. User-Centered
- Organize by user tasks, not system structure
- Match user mental models
- Support common workflows

### 2. Clear Hierarchy
- Most important content first
- Logical grouping
- Progressive disclosure

### 3. Consistent Navigation
- Predictable patterns
- Clear paths
- Easy to backtrack

### 4. Findable
- Search and filter
- Multiple access paths
- Clear labels

---

## Content Organization

### Top-Level Structure

```
Lyra CLI
├── Chat Mode (default)
│   ├── Conversation history
│   ├── Tool calls
│   └── Context
├── Goal Mode
│   ├── Active goal
│   ├── Plan
│   ├── Progress
│   └── Budget
├── Agent View
│   ├── Status
│   ├── Current task
│   ├── Memory
│   └── Activity log
├── Commands
│   ├── /help
│   ├── /history
│   ├── /memory
│   ├── /skills
│   ├── /tools
│   ├── /settings
│   └── /quit
└── Settings
    ├── Model configuration
    ├── UI preferences
    ├── Safety settings
    └── API keys
```

---

## Navigation Patterns

### 1. Command-Based Navigation

**Primary Navigation**: Slash commands

```
/chat       → Switch to chat mode
/goal       → Start goal mode
/agent      → View agent dashboard
/history    → View conversation history
/memory     → View and manage memory
/skills     → Browse and manage skills
/tools      → Browse available tools
/settings   → Open settings
/help       → Show help
/quit       → Exit Lyra
```

**Benefits**:
- Fast keyboard access
- Discoverable via /help
- Consistent pattern
- No mouse required

### 2. Contextual Navigation

**In-Context Actions**: Available based on current view

```
Chat Mode:
  Ctrl+C    → Cancel current operation
  Ctrl+D    → Exit chat
  ↑/↓       → Navigate history
  Tab       → Autocomplete

Goal Mode:
  Ctrl+P    → Pause goal
  Ctrl+S    → Stop goal
  Ctrl+D    → View details

Agent View:
  R         → Refresh
  P         → Pause agent
  S         → Stop agent
  D         → View details
```

### 3. Breadcrumb Navigation

**Show Current Location**:

```
Lyra > Chat Mode
Lyra > Goal Mode > Fix authentication bug
Lyra > Agent View > Agent #1
Lyra > Settings > Model Configuration
```

**Benefits**:
- Clear context
- Easy to understand location
- Shows hierarchy

---

## Content Hierarchy

### Level 1: Primary Views

**Chat Mode** (Default):
- Purpose: Interactive conversation with agent
- Priority: Highest (default view)
- Access: Direct (default), /chat command

**Goal Mode**:
- Purpose: Autonomous task execution
- Priority: High (power user feature)
- Access: /goal command, goal_create tool

**Agent View**:
- Purpose: Monitor agent status and activity
- Priority: Medium (debugging, monitoring)
- Access: /agent command

### Level 2: Secondary Views

**History**:
- Purpose: Review past conversations
- Priority: Medium
- Access: /history command

**Memory**:
- Purpose: View and manage agent memory
- Priority: Medium
- Access: /memory command

**Skills**:
- Purpose: Browse and manage skills
- Priority: Medium
- Access: /skills command

**Tools**:
- Purpose: Browse available tools
- Priority: Low (reference)
- Access: /tools command

**Settings**:
- Purpose: Configure Lyra
- Priority: Low (one-time setup)
- Access: /settings command

### Level 3: Detail Views

**Conversation Detail**:
- Parent: History
- Content: Full conversation transcript
- Navigation: Select from history list

**Memory Detail**:
- Parent: Memory
- Content: Individual memory entry
- Navigation: Select from memory list

**Skill Detail**:
- Parent: Skills
- Content: Skill instructions and metadata
- Navigation: Select from skill list

**Tool Detail**:
- Parent: Tools
- Content: Tool documentation and parameters
- Navigation: Select from tool list

---

## Information Grouping

### Chat Mode Content Groups

```
┌─ Conversation ──────────────────────────────────────────────┐
│  Primary content: Messages and tool calls                   │
│  Chronological order (newest at bottom)                     │
└──────────────────────────────────────────────────────────────┘

┌─ Context (Collapsible) ─────────────────────────────────────┐
│  Secondary content: Current context, memory, active skills  │
│  Collapsed by default, expand with /context                 │
└──────────────────────────────────────────────────────────────┘

┌─ Status Bar ────────────────────────────────────────────────┐
│  Tertiary content: Model, cost, tokens, tips                │
│  Always visible at bottom                                   │
└──────────────────────────────────────────────────────────────┘
```

### Goal Mode Content Groups

```
┌─ Goal Header ───────────────────────────────────────────────┐
│  Primary: Goal title, status, progress                      │
│  Always visible at top                                      │
└──────────────────────────────────────────────────────────────┘

┌─ Current Step ──────────────────────────────────────────────┐
│  Primary: What agent is doing right now                     │
│  Prominent display with animation                           │
└──────────────────────────────────────────────────────────────┘

┌─ Plan ──────────────────────────────────────────────────────┐
│  Secondary: Full plan with step status                      │
│  Scrollable list                                            │
└──────────────────────────────────────────────────────────────┘

┌─ Budget & Controls ─────────────────────────────────────────┐
│  Tertiary: Budget tracking, pause/stop buttons             │
│  Always visible at bottom                                   │
└──────────────────────────────────────────────────────────────┘
```

### Agent View Content Groups

```
┌─ Status ────────────────────────────────────────────────────┐
│  Primary: Agent state, current task, key metrics            │
│  Compact, always visible                                    │
└──────────────────────────────────────────────────────────────┘

┌─ Task & Memory ─────────────────────────────────────────────┐
│  Secondary: Split view of current task and relevant memory  │
│  Side-by-side on wide terminals                             │
└──────────────────────────────────────────────────────────────┘

┌─ Activity Log ──────────────────────────────────────────────┐
│  Tertiary: Recent actions and events                        │
│  Scrollable, chronological                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Search and Filter

### Global Search

**Command**: `/search <query>`

**Scope**:
- Conversation history
- Memory entries
- Skills
- Tools
- Documentation

**Results Display**:
```
┌─ Search Results: "authentication" ──────────────────────────┐
│                                                              │
│  💬 Conversations (3)                                        │
│  • Fix authentication bug (2 days ago)                      │
│  • Add OAuth support (1 week ago)                           │
│  • Debug login issue (2 weeks ago)                          │
│                                                              │
│  🧠 Memory (5)                                               │
│  • User prefers JWT tokens                                  │
│  • Authentication flow diagram                              │
│  • Common auth errors                                       │
│  ...                                                         │
│                                                              │
│  🔧 Skills (2)                                               │
│  • implement-oauth                                          │
│  • debug-auth-issues                                        │
│                                                              │
│  🛠️  Tools (1)                                               │
│  • check_auth_status                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Contextual Filters

**History Filters**:
```
/history --today          → Today's conversations
/history --week           → This week
/history --month          → This month
/history --search "bug"   → Search in history
/history --with-errors    → Conversations with errors
```

**Memory Filters**:
```
/memory --recent          → Recent memories
/memory --important       → High importance
/memory --type episodic   → Episodic memories only
/memory --search "auth"   → Search memories
```

**Skills Filters**:
```
/skills --recent          → Recently used
/skills --unused          → Never used
/skills --tag backend     → By tag
/skills --search "test"   → Search skills
```

---

## Progressive Disclosure

### Collapsed by Default

**Tool Call Details**:
```
Collapsed:
  ⚡ read_file(path="src/auth.py") ✅

Expanded (click or press Enter):
  ⚡ read_file
  ┌─ Arguments ─────────────────────────────────────────────┐
  │  path: "src/auth.py"                                    │
  └─────────────────────────────────────────────────────────┘
  ┌─ Result ────────────────────────────────────────────────┐
  │  Read 245 lines (3.2 KB)                                │
  │  Last modified: 2 hours ago                             │
  └─────────────────────────────────────────────────────────┘
```

**Memory Context**:
```
Collapsed:
  🧠 3 relevant memories

Expanded:
  🧠 Relevant Memories
  ┌────────────────────────────────────────────────────────┐
  │  • User prefers JWT tokens over sessions               │
  │  • Authentication flow uses OAuth 2.0                  │
  │  • Common error: Token expiration not handled          │
  └────────────────────────────────────────────────────────┘
```

**Plan Steps**:
```
Collapsed:
  ✅ 1. Understand the bug
  ✅ 2. Read error logs
  🔄 3. Analyze code (current)
  ⏳ 4. Identify root cause
  ⏳ 5. Implement fix
  ... (2 more steps)

Expanded:
  ✅ 1. Understand the bug
     Duration: 30s | Cost: $0.05
     Result: Bug is in token validation
  
  ✅ 2. Read error logs
     Duration: 15s | Cost: $0.02
     Result: Found 3 related errors
  
  🔄 3. Analyze code (current)
     Started: 12s ago
     Reading: src/auth.py
  
  ... (full plan)
```

---

## Content Prioritization

### Priority Levels

**P0 - Critical** (Always visible):
- Current agent state
- Active task/goal
- Error messages
- Budget warnings

**P1 - High** (Visible by default):
- Conversation messages
- Tool call results
- Progress indicators
- Status updates

**P2 - Medium** (Collapsed by default):
- Tool call details
- Memory context
- Plan details
- Metrics

**P3 - Low** (Hidden, accessible via commands):
- Full history
- All memories
- All skills
- Settings

### Visibility Rules

```python
class ContentPriority:
    CRITICAL = 0  # Always visible, never collapse
    HIGH = 1      # Visible by default
    MEDIUM = 2    # Collapsed by default
    LOW = 3       # Hidden, command access only
    
    @staticmethod
    def should_show(priority: int, context: str) -> bool:
        if priority == ContentPriority.CRITICAL:
            return True
        
        if context == "chat":
            return priority <= ContentPriority.HIGH
        
        if context == "goal":
            return priority <= ContentPriority.MEDIUM
        
        if context == "agent":
            return priority <= ContentPriority.MEDIUM
        
        return False
```

---

## Navigation Shortcuts

### Global Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| Ctrl+C | Cancel operation | All |
| Ctrl+D | Exit/Back | All |
| Ctrl+L | Clear screen | All |
| Ctrl+R | Refresh | All |
| / | Command mode | All |
| ? | Help | All |

### Context-Specific Shortcuts

**Chat Mode**:
| Shortcut | Action |
|----------|--------|
| ↑ | Previous message |
| ↓ | Next message |
| Tab | Autocomplete |
| Enter | Send message |
| Esc | Cancel input |

**Goal Mode**:
| Shortcut | Action |
|----------|--------|
| Ctrl+P | Pause goal |
| Ctrl+S | Stop goal |
| Ctrl+D | View details |
| Space | Expand/collapse step |

**Agent View**:
| Shortcut | Action |
|----------|--------|
| R | Refresh |
| P | Pause agent |
| S | Stop agent |
| D | View details |
| L | View logs |

**List Views** (History, Memory, Skills):
| Shortcut | Action |
|----------|--------|
| ↑/↓ | Navigate items |
| Enter | Select item |
| Space | Toggle selection |
| / | Search |
| F | Filter |
| Esc | Back |

---

## Help System

### Contextual Help

**Command**: `?` or `/help`

**Chat Mode Help**:
```
┌─ Chat Mode Help ────────────────────────────────────────────┐
│                                                              │
│  Commands:                                                  │
│  /goal <objective>  → Start autonomous goal                 │
│  /agent             → View agent dashboard                  │
│  /history           → View conversation history             │
│  /memory            → View agent memory                     │
│  /help              → Show this help                        │
│                                                              │
│  Shortcuts:                                                 │
│  Ctrl+C             → Cancel current operation              │
│  Ctrl+D             → Exit chat                             │
│  ↑/↓                → Navigate message history              │
│  Tab                → Autocomplete                          │
│                                                              │
│  Tips:                                                      │
│  • Be specific in your requests                            │
│  • Use /goal for multi-step tasks                          │
│  • Check /agent to see what I'm doing                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Goal Mode Help**:
```
┌─ Goal Mode Help ────────────────────────────────────────────┐
│                                                              │
│  Controls:                                                  │
│  Ctrl+P             → Pause goal execution                  │
│  Ctrl+S             → Stop goal (cannot resume)             │
│  Ctrl+D             → View detailed plan                    │
│  Space              → Expand/collapse current step          │
│                                                              │
│  Budget:                                                    │
│  • Cost limit: $5.00 (configurable)                        │
│  • Time limit: 10 minutes (configurable)                   │
│  • Goal pauses at 80% of limits                            │
│                                                              │
│  Tips:                                                      │
│  • Clear objectives work best                              │
│  • Monitor progress in real-time                           │
│  • Pause to review before completion                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Command Reference

**Command**: `/help <command>`

```
┌─ Command: /goal ────────────────────────────────────────────┐
│                                                              │
│  Usage:                                                     │
│  /goal <objective>                                          │
│  /goal --budget 10 --time 20m <objective>                  │
│                                                              │
│  Description:                                               │
│  Start autonomous goal mode. The agent will create a plan   │
│  and execute it with minimal human intervention.            │
│                                                              │
│  Options:                                                   │
│  --budget <amount>  → Set cost budget (default: $5)        │
│  --time <duration>  → Set time limit (default: 10m)        │
│  --level <1-5>      → Set autonomy level (default: 3)      │
│                                                              │
│  Examples:                                                  │
│  /goal Fix the authentication bug in src/auth.py           │
│  /goal --budget 2 Add unit tests for user service          │
│  /goal --level 5 Refactor the entire codebase              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Error Handling

### Error Message Hierarchy

**Critical Errors** (Block operation):
```
┌─ ❌ Critical Error ─────────────────────────────────────────┐
│                                                              │
│  API key not found                                          │
│                                                              │
│  Lyra cannot function without an API key. Please set:       │
│  export ANTHROPIC_API_KEY=your_key_here                     │
│                                                              │
│  [View Documentation] [Exit]                                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Recoverable Errors** (Suggest action):
```
┌─ ⚠️  Error ─────────────────────────────────────────────────┐
│                                                              │
│  Failed to read file: src/auth.py                           │
│  Reason: File not found                                     │
│                                                              │
│  Suggestions:                                               │
│  • Check if the file path is correct                       │
│  • Use /ls to list available files                         │
│  • Create the file with /create                            │
│                                                              │
│  [Retry] [Cancel]                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Warnings** (Non-blocking):
```
⚠️  Warning: Approaching budget limit (80% used)
    Current: $4.00 / $5.00
    Consider pausing or increasing budget
```

---

## Accessibility

### Screen Reader Support

**Semantic Structure**:
- Use clear headings (H1, H2, H3)
- Provide text alternatives for symbols
- Announce state changes
- Describe visual elements

**Example**:
```
Visual:  ✅ Done!
Screen reader: "Success: Done!"

Visual:  🔄 Processing...
Screen reader: "In progress: Processing..."

Visual:  ❌ Error
Screen reader: "Error occurred"
```

### Keyboard Navigation

**All interactive elements accessible via keyboard**:
- Tab to navigate between elements
- Enter to activate
- Space to toggle
- Esc to cancel/back
- Arrow keys for lists

**Focus Indicators**:
```
Normal:  [Button]
Focused: [Button] ← (highlighted)
```

---

## Content Guidelines

### Writing Style

**Clear and Concise**:
- Use simple language
- Short sentences
- Active voice
- Specific terms

**Examples**:
```
❌ Bad:  "The operation has been completed successfully"
✅ Good: "Done!"

❌ Bad:  "An error has occurred during the execution of the command"
✅ Good: "Command failed: File not found"

❌ Bad:  "The agent is currently in the process of analyzing"
✅ Good: "Analyzing..."
```

### Terminology

**Consistent Terms**:
- Agent (not: bot, assistant, AI)
- Goal (not: task, objective, mission)
- Memory (not: knowledge, context, history)
- Skill (not: capability, function, ability)
- Tool (not: function, command, utility)

### Tone

**Professional but Friendly**:
- Helpful, not condescending
- Clear, not verbose
- Confident, not arrogant
- Supportive, not patronizing

---

## Information Architecture Map

```
Lyra CLI
│
├── Primary Views
│   ├── Chat Mode (default)
│   │   ├── Conversation
│   │   ├── Tool calls
│   │   └── Context (collapsible)
│   │
│   ├── Goal Mode
│   │   ├── Goal header
│   │   ├── Current step
│   │   ├── Plan
│   │   └── Budget & controls
│   │
│   └── Agent View
│       ├── Status
│       ├── Task & memory
│       └── Activity log
│
├── Secondary Views
│   ├── History
│   │   ├── Conversation list
│   │   └── Conversation detail
│   │
│   ├── Memory
│   │   ├── Memory list
│   │   └── Memory detail
│   │
│   ├── Skills
│   │   ├── Skill list
│   │   └── Skill detail
│   │
│   └── Tools
│       ├── Tool list
│       └── Tool detail
│
├── Utility Views
│   ├── Settings
│   │   ├── Model config
│   │   ├── UI preferences
│   │   ├── Safety settings
│   │   └── API keys
│   │
│   └── Help
│       ├── Command reference
│       ├── Shortcuts
│       └── Tips
│
└── Global Features
    ├── Search
    ├── Filters
    ├── Navigation
    └── Shortcuts
```

---

## Summary

This information architecture provides:
- ✅ Clear content organization (3-level hierarchy)
- ✅ Consistent navigation patterns (commands, shortcuts, breadcrumbs)
- ✅ Progressive disclosure (collapsed by default)
- ✅ Search and filter capabilities
- ✅ Contextual help system
- ✅ Accessibility support
- ✅ Content guidelines

**Key Principles**:
- User-centered organization
- Clear hierarchy
- Consistent navigation
- Findable content
- Accessible to all users

**Next**: See 06-BRAND_IDENTITY.md for visual identity and brand guidelines.

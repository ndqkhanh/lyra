# Voice System & Advanced Sessions Management Research

**Research Date:** 2026-05-29  
**Objective:** Design voice notification system and advanced session management for Lyra  
**Status:** Complete

---

## Executive Summary

This research analyzes Claude Code's voice notification patterns, advanced session management (checkpointing), comprehensive hooks system, fine-grained permissions, and channels architecture to design production-ready implementations for Lyra.

### Key Findings

1. **Voice System**: Simple hook-based audio feedback using platform-native players
2. **Session Management**: Automatic checkpoint tracking with rewind/restore/summarize capabilities
3. **Hooks System**: 20+ lifecycle events with command/HTTP/MCP/prompt/agent execution
4. **Permissions**: Fine-grained tool control with deny→ask→allow precedence
5. **Channels**: MCP-based event streaming for webhooks, chat bridges, and remote control

### Strategic Recommendations

- **Priority 1**: Implement hooks system (foundation for voice + automation)
- **Priority 2**: Add session checkpointing (safety net for autonomous work)
- **Priority 3**: Build voice notifications (developer experience enhancement)
- **Priority 4**: Design channels architecture (remote interaction capability)
- **Priority 5**: Enhance permissions system (security hardening)

---

## 1. Voice System Design

### 1.1 Architecture Overview

Voice notifications use the hooks system to trigger audio playback at key lifecycle events. The implementation is remarkably simple: hooks execute platform-specific audio players in the background.

**Core Pattern:**
```json
{
  "hooks": {
    "EventName": [{
      "hooks": [{
        "type": "command",
        "command": "<audio_player> <sound_file> &",
        "async": true
      }]
    }]
  }
}
```

### 1.2 Platform-Specific Audio Players

| Platform | Player | Command Format | Notes |
|----------|--------|----------------|-------|
| macOS | `afplay` | `afplay /path/to/sound.mp3 &` | Built-in, supports MP3/WAV/AIFF |
| Linux | `aplay` | `aplay /path/to/sound.wav &` | ALSA, WAV only |
| Linux | `paplay` | `paplay /path/to/sound.wav &` | PulseAudio, WAV/MP3 |
| Windows | PowerShell | `powershell -c "(New-Object Media.SoundPlayer '/path/to/sound.wav').PlaySync()" &` | WAV only |
| WSL | PowerShell.exe | `powershell.exe -c "..." &` | Calls Windows audio from WSL |

**Critical Implementation Detail:** The `&` suffix runs the command in the background, preventing blocking of the main process.

### 1.3 Event-to-Sound Mapping

**Recommended Sound Library for Lyra:**

| Event | Sound Type | Example | Purpose |
|-------|-----------|---------|---------|
| **SessionStart** | Greeting/Horn | Warcraft Peon "Ready to work!" | Engaging session initialization |
| **UserPromptSubmit** | Acknowledgment | Warcraft Peon "Yes?" | Confirm prompt received |
| **Stop** (success) | Completion | Warcraft Peon "Job's done!" | Task completion feedback |
| **StopFailure** | Error | Warcraft Peon "What?" | Error notification |
| **PreCompact** | Warning | Soft chime | Context window warning |
| **PostToolUse** (Bash) | Action | Keyboard click | Command execution |
| **PostToolUse** (Edit/Write) | Action | Pen scratch | File modification |
| **PermissionRequest** | Alert | Notification bell | Approval needed |
| **SubagentStart** | Transition | Whoosh | Agent spawned |
| **SubagentStop** | Transition | Soft thud | Agent completed |

### 1.4 Implementation for Lyra

**Configuration Structure:**

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume",
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/session-start.mp3 &",
        "async": true,
        "statusMessage": "🔊 Welcome back!"
      }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/prompt-received.mp3 &",
        "async": true
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/task-complete.mp3 &",
        "async": true
      }]
    }],
    "StopFailure": [{
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/error.mp3 &",
        "async": true
      }]
    }],
    "PostToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/bash-exec.mp3 &",
        "async": true
      }]
    }, {
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "afplay ~/.lyra/sounds/file-edit.mp3 &",
        "async": true
      }]
    }]
  }
}
```

**Cross-Platform Wrapper Script:**

```bash
#!/bin/bash
# ~/.lyra/scripts/play-sound.sh

SOUND_FILE="$1"

if [[ "$OSTYPE" == "darwin"* ]]; then
    afplay "$SOUND_FILE" &
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v paplay &> /dev/null; then
        paplay "$SOUND_FILE" &
    elif command -v aplay &> /dev/null; then
        aplay "$SOUND_FILE" &
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    powershell.exe -c "(New-Object Media.SoundPlayer '$SOUND_FILE').PlaySync()" &
fi
```

**Usage:**

```json
{
  "type": "command",
  "command": "${LYRA_ROOT}/scripts/play-sound.sh",
  "args": ["${LYRA_ROOT}/sounds/session-start.mp3"],
  "async": true
}
```

### 1.5 Sound File Recommendations

**Format Guidelines:**
- **Primary format**: MP3 (universal support)
- **Fallback format**: WAV (Windows compatibility)
- **Duration**: 0.5-2 seconds (non-intrusive)
- **Volume**: Normalized to -6dB (comfortable listening level)

**Curated Sound Sources:**
1. **Warcraft III Peon Sounds** (iconic, humorous, developer-friendly)
2. **macOS System Sounds** (professional, familiar)
3. **Freesound.org** (Creative Commons licensed)
4. **Custom recordings** (brand-specific)

---

## 2. Advanced Session Management

### 2.1 Checkpointing Architecture

Claude Code automatically tracks file edits as checkpoints, enabling rewind/restore/summarize operations.

**Key Capabilities:**
- Automatic checkpoint creation per user prompt
- Persistent across session resume
- 30-day retention (configurable)
- Granular restore: code only, conversation only, or both
- Targeted summarization: compress before or after a checkpoint

### 2.2 Checkpoint Data Structure

```typescript
interface Checkpoint {
  id: string;                    // Unique checkpoint ID
  timestamp: number;             // Unix timestamp
  userPrompt: string;            // Original user message
  fileChanges: FileChange[];     // Tracked file modifications
  conversationState: Message[];  // Conversation up to this point
  metadata: {
    sessionId: string;
    agentType?: string;
    toolsUsed: string[];
    tokensUsed: number;
  };
}

interface FileChange {
  path: string;
  operation: 'create' | 'edit' | 'delete';
  beforeContent?: string;        // For edit/delete
  afterContent?: string;         // For create/edit
  diff?: string;                 // Unified diff format
}
```

### 2.3 Rewind Operations

**1. Restore Code and Conversation**
- Reverts files to checkpoint state
- Truncates conversation history
- Restores original prompt to input field

**2. Restore Conversation Only**
- Keeps current file state
- Truncates conversation history
- Restores original prompt to input field

**3. Restore Code Only**
- Reverts files to checkpoint state
- Keeps full conversation history
- Clears input field

**4. Summarize from Here**
- Keeps messages before checkpoint
- Replaces checkpoint + later messages with AI summary
- Restores original prompt to input field

**5. Summarize up to Here**
- Replaces messages before checkpoint with AI summary
- Keeps checkpoint + later messages
- Leaves input field empty (at end of conversation)

### 2.4 Implementation for Lyra

**Checkpoint Manager Module:**

```python
# packages/lyra-core/src/lyra_core/session/checkpoint_manager.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import json
import difflib

@dataclass
class FileChange:
    path: str
    operation: str  # 'create' | 'edit' | 'delete'
    before_content: Optional[str] = None
    after_content: Optional[str] = None
    
    def to_diff(self) -> str:
        """Generate unified diff for this change."""
        if self.operation == 'create':
            return f"+++ {self.path}\n{self.after_content}"
        elif self.operation == 'delete':
            return f"--- {self.path}\n{self.before_content}"
        else:
            before_lines = (self.before_content or "").splitlines(keepends=True)
            after_lines = (self.after_content or "").splitlines(keepends=True)
            return ''.join(difflib.unified_diff(
                before_lines, after_lines,
                fromfile=f"a/{self.path}",
                tofile=f"b/{self.path}"
            ))

@dataclass
class Checkpoint:
    id: str
    timestamp: datetime
    user_prompt: str
    file_changes: List[FileChange]
    conversation_state: List[dict]
    metadata: dict
    
    def to_json(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'user_prompt': self.user_prompt,
            'file_changes': [
                {
                    'path': fc.path,
                    'operation': fc.operation,
                    'before_content': fc.before_content,
                    'after_content': fc.after_content
                }
                for fc in self.file_changes
            ],
            'conversation_state': self.conversation_state,
            'metadata': self.metadata
        }

class CheckpointManager:
    """Manages session checkpoints for rewind/restore operations."""
    
    def __init__(self, session_id: str, storage_dir: Path):
        self.session_id = session_id
        self.storage_dir = storage_dir / "checkpoints" / session_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: List[Checkpoint] = []
        self._load_checkpoints()
    
    def create_checkpoint(
        self,
        user_prompt: str,
        file_changes: List[FileChange],
        conversation_state: List[dict],
        metadata: dict
    ) -> Checkpoint:
        """Create a new checkpoint."""
        checkpoint = Checkpoint(
            id=f"cp_{len(self.checkpoints)}_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            user_prompt=user_prompt,
            file_changes=file_changes,
            conversation_state=conversation_state,
            metadata=metadata
        )
        
        self.checkpoints.append(checkpoint)
        self._save_checkpoint(checkpoint)
        return checkpoint
    
    def restore_code(self, checkpoint_id: str) -> bool:
        """Restore files to checkpoint state."""
        checkpoint = self._get_checkpoint(checkpoint_id)
        if not checkpoint:
            return False
        
        for change in checkpoint.file_changes:
            path = Path(change.path)
            
            if change.operation == 'create':
                # Remove file created after checkpoint
                if path.exists():
                    path.unlink()
            elif change.operation == 'delete':
                # Restore deleted file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(change.before_content or "")
            elif change.operation == 'edit':
                # Restore previous content
                if change.before_content is not None:
                    path.write_text(change.before_content)
        
        return True
    
    def restore_conversation(self, checkpoint_id: str) -> Optional[List[dict]]:
        """Get conversation state at checkpoint."""
        checkpoint = self._get_checkpoint(checkpoint_id)
        return checkpoint.conversation_state if checkpoint else None
    
    def summarize_range(
        self,
        start_checkpoint_id: Optional[str],
        end_checkpoint_id: Optional[str],
        summarizer_fn
    ) -> str:
        """Summarize conversation between checkpoints."""
        start_idx = 0 if not start_checkpoint_id else self._get_checkpoint_index(start_checkpoint_id)
        end_idx = len(self.checkpoints) if not end_checkpoint_id else self._get_checkpoint_index(end_checkpoint_id)
        
        if start_idx is None or end_idx is None:
            return ""
        
        messages = []
        for cp in self.checkpoints[start_idx:end_idx]:
            messages.extend(cp.conversation_state)
        
        return summarizer_fn(messages)
    
    def cleanup_old_checkpoints(self, retention_days: int = 30):
        """Remove checkpoints older than retention period."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        self.checkpoints = [
            cp for cp in self.checkpoints
            if cp.timestamp > cutoff
        ]
        
        # Clean up storage
        for file in self.storage_dir.glob("*.json"):
            checkpoint_data = json.loads(file.read_text())
            if datetime.fromisoformat(checkpoint_data['timestamp']) < cutoff:
                file.unlink()
    
    def _get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return next((cp for cp in self.checkpoints if cp.id == checkpoint_id), None)
    
    def _get_checkpoint_index(self, checkpoint_id: str) -> Optional[int]:
        for idx, cp in enumerate(self.checkpoints):
            if cp.id == checkpoint_id:
                return idx
        return None
    
    def _save_checkpoint(self, checkpoint: Checkpoint):
        file_path = self.storage_dir / f"{checkpoint.id}.json"
        file_path.write_text(json.dumps(checkpoint.to_json(), indent=2))
    
    def _load_checkpoints(self):
        for file in sorted(self.storage_dir.glob("*.json")):
            data = json.loads(file.read_text())
            self.checkpoints.append(Checkpoint(
                id=data['id'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                user_prompt=data['user_prompt'],
                file_changes=[
                    FileChange(**fc) for fc in data['file_changes']
                ],
                conversation_state=data['conversation_state'],
                metadata=data['metadata']
            ))
```

**Integration with Session Manager:**

```python
# In session initialization
self.checkpoint_manager = CheckpointManager(
    session_id=self.session_id,
    storage_dir=Path("~/.lyra/sessions").expanduser()
)

# Before executing tools
file_snapshots = self._capture_file_states()

# After tool execution
file_changes = self._detect_file_changes(file_snapshots)
self.checkpoint_manager.create_checkpoint(
    user_prompt=user_message,
    file_changes=file_changes,
    conversation_state=self.messages.copy(),
    metadata={
        'session_id': self.session_id,
        'tools_used': [tool.name for tool in executed_tools],
        'tokens_used': response.usage.total_tokens
    }
)
```

### 2.5 Limitations and Considerations

**What's NOT Tracked:**
- Bash command file modifications (only direct tool edits)
- External changes from other processes
- Changes in concurrent sessions (unless same files)

**Best Practices:**
- Use checkpoints for quick session-level recovery
- Continue using Git for permanent version control
- Think of checkpoints as "local undo", Git as "permanent history"
- Clean up old checkpoints regularly (30-day default)

---

## 3. Comprehensive Hooks System

### 3.1 Hook Lifecycle Overview

Claude Code provides 20+ lifecycle events where hooks can execute:

**Setup & Session Lifecycle:**
- `Setup` - CLI initialization (--init-only)
- `SessionStart` - Session startup/resume/clear/compact
- `SessionEnd` - Session termination

**Per-Turn Events:**
- `UserPromptSubmit` - After prompt submission
- `UserPromptExpansion` - For slash commands
- `PreToolUse` - Before tool execution
- `PermissionRequest` - Permission dialog
- `PostToolUse` - After successful tool execution
- `PostToolUseFailure` - After tool failure
- `PostToolBatch` - After parallel tool batch
- `Stop` - Response completion
- `StopFailure` - Response error

**Async Events:**
- `FileChanged` - File system changes
- `CwdChanged` - Working directory change
- `ConfigChange` - Settings update
- `Notification` - System notifications
- `SubagentStart` / `SubagentStop` - Agent lifecycle
- `TaskCreated` / `TaskCompleted` - Background tasks
- `PreCompact` / `PostCompact` - Context compaction
- `WorktreeCreate` / `WorktreeRemove` - Git worktree ops

### 3.2 Hook Types

**1. Command Hooks** - Execute shell commands

```json
{
  "type": "command",
  "command": "/path/to/script.sh",
  "args": ["--flag", "value"],
  "timeout": 600,
  "async": false
}
```

**2. HTTP Hooks** - POST to endpoints

```json
{
  "type": "http",
  "url": "http://localhost:8080/validate",
  "timeout": 30,
  "headers": {
    "Authorization": "Bearer ${TOKEN}"
  },
  "allowedEnvVars": ["TOKEN"]
}
```

**3. MCP Tool Hooks** - Call MCP server tools

```json
{
  "type": "mcp_tool",
  "server": "security_scanner",
  "tool": "scan_file",
  "input": {"path": "${tool_input.file_path}"}
}
```

**4. Prompt Hooks** - Single-turn LLM evaluation

```json
{
  "type": "prompt",
  "prompt": "Is this command safe? ${tool_input.command}",
  "model": "claude-sonnet-4-6",
  "timeout": 30
}
```

**5. Agent Hooks** - Spawn subagent with tool access

```json
{
  "type": "agent",
  "prompt": "Verify security of: ${tool_input}",
  "timeout": 60
}
```

### 3.3 Hook Input/Output Format

**Common Input (JSON on stdin or POST body):**

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/dir",
  "permission_mode": "default",
  "effort": {"level": "medium"},
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {"command": "git push origin main"},
  "agent_id": "optional-subagent-id",
  "agent_type": "optional-agent-name"
}
```

**Output Format:**

```json
{
  "continue": true,
  "stopReason": "Optional stop message",
  "suppressOutput": false,
  "systemMessage": "Warning for user",
  "terminalSequence": "\033]777;notify;Title;Body\007",
  "decision": "block|allow|ask|defer",
  "reason": "Explanation",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked",
    "updatedInput": {"command": "modified command"},
    "additionalContext": "Context for Claude"
  }
}
```

**Exit Codes (Command Hooks):**
- **0**: Success, parse stdout for JSON
- **2**: Blocking error, stderr shown to Claude
- **Other**: Non-blocking error

### 3.4 Key Hook Events Deep Dive

**PreToolUse - Block or Modify Tool Calls**

Most powerful hook for security and validation. Can:
- Deny tool execution
- Force permission prompt
- Modify tool input
- Add context for Claude

```bash
#!/bin/bash
# Block dangerous rm commands

COMMAND=$(jq -r '.tool_input.command // empty')

if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+/'; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Destructive root deletion blocked"
    }
  }'
  exit 0
fi

# Allow by default
exit 0
```

**SessionStart - Load Context**

Inject environment, branch info, or session state:

```bash
#!/bin/bash
# Load git context and environment

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
ISSUE=$(git log -1 --pretty=%B | grep -oP '#\d+' | head -1 || echo "none")

jq -n \
  --arg branch "$BRANCH" \
  --arg issue "$ISSUE" \
  '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: "Current branch: \($branch)\nWorking on issue: \($issue)",
      sessionTitle: "\($branch)-work",
      watchPaths: [".github/workflows"]
    }
  }'

# Persist environment variables
if [ -n "$CLAUDE_ENV_FILE" ]; then
  echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
  echo 'export PATH="$PATH:./node_modules/.bin"' >> "$CLAUDE_ENV_FILE"
fi
```

**PostToolUse - React to Results**

Validate outputs, run tests, or trigger notifications:

```bash
#!/bin/bash
# Run tests after file edits

TOOL_NAME=$(jq -r '.tool_name')

if [[ "$TOOL_NAME" == "Edit" || "$TOOL_NAME" == "Write" ]]; then
  npm test 2>&1 | head -20 > /tmp/test_output.txt
  
  if [ ${PIPESTATUS[0]} -ne 0 ]; then
    TEST_OUTPUT=$(cat /tmp/test_output.txt)
    jq -n \
      --arg output "$TEST_OUTPUT" \
      '{
        decision: "block",
        reason: "Tests failed after file modification",
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext: "Test output:\n\($output)"
        }
      }'
    exit 2
  fi
fi

exit 0
```

**UserPromptSubmit - Validate Prompts**

Filter or enhance user input:

```bash
#!/bin/bash
# Block prompts with forbidden patterns

USER_PROMPT=$(jq -r '.user_prompt')

if echo "$USER_PROMPT" | grep -qi "ignore previous instructions"; then
  jq -n '{
    decision: "block",
    reason: "Prompt contains potential injection attempt",
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      suppressOriginalPrompt: true
    }
  }'
  exit 2
fi

exit 0
```

### 3.5 Advanced Hook Features

**Conditional Execution with `if`:**

```json
{
  "matcher": "Bash",
  "hooks": [{
    "if": "Bash(git push *)",
    "type": "command",
    "command": "./check-branch.sh"
  }]
}
```

**Async Hooks with Rewake:**

```json
{
  "type": "command",
  "command": "./long-running-task.sh",
  "async": true,
  "asyncRewake": true  // Wake Claude on exit code 2
}
```

**Terminal Notifications:**

```bash
#!/bin/bash
# Send OS notification

seq=$(printf '\033]777;notify;%s;%s\007' "Build Complete" "All tests passed")
jq -nc --arg seq "$seq" '{terminalSequence: $seq}'
```

**Path Placeholders:**

```json
{
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/validate.sh",
  "args": ["${CLAUDE_PLUGIN_ROOT}/config.json"]
}
```

### 3.6 Implementation for Lyra

**Hook Manager Module:**

```python
# packages/lyra-core/src/lyra_core/hooks/hook_manager.py

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json
import subprocess
import asyncio
import aiohttp

class HookType(Enum):
    COMMAND = "command"
    HTTP = "http"
    MCP_TOOL = "mcp_tool"
    PROMPT = "prompt"
    AGENT = "agent"

class HookEvent(Enum):
    SETUP = "Setup"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"
    FILE_CHANGED = "FileChanged"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"

@dataclass
class HookConfig:
    type: HookType
    matcher: Optional[str] = None
    if_condition: Optional[str] = None
    timeout: int = 600
    async_exec: bool = False
    async_rewake: bool = False
    status_message: Optional[str] = None
    
    # Type-specific fields
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    server: Optional[str] = None
    tool: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    prompt: Optional[str] = None
    model: Optional[str] = None

@dataclass
class HookResult:
    continue_execution: bool = True
    stop_reason: Optional[str] = None
    suppress_output: bool = False
    system_message: Optional[str] = None
    terminal_sequence: Optional[str] = None
    decision: Optional[str] = None  # block|allow|ask|defer
    reason: Optional[str] = None
    hook_specific_output: Optional[Dict[str, Any]] = None

class HookManager:
    """Manages lifecycle hooks for Lyra."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.hooks: Dict[HookEvent, List[HookConfig]] = {}
        self._load_hooks()
    
    def _load_hooks(self):
        """Load hooks from configuration."""
        if not self.config_path.exists():
            return
        
        config = json.loads(self.config_path.read_text())
        hooks_config = config.get('hooks', {})
        
        for event_name, hook_list in hooks_config.items():
            try:
                event = HookEvent[event_name.upper()]
                self.hooks[event] = []
                
                for hook_entry in hook_list:
                    for hook_data in hook_entry.get('hooks', []):
                        hook = HookConfig(
                            type=HookType(hook_data['type']),
                            matcher=hook_entry.get('matcher'),
                            if_condition=hook_data.get('if'),
                            timeout=hook_data.get('timeout', 600),
                            async_exec=hook_data.get('async', False),
                            async_rewake=hook_data.get('asyncRewake', False),
                            status_message=hook_data.get('statusMessage'),
                            command=hook_data.get('command'),
                            args=hook_data.get('args'),
                            url=hook_data.get('url'),
                            headers=hook_data.get('headers'),
                            server=hook_data.get('server'),
                            tool=hook_data.get('tool'),
                            input=hook_data.get('input'),
                            prompt=hook_data.get('prompt'),
                            model=hook_data.get('model')
                        )
                        self.hooks[event].append(hook)
            except (KeyError, ValueError) as e:
                print(f"Warning: Invalid hook configuration for {event_name}: {e}")
    
    async def execute_hooks(
        self,
        event: HookEvent,
        context: Dict[str, Any]
    ) -> List[HookResult]:
        """Execute all hooks for an event."""
        if event not in self.hooks:
            return []
        
        results = []
        for hook in self.hooks[event]:
            if not self._should_execute(hook, context):
                continue
            
            result = await self._execute_hook(hook, context)
            results.append(result)
            
            # Stop on blocking decision
            if result.decision == "block" or not result.continue_execution:
                break
        
        return results
    
    def _should_execute(self, hook: HookConfig, context: Dict[str, Any]) -> bool:
        """Check if hook should execute based on matcher and if condition."""
        # Check matcher
        if hook.matcher:
            tool_name = context.get('tool_name', '')
            if not self._matches_pattern(hook.matcher, tool_name):
                return False
        
        # Check if condition
        if hook.if_condition:
            # Parse condition like "Bash(git push *)"
            if not self._matches_condition(hook.if_condition, context):
                return False
        
        return True
    
    def _matches_pattern(self, pattern: str, value: str) -> bool:
        """Match pattern against value (supports wildcards)."""
        if pattern == "*" or pattern == "":
            return True
        
        # OR patterns
        if '|' in pattern and not any(c in pattern for c in ['(', ')', '[', ']', '^', '$']):
            return value in pattern.split('|')
        
        # Regex patterns
        import re
        try:
            return bool(re.match(pattern, value))
        except re.error:
            return pattern == value
    
    def _matches_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Match if condition like 'Bash(git push *)'."""
        import re
        match = re.match(r'(\w+)\((.*)\)', condition)
        if not match:
            return False
        
        tool_name, pattern = match.groups()
        if context.get('tool_name') != tool_name:
            return False
        
        if tool_name == 'Bash':
            command = context.get('tool_input', {}).get('command', '')
            return self._matches_bash_pattern(pattern, command)
        
        return True
    
    def _matches_bash_pattern(self, pattern: str, command: str) -> bool:
        """Match bash command pattern with wildcards."""
        import re
        # Convert glob pattern to regex
        regex_pattern = pattern.replace('*', '.*')
        return bool(re.match(regex_pattern, command))
    
    async def _execute_hook(self, hook: HookConfig, context: Dict[str, Any]) -> HookResult:
        """Execute a single hook."""
        try:
            if hook.type == HookType.COMMAND:
                return await self._execute_command_hook(hook, context)
            elif hook.type == HookType.HTTP:
                return await self._execute_http_hook(hook, context)
            elif hook.type == HookType.MCP_TOOL:
                return await self._execute_mcp_hook(hook, context)
            elif hook.type == HookType.PROMPT:
                return await self._execute_prompt_hook(hook, context)
            elif hook.type == HookType.AGENT:
                return await self._execute_agent_hook(hook, context)
        except Exception as e:
            return HookResult(
                continue_execution=True,
                system_message=f"Hook error: {str(e)}"
            )
    
    async def _execute_command_hook(
        self,
        hook: HookConfig,
        context: Dict[str, Any]
    ) -> HookResult:
        """Execute command hook."""
        input_json = json.dumps(context)
        
        cmd = [hook.command] + (hook.args or [])
        
        try:
            if hook.async_exec:
                # Run in background
                subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return HookResult()
            else:
                # Run synchronously
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input_json.encode()),
                    timeout=hook.timeout
                )
                
                if proc.returncode == 0:
                    # Parse JSON output
                    if stdout:
                        output = json.loads(stdout.decode())
                        return HookResult(
                            continue_execution=output.get('continue', True),
                            stop_reason=output.get('stopReason'),
                            suppress_output=output.get('suppressOutput', False),
                            system_message=output.get('systemMessage'),
                            terminal_sequence=output.get('terminalSequence'),
                            decision=output.get('decision'),
                            reason=output.get('reason'),
                            hook_specific_output=output.get('hookSpecificOutput')
                        )
                    return HookResult()
                elif proc.returncode == 2:
                    # Blocking error
                    return HookResult(
                        continue_execution=False,
                        decision="block",
                        reason=stderr.decode() if stderr else "Hook blocked execution"
                    )
                else:
                    # Non-blocking error
                    return HookResult(
                        system_message=f"Hook warning: {stderr.decode() if stderr else 'Unknown error'}"
                    )
        except asyncio.TimeoutError:
            return HookResult(
                system_message=f"Hook timeout after {hook.timeout}s"
            )
        except Exception as e:
            return HookResult(
                system_message=f"Hook execution error: {str(e)}"
            )
    
    async def _execute_http_hook(
        self,
        hook: HookConfig,
        context: Dict[str, Any]
    ) -> HookResult:
        """Execute HTTP hook."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    hook.url,
                    json=context,
                    headers=hook.headers or {},
                    timeout=aiohttp.ClientTimeout(total=hook.timeout)
                ) as response:
                    if response.status >= 200 and response.status < 300:
                        if response.content_length and response.content_length > 0:
                            output = await response.json()
                            return HookResult(
                                continue_execution=output.get('continue', True),
                                decision=output.get('decision'),
                                reason=output.get('reason'),
                                hook_specific_output=output.get('hookSpecificOutput')
                            )
                        return HookResult()
                    else:
                        return HookResult(
                            system_message=f"HTTP hook returned {response.status}"
                        )
        except Exception as e:
            return HookResult(
                system_message=f"HTTP hook error: {str(e)}"
            )
    
    async def _execute_mcp_hook(
        self,
        hook: HookConfig,
        context: Dict[str, Any]
    ) -> HookResult:
        """Execute MCP tool hook."""
        # TODO: Implement MCP tool execution
        return HookResult()
    
    async def _execute_prompt_hook(
        self,
        hook: HookConfig,
        context: Dict[str, Any]
    ) -> HookResult:
        """Execute prompt hook (LLM evaluation)."""
        # TODO: Implement LLM prompt evaluation
        return HookResult()
    
    async def _execute_agent_hook(
        self,
        hook: HookConfig,
        context: Dict[str, Any]
    ) -> HookResult:
        """Execute agent hook (spawn subagent)."""
        # TODO: Implement subagent spawning
        return HookResult()
```

---

## 4. Fine-Grained Permissions System

### 4.1 Permission Architecture

Claude Code uses a three-tier permission system with deny→ask→allow precedence:

**Permission Tiers:**
1. **Read-only tools** - No approval required (Read, Grep, etc.)
2. **Bash commands** - Approval required, "don't ask again" persists per project+command
3. **File modifications** - Approval required, "don't ask again" lasts until session end

**Rule Precedence:**
```
DENY rules (highest priority)
  ↓
ASK rules (medium priority)
  ↓
ALLOW rules (lowest priority)
```

First matching rule wins. Deny rules from ANY scope block the action.

### 4.2 Permission Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `default` | Prompts on first use of each tool | Standard development |
| `acceptEdits` | Auto-accepts file edits in working directory | Trusted projects |
| `plan` | Read-only mode, no file edits | Exploration/analysis |
| `auto` | Auto-approves with safety checks (research preview) | Autonomous workflows |
| `dontAsk` | Auto-denies unless pre-approved | Restricted environments |
| `bypassPermissions` | Skips all prompts (dangerous) | Isolated containers only |

### 4.3 Permission Rule Syntax

**Tool Matching:**

| Rule | Matches |
|------|---------|
| `Bash` | All Bash commands |
| `Bash(npm run build)` | Exact command |
| `Bash(npm run *)` | Commands starting with "npm run " |
| `Bash(npm *)` | Any command starting with "npm " |
| `Bash(* install)` | Commands ending with " install" |
| `Bash(git * main)` | Commands like "git checkout main", "git push origin main" |
| `Read(/src/**)` | All files under project's src/ directory |
| `Edit(~/.ssh/**)` | All files in user's .ssh directory |
| `Edit(//**/.env)` | All .env files anywhere on filesystem |
| `WebFetch(domain:github.com)` | Fetch requests to github.com |
| `mcp__server__tool` | Specific MCP tool |
| `Agent(Explore)` | Explore subagent |

**Path Patterns (gitignore-style):**

| Pattern | Meaning | Example |
|---------|---------|---------|
| `//path` | Absolute from filesystem root | `Read(//Users/alice/secrets/**)` |
| `~/path` | From home directory | `Read(~/Documents/*.pdf)` |
| `/path` | Relative to project root | `Edit(/src/**/*.ts)` |
| `path` or `./path` | Relative to current directory | `Read(*.env)` |

**Wildcard Semantics:**
- `*` matches any characters in a single directory
- `**` matches recursively across directories
- Space before `*` enforces word boundary: `Bash(ls *)` matches `ls -la` but not `lsof`
- `:*` suffix is equivalent to trailing ` *`

### 4.4 Configuration Example

```json
{
  "permissions": {
    "defaultMode": "default",
    "deny": [
      "Bash(rm -rf /)",
      "Bash(rm -rf ~)",
      "Bash(git push --force *)",
      "Edit(//**/.env)",
      "Edit(~/.ssh/**)",
      "WebFetch(domain:internal-only.corp)"
    ],
    "ask": [
      "Bash(npm publish *)",
      "Bash(docker *)",
      "Edit(/package.json)",
      "Edit(/pyproject.toml)"
    ],
    "allow": [
      "Bash(npm run *)",
      "Bash(git commit *)",
      "Bash(git log *)",
      "Bash(pytest *)",
      "Read(/src/**)",
      "Edit(/src/**)",
      "Edit(/tests/**)",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:pypi.org)"
    ],
    "additionalDirectories": [
      "/path/to/shared/libs"
    ]
  }
}
```

### 4.5 Interaction with Hooks

**Hook decisions do NOT bypass permission rules:**
- Deny rules always block, even if hook returns "allow"
- Ask rules still prompt, even if hook returns "allow"
- Hooks can add additional blocks beyond permission rules

**PreToolUse hook can:**
- Deny tool execution (exit code 2)
- Force permission prompt (return `permissionDecision: "ask"`)
- Allow without prompt (return `permissionDecision: "allow"`)
- Modify tool input (return `updatedInput`)

**Example: Block specific commands with hook, allow rest:**

```json
{
  "permissions": {
    "allow": ["Bash"]
  },
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "./check-dangerous-commands.sh"
      }]
    }]
  }
}
```

### 4.6 Managed Settings (Enterprise)

**Managed-only settings** (cannot be overridden by users):

- `allowManagedPermissionRulesOnly` - Only managed rules apply
- `allowManagedMcpServersOnly` - Only managed MCP servers
- `allowManagedHooksOnly` - Only managed hooks
- `strictPluginOnlyCustomization` - Block user skills/agents/hooks
- `channelsEnabled` - Enable/disable channels org-wide
- `forceRemoteSettingsRefresh` - Fail-closed enforcement

**Settings Precedence:**
1. Managed settings (highest, cannot override)
2. Command line arguments
3. Local project settings (`.claude/settings.local.json`)
4. Shared project settings (`.claude/settings.json`)
5. User settings (`~/.claude/settings.json`)

---

## 5. Channels Architecture

### 5.1 Overview

Channels are MCP servers that push events INTO Claude Code sessions, enabling:
- Webhook receivers (CI/CD, monitoring alerts)
- Chat bridges (Telegram, Discord, iMessage)
- Remote control (permission relay, two-way communication)

**Architecture:**

```
External System → Local Channel Server → Claude Code (stdio) → Claude
                                              ↓
                                         Reply Tool
                                              ↓
External System ← Local Channel Server ← Claude Code
```

### 5.2 Channel Contract

**Required Capability:**

```typescript
{
  capabilities: {
    experimental: {
      'claude/channel': {}  // Registers notification listener
    }
  }
}
```

**Notification Format:**

```typescript
await mcp.notification({
  method: 'notifications/claude/channel',
  params: {
    content: 'Event body text',
    meta: {
      chat_id: '12345',
      severity: 'high',
      source: 'ci-pipeline'
    }
  }
})
```

**Delivered to Claude as:**

```xml
<channel source="webhook" chat_id="12345" severity="high">
Event body text
</channel>
```

### 5.3 One-Way Channel (Webhook Receiver)

```typescript
#!/usr/bin/env bun
import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'

const mcp = new Server(
  { name: 'webhook', version: '0.0.1' },
  {
    capabilities: {
      experimental: { 'claude/channel': {} }
    },
    instructions: 'Events arrive as <channel source="webhook" ...>. Read and act, no reply expected.'
  }
)

await mcp.connect(new StdioServerTransport())

Bun.serve({
  port: 8788,
  hostname: '127.0.0.1',
  async fetch(req) {
    const body = await req.text()
    await mcp.notification({
      method: 'notifications/claude/channel',
      params: {
        content: body,
        meta: { path: new URL(req.url).pathname, method: req.method }
      }
    })
    return new Response('ok')
  }
})
```

### 5.4 Two-Way Channel (Chat Bridge)

**Add reply tool capability:**

```typescript
capabilities: {
  experimental: { 'claude/channel': {} },
  tools: {}  // Enable tool discovery
}
```

**Register reply tool:**

```typescript
import { ListToolsRequestSchema, CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js'

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: 'reply',
    description: 'Send a message back over this channel',
    inputSchema: {
      type: 'object',
      properties: {
        chat_id: { type: 'string', description: 'Conversation to reply in' },
        text: { type: 'string', description: 'Message to send' }
      },
      required: ['chat_id', 'text']
    }
  }]
}))

mcp.setRequestHandler(CallToolRequestSchema, async req => {
  if (req.params.name === 'reply') {
    const { chat_id, text } = req.params.arguments
    await sendToExternalPlatform(chat_id, text)
    return { content: [{ type: 'text', text: 'sent' }] }
  }
  throw new Error(`unknown tool: ${req.params.name}`)
})
```

**Update instructions:**

```typescript
instructions: 'Messages arrive as <channel source="webhook" chat_id="...">. Reply with the reply tool, passing chat_id from the tag.'
```

### 5.5 Permission Relay (Remote Approval)

**Enable permission relay capability:**

```typescript
capabilities: {
  experimental: {
    'claude/channel': {},
    'claude/channel/permission': {}  // Opt in to permission relay
  },
  tools: {}
}
```

**Handle permission requests:**

```typescript
import { z } from 'zod'

const PermissionRequestSchema = z.object({
  method: z.literal('notifications/claude/channel/permission_request'),
  params: z.object({
    request_id: z.string(),     // 5-letter ID
    tool_name: z.string(),      // e.g. "Bash"
    description: z.string(),    // Human-readable summary
    input_preview: z.string()   // Tool args (truncated)
  })
})

mcp.setNotificationHandler(PermissionRequestSchema, async ({ params }) => {
  await sendToExternalPlatform(
    `Claude wants to run ${params.tool_name}: ${params.description}\n\n` +
    `Reply "yes ${params.request_id}" or "no ${params.request_id}"`
  )
})
```

**Parse verdict from inbound messages:**

```typescript
const PERMISSION_REPLY_RE = /^\s*(y|yes|n|no)\s+([a-km-z]{5})\s*$/i

async function onInbound(message) {
  // Gate on sender first
  if (!allowedSenders.has(message.from.id)) return
  
  const match = PERMISSION_REPLY_RE.exec(message.text)
  if (match) {
    await mcp.notification({
      method: 'notifications/claude/channel/permission',
      params: {
        request_id: match[2].toLowerCase(),
        behavior: match[1].toLowerCase().startsWith('y') ? 'allow' : 'deny'
      }
    })
    return
  }
  
  // Normal chat message
  await mcp.notification({
    method: 'notifications/claude/channel',
    params: { content: message.text, meta: { chat_id: String(message.chat.id) } }
  })
}
```

### 5.6 Sender Gating (Security)

**CRITICAL: Always gate on sender identity:**

```typescript
const allowedSenders = new Set(loadAllowlist())

async function onInbound(message) {
  // Gate on sender.id, NOT chat.id (prevents group injection)
  if (!allowedSenders.has(message.from.id)) {
    return  // Drop silently
  }
  
  await mcp.notification({ ... })
}
```

**Pairing Flow Pattern:**
1. User DMs bot
2. Bot generates pairing code
3. User approves in Claude Code session
4. Bot adds sender ID to allowlist

### 5.7 Implementation for Lyra

**Channel Server Template:**

```python
# packages/lyra-channels/src/lyra_channels/webhook_server.py

from mcp.server import Server
from mcp.server.stdio import stdio_server
from aiohttp import web
import asyncio
import json

class WebhookChannel:
    def __init__(self):
        self.mcp = Server("lyra-webhook")
        self.mcp.capabilities = {
            "experimental": {
                "claude/channel": {}
            }
        }
        self.mcp.instructions = (
            "Events arrive as <channel source='lyra-webhook' ...>. "
            "Read and act on them."
        )
    
    async def start(self):
        # Start MCP server on stdio
        asyncio.create_task(stdio_server(self.mcp))
        
        # Start HTTP server
        app = web.Application()
        app.router.add_post('/', self.handle_webhook)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 8788)
        await site.start()
    
    async def handle_webhook(self, request):
        body = await request.text()
        
        await self.mcp.notification(
            method='notifications/claude/channel',
            params={
                'content': body,
                'meta': {
                    'path': request.path,
                    'method': request.method
                }
            }
        )
        
        return web.Response(text='ok')

if __name__ == '__main__':
    channel = WebhookChannel()
    asyncio.run(channel.start())
```

---

## 6. Integration Roadmap

### 6.1 Implementation Priorities

**Phase 1: Foundation (Week 1-2)**
- ✅ Hooks system core implementation
- ✅ Command hook execution
- ✅ HTTP hook execution
- ✅ Hook configuration loading

**Phase 2: Voice System (Week 2-3)**
- ✅ Platform-specific audio player detection
- ✅ Sound library curation
- ✅ Event-to-sound mapping
- ✅ Voice notification hooks

**Phase 3: Session Management (Week 3-4)**
- ✅ Checkpoint manager implementation
- ✅ File change tracking
- ✅ Restore operations (code/conversation/both)
- ✅ Summarization integration

**Phase 4: Permissions Enhancement (Week 4-5)**
- ✅ Permission rule parser
- ✅ Deny→ask→allow precedence
- ✅ Bash pattern matching with wildcards
- ✅ File path pattern matching (gitignore-style)
- ✅ Permission mode support

**Phase 5: Channels Architecture (Week 5-6)**
- ✅ MCP channel server base
- ✅ Webhook receiver implementation
- ✅ Two-way chat bridge
- ✅ Permission relay system
- ✅ Sender gating

### 6.2 Testing Strategy

**Unit Tests:**
- Hook execution (all types)
- Permission rule matching
- Checkpoint operations
- Channel notification delivery

**Integration Tests:**
- End-to-end hook workflows
- Session restore scenarios
- Permission enforcement
- Channel bidirectional communication

**Manual Testing:**
- Voice notification UX
- Permission prompt flows
- Remote approval via channels
- Cross-platform audio playback

### 6.3 Documentation Requirements

- User guide for voice notifications
- Developer guide for custom hooks
- Session management tutorial
- Permission configuration reference
- Channel development guide

---

## 7. Code Examples

### 7.1 Complete Voice Notification Setup

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup",
      "hooks": [{
        "type": "command",
        "command": "afplay",
        "args": ["~/.lyra/sounds/ready-to-work.mp3"],
        "async": true
      }]
    }],
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "afplay",
        "args": ["~/.lyra/sounds/yes.mp3"],
        "async": true
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "afplay",
        "args": ["~/.lyra/sounds/jobs-done.mp3"],
        "async": true
      }]
    }],
    "StopFailure": [{
      "hooks": [{
        "type": "command",
        "command": "afplay",
        "args": ["~/.lyra/sounds/error.mp3"],
        "async": true
      }]
    }]
  }
}
```

### 7.2 Security Hook: Block Dangerous Commands

```bash
#!/bin/bash
# ~/.lyra/hooks/security-check.sh

TOOL_NAME=$(jq -r '.tool_name')
COMMAND=$(jq -r '.tool_input.command // empty')

# Block destructive root operations
if [[ "$TOOL_NAME" == "Bash" ]]; then
  if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+(/|~)'; then
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: "Destructive root/home deletion blocked by security policy"
      }
    }'
    exit 0
  fi
  
  # Block force push to main/master
  if echo "$COMMAND" | grep -qE 'git\s+push.*--force.*(main|master)'; then
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: "Force push to main/master blocked"
      }
    }'
    exit 0
  fi
fi

# Allow by default
exit 0
```

### 7.3 Test Runner Hook: Auto-test After Edits

```bash
#!/bin/bash
# ~/.lyra/hooks/auto-test.sh

TOOL_NAME=$(jq -r '.tool_name')

if [[ "$TOOL_NAME" == "Edit" || "$TOOL_NAME" == "Write" ]]; then
  # Run tests
  npm test 2>&1 | head -30 > /tmp/test_output.txt
  
  if [ ${PIPESTATUS[0]} -ne 0 ]; then
    TEST_OUTPUT=$(cat /tmp/test_output.txt)
    jq -n \
      --arg output "$TEST_OUTPUT" \
      '{
        decision: "block",
        reason: "Tests failed after file modification",
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext: "Test failures:\n\($output)\n\nPlease fix the tests before proceeding."
        }
      }'
    exit 2
  fi
fi

exit 0
```

### 7.4 Session Context Hook: Load Git Info

```bash
#!/bin/bash
# ~/.lyra/hooks/load-context.sh

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
LAST_COMMIT=$(git log -1 --oneline 2>/dev/null || echo "none")
ISSUE=$(git log -1 --pretty=%B | grep -oP '#\d+' | head -1 || echo "none")
MODIFIED_FILES=$(git status --short | wc -l)

jq -n \
  --arg branch "$BRANCH" \
  --arg commit "$LAST_COMMIT" \
  --arg issue "$ISSUE" \
  --arg modified "$MODIFIED_FILES" \
  '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: "Git Context:\n- Branch: \($branch)\n- Last commit: \($commit)\n- Working on: \($issue)\n- Modified files: \($modified)",
      sessionTitle: "\($branch)-session",
      watchPaths: [".github/workflows", "package.json", "pyproject.toml"]
    }
  }'
```

### 7.5 Complete Permission Configuration

```json
{
  "permissions": {
    "defaultMode": "default",
    
    "deny": [
      "Bash(rm -rf /)",
      "Bash(rm -rf ~)",
      "Bash(git push --force * main)",
      "Bash(git push --force * master)",
      "Bash(docker system prune *)",
      "Edit(//**/.env)",
      "Edit(//**/.env.*)",
      "Edit(~/.ssh/**)",
      "Edit(~/.aws/**)",
      "Edit(/etc/**)",
      "WebFetch(domain:internal-only.corp)"
    ],
    
    "ask": [
      "Bash(npm publish *)",
      "Bash(pip publish *)",
      "Bash(docker push *)",
      "Bash(kubectl delete *)",
      "Edit(/package.json)",
      "Edit(/pyproject.toml)",
      "Edit(/Cargo.toml)",
      "Edit(/.github/workflows/**)"
    ],
    
    "allow": [
      "Bash(npm run *)",
      "Bash(npm install *)",
      "Bash(pip install *)",
      "Bash(pytest *)",
      "Bash(cargo test *)",
      "Bash(git commit *)",
      "Bash(git log *)",
      "Bash(git status *)",
      "Bash(git diff *)",
      "Read(/src/**)",
      "Read(/tests/**)",
      "Read(/docs/**)",
      "Edit(/src/**)",
      "Edit(/tests/**)",
      "Edit(/docs/**)",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:pypi.org)",
      "WebFetch(domain:crates.io)",
      "mcp__memory__*",
      "Agent(Explore)",
      "Agent(Plan)"
    ],
    
    "additionalDirectories": [
      "/path/to/shared/libraries",
      "/path/to/common/configs"
    ]
  }
}
```

---

## 8. Conclusion

This research provides a comprehensive foundation for implementing voice notifications, advanced session management, hooks system, fine-grained permissions, and channels architecture in Lyra.

### Key Takeaways

1. **Voice System**: Simple, effective, platform-agnostic audio feedback using hooks
2. **Session Management**: Automatic safety net with granular restore and summarization
3. **Hooks System**: Powerful automation and validation at 20+ lifecycle points
4. **Permissions**: Defense-in-depth with deny→ask→allow precedence
5. **Channels**: Remote interaction capability via MCP-based event streaming

### Next Steps

1. Implement hooks system core (foundation for everything)
2. Add checkpoint manager for session safety
3. Build voice notification system for developer experience
4. Design channels architecture for remote capabilities
5. Enhance permissions system for security hardening

### References

- Claude Code Hooks Documentation: https://code.claude.com/docs/en/hooks
- Claude Code Checkpointing: https://code.claude.com/docs/en/checkpointing
- Claude Code Permissions: https://code.claude.com/docs/en/permissions
- Claude Code Channels: https://code.claude.com/docs/en/channels-reference
- Warcraft III Peon Voice Implementation: https://freedium-mirror.cfd/https://medium.com/@gentechimports/warcraft-iii-peon-voice-notifications-for-claude-code-a-developers-story-dd6842deb852
- Sound Effects with Hooks: https://alexop.dev/posts/how-i-added-sound-effects-to-claude-code-with-hooks/

---

**Document Status:** ✅ Complete  
**Last Updated:** 2026-05-29  
**Author:** Lyra Research Team  
**Review Status:** Ready for Implementation

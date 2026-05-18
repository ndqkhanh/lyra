#!/bin/bash
# Manual Interactive Test Guide for Lyra with DeepSeek

cat << 'EOF'
════════════════════════════════════════════════════════════════
  Lyra Interactive Test Guide with DeepSeek
════════════════════════════════════════════════════════════════

OBSERVATIONS FROM AUTOMATED TESTS:
✓ Lyra launches successfully with DeepSeek
✓ Status bar shows: model, tokens, cost, context %, cache, turn count
✓ Keyboard shortcuts displayed: ctrl+c, ctrl+o, ctrl+h, ctrl+r
✓ Welcome banner with ASCII art and version info
✓ Mode cycling hint: "shift+tab cycle mode"

MANUAL TESTS TO RUN:

1. BASIC CHAT TEST
   Command: ly --model deepseek-chat
   Type: "What is async/await in Python? Explain briefly."
   
   ✓ Check for:
   - Spinner animation while thinking
   - Token count updates in status bar
   - Response appears clearly
   - Cost tracking updates

2. DEEP RESEARCH TEST
   Command: ly --model deepseek-reasoner
   Type: "/research transformer architecture"
   
   ✓ Check for:
   - Multiple agents spawning (⏺ Running X agents...)
   - Progress per agent (tool uses, tokens)
   - Background task indicators (ctrl+b hint)
   - Subagent names (oh-my-claudecode:explore, etc.)
   - Final synthesis

3. MODEL SWITCHING TEST
   Command: ly
   Type: "/model"
   
   ✓ Check for:
   - Interactive model picker
   - Effort slider (←/→ to adjust)
   - Model list with descriptions
   - Confirmation prompt

4. STATUS & TOOLS TEST
   Command: ly
   Type: "/status"
   Type: "/tools"
   Type: "/skills"
   
   ✓ Check for:
   - Current model and slots displayed
   - Budget information
   - Available tools list
   - Loaded skills

5. CONTEXT MANAGEMENT TEST
   Command: ly
   Type: "Remember: I prefer concise answers"
   Type: "/memory"
   Type: "/context checkpoint test1"
   
   ✓ Check for:
   - Memory stored confirmation
   - Checkpoint saved message
   - Context window stats

6. ERROR HANDLING TEST
   Command: ly
   Type: "/invalid_command"
   Type: "/model nonexistent-model"
   
   ✓ Check for:
   - Clear error messages
   - Suggestions for corrections
   - No crashes

7. BACKGROUND TASK TEST
   Command: ly
   Type: "Write a Python script to calculate fibonacci"
   Press: Ctrl+B (before response completes)
   
   ✓ Check for:
   - Task moves to background
   - Status bar shows "bg tasks ↓"
   - Can continue working
   - Notification when complete

8. TOOL OUTPUT EXPANSION TEST
   Command: ly
   Type: "List files in current directory"
   Press: Ctrl+O (when tool output appears)
   
   ✓ Check for:
   - Expanded tool output
   - Full command details
   - "ctrl+o to expand" hint

RUN THESE TESTS:
════════════════════════════════════════════════════════════════

# Test 1: Basic chat
ly --model deepseek-chat

# Test 2: Deep research (takes 2-3 minutes)
ly --model deepseek-reasoner

# Test 3: Interactive features
ly

════════════════════════════════════════════════════════════════
EXPECTED UX ELEMENTS (from Claude Code reference):

✓ Spinner states: ⏺ ✳ ✻ ✶ ✽
✓ Progress format: "⏺ Running 4 agents... (ctrl+o to expand)"
✓ Agent details: "├ agent-name · X tool uses · Y.Zk tokens"
✓ Status updates: "✳ Blanching... (10m 50s · ↓ 62.1k tokens)"
✓ Tips: "⎿ Tip: Use /btw to ask a quick side question..."
✓ Background hints: "(ctrl+b to run in background)"
✓ Task management: "↓ to manage" in status bar
✓ Compaction notice: "✻ Conversation compacted (ctrl+o for history)"

════════════════════════════════════════════════════════════════
EOF

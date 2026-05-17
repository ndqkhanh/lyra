# Quick Start: Manual Testing Lyra CLI

**Run these commands to verify Lyra's UX features work correctly.**

## Setup (One-time)

```bash
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra
export DEEPSEEK_API_KEY=$(cat ~/.lyra/auth.json | jq -r '.providers.deepseek.api_key')
```

## Quick Test Suite (5 minutes)

### Test 1: Basic Chat (30 seconds)
```bash
lyra --model deepseek-chat
```
Type: `What is 2+2?`

**Expected:** Status bar shows model, tokens, cost, spinner animates, response appears.

---

### Test 2: Deep Research (2-3 minutes)
```bash
lyra --model deepseek-reasoner
```
Type: `/research "Python async patterns"`

**Expected:** Multiple agents spawn, progress shown per agent, final synthesis with citations.

---

### Test 3: Model Picker (30 seconds)
```bash
lyra
```
Type: `/model`

**Expected:** Interactive picker with effort slider, model descriptions.

---

### Test 4: Command Palette (30 seconds)
```bash
lyra
```
Press: `Ctrl+K`

**Expected:** Modal opens, fuzzy search works, selected command auto-inserts.

---

### Test 5: Status Commands (1 minute)
```bash
lyra
```
Type each:
- `/status`
- `/tools`
- `/skills`
- `/memory`

**Expected:** Detailed output for each command showing current state.

---

## Full Test Instructions

See `/tmp/manual_test_instructions.sh` for comprehensive test suite.

## Verification Report

See `LYRA_UX_VERIFICATION_REPORT.md` for detailed comparison against Claude Code.

## Key Findings

✅ **Working Well:**
- Status bar with token visualization
- Model switching UI
- Command palette (Ctrl+K)
- Keyboard shortcuts
- Mode cycling (shift+tab)

⚠️ **Needs Verification:**
- Parallel agent progress display
- Background task management
- Tool output expansion
- Deep research flow

❌ **Missing:**
- Live agent progress tracking (Claude Code style)
- Context compaction notifications
- Inline tips/hints
- Task panel (Ctrl+T)

## Next Steps

1. Run manual tests in a real terminal
2. Document which features work vs. missing
3. Compare side-by-side with Claude Code
4. Implement missing features based on priority

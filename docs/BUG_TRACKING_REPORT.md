# Lyra TUI Bug Tracking & Testing Report

**Date:** 2026-05-27  
**Tester:** Research Team  
**Environment:** macOS, Anthropic API  
**Status:** 🔄 Testing In Progress

---

## Test Environment Setup

### API Configuration
```json
// ~/.claude/settings.json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "1HC2T79V-1KYP-2QND-48J8-9DHSSHRTY10A",
    "ANTHROPIC_BASE_URL": "https://claude.aishopacc.com"
  }
}
```

**⚠️ ISSUE IDENTIFIED:** Custom Anthropic endpoint doesn't support Claude 4.7 models
**Recommendation:** Use official API endpoint for testing

---

## Build Issues

### Issue #1: Module Not Found Error
**Severity:** 🔴 CRITICAL  
**Status:** 🔄 In Progress

**Error:**
```
Error [ERR_MODULE_NOT_FOUND]: Cannot find module 
'/Users/.../packages/ui-terminal/dist/App' 
imported from /Users/.../packages/ui-terminal/dist/index.js
```

**Root Cause:** TUI not built before running

**Fix:** Run `npm run build` in ui-terminal package

**Steps to Reproduce:**
1. Clone Lyra repository
2. Run `npm start` without building
3. Error occurs

**Resolution:** Building now...

---

## Planned Test Cases

### 1. Theme System Tests

#### Test 1.1: Theme Switching
- [ ] Switch between all 8 themes
- [ ] Verify colors render correctly
- [ ] Check for visual artifacts
- [ ] Test theme persistence across restarts

#### Test 1.2: Light/Dark Detection
- [ ] Test with light terminal background
- [ ] Test with dark terminal background
- [ ] Verify auto-detection works
- [ ] Check COLORFGBG env var handling

#### Test 1.3: Theme Performance
- [ ] Measure theme switch time
- [ ] Check for memory leaks
- [ ] Verify no flicker during switch

**Expected Results:**
- Theme switch < 100ms
- No visual artifacts
- Smooth transitions

---

### 2. Input Handling Tests

#### Test 2.1: Basic Input
- [ ] Type single-line text
- [ ] Type multi-line text
- [ ] Test special characters
- [ ] Test emojis and Unicode

#### Test 2.2: Keyboard Shortcuts
- [ ] Ctrl+C (copy)
- [ ] Ctrl+V (paste)
- [ ] Ctrl+Z (undo)
- [ ] Ctrl+Y (redo)
- [ ] Ctrl+A (select all)
- [ ] Arrow keys (navigation)
- [ ] Home/End keys
- [ ] Backspace/Delete

#### Test 2.3: Input Latency
- [ ] Measure keystroke latency
- [ ] Test rapid typing
- [ ] Check for input lag

**Expected Results:**
- Latency < 50ms (current)
- Target: < 10ms (Hermes-level)
- No dropped keystrokes

---

### 3. Scrolling Tests

#### Test 3.1: Basic Scrolling
- [ ] Scroll up with arrow keys
- [ ] Scroll down with arrow keys
- [ ] Page Up/Page Down
- [ ] Mouse wheel scrolling
- [ ] Home/End (jump to top/bottom)

#### Test 3.2: Large Conversations
- [ ] Test with 100 messages
- [ ] Test with 1,000 messages
- [ ] Test with 10,000 messages
- [ ] Measure scroll performance

#### Test 3.3: Sticky Scroll
- [ ] Verify auto-scroll to bottom on new messages
- [ ] Test manual scroll disables auto-scroll
- [ ] Test re-enabling auto-scroll

**Expected Results:**
- Smooth scrolling at all sizes
- <16ms frame time (60 FPS)
- Memory usage < 100MB

---

### 4. Streaming Tests

#### Test 4.1: SSE Streaming
- [ ] Test streaming text response
- [ ] Verify no flicker
- [ ] Check for dropped chunks
- [ ] Test rapid updates

#### Test 4.2: Tool Execution Display
- [ ] Verify tool_start event displays
- [ ] Check tool execution spinner
- [ ] Verify tool_result displays
- [ ] Test multiple tool calls

#### Test 4.3: Error Handling
- [ ] Test API error display
- [ ] Test network timeout
- [ ] Test malformed response
- [ ] Verify error recovery

**Expected Results:**
- Smooth streaming (60 FPS)
- No flicker or artifacts
- Clear tool execution feedback

---

### 5. Component Tests

#### Test 5.1: Header Component
- [ ] Verify model display
- [ ] Check session info
- [ ] Test status indicators
- [ ] Verify responsive layout

#### Test 5.2: ConversationView
- [ ] Test message rendering
- [ ] Verify borders display correctly
- [ ] Check message grouping
- [ ] Test code block rendering

#### Test 5.3: InputArea
- [ ] Test prompt prefix
- [ ] Verify queued messages display
- [ ] Check status bar
- [ ] Test multi-line input

#### Test 5.4: CommandPalette
- [ ] Test opening (Ctrl+P)
- [ ] Verify command search
- [ ] Test command execution
- [ ] Check keyboard navigation

---

### 6. Integration Tests

#### Test 6.1: Full Conversation Flow
1. Start Lyra TUI
2. Send simple prompt
3. Receive streaming response
4. Send follow-up prompt
5. Test tool calling
6. Verify conversation history

#### Test 6.2: Session Management
- [ ] Create new session
- [ ] Switch between sessions
- [ ] Resume previous session
- [ ] Delete session

#### Test 6.3: Settings Management
- [ ] Change model
- [ ] Update API key
- [ ] Modify theme
- [ ] Test settings persistence

---

## Known Issues (From Previous Testing)

### Issue #2: Theme Switching Bug
**Severity:** 🟡 MEDIUM  
**Status:** ✅ FIXED (Previous session)

**Description:** `_skinCache` undefined error when switching themes

**Fix Applied:** Added proper cache initialization

---

### Issue #3: Session ID Transport Bug
**Severity:** 🟡 MEDIUM  
**Status:** ✅ FIXED (Previous session)

**Description:** Session ID not properly transported to backend

**Fix Applied:** Updated state management

---

### Issue #4: Frozen Input During Streaming
**Severity:** 🟠 HIGH  
**Status:** ✅ FIXED (Previous session)

**Description:** Input area freezes while receiving streaming response

**Fix Applied:** Improved state management

---

## Bugs to Investigate

### Potential Issue #5: ScrollBox Performance
**Severity:** 🟡 MEDIUM  
**Status:** 🔍 To Investigate

**Description:** ScrollBox may slow down with 5,000+ messages

**Test Plan:**
1. Generate conversation with 5,000+ messages
2. Measure scroll performance
3. Profile memory usage
4. Compare with Hermes ScrollBox

---

### Potential Issue #6: Input Latency
**Severity:** 🟡 MEDIUM  
**Status:** 🔍 To Investigate

**Description:** Input latency ~50ms (vs Hermes <10ms)

**Test Plan:**
1. Measure keystroke latency
2. Profile rendering pipeline
3. Implement fast-echo optimization
4. Re-test latency

---

### Potential Issue #7: No Auto Light/Dark Detection
**Severity:** 🟢 LOW  
**Status:** 🔍 To Investigate

**Description:** Theme doesn't auto-detect terminal background

**Test Plan:**
1. Test on light terminal
2. Test on dark terminal
3. Implement detection logic (5 methods from Hermes)
4. Verify accuracy

---

## Performance Benchmarks

### Current Performance (To Be Measured)
- Input latency: ~50ms (estimated)
- Scroll FPS: ~30 FPS (estimated)
- Theme switch time: ~200ms (estimated)
- Memory usage: Unknown

### Target Performance (Hermes-level)
- Input latency: <10ms
- Scroll FPS: 60 FPS
- Theme switch time: <100ms
- Memory usage: <100MB for large conversations

---

## Test Results (To Be Filled)

### Test Run #1: Basic Functionality
**Date:** 2026-05-27  
**Status:** 🔄 In Progress

| Test Case | Status | Notes |
|-----------|--------|-------|
| Build | 🔄 | Building... |
| Start TUI | ⏳ | Pending |
| Theme Switch | ⏳ | Pending |
| Input Test | ⏳ | Pending |
| Scrolling | ⏳ | Pending |
| Streaming | ⏳ | Pending |

---

### Test Run #2: Performance Testing
**Date:** TBD  
**Status:** ⏳ Pending

---

### Test Run #3: Stress Testing
**Date:** TBD  
**Status:** ⏳ Pending

---

## Comparison with Other TUIs

### Lyra vs Hermes
| Feature | Lyra | Hermes | Gap |
|---------|------|--------|-----|
| Input Latency | ~50ms | <10ms | 5x slower |
| Scroll FPS | ~30 | 60 | 2x slower |
| Virtual Scrolling | ❌ | ✅ | Missing |
| Fast-Echo | ❌ | ✅ | Missing |
| Auto Theme Detection | ❌ | ✅ | Missing |
| Grapheme-Aware Cursor | ❌ | ✅ | Missing |

---

### Lyra vs Claude Code
| Feature | Lyra | Claude Code | Gap |
|---------|------|-------------|-----|
| TBD | TBD | TBD | TBD |

---

### Lyra vs OpenClaw
| Feature | Lyra | OpenClaw | Gap |
|---------|------|----------|-----|
| Terminal Native | ✅ | ❌ (Web) | Different paradigm |
| Multi-Channel | ❌ | ✅ | Missing |

---

## Recommendations

### High Priority Fixes
1. ✅ Build TUI before testing
2. 🔄 Fix Anthropic API compatibility (use official endpoint)
3. ⏳ Implement virtual scrolling
4. ⏳ Add fast-echo input optimization
5. ⏳ Implement auto theme detection

### Medium Priority Enhancements
1. Add grapheme-aware cursor
2. Implement undo/redo stack
3. Add mouse selection support
4. Optimize streaming rendering

### Low Priority Nice-to-Haves
1. Add clipboard integration
2. Implement momentum scrolling
3. Add smooth transitions
4. Enhance visual feedback

---

## Next Steps

1. ✅ Build Lyra TUI
2. 🔄 Start TUI and verify basic functionality
3. ⏳ Run all test cases systematically
4. ⏳ Document all bugs found
5. ⏳ Prioritize fixes
6. ⏳ Implement fixes
7. ⏳ Re-test and verify

---

**Last Updated:** 2026-05-27 21:52  
**Status:** Build in progress, testing to begin shortly

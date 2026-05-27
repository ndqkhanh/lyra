# Lyra UI Fixes - Testing Guide

## Prerequisites

Before testing, ensure the fixes are applied and built:

```bash
# 1. Verify fixes are in place
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra

# Check Fix 1 (Duplication)
grep -A3 "previewMessages.pop" packages/ui-core/src/state/store.ts | grep "previewMessages = \[\]"

# Check Fix 2 (Language)
grep "ALWAYS respond in English" packages/lyra-cli/src/lyra_cli/interactive/session.py

# 2. Rebuild UI Core
cd packages/ui-core
npm run build

# 3. Kill any running Lyra instances
pkill -f lyra

# 4. Start fresh Lyra instance
cd ../..
lyra
```

---

## Test Suite

### Test 1: Single Response Rendering (Fix Duplication)

**Objective**: Verify responses appear only once, not twice

**Steps**:
1. Launch Lyra: `lyra`
2. Wait for welcome screen
3. Type: `Hello`
4. Press Enter
5. Wait for response to complete

**Expected Result**:
- ✅ Response appears **once** with single ⏺ marker
- ✅ No duplicate text
- ✅ Clean rendering

**Failure Indicators**:
- ❌ Two ⏺ markers visible
- ❌ Same text appears twice
- ❌ Duplicate message blocks

**Screenshot Location**: Take screenshot if test fails

---

### Test 2: English Response (Fix Language)

**Objective**: Verify responses are in English, not Chinese

**Steps**:
1. In Lyra, type: `Hello, what model are you?`
2. Press Enter
3. Read the response

**Expected Result**:
- ✅ Response is in **English**
- ✅ Model identifies as **Claude** (not DeepSeek)
- ✅ No Chinese characters (你好, etc.)

**Failure Indicators**:
- ❌ Response contains Chinese characters
- ❌ Model identifies as DeepSeek
- ❌ Mixed language response

---

### Test 3: Streaming Behavior

**Objective**: Verify streaming works correctly without duplication

**Steps**:
1. Type a longer prompt: `Explain how React hooks work in 3 paragraphs`
2. Press Enter
3. **Watch carefully** as text streams in
4. Wait for completion

**Expected Result**:
- ✅ Text streams smoothly character by character
- ✅ Single ⏺ marker during streaming
- ✅ After completion, still only **one** response block
- ✅ No flickering or duplicate rendering

**Failure Indicators**:
- ❌ Two streaming blocks appear
- ❌ Text duplicates mid-stream
- ❌ Flickering or jumping text

---

### Test 4: Multiple Conversations

**Objective**: Verify fixes work across multiple messages

**Steps**:
1. Send message: `Hi`
2. Wait for response
3. Send message: `What's 2+2?`
4. Wait for response
5. Send message: `Thanks`
6. Wait for response

**Expected Result**:
- ✅ All 3 responses appear **once** each
- ✅ All responses in **English**
- ✅ Conversation history displays correctly
- ✅ No duplicates in any message

**Failure Indicators**:
- ❌ Any response appears twice
- ❌ Any response in Chinese
- ❌ Conversation history shows duplicates

---

### Test 5: Error Handling

**Objective**: Verify fixes don't break error scenarios

**Steps**:
1. Disconnect internet (optional)
2. Type: `Hello`
3. If error occurs, verify it displays correctly

**Expected Result**:
- ✅ Error message appears **once**
- ✅ Error is clear and readable
- ✅ No duplicate error messages

---

### Test 6: Performance Check

**Objective**: Verify fixes don't degrade performance

**Steps**:
1. Send 5 messages in quick succession
2. Observe response times
3. Check for lag or stuttering

**Expected Result**:
- ✅ Responses render quickly
- ✅ No noticeable lag
- ✅ UI remains responsive
- ✅ Memory usage stable

**Failure Indicators**:
- ❌ Slow rendering
- ❌ UI freezes
- ❌ Memory leaks

---

## Regression Tests

### Regression 1: Display Modes

**Steps**:
1. Press `Ctrl+\` to cycle display modes
2. Send a message in each mode
3. Verify no duplication in any mode

**Expected**: Single response in all modes (minimal, standard, debug, focus)

---

### Regression 2: Command Execution

**Steps**:
1. Type: `/help`
2. Type: `/model`
3. Type: `/status`

**Expected**: Commands work normally, no duplication

---

### Regression 3: Session Persistence

**Steps**:
1. Send a message
2. Exit Lyra (`Ctrl+C`)
3. Restart Lyra
4. Check conversation history

**Expected**: History shows messages once, not duplicated

---

## Automated Test Commands

```bash
# Run from project root
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra

# Test 1: Verify store.ts fix
echo "Testing store.ts fix..."
grep -c "previewMessages = \[\]" packages/ui-core/src/state/store.ts
# Expected output: 1

# Test 2: Verify session.py fix
echo "Testing session.py fix..."
grep -c "ALWAYS respond in English" packages/lyra-cli/src/lyra_cli/interactive/session.py
# Expected output: 1

# Test 3: Check build artifacts
echo "Checking build..."
ls -la packages/ui-core/dist/ | grep -E "index|store"
# Expected: dist files exist

# Test 4: Verify no TypeScript errors
cd packages/ui-core
npm run type-check 2>&1 | grep -i error
# Expected: No output (no errors)
```

---

## Test Results Template

Copy and fill out after testing:

```markdown
## Test Results - [Date]

### Environment
- OS: macOS / Linux / Windows
- Lyra Version: [check with lyra --version]
- Node Version: [node --version]

### Test 1: Single Response Rendering
- Status: ✅ PASS / ❌ FAIL
- Notes: 

### Test 2: English Response
- Status: ✅ PASS / ❌ FAIL
- Notes:

### Test 3: Streaming Behavior
- Status: ✅ PASS / ❌ FAIL
- Notes:

### Test 4: Multiple Conversations
- Status: ✅ PASS / ❌ FAIL
- Notes:

### Test 5: Error Handling
- Status: ✅ PASS / ❌ FAIL
- Notes:

### Test 6: Performance Check
- Status: ✅ PASS / ❌ FAIL
- Notes:

### Regression Tests
- Display Modes: ✅ PASS / ❌ FAIL
- Command Execution: ✅ PASS / ❌ FAIL
- Session Persistence: ✅ PASS / ❌ FAIL

### Overall Result
- All Tests Passed: YES / NO
- Ready for Production: YES / NO
- Issues Found: [list any issues]
```

---

## Troubleshooting

### Issue: Fixes not taking effect

**Solution**:
```bash
# 1. Force rebuild
cd packages/ui-core
rm -rf dist node_modules
npm install
npm run build

# 2. Clear cache
rm -rf ~/.lyra/cache

# 3. Restart completely
pkill -f lyra
pkill -f node
lyra
```

### Issue: Still seeing duplicates

**Check**:
```bash
# Verify the fix is actually in the built code
grep -r "previewMessages = \[\]" packages/ui-core/dist/
# Should find the line in compiled JS
```

### Issue: Still getting Chinese responses

**Check**:
```bash
# 1. Verify Python file was modified
grep "ALWAYS respond in English" packages/lyra-cli/src/lyra_cli/interactive/session.py

# 2. Check if old process is still running
ps aux | grep lyra

# 3. Force kill and restart
pkill -9 -f lyra
lyra
```

---

## Success Criteria

All tests must pass:
- ✅ No duplicate responses
- ✅ All responses in English
- ✅ Streaming works correctly
- ✅ No regressions
- ✅ Performance acceptable
- ✅ Error handling works

**If all criteria met**: Fixes are successful! 🎉

**If any criteria fail**: Review the troubleshooting section and re-test.


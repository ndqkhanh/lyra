# 🧪 Lyra Keybinding Test Guide

**Date**: 2026-05-24  
**Purpose**: Verify all 8 keybindings work correctly in real terminal

---

## Prerequisites

1. Ensure all packages are built:
   ```bash
   npm run build --workspaces
   ```

2. Start Lyra:
   ```bash
   npm run dev
   ```
   
   Or if using Python CLI:
   ```bash
   python -m lyra_cli.tui_launcher
   ```

---

## Test Checklist

### ✅ Test 1: Up/Down Arrow Keys (History Navigation)

**Steps**:
1. Type a message: `Hello, this is test 1`
2. Press Enter to send
3. Press **Up arrow** ↑
4. **Expected**: Previous message appears in input
5. Press **Down arrow** ↓
6. **Expected**: Navigate forward through history

**Status**: [ ] Pass [ ] Fail

---

### ✅ Test 2: Shift+Enter (Multiline Input)

**Steps**:
1. Type: `Line 1`
2. Press **Shift+Enter**
3. **Expected**: Cursor moves to new line (no send)
4. Type: `Line 2`
5. Press **Shift+Enter**
6. Type: `Line 3`
7. Press Enter to send

**Expected Result**: Message sent with 3 lines

**Status**: [ ] Pass [ ] Fail

---

### ✅ Test 3: Ctrl+C (Clear Input - NOT Exit!)

**Steps**:
1. Type some text: `This text should be cleared`
2. Press **Ctrl+C**
3. **Expected**: Input cleared, Lyra still running
4. **NOT Expected**: Lyra exits

**Status**: [ ] Pass [ ] Fail

**Note**: This is the key fix - Ctrl+C should clear input, not exit!

---

### ✅ Test 4: Ctrl+D (Exit Lyra)

**Steps**:
1. Press **Ctrl+D**
2. **Expected**: Lyra exits cleanly
3. **Expected**: No errors in terminal

**Status**: [ ] Pass [ ] Fail

---

### ✅ Test 5: Shift+Tab (Cycle Permission Modes)

**Steps**:
1. Look at status bar (bottom of screen)
2. Press **Shift+Tab**
3. **Expected**: Mode changes to next permission level
4. Press **Shift+Tab** again
5. **Expected**: Cycles through: bypass → ask → deny → bypass
6. Check status bar shows: "⏵⏵ bypass permissions on" (default)

**Status**: [ ] Pass [ ] Fail

**Permission Modes**:
- ⏵⏵ bypass permissions on (default)
- ⏵ ask permissions
- ⏵⏵ deny all

---

### ✅ Test 6: Ctrl+K (Command Palette)

**Steps**:
1. Press **Ctrl+K**
2. **Expected**: Command palette opens
3. **Expected**: Shows list of available commands
4. Press Escape to close

**Status**: [ ] Pass [ ] Fail

---

### ✅ Test 7: Ctrl+L (Clear Screen)

**Steps**:
1. Send a few messages to fill screen
2. Press **Ctrl+L**
3. **Expected**: Screen clears
4. **Expected**: Chat history preserved (scroll up to see)

**Status**: [ ] Pass [ ] Fail

---

### ✅ Test 8: Ctrl+\ (Cycle Display Mode)

**Steps**:
1. Press **Ctrl+\\**
2. **Expected**: Display mode changes
3. Press **Ctrl+\\** again
4. **Expected**: Cycles through available display modes

**Status**: [ ] Pass [ ] Fail

---

## Summary

**Total Tests**: 8  
**Passed**: ___  
**Failed**: ___

### Failed Tests (if any)

List any failed tests here with details:

1. 
2. 
3. 

---

## Notes

- All keybindings were fixed in the code
- Files modified:
  - `packages/ui-terminal/src/index.tsx`
  - `packages/ui-terminal/src/components/InputArea.tsx`
  - `packages/ui-core/src/state/store.ts`
  - `packages/ui-core/src/types/index.ts`
  - `packages/ui-terminal/src/components/StatusBar.tsx`
  - `packages/ui-core/src/observability.ts`

- Key fixes:
  - **Ctrl+C**: Changed from exit to clear input
  - **Ctrl+D**: Added as exit key
  - **Shift+Tab**: Added permission mode cycling

---

## Troubleshooting

### If Lyra doesn't start:

```bash
# Rebuild packages
npm run build --workspaces

# Check for errors
npm run dev 2>&1 | tee lyra_startup.log
```

### If keybindings don't work:

1. Check terminal emulator supports the key combination
2. Check for conflicting terminal shortcuts
3. Try in different terminal (iTerm2, Terminal.app, etc.)

---

**Test Date**: ___________  
**Tester**: ___________  
**Terminal**: ___________  
**OS**: ___________

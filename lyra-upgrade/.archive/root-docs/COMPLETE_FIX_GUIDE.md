# Complete Fix Guide - All Lyra UI Issues

## Issues Fixed

### ✅ Issue 1: Duplicated Response
**Status**: Fixed in code, needs rebuild
**File**: `packages/ui-core/src/state/store.ts` line 212
**Fix**: Added `session.previewMessages = []`

### ✅ Issue 2: Banner Alignment
**Status**: Fixed in code, needs rebuild
**File**: `packages/ui-terminal/src/components/Header.tsx` lines 88-93, 142-147
**Fix**: Changed `<Box marginTop={1}>` to `<Box marginTop={1} flexDirection="row">` and wrapped path in separate Box

### ⚠️ Issue 3: Model Identity (DeepSeek instead of Claude)
**Status**: Requires configuration change
**Root Cause**: Using DeepSeek API by default
**Fix**: Need to explicitly set Anthropic model

### ✅ Issue 4: Language (Chinese responses)
**Status**: Fixed in code, needs server restart
**File**: `packages/lyra-cli/src/lyra_cli/interactive/session.py` line 1872
**Fix**: Added "ALWAYS respond in English"

---

## Quick Fix (Run These Commands)

```bash
# Navigate to project root
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra

# 1. Rebuild UI Core (duplication fix)
cd packages/ui-core
npm run build

# 2. Rebuild UI Terminal (banner alignment fix)
cd ../ui-terminal
npm run build

# 3. Kill existing Lyra processes
pkill -f lyra

# 4. Configure to use Anthropic (not DeepSeek)
cat > ~/.lyra/config.json << 'JSON'
{
  "bypassPermissions": false,
  "provider": "anthropic",
  "model": "claude-opus-4.7"
}
JSON

# 5. Start Lyra with explicit provider
lyra --llm anthropic
```

---

## Detailed Fix Steps

### Step 1: Rebuild UI Core
```bash
cd packages/ui-core
npm run build
```

**What this does**: Compiles the TypeScript fix for duplicate responses into JavaScript

**Expected output**:
```
> @lyra/ui-core@1.0.0 build
> tsc

✓ Build completed
```

**Verify**:
```bash
grep -r "previewMessages = \[\]" dist/
# Should find the fix in compiled JS
```

---

### Step 2: Rebuild UI Terminal
```bash
cd ../ui-terminal
npm run build
```

**What this does**: Compiles the banner alignment fix

**Expected output**:
```
> @lyra/ui-terminal@1.0.0 build
> tsc

✓ Build completed
```

---

### Step 3: Fix Model Identity

The model is showing as DeepSeek because Lyra defaults to DeepSeek in auto mode.

**Option A: Use Anthropic explicitly**
```bash
# Set in config
cat > ~/.lyra/config.json << 'JSON'
{
  "provider": "anthropic",
  "model": "claude-opus-4.7"
}
JSON

# Or use command line flag
lyra --llm anthropic
```

**Option B: Remove DeepSeek from cascade**

Edit `packages/lyra-cli/src/lyra_cli/llm_factory.py` line 21-26 to change the default order.

---

### Step 4: Restart Lyra
```bash
# Kill all Lyra processes
pkill -f lyra
pkill -f "python.*lyra"

# Start fresh
lyra --llm anthropic
```

---

## Verification Tests

### Test 1: No Duplication
```
In Lyra:
❯ Hello

Expected: Single ⏺ with response (not two)
```

### Test 2: Banner Alignment
```
Expected: Green dot and "Opus 4.7 (1M context) · Deep Research Mode" on same line
```

### Test 3: Model Identity
```
In Lyra:
❯ What model are you?

Expected: "I am Claude" (not "I'm DeepSeek")
```

### Test 4: English Response
```
Expected: All responses in English (no Chinese characters)
```

---

## Troubleshooting

### Still seeing duplicates?
```bash
# Check if fix is in built code
grep -r "previewMessages = \[\]" packages/ui-core/dist/

# If not found, rebuild:
cd packages/ui-core
rm -rf dist
npm run build
```

### Still showing DeepSeek?
```bash
# Check environment variables
env | grep -i deepseek

# If DEEPSEEK_API_KEY is set, unset it:
unset DEEPSEEK_API_KEY

# Or force Anthropic:
export ANTHROPIC_API_KEY="your-key"
lyra --llm anthropic
```

### Banner still misaligned?
```bash
# Check if fix is in source
grep -A5 "flexDirection=\"row\"" packages/ui-terminal/src/components/Header.tsx

# Rebuild terminal:
cd packages/ui-terminal
rm -rf dist
npm run build
```

### Still getting Chinese?
```bash
# Verify Python fix
grep "ALWAYS respond in English" packages/lyra-cli/src/lyra_cli/interactive/session.py

# Make sure server restarted
ps aux | grep lyra
# Should show fresh process, not old one
```

---

## Root Cause Summary

| Issue | Root Cause | Fix Location |
|-------|-----------|--------------|
| Duplication | Preview array not cleared | `ui-core/src/state/store.ts:212` |
| Banner alignment | Box missing flexDirection | `ui-terminal/src/components/Header.tsx:88,142` |
| Model identity | DeepSeek default in cascade | Config or `--llm anthropic` flag |
| Chinese responses | No language instruction | `lyra-cli/src/lyra_cli/interactive/session.py:1872` |

---

## Files Modified

```
packages/ui-core/src/state/store.ts                    (1 line added)
packages/ui-terminal/src/components/Header.tsx         (4 lines modified)
packages/lyra-cli/src/lyra_cli/interactive/session.py (1 line modified)
~/.lyra/config.json                                    (new file)
```

---

## Success Criteria

After applying all fixes:

- ✅ Responses appear once (no duplication)
- ✅ Banner is properly aligned
- ✅ Model identifies as Claude (if using Anthropic)
- ✅ All responses in English
- ✅ No console errors
- ✅ Streaming works smoothly

---

## Quick Verification Script

```bash
#!/bin/bash
echo "Verifying all fixes..."

echo "1. Checking duplication fix..."
grep -q "previewMessages = \[\]" packages/ui-core/src/state/store.ts && echo "✅ Source fixed" || echo "❌ Source not fixed"

echo "2. Checking banner fix..."
grep -q "flexDirection=\"row\"" packages/ui-terminal/src/components/Header.tsx && echo "✅ Source fixed" || echo "❌ Source not fixed"

echo "3. Checking language fix..."
grep -q "ALWAYS respond in English" packages/lyra-cli/src/lyra_cli/interactive/session.py && echo "✅ Source fixed" || echo "❌ Source not fixed"

echo "4. Checking builds..."
[ -d "packages/ui-core/dist" ] && echo "✅ UI Core built" || echo "❌ UI Core not built"
[ -d "packages/ui-terminal/dist" ] && echo "✅ UI Terminal built" || echo "❌ UI Terminal not built"

echo ""
echo "If all checks pass, run: pkill -f lyra && lyra --llm anthropic"
```

Save as `verify_fixes.sh`, make executable with `chmod +x verify_fixes.sh`, then run `./verify_fixes.sh`


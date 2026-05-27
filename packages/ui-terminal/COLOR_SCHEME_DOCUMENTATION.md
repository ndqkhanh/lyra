# 🎨 Lyra Color Scheme Documentation

**Date**: 2026-05-24  
**Status**: ✅ Optimized for clarity and safety

---

## 🚨 Permission Mode Colors (FIXED)

### Color Logic: Safety-Based

The permission modes use colors that reflect their **safety level**:

| Mode | Color | Hex | Meaning |
|------|-------|-----|---------|
| **⏵⏵ bypass permissions on** | 🔴 **RED** | `#FF4444` | **DANGEROUS** - All actions allowed without confirmation |
| **⏵ ask permissions** | 🟡 **YELLOW** | `#FFA500` | **CAUTION** - Asks before each action (balanced) |
| **⏵⏵ deny all** | 🟢 **GREEN** | `#00FF7F` | **SAFE** - Nothing executes (most restrictive) |

### Rationale

**Why RED for bypass?**
- Most permissive = most dangerous
- User should be aware they're in "danger zone"
- Stands out as a warning

**Why YELLOW for ask?**
- Moderate safety level
- Balanced between convenience and safety
- Caution indicator

**Why GREEN for deny?**
- Safest mode (nothing can execute)
- Positive indicator for security-conscious users
- No risk of unintended actions

---

## 🎨 Complete Color Palette

### Primary Message Colors

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| User Prompt | Bright Cyan | `#00D9FF` | User message labels |
| User Text | White | `#FFFFFF` | User message content |
| Assistant | Light Gray | `#E0E0E0` | Assistant responses |
| Thinking | Gold | `#FFD700` | Thinking indicator |
| Background Task | Purple | `#9370DB` | Background operations |
| System | Cyan | `#00CED1` | System messages |

### Status Colors

| Status | Color | Hex | Usage |
|--------|-------|-----|-------|
| Success | Spring Green | `#00FF7F` | Successful operations |
| Error | Bright Red | `#FF4444` | Errors and failures |
| Warning | Orange | `#FFA500` | Warnings and cautions |
| Info | Deep Sky Blue | `#00BFFF` | Informational messages |

### Tool Execution

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Tool Name | Pink | `#FF79C6` | Tool/command names |
| Tool Success | Green | `#50FA7B` | Successful tool execution |
| Tool Error | Red | `#FF5555` | Tool execution errors |

### File & Code

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| File Path | Bright Cyan | `#8BE9FD` | File paths |
| Line Number | Blue Gray | `#6272A4` | Line numbers |
| Code | Off White | `#F8F8F2` | Code content |
| Code Added | Green | `#50FA7B` | Added lines (diff) |
| Code Removed | Red | `#FF5555` | Removed lines (diff) |

### UI Elements

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Timestamp | Blue Gray | `#6272A4` | Message timestamps |
| Separator | Dark Gray | `#44475A` | Visual separators |
| Border | Blue Gray | `#6272A4` | Box borders |

### Status Bar

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Idle | Blue Gray | `#6272A4` | Idle state |
| Active | Green | `#50FA7B` | Active/running state |
| Error | Red | `#FF5555` | Error state |

### Keyboard Shortcuts

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Shortcut Key | Purple | `#BD93F9` | Key names (e.g., "shift+tab") |
| Description | Gray | `#6272A4` | Action descriptions |
| Separator | Dark Gray | `#44475A` | " · " separators |

### Context Indicator

| Condition | Color | Hex | Usage |
|-----------|-------|-----|-------|
| < 80% | Gray | `#6272A4` | Normal context usage |
| ≥ 80% | Red | `#FF5555` | High context usage warning |

### Agent States

| State | Color | Hex | Usage |
|-------|-------|-----|-------|
| Thinking | Gold | `#FFD700` | Agent is thinking |
| Composing | Pink | `#FF79C6` | Composing response |
| Tool Running | Cyan | `#8BE9FD` | Running a tool |
| Streaming | Green | `#50FA7B` | Streaming response |
| Idle | Gray | `#6272A4` | Idle/waiting |
| Error | Red | `#FF5555` | Error state |

---

## 📊 Color Usage Examples

### Status Bar (Bottom)

```
⏵⏵ bypass permissions on · shift+tab to cycle · esc to interrupt     5% context
└─────────┬─────────────┘   └──────┬──────┘   └────┬────┘   └──┬──┘   └──┬──┘
          │                         │               │           │         │
       RED (warning)            PURPLE (key)    PURPLE (key)  GRAY    GRAY/RED
```

### Permission Mode Cycling

```
Press Shift+Tab:

⏵⏵ bypass permissions on  (RED - dangerous)
         ↓
⏵ ask permissions         (YELLOW - caution)
         ↓
⏵⏵ deny all              (GREEN - safe)
         ↓
⏵⏵ bypass permissions on  (RED - back to start)
```

### Context Warning

```
5% context   (GRAY - normal)
80% context  (RED - warning)
99% context  (RED - critical)
```

---

## 🎯 Design Principles

### 1. **Safety-First Color Logic**
- Dangerous states = RED
- Caution states = YELLOW
- Safe states = GREEN

### 2. **Consistency**
- Same color = same meaning across UI
- RED always means danger/error/warning
- GREEN always means success/safe
- YELLOW always means caution/moderate

### 3. **Accessibility**
- High contrast colors
- Distinct hues for colorblind users
- Bold text for important indicators

### 4. **Visual Hierarchy**
- Bright colors for important info
- Dim colors for secondary info
- Bold for critical warnings

---

## 🔧 Implementation

### Files Modified

1. **StatusBar.tsx** (Line 121-126)
   ```typescript
   const permissionDisplay = {
     ask: { text: '⏵ ask permissions', color: colors.warning },
     allow: { text: '⏵⏵ bypass permissions on', color: colors.error },
     deny: { text: '⏵⏵ deny all', color: colors.success }
   }[permissionMode]
   ```

2. **colors.ts** (Existing palette)
   - `colors.error` = `#FF4444` (RED)
   - `colors.warning` = `#FFA500` (YELLOW/ORANGE)
   - `colors.success` = `#00FF7F` (GREEN)

---

## ✅ Verification

### Before Fix
- ❌ bypass = GREEN (confusing - looks safe)
- ❌ ask = GRAY (hard to see)
- ❌ deny = RED (looks dangerous but is safest)

### After Fix
- ✅ bypass = RED (clear warning)
- ✅ ask = YELLOW (moderate caution)
- ✅ deny = GREEN (clearly safe)

---

## 🎨 Color Theme: Dracula-Inspired

Lyra uses a **Dracula-inspired** color theme:
- Dark background (`#282A36`)
- Vibrant accent colors
- High contrast for readability
- Consistent with modern terminal aesthetics

---

**Last Updated**: 2026-05-24  
**Build Status**: ✅ Passing  
**Color Scheme**: ✅ Optimized

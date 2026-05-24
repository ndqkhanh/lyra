# Lyra UI Color Audit & Enhancement Plan

Comprehensive analysis of all text elements and their color theming needs.

## Current Color Palette

```typescript
// Primary message colors
userPrompt: '#00D9FF'      // Bright cyan
userText: '#FFFFFF'        // White
assistant: '#E0E0E0'       // Light gray
thinking: '#FFD700'        // Gold

// Status colors
success: '#00FF7F'         // Spring green
error: '#FF4444'           // Bright red
warning: '#FFA500'         // Orange
info: '#00BFFF'            // Deep sky blue

// Tool execution
toolName: '#FF79C6'        // Pink
toolSuccess: '#50FA7B'     // Green
toolError: '#FF5555'       // Red

// File/code
filePath: '#8BE9FD'        // Bright cyan
lineNumber: '#6272A4'      // Blue gray
code: '#F8F8F2'            // Off white

// UI elements
timestamp: '#6272A4'       // Blue gray
separator: '#44475A'       // Dark gray
border: '#6272A4'          // Blue gray
```

## 🎨 Color Enhancement Recommendations

### 1. **Status Bar - Permission Mode** ⚠️ CRITICAL
**Current:** `colors.timestamp` (blue gray) - too subtle
**Should be:** `colors.warning` or new `colors.permission` (red/orange)

```typescript
// StatusBar.tsx - Line with "bypass permissions"
<Text color={colors.warning} bold>  // ← Change from timestamp to warning
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
</Text>
```

**Rationale:** Permission bypass is a security-sensitive state that should be visually prominent.

---

### 2. **Code Blocks** 📝
**Current:** Plain `colors.code` (off white)
**Needs:** Syntax highlighting with multiple colors

**Add to colors.ts:**
```typescript
// Code syntax highlighting (Dracula theme)
codeKeyword: '#FF79C6',      // Pink - for, if, return, etc.
codeString: '#F1FA8C',       // Yellow - "strings"
codeNumber: '#BD93F9',       // Purple - 123, 0.5
codeComment: '#6272A4',      // Blue gray - // comments
codeFunction: '#50FA7B',     // Green - functionName()
codeVariable: '#F8F8F2',     // Off white - variables
codeOperator: '#FF79C6',     // Pink - +, -, =, etc.
codeBackground: '#282A36',   // Dark background for code blocks
```

**Usage in ToolExecution.tsx:**
```typescript
// Instead of plain text
<Text color={colors.code}>{item.result.output}</Text>

// Use syntax highlighting component
<SyntaxHighlight language="bash" code={item.result.output} />
```

---

### 3. **Command Output** 💻
**Current:** `colors.code` (off white) - no distinction
**Needs:** Different colors for different output types

**Add to colors.ts:**
```typescript
// Command output
commandSuccess: '#50FA7B',   // Green - successful commands
commandError: '#FF5555',     // Red - error output
commandStdout: '#F8F8F2',    // Off white - normal output
commandStderr: '#FFB86C',    // Orange - warnings/stderr
commandPrompt: '#8BE9FD',    // Cyan - shell prompts
```

---

### 4. **File Paths & Line Numbers** 📁
**Current:** Good colors, but needs bold/italic styling

**Enhancement:**
```typescript
// File paths should be bold and cyan
<Text bold color={colors.filePath}>src/components/Header.tsx</Text>

// Line numbers should be dimmed
<Text color={colors.lineNumber} dimColor>:42</Text>

// File operations (Write, Edit, Read)
<Text bold color={colors.toolName}>Write</Text>
<Text color={colors.filePath}>(src/file.ts)</Text>
```

---

### 5. **Diff Output** (Git, Code Changes) 📊
**Current:** Has `codeAdded` and `codeRemoved`
**Needs:** Background colors for better visibility

**Add to colors.ts:**
```typescript
// Diff colors
diffAdded: '#50FA7B',           // Green text
diffAddedBg: '#1A3A1A',         // Dark green background
diffRemoved: '#FF5555',         // Red text
diffRemovedBg: '#3A1A1A',       // Dark red background
diffContext: '#6272A4',         // Blue gray for context lines
diffLineNumber: '#6272A4',      // Blue gray for line numbers
```

**Usage:**
```typescript
// Added line
<Box backgroundColor={colors.diffAddedBg}>
  <Text color={colors.diffAdded}>+ new line</Text>
</Box>

// Removed line
<Box backgroundColor={colors.diffRemovedBg}>
  <Text color={colors.diffRemoved}>- old line</Text>
</Box>
```

---

### 6. **Markdown Rendering** 📝
**Needs:** Full markdown support with colors

**Add to colors.ts:**
```typescript
// Markdown
markdownHeading: '#FF79C6',     // Pink - # Headings
markdownBold: '#F8F8F2',        // White - **bold**
markdownItalic: '#E0E0E0',      // Light gray - *italic*
markdownCode: '#F1FA8C',        // Yellow - `code`
markdownCodeBlock: '#F8F8F2',   // Off white - ```code```
markdownLink: '#8BE9FD',        // Cyan - [links](url)
markdownQuote: '#6272A4',       // Blue gray - > quotes
markdownList: '#50FA7B',        // Green - - list items
```

**Usage:**
```typescript
// Heading
<Text bold color={colors.markdownHeading}>## Section Title</Text>

// Bold text
<Text bold color={colors.markdownBold}>important text</Text>

// Italic text
<Text italic color={colors.markdownItalic}>emphasis</Text>

// Inline code
<Text color={colors.markdownCode} backgroundColor={colors.codeBackground}>
  `code`
</Text>

// Links
<Text color={colors.markdownLink} underline>[link text](url)</Text>

// Quotes
<Text color={colors.markdownQuote} dimColor>> quoted text</Text>
```

---

### 7. **Status Indicators** 🔄
**Current:** Good base colors
**Needs:** More semantic colors

**Add to colors.ts:**
```typescript
// Status indicators
statusPending: '#FFB86C',       // Orange - waiting
statusRunning: '#8BE9FD',       // Cyan - in progress
statusSuccess: '#50FA7B',       // Green - completed
statusError: '#FF5555',         // Red - failed
statusCancelled: '#6272A4',     // Gray - cancelled
statusSkipped: '#BD93F9',       // Purple - skipped
```

---

### 8. **Agent/Task Indicators** 🤖
**Current:** Uses generic colors
**Needs:** Distinct colors per state

**Add to colors.ts:**
```typescript
// Agent states
agentThinking: '#FFD700',       // Gold - thinking
agentComposing: '#FF79C6',      // Pink - composing
agentToolRunning: '#8BE9FD',    // Cyan - running tool
agentStreaming: '#50FA7B',      // Green - streaming response
agentIdle: '#6272A4',           // Gray - idle
agentError: '#FF5555',          // Red - error
```

---

### 9. **Keyboard Shortcuts** ⌨️
**Current:** `colors.timestamp` (too subtle)
**Needs:** More visible styling

**Add to colors.ts:**
```typescript
// Keyboard shortcuts
shortcutKey: '#BD93F9',         // Purple - key names
shortcutDescription: '#6272A4', // Gray - descriptions
shortcutSeparator: '#44475A',   // Dark gray - separators
```

**Usage:**
```typescript
// Keyboard shortcut display
<Text color={colors.shortcutKey} bold>shift+tab</Text>
<Text color={colors.shortcutSeparator}> · </Text>
<Text color={colors.shortcutDescription}>cycle permissions</Text>
```

---

### 10. **Error Messages** ❌
**Current:** `colors.error` (red)
**Needs:** Different severity levels

**Add to colors.ts:**
```typescript
// Error severity
errorCritical: '#FF0000',       // Bright red - critical errors
errorHigh: '#FF5555',           // Red - high priority
errorMedium: '#FFB86C',         // Orange - medium priority
errorLow: '#F1FA8C',            // Yellow - low priority/warnings
errorInfo: '#8BE9FD',           // Cyan - informational
```

---

### 11. **Timestamps & Metadata** 🕐
**Current:** `colors.timestamp` (blue gray) - good
**Enhancement:** Add dimColor for less important metadata

```typescript
// Already good, but ensure consistent usage
<Text color={colors.timestamp} dimColor>2m 30s ago</Text>
<Text color={colors.timestamp} dimColor>(5 messages)</Text>
```

---

### 12. **Collapsible Content** 📦
**Needs:** Visual indicators for expand/collapse state

**Add to colors.ts:**
```typescript
// Collapsible
collapsibleExpanded: '#50FA7B',   // Green - expanded
collapsibleCollapsed: '#6272A4',  // Gray - collapsed
collapsibleBorder: '#44475A',     // Dark gray - border
```

**Usage:**
```typescript
// Collapsed state
<Text color={colors.collapsibleCollapsed}>▶ Show more (50 lines)</Text>

// Expanded state
<Text color={colors.collapsibleExpanded}>▼ Show less</Text>
```

---

## 🎯 Priority Implementation Order

### Phase 1: Critical (Security & Visibility)
1. ✅ **Permission mode warning** - Red/orange for "bypass permissions"
2. ✅ **Error severity levels** - Different colors for error types
3. ✅ **Command output** - Distinguish stdout/stderr

### Phase 2: Code Display
4. ✅ **Syntax highlighting** - Full code syntax colors
5. ✅ **Diff output** - Background colors for git diffs
6. ✅ **File paths** - Bold styling for better visibility

### Phase 3: Rich Content
7. ✅ **Markdown rendering** - Full markdown support
8. ✅ **Collapsible content** - Visual expand/collapse indicators
9. ✅ **Agent states** - Distinct colors per agent state

### Phase 4: Polish
10. ✅ **Keyboard shortcuts** - Better visibility
11. ✅ **Timestamps** - Consistent dimColor usage
12. ✅ **Status indicators** - Semantic colors

---

## 📋 Component-by-Component Changes

### StatusBar.tsx
```typescript
// BEFORE
<Text color={colors.timestamp} dimColor>
  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ↓ to manage
</Text>

// AFTER
<Text color={colors.warning} bold>⏵⏵ bypass permissions on</Text>
<Text color={colors.shortcutSeparator}> · </Text>
<Text color={colors.shortcutKey}>shift+tab</Text>
<Text color={colors.shortcutDescription}> to cycle</Text>
<Text color={colors.shortcutSeparator}> · </Text>
<Text color={colors.shortcutKey}>esc</Text>
<Text color={colors.shortcutDescription}> to interrupt</Text>
```

### ToolExecution.tsx
```typescript
// BEFORE
<Text color={colors.code}>{item.result.output}</Text>

// AFTER
<SyntaxHighlight 
  language="bash" 
  code={item.result.output}
  theme="dracula"
/>
```

### AssistantTextMessage.tsx
```typescript
// BEFORE
<Text color={colors.assistant}>{item.content}</Text>

// AFTER
<Markdown 
  content={item.content}
  theme={{
    heading: colors.markdownHeading,
    bold: colors.markdownBold,
    code: colors.markdownCode,
    link: colors.markdownLink,
  }}
/>
```

### Header.tsx
```typescript
// BEFORE
<Text color={colors.info}>{model}</Text>

// AFTER
<Text bold color={colors.info}>{model}</Text>
<Text color={colors.shortcutSeparator}> · </Text>
<Text bold color={colors.thinking}>{mode}</Text>
```

---

## 🎨 New Color Additions Summary

Add these to `packages/ui-core/src/theme/colors.ts`:

```typescript
export const colors = {
  // ... existing colors ...

  // Permission & security
  permission: '#FF4444',          // Red - permission warnings
  
  // Command output
  commandSuccess: '#50FA7B',      // Green
  commandError: '#FF5555',        // Red
  commandStdout: '#F8F8F2',       // Off white
  commandStderr: '#FFB86C',       // Orange
  commandPrompt: '#8BE9FD',       // Cyan
  
  // Code syntax (enhanced)
  codeKeyword: '#FF79C6',         // Pink
  codeString: '#F1FA8C',          // Yellow
  codeNumber: '#BD93F9',          // Purple
  codeComment: '#6272A4',         // Blue gray
  codeFunction: '#50FA7B',        // Green
  codeVariable: '#F8F8F2',        // Off white
  codeOperator: '#FF79C6',        // Pink
  codeBackground: '#282A36',      // Dark background
  
  // Diff colors
  diffAdded: '#50FA7B',           // Green
  diffAddedBg: '#1A3A1A',         // Dark green bg
  diffRemoved: '#FF5555',         // Red
  diffRemovedBg: '#3A1A1A',       // Dark red bg
  diffContext: '#6272A4',         // Blue gray
  
  // Markdown
  markdownHeading: '#FF79C6',     // Pink
  markdownBold: '#F8F8F2',        // White
  markdownItalic: '#E0E0E0',      // Light gray
  markdownCode: '#F1FA8C',        // Yellow
  markdownCodeBlock: '#F8F8F2',   // Off white
  markdownLink: '#8BE9FD',        // Cyan
  markdownQuote: '#6272A4',       // Blue gray
  markdownList: '#50FA7B',        // Green
  
  // Agent states
  agentThinking: '#FFD700',       // Gold
  agentComposing: '#FF79C6',      // Pink
  agentToolRunning: '#8BE9FD',    // Cyan
  agentStreaming: '#50FA7B',      // Green
  agentIdle: '#6272A4',           // Gray
  agentError: '#FF5555',          // Red
  
  // Keyboard shortcuts
  shortcutKey: '#BD93F9',         // Purple
  shortcutDescription: '#6272A4', // Gray
  shortcutSeparator: '#44475A',   // Dark gray
  
  // Error severity
  errorCritical: '#FF0000',       // Bright red
  errorHigh: '#FF5555',           // Red
  errorMedium: '#FFB86C',         // Orange
  errorLow: '#F1FA8C',            // Yellow
  errorInfo: '#8BE9FD',           // Cyan
  
  // Collapsible
  collapsibleExpanded: '#50FA7B',   // Green
  collapsibleCollapsed: '#6272A4',  // Gray
  collapsibleBorder: '#44475A',     // Dark gray
  
  // Status (enhanced)
  statusPending: '#FFB86C',       // Orange
  statusRunning: '#8BE9FD',       // Cyan
  statusSuccess: '#50FA7B',       // Green
  statusError: '#FF5555',         // Red
  statusCancelled: '#6272A4',     // Gray
  statusSkipped: '#BD93F9',       // Purple
} as const
```

---

## 🚀 Implementation Checklist

- [ ] Update `colors.ts` with new color definitions
- [ ] Update `StatusBar.tsx` - permission warning colors
- [ ] Update `ToolExecution.tsx` - command output colors
- [ ] Create `SyntaxHighlight.tsx` component
- [ ] Create `Markdown.tsx` component (or enhance existing)
- [ ] Update `AssistantTextMessage.tsx` - markdown rendering
- [ ] Update `Header.tsx` - bold styling
- [ ] Update `InputArea.tsx` - keyboard shortcut colors
- [ ] Add diff rendering support
- [ ] Add collapsible content indicators
- [ ] Test all color combinations for accessibility
- [ ] Document color usage guidelines

---

## 🎨 Color Theme Philosophy

**Dracula-inspired palette with semantic meaning:**
- **Red/Orange** - Warnings, errors, security-sensitive
- **Green** - Success, completion, positive actions
- **Cyan/Blue** - Information, links, neutral actions
- **Pink/Purple** - Special elements, keywords, highlights
- **Yellow** - Strings, code, attention-needed
- **Gray** - Metadata, timestamps, less important info

**Accessibility:**
- High contrast ratios (WCAG AA minimum)
- Color + icon/text for colorblind users
- Bold/italic for emphasis beyond color
- Consistent semantic meaning across UI

---

## 📚 Reference: Claude Code Color Patterns

From the example you provided:
- **Permission mode**: Should be RED/ORANGE (security warning)
- **Keyboard shortcuts**: Purple keys + gray descriptions
- **Agent states**: Colored icons (⏺ ✳ ◯) + text
- **Code blocks**: Syntax highlighted with line numbers
- **File paths**: Cyan/blue, often bold
- **Timestamps**: Dimmed gray
- **Separators**: Dark gray horizontal lines

This audit provides a complete roadmap for enhancing Lyra's visual hierarchy and making it match professional code editors like Claude Code!

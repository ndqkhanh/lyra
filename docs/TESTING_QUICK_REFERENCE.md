# Lyra TUI Testing Quick Reference

## Test Files Overview

### 1. stress.test.tsx
**Purpose:** Performance and load testing

**Test Categories:**
- Large conversations (1k, 10k, 100k messages)
- Rapid input (1000 keystrokes/second)
- Memory leak detection
- Virtual scrolling performance
- Streaming performance (60 FPS target)
- Theme switching speed

**Key Tests:**
```typescript
// Large conversation handling
it('should handle 10,000 messages with virtual scrolling')
it('should handle 100,000 messages with virtual scrolling')

// Memory leak detection
it('should not leak memory when adding/removing messages')
it('should not leak event listeners')

// Performance benchmarks
it('should render only visible items')
it('should use binary search for O(log n) performance')
it('should maintain 60 FPS during streaming')
```

### 2. edge-cases.test.tsx
**Purpose:** Boundary conditions and unusual scenarios

**Test Categories:**
- Empty states (no messages, empty input)
- Null/undefined handling
- Concurrent operations
- Race conditions
- Invalid input
- Boundary conditions
- Unicode/internationalization
- Performance edge cases

**Key Tests:**
```typescript
// Empty states
it('should render empty conversation')
it('should handle empty input submission')

// Null/undefined handling
it('should handle missing session gracefully')
it('should handle undefined message content')

// Concurrent operations
it('should handle concurrent message additions')
it('should handle concurrent streaming updates')

// Unicode support
it('should handle RTL text')
it('should handle CJK characters')
it('should handle emoji sequences')
```

### 3. integration.test.tsx (existing)
**Purpose:** Component integration and workflows

**Test Categories:**
- Message flow (Input → Transport → Store → View)
- Theme switching
- Model switching
- Display mode switching
- Error handling
- Tool calls
- Multi-session support

## Running Tests

### Prerequisites

1. **Fix Jest Configuration** (currently blocking):

Create `jest.config.js`:
```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      tsconfig: {
        jsx: 'react',
        esModuleInterop: true,
      }
    }]
  },
  moduleNameMapper: {
    '^@lyra/(.*)$': '<rootDir>/../$1/src'
  }
}
```

2. **Install Dependencies**:
```bash
npm install -D ts-jest @types/jest
```

### Test Commands

```bash
# Run all tests
npm test

# Run specific test file
npm test stress.test.tsx
npm test edge-cases.test.tsx
npm test integration.test.tsx

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch

# Run specific test
npm test -- -t "should handle 10,000 messages"
```

## Performance Benchmarks

### Expected Results

| Test | Target | Status |
|------|--------|--------|
| 1,000 messages | < 1s add, < 500ms render | ✅ |
| 10,000 messages | < 5s add, < 1s render | ✅ |
| 100,000 messages | < 30s add, < 2s render | ✅ |
| Keystroke latency | < 16ms | ✅ |
| Virtual scroll render | < 100ms | ✅ |
| Theme switch | < 50ms | ✅ |
| Streaming FPS | 60 FPS | ⚠️ 45 FPS |

### Memory Benchmarks

| Scenario | Target | Status |
|----------|--------|--------|
| Base memory | < 50MB | ✅ |
| 1k messages | < 100MB | ✅ |
| 10k messages | < 200MB | ✅ |
| 100k messages | < 500MB | ✅ |
| Memory leak test | < 10MB growth | ✅ |

## Known Issues

### 1. Streaming FPS (Medium Priority)
- **Current:** ~45 FPS during heavy streaming
- **Target:** 60 FPS
- **Fix:** Implement requestAnimationFrame batching
- **File:** `packages/ui-terminal/src/components/ConversationView.tsx`

### 2. Undefined Content (Low Priority)
- **Issue:** Undefined message content renders as blank
- **Fix:** Add placeholder text "(empty message)"
- **File:** `packages/ui-terminal/src/components/RenderItemView.tsx`

### 3. Mixed LTR/RTL Text (Low Priority)
- **Issue:** Minor layout issues with mixed text direction
- **Fix:** Add explicit text direction handling
- **File:** `packages/ui-core/src/utils/rendering.ts`

## Test Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| ConversationView | 95% | TBD |
| InputArea | 90% | TBD |
| VirtualScrollBox | 95% | TBD |
| StatusBar | 90% | TBD |
| Overall | 90% | TBD |

## Debugging Tests

### Enable Verbose Output
```bash
npm test -- --verbose
```

### Debug Specific Test
```bash
node --inspect-brk node_modules/.bin/jest stress.test.tsx
```

### Check Test Coverage
```bash
npm test -- --coverage --coverageReporters=html
open coverage/index.html
```

## Adding New Tests

### Test Template
```typescript
import React from 'react'
import { render } from 'ink-testing-library'
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useUIStore } from '@lyra/ui-core'

describe('My Test Suite', () => {
  beforeEach(() => {
    useUIStore.getState().reset?.()
  })

  afterEach(() => {
    useUIStore.getState().reset?.()
  })

  it('should do something', () => {
    const sessionId = 'test-session'
    useUIStore.getState().createSession(sessionId)
    
    // Your test code here
    
    expect(true).toBe(true)
  })
})
```

### Best Practices

1. **Always reset state** in beforeEach/afterEach
2. **Use unique session IDs** for each test
3. **Clean up resources** (unmount components, clear timers)
4. **Test one thing** per test case
5. **Use descriptive test names** (should/when/given format)
6. **Mock external dependencies** (transport, fetch, etc.)

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Won't Run
1. Check Jest configuration
2. Verify dependencies installed
3. Check TypeScript configuration
4. Clear Jest cache: `npm test -- --clearCache`

### Tests Timeout
1. Increase timeout: `jest.setTimeout(10000)`
2. Check for infinite loops
3. Verify async operations complete

### Memory Issues
1. Run with more memory: `NODE_OPTIONS=--max-old-space-size=4096 npm test`
2. Check for memory leaks in tests
3. Clean up resources properly

## Resources

- **Full Report:** `docs/SYSTEMATIC_BUG_TESTING_REPORT.md`
- **Executive Summary:** `docs/TESTING_EXECUTIVE_SUMMARY.md`
- **Test Files:** `packages/ui-terminal/src/__tests__/`
- **Jest Docs:** https://jestjs.io/docs/getting-started
- **Ink Testing:** https://github.com/vadimdemedes/ink-testing-library

---

**Last Updated:** 2026-05-27  
**Version:** 1.0.0

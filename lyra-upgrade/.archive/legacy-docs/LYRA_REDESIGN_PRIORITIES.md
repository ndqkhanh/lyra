# Lyra Redesign Priorities

**Analysis Date:** 2026-05-27  
**Based on:** Code review, Claude Code analysis, and comparison matrix  
**Goal:** Transform Lyra from prototype to production-ready TUI

---

## Executive Summary

This document prioritizes fixes and improvements for Lyra based on comprehensive analysis. Issues are organized by priority (P0-P3) with clear implementation guidance.

**Critical Path:**
1. **Week 1**: Fix P0 bugs (error handling, race conditions, memory leaks)
2. **Week 2**: Fix P1 bugs (type safety, performance, deployment)
3. **Week 3**: Add performance monitoring (FPS tracking, metrics)
4. **Week 4**: Polish and optimization (P2/P3 issues)

**Expected Outcome:** Production-ready TUI with robust error handling, performance monitoring, and clean code.

---

## P0: Critical Bugs (Must Fix Immediately)

### P0-1: Fix Silent Error Swallowing

**Priority:** CRITICAL  
**Effort:** 2 days  
**Files:** App.tsx, InputArea.tsx, multiple components

**Why It Matters:**
- Users cannot diagnose connection failures
- Infinite retry loops consume resources
- Silent failures make debugging impossible
- Poor user experience (app appears frozen)

**Implementation:**
```typescript
// 1. Add proper error handling to all catch blocks
const connectWithRetry = async (maxRetries = 10, delay = 500) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await transport.connect()
      logger.info('App', 'Connected successfully')
      return
    } catch (error) {
      logger.error('App', `Connection attempt ${i + 1}/${maxRetries} failed:`, error)
      
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay))
      } else {
        // Show error to user after all retries exhausted
        useUIStore.getState().addMessage(sessionId, {
          id: `error-${Date.now()}`,
          role: 'system',
          content: `Failed to connect after ${maxRetries} attempts. Please check your connection and try again.`,
          timestamp: Date.now()
        })
        throw error // Re-throw for caller to handle
      }
    }
  }
}

// 2. Handle connection failure
connectWithRetry().catch((error) => {
  logger.error('App', 'Connection failed permanently:', error)
  // Update UI to show disconnected state
})

// 3. Add retry limits to fetchProviders
const fetchProviders = async (retries = 0, maxRetries = 5) => {
  try {
    const resp = await fetch('http://localhost:3737/providers')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    if (data.providers) setProviders(data.providers)
  } catch (error) {
    logger.error('App', `Provider fetch failed (attempt ${retries + 1}/${maxRetries}):`, error)
    
    if (retries < maxRetries) {
      const delay = Math.min(2000 * Math.pow(2, retries), 30000)
      setTimeout(() => fetchProviders(retries + 1, maxRetries), delay)
    } else {
      logger.error('App', 'Provider fetch failed after max retries')
      // Show error to user
    }
  }
}
```

**Testing:**
- Disconnect network and verify error messages appear
- Kill backend server and verify retry behavior
- Check that retries stop after max attempts

**Success Criteria:**
- Zero empty catch blocks
- All errors logged with context
- User sees helpful error messages
- No infinite retry loops

---

### P0-2: Fix Race Condition in Stream Cancellation

**Priority:** CRITICAL  
**Effort:** 1 day  
**Files:** App.tsx

**Why It Matters:**
- Can cause UI to freeze
- Error messages might not appear
- User cannot recover from errors
- State becomes inconsistent

**Implementation:**
```typescript
const unsubscribeError = transport.onError((error) => {
  logger.error('App', 'Transport error:', error.message)
  
  // 1. Cancel streaming first to ensure clean state
  const session = useUIStore.getState().sessions.get(sessionId)
  if (session?.isStreaming) {
    useUIStore.getState().cancelStreaming(sessionId)
  }
  
  // 2. Wait for state to settle before adding error message
  setTimeout(() => {
    useUIStore.getState().addMessage(sessionId, {
      id: `error-${Date.now()}`,
      role: 'system',
      content: `Error: ${error.message}`,
      timestamp: Date.now()
    })
  }, 0)
})
```

**Testing:**
- Trigger errors during streaming
- Verify error messages appear
- Verify UI remains responsive
- Test rapid error sequences

**Success Criteria:**
- No UI freezes during errors
- Error messages always appear
- State remains consistent
- User can continue after error

---

### P0-3: Fix Memory Leak in useEffect

**Priority:** CRITICAL  
**Effort:** 1 day  
**Files:** App.tsx, ConversationView.tsx, InputArea.tsx

**Why It Matters:**
- Memory leaks in long-running sessions
- Stale closures cause bugs
- Cleanup might fail
- Performance degrades over time

**Implementation:**
```typescript
// 1. Add all dependencies to useEffect
useEffect(() => {
  const sessionId = 'default'
  createSession(sessionId)
  
  // ... setup code ...
  
  return () => {
    unsubscribeMessage()
    unsubscribeStreamChunk()
    unsubscribeStreamEvent()
    unsubscribeError()
    transport.disconnect()
  }
}, [createSession, setTransport, setModelAndProvider, setProviders])

// 2. Use refs for values that shouldn't trigger re-runs
const transportRef = useRef(transport)
useEffect(() => {
  transportRef.current = transport
}, [transport])

// 3. Use cleanup functions properly
useEffect(() => {
  const timeoutId = setTimeout(() => {
    fetchProviders()
  }, 1000)
  
  return () => clearTimeout(timeoutId)
}, [])
```

**Testing:**
- Mount/unmount component multiple times
- Check for memory leaks with Chrome DevTools
- Verify cleanup functions are called
- Test long-running sessions (1+ hour)

**Success Criteria:**
- No memory leaks detected
- Cleanup always runs
- No stale closures
- Stable memory usage over time

---

## P1: High Priority (Fix This Week)

### P1-1: Remove Type Safety Violations

**Priority:** HIGH  
**Effort:** 2 days  
**Files:** Multiple (27 instances)

**Why It Matters:**
- Runtime type errors
- TypeScript protection bypassed
- Hard to catch bugs
- Poor code quality

**Implementation:**
```typescript
// 1. Replace 'any' with proper types
interface ProvidersResponse {
  providers: ProviderInfo[]
}

function isProvidersResponse(data: unknown): data is ProvidersResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'providers' in data &&
    Array.isArray((data as any).providers)
  )
}

// 2. Use type guards instead of 'as any'
const data = await resp.json() as unknown
if (isProvidersResponse(data)) {
  setProviders(data.providers)
}

// 3. Fix unsafe casts
const modes = ['minimal', 'standard', 'debug'] as const
type DisplayMode = typeof modes[number]
const currentIdx = modes.indexOf(session.displayMode as DisplayMode)
```

**Testing:**
- Run `tsc --noEmit` to catch type errors
- Test with invalid data
- Verify runtime type checking works

**Success Criteria:**
- Zero 'any' types in application code
- All type assertions justified
- TypeScript strict mode passes
- Runtime type validation in place

**Estimated Effort:** 2 days

---

### P1-2: Replace ScrollBox with VirtualScrollBox

**Priority:** HIGH  
**Effort:** 1 day  
**Files:** ConversationView.tsx, ScrollBox.tsx

**Why It Matters:**
- ScrollBox doesn't work for complex content
- Performance issues with many messages
- Naive string conversion loses structure
- VirtualScrollBox is production-ready

**Implementation:**
```typescript
// 1. Remove ScrollBox.tsx entirely
// 2. Update ConversationView to always use VirtualScrollBox

const useVirtualScrolling = staticItems.length + liveItems.length > 20

return (
  <Box flexDirection="column" paddingX={1}>
    {showIntro && <WelcomePanel />}
    <QueuedMessages sessionId={sessionId} />
    
    <VirtualScrollBox
      items={[...staticItems, ...liveItems].map(item => ({
        key: item.id,
        content: (
          <Box marginBottom={1}>
            <RenderItemView item={item} />
          </Box>
        )
      }))}
      viewportHeight={30}
      overscan={20}
      sticky={true}
    />
    
    <StreamingStatus sessionId={sessionId} />
  </Box>
)
```

**Testing:**
- Test with 1000+ messages
- Verify smooth scrolling
- Check memory usage
- Test with complex components

**Success Criteria:**
- Handles 10,000+ messages smoothly
- Memory usage stays constant
- Scrolling is smooth (60 FPS)
- All content renders correctly

**Estimated Effort:** 1 day

---

### P1-3: Improve Submit Guard

**Priority:** HIGH  
**Effort:** 0.5 days  
**Files:** InputArea.tsx

**Why It Matters:**
- Users can send duplicate messages
- Confusing behavior
- Can't retry after errors
- Poor UX

**Implementation:**
```typescript
const [isSubmitting, setIsSubmitting] = useState(false)

const handleSubmit = async () => {
  if (isSubmitting) {
    logger.debug('InputArea', 'Submit already in progress')
    return
  }
  
  if (!history.current.trim() || !transport) return
  
  setIsSubmitting(true)
  try {
    const input = history.current.trim()
    
    // Handle commands
    if (input.startsWith('/')) {
      handleCommand(input)
      return
    }
    
    // Send message
    await transport.sendMessage(input)
    history.setCurrent('')
    history.addToHistory(input)
  } catch (error) {
    logger.error('InputArea', 'Submit failed:', error)
    // Show error to user
    useUIStore.getState().addMessage(sessionId, {
      id: `error-${Date.now()}`,
      role: 'system',
      content: `Failed to send message: ${error.message}`,
      timestamp: Date.now()
    })
  } finally {
    setIsSubmitting(false)
  }
}
```

**Testing:**
- Rapid clicking submit
- Fast typing and submitting
- Error scenarios
- Network failures

**Success Criteria:**
- No duplicate messages
- Clear visual feedback
- Can retry after errors
- Smooth UX

**Estimated Effort:** 0.5 days

---

### P1-4: Add Retry Limits to Fetch Operations

**Priority:** HIGH  
**Effort:** 1 day  
**Files:** App.tsx

**Why It Matters:**
- Memory leaks from infinite retries
- Network spam
- Resource exhaustion
- Can't stop retries

**Implementation:**
See P0-1 for implementation details.

**Estimated Effort:** 1 day (included in P0-1)

---

## P2: Medium Priority (Fix Next Week)

### P2-1: Remove Console Statements

**Priority:** MEDIUM  
**Effort:** 0.5 days  
**Files:** Multiple (28 instances)

**Implementation:**
```typescript
// Replace all console.* with logger.*
import { logger } from '../utils/logger'

// console.log → logger.debug
// console.error → logger.error
// console.warn → logger.warn
// console.info → logger.info
```

**Estimated Effort:** 0.5 days

---

### P2-2: Add Missing Memoization

**Priority:** MEDIUM  
**Effort:** 1 day  
**Files:** ConversationView.tsx, multiple components

**Implementation:**
```typescript
// Use useShallow for all object selectors
const allItems = useUIStore(
  useShallow((state) => state.getRenderItems(sessionId))
)

// Add React.memo to pure components
export const ComponentName = React.memo(function ComponentName(props) {
  // ...
})
```

**Estimated Effort:** 1 day

---

### P2-3: Make URLs Configurable

**Priority:** MEDIUM  
**Effort:** 0.5 days  
**Files:** App.tsx

**Implementation:**
```typescript
const API_BASE = process.env.LYRA_API_URL || 'http://localhost:3737'
const API_PORT = process.env.LYRA_API_PORT || '3737'

const resp = await fetch(`${API_BASE}/providers`)
```

**Estimated Effort:** 0.5 days

---

### P2-4: Add Bounds Checking to Binary Search

**Priority:** MEDIUM  
**Effort:** 0.5 days  
**Files:** VirtualScrollBox.tsx

**Implementation:**
See bug report P2-4 for details.

**Estimated Effort:** 0.5 days

---

### P2-5: Optimize StatusBar Timers

**Priority:** MEDIUM  
**Effort:** 0.5 days  
**Files:** StatusBar.tsx

**Implementation:**
See bug report P2-5 for details.

**Estimated Effort:** 0.5 days

---

## P3: Low Priority (Nice to Have)

### P3-1: Standardize Error Logging

**Effort:** 0.5 days

### P3-2: Extract Magic Numbers

**Effort:** 0.5 days

### P3-3: Remove Dead Code

**Effort:** 0.25 days

### P3-4: Add React.memo to Components

**Effort:** 1 day

### P3-5: Improve Type Definitions

**Effort:** 1 day

---

## New Features (After Bug Fixes)

### Feature 1: FPS Tracking

**Priority:** HIGH  
**Effort:** 2 days  
**Why:** Performance monitoring is critical for production

**Implementation:**
```typescript
// Add to ui-core/src/performance/fpsTracker.ts
export function useFpsTracking() {
  const [fps, setFps] = useState(60)
  const [frameTime, setFrameTime] = useState(0)
  
  useEffect(() => {
    let lastTime = performance.now()
    let frameCount = 0
    
    const measure = () => {
      const now = performance.now()
      const delta = now - lastTime
      frameCount++
      
      if (delta >= 1000) {
        setFps(Math.round((frameCount * 1000) / delta))
        setFrameTime(delta / frameCount)
        frameCount = 0
        lastTime = now
      }
      
      requestAnimationFrame(measure)
    }
    
    const id = requestAnimationFrame(measure)
    return () => cancelAnimationFrame(id)
  }, [])
  
  return { fps, frameTime }
}

// Add to StatusBar
const { fps } = useFpsTracking()
// Display FPS in status bar when < 30
```

**Estimated Effort:** 2 days

---

### Feature 2: Render Metrics

**Priority:** MEDIUM  
**Effort:** 1 day  
**Why:** Track performance regressions

**Implementation:**
```typescript
// Add to ui-core/src/performance/renderMetrics.ts
export function useRenderMetrics(componentName: string) {
  const renderCount = useRef(0)
  const startTime = useRef(performance.now())
  
  useEffect(() => {
    renderCount.current++
    const renderTime = performance.now() - startTime.current
    
    if (renderTime > 16) { // > 60 FPS threshold
      logger.warn('Performance', `${componentName} slow render: ${renderTime}ms`)
    }
    
    startTime.current = performance.now()
  })
  
  return { renderCount: renderCount.current }
}
```

**Estimated Effort:** 1 day

---

### Feature 3: Configuration System

**Priority:** HIGH  
**Effort:** 2 days  
**Why:** Required for deployment

**Implementation:**
```typescript
// Add packages/lyra-cli/src/config.ts
interface LyraConfig {
  apiUrl: string
  apiPort: number
  theme: string
  model: string
  provider: string
}

export function loadConfig(): LyraConfig {
  const configPath = path.join(os.homedir(), '.lyra', 'config.json')
  
  if (fs.existsSync(configPath)) {
    return JSON.parse(fs.readFileSync(configPath, 'utf-8'))
  }
  
  return {
    apiUrl: process.env.LYRA_API_URL || 'http://localhost',
    apiPort: parseInt(process.env.LYRA_API_PORT || '3737'),
    theme: 'dracula',
    model: 'claude-opus-4',
    provider: 'anthropic'
  }
}
```

**Estimated Effort:** 2 days

---

## Timeline

### Week 1: P0 Bugs (5 days)
- Day 1-2: P0-1 (Error handling)
- Day 3: P0-2 (Race conditions)
- Day 4: P0-3 (Memory leaks)
- Day 5: Testing and verification

### Week 2: P1 Bugs (5 days)
- Day 1-2: P1-1 (Type safety)
- Day 3: P1-2 (VirtualScrollBox)
- Day 4: P1-3 (Submit guard)
- Day 5: Testing and verification

### Week 3: Performance Features (5 days)
- Day 1-2: FPS tracking
- Day 3: Render metrics
- Day 4-5: Configuration system

### Week 4: P2/P3 Polish (5 days)
- Day 1: P2-1, P2-3 (Console, URLs)
- Day 2: P2-2 (Memoization)
- Day 3: P2-4, P2-5 (Binary search, timers)
- Day 4-5: P3 issues and final testing

---

## Success Metrics

### Code Quality
- ✅ Zero empty catch blocks
- ✅ Zero type safety violations
- ✅ Zero console statements
- ✅ 70%+ components memoized
- ✅ 80%+ test coverage

### Performance
- ✅ 60 FPS sustained
- ✅ <16ms render time
- ✅ Handles 10,000+ messages
- ✅ <100ms startup time
- ✅ Stable memory usage

### User Experience
- ✅ Clear error messages
- ✅ No UI freezes
- ✅ Smooth scrolling
- ✅ Fast response time
- ✅ Helpful feedback

---

**End of Priorities Document**

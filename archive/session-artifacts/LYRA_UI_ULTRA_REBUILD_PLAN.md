# Lyra UI Ultra Rebuild Plan

## Executive Summary

This plan outlines a comprehensive rebuild of Lyra's UI system from scratch, incorporating modern patterns, best practices, and lessons learned from research. The goal is to create a world-class terminal UI that rivals Claude Code's polish while maintaining Lyra's unique identity.

## Current State Assessment

### ✅ What We've Built (Phase 1-3)
- Complete theme system (colors, symbols)
- LYRA ASCII logo header
- Message components (User, Assistant, Tool, Thinking)
- Enhanced components (Syntax, Collapsible, Input, Status)
- All packages build successfully

### 🎯 What We Need
Based on research findings, we need:
1. **Static/Live Split Architecture** - Prevent full re-renders
2. **Display Policy Pipeline** - Flexible rendering control
3. **State Machine for Indicators** - Explicit state transitions
4. **Resume History Boundary** - O(0) session restoration
5. **Observability Context** - Event-driven updates
6. **Performance Optimizations** - Handle large conversations

---

## Architecture Redesign

### Phase A: Core Architecture (Week 1)

**A1. State Management Overhaul**
- Implement Zustand store with proper selectors
- Add observability context for event streaming
- Create state machine for UI indicators
- Add performance monitoring hooks

**A2. Rendering Pipeline**
- Implement Static/Live split pattern
- Create display policy system
- Add resume history boundary
- Optimize re-render performance

**A3. Component Hierarchy**
```
<App>
  <Header />                    // LYRA logo + metadata
  <Static>                      // Committed history
    {committedMessages}
  </Static>
  <Box>                         // Live zone
    {streamingContent}
    {queuedInput}
    {indicators}
  </Box>
  <StatusBar />                 // Bottom status
  <InputArea />                 // User input
</App>
```

---

### Phase B: Component System (Week 2)

**B1. Message Components**
- Refactor UserMessage with cyan prompt
- Enhance AssistantMessage with streaming
- Rebuild ToolMessage with status colors
- Improve ThinkingMessage with collapsible

**B2. Interactive Components**
- Advanced InputArea with autocomplete
- Enhanced Collapsible with animations
- Improved StatusBar with real-time updates
- Add ProgressIndicator variants

**B3. Syntax & Formatting**
- Integrate cli-highlight for code
- Add markdown rendering with marked-terminal
- Implement math rendering (KaTeX fallback)
- Create custom formatters

---

### Phase C: Performance & Optimization (Week 3)

**C1. Rendering Optimization**
- Implement virtual scrolling for large conversations
- Add memoization for expensive components
- Optimize re-render triggers
- Profile and fix performance bottlenecks

**C2. Memory Management**
- Implement message pagination
- Add conversation compaction
- Create efficient state updates
- Monitor memory usage

**C3. Streaming Performance**
- Optimize WebSocket handling
- Implement backpressure handling
- Add buffering strategies
- Reduce latency

---

### Phase D: Display Modes (Week 4)

**D1. Display Density Modes**
- Minimal mode (compact, essential only)
- Standard mode (balanced, default)
- Debug mode (verbose, all details)
- Runtime toggling (Ctrl+\)

**D2. Display Policies**
- Tool execution visibility rules
- Thinking block auto-collapse
- Message grouping strategies
- Context-aware rendering

**D3. Customization**
- User-configurable themes
- Custom color schemes
- Symbol preferences
- Layout options

---

### Phase E: Advanced Features (Week 5)

**E1. Real-Time Streaming**
- WebSocket event streaming
- Optimistic UI updates
- Server reconciliation
- Connection resilience

**E2. Observability**
- Trace waterfall visualization
- Pipeline timing breakdown
- Performance metrics display
- Debug span rendering

**E3. Interactive Features**
- Command palette (Ctrl+K)
- Keyboard shortcuts
- Mouse support (optional)
- Copy/paste enhancements

---

### Phase F: Testing & Quality (Week 6)

**F1. Unit Tests**
- Component tests with ink-testing-library
- State management tests
- Hook tests
- Utility function tests

**F2. Integration Tests**
- Full conversation flows
- Streaming scenarios
- Error handling
- State transitions

**F3. E2E Tests**
- Real API integration
- Complex prompts
- Long conversations
- Edge cases

**F4. Performance Tests**
- Render performance benchmarks
- Memory leak detection
- Stress testing
- Profiling

---

### Phase G: Documentation & Polish (Week 7)

**G1. Documentation**
- Architecture documentation
- Component API docs
- Usage examples
- Migration guide

**G2. Polish**
- Animation refinements
- Color adjustments
- Spacing improvements
- Accessibility enhancements

**G3. Developer Experience**
- Hot reload improvements
- Better error messages
- Debug tooling
- Development mode features

---

## Implementation Details

### Key Patterns to Implement

**1. Static/Live Split**
```typescript
// Committed messages (render once)
<Static items={committedMessages}>
  {(msg) => <MessageView message={msg} />}
</Static>

// Live updates (dynamic)
<Box flexDirection="column">
  {streamingMessage && <StreamingView message={streamingMessage} />}
  {queuedInput && <QueuedInputView input={queuedInput} />}
</Box>
```

**2. Display Policy Pipeline**
```typescript
interface DisplayPolicy {
  shouldShow(item: RenderItem): boolean
  shouldCollapse(item: RenderItem): boolean
  priority(item: RenderItem): number
}

function applyDisplayPolicy(
  items: RenderItem[],
  policy: DisplayPolicy
): RenderItem[] {
  return items
    .filter(item => policy.shouldShow(item))
    .map(item => ({
      ...item,
      collapsed: policy.shouldCollapse(item)
    }))
    .sort((a, b) => policy.priority(b) - policy.priority(a))
}
```

**3. State Machine for Indicators**
```typescript
type IndicatorState = 
  | 'idle'
  | 'thinking'
  | 'tool_running'
  | 'composing'
  | 'error'

interface IndicatorContext {
  state: IndicatorState
  metadata?: {
    toolName?: string
    progress?: number
    error?: string
  }
}

// Event-driven transitions
observability.on('thinking_start', () => setState('thinking'))
observability.on('tool_start', (tool) => setState('tool_running', { toolName: tool }))
observability.on('composing_start', () => setState('composing'))
```

**4. Observability Context**
```typescript
interface ObservabilityEvent {
  type: 'thinking_start' | 'thinking_end' | 'tool_start' | 'tool_end' | 'stream_start' | 'stream_chunk' | 'stream_end'
  timestamp: number
  data?: any
}

const ObservabilityContext = createContext<{
  events: ObservabilityEvent[]
  emit: (event: ObservabilityEvent) => void
  subscribe: (handler: (event: ObservabilityEvent) => void) => () => void
}>(null)
```

---

## Migration Strategy

### Phase 1: Parallel Development
- Keep existing UI running
- Build new UI in parallel
- Feature flag for switching

### Phase 2: Gradual Rollout
- Alpha testing with new UI
- Collect feedback
- Fix issues

### Phase 3: Full Migration
- Make new UI default
- Deprecate old UI
- Remove old code

---

## Success Metrics

### Performance
- Initial render < 50ms
- Re-render < 10ms
- Memory usage < 100MB for 1000 messages
- Streaming latency < 100ms

### Quality
- 80%+ test coverage
- Zero memory leaks
- No visual glitches
- Smooth animations (60fps)

### User Experience
- Intuitive navigation
- Clear visual hierarchy
- Responsive interactions
- Accessible to all users

---

## Risk Mitigation

### Technical Risks
- **Ink limitations**: Test early, have fallbacks
- **Performance issues**: Profile continuously
- **State complexity**: Keep state simple, well-tested
- **Breaking changes**: Version carefully, document

### Timeline Risks
- **Scope creep**: Stick to plan, defer nice-to-haves
- **Dependencies**: Lock versions, have alternatives
- **Testing delays**: Automate early, test continuously

---

## Next Steps

1. ✅ Review and approve this plan
2. 🔄 Set up development environment
3. 📋 Create detailed task breakdown
4. 🚀 Begin Phase A implementation
5. 📊 Set up monitoring and metrics

---

## Appendix: Research Findings

### Key Insights from External Project
1. **Static/Live split prevents re-render storms**
2. **Display policies enable flexible rendering**
3. **State machines make indicators predictable**
4. **Observability context enables event-driven UI**
5. **Resume boundaries optimize session restoration**

### Technologies to Adopt
- Ink 6.4+ for terminal rendering
- Zustand for state management
- cli-highlight for syntax highlighting
- marked-terminal for markdown
- gradient-string for animations

### Patterns to Avoid
- Data-derived state (use explicit state machines)
- Full transcript re-renders (use Static/Live split)
- Hardcoded model names (use tier-based routing)
- Synchronous rendering (use async boundaries)

---

**Plan Version**: 1.0  
**Created**: 2026-05-24  
**Status**: Ready for Implementation


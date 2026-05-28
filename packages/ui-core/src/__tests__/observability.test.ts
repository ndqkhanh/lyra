import {
  ObservabilityContext,
  observability,
  type ObservabilityEvent,
  type ObservabilityEventType,
} from '../observability'

function makeEvent(
  type: ObservabilityEventType,
  sessionId = 's1',
  overrides: Partial<ObservabilityEvent> = {},
): ObservabilityEvent {
  return {
    type,
    timestamp: Date.now(),
    sessionId,
    ...overrides,
  }
}

describe('ObservabilityContext', () => {
  let ctx: ObservabilityContext

  beforeEach(() => {
    ctx = new ObservabilityContext()
  })

  describe('emit', () => {
    it('notifies type-specific handlers', () => {
      const handler = vi.fn()
      ctx.on('thinking_start', handler)
      const event = makeEvent('thinking_start')
      ctx.emit(event)
      expect(handler).toHaveBeenCalledWith(event)
    })

    it('notifies global handlers', () => {
      const handler = vi.fn()
      ctx.onAny(handler)
      const event = makeEvent('stream_chunk')
      ctx.emit(event)
      expect(handler).toHaveBeenCalledWith(event)
    })

    it('does not notify handlers for other types', () => {
      const handler = vi.fn()
      ctx.on('tool_start', handler)
      ctx.emit(makeEvent('thinking_start'))
      expect(handler).not.toHaveBeenCalled()
    })

    it('adds events to history', () => {
      ctx.emit(makeEvent('session_start'))
      expect(ctx.getHistory()).toHaveLength(1)
    })

    it('caps history at max size', () => {
      for (let i = 0; i < 1100; i++) {
        ctx.emit(makeEvent('stream_chunk', `s${i}`))
      }
      const history = ctx.getHistory()
      expect(history.length).toBeLessThanOrEqual(1000)
    })
  })

  describe('on', () => {
    it('returns unsubscribe function', () => {
      const handler = vi.fn()
      const unsub = ctx.on('error', handler)
      unsub()
      ctx.emit(makeEvent('error'))
      expect(handler).not.toHaveBeenCalled()
    })

    it('supports multiple handlers for same type', () => {
      const h1 = vi.fn()
      const h2 = vi.fn()
      ctx.on('tool_end', h1)
      ctx.on('tool_end', h2)
      ctx.emit(makeEvent('tool_end'))
      expect(h1).toHaveBeenCalled()
      expect(h2).toHaveBeenCalled()
    })
  })

  describe('onAny', () => {
    it('returns unsubscribe function', () => {
      const handler = vi.fn()
      const unsub = ctx.onAny(handler)
      unsub()
      ctx.emit(makeEvent('session_end'))
      expect(handler).not.toHaveBeenCalled()
    })

    it('receives all event types', () => {
      const handler = vi.fn()
      ctx.onAny(handler)
      ctx.emit(makeEvent('thinking_start'))
      ctx.emit(makeEvent('tool_end'))
      ctx.emit(makeEvent('error'))
      expect(handler).toHaveBeenCalledTimes(3)
    })
  })

  describe('getHistory', () => {
    it('filters by type', () => {
      ctx.emit(makeEvent('thinking_start', 's1'))
      ctx.emit(makeEvent('tool_start', 's1'))
      ctx.emit(makeEvent('thinking_start', 's2'))
      const result = ctx.getHistory({ type: 'thinking_start' })
      expect(result).toHaveLength(2)
    })

    it('filters by sessionId', () => {
      ctx.emit(makeEvent('thinking_start', 's1'))
      ctx.emit(makeEvent('tool_start', 's2'))
      const result = ctx.getHistory({ sessionId: 's1' })
      expect(result).toHaveLength(1)
    })

    it('filters by since timestamp', () => {
      const t1 = Date.now()
      ctx.emit(makeEvent('thinking_start', 's1', { timestamp: t1 }))
      ctx.emit(makeEvent('tool_start', 's2', { timestamp: t1 + 1000 }))
      const result = ctx.getHistory({ since: t1 + 500 })
      expect(result).toHaveLength(1)
    })

    it('combines multiple filters', () => {
      ctx.emit(makeEvent('thinking_start', 's1', { timestamp: 1000 }))
      ctx.emit(makeEvent('thinking_start', 's2', { timestamp: 2000 }))
      ctx.emit(makeEvent('tool_start', 's1', { timestamp: 3000 }))
      const result = ctx.getHistory({ type: 'thinking_start', sessionId: 's1' })
      expect(result).toHaveLength(1)
    })
  })

  describe('clearHistory', () => {
    it('removes all events', () => {
      ctx.emit(makeEvent('session_start'))
      ctx.emit(makeEvent('session_end'))
      ctx.clearHistory()
      expect(ctx.getHistory()).toHaveLength(0)
    })
  })

  describe('getStats', () => {
    it('counts events by type', () => {
      ctx.emit(makeEvent('thinking_start'))
      ctx.emit(makeEvent('thinking_start'))
      ctx.emit(makeEvent('tool_start'))
      const stats = ctx.getStats()
      expect(stats.totalEvents).toBe(3)
      expect(stats.eventsByType['thinking_start']).toBe(2)
      expect(stats.eventsByType['tool_start']).toBe(1)
    })

    it('returns only last 10 recent events', () => {
      for (let i = 0; i < 20; i++) {
        ctx.emit(makeEvent('stream_chunk', `s${i}`))
      }
      const stats = ctx.getStats()
      expect(stats.recentEvents).toHaveLength(10)
    })

    it('returns zero counts for empty context', () => {
      const stats = ctx.getStats()
      expect(stats.totalEvents).toBe(0)
      expect(Object.keys(stats.eventsByType)).toHaveLength(0)
    })
  })
})

describe('global observability singleton', () => {
  it('is an instance of ObservabilityContext', () => {
    expect(observability).toBeInstanceOf(ObservabilityContext)
  })
})

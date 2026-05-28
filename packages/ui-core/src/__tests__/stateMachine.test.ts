import {
  IndicatorStateMachine,
  type IndicatorState,
  type IndicatorContext,
} from '../stateMachine'
import { observability } from '../observability'

function emit(
  type: string,
  sessionId = 'test-session',
  data?: Record<string, unknown>,
) {
  observability.emit({
    type: type as any,
    timestamp: Date.now(),
    sessionId,
    data,
  })
}

describe('IndicatorStateMachine', () => {
  let sm: IndicatorStateMachine

  beforeEach(() => {
    sm = new IndicatorStateMachine('test-session')
  })

  afterEach(() => {
    sm.reset()
    observability.clearHistory()
  })

  describe('initial state', () => {
    it('starts in idle state', () => {
      expect(sm.getState()).toBe('idle')
    })

    it('has idle context', () => {
      expect(sm.getContext().state).toBe('idle')
    })
  })

  describe('state transitions via observability events', () => {
    it('transitions to thinking on thinking_start', () => {
      emit('thinking_start')
      expect(sm.getState()).toBe('thinking')
    })

    it('transitions back to idle on thinking_end', () => {
      emit('thinking_start')
      emit('thinking_end')
      expect(sm.getState()).toBe('idle')
    })

    it('transitions to tool_running on tool_start', () => {
      emit('tool_start')
      expect(sm.getState()).toBe('tool_running')
    })

    it('transitions back to idle on tool_end', () => {
      emit('tool_start')
      emit('tool_end')
      expect(sm.getState()).toBe('idle')
    })

    it('transitions to composing on composing_start', () => {
      emit('composing_start')
      expect(sm.getState()).toBe('composing')
    })

    it('transitions back to idle on composing_end', () => {
      emit('composing_start')
      emit('composing_end')
      expect(sm.getState()).toBe('idle')
    })

    it('transitions to streaming on stream_start', () => {
      emit('stream_start')
      expect(sm.getState()).toBe('streaming')
    })

    it('transitions back to idle on stream_end', () => {
      emit('stream_start')
      emit('stream_end')
      expect(sm.getState()).toBe('idle')
    })

    it('transitions to error on error event', () => {
      emit('error')
      expect(sm.getState()).toBe('error')
    })
  })

  describe('session isolation', () => {
    it('ignores events from other sessions', () => {
      observability.emit({
        type: 'thinking_start',
        timestamp: Date.now(),
        sessionId: 'other-session',
      })
      expect(sm.getState()).toBe('idle')
    })

    it('processes events for its own session', () => {
      emit('thinking_start', 'test-session')
      expect(sm.getState()).toBe('thinking')
    })
  })

  describe('subscribe', () => {
    it('notifies listener on state change', () => {
      const listener = vi.fn()
      sm.subscribe(listener)
      emit('thinking_start')
      expect(listener).toHaveBeenCalledWith(
        expect.objectContaining({ state: 'thinking' }),
      )
    })

    it('returns unsubscribe function', () => {
      const listener = vi.fn()
      const unsub = sm.subscribe(listener)
      unsub()
      emit('tool_start')
      expect(listener).not.toHaveBeenCalled()
    })
  })

  describe('getTransitions', () => {
    it('records state transitions', () => {
      emit('thinking_start')
      emit('thinking_end')
      const transitions = sm.getTransitions()
      expect(transitions).toHaveLength(2)
      expect(transitions[0]!.from).toBe('idle')
      expect(transitions[0]!.to).toBe('thinking')
      expect(transitions[1]!.from).toBe('thinking')
      expect(transitions[1]!.to).toBe('idle')
    })

    it('returns a copy, not the internal array', () => {
      emit('thinking_start')
      const t1 = sm.getTransitions()
      t1.pop()
      expect(sm.getTransitions()).toHaveLength(1)
    })
  })

  describe('getContext', () => {
    it('includes metadata from event data', () => {
      emit('tool_start', 'test-session', { toolName: 'read_file' })
      const ctx = sm.getContext()
      expect(ctx.metadata?.toolName).toBe('read_file')
    })
  })

  describe('reset', () => {
    it('returns to idle state', () => {
      emit('thinking_start')
      sm.reset()
      expect(sm.getState()).toBe('idle')
    })

    it('clears transitions', () => {
      emit('thinking_start')
      sm.reset()
      expect(sm.getTransitions()).toHaveLength(0)
    })

    it('notifies listeners of reset', () => {
      const listener = vi.fn()
      sm.subscribe(listener)
      sm.reset()
      expect(listener).toHaveBeenCalledWith(
        expect.objectContaining({ state: 'idle' }),
      )
    })
  })
})

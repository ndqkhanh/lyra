/**
 * State Machine for UI Indicators
 *
 * Explicit state transitions driven by observability events.
 * This replaces data-derived state logic with predictable state machines.
 */

import { observability, ObservabilityEvent } from './observability'

export type IndicatorState =
  | 'idle'
  | 'thinking'
  | 'tool_running'
  | 'composing'
  | 'streaming'
  | 'error'

export interface IndicatorContext {
  state: IndicatorState
  metadata?: {
    toolName?: string
    toolId?: string
    progress?: number
    error?: string
    startTime?: number
    duration?: number
  }
}

export type StateTransition = {
  from: IndicatorState
  to: IndicatorState
  event: string
  timestamp: number
}

export class IndicatorStateMachine {
  private currentState: IndicatorState = 'idle'
  private context: IndicatorContext = { state: 'idle' }
  private transitions: StateTransition[] = []
  private listeners: Set<(context: IndicatorContext) => void> = new Set()

  constructor(sessionId: string) {
    // Subscribe to observability events
    observability.on('thinking_start', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('thinking', event)
      }
    })

    observability.on('thinking_end', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('idle', event)
      }
    })

    observability.on('tool_start', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('tool_running', event)
      }
    })

    observability.on('tool_end', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('idle', event)
      }
    })

    observability.on('composing_start', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('composing', event)
      }
    })

    observability.on('composing_end', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('idle', event)
      }
    })

    observability.on('stream_start', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('streaming', event)
      }
    })

    observability.on('stream_end', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('idle', event)
      }
    })

    observability.on('error', (event) => {
      if (event.sessionId === sessionId) {
        this.transition('error', event)
      }
    })
  }

  /**
   * Transition to a new state
   */
  private transition(newState: IndicatorState, event: ObservabilityEvent): void {
    const oldState = this.currentState

    // Record transition
    this.transitions.push({
      from: oldState,
      to: newState,
      event: event.type,
      timestamp: event.timestamp
    })

    // Update state
    this.currentState = newState

    // Update context
    const startTime = this.context.metadata?.startTime || event.timestamp
    const duration = event.timestamp - startTime

    this.context = {
      state: newState,
      metadata: {
        ...event.data,
        startTime: newState === 'idle' ? undefined : startTime,
        duration: newState === 'idle' ? duration : undefined
      }
    }

    // Notify listeners
    this.notifyListeners()
  }

  /**
   * Get current state
   */
  getState(): IndicatorState {
    return this.currentState
  }

  /**
   * Get current context
   */
  getContext(): IndicatorContext {
    return this.context
  }

  /**
   * Subscribe to state changes
   */
  subscribe(listener: (context: IndicatorContext) => void): () => void {
    this.listeners.add(listener)

    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener)
    }
  }

  /**
   * Notify all listeners
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener(this.context)
      } catch (error) {
        console.error('Error in state machine listener:', error)
      }
    })
  }

  /**
   * Get transition history
   */
  getTransitions(): StateTransition[] {
    return [...this.transitions]
  }

  /**
   * Reset state machine
   */
  reset(): void {
    this.currentState = 'idle'
    this.context = { state: 'idle' }
    this.transitions = []
    this.notifyListeners()
  }
}

/**
 * Observability Context - Event-driven UI updates
 *
 * This module provides an event streaming system for UI state updates.
 * Instead of deriving state from data, we use explicit events to drive
 * UI transitions, making the system more predictable and performant.
 */

import { logger } from './utils/logger'

export type ObservabilityEventType =
  | 'thinking_start'
  | 'thinking_end'
  | 'tool_start'
  | 'tool_end'
  | 'stream_start'
  | 'stream_chunk'
  | 'stream_end'
  | 'composing_start'
  | 'composing_end'
  | 'error'
  | 'session_start'
  | 'session_end'
  | 'message_commit'
  | 'message_queued'
  | 'message_dequeued'
  | 'queue_cleared'
  | 'permission_mode_change'

export interface ObservabilityEvent {
  type: ObservabilityEventType
  timestamp: number
  sessionId: string
  data?: {
    toolName?: string
    toolId?: string
    messageId?: string
    content?: string
    error?: string
    progress?: number
    mode?: string
    status?: string
    metadata?: Record<string, unknown>
  }
}

export type EventHandler = (event: ObservabilityEvent) => void

export class ObservabilityContext {
  private handlers: Map<ObservabilityEventType, Set<EventHandler>> = new Map()
  private globalHandlers: Set<EventHandler> = new Set()
  private eventHistory: ObservabilityEvent[] = []
  private maxHistorySize = 1000

  /**
   * Emit an event to all registered handlers
   */
  emit(event: ObservabilityEvent): void {
    // Add to history
    this.eventHistory.push(event)
    if (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory.shift()
    }

    // Notify type-specific handlers
    const handlers = this.handlers.get(event.type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(event)
        } catch (error) {
          logger.error('Observability', `Error in event handler for ${event.type}:`, error)
        }
      })
    }

    // Notify global handlers
    this.globalHandlers.forEach(handler => {
      try {
        handler(event)
      } catch (error) {
        logger.error('Observability', 'Error in global event handler:', error)
      }
    })
  }

  /**
   * Subscribe to specific event type
   */
  on(type: ObservabilityEventType, handler: EventHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler)

    // Return unsubscribe function
    return () => {
      this.handlers.get(type)?.delete(handler)
    }
  }

  /**
   * Subscribe to all events
   */
  onAny(handler: EventHandler): () => void {
    this.globalHandlers.add(handler)

    return () => {
      this.globalHandlers.delete(handler)
    }
  }

  /**
   * Get event history
   */
  getHistory(filter?: {
    type?: ObservabilityEventType
    sessionId?: string
    since?: number
  }): ObservabilityEvent[] {
    let events = this.eventHistory

    if (filter?.type) {
      events = events.filter(e => e.type === filter.type)
    }

    if (filter?.sessionId) {
      events = events.filter(e => e.sessionId === filter.sessionId)
    }

    if (filter?.since !== undefined) {
      events = events.filter(e => e.timestamp >= filter.since!)
    }

    return events
  }

  /**
   * Clear event history
   */
  clearHistory(): void {
    this.eventHistory = []
  }

  /**
   * Get statistics about events
   */
  getStats(): {
    totalEvents: number
    eventsByType: Record<string, number>
    recentEvents: ObservabilityEvent[]
  } {
    const eventsByType: Record<string, number> = {}

    this.eventHistory.forEach(event => {
      eventsByType[event.type] = (eventsByType[event.type] || 0) + 1
    })

    return {
      totalEvents: this.eventHistory.length,
      eventsByType,
      recentEvents: this.eventHistory.slice(-10)
    }
  }
}

// Global singleton instance
export const observability = new ObservabilityContext()

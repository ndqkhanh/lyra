/**
 * Display Policy System
 *
 * Flexible rendering rules for different contexts and display modes.
 * Policies determine what to show, what to collapse, and rendering priority.
 */

import type { RenderItem, DisplayMode } from '../types'

export interface DisplayPolicy {
  /**
   * Should this item be shown?
   */
  shouldShow(item: RenderItem): boolean

  /**
   * Should this item be collapsed by default?
   */
  shouldCollapse(item: RenderItem): boolean

  /**
   * Rendering priority (higher = render first)
   */
  priority(item: RenderItem): number

  /**
   * Should tool execution be visible?
   */
  showToolExecution(item: RenderItem): boolean

  /**
   * Should thinking blocks be visible?
   */
  showThinking(item: RenderItem): boolean
}

/**
 * Minimal display policy - compact, essential only
 */
export class MinimalDisplayPolicy implements DisplayPolicy {
  shouldShow(item: RenderItem): boolean {
    // Only show user and assistant messages
    if ('role' in item) {
      return item.role === 'user' || item.role === 'assistant'
    }
    return false
  }

  shouldCollapse(_item: RenderItem): boolean {
    // Collapse everything by default
    return true
  }

  priority(item: RenderItem): number {
    if ('role' in item && item.role === 'user') return 100
    if ('role' in item && item.role === 'assistant') return 90
    return 0
  }

  showToolExecution(): boolean {
    return false
  }

  showThinking(): boolean {
    return false
  }
}

/**
 * Standard display policy - balanced, default
 */
export class StandardDisplayPolicy implements DisplayPolicy {
  shouldShow(item: RenderItem): boolean {
    // Show user, assistant, and tool messages
    if ('role' in item) {
      return ['user', 'assistant', 'tool'].includes(String(item.role))
    }
    return true
  }

  shouldCollapse(item: RenderItem): boolean {
    // Auto-collapse thinking blocks
    if ('role' in item && item.role === 'thinking') {
      return true
    }

    // Auto-collapse long tool outputs
    if ('role' in item && item.role === 'tool' && 'content' in item) {
      const content = String(item.content)
      return content.length > 1000
    }

    return false
  }

  priority(item: RenderItem): number {
    if ('role' in item) {
      switch (item.role) {
        case 'user': return 100
        case 'assistant': return 90
        case 'tool': return 80
        case 'thinking': return 70
        default: return 50
      }
    }
    return 0
  }

  showToolExecution(): boolean {
    return true
  }

  showThinking(): boolean {
    return true
  }
}

/**
 * Debug display policy - verbose, all details
 */
export class DebugDisplayPolicy implements DisplayPolicy {
  shouldShow(): boolean {
    // Show everything
    return true
  }

  shouldCollapse(): boolean {
    // Never collapse
    return false
  }

  priority(item: RenderItem): number {
    // Chronological order
    if ('timestamp' in item) {
      return item.timestamp
    }
    return 0
  }

  showToolExecution(): boolean {
    return true
  }

  showThinking(): boolean {
    return true
  }
}

/**
 * Get display policy for a display mode
 */
export function getDisplayPolicy(mode: DisplayMode): DisplayPolicy {
  switch (mode) {
    case 'minimal':
      return new MinimalDisplayPolicy()
    case 'debug':
      return new DebugDisplayPolicy()
    case 'standard':
    default:
      return new StandardDisplayPolicy()
  }
}

/**
 * Apply display policy to render items
 */
export function applyPolicy(
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

/**
 * Rendering Pipeline - Static/Live Split
 *
 * This module implements the Static/Live split pattern to prevent
 * full re-renders on every update. Committed messages render once
 * to terminal scrollback, while streaming content lives in dynamic
 * components.
 */

import type { RenderItem } from '../types'

export interface RenderPartition {
  // Static items (committed, render once)
  static: RenderItem[]

  // Live items (dynamic, re-render on updates)
  live: RenderItem[]

  // Resume boundary (filter out pre-resume messages)
  resumeBoundary?: number
}

/**
 * Partition render items into static and live zones
 */
export function partitionForRendering(
  items: RenderItem[],
  options: {
    resumeBoundary?: number
    streamingMessageId?: string
  } = {}
): RenderPartition {
  const { resumeBoundary, streamingMessageId } = options

  // Filter out pre-resume messages (O(0) session restoration)
  let filteredItems = items
  if (resumeBoundary !== undefined) {
    filteredItems = items.filter(item => {
      const timestamp = 'timestamp' in item ? item.timestamp : 0
      return timestamp >= resumeBoundary
    })
  }

  // Split into static and live
  const staticItems: RenderItem[] = []
  const liveItems: RenderItem[] = []

  filteredItems.forEach(item => {
    // Streaming messages go to live zone
    if ('streaming' in item && item.streaming) {
      liveItems.push(item)
      return
    }

    // Messages being actively updated go to live zone
    if ('id' in item && item.id === streamingMessageId) {
      liveItems.push(item)
      return
    }

    // Everything else is static (committed)
    staticItems.push(item)
  })

  return {
    static: staticItems,
    live: liveItems,
    resumeBoundary
  }
}

/**
 * Check if a re-render is needed based on what changed
 */
export function shouldRerender(
  prev: RenderPartition,
  next: RenderPartition
): {
  staticChanged: boolean
  liveChanged: boolean
  needsFullRerender: boolean
} {
  // Static zone changed (rare - only on commit)
  const staticChanged = prev.static.length !== next.static.length

  // Live zone changed (common - on every stream chunk)
  const liveChanged =
    prev.live.length !== next.live.length ||
    prev.live.some((item, i) => {
      const nextItem = next.live[i]
      if (!nextItem) return true

      // Check if content changed
      if ('content' in item && 'content' in nextItem) {
        return item.content !== nextItem.content
      }

      return false
    })

  // Full rerender needed if resume boundary changed
  const needsFullRerender = prev.resumeBoundary !== next.resumeBoundary

  return {
    staticChanged,
    liveChanged,
    needsFullRerender
  }
}

/**
 * Optimize render items for performance
 */
export function optimizeRenderItems(items: RenderItem[]): RenderItem[] {
  // Remove duplicate consecutive items
  const deduplicated: RenderItem[] = []
  let lastItem: RenderItem | null = null

  for (const item of items) {
    if (!lastItem || !areItemsEqual(lastItem, item)) {
      deduplicated.push(item)
      lastItem = item
    }
  }

  return deduplicated
}

/**
 * Check if two render items are equal
 */
function areItemsEqual(a: RenderItem, b: RenderItem): boolean {
  if ('id' in a && 'id' in b && a.id !== b.id) {
    return false
  }

  if ('role' in a && 'role' in b && a.role !== b.role) {
    return false
  }

  if ('content' in a && 'content' in b && a.content !== b.content) {
    return false
  }

  return true
}

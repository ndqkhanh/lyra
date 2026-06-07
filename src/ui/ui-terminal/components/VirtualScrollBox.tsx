/**
 * Virtual ScrollBox Component
 *
 * Implements Hermes-style virtual scrolling with binary search for O(log n) performance.
 * Only renders visible items + buffer, enabling smooth handling of 10,000+ messages.
 *
 * Key Features:
 * - Binary search on Float64Array offsets (O(log n))
 * - Only renders visible + overscan buffer (~120 items max)
 * - Constant memory usage regardless of total items
 * - Smooth 60 FPS scrolling
 * - Auto-scroll to bottom (sticky scroll)
 *
 * Based on Hermes Agent's useVirtualHistory hook.
 */

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { Box } from 'ink'

interface VirtualItem {
  key: string
  height?: number
  content: React.ReactNode
}

interface VirtualScrollBoxProps {
  items: VirtualItem[]
  viewportHeight?: number
  overscan?: number
  estimateHeight?: (item: VirtualItem, index: number) => number
  onHeightsChange?: (heights: Map<string, number>) => void
  sticky?: boolean
}

// Constants from Hermes
const DEFAULT_ESTIMATE = 4
const DEFAULT_OVERSCAN = 20
const MAX_MOUNTED = 120

/**
 * Binary search for upper bound in sorted array
 * Returns the first index where arr[index] > target
 */
function upperBound(arr: Float64Array, target: number, length: number): number {
  let lo = 0
  let hi = length

  while (lo < hi) {
    const mid = (lo + hi) >> 1
    arr[mid]! <= target ? (lo = mid + 1) : (hi = mid)
  }

  return lo
}

/**
 * Estimate item height with fallback chain
 */
function ensureHeight(
  heights: Map<string, number>,
  key: string,
  index: number,
  estimate: number,
  estimateFn?: (item: VirtualItem, index: number) => number,
  item?: VirtualItem
): number {
  // 1. Use measured height if available
  const measured = heights.get(key)
  if (measured !== undefined) return measured

  // 2. Use provided height from item
  if (item?.height !== undefined) return item.height

  // 3. Use custom estimator
  if (estimateFn && item) {
    const estimated = estimateFn(item, index)
    if (estimated > 0) return estimated
  }

  // 4. Fallback to default estimate
  return estimate
}

export function VirtualScrollBox({
  items,
  viewportHeight = 30,
  overscan = DEFAULT_OVERSCAN,
  estimateHeight,
  onHeightsChange,
  sticky = true
}: VirtualScrollBoxProps) {
  const n = items.length

  // Measured heights cache
  const heights = useRef(new Map<string, number>())
  const offsetVersion = useRef(0)

  // Cumulative offsets cache (zero-allocation reuse)
  const offsetsCache = useRef<{ arr: Float64Array; n: number; version: number }>({
    arr: new Float64Array(0),
    n: -1,
    version: -1
  })

  // Scroll state
  const [scrollTop, setScrollTop] = useState(0)
  const [pendingDelta, setPendingDelta] = useState(0)

  // Build cumulative offsets array
  const offsets = useMemo(() => {
    const cache = offsetsCache.current

    // Reuse cached offsets if unchanged
    if (cache.version === offsetVersion.current && cache.n === n) {
      return cache.arr
    }

    // Allocate or reuse array
    const arr = cache.arr.length >= n + 1 ? cache.arr : new Float64Array(n + 1)

    arr[0] = 0
    for (let i = 0; i < n; i++) {
      const height = ensureHeight(
        heights.current,
        items[i]!.key,
        i,
        DEFAULT_ESTIMATE,
        estimateHeight,
        items[i]
      )
      arr[i + 1] = arr[i]! + height
    }

    offsetsCache.current = { arr, n, version: offsetVersion.current }
    return arr
  }, [n, items, estimateHeight, offsetVersion.current])

  const totalHeight = offsets[n] || 0

  // Calculate visible range using binary search
  const { start, end, topSpacer, bottomSpacer } = useMemo(() => {
    if (n === 0) {
      return { start: 0, end: 0, topSpacer: 0, bottomSpacer: 0 }
    }

    const target = sticky ? Math.max(0, totalHeight - viewportHeight) : scrollTop + pendingDelta
    const clampedTarget = Math.max(0, Math.min(target, totalHeight - viewportHeight))

    const lo = Math.max(0, clampedTarget - overscan)
    const hi = clampedTarget + viewportHeight + overscan

    let start = Math.max(0, Math.min(n - 1, upperBound(offsets, lo, n + 1) - 1))
    let end = Math.max(start + 1, Math.min(n, upperBound(offsets, hi, n + 1)))

    // Cap at MAX_MOUNTED items
    if (end - start > MAX_MOUNTED) {
      if (sticky) {
        start = Math.max(0, end - MAX_MOUNTED)
      } else {
        end = Math.min(n, start + MAX_MOUNTED)
      }
    }

    // Coverage guarantee: ensure viewport is physically filled
    if (viewportHeight > 0) {
      const needed = viewportHeight + 2 * overscan
      let coverage = 0

      for (let i = start; i < end; i++) {
        coverage += ensureHeight(
          heights.current,
          items[i]!.key,
          i,
          1,  // Pessimistic estimate
          estimateHeight,
          items[i]
        )
      }

      if (sticky) {
        const minStart = Math.max(0, end - MAX_MOUNTED)
        while (start > minStart && coverage < needed) {
          start--
          coverage += ensureHeight(
            heights.current,
            items[start]!.key,
            start,
            1,
            estimateHeight,
            items[start]
          )
        }
      } else {
        const maxEnd = Math.min(n, start + MAX_MOUNTED)
        while (end < maxEnd && coverage < needed) {
          coverage += ensureHeight(
            heights.current,
            items[end]!.key,
            end,
            1,
            estimateHeight,
            items[end]
          )
          end++
        }
      }
    }

    const topSpacer = offsets[start] || 0
    const bottomSpacer = totalHeight - (offsets[end] || 0)

    return { start, end, topSpacer, bottomSpacer }
  }, [n, items, offsets, totalHeight, viewportHeight, overscan, sticky, scrollTop, pendingDelta, estimateHeight])

  // Measure callback for items
  const measureRef = useCallback((key: string, height: number) => {
    if (height > 0 && heights.current.get(key) !== height) {
      heights.current.set(key, height)
      offsetVersion.current++
      onHeightsChange?.(heights.current)
    }
  }, [onHeightsChange])

  // Auto-scroll to bottom when sticky
  useEffect(() => {
    if (sticky && n > 0) {
      const maxScroll = Math.max(0, totalHeight - viewportHeight)
      setScrollTop(maxScroll)
      setPendingDelta(0)
    }
  }, [sticky, n, totalHeight, viewportHeight])

  // Render visible items
  const visibleItems = items.slice(start, end)

  return (
    <Box flexDirection="column">
      {/* Top spacer */}
      {topSpacer > 0 && <Box height={Math.floor(topSpacer)} />}

      {/* Visible items */}
      {visibleItems.map((item) => (
        <MeasuredItem
          key={item.key}
          itemKey={item.key}
          onMeasure={measureRef}
        >
          {item.content}
        </MeasuredItem>
      ))}

      {/* Bottom spacer */}
      {bottomSpacer > 0 && <Box height={Math.floor(bottomSpacer)} />}

      {/* Debug info removed - enable via external component if needed */}
    </Box>
  )
}

/**
 * Wrapper component that measures item height
 */
interface MeasuredItemProps {
  itemKey: string
  onMeasure: (key: string, height: number) => void
  children: React.ReactNode
}

function MeasuredItem({ itemKey, onMeasure, children }: MeasuredItemProps) {
  const ref = useRef<any>(null)
  const [measured, setMeasured] = useState(false)

  useEffect(() => {
    if (!measured && ref.current?.yogaNode) {
      const height = Math.ceil(ref.current.yogaNode.getComputedHeight?.() ?? 0)
      if (height > 0) {
        onMeasure(itemKey, height)
        setMeasured(true)
      }
    }
  }, [measured, itemKey, onMeasure])

  // Measure at unmount to capture final height
  useEffect(() => {
    return () => {
      if (ref.current?.yogaNode) {
        const height = Math.ceil(ref.current.yogaNode.getComputedHeight?.() ?? 0)
        if (height > 0) {
          onMeasure(itemKey, height)
        }
      }
    }
  }, [itemKey, onMeasure])

  return (
    <Box ref={ref} flexDirection="column">
      {children}
    </Box>
  )
}

import React, { useRef, useEffect } from 'react'

/**
 * Debounce hook for performance optimization
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

/**
 * Throttle hook for performance optimization
 */
export function useThrottle<T>(value: T, interval: number): T {
  const [throttledValue, setThrottledValue] = React.useState<T>(value)
  const lastExecuted = useRef<number>(Date.now())

  useEffect(() => {
    if (Date.now() >= lastExecuted.current + interval) {
      lastExecuted.current = Date.now()
      setThrottledValue(value)
      return
    }

    const timerId = setTimeout(() => {
      lastExecuted.current = Date.now()
      setThrottledValue(value)
    }, interval)

    return () => clearTimeout(timerId)
  }, [value, interval])

  return throttledValue
}

/**
 * Memoize expensive computations
 */
export function useMemoizedValue<T>(factory: () => T, deps: React.DependencyList): T {
  return React.useMemo(factory, deps)
}

/**
 * Track render performance
 */
export function useRenderPerformance(_componentName: string) {
  const renderCount = useRef(0)
  const startTime = useRef(Date.now())

  useEffect(() => {
    renderCount.current++
    // Performance tracking is handled by monitoring system
    // No console logging in production
    startTime.current = Date.now()
  })

  return {
    renderCount: renderCount.current,
    reset: () => {
      renderCount.current = 0
      startTime.current = Date.now()
    }
  }
}

/**
 * Virtualization helper for large lists
 */
export function useVirtualization(
  totalItems: number,
  itemHeight: number,
  viewportHeight: number,
  scrollTop: number
) {
  const startIndex = Math.floor(scrollTop / itemHeight)
  const endIndex = Math.min(
    totalItems - 1,
    Math.ceil((scrollTop + viewportHeight) / itemHeight)
  )

  const visibleItems = []
  for (let i = startIndex; i <= endIndex; i++) {
    visibleItems.push(i)
  }

  return {
    startIndex,
    endIndex,
    visibleItems,
    offsetY: startIndex * itemHeight,
    totalHeight: totalItems * itemHeight
  }
}

/**
 * Batch updates for better performance
 */
export function useBatchedUpdates<T>(initialValue: T, batchDelay: number = 100) {
  const [value, setValue] = React.useState<T>(initialValue)
  const pendingUpdates = useRef<Array<(prev: T) => T>>([])
  const timeoutRef = useRef<NodeJS.Timeout>()

  const batchUpdate = React.useCallback((updater: (prev: T) => T) => {
    pendingUpdates.current.push(updater)

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    timeoutRef.current = setTimeout(() => {
      setValue(prev => {
        let result = prev
        for (const update of pendingUpdates.current) {
          result = update(result)
        }
        pendingUpdates.current = []
        return result
      })
    }, batchDelay)
  }, [batchDelay])

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return [value, batchUpdate] as const
}

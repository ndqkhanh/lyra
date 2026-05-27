import React from 'react'

/**
 * Memoized message component wrapper
 */
export const MemoizedMessage = React.memo<{ children: React.ReactNode }>(
  ({ children }) => {
    return React.createElement(React.Fragment, null, children)
  },
  (prevProps, nextProps) => {
    // Custom comparison - only re-render if children actually changed
    return prevProps.children === nextProps.children
  }
)

/**
 * Shallow comparison for props
 */
export function shallowEqual(obj1: any, obj2: any): boolean {
  if (obj1 === obj2) return true
  if (!obj1 || !obj2) return false

  const keys1 = Object.keys(obj1)
  const keys2 = Object.keys(obj2)

  if (keys1.length !== keys2.length) return false

  for (const key of keys1) {
    if (obj1[key] !== obj2[key]) return false
  }

  return true
}

/**
 * Deep comparison for complex objects
 */
export function deepEqual(obj1: any, obj2: any): boolean {
  if (obj1 === obj2) return true
  if (!obj1 || !obj2) return false
  if (typeof obj1 !== 'object' || typeof obj2 !== 'object') return false

  const keys1 = Object.keys(obj1)
  const keys2 = Object.keys(obj2)

  if (keys1.length !== keys2.length) return false

  for (const key of keys1) {
    if (!deepEqual(obj1[key], obj2[key])) return false
  }

  return true
}

/**
 * Create a memoized selector
 */
export function createSelector<T, R>(
  selector: (state: T) => R,
  equalityFn: (a: R, b: R) => boolean = shallowEqual
) {
  let lastState: T | undefined
  let lastResult: R | undefined

  return (state: T): R => {
    if (lastState === undefined) {
      lastResult = selector(state)
      lastState = state
      return lastResult!
    }

    const result = selector(state)
    if (equalityFn(result, lastResult!)) {
      return lastResult!
    }

    lastResult = result
    lastState = state
    return result
  }
}

/**
 * Batch multiple state updates
 */
export class UpdateBatcher<T> {
  private updates: Array<(state: T) => T> = []
  private timeout: NodeJS.Timeout | null = null
  private callback: (updater: (state: T) => T) => void

  constructor(callback: (updater: (state: T) => T) => void, delay: number = 16) {
    this.callback = callback
    this.delay = delay
  }

  private delay: number

  add(updater: (state: T) => T) {
    this.updates.push(updater)

    if (this.timeout) {
      clearTimeout(this.timeout)
    }

    this.timeout = setTimeout(() => {
      this.flush()
    }, this.delay)
  }

  flush() {
    if (this.updates.length === 0) return

    const updates = [...this.updates]
    this.updates = []

    this.callback(state => {
      let result = state
      for (const update of updates) {
        result = update(result)
      }
      return result
    })

    if (this.timeout) {
      clearTimeout(this.timeout)
      this.timeout = null
    }
  }

  clear() {
    this.updates = []
    if (this.timeout) {
      clearTimeout(this.timeout)
      this.timeout = null
    }
  }
}

/**
 * LRU Cache for expensive computations
 */
export class LRUCache<K, V> {
  private cache = new Map<K, V>()
  private maxSize: number

  constructor(maxSize: number = 100) {
    this.maxSize = maxSize
  }

  get(key: K): V | undefined {
    const value = this.cache.get(key)
    if (value !== undefined) {
      // Move to end (most recently used)
      this.cache.delete(key)
      this.cache.set(key, value)
    }
    return value
  }

  set(key: K, value: V): void {
    // Remove if exists
    if (this.cache.has(key)) {
      this.cache.delete(key)
    }

    // Add to end
    this.cache.set(key, value)

    // Evict oldest if over capacity
    if (this.cache.size > this.maxSize) {
      const firstKey = this.cache.keys().next().value
      if (firstKey !== undefined) {
        this.cache.delete(firstKey)
      }
    }
  }

  has(key: K): boolean {
    return this.cache.has(key)
  }

  clear(): void {
    this.cache.clear()
  }

  get size(): number {
    return this.cache.size
  }
}
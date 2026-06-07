import { RenderItem } from '@lyra/ui-core'
import { LRUCache } from './memoization'

/**
 * Cache for rendered items to avoid re-rendering unchanged content
 */
export class RenderCache {
  private cache = new LRUCache<string, RenderItem>(500)
  private hitCount = 0
  private missCount = 0

  get(key: string): RenderItem | undefined {
    const item = this.cache.get(key)
    if (item) {
      this.hitCount++
    } else {
      this.missCount++
    }
    return item
  }

  set(key: string, item: RenderItem): void {
    this.cache.set(key, item)
  }

  has(key: string): boolean {
    return this.cache.has(key)
  }

  clear(): void {
    this.cache.clear()
    this.hitCount = 0
    this.missCount = 0
  }

  getStats() {
    const total = this.hitCount + this.missCount
    return {
      size: this.cache.size,
      hits: this.hitCount,
      misses: this.missCount,
      hitRate: total > 0 ? this.hitCount / total : 0
    }
  }
}

/**
 * Batch render operations for better performance
 */
export class RenderBatcher {
  private pendingItems: RenderItem[] = []
  private timeout: NodeJS.Timeout | null = null
  private callback: (items: RenderItem[]) => void
  private delay: number

  constructor(callback: (items: RenderItem[]) => void, delay: number = 16) {
    this.callback = callback
    this.delay = delay
  }

  add(item: RenderItem): void {
    this.pendingItems.push(item)

    if (this.timeout) {
      clearTimeout(this.timeout)
    }

    this.timeout = setTimeout(() => {
      this.flush()
    }, this.delay)
  }

  addBatch(items: RenderItem[]): void {
    this.pendingItems.push(...items)

    if (this.timeout) {
      clearTimeout(this.timeout)
    }

    this.timeout = setTimeout(() => {
      this.flush()
    }, this.delay)
  }

  flush(): void {
    if (this.pendingItems.length === 0) return

    const items = [...this.pendingItems]
    this.pendingItems = []

    this.callback(items)

    if (this.timeout) {
      clearTimeout(this.timeout)
      this.timeout = null
    }
  }

  clear(): void {
    this.pendingItems = []
    if (this.timeout) {
      clearTimeout(this.timeout)
      this.timeout = null
    }
  }
}

/**
 * Incremental rendering for large message lists
 */
export class IncrementalRenderer {
  private items: RenderItem[] = []
  private renderedCount = 0
  private batchSize: number
  private onBatchRendered: (items: RenderItem[], isComplete: boolean) => void

  constructor(
    items: RenderItem[],
    batchSize: number,
    onBatchRendered: (items: RenderItem[], isComplete: boolean) => void
  ) {
    this.items = items
    this.batchSize = batchSize
    this.onBatchRendered = onBatchRendered
  }

  renderNext(): boolean {
    if (this.renderedCount >= this.items.length) {
      return false
    }

    const end = Math.min(this.renderedCount + this.batchSize, this.items.length)
    const batch = this.items.slice(this.renderedCount, end)
    this.renderedCount = end

    const isComplete = this.renderedCount >= this.items.length
    this.onBatchRendered(batch, isComplete)

    return !isComplete
  }

  renderAll(): void {
    while (this.renderNext()) {
      // Continue rendering
    }
  }

  reset(): void {
    this.renderedCount = 0
  }

  get progress(): number {
    return this.items.length > 0 ? this.renderedCount / this.items.length : 1
  }

  get isComplete(): boolean {
    return this.renderedCount >= this.items.length
  }
}

/**
 * Diff two render item arrays to find changes
 */
export function diffRenderItems(
  oldItems: RenderItem[],
  newItems: RenderItem[]
): {
  added: RenderItem[]
  removed: RenderItem[]
  updated: RenderItem[]
  unchanged: RenderItem[]
} {
  const oldMap = new Map(oldItems.map(item => [item.id, item]))
  const newMap = new Map(newItems.map(item => [item.id, item]))

  const added: RenderItem[] = []
  const removed: RenderItem[] = []
  const updated: RenderItem[] = []
  const unchanged: RenderItem[] = []

  // Find added and updated
  for (const newItem of newItems) {
    const oldItem = oldMap.get(newItem.id)
    if (!oldItem) {
      added.push(newItem)
    } else if (oldItem.timestamp !== newItem.timestamp) {
      updated.push(newItem)
    } else {
      unchanged.push(newItem)
    }
  }

  // Find removed
  for (const oldItem of oldItems) {
    if (!newMap.has(oldItem.id)) {
      removed.push(oldItem)
    }
  }

  return { added, removed, updated, unchanged }
}

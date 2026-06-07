/**
 * 60 FPS Streaming Debouncer
 *
 * Implements Hermes-style frame-rate limiting for smooth streaming updates.
 * Batches rapid token arrivals into 60 FPS (16.67ms) render frames.
 *
 * Key Features:
 * - 60 FPS target (16.67ms frame budget)
 * - Quantized snapshots (reduces React re-renders)
 * - Accumulates tokens between frames
 * - Flushes on stream end
 * - Zero dropped tokens
 *
 * Based on Hermes Agent's streaming_debouncer.py
 */

export interface StreamingDebouncerOptions {
  /** Target FPS (default: 60) */
  targetFPS?: number
  /** Minimum update interval in ms (default: 16.67ms for 60 FPS) */
  minInterval?: number
  /** Maximum buffered tokens before force flush (default: 1000) */
  maxBufferSize?: number
  /** Enable quantized snapshots (default: true) */
  quantize?: boolean
  /** Quantization bin size in tokens (default: 10) */
  quantizeBinSize?: number
}

export interface StreamUpdate {
  sessionId: string
  content: string
  timestamp: number
  tokenCount: number
}

type UpdateCallback = (update: StreamUpdate) => void

/**
 * Streaming debouncer that batches rapid token arrivals into 60 FPS frames.
 */
export class StreamingDebouncer {
  private targetFPS: number
  private minInterval: number
  private maxBufferSize: number
  private quantize: boolean
  private quantizeBinSize: number

  // Per-session state
  private buffers = new Map<string, string>()
  private lastFlushTime = new Map<string, number>()
  private pendingFlush = new Map<string, NodeJS.Timeout>()
  private tokenCounts = new Map<string, number>()
  private lastQuantizedCount = new Map<string, number>()

  private callback: UpdateCallback

  constructor(callback: UpdateCallback, options: StreamingDebouncerOptions = {}) {
    this.callback = callback
    this.targetFPS = options.targetFPS ?? 60
    this.minInterval = options.minInterval ?? (1000 / this.targetFPS)
    this.maxBufferSize = options.maxBufferSize ?? 1000
    this.quantize = options.quantize ?? true
    this.quantizeBinSize = options.quantizeBinSize ?? 10
  }

  /**
   * Add a token chunk to the buffer.
   * Will flush immediately if frame budget allows, otherwise schedules flush.
   */
  push(sessionId: string, chunk: string): void {
    // Initialize session state
    if (!this.buffers.has(sessionId)) {
      this.buffers.set(sessionId, '')
      this.lastFlushTime.set(sessionId, 0)
      this.tokenCounts.set(sessionId, 0)
      this.lastQuantizedCount.set(sessionId, 0)
    }

    // Accumulate chunk
    const currentBuffer = this.buffers.get(sessionId)!
    this.buffers.set(sessionId, currentBuffer + chunk)

    // Estimate token count (rough: 1 token ≈ 4 chars)
    const tokenCount = Math.ceil((currentBuffer.length + chunk.length) / 4)
    this.tokenCounts.set(sessionId, tokenCount)

    // Check if we should flush
    const now = Date.now()
    const lastFlush = this.lastFlushTime.get(sessionId)!
    const timeSinceLastFlush = now - lastFlush

    // Force flush if buffer is too large
    if (tokenCount >= this.maxBufferSize) {
      this.flushNow(sessionId)
      return
    }

    // Flush immediately if frame budget allows
    if (timeSinceLastFlush >= this.minInterval) {
      this.flushNow(sessionId)
      return
    }

    // Schedule flush for next frame
    this.scheduleFlush(sessionId)
  }

  /**
   * Schedule a flush for the next available frame.
   */
  private scheduleFlush(sessionId: string): void {
    // Clear existing pending flush
    const existing = this.pendingFlush.get(sessionId)
    if (existing) {
      clearTimeout(existing)
    }

    // Calculate time until next frame
    const now = Date.now()
    const lastFlush = this.lastFlushTime.get(sessionId)!
    const timeSinceLastFlush = now - lastFlush
    const timeUntilNextFrame = Math.max(0, this.minInterval - timeSinceLastFlush)

    // Schedule flush
    const timeout = setTimeout(() => {
      this.flushNow(sessionId)
    }, timeUntilNextFrame)

    this.pendingFlush.set(sessionId, timeout)
  }

  /**
   * Flush buffered content immediately.
   */
  private flushNow(sessionId: string): void {
    // Clear pending flush
    const pending = this.pendingFlush.get(sessionId)
    if (pending) {
      clearTimeout(pending)
      this.pendingFlush.delete(sessionId)
    }

    // Get buffered content
    const content = this.buffers.get(sessionId)
    if (!content) return

    const tokenCount = this.tokenCounts.get(sessionId) ?? 0

    // Quantized snapshots: only flush if we've crossed a bin boundary
    if (this.quantize) {
      const lastQuantized = this.lastQuantizedCount.get(sessionId) ?? 0
      const currentBin = Math.floor(tokenCount / this.quantizeBinSize)
      const lastBin = Math.floor(lastQuantized / this.quantizeBinSize)

      // Skip flush if we're still in the same bin
      if (currentBin === lastBin && tokenCount > 0) {
        return
      }

      this.lastQuantizedCount.set(sessionId, tokenCount)
    }

    // Emit update
    this.callback({
      sessionId,
      content,
      timestamp: Date.now(),
      tokenCount
    })

    // Update state
    this.lastFlushTime.set(sessionId, Date.now())
    this.buffers.set(sessionId, '')
    this.tokenCounts.set(sessionId, 0)
  }

  /**
   * Force flush all buffered content for a session.
   * Call this when streaming ends to ensure no tokens are lost.
   */
  flush(sessionId: string): void {
    // Disable quantization for final flush
    const wasQuantized = this.quantize
    this.quantize = false

    this.flushNow(sessionId)

    // Restore quantization setting
    this.quantize = wasQuantized
  }

  /**
   * Clean up session state.
   * Call this when a session ends.
   */
  cleanup(sessionId: string): void {
    // Flush any remaining content
    this.flush(sessionId)

    // Clear state
    this.buffers.delete(sessionId)
    this.lastFlushTime.delete(sessionId)
    this.tokenCounts.delete(sessionId)
    this.lastQuantizedCount.delete(sessionId)

    const pending = this.pendingFlush.get(sessionId)
    if (pending) {
      clearTimeout(pending)
      this.pendingFlush.delete(sessionId)
    }
  }

  /**
   * Get current buffer size for a session.
   */
  getBufferSize(sessionId: string): number {
    return this.buffers.get(sessionId)?.length ?? 0
  }

  /**
   * Get current token count for a session.
   */
  getTokenCount(sessionId: string): number {
    return this.tokenCounts.get(sessionId) ?? 0
  }

  /**
   * Check if a session has pending content.
   */
  hasPendingContent(sessionId: string): boolean {
    return this.getBufferSize(sessionId) > 0
  }
}

/**
 * Create a streaming debouncer with default 60 FPS settings.
 */
export function createStreamingDebouncer(
  callback: UpdateCallback,
  options?: StreamingDebouncerOptions
): StreamingDebouncer {
  return new StreamingDebouncer(callback, options)
}

/**
 * Performance metrics for streaming.
 */
export interface StreamingMetrics {
  totalTokens: number
  totalUpdates: number
  averageFPS: number
  droppedFrames: number
  bufferOverflows: number
}

/**
 * Streaming metrics tracker.
 */
export class StreamingMetricsTracker {
  private startTime = 0
  private totalTokens = 0
  private totalUpdates = 0
  private droppedFrames = 0
  private bufferOverflows = 0
  private lastUpdateTime = 0

  start(): void {
    this.startTime = Date.now()
    this.lastUpdateTime = this.startTime
  }

  recordUpdate(tokenCount: number): void {
    this.totalTokens += tokenCount
    this.totalUpdates++

    const now = Date.now()
    const timeSinceLastUpdate = now - this.lastUpdateTime

    // Detect dropped frames (>33ms between updates = missed 60 FPS target)
    if (timeSinceLastUpdate > 33 && this.lastUpdateTime > 0) {
      this.droppedFrames++
    }

    this.lastUpdateTime = now
  }

  recordBufferOverflow(): void {
    this.bufferOverflows++
  }

  getMetrics(): StreamingMetrics {
    const elapsed = Date.now() - this.startTime
    const averageFPS = elapsed > 0 ? (this.totalUpdates / elapsed) * 1000 : 0

    return {
      totalTokens: this.totalTokens,
      totalUpdates: this.totalUpdates,
      averageFPS: Math.round(averageFPS),
      droppedFrames: this.droppedFrames,
      bufferOverflows: this.bufferOverflows
    }
  }

  reset(): void {
    this.startTime = 0
    this.totalTokens = 0
    this.totalUpdates = 0
    this.droppedFrames = 0
    this.bufferOverflows = 0
    this.lastUpdateTime = 0
  }
}

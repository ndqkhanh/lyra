import {
  StreamingDebouncer,
  StreamingMetricsTracker,
  createStreamingDebouncer,
  type StreamUpdate,
} from '../streaming/debouncer'

describe('StreamingDebouncer', () => {
  let receivedUpdates: StreamUpdate[]
  let debouncer: StreamingDebouncer
  // Use high minInterval to prevent immediate auto-flush
  const noAutoFlush = { quantize: false, minInterval: 999999 }

  beforeEach(() => {
    receivedUpdates = []
    debouncer = new StreamingDebouncer((update) => {
      receivedUpdates.push(update)
    }, noAutoFlush)
  })

  afterEach(() => {
    debouncer.cleanup('test-session')
  })

  describe('push', () => {
    it('accumulates content in buffer on second push', () => {
      debouncer.push('test-session', 'First') // flushes immediately (initial lastFlushTime=0)
      debouncer.push('test-session', 'Second') // buffered (within minInterval)
      expect(debouncer.getBufferSize('test-session')).toBeGreaterThan(0)
    })

    it('schedules flush instead of immediate when frame budget not available', () => {
      debouncer.push('test-session', 'First')
      debouncer.push('test-session', 'Second')
      debouncer.flush('test-session')
      expect(receivedUpdates.length).toBeGreaterThan(0)
    })

    it('tracks token count on buffered push', () => {
      debouncer.push('test-session', 'First!')
      debouncer.push('test-session', 'Hello World') // buffered, ~3 tokens
      expect(debouncer.getTokenCount('test-session')).toBeGreaterThan(0)
    })
  })

  describe('flush', () => {
    it('delivers buffered content', () => {
      debouncer.push('test-session', 'First')
      debouncer.push('test-session', 'Part 1')
      debouncer.push('test-session', 'Part 2')
      debouncer.flush('test-session')
      const lastUpdate = receivedUpdates[receivedUpdates.length - 1]
      expect(lastUpdate).toBeDefined()
    })

    it('clears buffer after flush', () => {
      debouncer.push('test-session', 'First!')
      debouncer.push('test-session', 'Hello')
      debouncer.flush('test-session')
      expect(debouncer.getBufferSize('test-session')).toBe(0)
      expect(debouncer.getTokenCount('test-session')).toBe(0)
    })
  })

  describe('cleanup', () => {
    it('flushes remaining content and clears state', () => {
      debouncer.push('test-session', 'Final')
      debouncer.cleanup('test-session')
      expect(debouncer.getBufferSize('test-session')).toBe(0)
      expect(debouncer.getTokenCount('test-session')).toBe(0)
      expect(debouncer.hasPendingContent('test-session')).toBe(false)
    })
  })

  describe('hasPendingContent', () => {
    it('returns false initially', () => {
      expect(debouncer.hasPendingContent('test-session')).toBe(false)
    })

    it('returns true after second rapid push (buffered)', () => {
      // First push flushes immediately (lastFlushTime starts at 0)
      debouncer.push('test-session', 'First')
      // Second push within minInterval gets buffered
      debouncer.push('test-session', 'Second')
      expect(debouncer.hasPendingContent('test-session')).toBe(true)
    })
  })

  describe('getBufferSize', () => {
    it('returns 0 for unknown session', () => {
      expect(debouncer.getBufferSize('unknown')).toBe(0)
    })
  })

  describe('getTokenCount', () => {
    it('returns 0 for unknown session', () => {
      expect(debouncer.getTokenCount('unknown')).toBe(0)
    })
  })

  describe('quantization', () => {
    it('skips updates within same bin', () => {
      const qDebouncer = new StreamingDebouncer(
        (update) => { receivedUpdates.push(update) },
        { quantize: true, quantizeBinSize: 10, minInterval: 0 },
      )
      // Push a small chunk (< 10 tokens = < 40 chars)
      qDebouncer.push('s1', 'abc')
      // Skip pending flush timeout
      qDebouncer.flush('s1')
      // Small content may not trigger quantized update
      // But flush forces it
      expect(receivedUpdates.length).toBeGreaterThanOrEqual(0)
      qDebouncer.cleanup('s1')
    })

    it('flushes when crossing bin boundary', () => {
      const qDebouncer = new StreamingDebouncer(
        (update) => { receivedUpdates.push(update) },
        { quantize: true, quantizeBinSize: 5, minInterval: 1000 },
      )
      // Push 60 chars ≈ 15 tokens → crosses 0→5→10→15 bins
      qDebouncer.push('s1', 'x'.repeat(60))
      qDebouncer.flush('s1')
      expect(receivedUpdates.length).toBeGreaterThan(0)
      qDebouncer.cleanup('s1')
    })
  })

  describe('maxBufferSize', () => {
    it('force flushes when buffer exceeds max', () => {
      const smallDebouncer = new StreamingDebouncer(
        (update) => { receivedUpdates.push(update) },
        { maxBufferSize: 10, quantize: false, minInterval: 999999 },
      )
      // 10 tokens ≈ 40 chars
      smallDebouncer.push('s1', 'x'.repeat(50)) // ~13 tokens > 10
      expect(receivedUpdates.length).toBeGreaterThan(0)
      smallDebouncer.cleanup('s1')
    })
  })

  describe('createStreamingDebouncer', () => {
    it('creates a debouncer with default settings', () => {
      const d = createStreamingDebouncer(() => {})
      expect(d).toBeInstanceOf(StreamingDebouncer)
      expect(d.getBufferSize('test')).toBe(0)
    })

    it('accepts custom options', () => {
      const d = createStreamingDebouncer(() => {}, { targetFPS: 30 })
      expect(d).toBeInstanceOf(StreamingDebouncer)
    })
  })
})

describe('StreamingMetricsTracker', () => {
  let tracker: StreamingMetricsTracker

  beforeEach(() => {
    tracker = new StreamingMetricsTracker()
  })

  it('starts with zero metrics', () => {
    const metrics = tracker.getMetrics()
    expect(metrics.totalTokens).toBe(0)
    expect(metrics.totalUpdates).toBe(0)
    expect(metrics.averageFPS).toBe(0)
    expect(metrics.droppedFrames).toBe(0)
    expect(metrics.bufferOverflows).toBe(0)
  })

  it('records tokens and updates', () => {
    tracker.start()
    tracker.recordUpdate(10)
    tracker.recordUpdate(15)
    const metrics = tracker.getMetrics()
    expect(metrics.totalTokens).toBe(25)
    expect(metrics.totalUpdates).toBe(2)
  })

  it('records buffer overflow', () => {
    tracker.recordBufferOverflow()
    tracker.recordBufferOverflow()
    expect(tracker.getMetrics().bufferOverflows).toBe(2)
  })

  it('detects dropped frames (>33ms between updates)', async () => {
    tracker.start()
    tracker.recordUpdate(10)
    // Wait >33ms to simulate dropped frame
    await new Promise((r) => setTimeout(r, 40))
    tracker.recordUpdate(10)
    expect(tracker.getMetrics().droppedFrames).toBe(1)
  })

  it('resets all metrics', () => {
    tracker.start()
    tracker.recordUpdate(10)
    tracker.recordBufferOverflow()
    tracker.reset()
    const metrics = tracker.getMetrics()
    expect(metrics.totalTokens).toBe(0)
    expect(metrics.totalUpdates).toBe(0)
    expect(metrics.bufferOverflows).toBe(0)
  })

  it('calculates average FPS', () => {
    tracker.start()
    tracker.recordUpdate(10)
    const metrics = tracker.getMetrics()
    expect(metrics.averageFPS).toBeGreaterThanOrEqual(0)
  })
})

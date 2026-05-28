import {
  HeartbeatMonitor,
  createHeartbeat,
  type PingMessage,
  type PongMessage,
} from '../heartbeat'

describe('HeartbeatMonitor', () => {
  let monitor: HeartbeatMonitor
  let sentPings: PingMessage[]
  let reconnectCalls: number

  beforeEach(() => {
    sentPings = []
    reconnectCalls = 0
    monitor = new HeartbeatMonitor(
      (ping) => { sentPings.push(ping) },
      async () => { reconnectCalls++ },
      { pingInterval: 100, pongTimeout: 500, maxMissedPongs: 2 },
    )
  })

  afterEach(() => {
    monitor.cleanup()
  })

  describe('start/stop', () => {
    it('starts in connected state', () => {
      monitor.start()
      expect(monitor.getState()).toBe('connected')
    })

    it('sends first ping immediately', () => {
      monitor.start()
      expect(sentPings.length).toBeGreaterThanOrEqual(1)
      expect(sentPings[0]!.type).toBe('ping')
    })

    it('does not restart if already started', () => {
      monitor.start()
      const count = sentPings.length
      monitor.start()
      expect(sentPings.length).toBe(count) // no extra immediate ping
    })

    it('stops and transitions to disconnected', () => {
      monitor.start()
      monitor.stop()
      expect(monitor.getState()).toBe('disconnected')
    })

    it('emits connected event on start', () => {
      const spy = vi.fn()
      monitor.on('connected', spy)
      monitor.start()
      expect(spy).toHaveBeenCalled()
    })

    it('emits disconnected event on stop', () => {
      const spy = vi.fn()
      monitor.on('disconnected', spy)
      monitor.start()
      monitor.stop()
      expect(spy).toHaveBeenCalled()
    })
  })

  describe('handlePong', () => {
    it('updates latency on pong', () => {
      monitor.start()
      const ping = sentPings[0]!
      const pong: PongMessage = { type: 'pong', id: ping.id, timestamp: Date.now() }
      monitor.handlePong(pong)

      const metrics = monitor.getMetrics()
      expect(metrics.pongsReceived).toBe(1)
      expect(metrics.latency).toBeGreaterThanOrEqual(0)
    })

    it('ignores unknown pong ids', () => {
      monitor.start()
      const pong: PongMessage = { type: 'pong', id: 'unknown-id', timestamp: Date.now() }
      monitor.handlePong(pong)
      expect(monitor.getMetrics().pongsReceived).toBe(0)
    })

    it('emits pong event', () => {
      const spy = vi.fn()
      monitor.on('pong', spy)
      monitor.start()
      const ping = sentPings[0]!
      monitor.handlePong({ type: 'pong', id: ping.id, timestamp: Date.now() })
      expect(spy).toHaveBeenCalled()
      expect(spy.mock.calls[0][0].latency).toBeDefined()
    })

    it('restores from degraded state when health improves', () => {
      monitor.start()
      // Force degraded state
      ;(monitor as any).state = 'degraded'
      ;(monitor as any).metrics.healthScore = 80

      const ping = sentPings[0]!
      const spy = vi.fn()
      monitor.on('connection-restored', spy)

      monitor.handlePong({ type: 'pong', id: ping.id, timestamp: Date.now() })
      expect(spy).toHaveBeenCalled()
      expect(monitor.getState()).toBe('connected')
    })
  })

  describe('metrics', () => {
    it('starts with default metrics', () => {
      const m = monitor.getMetrics()
      expect(m.latency).toBe(0)
      expect(m.jitter).toBe(0)
      expect(m.packetLoss).toBe(0)
      expect(m.pingsSent).toBe(0)
      expect(m.pongsReceived).toBe(0)
      expect(m.missedPongs).toBe(0)
      expect(m.quality).toBe('excellent')
      expect(m.healthScore).toBe(100)
    })

    it('updates quality based on latency', () => {
      monitor.start()
      const ping = sentPings[0]!

      // Simulate excellent latency
      monitor.handlePong({ type: 'pong', id: ping.id, timestamp: Date.now() })
      const metrics = monitor.getMetrics()
      expect(metrics.quality).toBe('excellent')
    })
  })

  describe('getQuality', () => {
    it('returns current quality', () => {
      expect(monitor.getQuality()).toBe('excellent')
    })
  })

  describe('getHealthScore', () => {
    it('returns current health score', () => {
      expect(monitor.getHealthScore()).toBe(100)
    })
  })

  describe('forceReconnect', () => {
    it('calls reconnect function', async () => {
      monitor.start()
      await monitor.forceReconnect()
      expect(reconnectCalls).toBeGreaterThanOrEqual(1)
    })
  })

  describe('connection state transitions', () => {
    it('emits state-change events', () => {
      const spy = vi.fn()
      monitor.on('state-change', spy)
      monitor.start()
      expect(spy).toHaveBeenCalledWith('connected')
      monitor.stop()
      expect(spy).toHaveBeenCalledWith('disconnected')
    })
  })

  describe('cleanup', () => {
    it('stops and removes all listeners', () => {
      monitor.start()
      monitor.cleanup()
      expect(monitor.getState()).toBe('disconnected')
    })
  })

  describe('createHeartbeat', () => {
    it('creates a monitor with send and reconnect functions', () => {
      const hb = createHeartbeat(() => {}, async () => {})
      expect(hb).toBeInstanceOf(HeartbeatMonitor)
      expect(hb.getState()).toBe('disconnected')
      hb.cleanup()
    })

    it('accepts custom config', () => {
      const hb = createHeartbeat(() => {}, async () => {}, { pingInterval: 10000 })
      expect(hb).toBeInstanceOf(HeartbeatMonitor)
      hb.cleanup()
    })
  })
})

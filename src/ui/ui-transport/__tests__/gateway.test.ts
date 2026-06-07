import { EventEmitter } from 'eventemitter3'
import {
  MultiChannelGateway,
  createGateway,
  type ChannelConfig,
  type GatewayConfig,
} from '../gateway'
import type { Transport, ConnectionStatus } from '@lyra/ui-core'

class MockTransport extends EventEmitter implements Transport {
  status: ConnectionStatus = 'disconnected'
  private sessionId = ''

  setSessionId(id: string): void { this.sessionId = id }
  getSessionId(): string { return this.sessionId }

  async connect(): Promise<void> {
    this.status = 'connected'
    this.emit('status', 'connected')
  }
  async disconnect(): Promise<void> {
    this.status = 'disconnected'
    this.emit('status', 'disconnected')
  }
  async sendMessage(): Promise<void> {}

  onMessage(h: (m: any) => void): () => void {
    this.on('message', h)
    return () => this.off('message', h)
  }
  onStreamChunk(h: (c: any) => void): () => void {
    this.on('stream-chunk', h)
    return () => this.off('stream-chunk', h)
  }
  onStreamEvent(h: (e: any) => void): () => void {
    this.on('stream-event', h)
    return () => this.off('stream-event', h)
  }
  onError(h: (e: Error) => void): () => void {
    this.on('error', h)
    return () => this.off('error', h)
  }
  onStatusChange(h: (s: ConnectionStatus) => void): () => void {
    this.on('status', h)
    return () => this.off('status', h)
  }
}

function makeChannel(
  id: string,
  priority: 'high' | 'medium' | 'low' = 'high',
): ChannelConfig {
  return {
    id,
    type: 'websocket',
    transport: new MockTransport(),
    priority,
    failover: true,
    maxRetries: 3,
    retryDelay: 100,
    healthCheckInterval: 0,
  }
}

describe('MultiChannelGateway', () => {
  let gateway: MultiChannelGateway

  beforeEach(() => {
    gateway = new MultiChannelGateway()
  })

  afterEach(async () => {
    await gateway.disconnect()
  })

  describe('status', () => {
    it('is disconnected with no channels', () => {
      expect(gateway.status).toBe('disconnected')
    })

    it('is connected when any channel is connected', async () => {
      const ch = makeChannel('ch1')
      gateway.addChannel(ch)
      await gateway.connect()
      expect(gateway.status).toBe('connected')
    })

    it('is connecting when any channel is connecting', () => {
      const ch = makeChannel('ch1')
      ;(ch.transport as MockTransport).status = 'connecting'
      gateway.addChannel(ch)
      expect(gateway.status).toBe('connecting')
    })

    it('is error when all channels have error', () => {
      const ch = makeChannel('ch1')
      ;(ch.transport as MockTransport).status = 'error'
      gateway.addChannel(ch)
      expect(gateway.status).toBe('error')
    })
  })

  describe('addChannel', () => {
    it('adds channel and emits event', () => {
      const spy = vi.fn()
      gateway.on('channel-added', spy)
      gateway.addChannel(makeChannel('ch1'))
      expect(spy).toHaveBeenCalledWith('ch1')
    })

    it('initializes health tracking', () => {
      gateway.addChannel(makeChannel('ch1'))
      const health = gateway.getChannelHealth('ch1')
      expect(health).toBeDefined()
      expect(health!.channelId).toBe('ch1')
      expect(health!.status).toBe('disconnected')
    })
  })

  describe('removeChannel', () => {
    it('removes channel and emits event', async () => {
      const spy = vi.fn()
      gateway.on('channel-removed', spy)
      gateway.addChannel(makeChannel('ch1'))
      await gateway.removeChannel('ch1')
      expect(spy).toHaveBeenCalledWith('ch1')
      expect(gateway.getChannelHealth('ch1')).toBeNull()
    })

    it('is no-op for unknown channel', async () => {
      await expect(gateway.removeChannel('unknown')).resolves.toBeUndefined()
    })
  })

  describe('setSessionId', () => {
    it('sets session id on all channels', () => {
      const ch1 = makeChannel('ch1')
      const ch2 = makeChannel('ch2')
      gateway.addChannel(ch1)
      gateway.addChannel(ch2)
      gateway.setSessionId('session-123')
      expect(gateway.getSessionId()).toBe('session-123')
    })

    it('returns null without session', () => {
      expect(gateway.getSessionId()).toBeNull()
    })
  })

  describe('connect/disconnect', () => {
    it('connects all channels', async () => {
      gateway.addChannel(makeChannel('ch1'))
      gateway.addChannel(makeChannel('ch2'))
      await gateway.connect()
      expect(gateway.status).toBe('connected')
    })

    it('disconnects all channels', async () => {
      gateway.addChannel(makeChannel('ch1'))
      await gateway.connect()
      await gateway.disconnect()
      expect(gateway.status).toBe('disconnected')
    })
  })

  describe('getStats', () => {
    it('returns initial stats', () => {
      const stats = gateway.getStats()
      expect(stats.totalMessages).toBe(0)
      expect(stats.totalErrors).toBe(0)
      expect(stats.activeChannels).toBe(0)
      expect(stats.queuedMessages).toBe(0)
    })

    it('counts active channels', async () => {
      gateway.addChannel(makeChannel('ch1'))
      await gateway.connect()
      const stats = gateway.getStats()
      expect(stats.activeChannels).toBe(1)
    })
  })

  describe('routing: priority', () => {
    it('sends via highest priority channel', async () => {
      const chLow = makeChannel('low', 'low')
      const chHigh = makeChannel('high', 'high')
      gateway.addChannel(chLow)
      gateway.addChannel(chHigh)
      await gateway.connect()

      await gateway.sendMessage('test')
      const stats = gateway.getStats()
      expect(stats.totalMessages).toBe(1)
    })
  })

  describe('event forwarding', () => {
    it('forwards messages from channels', async () => {
      const spy = vi.fn()
      gateway.onMessage(spy)

      const ch = makeChannel('ch1')
      gateway.addChannel(ch)
      await gateway.connect()

      const msg = { id: 'm1', role: 'user', content: 'Hello', timestamp: Date.now() }
      ;(ch.transport as MockTransport).emit('message', msg)
      expect(spy).toHaveBeenCalledWith(msg)
    })

    it('forwards stream chunks', async () => {
      const spy = vi.fn()
      gateway.onStreamChunk(spy)

      const ch = makeChannel('ch1')
      gateway.addChannel(ch)
      await gateway.connect()

      const chunk = { type: 'delta', content: 'Hi' }
      ;(ch.transport as MockTransport).emit('stream-chunk', chunk)
      expect(spy).toHaveBeenCalledWith(chunk)
    })

    it('returns unsubscribe functions', () => {
      const unsub = gateway.onMessage(() => {})
      expect(typeof unsub).toBe('function')
      unsub()
    })
  })

  describe('createGateway', () => {
    it('creates gateway with defaults', () => {
      const gw = createGateway()
      expect(gw).toBeInstanceOf(MultiChannelGateway)
      expect(gw.status).toBe('disconnected')
    })

    it('accepts custom config', () => {
      const gw = createGateway({ strategy: 'round-robin' })
      expect(gw).toBeInstanceOf(MultiChannelGateway)
    })
  })
})

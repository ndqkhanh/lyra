import { EventEmitter } from 'events'
import { WebSocketTransport } from '../websocket'

// Mock ws module with a proper EventEmitter-based mock
vi.mock('ws', () => {
  const events = new EventEmitter()
  const MockWebSocket = vi.fn(function (this: any) {
    events.removeAllListeners()
    this._events = events
    return this
  })
  MockWebSocket.prototype = Object.create(EventEmitter.prototype)
  MockWebSocket.prototype.send = vi.fn()
  MockWebSocket.prototype.close = vi.fn()
  return { default: MockWebSocket }
})

import WebSocket from 'ws'

describe('WebSocketTransport', () => {
  let transport: WebSocketTransport

  beforeEach(() => {
    vi.clearAllMocks()
    transport = new WebSocketTransport('ws://localhost:3737/ws')
  })

  afterEach(() => {
    transport.disconnect()
  })

  function getMockWs(): any {
    return (WebSocket as any).mock.instances[0]
  }

  describe('initial state', () => {
    it('starts disconnected', () => {
      expect(transport.status).toBe('disconnected')
    })
  })

  describe('setSessionId', () => {
    it('stores session id', () => {
      transport.setSessionId('sess-456')
    })
  })

  describe('connect', () => {
    it('sets status to connecting immediately', () => {
      let resolved = false
      transport.connect().then(() => { resolved = true })
      expect(transport.status).toBe('connecting')
    })

    it('resolves on open event', async () => {
      const statusSpy = vi.fn()
      transport.onStatusChange(statusSpy)

      const connectPromise = transport.connect()
      getMockWs().emit('open')

      await connectPromise
      expect(transport.status).toBe('connected')
      expect(statusSpy).toHaveBeenCalledWith('connected')
    })

    it('rejects on error event', async () => {
      const connectPromise = transport.connect()
      getMockWs().emit('error', new Error('Connection refused'))

      await expect(connectPromise).rejects.toThrow('Connection refused')
      expect(transport.status).toBe('error')
    })
  })

  describe('disconnect', () => {
    it('closes websocket if open', async () => {
      const connectPromise = transport.connect()
      getMockWs().emit('open')
      await connectPromise

      transport.disconnect()
      expect(getMockWs().close).toHaveBeenCalled()
    })

    it('sets status to disconnected on close event', async () => {
      const connectPromise = transport.connect()
      getMockWs().emit('open')
      await connectPromise

      getMockWs().emit('close')
      expect(transport.status).toBe('disconnected')
    })

    it('handles disconnect when not connected', () => {
      expect(() => transport.disconnect()).not.toThrow()
    })
  })

  describe('sendMessage', () => {
    it('throws when not connected', async () => {
      await expect(transport.sendMessage('test')).rejects.toThrow('Not connected')
    })

    it('sends JSON message over websocket', async () => {
      const connectPromise = transport.connect()
      getMockWs().emit('open')
      await connectPromise

      transport.setSessionId('sess-1')
      await transport.sendMessage('hello')

      expect(getMockWs().send).toHaveBeenCalledWith(
        expect.stringContaining('hello'),
      )
    })

    it('includes model in payload when provided', async () => {
      const connectPromise = transport.connect()
      getMockWs().emit('open')
      await connectPromise

      await transport.sendMessage('hello', undefined, 'sonnet')

      const sent = JSON.parse((getMockWs().send as any).mock.calls[0][0])
      expect(sent.model).toBe('sonnet')
    })
  })

  describe('message handling', () => {
    it('emits stream-chunk on stream-chunk message', async () => {
      const chunkSpy = vi.fn()
      transport.onStreamChunk(chunkSpy)

      const connectPromise = transport.connect()
      getMockWs().emit('open')
      await connectPromise

      const chunk = { type: 'text', content: 'partial', done: false }
      getMockWs().emit('message', JSON.stringify({ type: 'stream-chunk', data: chunk }))

      expect(chunkSpy).toHaveBeenCalledWith(chunk)
    })

    it('emits message on message type', async () => {
      const msgSpy = vi.fn()
      transport.onMessage(msgSpy)

      const connectPromise = transport.connect()
      getMockWs().emit('open')
      await connectPromise

      getMockWs().emit('message', JSON.stringify({ type: 'message', data: { content: 'hi' } }))

      expect(msgSpy).toHaveBeenCalledWith({ content: 'hi' })
    })

    it('handles parse error gracefully', async () => {
      const errorSpy = vi.fn()
      transport.onError(errorSpy)

      const connectPromise = transport.connect()
      getMockWs().emit('open')
      await connectPromise

      getMockWs().emit('message', 'not valid json')

      expect(errorSpy).toHaveBeenCalled()
    })
  })

  describe('event subscriptions', () => {
    it('onMessage returns unsubscribe', () => {
      const handler = vi.fn()
      const unsub = transport.onMessage(handler)
      unsub()
      transport.emit('message', { content: 'test' } as any)
      expect(handler).not.toHaveBeenCalled()
    })

    it('onStreamChunk returns unsubscribe', () => {
      const handler = vi.fn()
      const unsub = transport.onStreamChunk(handler)
      unsub()
      transport.emit('stream-chunk', { type: 'text', content: 'x', done: false })
      expect(handler).not.toHaveBeenCalled()
    })
  })
})

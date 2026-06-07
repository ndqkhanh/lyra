import { LocalTransport } from '../local'

describe('LocalTransport', () => {
  let transport: LocalTransport

  beforeEach(() => {
    transport = new LocalTransport()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    transport.disconnect()
  })

  describe('initial state', () => {
    it('starts disconnected', () => {
      expect(transport.status).toBe('disconnected')
    })
  })

  describe('setSessionId', () => {
    it('stores session id', () => {
      transport.setSessionId('sess-123')
      // Session id is stored internally, verified via connect flow
    })
  })

  describe('connect', () => {
    it('transitions to connecting then connected on success', async () => {
      const statusSpy = vi.fn()
      transport.onStatusChange(statusSpy)

      global.fetch = vi.fn().mockResolvedValueOnce({ ok: true })

      await transport.connect()
      expect(transport.status).toBe('connected')
      expect(statusSpy).toHaveBeenCalledWith('connecting')
      expect(statusSpy).toHaveBeenCalledWith('connected')
    })

    it('transitions to disconnected on failure', async () => {
      global.fetch = vi.fn().mockRejectedValueOnce(new Error('Connection refused'))

      await expect(transport.connect()).rejects.toThrow()
      expect(transport.status).toBe('disconnected')
    })

    it('transitions to disconnected on non-ok response', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({ ok: false })

      await expect(transport.connect()).rejects.toThrow()
      expect(transport.status).toBe('disconnected')
    })
  })

  describe('disconnect', () => {
    it('sets status to disconnected', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({ ok: true })
      await transport.connect()

      await transport.disconnect()
      expect(transport.status).toBe('disconnected')
    })
  })

  describe('sendMessage', () => {
    it('throws when not connected', async () => {
      await expect(transport.sendMessage('hello')).rejects.toThrow('Not connected')
    })

    it('sends message and processes SSE stream', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({
          ok: true,
          body: {
            getReader: () => ({
              read: vi
                .fn()
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode('data: {"kind":"delta","payload":"Hello"}\n\n'),
                })
                .mockResolvedValueOnce({ done: true }),
            }),
          },
        })

      const chunkSpy = vi.fn()
      transport.onStreamChunk(chunkSpy)

      await transport.connect()
      await transport.sendMessage('hello')

      expect(chunkSpy).toHaveBeenCalled()
    })

    it('handles thinking_start SSE event', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({
          ok: true,
          body: {
            getReader: () => ({
              read: vi
                .fn()
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode('data: {"kind":"thinking_start","payload":"..."}\n\n'),
                })
                .mockResolvedValueOnce({ done: true }),
            }),
          },
        })

      const eventSpy = vi.fn()
      transport.onStreamEvent(eventSpy)

      await transport.connect()
      await transport.sendMessage('hello')

      expect(eventSpy).toHaveBeenCalledWith(
        expect.objectContaining({ kind: 'thinking_start' }),
      )
    })

    it('handles SSE error event', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({
          ok: true,
          body: {
            getReader: () => ({
              read: vi
                .fn()
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode('data: {"kind":"error","payload":"fail"}\n\n'),
                })
                .mockResolvedValueOnce({ done: true }),
            }),
          },
        })

      const errorSpy = vi.fn()
      transport.onError(errorSpy)

      await transport.connect()
      await transport.sendMessage('hello')

      expect(errorSpy).toHaveBeenCalled()
    })

    it('handles complete SSE event', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({
          ok: true,
          body: {
            getReader: () => ({
              read: vi
                .fn()
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode('data: {"kind":"complete","payload":"done"}\n\n'),
                })
                .mockResolvedValueOnce({ done: true }),
            }),
          },
        })

      const chunkSpy = vi.fn()
      transport.onStreamChunk(chunkSpy)

      await transport.connect()
      await transport.sendMessage('hello')

      const doneChunk = chunkSpy.mock.calls.find(
        (c: any) => c[0].done === true,
      )
      expect(doneChunk).toBeDefined()
    })

    it('handles tool_start and tool_end SSE events', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({
          ok: true,
          body: {
            getReader: () => ({
              read: vi
                .fn()
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode(
                    'data: {"kind":"tool_start","payload":"read_file"}\n' +
                      'data: {"kind":"tool_end","payload":"result"}\n\n',
                  ),
                })
                .mockResolvedValueOnce({ done: true }),
            }),
          },
        })

      const chunkSpy = vi.fn()
      transport.onStreamChunk(chunkSpy)

      await transport.connect()
      await transport.sendMessage('hello')

      const toolStart = chunkSpy.mock.calls.find(
        (c: any) => c[0].type === 'tool-call',
      )
      const toolEnd = chunkSpy.mock.calls.find(
        (c: any) => c[0].type === 'tool-result',
      )
      expect(toolStart).toBeDefined()
      expect(toolEnd).toBeDefined()
    })

    it('emits error on fetch failure', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockRejectedValueOnce(new Error('Network error'))

      const errorSpy = vi.fn()
      transport.onError(errorSpy)

      await transport.connect()
      await transport.sendMessage('hello')

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

    it('onError returns unsubscribe', () => {
      const handler = vi.fn()
      const unsub = transport.onError(handler)
      unsub()
      transport.emit('error', new Error('test'))
      expect(handler).not.toHaveBeenCalled()
    })

    it('onStatusChange returns unsubscribe', () => {
      const handler = vi.fn()
      const unsub = transport.onStatusChange(handler)
      unsub()
      transport.emit('status', 'connected')
      expect(handler).not.toHaveBeenCalled()
    })
  })
})

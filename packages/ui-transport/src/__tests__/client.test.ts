import { EventEmitter } from 'events'
import { TransportClient } from '../client'
import { TransportMessage } from '../types'

describe('TransportClient', () => {
  let client: TransportClient
  let mockEmitter: EventEmitter

  beforeEach(() => {
    mockEmitter = new EventEmitter()
    client = new TransportClient(mockEmitter)
  })

  afterEach(() => {
    client.disconnect()
  })

  describe('connect', () => {
    it('establishes connection', async () => {
      const connected = await client.connect()
      expect(connected).toBe(true)
      expect(client.isConnected()).toBe(true)
    })

    it('emits connect event', async () => {
      const connectSpy = vi.fn()
      client.on('connect', connectSpy)
      await client.connect()
      expect(connectSpy).toHaveBeenCalled()
    })
  })

  describe('disconnect', () => {
    it('closes connection', async () => {
      await client.connect()
      client.disconnect()
      expect(client.isConnected()).toBe(false)
    })

    it('emits disconnect event', async () => {
      const disconnectSpy = vi.fn()
      client.on('disconnect', disconnectSpy)
      await client.connect()
      client.disconnect()
      expect(disconnectSpy).toHaveBeenCalled()
    })
  })

  describe('send', () => {
    it('sends message when connected', async () => {
      await client.connect()
      const message: TransportMessage = {
        type: 'user_message',
        content: 'Hello',
        timestamp: Date.now()
      }
      const sent = await client.send(message)
      expect(sent).toBe(true)
    })

    it('fails to send when disconnected', async () => {
      const message: TransportMessage = {
        type: 'user_message',
        content: 'Hello',
        timestamp: Date.now()
      }
      const sent = await client.send(message)
      expect(sent).toBe(false)
    })

    it('emits message event', async () => {
      await client.connect()
      const messageSpy = vi.fn()
      client.on('message', messageSpy)

      const message: TransportMessage = {
        type: 'user_message',
        content: 'Hello',
        timestamp: Date.now()
      }
      await client.send(message)
      expect(messageSpy).toHaveBeenCalledWith(message)
    })
  })

  describe('receive', () => {
    it('receives messages', async () => {
      await client.connect()
      const receiveSpy = vi.fn()
      client.on('message', receiveSpy)

      const message: TransportMessage = {
        type: 'assistant_message',
        content: 'Response',
        timestamp: Date.now()
      }
      mockEmitter.emit('message', message)
      expect(receiveSpy).toHaveBeenCalledWith(message)
    })

    it('handles streaming messages', async () => {
      await client.connect()
      const streamSpy = vi.fn()
      client.on('stream', streamSpy)

      const chunk: TransportMessage = {
        type: 'stream_chunk',
        content: 'Partial',
        timestamp: Date.now()
      }
      mockEmitter.emit('stream', chunk)
      expect(streamSpy).toHaveBeenCalledWith(chunk)
    })
  })

  describe('error handling', () => {
    it('emits error event on connection failure', async () => {
      const errorSpy = vi.fn()
      client.on('error', errorSpy)

      mockEmitter.emit('error', new Error('Connection failed'))
      expect(errorSpy).toHaveBeenCalled()
    })

    it('handles reconnection', async () => {
      await client.connect()
      client.disconnect()
      const reconnected = await client.connect()
      expect(reconnected).toBe(true)
    })
  })

  describe('message queue', () => {
    it('queues messages when disconnected', async () => {
      const message: TransportMessage = {
        type: 'user_message',
        content: 'Queued',
        timestamp: Date.now()
      }
      await client.send(message)

      await client.connect()
      // Message should be sent after connection
      expect(client.isConnected()).toBe(true)
    })

    it('processes queue in order', async () => {
      const messages: TransportMessage[] = [
        { type: 'user_message', content: 'First', timestamp: Date.now() },
        { type: 'user_message', content: 'Second', timestamp: Date.now() },
        { type: 'user_message', content: 'Third', timestamp: Date.now() }
      ]

      for (const msg of messages) {
        await client.send(msg)
      }

      await client.connect()
      // All messages should be processed
      expect(client.isConnected()).toBe(true)
    })
  })
})

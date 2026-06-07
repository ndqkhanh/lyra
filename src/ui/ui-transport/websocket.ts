import { EventEmitter } from 'eventemitter3'
import WebSocket from 'ws'
import type {
  Transport,
  ConnectionStatus,
  StreamChunk,
  StreamEvent,
  Message,
  Attachment
} from '@lyra/ui-core'

export class WebSocketTransport extends EventEmitter implements Transport {
  private ws: WebSocket | null = null
  status: ConnectionStatus = 'disconnected'
  private url: string
  private sessionId: string | null = null

  constructor(url: string) {
    super()
    this.url = url
  }

  setSessionId(id: string): void {
    this.sessionId = id
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.status = 'connecting'
      this.emit('status', this.status)

      this.ws = new WebSocket(this.url)

      this.ws.on('open', () => {
        this.status = 'connected'
        this.emit('status', this.status)
        resolve()
      })

      this.ws.on('message', (data: string) => {
        try {
          const parsed = JSON.parse(data.toString())

          if (parsed.type === 'stream-chunk') {
            this.emit('stream-chunk', parsed.data as StreamChunk)
          } else if (parsed.type === 'message') {
            this.emit('message', parsed.data)
          }
        } catch (err) {
          this.emit('error', err as Error)
        }
      })

      this.ws.on('error', (err: Error) => {
        this.status = 'error'
        this.emit('status', this.status)
        this.emit('error', err)
        reject(err)
      })

      this.ws.on('close', () => {
        this.status = 'disconnected'
        this.emit('status', this.status)
      })
    })
  }

  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  async sendMessage(content: string, attachments?: Attachment[], model?: string): Promise<void> {
    if (!this.ws || this.status !== 'connected') {
      throw new Error('Not connected')
    }

    this.ws.send(JSON.stringify({
      type: 'message',
      content,
      model,
      session_id: this.sessionId,
      attachments
    }))
  }

  onMessage(handler: (message: Message) => void): () => void {
    this.on('message', handler)
    return () => this.off('message', handler)
  }

  onStreamChunk(handler: (chunk: StreamChunk) => void): () => void {
    this.on('stream-chunk', handler)
    return () => this.off('stream-chunk', handler)
  }

  onStreamEvent(handler: (event: StreamEvent) => void): () => void {
    this.on('stream-event', handler)
    return () => this.off('stream-event', handler)
  }

  onError(handler: (error: Error) => void): () => void {
    this.on('error', handler)
    return () => this.off('error', handler)
  }

  onStatusChange(handler: (status: ConnectionStatus) => void): () => void {
    this.on('status', handler)
    return () => this.off('status', handler)
  }
}

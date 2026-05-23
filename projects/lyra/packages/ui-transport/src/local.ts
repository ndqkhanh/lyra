import { EventEmitter } from 'eventemitter3'
import type {
  Transport,
  ConnectionStatus,
  StreamChunk,
  Message,
  Attachment
} from '@lyra/ui-core'

export class LocalTransport extends EventEmitter implements Transport {
  private socket: any = null
  private status: ConnectionStatus = 'disconnected'

  async connect(): Promise<void> {
    this.status = 'connecting'
    this.emit('status', this.status)

    // TODO: Connect to local daemon via Unix socket
    // For now, simulate connection
    await new Promise(resolve => setTimeout(resolve, 100))

    this.status = 'connected'
    this.emit('status', this.status)
  }

  async disconnect(): Promise<void> {
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
    this.status = 'disconnected'
    this.emit('status', this.status)
  }

  async sendMessage(content: string, attachments?: Attachment[]): Promise<void> {
    if (this.status !== 'connected') {
      throw new Error('Not connected')
    }

    // TODO: Send message to daemon
    this.emit('message-sent', { content, attachments })
  }

  onMessage(handler: (message: Message) => void): () => void {
    this.on('message', handler)
    return () => this.off('message', handler)
  }

  onStreamChunk(handler: (chunk: StreamChunk) => void): () => void {
    this.on('stream-chunk', handler)
    return () => this.off('stream-chunk', handler)
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

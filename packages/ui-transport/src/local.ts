import { EventEmitter } from 'eventemitter3'
import type {
  Transport,
  ConnectionStatus,
  StreamChunk,
  StreamEvent,
  Message,
  Attachment
} from '@lyra/ui-core'

export class LocalTransport extends EventEmitter implements Transport {
  private serverUrl = 'http://localhost:3737'
  private status: ConnectionStatus = 'disconnected'
  private sessionId: string | null = null

  async connect(): Promise<void> {
    this.status = 'connecting'
    this.emit('status', this.status)

    try {
      // Check if server is running
      const response = await fetch(`${this.serverUrl}/health`)
      if (!response.ok) {
        throw new Error('Server not responding')
      }

      this.status = 'connected'
      this.emit('status', this.status)
    } catch (error) {
      this.status = 'disconnected'
      this.emit('status', this.status)
      throw new Error('Failed to connect to Lyra server. Make sure the server is running.')
    }
  }

  async disconnect(): Promise<void> {
    this.status = 'disconnected'
    this.emit('status', this.status)
  }

  async sendMessage(content: string, attachments?: Attachment[], model?: string): Promise<void> {
    if (this.status !== 'connected') {
      throw new Error('Not connected')
    }

    try {
      const response = await fetch(`${this.serverUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: content,
          session_id: this.sessionId,
          model: model || undefined,
          attachments,
        }),
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`)
      }

      // Emit message-sent event
      this.emit('message-sent', { content, attachments })

      // Parse SSE stream
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))

            switch (data.kind) {
              case 'delta': {
                const chunk: StreamChunk = {
                  type: 'text',
                  content: data.payload,
                  done: false,
                  metadata: data.metadata,
                }
                this.emit('stream-chunk', chunk)
                break
              }
              case 'thinking_start': {
                const evt: StreamEvent = {
                  kind: 'thinking_start',
                  payload: data.payload,
                  metadata: data.metadata,
                }
                this.emit('stream-event', evt)
                break
              }
              case 'thinking_end': {
                const evt: StreamEvent = {
                  kind: 'thinking_end',
                  payload: data.payload,
                  metadata: data.metadata,
                }
                this.emit('stream-event', evt)
                break
              }
              case 'tool_start': {
                const chunk: StreamChunk = {
                  type: 'tool-call',
                  content: data.payload,
                  done: false,
                  metadata: data.metadata,
                }
                this.emit('stream-chunk', chunk)
                break
              }
              case 'tool_end': {
                const chunk: StreamChunk = {
                  type: 'tool-result',
                  content: data.payload,
                  done: false,
                  metadata: data.metadata,
                }
                this.emit('stream-chunk', chunk)
                break
              }
              case 'complete': {
                const chunk: StreamChunk = {
                  type: 'text',
                  content: '',
                  done: true,
                  metadata: data.metadata,
                }
                this.emit('stream-chunk', chunk)
                break
              }
              case 'error': {
                this.emit('error', new Error(data.payload))
                break
              }
            }
          }
        }
      }
    } catch (error) {
      this.emit('error', error instanceof Error ? error : new Error(String(error)))
    }
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

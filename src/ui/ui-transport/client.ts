import { EventEmitter } from 'events'
import type { TransportMessage } from './types'

export class TransportClient {
  private emitter: EventEmitter
  private connected = false
  private queue: TransportMessage[] = []

  constructor(emitter: EventEmitter) {
    this.emitter = emitter
  }

  async connect(): Promise<boolean> {
    this.connected = true
    this.emitter.emit('connect')
    this.flushQueue()
    return true
  }

  disconnect(): void {
    this.connected = false
    this.emitter.emit('disconnect')
  }

  isConnected(): boolean {
    return this.connected
  }

  async send(message: TransportMessage): Promise<boolean> {
    if (!this.connected) {
      this.queue.push(message)
      return false
    }
    this.emitter.emit('message', message)
    return true
  }

  on(event: string, handler: (...args: unknown[]) => void): void {
    this.emitter.on(event, handler)
  }

  private flushQueue(): void {
    while (this.queue.length > 0) {
      const msg = this.queue.shift()!
      this.emitter.emit('message', msg)
    }
  }
}

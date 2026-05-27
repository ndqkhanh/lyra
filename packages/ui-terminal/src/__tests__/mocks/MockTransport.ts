import type { Transport, Message, StreamChunk, StreamEvent, ConnectionStatus, Attachment } from '@lyra/ui-core'

type Handler = (...args: any[]) => void

/**
 * Mock transport that simulates DeepSeek API streaming responses.
 *
 * Instead of making HTTP calls, this stores handlers and lets tests fire
 * events programmatically to simulate any streaming scenario.
 */
export class MockTransport implements Transport {
  private _status: ConnectionStatus = 'disconnected'
  private _handlers = new Map<string, Set<Handler>>()

  // ── Transport interface ──────────────────────────────────

  async connect(): Promise<void> {
    this._status = 'connected'
    this._emit('status', 'connected')
  }

  async disconnect(): Promise<void> {
    this._status = 'disconnected'
    this._emit('status', 'disconnected')
  }

  async sendMessage(
    _content: string,
    _attachments?: Attachment[],
    _model?: string
  ): Promise<void> {
    // No-op — tests call simulate* methods directly
  }

  onMessage(handler: (message: Message) => void): () => void {
    return this._on('message', handler)
  }

  onStreamChunk(handler: (chunk: StreamChunk) => void): () => void {
    return this._on('stream-chunk', handler)
  }

  onStreamEvent(handler: (event: StreamEvent) => void): () => void {
    return this._on('stream-event', handler)
  }

  onError(handler: (error: Error) => void): () => void {
    return this._on('error', handler)
  }

  onStatusChange(handler: (status: ConnectionStatus) => void): () => void {
    return this._on('status', handler)
  }

  // ── Simulation API ───────────────────────────────────────

  /**
   * Simulate a complete DeepSeek-style streaming response:
   *   thinking_start → text chunks → tool calls → tool results → final text → complete
   *
   * Each item in the stream fires with the given delay (default 0ms for tests).
   * Returns a promise that resolves when all items have fired.
   */
  async simulateFullResponse(
    stream: SimulatedStreamItem[],
    options: { delay?: number } = {}
  ): Promise<void> {
    const { delay = 0 } = options
    for (const item of stream) {
      if (delay > 0) {
        await new Promise(r => setTimeout(r, delay))
      }
      this.fireItem(item)
    }
    // Always fire the done/complete chunk at the end
    this._emit('stream-chunk', { type: 'text', content: '', done: true } as StreamChunk)
  }

  /** Fire a single simulated stream item. */
  fireItem(item: SimulatedStreamItem): void {
    switch (item.kind) {
      case 'thinking_start':
        this._emit('stream-event', {
          kind: 'thinking_start',
          payload: item.content || '',
        } as StreamEvent)
        break
      case 'thinking_end':
        this._emit('stream-event', {
          kind: 'thinking_end',
          payload: '',
        } as StreamEvent)
        break
      case 'text':
        this._emit('stream-chunk', {
          type: 'text',
          content: item.content,
        } as StreamChunk)
        break
      case 'tool-call':
        this._emit('stream-chunk', {
          type: 'tool-call',
          content: item.name,
          metadata: { tool_args: JSON.stringify(item.args || {}) },
        } as StreamChunk)
        break
      case 'tool-result':
        this._emit('stream-chunk', {
          type: 'tool-result',
          content: item.output || '',
          metadata: { tool_name: item.name },
        } as StreamChunk)
        break
      case 'done':
        this._emit('stream-chunk', {
          type: 'text',
          content: '',
          done: true,
        } as StreamChunk)
        break
      case 'error':
        this._emit('error', new Error(item.message || 'Simulated error'))
        break
    }
  }

  // ── Internal helpers ─────────────────────────────────────

  private _on(event: string, handler: Handler): () => void {
    if (!this._handlers.has(event)) {
      this._handlers.set(event, new Set())
    }
    this._handlers.get(event)!.add(handler)
    return () => {
      this._handlers.get(event)?.delete(handler)
    }
  }

  private _emit(event: string, ...args: unknown[]): void {
    const handlers = this._handlers.get(event)
    if (handlers) {
      for (const handler of handlers) {
        handler(...args)
      }
    }
  }
}

// ── Types ──────────────────────────────────────────────

export type SimulatedStreamItem =
  | { kind: 'thinking_start'; content?: string }
  | { kind: 'thinking_end' }
  | { kind: 'text'; content: string }
  | { kind: 'tool-call'; name: string; args?: Record<string, unknown> }
  | { kind: 'tool-result'; name: string; output: string }
  | { kind: 'done' }
  | { kind: 'error'; message: string }

// ── Pre-built DeepSeek-style stream scenarios ──────────

/** Simple text-only response: "Hello! How can I help you today?" */
export const SIMPLE_TEXT_RESPONSE: SimulatedStreamItem[] = [
  { kind: 'text', content: 'Hello' },
  { kind: 'text', content: '! How' },
  { kind: 'text', content: ' can' },
  { kind: 'text', content: ' I' },
  { kind: 'text', content: ' help' },
  { kind: 'text', content: ' you' },
  { kind: 'text', content: ' today' },
  { kind: 'text', content: '?' },
]

/** Response with thinking block + text. */
export const THINKING_THEN_RESPONSE: SimulatedStreamItem[] = [
  { kind: 'thinking_start', content: 'Let me analyze this question...' },
  { kind: 'text', content: 'Based on my analysis' },
  { kind: 'text', content: ', here is the answer.' },
  { kind: 'thinking_end' },
  { kind: 'text', content: 'The answer is 42.' },
]

/** Response with tool calls: file read + write. */
export const TOOL_CALL_RESPONSE: SimulatedStreamItem[] = [
  { kind: 'text', content: 'Let me' },
  { kind: 'text', content: ' check the file first.' },
  { kind: 'tool-call', name: 'Read', args: { file_path: '/path/to/file.py' } },
  { kind: 'tool-result', name: 'Read', output: 'Wrote 13 lines to /path/to/file.py' },
  { kind: 'text', content: 'Now let me write' },
  { kind: 'text', content: ' the changes.' },
  { kind: 'tool-call', name: 'Write', args: { file_path: '/path/to/file.py' } },
  { kind: 'tool-result', name: 'Write', output: 'Wrote 13 lines to /path/to/file.py' },
  { kind: 'text', content: 'Done! The file has been updated.' },
]

/** Large streaming chunks to test re-render behavior (header duplication trigger). */
export const MANY_SMALL_CHUNKS: SimulatedStreamItem[] = Array.from(
  { length: 50 },
  (_, i) => ({ kind: 'text' as const, content: `chunk${i} ` })
)

/** Phased task response with checkboxes. */
export const PHASED_RESPONSE: SimulatedStreamItem[] = [
  { kind: 'thinking_start', content: 'Breaking down the task...' },
  { kind: 'text', content: "I'll complete this in phases:\n" },
  { kind: 'thinking_end' },
  { kind: 'text', content: 'Phase 1: Analysis - Done\n' },
  { kind: 'text', content: 'Phase 2: Implementation - In progress\n' },
  { kind: 'text', content: 'Phase 3: Testing - Pending' },
]

import React from 'react'
import { render } from 'ink-testing-library'
import { TerminalUI } from '../TerminalUI'
import { TransportClient } from '@lyra/ui-transport'
import { TransportMessage } from '@lyra/ui-transport'

describe('Integration: TerminalUI + Transport', () => {
  let client: TransportClient

  beforeEach(() => {
    client = new TransportClient()
  })

  afterEach(() => {
    client.disconnect()
  })

  it('renders complete UI with transport', async () => {
    await client.connect()
    const { lastFrame } = render(<TerminalUI transport={client} />)
    expect(lastFrame()).toBeDefined()
  })

  it('sends user message through transport', async () => {
    await client.connect()
    const messageSpy = jest.fn()
    client.on('message', messageSpy)

    const { stdin } = render(<TerminalUI transport={client} />)
    stdin.write('Hello')
    stdin.write('\r')

    expect(messageSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'user_message',
        content: 'Hello'
      })
    )
  })

  it('receives assistant message from transport', async () => {
    await client.connect()
    const { lastFrame } = render(<TerminalUI transport={client} />)

    const message: TransportMessage = {
      type: 'assistant_message',
      content: 'Response from assistant',
      timestamp: Date.now()
    }
    client.emit('message', message)

    expect(lastFrame()).toContain('Response from assistant')
  })

  it('handles streaming response', async () => {
    await client.connect()
    const { lastFrame } = render(<TerminalUI transport={client} />)

    const chunks = ['Hello', ' ', 'world', '!']
    for (const chunk of chunks) {
      client.emit('stream', {
        type: 'stream_chunk',
        content: chunk,
        timestamp: Date.now()
      })
    }

    expect(lastFrame()).toContain('Hello world!')
  })

  it('updates status bar during streaming', async () => {
    await client.connect()
    const { lastFrame } = render(<TerminalUI transport={client} />)

    client.emit('status', { status: 'streaming' })
    expect(lastFrame()).toContain('streaming')

    client.emit('status', { status: 'idle' })
    expect(lastFrame()).toContain('idle')
  })

  it('handles tool execution display', async () => {
    await client.connect()
    const { lastFrame } = render(<TerminalUI transport={client} />)

    client.emit('tool', {
      type: 'tool_execution',
      tool: 'read_file',
      input: { path: 'test.txt' },
      output: 'File content',
      timestamp: Date.now()
    })

    expect(lastFrame()).toContain('read_file')
    expect(lastFrame()).toContain('test.txt')
  })

  it('handles thinking block display', async () => {
    await client.connect()
    const { lastFrame } = render(<TerminalUI transport={client} />)

    client.emit('thinking', {
      type: 'thinking',
      content: 'Analyzing the problem...',
      timestamp: Date.now()
    })

    expect(lastFrame()).toContain('Analyzing the problem...')
  })

  it('handles connection errors', async () => {
    const { lastFrame } = render(<TerminalUI transport={client} />)

    client.emit('error', new Error('Connection failed'))
    expect(lastFrame()).toContain('error')
  })

  it('handles reconnection', async () => {
    await client.connect()
    const { lastFrame } = render(<TerminalUI transport={client} />)

    client.disconnect()
    expect(lastFrame()).toContain('disconnected')

    await client.connect()
    expect(lastFrame()).toContain('connected')
  })

  it('maintains message history across reconnection', async () => {
    await client.connect()
    const { stdin, lastFrame } = render(<TerminalUI transport={client} />)

    stdin.write('Message 1')
    stdin.write('\r')

    client.disconnect()
    await client.connect()

    stdin.write('Message 2')
    stdin.write('\r')

    expect(lastFrame()).toContain('Message 1')
    expect(lastFrame()).toContain('Message 2')
  })
})

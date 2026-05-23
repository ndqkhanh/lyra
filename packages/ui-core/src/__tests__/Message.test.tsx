import React from 'react'
import { render } from 'ink-testing-library'
import { Message } from '../components/Message'
import { MessageProps } from '../types'

describe('Message', () => {
  const baseProps: MessageProps = {
    role: 'user',
    content: 'Test message',
    timestamp: new Date('2024-01-01T00:00:00Z')
  }

  it('renders user message correctly', () => {
    const { lastFrame } = render(<Message {...baseProps} />)
    expect(lastFrame()).toContain('Test message')
    expect(lastFrame()).toContain('You')
  })

  it('renders assistant message correctly', () => {
    const { lastFrame } = render(
      <Message {...baseProps} role="assistant" />
    )
    expect(lastFrame()).toContain('Test message')
    expect(lastFrame()).toContain('Assistant')
  })

  it('renders system message correctly', () => {
    const { lastFrame } = render(
      <Message {...baseProps} role="system" />
    )
    expect(lastFrame()).toContain('Test message')
    expect(lastFrame()).toContain('System')
  })

  it('formats timestamp correctly', () => {
    const { lastFrame } = render(<Message {...baseProps} />)
    expect(lastFrame()).toMatch(/\d{2}:\d{2}:\d{2}/)
  })

  it('handles multiline content', () => {
    const multilineContent = 'Line 1\nLine 2\nLine 3'
    const { lastFrame } = render(
      <Message {...baseProps} content={multilineContent} />
    )
    expect(lastFrame()).toContain('Line 1')
    expect(lastFrame()).toContain('Line 2')
    expect(lastFrame()).toContain('Line 3')
  })

  it('handles empty content', () => {
    const { lastFrame } = render(
      <Message {...baseProps} content="" />
    )
    expect(lastFrame()).toBeDefined()
  })

  it('applies custom styling', () => {
    const { lastFrame } = render(
      <Message {...baseProps} style={{ color: 'red' }} />
    )
    expect(lastFrame()).toBeDefined()
  })
})

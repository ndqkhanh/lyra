import React from 'react'
import { render } from 'ink-testing-library'
import { ConversationView } from '../components/ConversationView'
import { ConversationViewProps } from '../types'

describe('ConversationView', () => {
  const baseProps: ConversationViewProps = {
    messages: [
      {
        role: 'user',
        content: 'Hello',
        timestamp: new Date('2024-01-01T00:00:00Z')
      },
      {
        role: 'assistant',
        content: 'Hi there!',
        timestamp: new Date('2024-01-01T00:00:01Z')
      }
    ]
  }

  it('renders all messages', () => {
    const { lastFrame } = render(<ConversationView {...baseProps} />)
    expect(lastFrame()).toContain('Hello')
    expect(lastFrame()).toContain('Hi there!')
  })

  it('renders messages in order', () => {
    const { lastFrame } = render(<ConversationView {...baseProps} />)
    const frame = lastFrame()!
    const helloIndex = frame.indexOf('Hello')
    const hiIndex = frame.indexOf('Hi there!')
    expect(helloIndex).toBeLessThan(hiIndex)
  })

  it('handles empty message list', () => {
    const { lastFrame } = render(
      <ConversationView {...baseProps} messages={[]} />
    )
    expect(lastFrame()).toBeDefined()
  })

  it('handles single message', () => {
    const { lastFrame } = render(
      <ConversationView
        {...baseProps}
        messages={[baseProps.messages[0]]}
      />
    )
    expect(lastFrame()).toContain('Hello')
    expect(lastFrame()).not.toContain('Hi there!')
  })

  it('scrolls to bottom on new message', () => {
    const { rerender, lastFrame } = render(
      <ConversationView {...baseProps} />
    )

    const newMessages = [
      ...baseProps.messages,
      {
        role: 'user',
        content: 'New message',
        timestamp: new Date('2024-01-01T00:00:02Z')
      }
    ]

    rerender(<ConversationView {...baseProps} messages={newMessages} />)
    expect(lastFrame()).toContain('New message')
  })

  it('handles long message list', () => {
    const longMessages = Array.from({ length: 100 }, (_, i) => ({
      role: i % 2 === 0 ? 'user' : 'assistant',
      content: `Message ${i}`,
      timestamp: new Date(`2024-01-01T00:00:${i.toString().padStart(2, '0')}Z`)
    }))

    const { lastFrame } = render(
      <ConversationView {...baseProps} messages={longMessages} />
    )
    expect(lastFrame()).toBeDefined()
  })
})

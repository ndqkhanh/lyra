import React from 'react'
import { render } from 'ink-testing-library'
import { InputArea } from '../components/InputArea'
import { InputAreaProps } from '../types'

describe('InputArea', () => {
  const mockOnSubmit = jest.fn()
  const baseProps: InputAreaProps = {
    onSubmit: mockOnSubmit,
    placeholder: 'Type a message...'
  }

  beforeEach(() => {
    mockOnSubmit.mockClear()
  })

  it('renders input area', () => {
    const { lastFrame } = render(<InputArea {...baseProps} />)
    expect(lastFrame()).toBeDefined()
  })

  it('shows placeholder text', () => {
    const { lastFrame } = render(<InputArea {...baseProps} />)
    expect(lastFrame()).toContain('Type a message...')
  })

  it('handles text input', () => {
    const { stdin, lastFrame } = render(<InputArea {...baseProps} />)
    stdin.write('Hello')
    expect(lastFrame()).toContain('Hello')
  })

  it('submits on Enter key', () => {
    const { stdin } = render(<InputArea {...baseProps} />)
    stdin.write('Test message')
    stdin.write('\r')
    expect(mockOnSubmit).toHaveBeenCalledWith('Test message')
  })

  it('clears input after submit', () => {
    const { stdin, lastFrame } = render(<InputArea {...baseProps} />)
    stdin.write('Test')
    stdin.write('\r')
    expect(lastFrame()).not.toContain('Test')
  })

  it('handles empty submit', () => {
    const { stdin } = render(<InputArea {...baseProps} />)
    stdin.write('\r')
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  it('handles backspace', () => {
    const { stdin, lastFrame } = render(<InputArea {...baseProps} />)
    stdin.write('Hello')
    stdin.write('\x7F') // Backspace
    expect(lastFrame()).toContain('Hell')
  })

  it('navigates history with up arrow', () => {
    const { stdin, lastFrame } = render(<InputArea {...baseProps} />)
    stdin.write('First')
    stdin.write('\r')
    stdin.write('Second')
    stdin.write('\r')
    stdin.write('\x1B[A') // Up arrow
    expect(lastFrame()).toContain('Second')
  })

  it('navigates history with down arrow', () => {
    const { stdin, lastFrame } = render(<InputArea {...baseProps} />)
    stdin.write('First')
    stdin.write('\r')
    stdin.write('\x1B[A') // Up arrow
    stdin.write('\x1B[B') // Down arrow
    expect(lastFrame()).not.toContain('First')
  })

  it('handles disabled state', () => {
    const { stdin } = render(<InputArea {...baseProps} disabled />)
    stdin.write('Test')
    stdin.write('\r')
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })
})

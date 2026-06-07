import React from 'react'
import { render } from 'ink-testing-library'
import { StatusBar } from '../components/StatusBar'
import { StatusBarProps } from '../types'

describe('StatusBar', () => {
  const baseProps: StatusBarProps = {
    status: 'idle',
    model: 'claude-opus-4',
    tokensUsed: 1000,
    tokensTotal: 200000
  }

  it('renders status correctly', () => {
    const { lastFrame } = render(<StatusBar {...baseProps} />)
    expect(lastFrame()).toContain('idle')
  })

  it('renders model name', () => {
    const { lastFrame } = render(<StatusBar {...baseProps} />)
    expect(lastFrame()).toContain('claude-opus-4')
  })

  it('renders token usage', () => {
    const { lastFrame } = render(<StatusBar {...baseProps} />)
    expect(lastFrame()).toContain('1000')
    expect(lastFrame()).toContain('200000')
  })

  it('calculates token percentage correctly', () => {
    const { lastFrame } = render(<StatusBar {...baseProps} />)
    expect(lastFrame()).toContain('0.5%')
  })

  it('shows thinking status', () => {
    const { lastFrame } = render(
      <StatusBar {...baseProps} status="thinking" />
    )
    expect(lastFrame()).toContain('thinking')
  })

  it('shows streaming status', () => {
    const { lastFrame } = render(
      <StatusBar {...baseProps} status="streaming" />
    )
    expect(lastFrame()).toContain('streaming')
  })

  it('shows error status', () => {
    const { lastFrame } = render(
      <StatusBar {...baseProps} status="error" />
    )
    expect(lastFrame()).toContain('error')
  })

  it('handles high token usage', () => {
    const { lastFrame } = render(
      <StatusBar {...baseProps} tokensUsed={180000} />
    )
    expect(lastFrame()).toContain('90.0%')
  })

  it('handles zero tokens', () => {
    const { lastFrame } = render(
      <StatusBar {...baseProps} tokensUsed={0} />
    )
    expect(lastFrame()).toContain('0.0%')
  })
})

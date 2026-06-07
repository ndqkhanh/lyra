import React, { useEffect } from 'react'
import { render as inkRender } from 'ink-testing-library'
import { useUIStore } from '@lyra/ui-core'
import { MockTransport } from './MockTransport'
import { App } from '../../App''

/**
 * Test harness that wires up a MockTransport and renders the full App.
 *
 * Usage:
 *   const harness = createTestHarness()
 *   await harness.transport.connect()
 *   harness.stdin.write('Hello world\r')
 *   await harness.transport.simulateFullResponse([...])
 *   const output = harness.lastFrame()
 */
export function createTestHarness() {
  const transport = new MockTransport()

  // Inject mock transport and create session BEFORE rendering App
  useUIStore.getState().setTransport(transport)
  useUIStore.getState().createSession('default')
  useUIStore.getState().setModelAndProvider('deepseek-v4-pro', 'anthropic')

  const result = inkRender(<App />)

  return {
    transport,
    ...result,
    /** Wait for the next render frame (for async state updates). */
    waitForRender: (ms = 50) => new Promise(r => setTimeout(r, ms)),
  }
}

/**
 * Minimal component wrapper for testing individual UI components in isolation.
 * Sets up the store with a session and optional transport.
 */
export function StoreProvider({
  sessionId = 'test',
  transport,
  children,
}: {
  sessionId?: string
  transport?: MockTransport
  children: React.ReactNode
}) {
  useEffect(() => {
    const store = useUIStore.getState()
    if (!store.sessions.has(sessionId)) {
      store.createSession(sessionId)
    }
    if (transport) {
      store.setTransport(transport)
    }
  }, [])

  return <>{children}</>
}

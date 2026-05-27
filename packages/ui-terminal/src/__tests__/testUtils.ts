import { render as inkRender } from 'ink-testing-library'
import { ReactElement } from 'react'

/**
 * Test utilities for Lyra UI components
 */

export function renderComponent(component: ReactElement) {
  return inkRender(component)
}

export function waitForText(instance: ReturnType<typeof inkRender>, text: string, timeout = 1000) {
  return new Promise<void>((resolve, reject) => {
    const startTime = Date.now()

    const check = () => {
      if (instance.lastFrame()?.includes(text)) {
        resolve()
      } else if (Date.now() - startTime > timeout) {
        reject(new Error(`Timeout waiting for text: ${text}`))
      } else {
        setTimeout(check, 50)
      }
    }

    check()
  })
}

export function getLastFrame(instance: ReturnType<typeof inkRender>): string {
  return instance.lastFrame() || ''
}

export function pressKey(instance: ReturnType<typeof inkRender>, key: string, options?: { ctrl?: boolean; shift?: boolean }) {
  instance.stdin.write(key)
  if (options?.ctrl) {
    // Simulate ctrl key
  }
  if (options?.shift) {
    // Simulate shift key
  }
}

export function cleanup(instance: ReturnType<typeof inkRender>) {
  instance.unmount()
}

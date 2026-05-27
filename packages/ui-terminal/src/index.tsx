#!/usr/bin/env node
import React from 'react'
import { render } from 'ink'
import { App } from './App'
import { logger } from './utils/logger'

if (!process.stdin.isTTY) {
  console.log('lyra-tui: no TTY')
  process.exit(0)
}

// Enter alternate screen, clear, hide cursor — MUST happen before render()
// so the first Ink frame lands inside the alt buffer, not the main screen.
// Equivalent to Hermes's useInsertionEffect in AlternateScreen.
const alternateScreenEntered = true

process.stdout.write('\x1B[?1049h\x1B[2J\x1B[H\x1B[?25l')

let waitUntilExit: ReturnType<typeof render>['waitUntilExit']

try {
  ;({ waitUntilExit } = render(<App />, {
    stdin: process.stdin,
    stdout: process.stdout,
    stderr: process.stderr,
    patchConsole: true,
  }))
} catch (err) {
  // Restore terminal on render failure
  if (alternateScreenEntered) {
    process.stdout.write('\x1B[?25h\x1B[?1049l')
  }
  logger.error('App', 'Render error:', (err as Error).message)
  process.exit(1)
}

waitUntilExit()
  .then(() => {
    process.stdout.write('\x1B[?25h\x1B[?1049l')
  })
  .catch((err) => {
    process.stdout.write('\x1B[?25h\x1B[?1049l')
    logger.error('App', 'Exit error:', err.message)
  })

#!/usr/bin/env node
import React from 'react'
import { render } from 'ink'
import { App } from './App'
import { logger } from './utils/logger'

// Clear screen and hide cursor
process.stdout.write('c')
process.stdout.write('[?25l')

const { waitUntilExit } = render(<App />, {
  stdin: process.stdin,
  stdout: process.stdout,
  stderr: process.stderr,
  patchConsole: false
})

waitUntilExit()
  .then(() => {
    process.stdout.write('[?25h')
  })
  .catch((err) => {
    process.stdout.write('[?25h')
    logger.error('App', 'Exit error:', err.message)
  })

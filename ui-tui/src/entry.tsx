#!/usr/bin/env -S node --max-old-space-size=8192 --expose-gc
import './lib/forceTruecolor.js'

import type { FrameEvent } from '@lyra/ink'

import { GatewayClient } from './gatewayClient.js'
import { setupGracefulExit } from './lib/gracefulExit.js'
import { formatBytes, type HeapDumpResult, performHeapDump } from './lib/memory.js'
import { type MemorySnapshot, startMemoryMonitor } from './lib/memoryMonitor.js'
import { openExternalUrl } from './lib/openExternalUrl.js'
import { resetTerminalModes } from './lib/terminalModes.js'

if (!process.stdin.isTTY) {
  console.log('lyra-tui: no TTY')
  process.exit(0)
}

resetTerminalModes()

process.stdout.write('\x1b[2J\x1b[H\x1b[3J')

const gw = new GatewayClient()

gw.start()

const dumpNotice = (snap: MemorySnapshot, dump: HeapDumpResult | null) =>
  `lyra-tui: ${snap.level} memory (${formatBytes(snap.heapUsed)}) — auto heap dump → ${dump?.heapPath ?? '(failed)'}\n`

setupGracefulExit({
  cleanups: [
    () => {
      resetTerminalModes()
      return gw.kill('graceful-exit-cleanup')
    }
  ],
  onError: (scope, err) => {
    const message = err instanceof Error ? `${err.name}: ${err.message}\n${err.stack ?? ''}` : String(err)
    process.stderr.write(`lyra-tui lifecycle ${scope}: ${message.slice(0, 2000)}\n`)
  },
  onSignal: signal => {
    resetTerminalModes()
    process.stderr.write(`lyra-tui lifecycle: received ${signal}\n`)
  }
})

const stopMemoryMonitor = startMemoryMonitor({
  onCritical: (snap, dump) => {
    resetTerminalModes()
    process.stderr.write(`lyra-tui lifecycle: memory critical exit heap=${formatBytes(snap.heapUsed)} rss=${formatBytes(snap.rss)}\n`)
    process.stderr.write(dumpNotice(snap, dump))
    process.stderr.write('lyra-tui: exiting to avoid OOM; restart to recover\n')
    process.exit(137)
  },
  onHigh: (snap, dump) => process.stderr.write(dumpNotice(snap, dump))
})

if (process.env.LYRA_HEAPDUMP_ON_START === '1') {
  void performHeapDump('manual')
}

process.on('beforeExit', () => stopMemoryMonitor())

const [ink, { App }, { logFrameEvent }, { trackFrame }] = await Promise.all([
  import('@lyra/ink'),
  import('./app.js'),
  import('./lib/perfPane.js'),
  import('./lib/fpsStore.js')
])

const onFrame =
  logFrameEvent || trackFrame
    ? (event: FrameEvent) => {
        logFrameEvent?.(event)
        trackFrame?.(event.durationMs)
      }
    : undefined

ink.render(<App gw={gw} />, {
  exitOnCtrlC: false,
  onFrame,
  onHyperlinkClick: url => {
    openExternalUrl(url)
  }
})

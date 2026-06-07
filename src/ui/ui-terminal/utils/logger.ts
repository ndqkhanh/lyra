import { appendFileSync, mkdirSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'

const LOG_DIR = join(homedir(), '.lyra', 'logs')

function ensureDir() {
  try { mkdirSync(LOG_DIR, { recursive: true }) } catch { /* ignore */ }
}

function timestamp(): string {
  return new Date().toISOString().replace('T', ' ').slice(0, 19)
}

function write(level: string, component: string, message: string, ...args: unknown[]) {
  ensureDir()
  const extra = args.length ? ' ' + args.map(a => {
    try { return JSON.stringify(a) } catch { return String(a) }
  }).join(' ') : ''
  const line = `[${timestamp()}] [${level}] [${component}] ${message}${extra}\n`
  try {
    appendFileSync(join(LOG_DIR, 'lyra-ui.log'), line)
  } catch {
    // Last resort: stderr for log failures
    process.stderr.write(line)
  }
}

export const logger = {
  info(component: string, message: string, ...args: unknown[]) {
    write('INFO', component, message, ...args)
  },
  warn(component: string, message: string, ...args: unknown[]) {
    write('WARN', component, message, ...args)
  },
  error(component: string, message: string, ...args: unknown[]) {
    write('ERROR', component, message, ...args)
  },
  debug(component: string, message: string, ...args: unknown[]) {
    if (process.env['LYRA_DEBUG']) {
      write('DEBUG', component, message, ...args)
    }
  }
}

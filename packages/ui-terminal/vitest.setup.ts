import { vi } from 'vitest'

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  error: vi.fn(),
  warn: vi.fn(),
  log: vi.fn(),
  debug: vi.fn(),
} as any

// Mock process.stdout for Ink tests — ensure columns is set
Object.defineProperty(process.stdout, 'isTTY', { value: true, writable: true })
process.stdout.columns = 120
process.stdout.rows = 24

import '@testing-library/jest-dom'

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  error: jest.fn(),
  warn: jest.fn(),
  log: jest.fn(),
  debug: jest.fn()
}

// Mock process.stdout for Ink tests
if (!process.stdout.isTTY) {
  process.stdout.isTTY = true
  process.stdout.columns = 80
  process.stdout.rows = 24
}

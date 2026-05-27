import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/__tests__/**/*.test.{ts,tsx}'],
    setupFiles: ['./vitest.setup.ts'],
  },
  resolve: {
    alias: {
      '@lyra/ui-core': new URL('../ui-core/src', import.meta.url).pathname,
      '@lyra/ui-transport': new URL('../ui-transport/src', import.meta.url).pathname,
      'ink-testing-library': new URL('../../node_modules/ink-testing-library/build/index.js', import.meta.url).pathname,
    },
  },
})

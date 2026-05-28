import { loadConfig, config, type LyraConfig } from '../config'

describe('loadConfig', () => {
  const originalEnv = process.env

  beforeEach(() => {
    vi.resetModules()
    process.env = { ...originalEnv }
    // Clear Lyra-specific env vars
    delete process.env.LYRA_API_URL
    delete process.env.LYRA_WS_URL
    delete process.env.LYRA_TIMEOUT
    delete process.env.LYRA_MAX_RETRIES
    delete process.env.LYRA_RETRY_DELAY
    delete process.env.LYRA_BACKOFF_MULTIPLIER
    delete process.env.LYRA_PROVIDER_FETCH_INTERVAL
    delete process.env.LYRA_SETTINGS_FETCH_INTERVAL
  })

  afterEach(() => {
    process.env = originalEnv
  })

  it('returns default config', () => {
    const cfg = loadConfig()
    expect(cfg.apiUrl).toBe('http://localhost:3737')
    expect(cfg.wsUrl).toBe('ws://localhost:3737')
    expect(cfg.timeout).toBe(30000)
  })

  it('has default retry config', () => {
    const cfg = loadConfig()
    expect(cfg.retryConfig.maxRetries).toBe(10)
    expect(cfg.retryConfig.initialDelay).toBe(500)
    expect(cfg.retryConfig.backoffMultiplier).toBe(2)
  })

  it('has default fetch intervals', () => {
    const cfg = loadConfig()
    expect(cfg.fetchIntervals.providers).toBe(2000)
    expect(cfg.fetchIntervals.settings).toBe(1000)
  })

  it('reads LYRA_API_URL from env', () => {
    process.env.LYRA_API_URL = 'https://api.example.com'
    const cfg = loadConfig()
    expect(cfg.apiUrl).toBe('https://api.example.com')
  })

  it('reads LYRA_WS_URL from env', () => {
    process.env.LYRA_WS_URL = 'wss://ws.example.com'
    const cfg = loadConfig()
    expect(cfg.wsUrl).toBe('wss://ws.example.com')
  })

  it('reads LYRA_TIMEOUT from env', () => {
    process.env.LYRA_TIMEOUT = '60000'
    const cfg = loadConfig()
    expect(cfg.timeout).toBe(60000)
  })

  it('reads retry config from env', () => {
    process.env.LYRA_MAX_RETRIES = '5'
    process.env.LYRA_RETRY_DELAY = '1000'
    process.env.LYRA_BACKOFF_MULTIPLIER = '3'
    const cfg = loadConfig()
    expect(cfg.retryConfig.maxRetries).toBe(5)
    expect(cfg.retryConfig.initialDelay).toBe(1000)
    expect(cfg.retryConfig.backoffMultiplier).toBe(3)
  })

  it('reads fetch intervals from env', () => {
    process.env.LYRA_PROVIDER_FETCH_INTERVAL = '5000'
    process.env.LYRA_SETTINGS_FETCH_INTERVAL = '3000'
    const cfg = loadConfig()
    expect(cfg.fetchIntervals.providers).toBe(5000)
    expect(cfg.fetchIntervals.settings).toBe(3000)
  })
})

describe('config singleton', () => {
  it('is frozen/loaded at import time', () => {
    expect(config).toBeDefined()
    expect(typeof config.apiUrl).toBe('string')
    expect(typeof config.timeout).toBe('number')
    expect(config.retryConfig).toBeDefined()
  })
})

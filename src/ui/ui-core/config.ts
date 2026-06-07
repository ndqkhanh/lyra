/**
 * Lyra Configuration
 *
 * Centralized configuration for API URLs, timeouts, and other settings.
 * All values can be overridden via environment variables.
 */

export interface LyraConfig {
  apiUrl: string
  wsUrl: string
  timeout: number
  retryConfig: {
    maxRetries: number
    initialDelay: number
    backoffMultiplier: number
  }
  fetchIntervals: {
    providers: number
    settings: number
  }
}

export function loadConfig(): LyraConfig {
  const apiUrl = process.env.LYRA_API_URL || 'http://localhost:3737'
  const wsUrl = process.env.LYRA_WS_URL || 'ws://localhost:3737'

  return {
    apiUrl,
    wsUrl,
    timeout: parseInt(process.env.LYRA_TIMEOUT || '30000', 10),
    retryConfig: {
      maxRetries: parseInt(process.env.LYRA_MAX_RETRIES || '10', 10),
      initialDelay: parseInt(process.env.LYRA_RETRY_DELAY || '500', 10),
      backoffMultiplier: parseInt(process.env.LYRA_BACKOFF_MULTIPLIER || '2', 10)
    },
    fetchIntervals: {
      providers: parseInt(process.env.LYRA_PROVIDER_FETCH_INTERVAL || '2000', 10),
      settings: parseInt(process.env.LYRA_SETTINGS_FETCH_INTERVAL || '1000', 10)
    }
  }
}

export const config = loadConfig()

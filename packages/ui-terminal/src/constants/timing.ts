/**
 * Timing constants for the application
 * Centralized to avoid magic numbers throughout the codebase
 */

/**
 * Retry configuration for connection attempts
 */
export const RETRY_CONFIG = {
  /** Maximum number of retry attempts */
  MAX_RETRIES: 10,
  /** Initial delay between retries in milliseconds */
  INITIAL_DELAY_MS: 500,
  /** Backoff multiplier for exponential backoff */
  BACKOFF_MULTIPLIER: 2,
} as const

/**
 * Fetch intervals for polling operations
 */
export const FETCH_INTERVALS = {
  /** Interval for fetching providers in milliseconds */
  PROVIDERS_MS: 2000,
  /** Interval for fetching settings in milliseconds */
  SETTINGS_MS: 1000,
} as const

/**
 * UI interaction timing
 */
export const UI_TIMING = {
  /** Debounce delay for submit button to prevent double-firing in milliseconds */
  SUBMIT_DEBOUNCE_MS: 500,
  /** Face animation tick interval in milliseconds */
  FACE_TICK_MS: 2500,
  /** Session duration update interval in milliseconds */
  SESSION_DURATION_UPDATE_MS: 1000,
  /** Streaming elapsed time update interval in milliseconds */
  STREAMING_ELAPSED_UPDATE_MS: 1000,
} as const

/**
 * Context window configuration
 */
export const CONTEXT_CONFIG = {
  /** Total context window size in tokens */
  CONTEXT_WINDOW_TOKENS: 200_000,
} as const

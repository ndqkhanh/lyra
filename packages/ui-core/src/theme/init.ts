/**
 * Auto Theme Detection Integration
 *
 * Provides a simple function to detect and apply the appropriate theme on startup.
 * Call this once when initializing the UI.
 */

import { detectTerminalThemeSync, getRecommendedThemeId } from './autoDetect'
import type { UIStore } from '../state/store'
import { logger } from '../utils/logger'

/**
 * Initialize theme based on terminal detection.
 * Call this once on app startup before rendering.
 *
 * @param store - The UI store instance
 * @param force - Force detection even if theme is already set
 * @returns The detected theme ID
 */
export function initializeTheme(store: UIStore, force = false): string {
  // Skip if theme is already set (unless forced)
  if (!force && store.activeThemeId && store.activeThemeId !== 'dracula') {
    return store.activeThemeId
  }

  // Detect terminal theme
  const detection = detectTerminalThemeSync()
  const themeId = getRecommendedThemeId(detection.variant)

  // Apply theme
  store.setActiveTheme(themeId)

  // Log detection result
  logger.info('Theme', `Auto-detected ${detection.variant} theme via ${detection.method} (confidence: ${detection.confidence})`)
  logger.info('Theme', `Applied theme: ${themeId}`)

  return themeId
}

/**
 * Async version that uses all 5 detection methods.
 * Provides higher accuracy but takes up to 200ms.
 *
 * @param store - The UI store instance
 * @param force - Force detection even if theme is already set
 * @returns The detected theme ID
 */
export async function initializeThemeAsync(store: UIStore, force = false): Promise<string> {
  // Skip if theme is already set (unless forced)
  if (!force && store.activeThemeId && store.activeThemeId !== 'dracula') {
    return store.activeThemeId
  }

  // Import async detection
  const { detectTerminalTheme } = await import('./autoDetect')

  // Detect terminal theme (async)
  const detection = await detectTerminalTheme()
  const themeId = getRecommendedThemeId(detection.variant)

  // Apply theme
  store.setActiveTheme(themeId)

  // Log detection result
  logger.info('Theme', `Auto-detected ${detection.variant} theme via ${detection.method} (confidence: ${detection.confidence})`)
  if (detection.details) {
    logger.info('Theme', `Details: ${detection.details}`)
  }
  logger.info('Theme', `Applied theme: ${themeId}`)

  return themeId
}

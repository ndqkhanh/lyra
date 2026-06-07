/**
 * Theme system for Lyra UI
 * Exports colors, symbols, and Hermes-style Theme
 */

import { colors, deriveColors, useThemeColors, type ColorName, type ColorSet } from './colors'
import { symbols, type SymbolName } from './symbols'
import { LYRA_THEME, LYRA_BRAND, type Theme, type ThemeBrand, type ThemeColors } from './theme'
import {
  THEME_PRESETS,
  THEME_ORDER,
  getThemePreset,
  getDefaultTheme,
  type ThemePreset,
  type ThemePalette,
} from './presets'
import {
  detectTerminalTheme,
  detectTerminalThemeSync,
  getRecommendedThemeId,
  type ThemeVariant,
  type ThemeDetectionResult,
} from './autoDetect'
import { initializeTheme, initializeThemeAsync } from './init'

export {
  colors,
  symbols,
  LYRA_THEME,
  LYRA_BRAND,
  THEME_PRESETS,
  THEME_ORDER,
  getThemePreset,
  getDefaultTheme,
  deriveColors,
  useThemeColors,
  detectTerminalTheme,
  detectTerminalThemeSync,
  getRecommendedThemeId,
  initializeTheme,
  initializeThemeAsync,
}
export type {
  ColorName,
  ColorSet,
  SymbolName,
  Theme,
  ThemeBrand,
  ThemeColors,
  ThemePreset,
  ThemePalette,
  ThemeVariant,
  ThemeDetectionResult,
}

// Helper function to get color by name
export function getColor(name: ColorName): string {
  return colors[name]
}

// Helper function to get symbol by name
export function getSymbol(name: SymbolName): string | readonly string[] {
  return symbols[name]
}

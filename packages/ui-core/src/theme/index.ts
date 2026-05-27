/**
 * Theme system for Lyra UI
 * Exports colors, symbols, and Hermes-style Theme
 */

import { colors, type ColorName } from './colors'
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

export { colors, symbols, LYRA_THEME, LYRA_BRAND, THEME_PRESETS, THEME_ORDER, getThemePreset, getDefaultTheme }
export type { ColorName, SymbolName, Theme, ThemeBrand, ThemeColors, ThemePreset, ThemePalette }

// Helper function to get color by name
export function getColor(name: ColorName): string {
  return colors[name]
}

// Helper function to get symbol by name
export function getSymbol(name: SymbolName): string | readonly string[] {
  return symbols[name]
}

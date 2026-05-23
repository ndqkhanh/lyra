/**
 * Theme system for Lyra UI
 * Exports colors and symbols
 */

import { colors, type ColorName } from './colors'
import { symbols, type SymbolName } from './symbols'

export { colors, symbols }
export type { ColorName, SymbolName }

// Helper function to get color by name
export function getColor(name: ColorName): string {
  return colors[name]
}

// Helper function to get symbol by name
export function getSymbol(name: SymbolName): string | readonly string[] {
  return symbols[name]
}

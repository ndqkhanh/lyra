// Types
export * from './types'

// State
export { useUIStore } from './state/store'
export type { UIStore } from './state/store'

// Observability & State Machines
export { observability, ObservabilityContext } from './observability'
export type { ObservabilityEvent, ObservabilityEventType, EventHandler } from './observability'
export { IndicatorStateMachine } from './stateMachine'
export type { IndicatorState, IndicatorContext, StateTransition } from './stateMachine'

// Utils
export { toRenderItems, applyDisplayPolicy, partitionRenderItems } from './utils/rendering'
export { partitionForRendering, shouldRerender, optimizeRenderItems } from './utils/renderingPipeline'
export type { RenderPartition } from './utils/renderingPipeline'

// Theme
export { colors, type ColorSet, deriveColors, useThemeColors } from './theme/colors'
export { symbols, getColor, getSymbol, LYRA_THEME, LYRA_BRAND } from './theme'
export type { ColorName, SymbolName, Theme, ThemeBrand, ThemeColors } from './theme'
export { THEME_PRESETS, THEME_ORDER, getThemePreset, getDefaultTheme } from './theme/presets'
export type { ThemePreset, ThemePalette } from './theme/presets'
export { buildSkinFromPreset, DEFAULT_WAITING_FACES, DEFAULT_THINKING_FACES, DEFAULT_THINKING_VERBS } from './theme/skin'
export type { SkinConfig, SkinColors, SkinBranding, SpinnerConfig } from './theme/skin'

// Streaming
export * from './streaming'

// Skills
export * from './skills'

// Plugins
export * from './plugins'

// Orchestration
export * from './orchestration'

// Monitoring
export * from './monitoring'

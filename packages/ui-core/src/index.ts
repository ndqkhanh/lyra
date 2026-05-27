// Types
export * from './types'

// State
export { useUIStore } from './state/store'

// Observability & State Machines
export { observability, ObservabilityContext } from './observability'
export type { ObservabilityEvent, ObservabilityEventType, EventHandler } from './observability'
export { IndicatorStateMachine } from './stateMachine'
export type { IndicatorState, IndicatorContext, StateTransition } from './stateMachine'

// Utils
export { toRenderItems, applyDisplayPolicy, partitionRenderItems } from './utils/rendering'
export { partitionForRendering, shouldRerender, optimizeRenderItems } from './utils/renderingPipeline'
export type { RenderPartition } from './utils/renderingPipeline'
export { getDisplayPolicy, applyPolicy } from './utils/displayPolicy'
export type { DisplayPolicy } from './utils/displayPolicy'
export { MinimalDisplayPolicy, StandardDisplayPolicy, DebugDisplayPolicy } from './utils/displayPolicy'

// Theme
export { colors, symbols, getColor, getSymbol } from './theme'
export type { ColorName, SymbolName } from './theme'

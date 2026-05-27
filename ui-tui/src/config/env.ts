import type { MouseTrackingMode } from '@lyra/ink'
import { isTermuxTuiMode } from '../lib/termux.js'

const truthy = (v?: string) => /^(?:1|true|yes|on)$/i.test((v ?? '').trim())
const falsy = (v?: string) => /^(?:0|false|no|off)$/i.test((v ?? '').trim())

const parseToggle = (v?: string): boolean | null => {
  const raw = (v ?? '').trim()
  if (!raw) return null
  if (truthy(raw)) return true
  if (falsy(raw)) return false
  return null
}

export const TERMUX_TUI_MODE = isTermuxTuiMode()

export const STARTUP_RESUME_ID = (process.env.LYRA_TUI_RESUME ?? '').trim()
export const STARTUP_QUERY = (process.env.LYRA_TUI_QUERY ?? '').trim()
export const STARTUP_IMAGE = (process.env.LYRA_TUI_IMAGE ?? '').trim()

const mouseTrackingOverride = parseToggle(process.env.LYRA_TUI_MOUSE_TRACKING)
const mouseTrackingDisabledLegacy = truthy(process.env.LYRA_TUI_DISABLE_MOUSE)
const resolvedBootMouseEnabled =
  mouseTrackingOverride ?? !mouseTrackingDisabledLegacy
export const MOUSE_TRACKING: MouseTrackingMode = resolvedBootMouseEnabled ? 'all' : 'off'

export const NO_CONFIRM_DESTRUCTIVE = truthy(process.env.LYRA_TUI_NO_CONFIRM)

const inlineOverride = parseToggle(process.env.LYRA_TUI_INLINE)
export const INLINE_MODE = inlineOverride ?? false

export const SHOW_FPS = truthy(process.env.LYRA_TUI_FPS)

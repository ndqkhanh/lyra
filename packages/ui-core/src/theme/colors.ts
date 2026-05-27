/**
 * Color palette for Lyra UI — theme-driven via deriveColors().
 * The static `colors` export is the Dracula default for backward compat.
 * React components should use `useThemeColors()` for live theme switching.
 */

import { useMemo } from 'react'
import { useUIStore } from '../state/store'
import type { ThemePalette } from './presets'
import { getThemePreset, getDefaultTheme } from './presets'

export interface ColorSet {
  gold: string; amber: string; bronze: string; cornsilk: string; dim: string
  label: string; shellDollar: string
  completionBg: string; completionCurrentBg: string; selectionBg: string
  statusBg: string; statusFg: string; statusGood: string; statusWarn: string
  statusBad: string; statusCritical: string
  userPrompt: string; userText: string; assistant: string; thinking: string
  backgroundTask: string; system: string
  success: string; error: string; warning: string; info: string
  toolName: string; toolSuccess: string; toolError: string
  filePath: string; lineNumber: string; code: string
  codeAdded: string; codeRemoved: string
  timestamp: string; muted: string; emptyState: string; separator: string; border: string
  background: string; backgroundAlt: string
  keyword: string; string: string; number: string; comment: string
  function: string; variable: string
  statusIdle: string; statusActive: string; statusError: string
  modeMinimal: string; modeStandard: string; modeDebug: string
  permission: string
  commandSuccess: string; commandError: string; commandStdout: string; commandStderr: string; commandPrompt: string
  codeKeyword: string; codeString: string; codeNumber: string; codeComment: string
  codeFunction: string; codeVariable: string; codeOperator: string; codeBackground: string
  diffAdded: string; diffAddedBg: string; diffRemoved: string; diffRemovedBg: string; diffContext: string
  markdownHeading: string; markdownBold: string; markdownItalic: string
  markdownCode: string; markdownCodeBlock: string; markdownLink: string
  markdownQuote: string; markdownList: string
  agentThinking: string; agentComposing: string; agentToolRunning: string
  agentStreaming: string; agentIdle: string; agentError: string
  shortcutKey: string; shortcutDescription: string; shortcutSeparator: string
  errorCritical: string; errorHigh: string; errorMedium: string; errorLow: string; errorInfo: string
  collapsibleExpanded: string; collapsibleCollapsed: string; collapsibleBorder: string
  statusPending: string; statusRunning: string; statusSuccess: string
  statusCancelled: string; statusSkipped: string
}

/** Derive full ColorSet from a ThemePalette. */
export function deriveColors(palette: ThemePalette): ColorSet {
  return {
    gold: palette.accent,
    amber: palette.yellow,
    bronze: palette.orange,
    cornsilk: palette.foreground,
    dim: palette.subtext0,
    label: palette.accent,
    shellDollar: palette.blue,
    completionBg: palette.selection,
    completionCurrentBg: palette.surface2,
    selectionBg: palette.surface1,
    statusBg: palette.statusBg,
    statusFg: palette.statusFg,
    statusGood: palette.statusSuccess,
    statusWarn: palette.statusWarning,
    statusBad: palette.orange,
    statusCritical: palette.statusError,
    userPrompt: palette.foreground,
    userText: palette.foreground,
    assistant: palette.text,
    thinking: palette.yellow,
    backgroundTask: palette.purple,
    system: palette.subtext0,
    success: palette.green,
    error: palette.red,
    warning: palette.yellow,
    info: palette.blue,
    toolName: palette.purple,
    toolSuccess: palette.green,
    toolError: palette.red,
    filePath: palette.cyan,
    lineNumber: palette.subtext0,
    code: palette.text,
    codeAdded: palette.green,
    codeRemoved: palette.red,
    timestamp: palette.subtext0,
    muted: palette.subtext1,
    emptyState: palette.cyan,
    separator: palette.surface1,
    border: palette.surface1,
    background: palette.background,
    backgroundAlt: palette.surface0,
    keyword: palette.purple,
    string: palette.green,
    number: palette.purple,
    comment: palette.comment,
    function: palette.blue,
    variable: palette.text,
    statusIdle: palette.comment,
    statusActive: palette.green,
    statusError: palette.red,
    modeMinimal: palette.cyan,
    modeStandard: palette.green,
    modeDebug: palette.orange,
    permission: palette.red,
    commandSuccess: palette.green,
    commandError: palette.red,
    commandStdout: palette.text,
    commandStderr: palette.orange,
    commandPrompt: palette.cyan,
    codeKeyword: palette.purple,
    codeString: palette.green,
    codeNumber: palette.purple,
    codeComment: palette.comment,
    codeFunction: palette.blue,
    codeVariable: palette.text,
    codeOperator: palette.purple,
    codeBackground: palette.background,
    diffAdded: palette.green,
    diffAddedBg: palette.surface0,
    diffRemoved: palette.red,
    diffRemovedBg: palette.surface0,
    diffContext: palette.comment,
    markdownHeading: palette.purple,
    markdownBold: palette.text,
    markdownItalic: palette.subtext1,
    markdownCode: palette.yellow,
    markdownCodeBlock: palette.text,
    markdownLink: palette.cyan,
    markdownQuote: palette.comment,
    markdownList: palette.green,
    agentThinking: palette.yellow,
    agentComposing: palette.purple,
    agentToolRunning: palette.cyan,
    agentStreaming: palette.green,
    agentIdle: palette.comment,
    agentError: palette.red,
    shortcutKey: palette.purple,
    shortcutDescription: palette.comment,
    shortcutSeparator: palette.surface1,
    errorCritical: palette.red,
    errorHigh: palette.red,
    errorMedium: palette.orange,
    errorLow: palette.yellow,
    errorInfo: palette.cyan,
    collapsibleExpanded: palette.green,
    collapsibleCollapsed: palette.comment,
    collapsibleBorder: palette.surface1,
    statusPending: palette.orange,
    statusRunning: palette.cyan,
    statusSuccess: palette.green,
    statusCancelled: palette.comment,
    statusSkipped: palette.purple,
  }
}

/** React hook: returns theme-driven colors that update when activeThemeId changes. */
export function useThemeColors(): ColorSet {
  const activeThemeId = useUIStore(state => state.activeThemeId)
  const preset = useMemo(() => {
    const p = getThemePreset(activeThemeId)
    return p ?? getDefaultTheme()
  }, [activeThemeId])
  return useMemo(() => deriveColors(preset.palette), [preset])
}

/** Static colors — Dracula default for backward compat and non-React contexts. */
export const colors: ColorSet = deriveColors(getDefaultTheme().palette)

export type ColorName = keyof ColorSet

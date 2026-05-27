/**
 * Hermes-style Theme system for Lyra UI.
 * Mirrors HermesAgent's theme.ts — same color keys, same brand shape.
 */

export interface ThemeColors {
  gold: string
  amber: string
  bronze: string
  cornsilk: string
  dim: string
  completionBg: string
  completionCurrentBg: string

  label: string
  ok: string
  error: string
  warn: string

  prompt: string
  sessionLabel: string
  sessionBorder: string

  statusBg: string
  statusFg: string
  statusGood: string
  statusWarn: string
  statusBad: string
  statusCritical: string
  selectionBg: string

  diffAdded: string
  diffRemoved: string
  diffAddedWord: string
  diffRemovedWord: string

  shellDollar: string
}

export interface ThemeBrand {
  name: string
  icon: string
  prompt: string
  welcome: string
  goodbye: string
  tool: string
  helpHeader: string
}

export interface Theme {
  color: ThemeColors
  brand: ThemeBrand
  bannerLogo: string
  bannerHero: string
}

export const LYRA_BRAND: ThemeBrand = {
  name: 'Lyra',
  icon: '⚕',
  prompt: '❯',
  welcome: 'Type your message or /help for commands.',
  goodbye: 'Goodbye! ⚕',
  tool: '┊',
  helpHeader: '(^_^)? Commands',
}

export const LYRA_THEME: Theme = {
  color: {
    gold: '#FFD700',
    amber: '#FFBF00',
    bronze: '#CD7F32',
    cornsilk: '#FFF8DC',
    dim: '#CC9B1F',
    completionBg: '#FFFFFF',
    completionCurrentBg: '#f5e6a3',

    label: '#DAA520',
    ok: '#4caf50',
    error: '#ef5350',
    warn: '#ffa726',

    prompt: '#FFF8DC',
    sessionLabel: '#CC9B1F',
    sessionBorder: '#CC9B1F',

    statusBg: '#1a1a2e',
    statusFg: '#C0C0C0',
    statusGood: '#8FBC8F',
    statusWarn: '#FFD700',
    statusBad: '#FF8C00',
    statusCritical: '#FF6B6B',
    selectionBg: '#3a3a55',

    diffAdded: 'rgb(220,255,220)',
    diffRemoved: 'rgb(255,220,220)',
    diffAddedWord: 'rgb(36,138,61)',
    diffRemovedWord: 'rgb(207,34,46)',
    shellDollar: '#4dabf7',
  },
  brand: LYRA_BRAND,
  bannerLogo: '',
  bannerHero: '',
}

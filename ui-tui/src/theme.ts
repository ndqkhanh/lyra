import type { Color } from '@lyra/ink'

export interface ThemeColors {
  // ── Core UI ──
  primary: Color
  accent: Color
  border: Color
  text: Color
  muted: Color
  completionBg: Color
  completionCurrentBg: Color
  completionMetaBg: Color
  completionMetaCurrentBg: Color

  // ── Labels & Semantic ──
  label: Color
  ok: Color
  error: Color
  warn: Color

  // ── Prompt & Session ──
  prompt: Color
  sessionLabel: Color
  sessionBorder: Color

  // ── Status Bar ──
  statusBg: Color
  statusFg: Color
  statusGood: Color
  statusWarn: Color
  statusBad: Color
  statusCritical: Color
  selectionBg: Color

  // ── Diffs ──
  diffAdded: Color
  diffRemoved: Color
  diffAddedWord: Color
  diffRemovedWord: Color

  // ── Shell ──
  shellDollar: Color

  // ── Functional Agent Coloring ──
  thinking: Color
  tool: Color
  search: Color
  synthesize: Color
  skill: Color
  agent: Color
  code: Color
  shell: Color
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

// ── Color math ───────────────────────────────────────────────────────

function parseHex(h: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(h)
  if (!m) return null
  const n = parseInt(m[1]!, 16)
  return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff]
}

function mix(a: string, b: string, t: number): Color {
  const pa = parseHex(a)
  const pb = parseHex(b)
  if (!pa || !pb) return a as Color
  const lerp = (i: 0 | 1 | 2) => Math.round(pa[i] + (pb[i] - pa[i]) * t)
  return ('#' + ((1 << 24) | (lerp(0) << 16) | (lerp(1) << 8) | lerp(2)).toString(16).slice(1)) as Color
}

const XTERM_6_LEVELS = [0, 95, 135, 175, 215, 255] as const
const ANSI_LIGHT_MAX_LUMINANCE = 0.72
const ANSI_LIGHT_TARGET_LUMINANCE = 0.34
const ANSI_LIGHT_MIN_SATURATION = 0.22
const ANSI_MUTED_BUCKET = 245

const ANSI_NORMALIZED_FOREGROUNDS: readonly (keyof ThemeColors)[] = [
  'text', 'label', 'ok', 'error', 'warn', 'prompt',
  'statusFg', 'statusGood', 'statusWarn', 'statusBad', 'statusCritical', 'shellDollar',
  'thinking', 'tool', 'search', 'synthesize', 'skill', 'agent', 'code', 'shell'
]

const ANSI_MUTED_FOREGROUNDS: readonly (keyof ThemeColors)[] = ['muted', 'sessionLabel', 'sessionBorder']

function xtermEightBitRgb(colorNumber: number): [number, number, number] {
  if (colorNumber >= 232) {
    const value = 8 + (colorNumber - 232) * 10
    return [value, value, value]
  }
  if (colorNumber >= 16) {
    const offset = colorNumber - 16
    return [
      XTERM_6_LEVELS[Math.floor(offset / 36) % 6]!,
      XTERM_6_LEVELS[Math.floor(offset / 6) % 6]!,
      XTERM_6_LEVELS[offset % 6]!
    ]
  }
  return [0, 0, 0]
}

function channelLuminance(value: number): number {
  const normalized = value / 255
  return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4
}

function relativeLuminance(red: number, green: number, blue: number): number {
  return 0.2126 * channelLuminance(red) + 0.7152 * channelLuminance(green) + 0.0722 * channelLuminance(blue)
}

function rgbToHsl(red: number, green: number, blue: number): [number, number, number] {
  const rn = red / 255
  const gn = green / 255
  const bn = blue / 255
  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  const lightness = (max + min) / 2
  if (max === min) return [0, 0, lightness]
  const delta = max - min
  const saturation = lightness > 0.5 ? delta / (2 - max - min) : delta / (max + min)
  const hue =
    max === rn ? (gn - bn) / delta + (gn < bn ? 6 : 0)
    : max === gn ? (bn - rn) / delta + 2
    : (rn - gn) / delta + 4
  return [hue / 6, saturation, lightness]
}

function circularDistance(a: number, b: number): number {
  const distance = Math.abs(a - b)
  return Math.min(distance, 1 - distance)
}

function richEightBitColorNumber(red: number, green: number, blue: number): number {
  const [, saturation, lightness] = rgbToHsl(red, green, blue)
  if (saturation < 0.15) {
    const gray = Math.round(lightness * 25)
    return gray === 0 ? 16 : gray === 25 ? 231 : 231 + gray
  }
  const sixRed = red < 95 ? red / 95 : 1 + (red - 95) / 40
  const sixGreen = green < 95 ? green / 95 : 1 + (green - 95) / 40
  const sixBlue = blue < 95 ? blue / 95 : 1 + (blue - 95) / 40
  return 16 + 36 * Math.round(sixRed) + 6 * Math.round(sixGreen) + Math.round(sixBlue)
}

function bestReadableAnsiColor(red: number, green: number, blue: number): number {
  const [hue, saturation, lightness] = rgbToHsl(red, green, blue)
  let bestColor = richEightBitColorNumber(red, green, blue)
  let bestScore = Number.POSITIVE_INFINITY
  for (let colorNumber = 16; colorNumber <= 255; colorNumber += 1) {
    const [candidateRed, candidateGreen, candidateBlue] = xtermEightBitRgb(colorNumber)
    const candidateLuminance = relativeLuminance(candidateRed, candidateGreen, candidateBlue)
    if (candidateLuminance > ANSI_LIGHT_MAX_LUMINANCE) continue
    const [candidateHue, candidateSaturation, candidateLightness] = rgbToHsl(candidateRed, candidateGreen, candidateBlue)
    const saturationFloorPenalty =
      candidateSaturation < ANSI_LIGHT_MIN_SATURATION ? (ANSI_LIGHT_MIN_SATURATION - candidateSaturation) * 3 : 0
    const score =
      circularDistance(candidateHue, hue) * 4 +
      Math.abs(candidateSaturation - Math.max(ANSI_LIGHT_MIN_SATURATION, saturation)) * 0.8 +
      Math.abs(candidateLightness - Math.min(lightness, ANSI_LIGHT_TARGET_LUMINANCE)) * 2 +
      saturationFloorPenalty
    if (score < bestScore) {
      bestColor = colorNumber
      bestScore = score
    }
  }
  return bestColor
}

function normalizeAnsiForeground(color: string): Color {
  const rgb = parseHex(color)
  if (!rgb) return color as Color
  const richAnsi = richEightBitColorNumber(rgb[0], rgb[1], rgb[2])
  const richRgb = xtermEightBitRgb(richAnsi)
  const ansi = relativeLuminance(richRgb[0], richRgb[1], richRgb[2]) > ANSI_LIGHT_MAX_LUMINANCE
    ? bestReadableAnsiColor(rgb[0], rgb[1], rgb[2])
    : richAnsi
  return `ansi256(${ansi})` as Color
}

// ── Lyra Brand ───────────────────────────────────────────────────────

const BRAND: ThemeBrand = {
  name: 'Lyra',
  icon: '✦',
  prompt: '❯',
  welcome: '✦ LYRA — Superintelligent Deep Research AI Agent. Type /help for commands.',
  goodbye: 'Goodbye! ✦',
  tool: '┊',
  helpHeader: '✦ Lyra Commands'
}

const cleanPromptSymbol = (s: string | undefined, fallback: string) => {
  const cleaned = String(s ?? '').replace(/\s+/g, ' ').trim()
  return cleaned || fallback
}

// ── Claude Code-Inspired Warm Amber/Orange Color Scheme ──────────────
//
// Claude Code uses warm amber/orange tones with a dark background,
// reminiscent of a cozy terminal.  Primary = warm amber (#FFA726),
// accent = deeper orange (#FF8C00), with warm grays for muted text.
//
// Layout: primary/accent/border form a warm gradient from bright amber
// through orange to deep brown, while text is a warm off-white and
// muted elements use warm grays.

export const DARK_THEME: Theme = {
  color: {
    // Warm amber → orange → brown gradient for borders and accents
    primary: '#FFA726',    // warm amber — logo, headings, key UI
    accent: '#FF8C00',     // deep orange — collapsible toggles, highlights
    border: '#BF7A3F',     // warm brown — panel borders, separators

    // Warm off-white text on dark backgrounds
    text: '#FFF8E1',       // warm white — primary content
    muted: '#BCAAA4',      // warm gray — secondary text, dim elements

    // Completion menu — warm dark backgrounds
    completionBg: '#1E1A16',
    completionCurrentBg: '#3D2E1F',
    completionMetaBg: '#1E1A16',
    completionMetaCurrentBg: '#3D2E1F',

    // Labels and semantic colors
    label: '#FFB74D',      // light orange — field labels
    ok: '#69F0AE',         // green — success
    error: '#FF5252',      // red — errors
    warn: '#FFD740',       // amber — warnings

    // Prompt symbol — bright warm
    prompt: '#FFB74D',
    sessionLabel: '#BCAAA4',
    sessionBorder: '#BCAAA4',

    // Status bar — warm dark tones
    statusBg: '#1E1A16',
    statusFg: '#D7CCC8',
    statusGood: '#69F0AE',
    statusWarn: '#FFD740',
    statusBad: '#FF8C00',
    statusCritical: '#FF5252',
    selectionBg: '#3D2E1F',

    // Diffs
    diffAdded: 'rgb(220,255,220)',
    diffRemoved: 'rgb(255,220,220)',
    diffAddedWord: 'rgb(36,138,61)',
    diffRemovedWord: 'rgb(207,34,46)',

    // Shell prompt — distinct from AI prompt
    shellDollar: '#FFA726',

    // Functional agent coloring
    thinking: '#FFB74D',
    tool: '#448AFF',
    search: '#69F0AE',
    synthesize: '#FF80AB',
    skill: '#B388FF',
    agent: '#4DD0E1',
    code: '#80CBC4',
    shell: '#FFD740'
  },

  brand: BRAND,

  bannerLogo: '',
  bannerHero: ''
}

export const LIGHT_THEME: Theme = {
  color: {
    // Warm amber on light backgrounds
    primary: '#E65100',
    accent: '#BF4F00',
    border: '#8B4513',
    text: '#3E2723',
    muted: '#8D6E63',
    completionBg: '#FFF8F0',
    completionCurrentBg: mix('#FFF8F0', '#FF8C00', 0.15),
    completionMetaBg: '#FFF8F0',
    completionMetaCurrentBg: mix('#FFF8F0', '#FF8C00', 0.15),

    label: '#BF4F00',
    ok: '#2E7D32',
    error: '#C62828',
    warn: '#E65100',

    prompt: '#E65100',
    sessionLabel: '#8D6E63',
    sessionBorder: '#8D6E63',

    statusBg: '#FFF8F0',
    statusFg: '#3E2723',
    statusGood: '#2E7D32',
    statusWarn: '#E65100',
    statusBad: '#D84315',
    statusCritical: '#B71C1C',
    selectionBg: '#FFE0B2',

    diffAdded: 'rgb(200,240,200)',
    diffRemoved: 'rgb(240,200,200)',
    diffAddedWord: 'rgb(27,94,32)',
    diffRemovedWord: 'rgb(183,28,28)',
    shellDollar: '#E65100',

    thinking: '#E65100',
    tool: '#1565C0',
    search: '#2E7D32',
    synthesize: '#C2185B',
    skill: '#6A1B9A',
    agent: '#00838F',
    code: '#00695C',
    shell: '#F57F17'
  },

  brand: BRAND,

  bannerLogo: '',
  bannerHero: ''
}

// ── Theme Presets (from theme-presets.ts) ──────────────────────────────

import {
  LYRA_EMBER,
  LYRA_NEBULA,
  LYRA_TERRA,
  LYRA_ABYSS,
  LYRA_BLOOM,
  LYRA_PHANTOM,
  LYRA_SOLAR,
  LYRA_VOID,
  LYRA_CORAL,
  LYRA_PRISM
} from './theme-presets.js'

// Lyra Ocean (Default) — Teal/Cyan primary, cool blue undertones.
// Primary recommendation: aligns with Lyra brand identity, works universally.
export const LYRA_OCEAN: ThemeColors = {
  primary: '#00BCD4',
  accent: '#7C4DFF',
  border: '#30363D',
  text: '#E6EDF3',
  muted: '#8B949E',
  completionBg: '#161B22',
  completionCurrentBg: '#1C2333',
  completionMetaBg: '#0D1117',
  completionMetaCurrentBg: '#252D3F',

  label: '#58A6FF',
  ok: '#3FB950',
  error: '#F85149',
  warn: '#D29922',

  prompt: '#00BCD4',
  sessionLabel: '#8B949E',
  sessionBorder: '#30363D',

  statusBg: '#161B22',
  statusFg: '#8B949E',
  statusGood: '#3FB950',
  statusWarn: '#D29922',
  statusBad: '#F0883E',
  statusCritical: '#F85149',
  selectionBg: '#1C2333',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#00BCD4',

  thinking: '#FFB74D',
  tool: '#448AFF',
  search: '#69DB7C',
  synthesize: '#FF80AB',
  skill: '#B388FF',
  agent: '#4DD0E1',
  code: '#00BCD4',
  shell: '#FFD740'
}

// Lyra Aurora — Warm amber primary, prose-first. Best for conversational AI.
export const LYRA_AURORA: ThemeColors = {
  primary: '#FFA726',
  accent: '#00BCD4',
  border: '#3A3937',
  text: '#F5F0E8',
  muted: '#B0AEA5',
  completionBg: '#1C1B1A',
  completionCurrentBg: '#252423',
  completionMetaBg: '#141413',
  completionMetaCurrentBg: '#2E2D2C',

  label: '#4D96FF',
  ok: '#6BCB77',
  error: '#FF6B6B',
  warn: '#FFD93D',

  prompt: '#FFA726',
  sessionLabel: '#B0AEA5',
  sessionBorder: '#3A3937',

  statusBg: '#1C1B1A',
  statusFg: '#B0AEA5',
  statusGood: '#6BCB77',
  statusWarn: '#FFD93D',
  statusBad: '#FF8C00',
  statusCritical: '#FF6B6B',
  selectionBg: '#252423',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#FFA726',

  thinking: '#FF8A65',
  tool: '#4D96FF',
  search: '#69DB7C',
  synthesize: '#FF80AB',
  skill: '#B388FF',
  agent: '#FFB74D',
  code: '#64FFDA',
  shell: '#FFD740'
}

// Lyra Frost — Nord-inspired, cool arctic tones. Maximum readability for long sessions.
export const LYRA_FROST: ThemeColors = {
  primary: '#81A1C1',
  accent: '#8FBCBB',
  border: '#4C566A',
  text: '#ECEFF4',
  muted: '#D8DEE9',
  completionBg: '#3B4252',
  completionCurrentBg: '#434C5E',
  completionMetaBg: '#2E3440',
  completionMetaCurrentBg: '#4C566A',

  label: '#81A1C1',
  ok: '#A3BE8C',
  error: '#BF616A',
  warn: '#EBCB8B',

  prompt: '#81A1C1',
  sessionLabel: '#D8DEE9',
  sessionBorder: '#4C566A',

  statusBg: '#3B4252',
  statusFg: '#D8DEE9',
  statusGood: '#A3BE8C',
  statusWarn: '#EBCB8B',
  statusBad: '#D08770',
  statusCritical: '#BF616A',
  selectionBg: '#434C5E',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#81A1C1',

  thinking: '#D08770',
  tool: '#81A1C1',
  search: '#A3BE8C',
  synthesize: '#B48EAD',
  skill: '#B48EAD',
  agent: '#8FBCBB',
  code: '#88C0D0',
  shell: '#EBCB8B'
}

// Lyra Synth — High contrast, vibrant. Tokyo Night-inspired, best for power users.
export const LYRA_SYNTH: ThemeColors = {
  primary: '#00E5FF',
  accent: '#BB86FC',
  border: '#414868',
  text: '#C0CAF5',
  muted: '#565F89',
  completionBg: '#24283B',
  completionCurrentBg: '#32344A',
  completionMetaBg: '#1A1B26',
  completionMetaCurrentBg: '#414868',

  label: '#7AA2F7',
  ok: '#9ECE6A',
  error: '#FF5370',
  warn: '#FFC777',

  prompt: '#00E5FF',
  sessionLabel: '#565F89',
  sessionBorder: '#414868',

  statusBg: '#24283B',
  statusFg: '#565F89',
  statusGood: '#9ECE6A',
  statusWarn: '#FFC777',
  statusBad: '#FF9E64',
  statusCritical: '#FF5370',
  selectionBg: '#32344A',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#00E5FF',

  thinking: '#FF9E64',
  tool: '#7AA2F7',
  search: '#9ECE6A',
  synthesize: '#BB9AF7',
  skill: '#F7768E',
  agent: '#7DCFFF',
  code: '#00E5FF',
  shell: '#E0AF68'
}

// Lyra Grove — Earthy forest tones. Everforest-inspired, best for all-day work.
export const LYRA_GROVE: ThemeColors = {
  primary: '#83C092',
  accent: '#D699B6',
  border: '#475258',
  text: '#D3C6AA',
  muted: '#859289',
  completionBg: '#343F44',
  completionCurrentBg: '#3D484D',
  completionMetaBg: '#2D353B',
  completionMetaCurrentBg: '#475258',

  label: '#7FBBB3',
  ok: '#A7C080',
  error: '#E67E80',
  warn: '#DBBC7F',

  prompt: '#83C092',
  sessionLabel: '#859289',
  sessionBorder: '#475258',

  statusBg: '#343F44',
  statusFg: '#859289',
  statusGood: '#A7C080',
  statusWarn: '#DBBC7F',
  statusBad: '#E69875',
  statusCritical: '#E67E80',
  selectionBg: '#3D484D',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#83C092',

  thinking: '#E69875',
  tool: '#7FBBB3',
  search: '#A7C080',
  synthesize: '#D699B6',
  skill: '#D47766',
  agent: '#8DA899',
  code: '#83C092',
  shell: '#DBBC7F'
}

// ── Theme Registry ────────────────────────────────────────────────────

export type ThemeName = 'ocean' | 'aurora' | 'frost' | 'synth' | 'grove'
  | 'ember' | 'nebula' | 'terra' | 'abyss' | 'bloom'
  | 'phantom' | 'solar' | 'void' | 'coral' | 'prism'

export const THEME_NAMES: readonly ThemeName[] = [
  'ocean', 'aurora', 'frost', 'synth', 'grove',
  'ember', 'nebula', 'terra', 'abyss', 'bloom',
  'phantom', 'solar', 'void', 'coral', 'prism'
] as const

export const THEME_LABELS: Record<ThemeName, string> = {
  aurora: 'Lyra Aurora',
  frost: 'Lyra Frost',
  grove: 'Lyra Grove',
  ocean: 'Lyra Ocean',
  synth: 'Lyra Synth',
  ember: 'Lyra Ember',
  nebula: 'Lyra Nebula',
  terra: 'Lyra Terra',
  abyss: 'Lyra Abyss',
  bloom: 'Lyra Bloom',
  phantom: 'Lyra Phantom',
  solar: 'Lyra Solar',
  void: 'Lyra Void',
  coral: 'Lyra Coral',
  prism: 'Lyra Prism'
}

export const THEME_PRESETS: Record<ThemeName, ThemeColors> = {
  aurora: LYRA_AURORA,
  frost: LYRA_FROST,
  grove: LYRA_GROVE,
  ocean: LYRA_OCEAN,
  synth: LYRA_SYNTH,
  ember: LYRA_EMBER,
  nebula: LYRA_NEBULA,
  terra: LYRA_TERRA,
  abyss: LYRA_ABYSS,
  bloom: LYRA_BLOOM,
  phantom: LYRA_PHANTOM,
  solar: LYRA_SOLAR,
  void: LYRA_VOID,
  coral: LYRA_CORAL,
  prism: LYRA_PRISM
}

export function themeNameFromEnv(env: NodeJS.ProcessEnv = process.env): ThemeName {
  const raw = (env.LYRA_THEME ?? '').trim().toLowerCase()
  if ((THEME_NAMES as readonly string[]).includes(raw)) return raw as ThemeName
  return 'ocean'
}

export function cycleTheme(current: ThemeName): ThemeName {
  const idx = THEME_NAMES.indexOf(current)
  return THEME_NAMES[(idx + 1) % THEME_NAMES.length]!
}

export function buildTheme(colors: ThemeColors, brandOverrides?: Partial<ThemeBrand>): Theme {
  return {
    color: colors,
    brand: brandOverrides ? { ...BRAND, ...brandOverrides } : BRAND,
    bannerLogo: '',
    bannerHero: ''
  }
}

// ── Light/Dark Detection ─────────────────────────────────────────────

const TRUE_RE = /^(?:1|true|yes|on)$/
const FALSE_RE = /^(?:0|false|no|off)$/

const LIGHT_DEFAULT_TERM_PROGRAMS = new Set<string>(['Apple_Terminal'])
const LUMA_LIGHT_THRESHOLD = 0.6

const HEX_3_RE = /^[0-9a-f]{3}$/
const HEX_6_RE = /^[0-9a-f]{6}$/

function backgroundLuminance(raw: string): null | number {
  const v = raw.trim().toLowerCase()
  if (!v) return null
  const hex = v.startsWith('#') ? v.slice(1) : v
  const rgb = HEX_6_RE.test(hex)
    ? [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)]
    : HEX_3_RE.test(hex)
      ? [parseInt(hex[0]! + hex[0]!, 16), parseInt(hex[1]! + hex[1]!, 16), parseInt(hex[2]! + hex[2]!, 16)]
      : null
  if (!rgb) return null
  return (0.2126 * rgb[0]! + 0.7152 * rgb[1]! + 0.0722 * rgb[2]!) / 255
}

export function detectLightMode(
  env: NodeJS.ProcessEnv = process.env,
  lightDefaultTermPrograms: ReadonlySet<string> = LIGHT_DEFAULT_TERM_PROGRAMS
): boolean {
  const lightFlag = (env.LYRA_TUI_LIGHT ?? '').trim().toLowerCase()
  if (TRUE_RE.test(lightFlag)) return true
  if (FALSE_RE.test(lightFlag)) return false

  const themeFlag = (env.LYRA_TUI_THEME ?? '').trim().toLowerCase()
  if (themeFlag === 'light') return true
  if (themeFlag === 'dark') return false

  const bgHint = backgroundLuminance(env.LYRA_TUI_BACKGROUND ?? '')
  if (bgHint !== null) return bgHint >= LUMA_LIGHT_THRESHOLD

  const colorfgbg = (env.COLORFGBG ?? '').trim()
  if (colorfgbg) {
    const lastField = colorfgbg.split(';').at(-1) ?? ''
    if (/^\d+$/.test(lastField)) {
      const bg = Number(lastField)
      if (bg === 7 || bg === 15) return true
      if (bg >= 0 && bg < 16) return false
    }
  }

  const termProgram = (env.TERM_PROGRAM ?? '').trim()
  return lightDefaultTermPrograms.has(termProgram)
}

function shouldNormalizeAnsiLightTheme(env: NodeJS.ProcessEnv = process.env, isLight = detectLightMode(env)): boolean {
  const colorTerm = (env.COLORTERM ?? '').trim().toLowerCase()
  const termProgram = (env.TERM_PROGRAM ?? '').trim()
  return termProgram === 'Apple_Terminal' && colorTerm !== 'truecolor' && colorTerm !== '24bit' && isLight
}

export function normalizeThemeForAnsiLightTerminal(
  theme: Theme,
  env: NodeJS.ProcessEnv = process.env,
  isLight = detectLightMode(env)
): Theme {
  if (!shouldNormalizeAnsiLightTheme(env, isLight)) return theme
  const color = { ...theme.color }
  for (const key of ANSI_NORMALIZED_FOREGROUNDS) {
    color[key] = normalizeAnsiForeground(color[key])
  }
  for (const key of ANSI_MUTED_FOREGROUNDS) {
    color[key] = `ansi256(${ANSI_MUTED_BUCKET})`
  }
  return { ...theme, color }
}

const DEFAULT_LIGHT_MODE = detectLightMode()
const DEFAULT_THEME_NAME = themeNameFromEnv()

export const DEFAULT_THEME: Theme = normalizeThemeForAnsiLightTerminal(
  buildTheme(DEFAULT_LIGHT_MODE ? LIGHT_THEME.color : THEME_PRESETS[DEFAULT_THEME_NAME]),
  process.env,
  DEFAULT_LIGHT_MODE
)

// ── Skin → Theme ─────────────────────────────────────────────────────

export function fromSkin(
  colors: Record<string, string>,
  branding: Record<string, string>,
  bannerLogo = '',
  bannerHero = '',
  toolPrefix = '',
  helpHeader = ''
): Theme {
  const d = DEFAULT_THEME
  const c = (k: string): Color | undefined => colors[k] as Color | undefined
  const hasSkinColors = Object.keys(colors).length > 0

  const accent: Color = (c('ui_accent') ?? c('banner_accent') ?? d.color.accent) as Color
  const bannerAccent: Color = (c('banner_accent') ?? c('banner_title') ?? d.color.accent) as Color
  const muted: Color = (c('banner_dim') ?? d.color.muted) as Color
  const completionBg: Color = (c('completion_menu_bg') ?? d.color.completionBg) as Color

  const completionCurrentBg: Color = (
    c('completion_menu_current_bg') ??
    (hasSkinColors ? mix(completionBg, bannerAccent, 0.25) : d.color.completionCurrentBg)
  ) as Color

  const completionMetaBg: Color = (c('completion_menu_meta_bg') ?? completionBg) as Color
  const completionMetaCurrentBg: Color = (c('completion_menu_meta_current_bg') ?? completionCurrentBg) as Color

  return normalizeThemeForAnsiLightTerminal({
    color: {
      primary: c('ui_primary') ?? c('banner_title') ?? d.color.primary,
      accent,
      border: c('ui_border') ?? c('banner_border') ?? d.color.border,
      text: c('ui_text') ?? c('banner_text') ?? d.color.text,
      muted,
      completionBg,
      completionCurrentBg,
      completionMetaBg,
      completionMetaCurrentBg,

      label: c('ui_label') ?? d.color.label,
      ok: c('ui_ok') ?? d.color.ok,
      error: c('ui_error') ?? d.color.error,
      warn: c('ui_warn') ?? d.color.warn,

      prompt: c('prompt') ?? c('banner_text') ?? d.color.prompt,
      sessionLabel: c('session_label') ?? muted,
      sessionBorder: c('session_border') ?? muted,

      statusBg: d.color.statusBg,
      statusFg: d.color.statusFg,
      statusGood: c('ui_ok') ?? d.color.statusGood,
      statusWarn: c('ui_warn') ?? d.color.statusWarn,
      statusBad: d.color.statusBad,
      statusCritical: d.color.statusCritical,
      selectionBg: c('selection_bg') ?? c('completion_menu_current_bg') ?? (hasSkinColors ? completionCurrentBg : d.color.selectionBg),

      diffAdded: d.color.diffAdded,
      diffRemoved: d.color.diffRemoved,
      diffAddedWord: d.color.diffAddedWord,
      diffRemovedWord: d.color.diffRemovedWord,
      shellDollar: c('shell_dollar') ?? d.color.shellDollar,

      thinking: c('thinking') ?? d.color.thinking,
      tool: c('tool') ?? d.color.tool,
      search: c('search') ?? d.color.search,
      synthesize: c('synthesize') ?? d.color.synthesize,
      skill: c('skill_color') ?? d.color.skill,
      agent: c('agent_color') ?? d.color.agent,
      code: c('code') ?? d.color.code,
      shell: c('shell') ?? d.color.shell
    },

    brand: {
      name: branding.agent_name ?? d.brand.name,
      icon: d.brand.icon,
      prompt: cleanPromptSymbol(branding.prompt_symbol, d.brand.prompt),
      welcome: branding.welcome ?? d.brand.welcome,
      goodbye: branding.goodbye ?? d.brand.goodbye,
      tool: toolPrefix || d.brand.tool,
      helpHeader: branding.help_header ?? (helpHeader || d.brand.helpHeader)
    },

    bannerLogo,
    bannerHero
  }, process.env, DEFAULT_LIGHT_MODE)
}

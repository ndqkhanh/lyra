/**
 * Hermes-style Skin Configuration System.
 *
 * Ported from hermes_cli/skin_engine.py — data-driven theme system
 * where SkinConfig carries semantic color slots, spinner/personality
 * config, branding strings, and per-tool emoji overrides.
 *
 * A SkinConfig is built from a ThemePreset + ThemeBrand via
 * buildSkinFromPreset(), bridging the existing 12-theme preset
 * system to the Hermes-style skin architecture.
 */

import type { ThemePreset } from './presets'

// ── Spinner / Personality ──────────────────────────────────────────

export interface SpinnerConfig {
  /** Faces shown while waiting for API (before first token) */
  waitingFaces?: string[]
  /** Faces shown during streaming/thinking */
  thinkingFaces?: string[]
  /** Verbs displayed in the status bar during streaming */
  thinkingVerbs?: string[]
  /** Optional left/right wing decorations for the spinner */
  wings?: Array<[string, string]>
}

// ── Branding ───────────────────────────────────────────────────────

export interface SkinBranding {
  agentName: string
  welcome: string
  goodbye: string
  responseLabel: string
  promptSymbol: string
  helpHeader: string
}

// ── Semantic Color Slots ───────────────────────────────────────────

export interface SkinColors {
  // Banner
  bannerBorder: string
  bannerTitle: string
  bannerAccent: string
  bannerDim: string
  bannerText: string
  // UI general
  uiAccent: string
  uiLabel: string
  uiOk: string
  uiError: string
  uiWarn: string
  // Prompt / input
  prompt: string
  inputRule: string
  // Response panel
  responseBorder: string
  // Status bar
  statusBarBg: string
  statusBarText: string
  statusBarStrong: string
  statusBarDim: string
  statusBarGood: string
  statusBarWarn: string
  statusBarBad: string
  statusBarCritical: string
  // Session
  sessionLabel: string
  sessionBorder: string
  // Completion menu
  completionMenuBg: string
  completionMenuCurrentBg: string
  // Voice (optional)
  voiceStatusBg: string
}

// ── Full Skin Config ───────────────────────────────────────────────

export interface SkinConfig {
  id: string
  name: string
  description: string
  variant: 'dark' | 'light' | 'midnight'
  colors: SkinColors
  spinner: SpinnerConfig
  branding: SkinBranding
  /** Character prefix for tool output lines */
  toolPrefix: string
  /** Per-tool emoji overrides */
  toolEmojis: Record<string, string>
}

// ── Kawaii Defaults (from Hermes display.py) ──────────────────────

export const DEFAULT_WAITING_FACES = [
  '（(*ﾉ◕ヮ◕)',
  '（◕ヮ◕✿）',
  '٩(◕ヮ◕١)۶',
  '(✧◠ヮ◠)',
  '(˚ˇ◘)っ♪',
  '♪(´ε\` )',
  '(◕メ◕✿)',
  'ヾ(＾∇＾)',
  '(≧◡≦)',
  '(★ω★)',
]

export const DEFAULT_THINKING_FACES = [
  '(｡•́﹏•̀｡)',
  '(◔_◔)',
  '(¬‿¬)',
  '(　•_>⌠■-■',
  '(⌡■_■)',
  '(´・_・\`)',
  '◉_◉',
  '(°ロ°)',
  '(˚⌣˚)♡',
  'ヽ(>∀<☆)ノ',
]

export const DEFAULT_THINKING_VERBS = [
  'pondering', 'contemplating', 'musing', 'cogitating', 'ruminating',
  'deliberating', 'mulling', 'reflecting', 'processing', 'reasoning',
  'analyzing', 'computing', 'synthesizing', 'formulating', 'brainstorming',
]

// ── Builder ────────────────────────────────────────────────────────

/**
 * Build a SkinConfig from a ThemePreset + optional branding overrides.
 * This bridges the existing preset system to Hermes-style skins.
 */
export function buildSkinFromPreset(
  preset: ThemePreset,
  branding?: Partial<SkinBranding>,
): SkinConfig {
  const p = preset.palette
  return {
    id: preset.id,
    name: preset.name,
    description: `${preset.name} (${preset.variant})`,
    variant: preset.variant,
    colors: {
      bannerBorder: p.accent,
      bannerTitle: p.accent,
      bannerAccent: p.accent,
      bannerDim: p.subtext0,
      bannerText: p.text,
      uiAccent: p.accent,
      uiLabel: p.accent,
      uiOk: p.green,
      uiError: p.red,
      uiWarn: p.yellow,
      prompt: p.foreground,
      inputRule: p.accent,
      responseBorder: p.accent,
      statusBarBg: p.statusBg,
      statusBarText: p.statusFg,
      statusBarStrong: p.accent,
      statusBarDim: p.subtext0,
      statusBarGood: p.statusSuccess,
      statusBarWarn: p.statusWarning,
      statusBarBad: p.orange,
      statusBarCritical: p.statusError,
      sessionLabel: p.accent,
      sessionBorder: p.subtext0,
      completionMenuBg: p.surface0,
      completionMenuCurrentBg: p.selection,
      voiceStatusBg: p.statusBg,
    },
    spinner: {
      waitingFaces: DEFAULT_WAITING_FACES,
      thinkingFaces: DEFAULT_THINKING_FACES,
      thinkingVerbs: DEFAULT_THINKING_VERBS,
    },
    branding: {
      agentName: 'Lyra',
      welcome: 'Type your message or /help for commands.',
      goodbye: 'Goodbye!',
      responseLabel: 'Lyra',
      promptSymbol: '❯',
      helpHeader: '(^_^)? Commands',
      ...branding,
    },
    toolPrefix: '┊',
    toolEmojis: {},
  }
}

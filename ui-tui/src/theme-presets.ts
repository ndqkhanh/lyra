import type { ThemeColors } from './theme.js'

// ── New Theme Presets ─────────────────────────────────────────────────────
// 10 professionally designed color themes for Lyra TUI.
// All themes are dark-mode optimized with dark backgrounds.

// ─────────────────────────────────────────────────────────────────────────
// Lyra Ember — Deep crimson/red with gold accents (sunset warmth)
// A bold, passionate palette inspired by glowing embers and sunset skies.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_EMBER: ThemeColors = {
  primary: '#FF5252',
  accent: '#FFB300',
  border: '#4A2C2C',
  text: '#FFF0E8',
  muted: '#B8897A',
  completionBg: '#1C1212',
  completionCurrentBg: '#2E1D1D',
  completionMetaBg: '#120A0A',
  completionMetaCurrentBg: '#3D2828',

  label: '#FF8A65',
  ok: '#69F0AE',
  error: '#FF1744',
  warn: '#FFD740',

  prompt: '#FF5252',
  sessionLabel: '#B8897A',
  sessionBorder: '#4A2C2C',

  statusBg: '#1C1212',
  statusFg: '#B8897A',
  statusGood: '#69F0AE',
  statusWarn: '#FFD740',
  statusBad: '#FF6E40',
  statusCritical: '#FF1744',
  selectionBg: '#2E1D1D',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#FFAB40',

  thinking: '#FF8A65',
  tool: '#40C4FF',
  search: '#69DB7C',
  synthesize: '#FF80AB',
  skill: '#B388FF',
  agent: '#4DD0E1',
  code: '#FF5252',
  shell: '#FFD740'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Nebula — Purple/violet with magenta accents (cosmic)
// A deep space-inspired palette with rich purples and vibrant magenta.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_NEBULA: ThemeColors = {
  primary: '#B388FF',
  accent: '#FF4081',
  border: '#3A2E52',
  text: '#ECE4F7',
  muted: '#9A8BB8',
  completionBg: '#19132E',
  completionCurrentBg: '#282044',
  completionMetaBg: '#100C20',
  completionMetaCurrentBg: '#3A2E52',

  label: '#82B1FF',
  ok: '#69F0AE',
  error: '#FF5252',
  warn: '#FFD740',

  prompt: '#B388FF',
  sessionLabel: '#9A8BB8',
  sessionBorder: '#3A2E52',

  statusBg: '#19132E',
  statusFg: '#9A8BB8',
  statusGood: '#69F0AE',
  statusWarn: '#FFD740',
  statusBad: '#FF6E40',
  statusCritical: '#FF5252',
  selectionBg: '#282044',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#EA80FC',

  thinking: '#FF8A65',
  tool: '#82B1FF',
  search: '#69DB7C',
  synthesize: '#FF80AB',
  skill: '#EA80FC',
  agent: '#84FFFF',
  code: '#B388FF',
  shell: '#FFD740'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Terra — Warm earth tones, terracotta/sienna (desert)
// An earthy palette inspired by desert landscapes, terracotta clay, and sun-baked stone.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_TERRA: ThemeColors = {
  primary: '#D4896A',
  accent: '#E8B84B',
  border: '#45342B',
  text: '#F5EDE0',
  muted: '#B09A85',
  completionBg: '#1B1612',
  completionCurrentBg: '#2C241E',
  completionMetaBg: '#110E0B',
  completionMetaCurrentBg: '#3D3229',

  label: '#E8B84B',
  ok: '#8BC34A',
  error: '#E57373',
  warn: '#FFD54F',

  prompt: '#D4896A',
  sessionLabel: '#B09A85',
  sessionBorder: '#45342B',

  statusBg: '#1B1612',
  statusFg: '#B09A85',
  statusGood: '#8BC34A',
  statusWarn: '#FFD54F',
  statusBad: '#E57373',
  statusCritical: '#EF5350',
  selectionBg: '#2C241E',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#E8B84B',

  thinking: '#FFB74D',
  tool: '#4FC3F7',
  search: '#81C784',
  synthesize: '#FF80AB',
  skill: '#CE93D8',
  agent: '#4DD0E1',
  code: '#D4896A',
  shell: '#FFD54F'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Abyss — Deep blue-black with electric blue accents (ocean depths)
// A deep palette inspired by ocean trenches, with bright electric blue highlights.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_ABYSS: ThemeColors = {
  primary: '#448AFF',
  accent: '#00E5FF',
  border: '#1A2744',
  text: '#DEE8FF',
  muted: '#7187A8',
  completionBg: '#0F1829',
  completionCurrentBg: '#1C2B47',
  completionMetaBg: '#0A101E',
  completionMetaCurrentBg: '#263858',

  label: '#4FC3F7',
  ok: '#69F0AE',
  error: '#FF5252',
  warn: '#FFD740',

  prompt: '#448AFF',
  sessionLabel: '#7187A8',
  sessionBorder: '#1A2744',

  statusBg: '#0F1829',
  statusFg: '#7187A8',
  statusGood: '#69F0AE',
  statusWarn: '#FFD740',
  statusBad: '#FF6E40',
  statusCritical: '#FF5252',
  selectionBg: '#1C2B47',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#00E5FF',

  thinking: '#FF8A65',
  tool: '#448AFF',
  search: '#69DB7C',
  synthesize: '#FF80AB',
  skill: '#B388FF',
  agent: '#4DD0E1',
  code: '#00E5FF',
  shell: '#FFD740'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Bloom — Green/emerald with gold accents (garden/spring)
// A fresh, rejuvenating palette inspired by spring gardens and new growth.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_BLOOM: ThemeColors = {
  primary: '#66BB6A',
  accent: '#FFD54F',
  border: '#2D4030',
  text: '#E8F5E9',
  muted: '#95A896',
  completionBg: '#162918',
  completionCurrentBg: '#243D27',
  completionMetaBg: '#0D1C0F',
  completionMetaCurrentBg: '#2D4030',

  label: '#AED581',
  ok: '#69F0AE',
  error: '#FF5252',
  warn: '#FFD740',

  prompt: '#66BB6A',
  sessionLabel: '#95A896',
  sessionBorder: '#2D4030',

  statusBg: '#162918',
  statusFg: '#95A896',
  statusGood: '#69F0AE',
  statusWarn: '#FFD740',
  statusBad: '#FF6E40',
  statusCritical: '#FF5252',
  selectionBg: '#243D27',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#FFD54F',

  thinking: '#FF8A65',
  tool: '#4FC3F7',
  search: '#66BB6A',
  synthesize: '#F06292',
  skill: '#CE93D8',
  agent: '#4DD0E1',
  code: '#81C784',
  shell: '#FFD740'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Phantom — Monochrome grayscale with subtle blue tints (stealth)
// A minimalist, professional palette with maximum readability and zero distraction.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_PHANTOM: ThemeColors = {
  primary: '#B0BEC5',
  accent: '#78909C',
  border: '#37474F',
  text: '#ECEFF1',
  muted: '#78909C',
  completionBg: '#1B1E21',
  completionCurrentBg: '#272B30',
  completionMetaBg: '#121416',
  completionMetaCurrentBg: '#37474F',

  label: '#90A4AE',
  ok: '#81C784',
  error: '#E57373',
  warn: '#FFD54F',

  prompt: '#B0BEC5',
  sessionLabel: '#78909C',
  sessionBorder: '#37474F',

  statusBg: '#1B1E21',
  statusFg: '#78909C',
  statusGood: '#81C784',
  statusWarn: '#FFD54F',
  statusBad: '#E57373',
  statusCritical: '#EF5350',
  selectionBg: '#272B30',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#B0BEC5',

  thinking: '#90A4AE',
  tool: '#64B5F6',
  search: '#81C784',
  synthesize: '#CE93D8',
  skill: '#90A4AE',
  agent: '#80CBC4',
  code: '#B0BEC5',
  shell: '#B0BEC5'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Solar — Yellow/gold primary with warm orange (sunlight)
// A bright, energetic palette inspired by golden sunlight and summer days.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_SOLAR: ThemeColors = {
  primary: '#FFD54F',
  accent: '#FF8A65',
  border: '#4A4035',
  text: '#FFF8E1',
  muted: '#B8A88C',
  completionBg: '#1E1A14',
  completionCurrentBg: '#2E2820',
  completionMetaBg: '#14110C',
  completionMetaCurrentBg: '#3D352C',

  label: '#FFB74D',
  ok: '#69F0AE',
  error: '#FF5252',
  warn: '#FFD740',

  prompt: '#FFD54F',
  sessionLabel: '#B8A88C',
  sessionBorder: '#4A4035',

  statusBg: '#1E1A14',
  statusFg: '#B8A88C',
  statusGood: '#69F0AE',
  statusWarn: '#FFD740',
  statusBad: '#FF8A65',
  statusCritical: '#FF5252',
  selectionBg: '#2E2820',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#FFB300',

  thinking: '#FF8A65',
  tool: '#40C4FF',
  search: '#69DB7C',
  synthesize: '#FF80AB',
  skill: '#B388FF',
  agent: '#4DD0E1',
  code: '#FFD54F',
  shell: '#FFD740'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Void — Pure dark with white/high-contrast accents (minimalist)
// The ultimate minimalist theme. Pure black background, white text, nothing extra.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_VOID: ThemeColors = {
  primary: '#FFFFFF',
  accent: '#9E9E9E',
  border: '#333333',
  text: '#FFFFFF',
  muted: '#888888',
  completionBg: '#111111',
  completionCurrentBg: '#222222',
  completionMetaBg: '#0A0A0A',
  completionMetaCurrentBg: '#333333',

  label: '#E0E0E0',
  ok: '#81C784',
  error: '#E57373',
  warn: '#FFD54F',

  prompt: '#FFFFFF',
  sessionLabel: '#888888',
  sessionBorder: '#333333',

  statusBg: '#111111',
  statusFg: '#888888',
  statusGood: '#81C784',
  statusWarn: '#FFD54F',
  statusBad: '#E57373',
  statusCritical: '#EF5350',
  selectionBg: '#222222',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#CCCCCC',

  thinking: '#E0E0E0',
  tool: '#B0BEC5',
  search: '#81C784',
  synthesize: '#CE93D8',
  skill: '#90A4AE',
  agent: '#80CBC4',
  code: '#E0E0E0',
  shell: '#B0BEC5'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Coral — Coral/pink with teal accents (tropical reef)
// A vibrant tropical palette with warm coral, cool teal, and ocean-fresh accents.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_CORAL: ThemeColors = {
  primary: '#FF6B6B',
  accent: '#4DD0E1',
  border: '#3D2E35',
  text: '#FDF5F0',
  muted: '#B09498',
  completionBg: '#1D1417',
  completionCurrentBg: '#2E2227',
  completionMetaBg: '#130C0F',
  completionMetaCurrentBg: '#3D2E35',

  label: '#FF8A80',
  ok: '#69F0AE',
  error: '#FF1744',
  warn: '#FFD740',

  prompt: '#FF6B6B',
  sessionLabel: '#B09498',
  sessionBorder: '#3D2E35',

  statusBg: '#1D1417',
  statusFg: '#B09498',
  statusGood: '#69F0AE',
  statusWarn: '#FFD740',
  statusBad: '#FF6E40',
  statusCritical: '#FF1744',
  selectionBg: '#2E2227',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#4DD0E1',

  thinking: '#FF8A65',
  tool: '#4DD0E1',
  search: '#69DB7C',
  synthesize: '#FF80AB',
  skill: '#B388FF',
  agent: '#4DD0E1',
  code: '#FF6B6B',
  shell: '#FFD740'
}

// ─────────────────────────────────────────────────────────────────────────
// Lyra Prism — Full rainbow semantic coloring on dark base (vibrant)
// A neutral dark base lets the functional agent colors form a complete rainbow.
// Each semantic role gets a distinct spectral hue for instant visual parsing.
// ─────────────────────────────────────────────────────────────────────────
export const LYRA_PRISM: ThemeColors = {
  primary: '#E0E0E0',
  accent: '#BBBBBB',
  border: '#404040',
  text: '#F5F5F5',
  muted: '#888888',
  completionBg: '#121212',
  completionCurrentBg: '#282828',
  completionMetaBg: '#0A0A0A',
  completionMetaCurrentBg: '#333333',

  label: '#E0E0E0',
  ok: '#69F0AE',
  error: '#FF5252',
  warn: '#FFD740',

  prompt: '#FFFFFF',
  sessionLabel: '#888888',
  sessionBorder: '#404040',

  statusBg: '#121212',
  statusFg: '#888888',
  statusGood: '#69F0AE',
  statusWarn: '#FFD740',
  statusBad: '#FF9100',
  statusCritical: '#FF5252',
  selectionBg: '#282828',

  diffAdded: 'rgb(200,240,200)',
  diffRemoved: 'rgb(240,200,200)',
  diffAddedWord: 'rgb(36,138,61)',
  diffRemovedWord: 'rgb(207,34,46)',
  shellDollar: '#CCCCCC',

  thinking: '#FF5252',
  tool: '#FF9100',
  search: '#FFD740',
  synthesize: '#69F0AE',
  skill: '#448AFF',
  agent: '#7C4DFF',
  code: '#E040FB',
  shell: '#18FFFF'
}

/**
 * Symbol system for Lyra UI
 * Unicode characters used throughout the interface
 */

export const symbols = {
  // Message markers
  userPrompt: '❯',
  assistant: '⏺',
  thinking: '✳',
  backgroundTask: '◯',
  system: '⏵⏵',

  // Tree/indent
  branch: '⎿',
  checkbox: '◻',
  checkboxChecked: '◼',

  // Navigation
  upArrow: '↑',
  downArrow: '↓',
  leftArrow: '←',
  rightArrow: '→',
  separator: '·',
  ellipsis: '…',

  // Status indicators
  spinner: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
  thinkingFrames: ['✳', '✴', '✵', '✶'],
  progressFrames: ['✢', '✶', '✳', '✽', '✻'],
  pending: '⏳',
  success: '✅',
  error: '❌',
  warning: '⚠',
  info: 'ℹ',

  // Logo — Constellation LYRA wordmark
  // Each row is colored independently for a gradient effect across the full mark
  logo: [
    '╦   ╦╦ ╦╦═╗╔═╗',
    '║   ╚╦╝╠╦╝╠═╣',
    '╩═╝  ╩ ╩╚═╩ ╩',
  ],

  // Decorative constellation stars (rendered in scattered positions)
  constellationTop:    '·   ✦   ·   ✧   ·   ✦   ·',
  constellationBottom: '·   ✧   ·   ✦   ·   ✧   ·',

  // Synthwave decorative divider
  synthwaveDivider: '━★━━━━━━━━━━━━━━━━━━━━━━━━━━★━',

  // Large block LYRA for alternative layouts
  logoBlock: [
    '╔╗ ╦ ╦╦═╗╔═╗',
    '╠╩╗╚╦╝╠╦╝╠═╣',
    '╚═╝ ╩ ╩╚═╩ ╩',
  ],

  // Borders
  horizontalLine: '─',
  verticalLine: '│',
  topLeft: '┌',
  topRight: '┐',
  bottomLeft: '└',
  bottomRight: '┘',
  cross: '┼',
  teeLeft: '├',
  teeRight: '┤',
  teeTop: '┬',
  teeBottom: '┴',
} as const

export type SymbolName = keyof typeof symbols

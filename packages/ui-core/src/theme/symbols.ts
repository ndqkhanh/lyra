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

  // Logo (3 lines)
  logo: [
    '██╗  ██╗   ██╗██████╗  █████╗ ',
    '██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗',
    '███████║ ╚████╔╝ ██████╔╝███████║'
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

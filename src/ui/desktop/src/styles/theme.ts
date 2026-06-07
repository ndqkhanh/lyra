/**
 * Lyra Desktop — Dark Theme Tokens
 * Inspired by the Dracula palette used in the terminal UI, adapted for desktop.
 */

export const theme = {
  colors: {
    // Background hierarchy
    bg: '#0f1117',
    bgAlt: '#161822',
    bgSurface: '#1c1e2e',
    bgHover: '#232539',
    bgInput: '#12141e',

    // Borders
    border: '#252840',
    borderLight: '#2d3050',

    // Text
    fg: '#e2e4f0',
    fgDim: '#8b8fa8',
    fgMuted: '#5c5f7a',

    // Accent / brand
    accent: '#bd93f9',
    accentDim: '#9a6fe0',

    // Syntax highlighting tokens
    keyword: '#ff79c6',
    string: '#f1fa8c',
    number: '#bd93f9',
    comment: '#6272a4',
    function: '#50fa7b',
    variable: '#f8f8f2',

    // Semantic
    success: '#50fa7b',
    warning: '#ffb86c',
    error: '#ff5555',
    info: '#8be9fd',

    // Agent states
    agentIdle: '#6272a4',
    agentActive: '#50fa7b',
    agentThinking: '#bd93f9',
    agentTool: '#ffb86c',
    agentError: '#ff5555',

    // Chat
    userBubble: '#232539',
    assistantBubble: '#1c1e2e',
    codeBg: '#161822',
    inlineCode: '#ff79c6',

    // Status bar
    statusBar: '#0b0d13',

    // Scrollbar
    scrollbar: '#2d3050',
    scrollbarHover: '#3d4070',
  },

  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    xxl: 32,
  },

  radius: {
    sm: 4,
    md: 6,
    lg: 8,
    xl: 12,
    full: 9999,
  },

  fontSize: {
    xs: 11,
    sm: 12,
    md: 13,
    lg: 14,
    xl: 16,
    xxl: 20,
    heading: 18,
  },

  fontFamily: {
    ui: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', Consolas, monospace",
  },

  shadow: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
    md: '0 4px 8px rgba(0, 0, 0, 0.4)',
    lg: '0 8px 24px rgba(0, 0, 0, 0.5)',
  },
} as const

export type Theme = typeof theme

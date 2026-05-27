/**
 * Color palette for Lyra UI
 * Matches Claude Code's visual style with vibrant colors
 */

export const colors = {
  // Primary message colors (more vibrant)
  userPrompt: '#00D9FF',      // Bright cyan for user prompts
  userText: '#FFFFFF',        // White for user text
  assistant: '#E0E0E0',       // Light gray for assistant text
  thinking: '#FFD700',        // Gold for thinking indicator
  backgroundTask: '#9370DB',  // Medium purple for background tasks
  system: '#00CED1',          // Cyan for system messages

  // Status colors (vibrant)
  success: '#00FF7F',         // Spring green
  error: '#FF4444',           // Bright red
  warning: '#FFA500',         // Orange
  info: '#00BFFF',            // Deep sky blue

  // Tool execution colors
  toolName: '#FF79C6',        // Pink for tool names
  toolSuccess: '#50FA7B',     // Green for success
  toolError: '#FF5555',       // Red for errors

  // File/code colors
  filePath: '#8BE9FD',        // Bright cyan for file paths
  lineNumber: '#6272A4',      // Blue gray for line numbers
  code: '#F8F8F2',            // Off white for code
  codeAdded: '#50FA7B',       // Green for added lines
  codeRemoved: '#FF5555',     // Red for removed lines

  // UI element colors
  timestamp: '#6272A4',       // Blue gray for timestamps
  muted: '#8899BB',           // Brighter muted text for readability
  emptyState: '#8BE9FD',      // Cyan for empty state / placeholder
  separator: '#44475A',       // Dark gray for separators
  border: '#6272A4',          // Blue gray for borders

  // Background
  background: '#282A36',      // Dracula background
  backgroundAlt: '#1A1A1A',   // Darker gray

  // Syntax highlighting (Dracula theme)
  keyword: '#FF79C6',         // Pink
  string: '#F1FA8C',          // Yellow
  number: '#BD93F9',          // Purple
  comment: '#6272A4',         // Blue gray
  function: '#50FA7B',        // Green
  variable: '#F8F8F2',        // Off white

  // Status bar colors
  statusIdle: '#6272A4',      // Blue gray
  statusActive: '#50FA7B',    // Green
  statusError: '#FF5555',     // Red

  // Mode colors
  modeMinimal: '#8BE9FD',     // Cyan
  modeStandard: '#50FA7B',    // Green
  modeDebug: '#FFB86C',       // Orange

  // Permission & security
  permission: '#FF4444',      // Red - permission warnings

  // Command output
  commandSuccess: '#50FA7B',  // Green
  commandError: '#FF5555',    // Red
  commandStdout: '#F8F8F2',   // Off white
  commandStderr: '#FFB86C',   // Orange
  commandPrompt: '#8BE9FD',   // Cyan

  // Code syntax (enhanced)
  codeKeyword: '#FF79C6',     // Pink
  codeString: '#F1FA8C',      // Yellow
  codeNumber: '#BD93F9',      // Purple
  codeComment: '#6272A4',     // Blue gray
  codeFunction: '#50FA7B',    // Green
  codeVariable: '#F8F8F2',    // Off white
  codeOperator: '#FF79C6',    // Pink
  codeBackground: '#282A36',  // Dark background

  // Diff colors
  diffAdded: '#50FA7B',       // Green
  diffAddedBg: '#1A3A1A',     // Dark green bg
  diffRemoved: '#FF5555',     // Red
  diffRemovedBg: '#3A1A1A',   // Dark red bg
  diffContext: '#6272A4',     // Blue gray

  // Markdown
  markdownHeading: '#FF79C6', // Pink
  markdownBold: '#F8F8F2',    // White
  markdownItalic: '#E0E0E0',  // Light gray
  markdownCode: '#F1FA8C',    // Yellow
  markdownCodeBlock: '#F8F8F2', // Off white
  markdownLink: '#8BE9FD',    // Cyan
  markdownQuote: '#6272A4',   // Blue gray
  markdownList: '#50FA7B',    // Green

  // Agent states
  agentThinking: '#FFD700',   // Gold
  agentComposing: '#FF79C6',  // Pink
  agentToolRunning: '#8BE9FD', // Cyan
  agentStreaming: '#50FA7B',  // Green
  agentIdle: '#6272A4',       // Gray
  agentError: '#FF5555',      // Red

  // Keyboard shortcuts
  shortcutKey: '#BD93F9',     // Purple
  shortcutDescription: '#6272A4', // Gray
  shortcutSeparator: '#44475A', // Dark gray

  // Error severity
  errorCritical: '#FF0000',   // Bright red
  errorHigh: '#FF5555',       // Red
  errorMedium: '#FFB86C',     // Orange
  errorLow: '#F1FA8C',        // Yellow
  errorInfo: '#8BE9FD',       // Cyan

  // Collapsible
  collapsibleExpanded: '#50FA7B',   // Green
  collapsibleCollapsed: '#6272A4',  // Gray
  collapsibleBorder: '#44475A',     // Dark gray

  // Status (enhanced)
  statusPending: '#FFB86C',   // Orange
  statusRunning: '#8BE9FD',   // Cyan
  statusSuccess: '#50FA7B',   // Green
  statusCancelled: '#6272A4', // Gray
  statusSkipped: '#BD93F9',   // Purple
} as const

export type ColorName = keyof typeof colors

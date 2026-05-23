/**
 * Color palette for Lyra UI
 * Matches Claude Code's visual style
 */

export const colors = {
  // Primary message colors
  userPrompt: '#00D9FF',      // Bright cyan
  assistant: '#E0E0E0',       // Light gray
  thinking: '#FFD700',        // Gold
  backgroundTask: '#808080',  // Gray
  system: '#00CED1',          // Cyan

  // Status colors
  success: '#00FF00',         // Green
  error: '#FF0000',           // Red
  warning: '#FFA500',         // Orange
  info: '#00BFFF',            // Deep sky blue

  // UI element colors
  filePath: '#00CED1',        // Cyan
  lineNumber: '#666666',      // Dark gray
  code: '#FFFFFF',            // White
  timestamp: '#999999',       // Medium gray
  separator: '#444444',       // Very dark gray

  // Background
  background: '#000000',      // Black
  backgroundAlt: '#1A1A1A',   // Dark gray
  border: '#333333',          // Dark gray

  // Syntax highlighting
  keyword: '#FF79C6',         // Pink
  string: '#50FA7B',          // Green
  number: '#BD93F9',          // Purple
  comment: '#6272A4',         // Blue gray
  function: '#8BE9FD',        // Cyan
  variable: '#F8F8F2',        // Off white
} as const

export type ColorName = keyof typeof colors

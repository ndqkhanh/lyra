import React from 'react'
import { theme } from '../styles/theme'

interface StatusBarProps {
  connected: boolean
  tokensIn: number
  tokensOut: number
  cost: number
  sessionCount: number
  activeSessionId: string | null
  isStreaming: boolean
}

function formatCost(cost: number): string {
  if (cost < 0.001) return '$0.0000'
  if (cost < 0.01) return `$${cost.toFixed(4)}`
  if (cost < 1) return `$${cost.toFixed(3)}`
  return `$${cost.toFixed(2)}`
}

export function StatusBar({
  connected,
  tokensIn,
  tokensOut,
  cost,
  sessionCount,
  activeSessionId,
  isStreaming,
}: StatusBarProps) {
  return (
    <div
      style={{
        height: 28,
        background: theme.colors.statusBar,
        borderTop: `1px solid ${theme.colors.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: `0 ${theme.spacing.md}px`,
        fontSize: theme.fontSize.xs,
        color: theme.colors.fgMuted,
        flexShrink: 0,
        userSelect: 'none',
      }}
    >
      {/* Left: connection & session info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.md }}>
        {/* Connection indicator */}
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: connected ? theme.colors.success : theme.colors.error,
              display: 'inline-block',
            }}
          />
          {connected ? 'Connected' : 'Disconnected'}
        </span>

        {isStreaming && (
          <span style={{ color: theme.colors.accent }}>
            Streaming...
          </span>
        )}

        <span>
          {sessionCount} session{sessionCount !== 1 ? 's' : ''}
        </span>
        {activeSessionId && (
          <span style={{ color: theme.colors.fgDim }}>
            ID: {activeSessionId.slice(0, 8)}
          </span>
        )}
      </div>

      {/* Right: token usage & cost */}
      <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.md }}>
        <span>in: {tokensIn.toLocaleString()}</span>
        <span>out: {tokensOut.toLocaleString()}</span>
        <span style={{ color: theme.colors.warning, fontWeight: 600 }}>
          {formatCost(cost)}
        </span>
      </div>
    </div>
  )
}

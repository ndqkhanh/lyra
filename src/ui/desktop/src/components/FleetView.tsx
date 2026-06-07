import React from 'react'
import { theme } from '../styles/theme'
import type { Session } from '../hooks/useLyraAPI'

interface FleetViewProps {
  sessions: Session[]
  onSelect: (id: string) => void
  activeId: string | null
}

/** Two-axis state badge: task-state x process-liveness. */
function StateBadge({ session }: { session: Session }) {
  const { taskState, processAlive } = session

  // Derived color
  let bg: string
  let label: string

  if (!processAlive) {
    bg = theme.colors.agentIdle
    label = 'dead'
  } else if (taskState === 'completed') {
    bg = theme.colors.success
    label = 'ok'
  } else if (taskState === 'running') {
    bg = theme.colors.agentActive
    label = 'live'
  } else if (taskState === 'failed') {
    bg = theme.colors.error
    label = 'fail'
  } else if (taskState === 'cancelled') {
    bg = theme.colors.warning
    label = 'cancel'
  } else {
    bg = theme.colors.fgMuted
    label = taskState
  }

  return (
    <span
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: bg,
        flexShrink: 0,
        marginRight: 6,
        boxShadow: processAlive ? `0 0 6px ${bg}` : 'none',
      }}
      title={`${taskState} | process: ${processAlive ? 'alive' : 'dead'}`}
    >
      {/* invisible label for a11y */}
      <span style={{ display: 'none' }}>{label}</span>
    </span>
  )
}

export function FleetView({ sessions, onSelect, activeId }: FleetViewProps) {
  if (sessions.length === 0) {
    return (
      <div
        style={{
          padding: theme.spacing.lg,
          color: theme.colors.fgMuted,
          fontSize: theme.fontSize.sm,
          textAlign: 'center',
        }}
      >
        No active sessions
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <div
        style={{
          padding: `${theme.spacing.sm}px ${theme.spacing.md}px`,
          fontSize: theme.fontSize.xs,
          color: theme.colors.fgMuted,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
      >
        Fleet ({sessions.length})
      </div>
      {sessions.map((session) => (
        <button
          key={session.id}
          onClick={() => onSelect(session.id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: `${theme.spacing.sm}px ${theme.spacing.md}px`,
            background: session.id === activeId ? theme.colors.bgHover : 'transparent',
            border: 'none',
            borderLeft: `3px solid ${session.id === activeId ? theme.colors.accent : 'transparent'}`,
            color: session.id === activeId ? theme.colors.fg : theme.colors.fgDim,
            cursor: 'pointer',
            fontSize: theme.fontSize.sm,
            textAlign: 'left',
            width: '100%',
            transition: 'background 0.15s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = theme.colors.bgHover
          }}
          onMouseLeave={(e) => {
            if (session.id !== activeId) {
              e.currentTarget.style.background = 'transparent'
            }
          }}
        >
          <StateBadge session={session} />
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {session.title}
          </span>
          <span style={{ fontSize: theme.fontSize.xs, color: theme.colors.fgMuted, flexShrink: 0 }}>
            {session.messageCount}
          </span>
        </button>
      ))}
    </div>
  )
}

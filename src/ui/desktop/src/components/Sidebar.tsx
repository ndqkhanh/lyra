import React from 'react'
import { theme } from '../styles/theme'
import { FleetView } from './FleetView'
import type { Session, ProviderInfo } from '../hooks/useLyraAPI'

interface SidebarProps {
  sessions: Session[]
  activeId: string | null
  providers: ProviderInfo[]
  onSelectSession: (id: string) => void
  onCreateSession: () => void
  onDeleteSession: (id: string) => void
  visible: boolean
}

export function Sidebar({
  sessions,
  activeId,
  providers,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  visible,
}: SidebarProps) {
  if (!visible) return null

  const providerCount = providers.length
  const modelCount = providers.reduce((acc, p) => acc + p.models.length, 0)

  return (
    <div
      style={{
        width: 240,
        background: theme.colors.bg,
        borderRight: `1px solid ${theme.colors.border}`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: `${theme.spacing.lg}px`,
          borderBottom: `1px solid ${theme.colors.border}`,
        }}
      >
        <div
          style={{
            fontSize: theme.fontSize.heading,
            fontWeight: 700,
            color: theme.colors.accent,
          }}
        >
          Lyra
        </div>
        <div style={{ fontSize: theme.fontSize.xs, color: theme.colors.fgMuted, marginTop: 2 }}>
          Desktop {providerCount > 0 ? `- ${providerCount} providers` : ''}
        </div>
      </div>

      {/* Fleet / Sessions */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <FleetView sessions={sessions} onSelect={onSelectSession} activeId={activeId} />
      </div>

      {/* Session actions */}
      <div
        style={{
          padding: `${theme.spacing.sm}px ${theme.spacing.md}px`,
          borderTop: `1px solid ${theme.colors.border}`,
          display: 'flex',
          gap: theme.spacing.sm,
        }}
      >
        <button
          onClick={onCreateSession}
          style={{
            flex: 1,
            padding: `${theme.spacing.sm}px ${theme.spacing.md}px`,
            background: theme.colors.accent,
            color: '#fff',
            borderRadius: theme.radius.md,
            fontSize: theme.fontSize.sm,
            fontWeight: 600,
            transition: 'opacity 0.15s',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.85' }}
          onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
        >
          + New Session
        </button>
      </div>

      {/* Provider config pane */}
      {providerCount > 0 && (
        <div
          style={{
            padding: `${theme.spacing.md}px`,
            borderTop: `1px solid ${theme.colors.border}`,
            fontSize: theme.fontSize.xs,
          }}
        >
          <div style={{ color: theme.colors.fgMuted, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Providers
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {providers.slice(0, 8).map((p) => (
              <div
                key={p.name}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  color: theme.colors.fgDim,
                  padding: '2px 0',
                }}
              >
                <span>{p.name}</span>
                <span style={{ color: theme.colors.fgMuted }}>{p.models.length} models</span>
              </div>
            ))}
            {providerCount > 8 && (
              <div style={{ color: theme.colors.fgMuted, padding: '2px 0' }}>
                +{providerCount - 8} more
              </div>
            )}
          </div>
          <div style={{ color: theme.colors.fgMuted, marginTop: 4 }}>
            {modelCount} models available
          </div>
        </div>
      )}

      {/* Skills browser placeholder */}
      <div
        style={{
          padding: `${theme.spacing.md}px`,
          borderTop: `1px solid ${theme.colors.border}`,
          fontSize: theme.fontSize.xs,
        }}
      >
        <div style={{ color: theme.colors.fgMuted, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Skills
        </div>
        <div style={{ color: theme.colors.fgMuted }}>
          Loaded from agent core
        </div>
      </div>

      {/* Delete active session */}
      {activeId && (
        <div
          style={{
            padding: `${theme.spacing.sm}px ${theme.spacing.md}px`,
            borderTop: `1px solid ${theme.colors.border}`,
          }}
        >
          <button
            onClick={() => onDeleteSession(activeId)}
            style={{
              width: '100%',
              padding: `${theme.spacing.xs}px ${theme.spacing.sm}px`,
              color: theme.colors.error,
              fontSize: theme.fontSize.xs,
              borderRadius: theme.radius.sm,
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,85,85,0.1)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
          >
            Delete Session
          </button>
        </div>
      )}
    </div>
  )
}

import { Box, Text } from '@lyra/ink'
import type { Color } from '@lyra/ink'
import { useEffect, useState } from 'react'

import { useGateway } from '../app/gatewayContext.js'
import type { EvolutionSnapshotResponse, EvolutionStatusResponse } from '../gatewayTypes.js'
import type { Theme } from '../theme.js'

interface EvolutionPanelProps {
  cols: number
  t: Theme
}

const LEVEL_COLORS: Record<string, Color> = {
  autonomous: '#FF5252',
  operator: '#FFD740',
  advisor: '#448AFF',
  observer: '#69F0AE',
}

const LEVEL_ICON: Record<string, string> = {
  autonomous: '⬤',
  operator: '◈',
  advisor: '◆',
  observer: '◉',
}

export function EvolutionPanel({ cols, t }: EvolutionPanelProps) {
  const { rpc } = useGateway()
  const [status, setStatus] = useState<EvolutionStatusResponse | null>(null)
  const [snapshot, setSnapshot] = useState<EvolutionSnapshotResponse | null>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let active = true
    const poll = () => {
      if (!active) return
      rpc('evolution.snapshot', {}).then((s) => {
        if (active && s) {
          setStatus(s.status as EvolutionStatusResponse)
          setSnapshot(s as EvolutionSnapshotResponse)
        }
      }).catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [rpc])

  if (!status) return null

  const levelColor: Color = LEVEL_COLORS[status.meta_level] ?? t.color.muted
  const icon = LEVEL_ICON[status.meta_level] ?? '●'
  const compact = cols < 100

  return (
    <Box flexDirection="column" flexShrink={0}>
      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.muted}>{'──'}</Text>
        <Text color={levelColor} bold>
          {' '}{icon} {status.meta_level.toUpperCase()}
        </Text>
        <Text color={t.color.muted}> · trust </Text>
        <Text color={t.color.ok}>{status.trust_score.toFixed(3)}</Text>
        <Text color={t.color.muted}> · fitness </Text>
        <Text color={t.color.accent}>{status.current_fitness.toFixed(3)}</Text>
      </Box>

      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.accent}>
          {expanded ? '▾' : '▸'} Tab to toggle evolution details
        </Text>
      </Box>

      {expanded && (
        <Box flexDirection="column" paddingX={2} paddingY={0}>
          <Box flexDirection={compact ? 'column' : 'row'} marginTop={1}>
            <Box flexDirection="column" marginRight={compact ? 0 : 4}>
              <Detail label="Level" value={status.meta_level} color={levelColor} t={t} />
              <Detail label="Trust" value={status.trust_score.toFixed(4)} color={t.color.ok} t={t} />
              <Detail label="Fitness" value={status.current_fitness.toFixed(4)} color={t.color.accent} t={t} />
              <Detail label="Cycles" value={String(status.cycles_completed)} color={t.color.text} t={t} />
              <Detail label="Improvement" value={`+${status.total_improvement.toFixed(4)}`} color={t.color.ok} t={t} />
            </Box>
            <Box flexDirection="column">
              <Detail label="Mutations" value={String(status.mutation_count)} color={t.color.text} t={t} />
              <Detail label="Active Goals" value={String(status.active_goals)} color={t.color.warn} t={t} />
              <Detail label="Pending Goals" value={String(status.pending_goals)} color={t.color.muted} t={t} />
              <Detail label="Claims" value={String(status.claims_count)} color={t.color.muted} t={t} />
              <Detail label="Snapshots" value={String(status.snapshots_available)} color={t.color.muted} t={t} />
            </Box>
          </Box>

          {snapshot && snapshot.recent_cycles.length > 0 && (
            <Box flexDirection="column" marginTop={1}>
              <Text color={t.color.muted}>Recent Cycles:</Text>
              {snapshot.recent_cycles.map((c) => (
                <Box key={c.id} flexDirection="row">
                  <Text color={t.color.muted}>  #{c.id}</Text>
                  <Text color={c.improvement > 0 ? t.color.ok : t.color.error}>
                    {' '}{c.improvement > 0 ? '+' : ''}{c.improvement.toFixed(4)}
                  </Text>
                  <Text color={c.council_decision === 'approved' ? t.color.ok : t.color.error}>
                    {' '}{c.council_decision}
                  </Text>
                  <Text color={t.color.muted}> {c.duration_ms.toFixed(0)}ms</Text>
                </Box>
              ))}
            </Box>
          )}

          {snapshot && snapshot.goals.length > 0 && (
            <Box flexDirection="column" marginTop={1}>
              <Text color={t.color.muted}>Goals:</Text>
              {snapshot.goals.slice(0, 5).map((g) => (
                <Box key={g.id} flexDirection="row">
                  <Text color={t.color.muted}>  [{g.status}]</Text>
                  <Text color={t.color.text}> {g.description}</Text>
                </Box>
              ))}
            </Box>
          )}

          {status.safe_mode && (
            <Box marginTop={1}>
              <Text color={t.color.ok}>▸ Safe mode active — council reviews all mutations</Text>
            </Box>
          )}
        </Box>
      )}
    </Box>
  )
}

function Detail({ label, value, color, t }: { label: string; value: string; color: Color; t: Theme }) {
  return (
    <Box flexDirection="row">
      <Text color={t.color.muted}>{label}: </Text>
      <Text color={color}>{value}</Text>
    </Box>
  )
}

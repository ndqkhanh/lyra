import { Box, Text } from '@lyra/ink'
import type { Color } from '@lyra/ink'
import { useEffect, useState } from 'react'

import { useGateway } from '../app/gatewayContext.js'
import type { RoutingStatusResponse } from '../gatewayTypes.js'
import type { Theme } from '../theme.js'

interface RoutingPanelProps {
  cols: number
  t: Theme
}

const STRATEGY_LABELS: Record<string, string> = {
  cost_optimal: 'Cost-Optimal',
  performance_max: 'Performance Max',
  balanced: 'Balanced',
  multi_turn: 'Multi-Turn',
  conformal: 'Conformal',
}

export function RoutingPanel({ cols, t }: RoutingPanelProps) {
  const { rpc } = useGateway()
  const [routing, setRouting] = useState<RoutingStatusResponse | null>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let active = true
    const poll = () => {
      if (!active) return
      rpc('routing.status', {}).then((s) => {
        if (active && s) setRouting(s as RoutingStatusResponse)
      }).catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [rpc])

  if (!routing) return null

  const strategyLabel = STRATEGY_LABELS[routing.strategy] ?? routing.strategy
  const tierColors: Record<string, Color> = {
    cheap: t.color.muted,
    fast: t.color.ok,
    standard: t.color.accent,
    reasoning: '#FFD740',
  }

  return (
    <Box flexDirection="column" flexShrink={0}>
      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.muted}>{'──'}</Text>
        <Text color={t.color.accent} bold>
          {' '}{strategyLabel}
        </Text>
        <Text color={t.color.muted}> · </Text>
        <Text color={t.color.text}>{routing.model_count} models</Text>
        <Text color={t.color.muted}> · </Text>
        <Text color={t.color.ok}>
          ${routing.router_snapshot.total_cost.toFixed(4)}
        </Text>
      </Box>

      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.accent}>
          {expanded ? '▾' : '▸'} Tab to toggle cascade details
        </Text>
      </Box>

      {expanded && (
        <Box flexDirection="column" paddingX={2} paddingY={0}>
          <Box flexDirection="row">
            {Object.entries(routing.router_snapshot.decisions_by_tier).map(([tier, count]) => (
              <Box key={tier} marginRight={2} flexDirection="row">
                <Text color={tierColors[tier] ?? t.color.muted}>{tier}: </Text>
                <Text color={t.color.text}>{String(count)}</Text>
              </Box>
            ))}
          </Box>
          <DetailRow label="Confidence" value={routing.router_snapshot.avg_confidence.toFixed(3)} color={t.color.text} t={t} />
          <DetailRow label="Decisions" value={String(routing.decision_count)} color={t.color.text} t={t} />
          <DetailRow label="Turns" value={String(routing.turn_count)} color={t.color.text} t={t} />
          <DetailRow label="Fallback Rate" value={routing.router_snapshot.fallback_rate.toFixed(3)} color={t.color.warn} t={t} />
        </Box>
      )}
    </Box>
  )
}

function DetailRow({ label, value, color, t }: { label: string; value: string; color: Color; t: Theme }) {
  return (
    <Box flexDirection="row">
      <Text color={t.color.muted}>{label}: </Text>
      <Text color={color}>{value}</Text>
    </Box>
  )
}

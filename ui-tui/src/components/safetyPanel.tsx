import { Box, Text } from '@lyra/ink'
import type { Color } from '@lyra/ink'
import { useEffect, useState } from 'react'

import { useGateway } from '../app/gatewayContext.js'
import type { SafetyStatusResponse } from '../gatewayTypes.js'
import type { Theme } from '../theme.js'

interface SafetyPanelProps {
  cols: number
  t: Theme
}

const TIER_COLORS: Record<string, Color> = {
  autonomous: '#FF5252',
  observer: '#69F0AE',
  operator: '#FFD740',
  assistant: '#448AFF',
}

const TIER_ICONS: Record<string, string> = {
  autonomous: '⬤',
  observer: '◉',
  operator: '◈',
  assistant: '◆',
}

export function SafetyPanel({ cols, t }: SafetyPanelProps) {
  const { rpc } = useGateway()
  const [safety, setSafety] = useState<SafetyStatusResponse | null>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let active = true
    const poll = () => {
      if (!active) return
      rpc('safety.status', {}).then((s) => {
        if (active && s) setSafety(s as SafetyStatusResponse)
      }).catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 3000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [rpc])

  if (!safety) return null

  const tierColor: Color = TIER_COLORS[safety.governance_tier] ?? t.color.muted
  const tierIcon = TIER_ICONS[safety.governance_tier] ?? '●'
  const compact = cols < 100

  return (
    <Box flexDirection="column" flexShrink={0}>
      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.muted}>
          {'──'}
        </Text>
        <Text
          color={safety.quarantine_active ? t.color.error : tierColor}
          bold={safety.quarantine_active}
        >
          {' '}{tierIcon} {safety.governance_tier.toUpperCase()}
        </Text>
        <Text color={t.color.muted}> · trust </Text>
        <Text color={t.color.ok}>{safety.trust_score.toFixed(2)}</Text>
        {safety.quarantine_active && (
          <Text color={t.color.error} bold>
            {' '}QUARANTINE
          </Text>
        )}
      </Box>

      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.accent}>
          {expanded ? '▾' : '▸'} Tab to toggle details
        </Text>
      </Box>

      {expanded && (
        <Box flexDirection={compact ? 'column' : 'row'} paddingX={2} paddingY={0}>
          <Box flexDirection="column" marginRight={compact ? 0 : 4}>
            <DetailRow label="Governance Tier" value={safety.governance_tier} color={tierColor} t={t} />
            <DetailRow label="Trust Score" value={safety.trust_score.toFixed(4)} color={t.color.ok} t={t} />
            <DetailRow label="Actions" value={String(safety.action_count)} color={t.color.text} t={t} />
            <DetailRow label="Violations" value={String(safety.violation_count)} color={safety.violation_count > 0 ? t.color.error : t.color.ok} t={t} />
          </Box>
          <Box flexDirection="column">
            <DetailRow label="Containment" value={safety.containment_active ? 'active' : 'inactive'} color={safety.containment_active ? t.color.ok : t.color.warn} t={t} />
            <DetailRow label="Quarantine" value={safety.quarantine_active ? 'ACTIVE' : 'inactive'} color={safety.quarantine_active ? t.color.error : t.color.ok} t={t} />
            <DetailRow label="Escape Signals" value={String(safety.escape_signals)} color={safety.escape_signals > 0 ? t.color.error : t.color.ok} t={t} />
            <DetailRow label="Self-Modify" value={String(safety.self_modify_attempts)} color={safety.self_modify_attempts > 0 ? t.color.warn : t.color.ok} t={t} />
            <DetailRow label="Blocked Flows" value={String(safety.blocked_flows)} color={safety.blocked_flows > 0 ? t.color.warn : t.color.ok} t={t} />
            <DetailRow label="Tainted Data" value={String(safety.tainted_count)} color={t.color.muted} t={t} />
          </Box>
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

import { Box, Text } from '@lyra/ink'
import type { Color } from '@lyra/ink'
import { useEffect, useState } from 'react'

import { useGateway } from '../app/gatewayContext.js'
import type { FleetStatusResponse } from '../gatewayTypes.js'
import type { Theme } from '../theme.js'

interface FleetPanelProps {
  cols: number
  t: Theme
}

const STATE_COLORS: Record<string, Color> = {
  running: '#69F0AE',
  idle: '#448AFF',
  scaling: '#FFD740',
  draining: '#FF5252',
  unknown: '#888888',
}

export function FleetPanel({ cols, t }: FleetPanelProps) {
  const { rpc } = useGateway()
  const [fleet, setFleet] = useState<FleetStatusResponse | null>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let active = true
    const poll = () => {
      if (!active) return
      rpc('fleet.status', {}).then((s) => {
        if (active && s) setFleet(s as FleetStatusResponse)
      }).catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 4000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [rpc])

  if (!fleet) return null

  const stateColor: Color = STATE_COLORS[fleet.state] ?? t.color.muted
  const total = fleet.completed_tasks + fleet.failed_tasks + fleet.pending_tasks

  return (
    <Box flexDirection="column" flexShrink={0}>
      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.muted}>{'──'}</Text>
        <Text color={t.color.accent} bold>
          {' '}Fleet
        </Text>
        <Text color={stateColor}> {fleet.state}</Text>
        <Text color={t.color.muted}> · </Text>
        <Text color={t.color.text}>{fleet.total_agents} agents</Text>
        <Text color={t.color.muted}> · </Text>
        <Text color={t.color.ok}>{fleet.active_agents} active</Text>
        {fleet.squads > 0 && (
          <Text color={t.color.muted}> · {fleet.squads} squads</Text>
        )}
      </Box>

      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.accent}>
          {expanded ? '▾' : '▸'} Tab to toggle fleet details
        </Text>
      </Box>

      {expanded && (
        <Box flexDirection="column" paddingX={2} paddingY={0}>
          <Box flexDirection="row" flexWrap="wrap">
            <MetricBox label="Agents" value={String(fleet.total_agents)} color={t.color.accent} t={t} />
            <MetricBox label="Active" value={String(fleet.active_agents)} color={t.color.ok} t={t} />
            <MetricBox label="Idle" value={String(fleet.idle_agents)} color={t.color.muted} t={t} />
            <MetricBox label="Squads" value={String(fleet.squads)} color="#FFD740" t={t} />
          </Box>
          <Box flexDirection="row" flexWrap="wrap" marginTop={1}>
            <MetricBox label="Pending" value={String(fleet.pending_tasks)} color={t.color.warn} t={t} />
            <MetricBox label="Running" value={String(fleet.running_tasks)} color="#448AFF" t={t} />
            <MetricBox label="Done" value={String(fleet.completed_tasks)} color={t.color.ok} t={t} />
            <MetricBox label="Failed" value={String(fleet.failed_tasks)} color={fleet.failed_tasks > 0 ? t.color.error : t.color.muted} t={t} />
          </Box>
          <Box flexDirection="row" marginTop={1}>
            <Text color={t.color.muted}>
              Throughput: {fleet.throughput.toFixed(1)} tasks/s · {total} total tasks
            </Text>
          </Box>
        </Box>
      )}
    </Box>
  )
}

function MetricBox({ label, value, color, t }: { label: string; value: string; color: Color; t: Theme }) {
  return (
    <Box flexDirection="column" marginRight={3}>
      <Text color={t.color.muted}>{label}</Text>
      <Text color={color} bold>{value}</Text>
    </Box>
  )
}

import { Box, Text } from '@lyra/ink'
import type { Color } from '@lyra/ink'
import { useEffect, useState } from 'react'

import { useGateway } from '../app/gatewayContext.js'
import type { MemoryStatsResponse } from '../gatewayTypes.js'
import type { Theme } from '../theme.js'

interface MemoryPanelProps {
  cols: number
  t: Theme
}

const TIER_LABELS: Record<string, string> = {
  L0: 'Working',
  L1: 'Episodic',
  L2: 'Semantic',
  L3: 'Procedural',
}

export function MemoryPanel({ cols, t }: MemoryPanelProps) {
  const { rpc } = useGateway()
  const [memory, setMemory] = useState<MemoryStatsResponse | null>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let active = true
    const poll = () => {
      if (!active) return
      rpc('memory.stats', {}).then((s) => {
        if (active && s) setMemory(s as MemoryStatsResponse)
      }).catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [rpc])

  if (!memory) return null

  const totalEntries =
    memory.working_entries +
    memory.episodic_events +
    memory.semantic_facts +
    memory.procedural_count

  return (
    <Box flexDirection="column" flexShrink={0}>
      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.muted}>{'──'}</Text>
        <Text color={t.color.accent} bold>
          {' '}Memory
        </Text>
        <Text color={t.color.muted}> · </Text>
        <Text color={t.color.text}>{totalEntries} entries</Text>
        {memory.kg_nodes > 0 && (
          <Text color={t.color.muted}>
            {' · KG '}{memory.kg_nodes}n/{memory.kg_edges}e
          </Text>
        )}
        {memory.active_memories > 0 && (
          <Text color={t.color.ok}>
            {' · '}{memory.active_memories} active
          </Text>
        )}
      </Box>

      <Box flexDirection="row" paddingX={1}>
        <Text color={t.color.accent}>
          {expanded ? '▾' : '▸'} Tab to toggle memory details
        </Text>
      </Box>

      {expanded && (
        <Box flexDirection="column" paddingX={2} paddingY={0}>
          <Box flexDirection="row" flexWrap="wrap">
            <TierBlock tier="L0" label="Working" count={memory.working_entries} extra={`${memory.working_tokens} tok`} color={t.color.ok} t={t} />
            <TierBlock tier="L1" label="Episodic" count={memory.episodic_events} color={t.color.accent} t={t} />
            <TierBlock tier="L2" label="Semantic" count={memory.semantic_facts} color="#448AFF" t={t} />
            <TierBlock tier="L3" label="Procedural" count={memory.procedural_count} color="#FFD740" t={t} />
          </Box>
          {memory.total_memories > 0 && (
            <Box flexDirection="row" marginTop={1}>
              <DetailRow label="Total" value={String(memory.total_memories)} color={t.color.text} t={t} />
              <DetailRow label="Active" value={String(memory.active_memories)} color={t.color.ok} t={t} />
              <DetailRow label="Dormant" value={String(memory.dormant_memories)} color={t.color.muted} t={t} />
              <DetailRow label="Budget" value={memory.budget_status} color={t.color.warn} t={t} />
            </Box>
          )}
        </Box>
      )}
    </Box>
  )
}

function TierBlock({
  tier, label, count, extra, color, t,
}: {
  tier: string
  label: string
  count: number
  extra?: string
  color: Color
  t: Theme
}) {
  return (
    <Box flexDirection="column" marginRight={3}>
      <Box flexDirection="row">
        <Text color={color} bold>{tier}</Text>
        <Text color={t.color.muted}> {label}</Text>
      </Box>
      <Text color={t.color.text}>
        {'  '}{count}{extra ? ` · ${extra}` : ''}
      </Text>
    </Box>
  )
}

function DetailRow({ label, value, color, t }: { label: string; value: string; color: Color; t: Theme }) {
  return (
    <Box flexDirection="row" marginRight={3}>
      <Text color={t.color.muted}>{label}: </Text>
      <Text color={color}>{value}</Text>
    </Box>
  )
}

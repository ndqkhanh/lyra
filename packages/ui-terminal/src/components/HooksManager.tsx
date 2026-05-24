import React, { useState, useEffect, useMemo } from 'react'
import { Box, Text, useInput } from 'ink'
import { colors } from '@lyra/ui-core'

interface Hook {
  name: string
  event: string
  enabled: boolean
  description: string
  lastRun?: string
  status: 'ok' | 'error' | 'never'
}

interface HooksManagerProps {
  visible: boolean
  onClose: () => void
}

const SERVER_URL = 'http://localhost:3737'

const FALLBACK_HOOKS: Hook[] = [
  { name: 'PreToolUse validator', event: 'PreToolUse', enabled: true, description: 'Validates tool parameters before execution', status: 'ok', lastRun: '2 min ago' },
  { name: 'PostToolUse formatter', event: 'PostToolUse', enabled: true, description: 'Auto-formats edited files', status: 'ok', lastRun: '1 min ago' },
  { name: 'Stop hook verifier', event: 'Stop', enabled: true, description: 'Runs final verification before exit', status: 'ok', lastRun: '5 min ago' },
  { name: 'SessionStart notifier', event: 'SessionStart', enabled: false, description: 'Sends notification on session start', status: 'never' },
  { name: 'console.log auditor', event: 'PostToolUse', enabled: true, description: 'Checks modified files for console.log', status: 'ok', lastRun: '3 min ago' },
]

export function HooksManager({ visible, onClose }: HooksManagerProps) {
  const [hooks, setHooks] = useState<Hook[]>(FALLBACK_HOOKS)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!visible) return
    let cancelled = false
    setLoading(true)
    fetch(`${SERVER_URL}/hooks`)
      .then(r => r.json() as Promise<{ hooks?: Hook[] }>)
      .then(data => {
        if (!cancelled && data.hooks?.length) setHooks(data.hooks)
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [visible])

  const grouped = useMemo(() => {
    const groups: Record<string, Hook[]> = {}
    for (const hook of hooks) {
      if (!groups[hook.event]) groups[hook.event] = []
      groups[hook.event].push(hook)
    }
    return groups
  }, [hooks])

  const flatHooks = hooks

  useInput((_input, key) => {
    if (!visible) return
    if (key.escape) { onClose(); return }
    if (key.upArrow) { setSelectedIndex(p => Math.max(0, p - 1)); return }
    if (key.downArrow) { setSelectedIndex(p => Math.min(flatHooks.length - 1, p + 1)); return }
  })

  if (!visible) return null

  const statusIcon: Record<string, string> = { ok: '✓', error: '✗', never: '○' }
  const statusColor: Record<string, string> = { ok: colors.success, error: colors.error, never: colors.timestamp }

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} height={20}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>Hooks Manager</Text>
        <Text dimColor>↑↓ navigate  Esc close</Text>
      </Box>

      <Box marginBottom={1}>
        <Text dimColor>Enabled: {hooks.filter(h => h.enabled).length}/{hooks.length}</Text>
      </Box>

      <Box flexDirection="column" flexGrow={1}>
        {loading && <Text color={colors.muted}>Loading hooks...</Text>}
        {!loading && Object.entries(grouped).map(([event, eventHooks]) => (
          <Box key={event} flexDirection="column" marginBottom={1}>
            <Text bold color={colors.info}>{event}</Text>
            {eventHooks.map((hook) => {
              const globalIdx = flatHooks.indexOf(hook)
              const isSelected = globalIdx === selectedIndex
              return (
                <Box key={hook.name} paddingLeft={2}>
                  <Text color={isSelected ? colors.userPrompt : colors.timestamp} bold={isSelected}>
                    {isSelected ? '❯ ' : '  '}
                  </Text>
                  <Text color={hook.enabled ? statusColor[hook.status] : colors.muted}>
                    {hook.enabled ? statusIcon[hook.status] : '○'}
                  </Text>
                  <Text> {hook.name}</Text>
                  <Text dimColor> — {hook.description}</Text>
                  {hook.lastRun && <Text dimColor> (last: {hook.lastRun})</Text>}
                </Box>
              )
            })}
          </Box>
        ))}
      </Box>
    </Box>
  )
}

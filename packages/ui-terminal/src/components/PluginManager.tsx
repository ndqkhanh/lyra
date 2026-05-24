import React, { useState, useEffect, useMemo } from 'react'
import { Box, Text, useInput } from 'ink'
import { colors } from '@lyra/ui-core'

interface Plugin {
  name: string
  version: string
  enabled: boolean
  description: string
  tokenCost: number
}

interface PluginManagerProps {
  visible: boolean
  onClose: () => void
}

const SERVER_URL = 'http://localhost:3737'

const FALLBACK_PLUGINS: Plugin[] = [
  { name: 'claude-mem', version: '1.0.0', enabled: true, description: 'Persistent memory via semantic search', tokenCost: 150 },
  { name: 'oh-my-claudecode', version: '4.13.6', enabled: true, description: 'Multi-agent orchestration layer', tokenCost: 500 },
]

export function PluginManager({ visible, onClose }: PluginManagerProps) {
  const [plugins, setPlugins] = useState<Plugin[]>(FALLBACK_PLUGINS)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [tab, setTab] = useState<'installed' | 'marketplace'>('installed')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!visible) return
    let cancelled = false
    setLoading(true)
    fetch(`${SERVER_URL}/plugins`)
      .then(r => r.json() as Promise<{ plugins?: Plugin[] }>)
      .then(data => {
        if (!cancelled && data.plugins?.length) setPlugins(data.plugins)
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [visible])

  const displayPlugins = useMemo(
    () => (tab === 'installed' ? plugins : plugins),
    [plugins, tab]
  )

  const totalTokens = plugins.reduce((sum, p) => sum + (p.enabled ? p.tokenCost : 0), 0)

  useInput((input, key) => {
    if (!visible) return
    if (key.escape) { onClose(); return }
    if (key.upArrow) { setSelectedIndex(p => Math.max(0, p - 1)); return }
    if (key.downArrow) { setSelectedIndex(p => Math.min(displayPlugins.length - 1, p + 1)); return }
    if (input === '1') { setTab('installed'); setSelectedIndex(0); return }
    if (input === '2') { setTab('marketplace'); setSelectedIndex(0); return }
  })

  if (!visible) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} height={18}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>Plugin Manager</Text>
        <Text dimColor>↑↓ navigate  Esc close</Text>
      </Box>

      <Box marginBottom={1}>
        <Text color={tab === 'installed' ? colors.userPrompt : colors.timestamp} bold={tab === 'installed'}>
          [1] Installed ({plugins.length})
        </Text>
        <Text>  </Text>
        <Text color={tab === 'marketplace' ? colors.userPrompt : colors.timestamp} bold={tab === 'marketplace'}>
          [2] Marketplace
        </Text>
      </Box>

      <Box marginBottom={1}>
        <Text dimColor>Token cost: </Text>
        <Text color={totalTokens > 1000 ? colors.warning : colors.info}>{totalTokens}/hr</Text>
      </Box>

      <Box flexDirection="column" flexGrow={1}>
        {loading && <Text color={colors.muted}>Loading plugins...</Text>}
        {!loading && displayPlugins.length === 0 && (
          <Text color={colors.muted}>No plugins installed</Text>
        )}
        {displayPlugins.map((plugin, i) => (
          <Box key={plugin.name}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
            </Text>
            <Text color={plugin.enabled ? colors.success : colors.error}>
              {plugin.enabled ? '●' : '○'}
            </Text>
            <Text> {plugin.name}@{plugin.version}</Text>
            <Text dimColor> — {plugin.description}</Text>
            <Text dimColor> ({plugin.tokenCost}t/hr)</Text>
          </Box>
        ))}
      </Box>

      <Box marginTop={1}>
        <Text dimColor>/plugin [install|uninstall|enable|disable|update]</Text>
      </Box>
    </Box>
  )
}

import React, { useState, useEffect, useCallback } from 'react'
import { Box, Text, useInput } from 'ink'
import { useUIStore, colors, symbols } from '@lyra/ui-core'
import type { ProviderInfo, ModelInfo } from '@lyra/ui-core'

interface ModelPickerProps {
  visible: boolean
  onSelect: (providerKey: string, modelSlug: string) => void
  onCancel: () => void
  onNeedKey: (providerKey: string) => void
}

interface FlatEntry {
  provider: ProviderInfo
  model: ModelInfo
  isSelected: boolean
  index: number
}

export function ModelPicker({ visible, onSelect, onCancel, onNeedKey }: ModelPickerProps) {
  const providers = useUIStore(state => state.providers)
  const currentModel = useUIStore(state => state.currentModel)
  const currentProvider = useUIStore(state => state.currentProvider)

  const [selectedIndex, setSelectedIndex] = useState(0)
  const [entries, setEntries] = useState<FlatEntry[]>([])
  const [showKeyPrompt, setShowKeyPrompt] = useState(false)
  const [keyPromptProvider, setKeyPromptProvider] = useState<ProviderInfo | null>(null)
  const [keyInput, setKeyInput] = useState('')
  const [keyError, setKeyError] = useState('')
  const [saving, setSaving] = useState(false)

  // Build flat entry list from providers
  useEffect(() => {
    if (!visible || providers.length === 0) return

    const flat: FlatEntry[] = []
    let idx = 0

    for (const provider of providers) {
      for (const model of provider.models) {
        flat.push({
          provider,
          model,
          isSelected: currentModel === model.slug && currentProvider === provider.key,
          index: idx,
        })
        idx++
      }
    }

    setEntries(flat)
    setSelectedIndex(0)
  }, [visible, providers, currentModel, currentProvider])

  // Keyboard navigation
  useInput((input, key) => {
    if (!visible) return

    if (showKeyPrompt) {
      if (key.escape) {
        setShowKeyPrompt(false)
        setKeyInput('')
        setKeyError('')
        return
      }
      if (key.return) {
        handleSaveKey()
        return
      }
      if (key.backspace || key.delete) {
        setKeyInput(prev => prev.slice(0, -1))
        setKeyError('')
        return
      }
      if (input && !key.ctrl && !key.meta) {
        setKeyInput(prev => prev + input)
        setKeyError('')
      }
      return
    }

    if (key.escape) {
      onCancel()
      return
    }

    if (key.upArrow) {
      setSelectedIndex(prev => Math.max(0, prev - 1))
      return
    }

    if (key.downArrow) {
      setSelectedIndex(prev => Math.min(entries.length - 1, prev + 1))
      return
    }

    if (key.return && entries.length > 0) {
      const entry = entries[selectedIndex]
      if (entry) {
        handleSelect(entry)
      }
      return
    }
  })

  const handleSelect = useCallback(async (entry: FlatEntry) => {
    const hasKey = entry.provider.key === 'ollama' || entry.provider.key === 'lmstudio'
    if (hasKey) {
      onSelect(entry.provider.key, entry.model.slug)
      return
    }

    // Check if credentials exist for this provider
    try {
      const resp = await fetch(`http://localhost:3737/auth/check/${entry.provider.key}`)
      const data = await resp.json() as { has_key: boolean }
      if (data.has_key) {
        // Save model selection
        await fetch('http://localhost:3737/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            last_model: `${entry.provider.key}:${entry.model.slug}`,
            last_provider: entry.provider.key,
          }),
        })
        onSelect(entry.provider.key, entry.model.slug)
      } else {
        // Need key
        setKeyPromptProvider(entry.provider)
        setShowKeyPrompt(true)
        setKeyInput('')
        setKeyError('')
      }
    } catch {
      // If server not available, still allow selection
      onSelect(entry.provider.key, entry.model.slug)
    }
  }, [onSelect])

  const handleSaveKey = useCallback(async () => {
    if (!keyPromptProvider || !keyInput.trim()) {
      setKeyError('API key is required')
      return
    }

    setSaving(true)
    setKeyError('')

    try {
      const resp = await fetch('http://localhost:3737/auth/set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: keyPromptProvider.key,
          key: keyInput.trim(),
        }),
      })
      const data = await resp.json() as { ok: boolean; error?: string }
      if (data.ok) {
        setShowKeyPrompt(false)
        setKeyInput('')
        onNeedKey(keyPromptProvider.key)
      } else {
        setKeyError(data.error || 'Failed to save key')
      }
    } catch {
      setKeyError('Cannot connect to server')
    } finally {
      setSaving(false)
    }
  }, [keyPromptProvider, keyInput, onNeedKey])

  if (!visible) return null

  // API Key prompt overlay
  if (showKeyPrompt && keyPromptProvider) {
    const terminalWidth = process.stdout.columns || 100
    const boxWidth = Math.min(70, terminalWidth - 4)

    return (
      <Box flexDirection="column" paddingX={2} marginBottom={1}>
        <Text color={colors.separator}>
          {symbols.horizontalLine.repeat(boxWidth)}
        </Text>
        <Box flexDirection="column" paddingY={1}>
          <Text bold color={colors.info}>
            API Key Required — {keyPromptProvider.display_name}
          </Text>
          <Text color={colors.muted}>
            Paste your API key from{' '}
            <Text color={colors.filePath}>{keyPromptProvider.api_key_url || keyPromptProvider.website}</Text>
          </Text>
          <Box marginTop={1}>
            <Text color={colors.userPrompt}>❯ </Text>
            <Text color={keyInput ? colors.userText : colors.muted}>
              {keyInput || 'Paste API key...'}
              {keyInput.length === 0 ? '' : ''}
            </Text>
          </Box>
          {keyError ? (
            <Text color={colors.error}>{keyError}</Text>
          ) : null}
          {saving ? (
            <Text color={colors.thinking}>Saving...</Text>
          ) : null}
        </Box>
        <Box>
          <Text color={colors.shortcutKey}>Enter</Text>
          <Text color={colors.shortcutDescription}> to save · </Text>
          <Text color={colors.shortcutKey}>Esc</Text>
          <Text color={colors.shortcutDescription}> to cancel</Text>
        </Box>
        <Text color={colors.separator}>
          {symbols.horizontalLine.repeat(boxWidth)}
        </Text>
      </Box>
    )
  }

  // Model picker
  const terminalWidth = process.stdout.columns || 100
  const boxWidth = Math.min(80, terminalWidth - 4)
  const maxVisible = 12
  const startIdx = Math.max(0, selectedIndex - Math.floor(maxVisible / 2))
  const visibleEntries = entries.slice(startIdx, startIdx + maxVisible)

  // Group visible entries by provider for rendering headers
  let lastProviderKey = ''

  return (
    <Box flexDirection="column" paddingX={2} marginBottom={1}>
      <Text color={colors.separator}>
        {symbols.horizontalLine.repeat(boxWidth)}
      </Text>

      {/* Title */}
      <Box flexDirection="column" paddingY={1}>
        <Text bold color={colors.userPrompt}>
          Select model
        </Text>
        <Text color={colors.muted}>
          Switch between AI providers and models. Applies to this session and future sessions.
        </Text>
      </Box>

      {/* Model list */}
      <Box flexDirection="column">
        {entries.length === 0 ? (
          <Text color={colors.muted}>Loading providers...</Text>
        ) : (
          visibleEntries.map((entry) => {
            const isSelected = entry.index === selectedIndex
            const showHeader = entry.provider.key !== lastProviderKey
            lastProviderKey = entry.provider.key

            return (
              <Box key={`${entry.provider.key}:${entry.model.slug}`} flexDirection="column">
                {/* Provider header */}
                {showHeader && (
                  <Box marginTop={entry.index > 0 ? 1 : 0}>
                    <Text bold color={colors.info}>
                      {entry.provider.icon} {entry.provider.display_name}
                    </Text>
                    <Text color={colors.separator}>
                      {' ' + symbols.horizontalLine.repeat(
                        Math.max(4, boxWidth - entry.provider.display_name.length - 25)
                      )}
                    </Text>
                  </Box>
                )}

                {/* Model row */}
                <Box paddingLeft={2}>
                  <Text color={isSelected ? colors.userPrompt : colors.muted}>
                    {isSelected ? symbols.rightArrow : ' '}
                    {' '}
                  </Text>
                  <Text
                    color={isSelected ? colors.userPrompt : colors.userText}
                    bold={isSelected}
                  >
                    {entry.model.slug.padEnd(24)}
                  </Text>
                  <Text color={entry.isSelected ? colors.success : colors.muted}>
                    {entry.model.description}
                    {entry.isSelected ? ' ✓' : ''}
                  </Text>
                </Box>
              </Box>
            )
          })
        )}
      </Box>

      {/* Scroll indicator */}
      {entries.length > maxVisible && (
        <Box>
          <Text color={colors.muted}>
            {startIdx > 0 ? '↑ more ' : ''}
            {selectedIndex + 1}/{entries.length}
            {startIdx + maxVisible < entries.length ? ' more ↓' : ''}
          </Text>
        </Box>
      )}

      {/* Footer */}
      <Box marginTop={1}>
        <Text color={colors.separator}>
          {symbols.horizontalLine.repeat(boxWidth)}
        </Text>
      </Box>
      <Box>
        <Text color={colors.shortcutKey}>Enter</Text>
        <Text color={colors.shortcutDescription}> to confirm · </Text>
        <Text color={colors.shortcutKey}>Esc</Text>
        <Text color={colors.shortcutDescription}> to cancel · </Text>
        <Text color={colors.shortcutKey}>↑↓</Text>
        <Text color={colors.shortcutDescription}> to navigate</Text>
      </Box>
    </Box>
  )
}

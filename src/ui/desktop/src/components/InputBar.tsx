import React, { useCallback, useRef, useState } from 'react'
import { theme } from '../styles/theme'
import type { ProviderInfo } from '../hooks/useLyraAPI'

interface InputBarProps {
  onSend: (message: string, model?: string, provider?: string) => void
  onCancel: () => void
  isStreaming: boolean
  providers: ProviderInfo[]
  disabled?: boolean
}

export function InputBar({ onSend, onCancel, isStreaming, providers, disabled }: InputBarProps) {
  const [input, setInput] = useState('')
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [showModelPicker, setShowModelPicker] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const currentProvider = providers.find((p) => p.name === selectedProvider)
  const models = currentProvider?.models ?? []

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text) return
    onSend(text, selectedModel || undefined, selectedProvider || undefined)
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [input, onSend, selectedModel, selectedProvider])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [])

  return (
    <div
      style={{
        borderTop: `1px solid ${theme.colors.border}`,
        background: theme.colors.bg,
        padding: `${theme.spacing.md}px ${theme.spacing.lg}px`,
      }}
    >
      {/* Model picker row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: theme.spacing.sm,
          marginBottom: theme.spacing.sm,
        }}
      >
        <button
          onClick={() => setShowModelPicker(!showModelPicker)}
          style={{
            fontSize: theme.fontSize.xs,
            color: theme.colors.fgDim,
            padding: '2px 8px',
            borderRadius: theme.radius.sm,
            border: `1px solid ${theme.colors.borderLight}`,
            background: theme.colors.bgInput,
          }}
        >
          {selectedProvider || selectedModel
            ? `${selectedProvider || 'any'} / ${selectedModel || 'auto'}`
            : 'Model: auto'}
        </button>

        {showModelPicker && (
          <div
            style={{
              position: 'absolute',
              bottom: '100%',
              left: theme.spacing.lg,
              background: theme.colors.bgSurface,
              border: `1px solid ${theme.colors.border}`,
              borderRadius: theme.radius.lg,
              padding: theme.spacing.sm,
              boxShadow: theme.shadow.lg,
              maxHeight: 300,
              overflowY: 'auto',
              minWidth: 200,
              zIndex: 100,
            }}
          >
            <div style={{ fontSize: theme.fontSize.xs, color: theme.colors.fgMuted, marginBottom: 4, padding: '2px 8px' }}>
              Select provider & model:
            </div>
            {providers.map((p) => (
              <div key={p.name} style={{ marginBottom: 4 }}>
                <div
                  style={{
                    fontSize: theme.fontSize.xs,
                    color: theme.colors.accent,
                    padding: '2px 8px',
                    fontWeight: 600,
                  }}
                >
                  {p.name}
                </div>
                {p.models.slice(0, 10).map((m) => (
                  <button
                    key={m}
                    onClick={() => {
                      setSelectedProvider(p.name)
                      setSelectedModel(m)
                      setShowModelPicker(false)
                    }}
                    style={{
                      display: 'block',
                      width: '100%',
                      textAlign: 'left',
                      padding: '2px 16px',
                      fontSize: theme.fontSize.xs,
                      color: theme.colors.fgDim,
                      borderRadius: theme.radius.sm,
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = theme.colors.bgHover }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                  >
                    {m}
                  </button>
                ))}
              </div>
            ))}
            {providers.length === 0 && (
              <div style={{ fontSize: theme.fontSize.xs, color: theme.colors.fgMuted, padding: '4px 8px' }}>
                No providers loaded
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input row */}
      <div style={{ display: 'flex', gap: theme.spacing.sm, alignItems: 'flex-end' }}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Shift+Enter for new line)"
          disabled={disabled || isStreaming}
          rows={1}
          style={{
            flex: 1,
            minHeight: 36,
            maxHeight: 200,
            padding: `${theme.spacing.sm}px ${theme.spacing.md}px`,
            background: theme.colors.bgInput,
            border: `1px solid ${theme.colors.borderLight}`,
            borderRadius: theme.radius.md,
            color: theme.colors.fg,
            fontSize: theme.fontSize.md,
            resize: 'none',
            lineHeight: 1.5,
          }}
        />

        {isStreaming ? (
          <button
            onClick={onCancel}
            style={{
              height: 36,
              padding: `0 ${theme.spacing.lg}px`,
              background: theme.colors.error,
              color: '#fff',
              borderRadius: theme.radius.md,
              fontSize: theme.fontSize.sm,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.85' }}
            onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
          >
            Stop
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim() || disabled}
            style={{
              height: 36,
              padding: `0 ${theme.spacing.lg}px`,
              background: input.trim() ? theme.colors.accent : theme.colors.bgSurface,
              color: input.trim() ? '#fff' : theme.colors.fgMuted,
              borderRadius: theme.radius.md,
              fontSize: theme.fontSize.sm,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              cursor: input.trim() ? 'pointer' : 'not-allowed',
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={(e) => {
              if (input.trim()) e.currentTarget.style.opacity = '0.85'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = '1'
            }}
          >
            Send
          </button>
        )}
      </div>
    </div>
  )
}

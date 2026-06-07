import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { theme } from '../styles/theme'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  isStreaming?: boolean
}

interface ChatViewProps {
  messages: Message[]
  sessionId: string | null
}

/** Simple inline code block renderer with syntax coloring. */
function CodeBlock({ className, children }: { className?: string; children?: React.ReactNode }) {
  const language = className?.replace('language-', '') ?? ''
  const code = String(children).replace(/\n$/, '')
  return (
    <div style={{ position: 'relative' }}>
      {language && (
        <span
          style={{
            position: 'absolute',
            top: 4,
            right: 8,
            fontSize: theme.fontSize.xs,
            color: theme.colors.fgMuted,
          }}
        >
          {language}
        </span>
      )}
      <pre>
        <code className={className}>{code}</code>
      </pre>
    </div>
  )
}

/** Cost per million tokens for estimation (Anthropic Sonnet 4.6 rates). */
const COST_PER_M_INPUT = 3.0
const COST_PER_M_OUTPUT = 15.0

function estimateCost(content: string): { tokens: number; cost: number } {
  const tokens = Math.ceil(content.length / 4)
  const isUser = true // rough — we don't track role here
  const perMTokens = isUser ? COST_PER_M_INPUT : COST_PER_M_OUTPUT
  return { tokens, cost: (tokens / 1_000_000) * perMTokens }
}

export function ChatView({ messages, sessionId }: ChatViewProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: `${theme.spacing.lg}px`,
        display: 'flex',
        flexDirection: 'column',
        gap: `${theme.spacing.md}px`,
      }}
    >
      {!sessionId && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flex: 1,
            color: theme.colors.fgMuted,
            fontSize: theme.fontSize.lg,
          }}
        >
          Select or create a session to begin
        </div>
      )}

      {messages.map((msg) => {
        const isUser = msg.role === 'user'
        const isSystem = msg.role === 'system'
        const stats = isUser || isSystem ? null : estimateCost(msg.content)

        return (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: isUser ? 'flex-end' : 'flex-start',
            }}
          >
            {/* Role label */}
            <div
              style={{
                fontSize: theme.fontSize.xs,
                color: theme.colors.fgMuted,
                marginBottom: 4,
                marginLeft: isUser ? 0 : theme.spacing.sm,
                marginRight: isUser ? theme.spacing.sm : 0,
              }}
            >
              {isUser ? 'You' : isSystem ? 'System' : 'Lyra'}
              {msg.isStreaming && (
                <span style={{ color: theme.colors.accent, marginLeft: 4 }}>writing...</span>
              )}
            </div>

            {/* Message bubble */}
            <div
              style={{
                maxWidth: '80%',
                padding: `${theme.spacing.sm}px ${theme.spacing.md}px`,
                borderRadius: theme.radius.lg,
                background: isUser
                  ? theme.colors.userBubble
                  : isSystem
                    ? theme.colors.bgSurface
                    : theme.colors.assistantBubble,
                border: isSystem ? `1px solid ${theme.colors.border}` : 'none',
                fontSize: theme.fontSize.md,
                lineHeight: 1.6,
              }}
            >
              {isUser ? (
                <span>{msg.content}</span>
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ className, children, ...props }) {
                      const isInline = !className
                      if (isInline) {
                        return (
                          <code
                            style={{
                              background: theme.colors.bgInput,
                              color: theme.colors.inlineCode,
                              padding: '1px 5px',
                              borderRadius: theme.radius.sm,
                              fontSize: theme.fontSize.sm,
                            }}
                            {...props}
                          >
                            {children}
                          </code>
                        )
                      }
                      return <CodeBlock className={className}>{children}</CodeBlock>
                    },
                    pre({ children }) {
                      return <>{children}</>
                    },
                    a({ href, children }) {
                      return (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: theme.colors.info }}
                        >
                          {children}
                        </a>
                      )
                    },
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>

            {/* Token/cost estimate */}
            {stats && !msg.isStreaming && (
              <div
                style={{
                  fontSize: theme.fontSize.xs,
                  color: theme.colors.fgMuted,
                  marginTop: 2,
                  marginLeft: theme.spacing.sm,
                }}
              >
                ~{stats.tokens} tokens | ${stats.cost.toFixed(4)}
              </div>
            )}
          </div>
        )
      })}

      <div ref={bottomRef} />
    </div>
  )
}

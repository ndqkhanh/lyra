import { useCallback, useEffect, useRef, useState } from 'react'

// Types for the SSE streaming API
export interface StreamChunk {
  content: string
  done: boolean
  type?: 'text' | 'tool-call' | 'tool-result' | 'thinking'
  metadata?: Record<string, unknown>
}

export interface Session {
  id: string
  title: string
  created: number
  updated: number
  messageCount: number
  status: 'idle' | 'streaming' | 'error'
  taskState: 'running' | 'completed' | 'failed' | 'cancelled'
  processAlive: boolean
}

export interface ProviderInfo {
  name: string
  models: string[]
  defaultModel: string
}

export interface UsageStats {
  tokensIn: number
  tokensOut: number
  cost: number
  duration: number
}

/** Callback invoked for each SSE chunk received during streaming. */
export type OnChunkCallback = (chunk: StreamChunk) => void

async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  const resp = await window.lyraAPI.fetch(path, options)
  if (!resp.ok) {
    throw new Error(resp.body || `HTTP ${resp.status}`)
  }
  return { ok: resp.ok, status: resp.status, json: async () => JSON.parse(resp.body) } as Response
}

// ─── Hook ─────────────────────────────────────────────────────

export function useLyraAPI() {
  const [connected, setConnected] = useState(false)
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [usage] = useState<UsageStats>({ tokensIn: 0, tokensOut: 0, cost: 0, duration: 0 })
  const abortRef = useRef<AbortController | null>(null)

  // Check connectivity on mount
  useEffect(() => {
    checkConnection()
  }, [])

  const checkConnection = useCallback(async () => {
    try {
      const resp = await apiFetch('/health')
      if (resp.ok) {
        setConnected(true)
        fetchProviders()
        return
      }
    } catch {
      // not connected
    }
    setConnected(false)
  }, [])

  const fetchProviders = useCallback(async () => {
    try {
      const resp = await apiFetch('/providers')
      const data = await resp.json() as { providers: ProviderInfo[] }
      setProviders(data.providers || [])
    } catch {
      // ignore
    }
  }, [])

  /** Send a chat message via SSE streaming.
   *
   * Uses the Electron IPC proxy (``window.lyraAPI.connectSSE``) rather than
   * direct ``fetch``, so the request goes through the main process where
   * TLS certs and proxy settings are properly handled.
   *
   * @param sessionId  Target session ID.
   * @param message    User message text.
   * @param onChunk    Called for every SSE event received.
   * @param model      Optional model override.
   * @param provider   Optional provider override.
   * @returns          Promise that resolves when the stream ends.
   */
  const sendMessage = useCallback(
    (
      sessionId: string,
      message: string,
      onChunk: OnChunkCallback,
      model?: string,
      provider?: string,
    ) => {
      // Abort any existing stream
      if (abortRef.current) {
        abortRef.current.abort()
      }

      return new Promise<void>((resolve, reject) => {
        const params = new URLSearchParams()
        if (model) params.set('model', model)
        if (provider) params.set('provider', provider)

        const ssePath = `/chat/${sessionId}/stream?${params.toString()}`

        const body = JSON.stringify({ message, model, provider })

        const unsubscribe = window.lyraAPI.connectSSE(ssePath, {
          onData: (_path, data) => {
            try {
              const chunk = JSON.parse(data) as StreamChunk
              onChunk(chunk)
              if (chunk.done) {
                resolve()
              }
            } catch {
              // ignore parse errors
            }
          },
          onError: (_path, error) => {
            reject(new Error(error))
          },
        }, body)

        // Store unsubscribe as cleanup
        abortRef.current = {
          abort: () => {
            unsubscribe()
            reject(new Error('Aborted'))
          },
          signal: new AbortController().signal,
        }
      })
    },
    [],
  )

  /** Stop the current stream. */
  const cancelStream = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
  }, [])

  return {
    connected,
    providers,
    usage,
    sendMessage,
    cancelStream,
    fetchProviders,
    checkConnection,
  }
}

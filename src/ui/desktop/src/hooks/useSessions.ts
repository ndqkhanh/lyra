import { useCallback, useEffect, useState } from 'react'
import type { Session } from './useLyraAPI'

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSessions = useCallback(async () => {
    try {
      const resp = await window.lyraAPI.fetch('/sessions')
      if (!resp.ok) {
        throw new Error(resp.body || `HTTP ${resp.status}`)
      }
      const data = JSON.parse(resp.body) as { sessions: Session[] }
      setSessions(data.sessions || [])
      if (!activeId && data.sessions.length > 0) {
        setActiveId(data.sessions[0]!.id)
      }
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }, [activeId])

  const switchSession = useCallback((id: string) => {
    setActiveId(id)
  }, [])

  const createSession = useCallback(async () => {
    try {
      const resp = await window.lyraAPI.fetch('/sessions', {
        method: 'POST',
        body: JSON.stringify({ title: `Session ${sessions.length + 1}` }),
      })
      if (!resp.ok) {
        throw new Error(resp.body || `HTTP ${resp.status}`)
      }
      const data = JSON.parse(resp.body) as { session: Session }
      setSessions((prev) => [...prev, data.session])
      setActiveId(data.session.id)
      return data.session
    } catch (err) {
      setError((err as Error).message)
      return null
    }
  }, [sessions.length])

  const deleteSession = useCallback(async (id: string) => {
    try {
      const resp = await window.lyraAPI.fetch(`/sessions/${id}`, { method: 'DELETE' })
      if (!resp.ok) {
        throw new Error(resp.body || `HTTP ${resp.status}`)
      }
      setSessions((prev) => prev.filter((s) => s.id !== id))
      if (activeId === id) {
        setActiveId(null)
      }
    } catch (err) {
      setError((err as Error).message)
    }
  }, [activeId])

  // Initial fetch
  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  // Poll for updates every 5s
  useEffect(() => {
    const interval = setInterval(fetchSessions, 5000)
    return () => clearInterval(interval)
  }, [fetchSessions])

  return {
    sessions,
    activeId,
    loading,
    error,
    switchSession,
    createSession,
    deleteSession,
    refresh: fetchSessions,
  }
}

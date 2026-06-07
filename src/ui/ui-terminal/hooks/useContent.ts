import { useState, useEffect } from 'react'

const SERVER_URL = 'http://localhost:3737'

interface Tip {
  title: string
  description: string
}

interface ChangelogEntry {
  version: string
  date: string
  highlights: string[]
}

const FALLBACK_TIPS: Tip[] = [
  { title: 'Run /init to create a project CLAUDE.md', description: 'Scaffold SOUL.md + .lyra/ in your repo' },
  { title: 'Use @ to mention files', description: 'Type @ then a filename for autocomplete' },
  { title: 'Press Tab to cycle modes', description: 'Switch between agent, plan, ask, and auto' },
  { title: 'Try /model for the picker', description: 'Interactive model selection with arrow keys' },
  { title: 'Use ! for shell commands', description: 'Prefix with ! to run bash directly' },
]

const FALLBACK_WHATS_NEW: ChangelogEntry[] = [
  { version: '5.0.0', date: '2026-05-24', highlights: ['135+ composable packages', 'Multi-agent orchestration', 'Hierarchical 8-level memory'] },
]

export function useTips(intervalMs: number = 30_000): { currentTip: Tip; allTips: Tip[] } {
  const [tips, setTips] = useState<Tip[]>(FALLBACK_TIPS)
  const [index, setIndex] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetch(`${SERVER_URL}/tips`)
      .then(r => r.json() as Promise<{ tips?: Tip[] }>)
      .then(data => {
        if (!cancelled && data.tips?.length) setTips(data.tips)
      })
      .catch(() => {}) // keep fallback
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (tips.length <= 1) return
    const timer = setInterval(() => {
      setIndex(prev => (prev + 1) % tips.length)
    }, intervalMs)
    return () => clearInterval(timer)
  }, [tips, intervalMs])

  return { currentTip: tips[index] ?? tips[0], allTips: tips }
}

export function useWhatsNew(): { entries: ChangelogEntry[]; loading: boolean } {
  const [entries, setEntries] = useState<ChangelogEntry[]>(FALLBACK_WHATS_NEW)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetch(`${SERVER_URL}/whats-new`)
      .then(r => r.json() as Promise<{ entries?: ChangelogEntry[] }>)
      .then(data => {
        if (!cancelled && data.entries?.length) setEntries(data.entries)
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  return { entries, loading }
}

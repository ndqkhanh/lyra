import React from 'react'
import { useInput } from 'ink'
import { DisplayMode, useUIStore } from '@lyra/ui-core'
import { MinimalMode } from './MinimalMode'
import { StandardMode } from './StandardMode'
import { DebugMode } from './DebugMode'
import { FocusMode } from '../components/FocusMode'

interface DisplayModeSwitcherProps {
  sessionId: string
}

/**
 * Switches between display modes based on session state
 * Ctrl+\ to cycle through modes
 */
export function DisplayModeSwitcher({ sessionId }: DisplayModeSwitcherProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))

  useInput((input, key) => {
    if (key.ctrl && input === '\\' && session) {
      // Cycle through modes
      const modes: DisplayMode[] = ['minimal', 'standard', 'debug', 'focus']
      const currentIndex = modes.indexOf(session.displayMode)
      const nextIndex = (currentIndex + 1) % modes.length
      const nextMode = modes[nextIndex]

      // Update session display mode
      useUIStore.setState(state => {
        const updatedSession = state.sessions.get(sessionId)
        if (updatedSession) {
          state.sessions.set(sessionId, {
            ...updatedSession,
            displayMode: nextMode
          })
        }
      })
    }
  })

  if (!session) return null

  switch (session.displayMode) {
    case 'minimal':
      return <MinimalMode sessionId={sessionId} />
    case 'debug':
      return <DebugMode sessionId={sessionId} />
    case 'focus':
      return <FocusMode sessionId={sessionId} enabled={true} />
    case 'standard':
    default:
      return <StandardMode sessionId={sessionId} />
  }
}

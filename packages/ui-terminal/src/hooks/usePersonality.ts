/**
 * Hermes-style personality hook — kawaii faces, thinking verbs,
 * and spinner configuration driven by the active skin.
 */

import { useState, useCallback } from 'react'
import { useUIStore, DEFAULT_WAITING_FACES, DEFAULT_THINKING_FACES, DEFAULT_THINKING_VERBS } from '@lyra/ui-core'

export function usePersonality() {
  const skin = useUIStore(state => state.getActiveSkin())

  const waitingFaces = skin.spinner.waitingFaces ?? DEFAULT_WAITING_FACES
  const thinkingFaces = skin.spinner.thinkingFaces ?? DEFAULT_THINKING_FACES
  const thinkingVerbs = skin.spinner.thinkingVerbs ?? DEFAULT_THINKING_VERBS
  const wings = skin.spinner.wings ?? []
  const toolPrefix = skin.toolPrefix

  const [faceIndex, setFaceIndex] = useState(0)
  const [verbIndex, setVerbIndex] = useState(0)

  const tick = useCallback(() => {
    setFaceIndex(n => (n + 1) % thinkingFaces.length)
    setVerbIndex(n => (n + 1) % thinkingVerbs.length)
  }, [thinkingFaces.length, thinkingVerbs.length])

  return {
    currentFace: thinkingFaces[faceIndex]!,
    currentVerb: thinkingVerbs[verbIndex]!,
    thinkingFaces,
    thinkingVerbs,
    waitingFaces,
    wings,
    toolPrefix,
    tick,
  }
}

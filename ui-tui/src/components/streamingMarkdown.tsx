import { Box } from '@lyra/ink'
import { memo, useRef } from 'react'

import type { Theme } from '../theme.js'

import { Md } from './markdown.js'

const fenceOpenAt = (s: string, end: number) => {
  let codeOpen = false
  let mathOpen = false
  let mathOpener: '$$' | '\\[' | null = null
  let i = 0

  while (i < end) {
    const nl = s.indexOf('\n', i)
    const lineEnd = nl < 0 || nl > end ? end : nl
    const line = s.slice(i, lineEnd).trim()

    if (/^(?:`{3,}|~{3,})/.test(line)) {
      codeOpen = !codeOpen
    } else if (!codeOpen) {
      if (!mathOpen && /^\$\$/.test(line)) {
        const isSingleLine = line.length >= 4 && /\$\$$/.test(line)

        if (!isSingleLine) {
          mathOpen = true
          mathOpener = '$$'
        }
      } else if (!mathOpen && /^\\\[/.test(line)) {
        const isSingleLine = /\\\]$/.test(line)

        if (!isSingleLine) {
          mathOpen = true
          mathOpener = '\\['
        }
      } else if (mathOpen && mathOpener === '$$' && /\$\$$/.test(line)) {
        mathOpen = false
        mathOpener = null
      } else if (mathOpen && mathOpener === '\\[' && /\\\]$/.test(line)) {
        mathOpen = false
        mathOpener = null
      }
    }

    if (nl < 0 || nl >= end) {
      break
    }

    i = nl + 1
  }

  return codeOpen || mathOpen
}

export const findStableBoundary = (text: string) => {
  let idx = text.length

  while (idx > 0) {
    const boundary = text.lastIndexOf('\n\n', idx - 1)

    if (boundary < 0) {
      return -1
    }

    const splitAt = boundary + 2

    if (!fenceOpenAt(text, splitAt)) {
      return splitAt
    }

    idx = boundary
  }

  return -1
}

export const StreamingMd = memo(function StreamingMd({ cols, compact, t, text }: StreamingMdProps) {
  const stablePrefixRef = useRef('')

  if (!text.startsWith(stablePrefixRef.current)) {
    stablePrefixRef.current = ''
  }

  const boundary = findStableBoundary(text)

  if (boundary > stablePrefixRef.current.length) {
    stablePrefixRef.current = text.slice(0, boundary)
  }

  const stablePrefix = stablePrefixRef.current
  const unstableSuffix = text.slice(stablePrefix.length)

  if (!stablePrefix) {
    return <Md cols={cols} compact={compact} t={t} text={unstableSuffix} />
  }

  if (!unstableSuffix) {
    return <Md cols={cols} compact={compact} t={t} text={stablePrefix} />
  }

  return (
    <Box flexDirection="column">
      <Md cols={cols} compact={compact} t={t} text={stablePrefix} />
      <Md cols={cols} compact={compact} t={t} text={unstableSuffix} />
    </Box>
  )
})

interface StreamingMdProps {
  cols?: number
  compact?: boolean
  t: Theme
  text: string
}

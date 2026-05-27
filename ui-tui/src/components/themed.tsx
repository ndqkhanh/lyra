import type { Color } from '@lyra/ink'
import { Text } from '@lyra/ink'
import { useStore } from '@nanostores/react'
import type { ReactNode } from 'react'

import { $uiState } from '../app/uiStore.js'
import type { ThemeColors } from '../theme.js'

export function Fg({ bold, c, children, dim, italic, literal, strikethrough, underline, wrap }: FgProps) {
  const { theme } = useStore($uiState)
  const color = literal ?? (c && theme.color[c])

  if (dim) {
    return (
      <Text color={color} dim italic={italic} strikethrough={strikethrough} underline={underline} wrap={wrap}>
        {children}
      </Text>
    )
  }
  if (bold) {
    return (
      <Text color={color} bold italic={italic} strikethrough={strikethrough} underline={underline} wrap={wrap}>
        {children}
      </Text>
    )
  }
  return (
    <Text color={color} italic={italic} strikethrough={strikethrough} underline={underline} wrap={wrap}>
      {children}
    </Text>
  )
}

export type ThemeColor = keyof ThemeColors

export interface FgProps {
  bold?: boolean
  c?: ThemeColor
  children?: ReactNode
  dim?: boolean
  italic?: boolean
  literal?: Color
  strikethrough?: boolean
  underline?: boolean
  wrap?: 'end' | 'middle' | 'truncate' | 'truncate-end' | 'truncate-middle' | 'truncate-start' | 'wrap' | 'wrap-trim'
}

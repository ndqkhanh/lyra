import React from 'react'
import { Box, Text } from 'ink'
import type { SystemNoticeItem as SystemNoticeItemType } from '@lyra/ui-core'
import { useThemeColors, symbols } from '@lyra/ui-core'

interface Props {
  item: SystemNoticeItemType
}

export function SystemNotice({ item }: Props) {
  const colors = useThemeColors()
  const noticeStyle: Record<string, { color: string; icon: string }> = {
    info:    { color: colors.info,    icon: symbols.info },
    warning: { color: colors.warning, icon: symbols.warning },
    success: { color: colors.success, icon: symbols.success },
  }
  const style = noticeStyle[item.noticeType] || noticeStyle.info
  return (
    <Box marginBottom={1}>
      <Box marginRight={1}>
        <Text color={style.color}>{style.icon}</Text>
      </Box>
      <Text color={style.color}>{item.content}</Text>
    </Box>
  )
}

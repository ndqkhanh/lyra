import React from 'react'
import { Text } from 'ink'
import type { RenderItem } from '@lyra/ui-core'
import { useThemeColors } from '@lyra/ui-core'
import { UserTextMessage } from './items/UserTextMessage'
import { UserImageMessage } from './items/UserImageMessage'
import { AssistantTextMessage } from './items/AssistantTextMessage'
import { ThinkingBlock } from './items/ThinkingBlock'
import { ToolExecution } from './items/ToolExecution'
import { ErrorItem } from './items/ErrorItem'
import { SystemNotice } from './items/SystemNotice'
import { ItemErrorBoundary } from './ErrorBoundary'

interface RenderItemViewProps {
  item: RenderItem
}

export const RenderItemView = React.memo(function RenderItemView({ item }: RenderItemViewProps) {
  const colors = useThemeColors()
  return (
    <ItemErrorBoundary>
      {(() => {
        switch (item.kind) {
          case 'user-text':
            return <UserTextMessage item={item} />
          case 'user-image':
            return <UserImageMessage item={item} />
          case 'assistant-text':
            return <AssistantTextMessage item={item} />
          case 'thinking':
            return <ThinkingBlock item={item} />
          case 'tool-execution':
            return <ToolExecution item={item} />
          case 'error':
            return <ErrorItem item={item} />
          case 'system-notice':
            return <SystemNotice item={item} />
          default:
            return <Text color={colors.errorHigh}>Unknown render item: {(item as RenderItem).kind}</Text>
        }
      })()}
    </ItemErrorBoundary>
  )
})

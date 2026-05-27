import React from 'react'
import type { RenderItem } from '@lyra/ui-core'
import { UserTextMessage } from './items/UserTextMessage'
import { UserImageMessage } from './items/UserImageMessage'
import { AssistantTextMessage } from './items/AssistantTextMessage'
import { ThinkingBlock } from './items/ThinkingBlock'
import { ToolExecution } from './items/ToolExecution'
import { ErrorItem } from './items/ErrorItem'
import { SystemNotice } from './items/SystemNotice'

interface RenderItemViewProps {
  item: RenderItem
}

export const RenderItemView = React.memo(function RenderItemView({ item }: RenderItemViewProps) {
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
  }
})

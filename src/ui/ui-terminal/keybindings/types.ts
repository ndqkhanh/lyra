export type KeybindingContext =
  | 'global'
  | 'chat'
  | 'autocomplete'
  | 'settings'
  | 'confirmation'
  | 'transcript'
  | 'historySearch'
  | 'task'
  | 'modelPicker'
  | 'releaseNotesPicker'
  | 'commandPalette'
  | 'sessionDashboard'
  | 'rewindMenu'
  | 'sidebar'
  | 'goalPanel'
  | 'effortPicker'
  | 'themePicker'
  | 'pluginManager'
  | 'hooksManager'
  | 'vimNormal'
  | 'vimInsert'

export interface KeyCombo {
  key?: string
  ctrl?: boolean
  alt?: boolean
  shift?: boolean
  meta?: boolean
}

export interface Keybinding {
  id: string
  combo: KeyCombo
  action: string
  description: string
  contexts: KeybindingContext[]
}

export interface KeybindingConfig {
  version: number
  bindings: Keybinding[]
}

export type KeybindingAction =
  | 'submit'
  | 'newline'
  | 'clearInput'
  | 'navigateHistoryUp'
  | 'navigateHistoryDown'
  | 'autocompleteNext'
  | 'autocompletePrev'
  | 'acceptSuggestion'
  | 'dismissSuggestions'
  | 'openCommandPalette'
  | 'openTranscript'
  | 'openHistorySearch'
  | 'toggleVim'
  | 'toggleFocus'
  | 'toggleFullscreen'
  | 'openSettings'
  | 'confirm'
  | 'cancel'
  | 'scrollUp'
  | 'scrollDown'
  | 'scrollPageUp'
  | 'scrollPageDown'
  | 'scrollTop'
  | 'scrollBottom'
  | 'toggleAutoFollow'
  | 'toggleTaskPanel'
  | 'copyLastResponse'
  | 'openSideQuestion'
  | 'cyclePermissionMode'
  | (string & {})

import { DEFAULT_KEYBINDINGS } from './defaults'
import type { Keybinding, KeybindingAction, KeybindingContext, KeyCombo } from './types'

interface MatchResult {
  binding: Keybinding
  action: KeybindingAction
}

export class KeybindingManager {
  private bindings: Keybinding[] = []
  private overrides: Map<string, KeyCombo> = new Map()
  private configPath: string
  private watcherInterval: ReturnType<typeof setInterval> | null = null

  constructor(configPath?: string) {
    this.configPath = configPath ?? ''
    this.bindings = [...DEFAULT_KEYBINDINGS]
  }

  loadDefaults(): void {
    this.bindings = [...DEFAULT_KEYBINDINGS]
    this.overrides.clear()
  }

  loadOverrides(overrides: Record<string, KeyCombo>): void {
    for (const [actionId, combo] of Object.entries(overrides)) {
      this.overrides.set(actionId, combo)
    }
  }

  match(input: string, key: { upArrow?: boolean; downArrow?: boolean; leftArrow?: boolean; rightArrow?: boolean; return?: boolean; escape?: boolean; tab?: boolean; backspace?: boolean; delete?: boolean; pageup?: boolean; pagedown?: boolean; home?: boolean; end?: boolean; ctrl?: boolean; shift?: boolean; alt?: boolean; meta?: boolean }, activeContexts: KeybindingContext[]): MatchResult | null {
    const normalizedKey = this.normalizeKeyName(key)

    for (const binding of this.bindings) {
      if (!binding.contexts.some(c => activeContexts.includes(c))) continue

      const effectiveCombo = this.overrides.get(binding.id) ?? binding.combo

      if (this.comboMatches(effectiveCombo, input, normalizedKey)) {
        return { binding, action: binding.action }
      }
    }

    return null
  }

  getBindingsForContext(context: KeybindingContext): Keybinding[] {
    return this.bindings.filter(b => b.contexts.includes(context))
  }

  getAllBindings(): Keybinding[] {
    return [...this.bindings]
  }

  startConfigWatcher(pollIntervalMs: number = 5000): void {
    if (this.watcherInterval || !this.configPath) return
    this.watcherInterval = setInterval(() => {
      this.reloadConfig()
    }, pollIntervalMs)
  }

  stopConfigWatcher(): void {
    if (this.watcherInterval) {
      clearInterval(this.watcherInterval)
      this.watcherInterval = null
    }
  }

  dispose(): void {
    this.stopConfigWatcher()
    this.bindings = []
    this.overrides.clear()
  }

  private reloadConfig(): void {
    try {
      const fs = require('fs')
      if (!fs.existsSync(this.configPath)) return
      const raw = fs.readFileSync(this.configPath, 'utf-8')
      const config = JSON.parse(raw)
      if (config?.bindings && Array.isArray(config.bindings)) {
        for (const override of config.bindings) {
          if (override.id && override.combo) {
            this.overrides.set(override.id, override.combo)
          }
        }
      }
    } catch {
      // Config file missing or invalid — keep current bindings
    }
  }

  private normalizeKeyName(key: MatchResult extends infer R ? (R extends MatchResult ? Parameters<KeybindingManager['match']>[1] : never) : never): string {
    if (key.upArrow) return 'upArrow'
    if (key.downArrow) return 'downArrow'
    if (key.leftArrow) return 'leftArrow'
    if (key.rightArrow) return 'rightArrow'
    if (key.return) return 'return'
    if (key.escape) return 'escape'
    if (key.tab) return 'tab'
    if (key.backspace) return 'backspace'
    if (key.delete) return 'delete'
    if (key.pageup) return 'pageup'
    if (key.pagedown) return 'pagedown'
    if (key.home) return 'home'
    if (key.end) return 'end'
    return ''
  }

  private comboMatches(combo: KeyCombo, input: string, normalizedKey: string): boolean {
    if (combo.ctrl && !input) return false

    const keyMatch = combo.key
      ? (combo.key === normalizedKey || combo.key.toLowerCase() === input.toLowerCase())
      : true

    if (!keyMatch) return false

    return true
  }
}

export const keybindingManager = new KeybindingManager()

export function createKeybindingManager(configPath?: string): KeybindingManager {
  return new KeybindingManager(configPath)
}

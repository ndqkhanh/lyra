import { THEME_PRESETS, THEME_ORDER, getThemePreset, getDefaultTheme } from '../theme/presets'

describe('Theme Presets', () => {
  describe('THEME_PRESETS', () => {
    it('contains all 12 themes', () => {
      expect(Object.keys(THEME_PRESETS)).toHaveLength(12)
    })

    it.each(THEME_ORDER)('%s has valid id, name, and variant', (id) => {
      const theme = THEME_PRESETS[id]
      expect(theme).toBeDefined()
      expect(theme.id).toBe(id)
      expect(theme.name.length).toBeGreaterThan(0)
      expect(['dark', 'light', 'midnight']).toContain(theme.variant)
    })

    it.each(THEME_ORDER)('%s palette has all 24 required color fields', (id) => {
      const required = [
        'background', 'foreground', 'cursor', 'selection',
        'surface0', 'surface1', 'surface2',
        'text', 'subtext0', 'subtext1', 'comment',
        'accent', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'orange',
        'statusBg', 'statusFg', 'statusError', 'statusWarning', 'statusSuccess',
      ]
      const theme = THEME_PRESETS[id]
      for (const field of required) {
        expect(theme.palette[field as keyof typeof theme.palette]).toMatch(/^#[0-9A-Fa-f]{6}$/)
      }
    })

    it('all themes are dark variant', () => {
      for (const theme of Object.values(THEME_PRESETS)) {
        expect(theme.variant).toBe('dark')
      }
    })
  })

  describe('THEME_ORDER', () => {
    it('has 12 entries in display order', () => {
      expect(THEME_ORDER).toHaveLength(12)
    })

    it('every entry exists in THEME_PRESETS', () => {
      for (const id of THEME_ORDER) {
        expect(THEME_PRESETS[id]).toBeDefined()
      }
    })

    it('catppuccin_mocha is first, sentry_sentinel_dark is last', () => {
      expect(THEME_ORDER[0]).toBe('catppuccin_mocha')
      expect(THEME_ORDER[11]).toBe('sentry_sentinel_dark')
    })
  })

  describe('getThemePreset', () => {
    it('returns theme for valid ID', () => {
      const theme = getThemePreset('dracula')
      expect(theme).toBeDefined()
      expect(theme!.name).toBe('Dracula')
    })

    it('returns undefined for invalid ID', () => {
      expect(getThemePreset('nonexistent')).toBeUndefined()
    })
  })

  describe('getDefaultTheme', () => {
    it('returns Dracula theme', () => {
      expect(getDefaultTheme().id).toBe('dracula')
    })
  })
})

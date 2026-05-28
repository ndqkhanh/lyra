import {
  detectTerminalThemeSync,
  getRecommendedThemeId,
  type ThemeVariant,
  type ThemeDetectionResult,
} from '../theme/autoDetect'

describe('detectTerminalThemeSync', () => {
  afterEach(() => {
    delete process.env.COLORFGBG
    delete process.env.TERM
    delete process.env.TERM_PROGRAM
  })

  it('returns a valid ThemeDetectionResult', () => {
    const result = detectTerminalThemeSync()
    expect(['dark', 'light']).toContain(result.variant)
    expect(['high', 'medium', 'low']).toContain(result.confidence)
    expect(typeof result.method).toBe('string')
    expect(result.method.length).toBeGreaterThan(0)
  })

  it('detects dark from COLORFGBG with dark background (0-6)', () => {
    process.env.COLORFGBG = '15;0'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
    expect(result.confidence).toBe('high')
    expect(result.method).toBe('COLORFGBG')
  })

  it('detects light from COLORFGBG with light background (7-15)', () => {
    process.env.COLORFGBG = '0;15'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('light')
    expect(result.confidence).toBe('high')
    expect(result.method).toBe('COLORFGBG')
  })

  it('detects dark from COLORFGBG with bg=2', () => {
    process.env.COLORFGBG = '7;2'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
    expect(result.confidence).toBe('high')
  })

  it('falls through to terminal heuristics when no COLORFGBG', () => {
    delete process.env.COLORFGBG
    process.env.TERM_PROGRAM = 'vscode'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
    expect(result.confidence).toBe('medium')
    expect(result.method).toBe('Terminal Heuristic')
  })

  it('detects iTerm2 as dark', () => {
    delete process.env.COLORFGBG
    process.env.TERM_PROGRAM = 'iTerm.app'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
    expect(result.method).toBe('Terminal Heuristic')
  })

  it('detects Apple_Terminal as light', () => {
    delete process.env.COLORFGBG
    process.env.TERM_PROGRAM = 'Apple_Terminal'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('light')
    expect(result.method).toBe('Terminal Heuristic')
  })

  it('detects Alacritty as dark via TERM', () => {
    delete process.env.COLORFGBG
    delete process.env.TERM_PROGRAM
    process.env.TERM = 'alacritty'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
    expect(result.method).toBe('Terminal Heuristic')
  })

  it('detects WezTerm as dark', () => {
    delete process.env.COLORFGBG
    process.env.TERM_PROGRAM = 'WezTerm'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
  })

  it('detects Kitty as dark via TERM', () => {
    delete process.env.COLORFGBG
    delete process.env.TERM_PROGRAM
    process.env.TERM = 'kitty-0.35'
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
    expect(result.method).toBe('Terminal Heuristic')
  })

  it('falls back to dark when no env vars are set', () => {
    delete process.env.COLORFGBG
    delete process.env.TERM
    delete process.env.TERM_PROGRAM
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
    expect(result.confidence).toBe('low')
    expect(result.method).toBe('Fallback')
  })

  it('handles invalid COLORFGBG format gracefully', () => {
    process.env.COLORFGBG = 'invalid'
    delete process.env.TERM_PROGRAM
    delete process.env.TERM
    const result = detectTerminalThemeSync()
    // Falls through to fallback since heuristics don't match
    expect(result.variant).toBe('dark')
  })

  it('handles COLORFGBG with only fg', () => {
    process.env.COLORFGBG = '7'
    delete process.env.TERM_PROGRAM
    delete process.env.TERM
    const result = detectTerminalThemeSync()
    expect(result.variant).toBe('dark')
  })
})

describe('getRecommendedThemeId', () => {
  it('returns dracula for dark variant', () => {
    expect(getRecommendedThemeId('dark')).toBe('dracula')
  })

  it('returns catppuccin_latte for light variant', () => {
    expect(getRecommendedThemeId('light')).toBe('catppuccin_latte')
  })

  it('returns a string for any variant', () => {
    const variants: ThemeVariant[] = ['dark', 'light']
    for (const v of variants) {
      expect(typeof getRecommendedThemeId(v)).toBe('string')
      expect(getRecommendedThemeId(v).length).toBeGreaterThan(0)
    }
  })
})

import {
  buildSkinFromPreset,
  DEFAULT_WAITING_FACES,
  DEFAULT_THINKING_FACES,
  DEFAULT_THINKING_VERBS,
} from '../theme/skin'
import { getDefaultTheme, getThemePreset } from '../theme/presets'

describe('DEFAULT_WAITING_FACES', () => {
  it('has 10 faces', () => {
    expect(DEFAULT_WAITING_FACES).toHaveLength(10)
  })

  it('all faces are non-empty strings', () => {
    for (const face of DEFAULT_WAITING_FACES) {
      expect(typeof face).toBe('string')
      expect(face.length).toBeGreaterThan(0)
    }
  })
})

describe('DEFAULT_THINKING_FACES', () => {
  it('has 10 faces', () => {
    expect(DEFAULT_THINKING_FACES).toHaveLength(10)
  })

  it('all faces are non-empty strings', () => {
    for (const face of DEFAULT_THINKING_FACES) {
      expect(typeof face).toBe('string')
      expect(face.length).toBeGreaterThan(0)
    }
  })
})

describe('DEFAULT_THINKING_VERBS', () => {
  it('has 15 verbs', () => {
    expect(DEFAULT_THINKING_VERBS).toHaveLength(15)
  })

  it('all verbs are non-empty strings', () => {
    for (const verb of DEFAULT_THINKING_VERBS) {
      expect(typeof verb).toBe('string')
      expect(verb.length).toBeGreaterThan(0)
    }
  })
})

describe('buildSkinFromPreset', () => {
  it('builds a skin from default theme', () => {
    const preset = getDefaultTheme()
    const skin = buildSkinFromPreset(preset)

    expect(skin.id).toBe(preset.id)
    expect(skin.name).toBe(preset.name)
    expect(skin.variant).toBe(preset.variant)
    expect(skin.description).toContain(preset.name)
  })

  it('uses default branding', () => {
    const skin = buildSkinFromPreset(getDefaultTheme())
    expect(skin.branding.agentName).toBe('Lyra')
    expect(skin.branding.promptSymbol).toBe('❯')
    expect(skin.branding.responseLabel).toBe('Lyra')
  })

  it('accepts branding overrides', () => {
    const skin = buildSkinFromPreset(getDefaultTheme(), {
      agentName: 'CustomBot',
      promptSymbol: '>',
    })
    expect(skin.branding.agentName).toBe('CustomBot')
    expect(skin.branding.promptSymbol).toBe('>')
    expect(skin.branding.responseLabel).toBe('Lyra') // not overridden
  })

  it('has complete color slots', () => {
    const skin = buildSkinFromPreset(getDefaultTheme())
    const colorKeys = Object.keys(skin.colors)
    expect(colorKeys).toContain('bannerBorder')
    expect(colorKeys).toContain('bannerTitle')
    expect(colorKeys).toContain('uiAccent')
    expect(colorKeys).toContain('uiOk')
    expect(colorKeys).toContain('uiError')
    expect(colorKeys).toContain('uiWarn')
    expect(colorKeys).toContain('prompt')
    expect(colorKeys).toContain('statusBarBg')
    expect(colorKeys).toContain('statusBarText')
    expect(colorKeys).toContain('statusBarGood')
    expect(colorKeys).toContain('statusBarBad')
    expect(colorKeys).toContain('completionMenuBg')
  })

  it('all color values are strings starting with #', () => {
    const skin = buildSkinFromPreset(getDefaultTheme())
    for (const [key, value] of Object.entries(skin.colors)) {
      expect(value).toMatch(/^#[0-9A-Fa-f]{6}$/)
    }
  })

  it('sets up spinner config with defaults', () => {
    const skin = buildSkinFromPreset(getDefaultTheme())
    expect(skin.spinner.waitingFaces).toEqual(DEFAULT_WAITING_FACES)
    expect(skin.spinner.thinkingFaces).toEqual(DEFAULT_THINKING_FACES)
    expect(skin.spinner.thinkingVerbs).toEqual(DEFAULT_THINKING_VERBS)
  })

  it('sets toolPrefix', () => {
    const skin = buildSkinFromPreset(getDefaultTheme())
    expect(skin.toolPrefix).toBe('┊')
  })

  it('has empty toolEmojis by default', () => {
    const skin = buildSkinFromPreset(getDefaultTheme())
    expect(skin.toolEmojis).toEqual({})
  })

  it('works with any theme preset', () => {
    const preset = getThemePreset('dracula')
    expect(preset).toBeDefined()
    const skin = buildSkinFromPreset(preset!)
    expect(skin.id).toBe('dracula')
    expect(skin.name).toBe('Dracula')
  })
})

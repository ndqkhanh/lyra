import { deriveColors, colors } from '../theme/colors'
import { getDefaultTheme } from '../theme/presets'

describe('deriveColors', () => {
  const palette = getDefaultTheme().palette

  it('returns a complete ColorSet', () => {
    const result = deriveColors(palette)
    expect(result).toBeDefined()
    expect(typeof result.background).toBe('string')
    expect(typeof result.gold).toBe('string')
  })

  it('maps palette accent to gold', () => {
    const result = deriveColors(palette)
    expect(result.gold).toBe(palette.accent)
  })

  it('maps palette yellow to amber', () => {
    const result = deriveColors(palette)
    expect(result.amber).toBe(palette.yellow)
  })

  it('maps palette orange to bronze', () => {
    const result = deriveColors(palette)
    expect(result.bronze).toBe(palette.orange)
  })

  it('maps background color', () => {
    const result = deriveColors(palette)
    expect(result.background).toBe(palette.background)
  })

  it('maps all agent state colors', () => {
    const result = deriveColors(palette)
    expect(result.agentThinking).toBe(palette.yellow)
    expect(result.agentComposing).toBe(palette.purple)
    expect(result.agentToolRunning).toBe(palette.cyan)
    expect(result.agentStreaming).toBe(palette.green)
    expect(result.agentIdle).toBe(palette.comment)
    expect(result.agentError).toBe(palette.red)
  })

  it('maps all status colors', () => {
    const result = deriveColors(palette)
    expect(result.statusPending).toBe(palette.orange)
    expect(result.statusRunning).toBe(palette.cyan)
    expect(result.statusSuccess).toBe(palette.green)
    expect(result.statusCancelled).toBe(palette.comment)
    expect(result.statusSkipped).toBe(palette.purple)
  })

  it('maps all code colors', () => {
    const result = deriveColors(palette)
    expect(result.codeKeyword).toBe(palette.purple)
    expect(result.codeString).toBe(palette.green)
    expect(result.codeFunction).toBe(palette.blue)
    expect(result.codeComment).toBe(palette.comment)
  })

  it('maps all diff colors', () => {
    const result = deriveColors(palette)
    expect(result.diffAdded).toBe(palette.green)
    expect(result.diffRemoved).toBe(palette.red)
    expect(result.diffContext).toBe(palette.comment)
  })

  it('maps all markdown colors', () => {
    const result = deriveColors(palette)
    expect(result.markdownHeading).toBe(palette.purple)
    expect(result.markdownCode).toBe(palette.yellow)
    expect(result.markdownLink).toBe(palette.cyan)
    expect(result.markdownQuote).toBe(palette.comment)
  })

  it('maps error severity colors', () => {
    const result = deriveColors(palette)
    expect(result.errorCritical).toBe(palette.red)
    expect(result.errorHigh).toBe(palette.red)
    expect(result.errorMedium).toBe(palette.orange)
    expect(result.errorLow).toBe(palette.yellow)
    expect(result.errorInfo).toBe(palette.cyan)
  })

  it('all color values are non-empty strings', () => {
    const result = deriveColors(palette)
    for (const [key, value] of Object.entries(result)) {
      expect(typeof value).toBe('string')
      expect((value as string).length).toBeGreaterThan(0)
    }
  })
})

describe('static colors', () => {
  it('is derived from default theme', () => {
    expect(colors.background).toBe(getDefaultTheme().palette.background)
  })

  it('has the same shape as deriveColors output', () => {
    const derived = deriveColors(getDefaultTheme().palette)
    expect(Object.keys(colors).sort()).toEqual(Object.keys(derived).sort())
  })
})

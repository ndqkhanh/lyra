import { symbols, type SymbolName } from '../theme/symbols'

describe('symbols', () => {
  it('has message marker symbols', () => {
    expect(symbols.user).toBe('❯')
    expect(symbols.assistant).toBe('⏺')
    expect(symbols.thinking).toBe('✳')
  })

  it('has navigation symbols', () => {
    expect(symbols.upArrow).toBe('↑')
    expect(symbols.downArrow).toBe('↓')
    expect(symbols.leftArrow).toBe('←')
    expect(symbols.rightArrow).toBe('→')
  })

  it('has status symbols', () => {
    expect(symbols.success).toBe('✅')
    expect(symbols.error).toBe('❌')
    expect(symbols.warning).toBe('⚠')
    expect(symbols.info).toBe('ℹ')
    expect(symbols.pending).toBe('⏳')
  })

  it('spinner has 10 frames', () => {
    expect(symbols.spinner).toHaveLength(10)
    for (const frame of symbols.spinner) {
      expect(typeof frame).toBe('string')
    }
  })

  it('thinkingFrames has 4 frames', () => {
    expect(symbols.thinkingFrames).toHaveLength(4)
  })

  it('progressFrames has 5 frames', () => {
    expect(symbols.progressFrames).toHaveLength(5)
  })

  it('logo has 3 lines', () => {
    expect(symbols.logo).toHaveLength(3)
    for (const line of symbols.logo) {
      expect(typeof line).toBe('string')
    }
  })

  it('logoBlock has 3 lines', () => {
    expect(symbols.logoBlock).toHaveLength(3)
  })

  it('has border drawing symbols', () => {
    expect(symbols.horizontalLine).toBe('─')
    expect(symbols.verticalLine).toBe('│')
    expect(symbols.topLeft).toBe('┌')
    expect(symbols.topRight).toBe('┐')
    expect(symbols.bottomLeft).toBe('└')
    expect(symbols.bottomRight).toBe('┘')
    expect(symbols.cross).toBe('┼')
  })

  it('has tree/indent symbols', () => {
    expect(symbols.branch).toBe('⎿')
    expect(symbols.checkbox).toBe('◻')
    expect(symbols.checkboxChecked).toBe('◼')
  })

  it('has decorative elements', () => {
    expect(symbols.constellationTop).toContain('✦')
    expect(symbols.constellationBottom).toContain('✦')
    expect(symbols.synthwaveDivider).toContain('★')
  })

  it('all top-level values that are strings are non-empty', () => {
    for (const [key, value] of Object.entries(symbols)) {
      if (typeof value === 'string') {
        expect(value.length).toBeGreaterThan(0)
      }
    }
  })
})

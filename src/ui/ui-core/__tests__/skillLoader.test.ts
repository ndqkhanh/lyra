import {
  loadFromObject,
  createSkill,
  SkillBuilder,
  skill,
  type LoaderOptions,
} from '../skills/loader'
import type { Skill, SkillMetadata, SkillContext } from '../skills/registry'

function makeMetadata(): SkillMetadata {
  return {
    id: 'test-skill',
    name: 'Test Skill',
    description: 'A test skill',
    version: '1.0.0',
    tags: ['test'],
    dependencies: {},
  }
}

async function noopExecute(_ctx: SkillContext): Promise<{ output: string }> {
  return { output: 'done' }
}

describe('loadFromObject', () => {
  it('loads a partial skill with defaults', () => {
    const skill = loadFromObject({
      metadata: { id: 's1', name: 'Skill 1', description: '', version: '1.0.0', tags: [], dependencies: {} },
    })
    expect(skill.metadata.id).toBe('s1')
    expect(skill.metadata.name).toBe('Skill 1')
    expect(skill.config.enabled).toBe(true)
  })

  it('uses unknown defaults when metadata missing', () => {
    const skill = loadFromObject({})
    expect(skill.metadata.id).toBe('unknown')
    expect(skill.metadata.name).toBe('Unknown Skill')
  })

  it('throws when execute is called without implementation', () => {
    const skill = loadFromObject({ metadata: { id: 's1', name: 'S', description: '', version: '1.0.0', tags: [], dependencies: {} } })
    expect(() => skill.execute({} as SkillContext)).toThrow('not implemented')
  })

  it('applies default config options', () => {
    const skill = loadFromObject(
      { metadata: { id: 's1', name: 'S', description: '', version: '1.0.0', tags: [], dependencies: {} } },
      { defaultConfig: { enabled: false, priority: 5 } },
    )
    expect(skill.config.enabled).toBe(false)
    expect(skill.config.priority).toBe(5)
  })

  it('preserves provided execute function', async () => {
    const skill = loadFromObject({
      metadata: { id: 's1', name: 'S', description: '', version: '1.0.0', tags: [], dependencies: {} },
      execute: noopExecute,
    })
    const result = await skill.execute({} as SkillContext)
    expect(result).toEqual({ output: 'done' })
  })

  it('preserves provided validate function', () => {
    const validate = vi.fn().mockReturnValue(true)
    const skill = loadFromObject({
      metadata: { id: 's1', name: 'S', description: '', version: '1.0.0', tags: [], dependencies: {} },
      validate,
    })
    expect(skill.validate).toBe(validate)
  })
})

describe('createSkill', () => {
  it('creates a skill with required fields', () => {
    const meta = makeMetadata()
    const s = createSkill(meta, noopExecute)

    expect(s.metadata.id).toBe('test-skill')
    expect(s.execute).toBeDefined()
    expect(s.config.enabled).toBe(true)
    expect(s.config.priority).toBe(0)
    expect(s.config.autoReload).toBe(false)
  })

  it('accepts optional config', () => {
    const s = createSkill(makeMetadata(), noopExecute, {
      config: { enabled: false, autoReload: true },
    })
    expect(s.config.enabled).toBe(false)
    expect(s.config.autoReload).toBe(true)
  })

  it('accepts hooks', () => {
    const onLoad = vi.fn()
    const s = createSkill(makeMetadata(), noopExecute, { hooks: { onLoad } })
    s.hooks.onLoad?.()
    expect(onLoad).toHaveBeenCalled()
  })

  it('accepts validate function', () => {
    const validate = vi.fn().mockReturnValue(true)
    const s = createSkill(makeMetadata(), noopExecute, { validate })
    expect(s.validate).toBe(validate)
  })
})

describe('SkillBuilder', () => {
  it('builds a valid skill', () => {
    const s = skill()
      .id('my-skill')
      .name('My Skill')
      .execute(noopExecute)
      .build()

    expect(s.metadata.id).toBe('my-skill')
    expect(s.metadata.name).toBe('My Skill')
    expect(s.execute).toBeDefined()
  })

  it('throws if id is missing', () => {
    expect(() => skill().name('N').execute(noopExecute).build()).toThrow('Skill ID is required')
  })

  it('throws if name is missing', () => {
    expect(() => skill().id('x').execute(noopExecute).build()).toThrow('Skill name is required')
  })

  it('throws if execute is missing', () => {
    expect(() => skill().id('x').name('N').build()).toThrow('Skill execute function is required')
  })

  it('sets metadata fields', () => {
    const s = skill()
      .id('s1')
      .name('Skill')
      .description('Desc')
      .version('2.0')
      .author('Author')
      .tags('a', 'b')
      .dependency('d1', '^1')
      .minLyraVersion('1.0')
      .maxLyraVersion('3.0')
      .icon('🔧')
      .homepage('https://example.com')
      .repository('https://github.com/example/skill')
      .license('MIT')
      .execute(noopExecute)
      .build()

    expect(s.metadata.id).toBe('s1')
    expect(s.metadata.description).toBe('Desc')
    expect(s.metadata.version).toBe('2.0')
    expect(s.metadata.author).toBe('Author')
    expect(s.metadata.tags).toEqual(['a', 'b'])
    expect(s.metadata.dependencies).toEqual({ d1: '^1' })
    expect(s.metadata.minLyraVersion).toBe('1.0')
    expect(s.metadata.maxLyraVersion).toBe('3.0')
    expect(s.metadata.icon).toBe('🔧')
    expect(s.metadata.homepage).toBe('https://example.com')
    expect(s.metadata.repository).toBe('https://github.com/example/skill')
    expect(s.metadata.license).toBe('MIT')
  })

  it('sets config fields', () => {
    const s = skill()
      .id('s1')
      .name('N')
      .execute(noopExecute)
      .enabled(false)
      .setting('key', 'val')
      .priority(5)
      .autoReload(true)
      .build()

    expect(s.config.enabled).toBe(false)
    expect(s.config.settings).toEqual({ key: 'val' })
    expect(s.config.priority).toBe(5)
    expect(s.config.autoReload).toBe(true)
  })

  it('sets hooks', () => {
    const onLoad = vi.fn()
    const onEnable = vi.fn()
    const s = skill()
      .id('s1')
      .name('N')
      .execute(noopExecute)
      .onLoad(onLoad)
      .onEnable(onEnable)
      .build()

    s.hooks.onLoad?.()
    s.hooks.onEnable?.()
    expect(onLoad).toHaveBeenCalled()
    expect(onEnable).toHaveBeenCalled()
  })

  it('sets validate', () => {
    const validate = vi.fn().mockReturnValue(true)
    const s = skill().id('s1').name('N').execute(noopExecute).validate(validate).build()
    expect(s.validate).toBe(validate)
  })
})

describe('skill factory', () => {
  it('returns a new SkillBuilder', () => {
    const builder = skill()
    expect(builder).toBeInstanceOf(SkillBuilder)
  })
})

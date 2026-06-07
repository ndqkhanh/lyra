import {
  PluginBuilder,
  plugin,
  createPlugin,
  DEFAULT_RESOURCE_LIMITS,
  DEFAULT_PERMISSIONS,
} from '../plugins/builder'
import type { PluginMetadata, PluginContext } from '../plugins/manager'

function makeMetadata(): PluginMetadata {
  return {
    id: 'test-plugin',
    name: 'Test Plugin',
    description: 'A test plugin',
    version: '1.0.0',
    author: 'Test Author',
    category: 'tools',
    tags: ['test'],
    dependencies: {},
    license: 'MIT',
  }
}

function noop(_ctx: PluginContext): void {}

describe('DEFAULT_RESOURCE_LIMITS', () => {
  it('has expected defaults', () => {
    expect(DEFAULT_RESOURCE_LIMITS.maxCpuTime).toBe(5000)
    expect(DEFAULT_RESOURCE_LIMITS.maxMemory).toBe(100 * 1024 * 1024)
    expect(DEFAULT_RESOURCE_LIMITS.maxExecutionTime).toBe(30000)
    expect(DEFAULT_RESOURCE_LIMITS.maxFileSize).toBe(10 * 1024 * 1024)
    expect(DEFAULT_RESOURCE_LIMITS.maxNetworkRequests).toBe(100)
  })
})

describe('DEFAULT_PERMISSIONS', () => {
  it('has safe defaults', () => {
    expect(DEFAULT_PERMISSIONS.filesystem.read).toBe(false)
    expect(DEFAULT_PERMISSIONS.filesystem.write).toBe(false)
    expect(DEFAULT_PERMISSIONS.network.enabled).toBe(false)
    expect(DEFAULT_PERMISSIONS.process.enabled).toBe(false)
    expect(DEFAULT_PERMISSIONS.ui.enabled).toBe(true)
    expect(DEFAULT_PERMISSIONS.data.read).toBe(true)
    expect(DEFAULT_PERMISSIONS.data.write).toBe(false)
  })
})

describe('PluginBuilder', () => {
  it('builds a valid plugin', () => {
    const p = plugin()
      .id('my-plugin')
      .name('My Plugin')
      .author('Me')
      .initialize(noop)
      .cleanup(noop)
      .build()

    expect(p.metadata.id).toBe('my-plugin')
    expect(p.metadata.name).toBe('My Plugin')
    expect(p.metadata.author).toBe('Me')
    expect(p.initialize).toBeDefined()
    expect(p.cleanup).toBeDefined()
  })

  it('throws if id is missing', () => {
    expect(() => plugin().name('N').author('A').initialize(noop).cleanup(noop).build()).toThrow(
      'Plugin ID is required',
    )
  })

  it('throws if name is missing', () => {
    expect(() => plugin().id('x').author('A').initialize(noop).cleanup(noop).build()).toThrow(
      'Plugin name is required',
    )
  })

  it('throws if author is missing', () => {
    expect(() => plugin().id('x').name('N').initialize(noop).cleanup(noop).build()).toThrow(
      'Plugin author is required',
    )
  })

  it('throws if initialize is missing', () => {
    expect(() => plugin().id('x').name('N').author('A').cleanup(noop).build()).toThrow(
      'Plugin initialize function is required',
    )
  })

  it('throws if cleanup is missing', () => {
    expect(() => plugin().id('x').name('N').author('A').initialize(noop).build()).toThrow(
      'Plugin cleanup function is required',
    )
  })

  it('sets metadata fields', () => {
    const p = plugin()
      .id('p1')
      .name('Plugin 1')
      .description('Desc')
      .version('2.0.0')
      .author('Author')
      .category('tools')
      .tags('a', 'b')
      .dependency('dep1', '^1.0')
      .minLyraVersion('1.0')
      .maxLyraVersion('3.0')
      .icon('🧩')
      .homepage('https://example.com')
      .repository('https://github.com/example/plugin')
      .license('Apache-2.0')
      .screenshots('s1.png', 's2.png')
      .changelog('https://example.com/changelog')
      .initialize(noop)
      .cleanup(noop)
      .build()

    expect(p.metadata.id).toBe('p1')
    expect(p.metadata.name).toBe('Plugin 1')
    expect(p.metadata.description).toBe('Desc')
    expect(p.metadata.version).toBe('2.0.0')
    expect(p.metadata.author).toBe('Author')
    expect(p.metadata.category).toBe('tools')
    expect(p.metadata.tags).toEqual(['a', 'b'])
    expect(p.metadata.dependencies).toEqual({ dep1: '^1.0' })
    expect(p.metadata.minLyraVersion).toBe('1.0')
    expect(p.metadata.maxLyraVersion).toBe('3.0')
    expect(p.metadata.icon).toBe('🧩')
    expect(p.metadata.homepage).toBe('https://example.com')
    expect(p.metadata.repository).toBe('https://github.com/example/plugin')
    expect(p.metadata.license).toBe('Apache-2.0')
    expect(p.metadata.screenshots).toEqual(['s1.png', 's2.png'])
    expect(p.metadata.changelog).toBe('https://example.com/changelog')
  })

  it('sets config fields', () => {
    const p = plugin()
      .id('p1')
      .name('N')
      .author('A')
      .initialize(noop)
      .cleanup(noop)
      .enabled(false)
      .setting('key1', 'value1')
      .settings({ key2: 42 })
      .permissions({ network: { enabled: true } })
      .resourceLimits({ maxCpuTime: 10000 })
      .autoUpdate(true)
      .priority(5)
      .build()

    expect(p.config.enabled).toBe(false)
    expect(p.config.settings).toEqual({ key2: 42 })
    expect(p.config.permissions.network.enabled).toBe(true)
    expect(p.config.resourceLimits.maxCpuTime).toBe(10000)
    expect(p.config.autoUpdate).toBe(true)
    expect(p.config.priority).toBe(5)
  })

  it('sets hook callbacks', () => {
    const onInstall = vi.fn()
    const onUninstall = vi.fn()
    const p = plugin()
      .id('p1')
      .name('N')
      .author('A')
      .initialize(noop)
      .cleanup(noop)
      .onInstall(onInstall)
      .onUninstall(onUninstall)
      .build()

    p.hooks.onInstall?.()
    p.hooks.onUninstall?.()
    expect(onInstall).toHaveBeenCalled()
    expect(onUninstall).toHaveBeenCalled()
  })

  it('sets api methods', () => {
    const api = { greet: (name: string) => `Hello ${name}` }
    const p = plugin()
      .id('p1')
      .name('N')
      .author('A')
      .initialize(noop)
      .cleanup(noop)
      .api(api)
      .build()

    expect(p.api).toEqual(api)
  })
})

describe('createPlugin', () => {
  it('creates a plugin with required fields', () => {
    const meta = makeMetadata()
    const p = createPlugin(meta, noop, noop)

    expect(p.metadata.id).toBe('test-plugin')
    expect(p.initialize).toBeDefined()
    expect(p.cleanup).toBeDefined()
    expect(p.config.enabled).toBe(true)
  })

  it('accepts optional config overrides', () => {
    const p = createPlugin(makeMetadata(), noop, noop, {
      config: { enabled: false, priority: 10 },
    })
    expect(p.config.enabled).toBe(false)
    expect(p.config.priority).toBe(10)
  })

  it('accepts hooks', () => {
    const onLoad = vi.fn()
    const p = createPlugin(makeMetadata(), noop, noop, {
      hooks: { onLoad },
    })
    p.hooks.onLoad?.()
    expect(onLoad).toHaveBeenCalled()
  })

  it('accepts api', () => {
    const api = { ping: () => 'pong' }
    const p = createPlugin(makeMetadata(), noop, noop, { api })
    expect(p.api).toBe(api)
  })
})

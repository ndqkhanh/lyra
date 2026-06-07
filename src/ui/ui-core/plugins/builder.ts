/**
 * Plugin Builder
 *
 * Fluent API for creating plugins with validation and defaults.
 */

import type {
  Plugin,
  PluginMetadata,
  PluginConfig,
  PluginHooks,
  PluginContext,
  PluginPermissions,
  PluginResourceLimits
} from './manager'

/**
 * Default resource limits
 */
export const DEFAULT_RESOURCE_LIMITS: PluginResourceLimits = {
  maxCpuTime: 5000,
  maxMemory: 100 * 1024 * 1024, // 100 MB
  maxExecutionTime: 30000,
  maxFileSize: 10 * 1024 * 1024, // 10 MB
  maxNetworkRequests: 100
}

/**
 * Default permissions
 */
export const DEFAULT_PERMISSIONS: PluginPermissions = {
  filesystem: { read: false, write: false },
  network: { enabled: false },
  process: { enabled: false },
  ui: { enabled: true },
  data: { read: true, write: false }
}

/**
 * Plugin builder
 */
export class PluginBuilder {
  private plugin: Partial<Plugin> = {
    metadata: {
      id: '',
      name: '',
      description: '',
      version: '1.0.0',
      author: '',
      category: 'other',
      tags: [],
      dependencies: {},
      license: 'MIT'
    },
    config: {
      enabled: true,
      settings: {},
      permissions: { ...DEFAULT_PERMISSIONS },
      resourceLimits: { ...DEFAULT_RESOURCE_LIMITS },
      autoUpdate: false,
      priority: 0
    },
    hooks: {}
  }

  // Metadata
  id(id: string): this {
    this.plugin.metadata!.id = id
    return this
  }

  name(name: string): this {
    this.plugin.metadata!.name = name
    return this
  }

  description(description: string): this {
    this.plugin.metadata!.description = description
    return this
  }

  version(version: string): this {
    this.plugin.metadata!.version = version
    return this
  }

  author(author: string): this {
    this.plugin.metadata!.author = author
    return this
  }

  category(category: PluginMetadata['category']): this {
    this.plugin.metadata!.category = category
    return this
  }

  tags(...tags: string[]): this {
    this.plugin.metadata!.tags = tags
    return this
  }

  dependency(id: string, version: string): this {
    this.plugin.metadata!.dependencies[id] = version
    return this
  }

  minLyraVersion(version: string): this {
    this.plugin.metadata!.minLyraVersion = version
    return this
  }

  maxLyraVersion(version: string): this {
    this.plugin.metadata!.maxLyraVersion = version
    return this
  }

  icon(icon: string): this {
    this.plugin.metadata!.icon = icon
    return this
  }

  homepage(url: string): this {
    this.plugin.metadata!.homepage = url
    return this
  }

  repository(url: string): this {
    this.plugin.metadata!.repository = url
    return this
  }

  license(license: string): this {
    this.plugin.metadata!.license = license
    return this
  }

  screenshots(...urls: string[]): this {
    this.plugin.metadata!.screenshots = urls
    return this
  }

  changelog(url: string): this {
    this.plugin.metadata!.changelog = url
    return this
  }

  // Configuration
  enabled(enabled: boolean): this {
    this.plugin.config!.enabled = enabled
    return this
  }

  setting(key: string, value: unknown): this {
    this.plugin.config!.settings[key] = value
    return this
  }

  settings(settings: Record<string, unknown>): this {
    this.plugin.config!.settings = settings
    return this
  }

  permissions(permissions: Partial<PluginPermissions>): this {
    this.plugin.config!.permissions = {
      ...this.plugin.config!.permissions,
      ...permissions
    }
    return this
  }

  resourceLimits(limits: Partial<PluginResourceLimits>): this {
    this.plugin.config!.resourceLimits = {
      ...this.plugin.config!.resourceLimits,
      ...limits
    }
    return this
  }

  autoUpdate(autoUpdate: boolean): this {
    this.plugin.config!.autoUpdate = autoUpdate
    return this
  }

  priority(priority: number): this {
    this.plugin.config!.priority = priority
    return this
  }

  // Hooks
  onInstall(hook: () => void | Promise<void>): this {
    this.plugin.hooks!.onInstall = hook
    return this
  }

  onUninstall(hook: () => void | Promise<void>): this {
    this.plugin.hooks!.onUninstall = hook
    return this
  }

  onLoad(hook: () => void | Promise<void>): this {
    this.plugin.hooks!.onLoad = hook
    return this
  }

  onUnload(hook: () => void | Promise<void>): this {
    this.plugin.hooks!.onUnload = hook
    return this
  }

  onEnable(hook: () => void | Promise<void>): this {
    this.plugin.hooks!.onEnable = hook
    return this
  }

  onDisable(hook: () => void | Promise<void>): this {
    this.plugin.hooks!.onDisable = hook
    return this
  }

  onUpdate(hook: (oldVersion: string, newVersion: string) => void | Promise<void>): this {
    this.plugin.hooks!.onUpdate = hook
    return this
  }

  onConfigChange(hook: (config: PluginConfig) => void | Promise<void>): this {
    this.plugin.hooks!.onConfigChange = hook
    return this
  }

  // Core functions
  initialize(fn: (context: PluginContext) => void | Promise<void>): this {
    this.plugin.initialize = fn
    return this
  }

  cleanup(fn: (context: PluginContext) => void | Promise<void>): this {
    this.plugin.cleanup = fn
    return this
  }

  api(methods: Record<string, (...args: unknown[]) => unknown | Promise<unknown>>): this {
    this.plugin.api = methods
    return this
  }

  build(): Plugin {
    // Validate required fields
    if (!this.plugin.metadata!.id) {
      throw new Error('Plugin ID is required')
    }

    if (!this.plugin.metadata!.name) {
      throw new Error('Plugin name is required')
    }

    if (!this.plugin.metadata!.author) {
      throw new Error('Plugin author is required')
    }

    if (!this.plugin.initialize) {
      throw new Error('Plugin initialize function is required')
    }

    if (!this.plugin.cleanup) {
      throw new Error('Plugin cleanup function is required')
    }

    return this.plugin as Plugin
  }
}

/**
 * Create a plugin builder
 */
export function plugin(): PluginBuilder {
  return new PluginBuilder()
}

/**
 * Create a simple plugin
 */
export function createPlugin(
  metadata: PluginMetadata,
  initialize: Plugin['initialize'],
  cleanup: Plugin['cleanup'],
  options: {
    config?: Partial<PluginConfig>
    hooks?: PluginHooks
    api?: Plugin['api']
  } = {}
): Plugin {
  return {
    metadata,
    config: {
      enabled: true,
      settings: {},
      permissions: { ...DEFAULT_PERMISSIONS },
      resourceLimits: { ...DEFAULT_RESOURCE_LIMITS },
      autoUpdate: false,
      priority: 0,
      ...options.config
    },
    hooks: options.hooks ?? {},
    initialize,
    cleanup,
    api: options.api
  }
}

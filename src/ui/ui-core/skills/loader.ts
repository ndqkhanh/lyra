/**
 * Skill Loader
 *
 * Utilities for loading skills from various sources (files, URLs, objects).
 */

import type { Skill, SkillMetadata, SkillConfig, SkillHooks } from './registry'

/**
 * Skill source types
 */
export type SkillSource = 'file' | 'url' | 'object' | 'string'

/**
 * Skill loader options
 */
export interface LoaderOptions {
  /** Default configuration for loaded skills */
  defaultConfig?: Partial<SkillConfig>
  /** Validate skill after loading */
  validate?: boolean
  /** Timeout for loading in ms */
  timeout?: number
}

/**
 * Load skill from object
 */
export function loadFromObject(
  obj: Partial<Skill>,
  options: LoaderOptions = {}
): Skill {
  // Merge with defaults
  const skill: Skill = {
    metadata: {
      id: obj.metadata?.id ?? 'unknown',
      name: obj.metadata?.name ?? 'Unknown Skill',
      description: obj.metadata?.description ?? '',
      version: obj.metadata?.version ?? '1.0.0',
      tags: obj.metadata?.tags ?? [],
      dependencies: obj.metadata?.dependencies ?? {},
      ...obj.metadata
    },
    config: {
      enabled: true,
      settings: {},
      priority: 0,
      autoReload: false,
      ...options.defaultConfig,
      ...obj.config
    },
    hooks: obj.hooks ?? {},
    execute: obj.execute ?? (() => {
      throw new Error('Skill execute function not implemented')
    }),
    validate: obj.validate
  }

  return skill
}

/**
 * Create a simple skill
 */
export function createSkill(
  metadata: SkillMetadata,
  execute: Skill['execute'],
  options: {
    config?: Partial<SkillConfig>
    hooks?: SkillHooks
    validate?: Skill['validate']
  } = {}
): Skill {
  return {
    metadata,
    config: {
      enabled: true,
      settings: {},
      priority: 0,
      autoReload: false,
      ...options.config
    },
    hooks: options.hooks ?? {},
    execute,
    validate: options.validate
  }
}

/**
 * Skill builder for fluent API
 */
export class SkillBuilder {
  private skill: Partial<Skill> = {
    metadata: {
      id: '',
      name: '',
      description: '',
      version: '1.0.0',
      tags: [],
      dependencies: {}
    },
    config: {
      enabled: true,
      settings: {},
      priority: 0,
      autoReload: false
    },
    hooks: {}
  }

  id(id: string): this {
    this.skill.metadata!.id = id
    return this
  }

  name(name: string): this {
    this.skill.metadata!.name = name
    return this
  }

  description(description: string): this {
    this.skill.metadata!.description = description
    return this
  }

  version(version: string): this {
    this.skill.metadata!.version = version
    return this
  }

  author(author: string): this {
    this.skill.metadata!.author = author
    return this
  }

  tags(...tags: string[]): this {
    this.skill.metadata!.tags = tags
    return this
  }

  dependency(id: string, version: string): this {
    this.skill.metadata!.dependencies[id] = version
    return this
  }

  minLyraVersion(version: string): this {
    this.skill.metadata!.minLyraVersion = version
    return this
  }

  maxLyraVersion(version: string): this {
    this.skill.metadata!.maxLyraVersion = version
    return this
  }

  icon(icon: string): this {
    this.skill.metadata!.icon = icon
    return this
  }

  homepage(url: string): this {
    this.skill.metadata!.homepage = url
    return this
  }

  repository(url: string): this {
    this.skill.metadata!.repository = url
    return this
  }

  license(license: string): this {
    this.skill.metadata!.license = license
    return this
  }

  enabled(enabled: boolean): this {
    this.skill.config!.enabled = enabled
    return this
  }

  setting(key: string, value: unknown): this {
    this.skill.config!.settings[key] = value
    return this
  }

  priority(priority: number): this {
    this.skill.config!.priority = priority
    return this
  }

  autoReload(autoReload: boolean): this {
    this.skill.config!.autoReload = autoReload
    return this
  }

  onLoad(hook: () => void | Promise<void>): this {
    this.skill.hooks!.onLoad = hook
    return this
  }

  onUnload(hook: () => void | Promise<void>): this {
    this.skill.hooks!.onUnload = hook
    return this
  }

  onEnable(hook: () => void | Promise<void>): this {
    this.skill.hooks!.onEnable = hook
    return this
  }

  onDisable(hook: () => void | Promise<void>): this {
    this.skill.hooks!.onDisable = hook
    return this
  }

  onReload(hook: () => void | Promise<void>): this {
    this.skill.hooks!.onReload = hook
    return this
  }

  execute(fn: Skill['execute']): this {
    this.skill.execute = fn
    return this
  }

  validate(fn: Skill['validate']): this {
    this.skill.validate = fn
    return this
  }

  build(): Skill {
    if (!this.skill.metadata!.id) {
      throw new Error('Skill ID is required')
    }

    if (!this.skill.metadata!.name) {
      throw new Error('Skill name is required')
    }

    if (!this.skill.execute) {
      throw new Error('Skill execute function is required')
    }

    return this.skill as Skill
  }
}

/**
 * Create a skill builder
 */
export function skill(): SkillBuilder {
  return new SkillBuilder()
}

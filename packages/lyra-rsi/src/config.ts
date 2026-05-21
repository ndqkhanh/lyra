import { Config } from './types';

export const defaultConfig: Config = {
  llm: {
    provider: process.env.LLM_PROVIDER as 'anthropic' | 'openai' || 'anthropic',
    model: process.env.LLM_MODEL || 'claude-3-opus-20240229',
    apiKey: process.env.ANTHROPIC_API_KEY || process.env.OPENAI_API_KEY || '',
  },
  agent0: {
    maxIterations: parseInt(process.env.AGENT0_MAX_ITERATIONS || '10'),
    syntheticTaskCount: parseInt(process.env.AGENT0_SYNTHETIC_TASK_COUNT || '100'),
  },
  skillRL: {
    evolutionInterval: parseInt(process.env.SKILLRL_EVOLUTION_INTERVAL || '3600000'),
    topK: parseInt(process.env.SKILLRL_TOP_K || '10'),
    errorThreshold: parseFloat(process.env.SKILLRL_ERROR_THRESHOLD || '0.3'),
    confidenceThreshold: parseFloat(process.env.SKILLRL_CONFIDENCE_THRESHOLD || '0.7'),
  },
  metaHarness: {
    maxIterations: parseInt(process.env.META_HARNESS_MAX_ITERATIONS || '5'),
    searchDir: process.env.META_HARNESS_SEARCH_DIR || './benchmarks',
  },
  alphaEvolve: {
    maxGenerations: parseInt(process.env.ALPHA_EVOLVE_MAX_GENERATIONS || '10'),
    populationSize: parseInt(process.env.ALPHA_EVOLVE_POPULATION_SIZE || '20'),
    mutationRate: parseFloat(process.env.ALPHA_EVOLVE_MUTATION_RATE || '0.1'),
  },
  postTraining: {
    computeBudgetPerGeneration: parseInt(process.env.POST_TRAINING_COMPUTE_BUDGET || '10000'),
  },
  hyperAgent: {
    sandboxEnabled: process.env.HYPER_AGENT_SANDBOX_ENABLED === 'true',
  },
  safety: {
    maxDegradation: parseFloat(process.env.SAFETY_MAX_DEGRADATION || '0.1'),
    explosionThreshold: parseFloat(process.env.SAFETY_EXPLOSION_THRESHOLD || '2.0'),
    generationInterval: parseInt(process.env.SAFETY_GENERATION_INTERVAL || '5'),
  },
};

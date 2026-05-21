import { IntelligenceExplosion } from '../core/intelligence-explosion';
import { Config } from '../types';

describe('IntelligenceExplosion', () => {
  let intelligenceExplosion: IntelligenceExplosion;
  let mockConfig: Config;

  beforeEach(() => {
    mockConfig = {
      llm: {
        provider: 'anthropic',
        model: 'claude-3-opus-20240229',
        apiKey: 'test-key',
      },
      agent0: {
        maxIterations: 2,
        syntheticTaskCount: 3,
      },
      skillRL: {
        evolutionInterval: 1000,
        topK: 3,
        errorThreshold: 0.3,
        confidenceThreshold: 0.7,
      },
      metaHarness: {
        maxIterations: 2,
        searchDir: './test-data',
      },
      alphaEvolve: {
        maxGenerations: 2,
        populationSize: 3,
        mutationRate: 0.1,
      },
      postTraining: {
        computeBudgetPerGeneration: 1000,
      },
      hyperAgent: {
        sandboxEnabled: true,
      },
      safety: {
        maxDegradation: 0.1,
        explosionThreshold: 2.0,
        generationInterval: 5,
      },
    };

    intelligenceExplosion = new IntelligenceExplosion(mockConfig);
  });

  describe('initialize', () => {
    it('should initialize successfully', async () => {
      await expect(intelligenceExplosion.initialize()).resolves.not.toThrow();
    });
  });

  describe('runGeneration', () => {
    it('should run generation successfully', async () => {
      await intelligenceExplosion.initialize();
      await expect(intelligenceExplosion.runGeneration()).resolves.not.toThrow();
    });
  });

  describe('getMetrics', () => {
    it('should return metrics', () => {
      const metrics = intelligenceExplosion.getMetrics();
      expect(metrics).toBeDefined();
      expect(metrics).toHaveProperty('reasoning');
      expect(metrics).toHaveProperty('planning');
      expect(metrics).toHaveProperty('coding');
    });
  });

  describe('getStatus', () => {
    it('should return status', () => {
      const status = intelligenceExplosion.getStatus();
      expect(status).toBeDefined();
      expect(status).toHaveProperty('generation');
      expect(status).toHaveProperty('phase');
      expect(status).toHaveProperty('metrics');
    });
  });
});

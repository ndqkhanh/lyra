import { LLMClient } from '../core/llm-client';
import { Agent0 } from '../agent0';
import { SkillRL } from '../skillrl';
import { MetaHarness } from '../meta-harness';
import { CLIAnything } from '../cli-anything';
import { AlphaEvolve } from '../alpha-evolve';
import { PostTraining } from '../post-training';
import { HyperAgent } from '../hyper-agent';
import { Config, PerformanceMetrics, Benchmark } from '../types';
import { Logger, sleep, generateId } from '../utils/helpers';

interface SystemStatus {
  generation: number;
  phase: 'initializing' | 'running' | 'complete' | 'safety-halt' | 'error';
  metrics: PerformanceMetrics;
  lastScore: number;
  improvement: number;
}

export class IntelligenceExplosion {
  private llm: LLMClient;
  private logger: Logger;
  private config: Config;

  // All 7 pillars
  private agent0: Agent0;
  private skillRL: SkillRL;
  private metaHarness: MetaHarness;
  private cliAnything: CLIAnything;
  private alphaEvolve: AlphaEvolve;
  private postTraining: PostTraining;
  private hyperAgent: HyperAgent;

  // State
  private generation: number = 0;
  private phase: SystemStatus['phase'] = 'initializing';
  private currentMetrics: PerformanceMetrics;
  private lastScore: number = 0;
  private improvement: number = 0;
  private initialized: boolean = false;

  constructor(config: Config) {
    this.config = config;
    this.llm = new LLMClient(config.llm);
    this.logger = new Logger('IntelligenceExplosion');

    // Initialize all pillars
    this.agent0 = new Agent0(this.llm, config.agent0);
    this.skillRL = new SkillRL(this.llm, config.skillRL);
    this.metaHarness = new MetaHarness(this.llm, config.metaHarness);
    this.cliAnything = new CLIAnything(this.llm);
    this.alphaEvolve = new AlphaEvolve(this.llm, config.alphaEvolve);
    this.postTraining = new PostTraining(this.llm, config.postTraining);
    this.hyperAgent = new HyperAgent(this.llm, config.hyperAgent);

    // Initialize metrics
    this.currentMetrics = this.createInitialMetrics();
  }

  async initialize(): Promise<void> {
    if (this.initialized) {
      this.logger.info('System already initialized');
      return;
    }

    this.logger.info('Initializing Intelligence Explosion System...');
    
    // Evaluate initial capabilities
    this.lastScore = await this.evaluateCapabilities();
    this.logger.info(`Initial capability score: ${this.lastScore.toFixed(4)}`);
    
    this.phase = 'running';
    this.initialized = true;
    this.logger.info('System initialized successfully');
  }

  async runGeneration(): Promise<void> {
    if (!this.initialized) {
      throw new Error('System not initialized. Call initialize() first.');
    }

    if (this.phase !== 'running') {
      this.logger.info(`Cannot run generation in phase: ${this.phase}`);
      return;
    }

    this.generation++;
    this.logger.info(`\n${'='.repeat(60)}`);
    this.logger.info(`GENERATION ${this.generation}`);
    this.logger.info('='.repeat(60));

    try {
      // Phase 1: Agent0 - Bootstrap from zero data
      this.logger.info('\n📍 Phase 1: Agent0 self-evolution...');
      await this.agent0.bootstrapFromZero();
      const experienceCount = this.agent0.getExperienceCount();
      this.logger.info(`   Experience buffer: ${experienceCount} entries`);

      // Phase 2: SkillRL - Evolve skill library
      this.logger.info('\n📍 Phase 2: SkillRL library evolution...');
      await this.skillRL.evolveSkillLibrary();
      const skillStats = this.skillRL.getLibraryStats();
      this.logger.info(`   Skills: ${skillStats.skillCount}, Mistakes: ${skillStats.mistakeCount}`);

      // Phase 3: CLI-Anything - Expand tool access
      this.logger.info('\n📍 Phase 3: CLI-Anything tool discovery...');
      await this.cliAnything.discoverAndInstallTools();
      const tools = this.cliAnything.getInstalledTools();
      this.logger.info(`   Tools available: ${tools.length}`);

      // Phase 4: Meta-Harness - Optimize harnesses
      this.logger.info('\n📍 Phase 4: Meta-Harness optimization...');
      const components = ['reasoning', 'planning'];
      for (const component of components) {
        const benchmark = this.getBenchmark(component);
        await this.metaHarness.optimizeHarness(component, benchmark);
      }

      // Phase 5: AlphaEvolve - Evolve algorithms
      this.logger.info('\n📍 Phase 5: AlphaEvolve algorithm evolution...');
      const algorithms = ['search'];
      for (const algo of algorithms) {
        const benchmark = this.getBenchmark(algo);
        await this.alphaEvolve.evolveAlgorithm(`Improve ${algo} algorithm`, benchmark);
      }

      // Phase 6: PostTraining - Self-improve via post-training
      this.logger.info('\n📍 Phase 6: PostTraining self-improvement...');
      this.currentMetrics = await this.evaluateCapabilitiesDetailed();
      await this.postTraining.generateSyntheticData(this.currentMetrics);

      // Phase 7: HyperAgent - Architectural self-modification
      this.logger.info('\n📍 Phase 7: HyperAgent self-modification...');
      const bottlenecks = await this.hyperAgent.analyzeBottlenecks(this.currentMetrics);
      this.logger.info(`   Bottlenecks identified: ${bottlenecks.length}`);

      // Evaluate improvement
      const newScore = await this.evaluateCapabilities();
      this.improvement = newScore - this.lastScore;
      const improvementPercent = (this.improvement / this.lastScore) * 100;

      this.logger.info(`\n${'='.repeat(60)}`);
      this.logger.info(`GENERATION ${this.generation} COMPLETE`);
      this.logger.info('='.repeat(60));
      this.logger.info(`Previous score: ${this.lastScore.toFixed(4)}`);
      this.logger.info(`New score:      ${newScore.toFixed(4)}`);
      this.logger.info(`Improvement:    ${this.improvement >= 0 ? '+' : ''}${this.improvement.toFixed(4)} (${improvementPercent >= 0 ? '+' : ''}${improvementPercent.toFixed(2)}%)`);

      // Check for intelligence explosion
      if (improvementPercent > this.config.safety.explosionThreshold * 100) {
        this.logger.info('\n🔥 INTELLIGENCE EXPLOSION DETECTED! 🔥');
      }

      // Safety check
      if (newScore < this.lastScore * (1 - this.config.safety.maxDegradation)) {
        this.logger.info('\n⚠️  Performance degradation detected. Entering safety halt...');
        this.phase = 'safety-halt';
        return;
      }

      this.lastScore = newScore;

      // Check if we should complete
      if (this.generation >= this.config.safety.generationInterval) {
        this.phase = 'complete';
      }

      // Wait before next generation
      await sleep(1000);

    } catch (error) {
      this.logger.info(`Generation ${this.generation} failed:`, error);
      this.phase = 'error';
      throw error;
    }
  }

  getStatus(): SystemStatus {
    return {
      generation: this.generation,
      phase: this.phase,
      metrics: this.currentMetrics,
      lastScore: this.lastScore,
      improvement: this.improvement,
    };
  }

  getMetrics(): PerformanceMetrics {
    return this.currentMetrics;
  }

  private createInitialMetrics(): PerformanceMetrics {
    return {
      reasoning: {
        mathReasoning: 0.6,
        logicalReasoning: 0.65,
        commonSense: 0.7,
      },
      planning: {
        taskPlanning: 0.62,
        longHorizon: 0.58,
        multiStep: 0.64,
      },
      coding: {
        humanEval: 0.68,
        mbpp: 0.66,
        apps: 0.61,
      },
      toolUse: {
        apiUsage: 0.72,
        composition: 0.67,
        errorRecovery: 0.63,
      },
      learning: {
        fewShot: 0.71,
        zeroShot: 0.65,
        transfer: 0.69,
      },
      creativity: {
        novelty: 0.64,
        diversity: 0.68,
        quality: 0.66,
      },
    };
  }

  private async evaluateCapabilitiesDetailed(): Promise<PerformanceMetrics> {
    // Simulate comprehensive evaluation with slight improvements
    const baseMetrics = this.currentMetrics;
    const improvement = 0.01 + Math.random() * 0.05;

    return {
      reasoning: {
        mathReasoning: Math.min(1.0, baseMetrics.reasoning.mathReasoning + improvement),
        logicalReasoning: Math.min(1.0, baseMetrics.reasoning.logicalReasoning + improvement),
        commonSense: Math.min(1.0, baseMetrics.reasoning.commonSense + improvement),
      },
      planning: {
        taskPlanning: Math.min(1.0, baseMetrics.planning.taskPlanning + improvement),
        longHorizon: Math.min(1.0, baseMetrics.planning.longHorizon + improvement),
        multiStep: Math.min(1.0, baseMetrics.planning.multiStep + improvement),
      },
      coding: {
        humanEval: Math.min(1.0, baseMetrics.coding.humanEval + improvement),
        mbpp: Math.min(1.0, baseMetrics.coding.mbpp + improvement),
        apps: Math.min(1.0, baseMetrics.coding.apps + improvement),
      },
      toolUse: {
        apiUsage: Math.min(1.0, baseMetrics.toolUse.apiUsage + improvement),
        composition: Math.min(1.0, baseMetrics.toolUse.composition + improvement),
        errorRecovery: Math.min(1.0, baseMetrics.toolUse.errorRecovery + improvement),
      },
      learning: {
        fewShot: Math.min(1.0, baseMetrics.learning.fewShot + improvement),
        zeroShot: Math.min(1.0, baseMetrics.learning.zeroShot + improvement),
        transfer: Math.min(1.0, baseMetrics.learning.transfer + improvement),
      },
      creativity: {
        novelty: Math.min(1.0, baseMetrics.creativity.novelty + improvement),
        diversity: Math.min(1.0, baseMetrics.creativity.diversity + improvement),
        quality: Math.min(1.0, baseMetrics.creativity.quality + improvement),
      },
    };
  }

  private async evaluateCapabilities(): Promise<number> {
    const metrics = await this.evaluateCapabilitiesDetailed();
    this.currentMetrics = metrics;

    // Weighted average
    const score =
      (metrics.reasoning.mathReasoning + metrics.reasoning.logicalReasoning + metrics.reasoning.commonSense) / 3 * 0.25 +
      (metrics.planning.taskPlanning + metrics.planning.longHorizon + metrics.planning.multiStep) / 3 * 0.20 +
      (metrics.coding.humanEval + metrics.coding.mbpp + metrics.coding.apps) / 3 * 0.20 +
      (metrics.toolUse.apiUsage + metrics.toolUse.composition + metrics.toolUse.errorRecovery) / 3 * 0.15 +
      (metrics.learning.fewShot + metrics.learning.zeroShot + metrics.learning.transfer) / 3 * 0.10 +
      (metrics.creativity.novelty + metrics.creativity.diversity + metrics.creativity.quality) / 3 * 0.10;

    return score;
  }

  private getBenchmark(component: string): Benchmark {
    return {
      id: generateId(),
      name: `${component}-benchmark`,
      tasks: [],
      evaluator: (_result: any) => Math.random(),
    };
  }
}

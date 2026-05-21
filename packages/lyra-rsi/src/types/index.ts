// Core type definitions for Lyra RSI System

export interface Task {
  id: string;
  description: string;
  type: string;
  difficulty?: number;
  requirements?: string[];
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  usage: string;
  parameters?: Record<string, any>;
}

export interface Skill {
  id: string;
  title: string;
  principle: string;
  whenToApply: string;
  examples: Example[];
  successRate: number;
  executionCount?: number;
  lastUsed?: number;
  tags?: string[];
}

export interface Example {
  input: string;
  output: string;
  explanation?: string;
}

export interface Experience {
  id: string;
  task: Task;
  actions: Action[];
  outcome: Outcome;
  success: boolean;
  timestamp: number;
  duration: number;
}

export interface Action {
  type: string;
  tool?: string;
  parameters?: Record<string, any>;
  result?: any;
  error?: string;
}

export interface Outcome {
  success: boolean;
  result?: any;
  error?: string;
  metrics?: Record<string, number>;
}

export interface Trajectory {
  id: string;
  task: Task;
  steps: Step[];
  success: boolean;
  reward: number;
}

export interface Step {
  action: Action;
  observation: any;
  reward: number;
}

export interface Benchmark {
  id: string;
  name: string;
  tasks: Task[];
  evaluator: (result: any) => number;
}

export interface PerformanceMetrics {
  reasoning: {
    mathReasoning: number;
    logicalReasoning: number;
    commonSense: number;
  };
  planning: {
    taskPlanning: number;
    longHorizon: number;
    multiStep: number;
  };
  coding: {
    humanEval: number;
    mbpp: number;
    apps: number;
  };
  toolUse: {
    apiUsage: number;
    composition: number;
    errorRecovery: number;
  };
  learning: {
    fewShot: number;
    zeroShot: number;
    transfer: number;
  };
  creativity: {
    novelty: number;
    diversity: number;
    quality: number;
  };
}

export interface Algorithm {
  id: string;
  code: string;
  fitness: number | null;
  metadata?: {
    parent?: string;
    parents?: string[];
    type?: string;
    hypothesis?: string;
    mutationType?: string;
  };
}

export interface HarnessCode {
  id: string;
  component: string;
  code: string;
  score: number;
  iteration: number;
  trace?: any;
}

export interface Candidate {
  id: string;
  code: string;
  score: number;
  trace: any;
  iteration: number;
  component?: string;
}

export interface CandidateMetadata {
  id: string;
  score: number;
  iteration: number;
  timestamp: number;
}

export interface ProposalContext {
  component: string;
  topCandidates: Array<{
    id: string;
    score: number;
    code: string;
    trace: any;
  }>;
  recentCandidates: Array<{
    id: string;
    score: number;
    summary: string;
  }>;
  failurePatterns: FailurePattern[];
  successPatterns: SuccessPattern[];
  allCandidates?: CandidateMetadata[];
}

export interface FailurePattern {
  pattern: string;
  count: number;
  rootCause: string;
}

export interface SuccessPattern {
  pattern: string;
  improvement: number;
}

export interface Dataset {
  examples: DataExample[];
  metadata: {
    source: string;
    targetWeaknesses?: string[];
    generatedAt: number;
  };
}

export interface DataExample {
  input: string;
  output: string;
  explanation?: string;
}

export interface TrainingStrategy {
  strategy: string;
  reasoning: string;
  expectedImprovement: number;
  estimatedCost: number;
}

export interface Weakness {
  taskType: string;
  errorRate: number;
  failureModes: string[];
}

export interface Bottleneck {
  type: string;
  component: string;
  impact: number;
  evidence: string;
  performanceData: any;
}

export interface ArchitecturalChange {
  description: string;
  reasoning: string;
  code: string;
  tests: string[];
  rollbackPlan: string;
  expectedImprovement: number;
}

export interface VerificationResult {
  safe: boolean;
  improvement: number;
  reason: string;
}

export interface SafetyReport {
  safe: boolean;
  performance: number;
  regressions: string[];
  newCapabilities: string[];
}

export interface ComputeBudget {
  total: number;
  used: number;
  remaining: number;
}

export interface LLMConfig {
  provider: 'anthropic' | 'openai';
  model: string;
  apiKey: string;
  temperature?: number;
  maxTokens?: number;
}

export interface Config {
  llm: LLMConfig;
  agent0: {
    maxIterations: number;
    syntheticTaskCount: number;
  };
  skillRL: {
    evolutionInterval: number;
    topK: number;
    errorThreshold: number;
    confidenceThreshold: number;
  };
  metaHarness: {
    maxIterations: number;
    searchDir: string;
  };
  alphaEvolve: {
    maxGenerations: number;
    populationSize: number;
    mutationRate: number;
  };
  postTraining: {
    computeBudgetPerGeneration: number;
  };
  hyperAgent: {
    sandboxEnabled: boolean;
  };
  safety: {
    maxDegradation: number;
    explosionThreshold: number;
    generationInterval: number;
  };
}

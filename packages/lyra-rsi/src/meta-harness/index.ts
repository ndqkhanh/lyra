import { LLMClient } from '../core/llm-client';
import { Benchmark, HarnessCode, Candidate, CandidateMetadata, ProposalContext } from '../types';
import { Logger, generateId, ensureDir, readJsonFile, writeJsonFile } from '../utils/helpers';
import * as fs from 'fs';
import * as path from 'path';
import * as glob from 'glob';

export class MetaHarness {
  private llm: LLMClient;
  private logger: Logger;
  private searchDir: string;
  private maxIterations: number;

  constructor(llm: LLMClient, config: { maxIterations: number; searchDir: string }) {
    this.llm = llm;
    this.logger = new Logger('MetaHarness');
    this.maxIterations = config.maxIterations;
    this.searchDir = config.searchDir;
    ensureDir(this.searchDir);
  }

  async optimizeHarness(component: string, benchmark: Benchmark): Promise<HarnessCode> {
    this.logger.info(`🔧 Optimizing ${component} harness...`);

    // 1. Evaluate baseline
    const baseline = await this.evaluateBaseline(component, benchmark);
    this.saveHarnessToFilesystem(baseline);
    this.logger.info(`Baseline score: ${baseline.score}`);

    let bestCandidate = baseline;

    // 2. Optimization loop
    for (let iteration = 0; iteration < this.maxIterations; iteration++) {
      this.logger.info(`\n--- Iteration ${iteration + 1}/${this.maxIterations} ---`);

      // 3. Build proposal context from filesystem
      const context = await this.buildProposalContext(component, bestCandidate.score);

      // 4. Generate variant
      const variantCode = await this.proposeVariant(component, context);

      // 5. Evaluate variant
      const score = await this.evaluateHarness(variantCode, benchmark);

      // 6. Save to filesystem
      const candidate: Candidate = {
        id: generateId(),
        code: variantCode,
        score,
        trace: { iteration, timestamp: Date.now() },
        iteration,
        component,
      };
      this.saveCandidateToFilesystem(candidate);

      // 7. Check for improvement
      const improvement = score - bestCandidate.score;
      if (improvement > 0) {
        this.logger.info(`✅ Improvement: +${improvement.toFixed(4)} (${score.toFixed(4)})`);
        bestCandidate = {
          id: candidate.id,
          code: candidate.code,
          score: candidate.score,
          iteration: candidate.iteration,
          component: component,
          trace: candidate.trace,
        };
      } else {
        this.logger.info(`❌ No improvement: ${score.toFixed(4)} vs ${bestCandidate.score.toFixed(4)}`);
      }
    }

    this.logger.info(`\n🎯 Final score: ${bestCandidate.score.toFixed(4)} (improvement: +${(bestCandidate.score - baseline.score).toFixed(4)})`);
    return bestCandidate;
  }

  private async evaluateBaseline(component: string, benchmark: Benchmark): Promise<HarnessCode> {
    const baselineCode = this.getBaselineCode(component);
    const score = await this.evaluateHarness(baselineCode, benchmark);

    return {
      id: generateId(),
      code: baselineCode,
      score,
      trace: { baseline: true, timestamp: Date.now() },
      iteration: 0,
      component,
    };
  }

  private getBaselineCode(component: string): string {
    // Return simple baseline implementations
    const baselines: Record<string, string> = {
      reasoning: `
export class ReasoningHarness {
  async reason(task: string): Promise<string> {
    // Simple chain-of-thought reasoning
    const steps = [
      "1. Understand the task",
      "2. Break down into steps",
      "3. Execute each step",
      "4. Synthesize result"
    ];
    return steps.join("\\n");
  }
}`,
      planning: `
export class PlanningHarness {
  async plan(goal: string): Promise<string[]> {
    // Simple sequential planning
    return [
      "Analyze goal",
      "Identify resources",
      "Create action sequence",
      "Execute plan"
    ];
  }
}`,
      'tool-selection': `
export class ToolSelectionHarness {
  async selectTool(task: string, tools: any[]): Promise<any> {
    // Simple first-match selection
    return tools[0];
  }
}`,
      memory: `
export class MemoryHarness {
  private store: Map<string, any> = new Map();
  
  async store(key: string, value: any): Promise<void> {
    this.store.set(key, value);
  }
  
  async retrieve(key: string): Promise<any> {
    return this.store.get(key);
  }
}`,
    };

    return baselines[component] || '// Baseline code';
  }

  private async evaluateHarness(code: string, _benchmark: Benchmark): Promise<number> {
    // Simulate evaluation
    // In real implementation, this would execute the harness on benchmark tasks
    const baseScore = 0.5;
    const randomVariation = (Math.random() - 0.5) * 0.2;
    const codeQualityBonus = code.length > 200 ? 0.1 : 0;
    
    return Math.max(0, Math.min(1, baseScore + randomVariation + codeQualityBonus));
  }

  private async buildProposalContext(component: string, currentBestScore: number): Promise<ProposalContext> {
    const candidates = this.listCandidates(component);

    // Sort by score
    candidates.sort((a, b) => b.score - a.score);

    // Get top performers
    const topCandidates = candidates.slice(0, 3).map(c => ({
      id: c.id,
      score: c.score,
      code: this.readSourceCode(c.id),
      trace: this.readExecutionTrace(c.id),
    }));

    // Get recent attempts
    const recentCandidates = candidates.slice(-5).map(c => ({
      id: c.id,
      score: c.score,
      summary: `Iteration ${c.iteration}, Score: ${c.score.toFixed(4)}`,
    }));

    return {
      component,
      topCandidates,
      recentCandidates,
      failurePatterns: this.analyzeFailures(candidates.filter(c => c.score < currentBestScore)),
      successPatterns: this.analyzeSuccesses(candidates.filter(c => c.score >= currentBestScore)),
      allCandidates: candidates,
    };
  }

  private async proposeVariant(component: string, context: ProposalContext): Promise<string> {
    const prompt = `You are optimizing the ${component} component of an AI agent harness.

# Current Best Performance
Score: ${context.topCandidates[0]?.score.toFixed(4) || 'N/A'}

# Top Performing Variant
${context.topCandidates[0] ? `
\`\`\`typescript
${context.topCandidates[0].code}
\`\`\`
` : 'No variants yet'}

# Recent Attempts
${context.recentCandidates.map(c => `- ${c.summary}`).join('\n')}

# Success Patterns
${context.successPatterns.map(p => `- ${p.pattern}: +${p.improvement.toFixed(4)}`).join('\n') || '- None identified yet'}

# Failure Patterns
${context.failurePatterns.map(p => `- ${p.pattern} (${p.count} times): ${p.rootCause}`).join('\n') || '- None identified yet'}

# Your Task
Propose an improved variant that:
1. Builds on successful patterns
2. Avoids known failure modes
3. Introduces a novel improvement

Output ONLY the improved TypeScript code, no explanations.`;

    try {
      const response = await this.llm.generate(prompt);
      
      // Extract code from response
      if (typeof response === 'string') {
        const codeMatch = response.match(/```typescript\n([\s\S]*?)\n```/) || response.match(/```\n([\s\S]*?)\n```/);
        return codeMatch ? codeMatch[1] : response;
      }
      
      return this.getBaselineCode(component);
    } catch (error) {
      this.logger.error('Failed to propose variant:', error);
      return this.getBaselineCode(component);
    }
  }

  private listCandidates(component?: string): CandidateMetadata[] {
    const pattern = path.join(this.searchDir, '*', 'metadata.json');
    const files = glob.sync(pattern);

    const candidates: CandidateMetadata[] = [];

    for (const file of files) {
      const metadata = readJsonFile<any>(file);
      if (metadata && (!component || metadata.component === component)) {
        const scoreFile = path.join(path.dirname(file), 'score.json');
        const scoreData = readJsonFile<any>(scoreFile);
        
        candidates.push({
          id: metadata.id,
          score: scoreData?.score || 0,
          iteration: scoreData?.iteration || 0,
          timestamp: metadata.timestamp,
        });
      }
    }

    return candidates;
  }

  private readSourceCode(candidateId: string): string {
    const codePath = path.join(this.searchDir, candidateId, 'code.ts');
    if (fs.existsSync(codePath)) {
      return fs.readFileSync(codePath, 'utf-8');
    }
    return '// Code not found';
  }

  private readExecutionTrace(candidateId: string): any {
    const tracePath = path.join(this.searchDir, candidateId, 'trace.json');
    return readJsonFile(tracePath) || {};
  }

  private saveCandidateToFilesystem(candidate: Candidate): void {
    const dir = path.join(this.searchDir, candidate.id);
    ensureDir(dir);

    // Save code
    fs.writeFileSync(path.join(dir, 'code.ts'), candidate.code, 'utf-8');

    // Save score
    writeJsonFile(path.join(dir, 'score.json'), {
      score: candidate.score,
      iteration: candidate.iteration,
    });

    // Save trace
    writeJsonFile(path.join(dir, 'trace.json'), candidate.trace);

    // Save metadata
    writeJsonFile(path.join(dir, 'metadata.json'), {
      id: candidate.id,
      timestamp: Date.now(),
      component: candidate.component,
    });
  }

  private saveHarnessToFilesystem(harness: HarnessCode): void {
    const dir = path.join(this.searchDir, harness.id);
    ensureDir(dir);

    // Save code
    fs.writeFileSync(path.join(dir, 'code.ts'), harness.code, 'utf-8');

    // Save score
    writeJsonFile(path.join(dir, 'score.json'), {
      score: harness.score,
      iteration: harness.iteration,
    });

    // Save trace
    if (harness.trace) {
      writeJsonFile(path.join(dir, 'trace.json'), harness.trace);
    }

    // Save metadata
    writeJsonFile(path.join(dir, 'metadata.json'), {
      id: harness.id,
      timestamp: Date.now(),
      component: harness.component,
    });
  }

  private analyzeFailures(failures: CandidateMetadata[]): Array<{ pattern: string; count: number; rootCause: string }> {
    if (failures.length === 0) return [];

    return [
      {
        pattern: 'Low complexity',
        count: failures.filter(f => f.score < 0.4).length,
        rootCause: 'Implementation too simple',
      },
    ];
  }

  private analyzeSuccesses(successes: CandidateMetadata[]): Array<{ pattern: string; improvement: number }> {
    if (successes.length === 0) return [];

    return [
      {
        pattern: 'Structured approach',
        improvement: 0.1,
      },
    ];
  }
}

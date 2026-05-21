import { LLMClient } from '../core/llm-client';
import { Tool } from '../types';
import { Logger, generateId } from '../utils/helpers';

export class CLIAnything {
  private llm: LLMClient;
  private logger: Logger;
  private installedHarnesses: Map<string, Harness> = new Map();

  constructor(llm: LLMClient) {
    this.llm = llm;
    this.logger = new Logger('CLI-Anything');
  }

  async discoverAndInstallTools(): Promise<void> {
    this.logger.info('🔍 Discovering and installing tools...');

    // 1. Scan for software that could be useful
    const potentialTools = await this.scanEnvironment();
    this.logger.info(`Found ${potentialTools.length} potential tools`);

    // 2. Generate harnesses for tools
    for (const tool of potentialTools) {
      try {
        const harness = await this.generateHarness(tool);
        await this.installHarness(harness);
        this.logger.info(`✅ Installed harness for ${tool.name}`);
      } catch (error) {
        this.logger.error(`Failed to generate harness for ${tool.name}:`, error);
      }
    }

    this.logger.info(`Total harnesses installed: ${this.installedHarnesses.size}`);
  }

  private async scanEnvironment(): Promise<Software[]> {
    // Simulate scanning for available software
    return [
      { name: 'git', repoPath: '/usr/bin/git', description: 'Version control system' },
      { name: 'docker', repoPath: '/usr/bin/docker', description: 'Container platform' },
      { name: 'npm', repoPath: '/usr/bin/npm', description: 'Package manager' },
      { name: 'curl', repoPath: '/usr/bin/curl', description: 'HTTP client' },
    ];
  }

  private async generateHarness(tool: Software): Promise<Harness> {
    this.logger.info(`Generating harness for ${tool.name}...`);

    // Phase 1-3: Design CLI commands
    const commands = await this.designCommands(tool);

    // Phase 4: Generate harness code
    const harnessCode = await this.generateHarnessCode(tool, commands);

    return {
      tool: tool.name,
      code: harnessCode,
      tests: [],
      docs: `# ${tool.name} Harness\n\n${tool.description}`,
      metadata: {
        version: '1.0.0',
        generatedAt: Date.now(),
        testsPassing: 0,
        testsTotal: 0,
      },
    };
  }

  private async designCommands(tool: Software): Promise<CLICommand[]> {
    const prompt = `Design CLI commands for ${tool.name}:

Description: ${tool.description}

Requirements:
1. Commands should be intuitive and follow Unix conventions
2. Use kebab-case for command names
3. Support both short (-f) and long (--file) flags
4. Provide sensible defaults

Output format:
{
  "commands": [
    {
      "name": "command-name",
      "description": "What it does",
      "flags": [
        { "short": "f", "long": "file", "description": "Input file" }
      ]
    }
  ]
}`;

    try {
      const response = await this.llm.generateStructured<{ commands: CLICommand[] }>(prompt);
      return response.commands;
    } catch (error) {
      this.logger.error('Failed to design commands:', error);
      return [];
    }
  }

  private async generateHarnessCode(tool: Software, commands: CLICommand[]): Promise<string> {
    const prompt = `Generate a TypeScript harness for ${tool.name} with these commands:

${commands.map(c => `- ${c.name}: ${c.description}`).join('\n')}

The harness should:
1. Provide a clean API for each command
2. Handle errors gracefully
3. Return structured results

Output ONLY the TypeScript code.`;

    try {
      const response = await this.llm.generate(prompt);
      
      if (typeof response === 'string') {
        const codeMatch = response.match(/```typescript\n([\s\S]*?)\n```/) || response.match(/```\n([\s\S]*?)\n```/);
        return codeMatch ? codeMatch[1] : response;
      }
      
      return `// Harness for ${tool.name}`;
    } catch (error) {
      this.logger.error('Failed to generate harness code:', error);
      return `// Harness for ${tool.name}`;
    }
  }

  private async installHarness(harness: Harness): Promise<void> {
    this.installedHarnesses.set(harness.tool, harness);
  }

  getInstalledTools(): Tool[] {
    return Array.from(this.installedHarnesses.values()).map(h => ({
      id: generateId(),
      name: h.tool,
      description: h.docs,
      usage: `${h.tool} CLI harness`,
    }));
  }
}

interface Software {
  name: string;
  repoPath: string;
  description: string;
}

interface CLICommand {
  name: string;
  description: string;
  flags?: Array<{
    short: string;
    long: string;
    description: string;
  }>;
}

interface Harness {
  tool: string;
  code: string;
  tests: any[];
  docs: string;
  metadata: {
    version: string;
    generatedAt: number;
    testsPassing: number;
    testsTotal: number;
  };
}

import Anthropic from '@anthropic-ai/sdk';
import OpenAI from 'openai';
import { LLMConfig } from '../types';

export class LLMClient {
  private anthropic?: Anthropic;
  private openai?: OpenAI;
  private config: LLMConfig;

  constructor(config: LLMConfig) {
    this.config = config;
    
    if (config.provider === 'anthropic') {
      this.anthropic = new Anthropic({
        apiKey: config.apiKey,
      });
    } else if (config.provider === 'openai') {
      this.openai = new OpenAI({
        apiKey: config.apiKey,
      });
    }
  }

  async generate(prompt: string, options?: { temperature?: number; maxTokens?: number }): Promise<any> {
    const temperature = options?.temperature ?? this.config.temperature ?? 0.7;
    const maxTokens = options?.maxTokens ?? this.config.maxTokens ?? 4096;

    if (this.config.provider === 'anthropic' && this.anthropic) {
      const response = await this.anthropic.messages.create({
        model: this.config.model,
        max_tokens: maxTokens,
        temperature,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
      });

      const content = response.content[0];
      if (content.type === 'text') {
        return this.parseResponse(content.text);
      }
      return null;
    } else if (this.config.provider === 'openai' && this.openai) {
      const response = await this.openai.chat.completions.create({
        model: this.config.model,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
        temperature,
        max_tokens: maxTokens,
      });

      const content = response.choices[0]?.message?.content;
      if (content) {
        return this.parseResponse(content);
      }
      return null;
    }

    throw new Error(`Unsupported LLM provider: ${this.config.provider}`);
  }

  private parseResponse(text: string): any {
    // Try to parse as JSON if it looks like JSON
    const jsonMatch = text.match(/```json\n([\s\S]*?)\n```/) || text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      try {
        return JSON.parse(jsonMatch[1] || jsonMatch[0]);
      } catch {
        // If parsing fails, return raw text
      }
    }
    return text;
  }

  async generateStructured<T>(prompt: string, _schema?: any): Promise<T> {
    const response = await this.generate(prompt);
    
    // If response is already an object, return it
    if (typeof response === 'object' && response !== null) {
      return response as T;
    }
    
    // Otherwise try to parse as JSON
    try {
      return JSON.parse(response) as T;
    } catch {
      throw new Error('Failed to parse structured response');
    }
  }
}

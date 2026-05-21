import 'dotenv/config';
import { IntelligenceExplosion } from './core/intelligence-explosion';
import { defaultConfig } from './config';
import { Logger } from './utils/helpers';

const logger = new Logger('main');

async function main() {
  try {
    logger.info('Starting Lyra RSI - Recursive Self-Improvement System');
    logger.info('Configuration:', defaultConfig);

    // Initialize the intelligence explosion orchestrator
    const system = new IntelligenceExplosion(defaultConfig);
    
    logger.info('Initializing system...');
    await system.initialize();
    
    logger.info('System initialized successfully');
    logger.info('Starting intelligence explosion...');

    // Run generations
    const maxGenerations = 5;
    for (let i = 0; i < maxGenerations; i++) {
      logger.info(`\n=== Generation ${i + 1}/${maxGenerations} ===`);
      
      await system.runGeneration();
      
      const status = system.getStatus();
      logger.info('Status:', status);
      
      // Check if we should stop
      if (status.phase === 'complete') {
        logger.info('Intelligence explosion complete!');
        break;
      }
      
      if (status.phase === 'safety-halt') {
        logger.info('Safety halt triggered. Stopping.');
        break;
      }
    }

    logger.info('\n=== Final Metrics ===');
    const finalMetrics = system.getMetrics();
    logger.info('Final Performance:', finalMetrics);

    logger.info('\nLyra RSI completed successfully');
  } catch (error) {
    logger.info('Error:', error);
    process.exit(1);
  }
}

// Run if this is the main module
if (require.main === module) {
  main();
}

export { main };

import {
  generateId,
  sleep,
  cosineSimilarity,
  calculateMean,
  calculateStdDev,
  formatDuration,
  formatBytes,
  Logger,
} from '../utils/helpers';

describe('Helpers', () => {
  describe('generateId', () => {
    it('should generate unique IDs', () => {
      const id1 = generateId();
      const id2 = generateId();
      expect(id1).not.toBe(id2);
      expect(typeof id1).toBe('string');
    });
  });

  describe('sleep', () => {
    it('should sleep for specified duration', async () => {
      const start = Date.now();
      await sleep(100);
      const duration = Date.now() - start;
      expect(duration).toBeGreaterThanOrEqual(90);
    });
  });

  describe('cosineSimilarity', () => {
    it('should calculate cosine similarity correctly', () => {
      const a = [1, 2, 3];
      const b = [4, 5, 6];
      const similarity = cosineSimilarity(a, b);
      expect(similarity).toBeGreaterThan(0);
      expect(similarity).toBeLessThanOrEqual(1);
    });

    it('should return 1 for identical vectors', () => {
      const a = [1, 2, 3];
      const similarity = cosineSimilarity(a, a);
      expect(similarity).toBeCloseTo(1);
    });

    it('should throw error for different length vectors', () => {
      const a = [1, 2, 3];
      const b = [4, 5];
      expect(() => cosineSimilarity(a, b)).toThrow();
    });
  });

  describe('calculateMean', () => {
    it('should calculate mean correctly', () => {
      expect(calculateMean([1, 2, 3, 4, 5])).toBe(3);
      expect(calculateMean([10, 20, 30])).toBe(20);
    });

    it('should return 0 for empty array', () => {
      expect(calculateMean([])).toBe(0);
    });
  });

  describe('calculateStdDev', () => {
    it('should calculate standard deviation correctly', () => {
      const stdDev = calculateStdDev([2, 4, 4, 4, 5, 5, 7, 9]);
      expect(stdDev).toBeGreaterThan(0);
    });

    it('should return 0 for empty array', () => {
      expect(calculateStdDev([])).toBe(0);
    });
  });

  describe('formatDuration', () => {
    it('should format milliseconds correctly', () => {
      expect(formatDuration(500)).toBe('500ms');
    });

    it('should format seconds correctly', () => {
      expect(formatDuration(5000)).toBe('5.00s');
    });

    it('should format minutes correctly', () => {
      expect(formatDuration(120000)).toBe('2.00m');
    });

    it('should format hours correctly', () => {
      expect(formatDuration(7200000)).toBe('2.00h');
    });
  });

  describe('formatBytes', () => {
    it('should format bytes correctly', () => {
      expect(formatBytes(500)).toBe('500B');
    });

    it('should format kilobytes correctly', () => {
      expect(formatBytes(5000)).toBe('4.88KB');
    });

    it('should format megabytes correctly', () => {
      expect(formatBytes(5000000)).toBe('4.77MB');
    });

    it('should format gigabytes correctly', () => {
      expect(formatBytes(5000000000)).toBe('4.66GB');
    });
  });

  describe('Logger', () => {
    let logger: Logger;
    let consoleSpy: jest.SpyInstance;

    beforeEach(() => {
      logger = new Logger('test');
      consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    });

    afterEach(() => {
      consoleSpy.mockRestore();
    });

    it('should log info messages', () => {
      logger.info('test message');
      expect(consoleSpy).toHaveBeenCalledWith('[test] test message');
    });

    it('should log with additional arguments', () => {
      logger.info('test', { data: 'value' });
      expect(consoleSpy).toHaveBeenCalledWith('[test] test', { data: 'value' });
    });
  });
});

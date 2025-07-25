// e2e/performance-tests.spec.js
const { test, expect } = require('@playwright/test');
const { APIHelpers } = require('../fixtures/api-helpers');
const { testScenarios } = require('../fixtures/test-data');

test.describe('Performance Tests', () => {
  let apiHelpers;

  test.beforeEach(async ({ request }) => {
    apiHelpers = new APIHelpers(request);
  });

  test.describe('Response Time Tests', () => {
    test('API endpoints should respond within acceptable time limits', async () => {
      const endpoints = [
        { method: 'GET', path: '/api/predictions', maxTime: 3000 },
        { method: 'GET', path: '/api/team-stats/Kansas%20City%20Chiefs', maxTime: 2000 },
        { method: 'POST', path: '/api/sports-data', body: { sport: 'NFL' }, maxTime: 10000 }
      ];

      for (const endpoint of endpoints) {
        const metrics = await apiHelpers.measurePerformance(async () => {
          if (endpoint.method === 'GET') {
            return await apiHelpers.get(endpoint.path);
          } else {
            return await apiHelpers.post(endpoint.path, endpoint.body || {});
          }
        });

        console.log(`${endpoint.method} ${endpoint.path}: ${metrics.duration}ms`);
        
        expect(metrics.success).toBe(true);
        expect(metrics.duration).toBeLessThan(endpoint.maxTime);
      }
    });

    test('Health check endpoint should be fast', async () => {
      const iterations = 10;
      const times = [];

      for (let i = 0; i < iterations; i++) {
        const startTime = Date.now();
        const health = await apiHelpers.healthCheck();
        const endTime = Date.now();
        
        expect(health.isHealthy).toBe(true);
        times.push(endTime - startTime);
      }

      const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
      const maxTime = Math.max(...times);
      
      console.log(`Health check - Average: ${avgTime}ms, Max: ${maxTime}ms`);
      
      expect(avgTime).toBeLessThan(500); // Average under 500ms
      expect(maxTime).toBeLessThan(1000); // Max under 1s
    });
  });

  test.describe('Load Testing', () => {
    test('should handle concurrent prediction requests', async () => {
      const concurrentRequests = 10;
      const gameData = apiHelpers.generateGameData('NFL');
      
      const promises = Array(concurrentRequests).fill().map(async (_, index) => {
        const uniqueGameData = {
          ...gameData,
          id: `${gameData.id}_${index}`,
          home_team: `${gameData.home_team} ${index}`
        };
        
        return apiHelpers.measurePerformance(async () => {
          return await apiHelpers.post('/api/game-predictor', uniqueGameData);
        });
      });

      const results = await Promise.all(promises);
      
      // Analyze results
      const successCount = results.filter(r => r.success).length;
      const avgResponseTime = results
        .filter(r => r.success)
        .reduce((sum, r) => sum + r.duration, 0) / successCount;
      
      console.log(`Concurrent requests: ${successCount}/${concurrentRequests} successful`);
      console.log(`Average response time: ${avgResponseTime}ms`);
      
      // At least 80% should succeed
      expect(successCount / concurrentRequests).toBeGreaterThanOrEqual(0.8);
      
      // Average response time should be reasonable
      expect(avgResponseTime).toBeLessThan(5000);
    });

    test('should handle burst traffic for predictions endpoint', async () => {
      const burstSize = 25;
      const burstInterval = 100; // ms between requests
      
      const results = [];
      
      for (let i = 0; i < burstSize; i++) {
        const startTime = Date.now();
        
        try {
          const response = await apiHelpers.get('/api/predictions', { limit: 5 });
          const endTime = Date.now();
          
          results.push({
            success: true,
            responseTime: endTime - startTime,
            status: response.status()
          });
        } catch (error) {
          results.push({
            success: false,
            error: error.message
          });
        }
        
        // Wait before next request
        if (i < burstSize - 1) {
          await apiHelpers.sleep(burstInterval);
        }
      }
      
      const successRate = results.filter(r => r.success).length / results.length;
      const avgResponseTime = results
        .filter(r => r.success)
        .reduce((sum, r) => sum + r.responseTime, 0) / results.filter(r => r.success).length;
      
      console.log(`Burst test - Success rate: ${(successRate * 100).toFixed(1)}%`);
      console.log(`Average response time: ${avgResponseTime.toFixed(0)}ms`);
      
      expect(successRate).toBeGreaterThanOrEqual(0.9); // 90% success rate
      expect(avgResponseTime).toBeLessThan(3000); // Under 3 seconds average
    });
  });

  test.describe('Memory and Resource Tests', () => {
    test('should not have memory leaks during extended use', async () => {
      const iterations = 50;
      const initialMemory = process.memoryUsage();
      
      for (let i = 0; i < iterations; i++) {
        await apiHelpers.get('/api/predictions', { limit: 1 });
        
        // Occasional garbage collection hint
        if (i % 10 === 0 && global.gc) {
          global.gc();
        }
      }
      
      const finalMemory = process.memoryUsage();
      const memoryIncrease = finalMemory.heapUsed - initialMemory.heapUsed;
      
      console.log(`Memory increase after ${iterations} requests: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB`);
      
      // Memory increase should be reasonable (less than 50MB)
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
    });

    test('should handle large response payloads efficiently', async () => {
      const response = await apiHelpers.get('/api/predictions', { 
        limit: 100 // Request large dataset
      });
      
      if (response.status() === 200) {
        const startTime = Date.now();
        const data = await response.json();
        const parseTime = Date.now() - startTime;
        
        console.log(`Parsed ${data.data.predictions.length} predictions in ${parseTime}ms`);
        
        // Should parse large responses quickly
        expect(parseTime).toBeLessThan(1000);
        
        // Validate data structure is maintained
        expect(Array.isArray(data.data.predictions)).toBe(true);
      }
    });
  });

  test.describe('Stress Testing', () => {
    test('should maintain performance under sustained load', async () => {
      const duration = 30000; // 30 seconds
      const requestInterval = 500; // Request every 500ms
      const startTime = Date.now();
      const results = [];
      
      while (Date.now() - startTime < duration) {
        const requestStart = Date.now();
        
        try {
          const response = await apiHelpers.get('/api/predictions', { limit: 5 });
          const requestEnd = Date.now();
          
          results.push({
            timestamp: requestEnd,
            responseTime: requestEnd - requestStart,
            status: response.status(),
            success: true
          });
        } catch (error) {
          results.push({
            timestamp: Date.now(),
            success: false,
            error: error.message
          });
        }
        
        await apiHelpers.sleep(requestInterval);
      }
      
      // Analyze sustained load performance
      const successfulRequests = results.filter(r => r.success);
      const successRate = successfulRequests.length / results.length;
      const avgResponseTime = successfulRequests
        .reduce((sum, r) => sum + r.responseTime, 0) / successfulRequests.length;
      
      // Check for performance degradation over time
      const firstHalf = successfulRequests.slice(0, Math.floor(successfulRequests.length / 2));
      const secondHalf = successfulRequests.slice(Math.floor(successfulRequests.length / 2));
      
      const firstHalfAvg = firstHalf.reduce((sum, r) => sum + r.responseTime, 0) / firstHalf.length;
      const secondHalfAvg = secondHalf.reduce((sum, r) => sum + r.responseTime, 0) / secondHalf.length;
      
      console.log(`Sustained load test results:`);
      console.log(`- Total requests: ${results.length}`);
      console.log(`- Success rate: ${(successRate * 100).toFixed(1)}%`);
      console.log(`- Average response time: ${avgResponseTime.toFixed(0)}ms`);
      console.log(`- First half avg: ${firstHalfAvg.toFixed(0)}ms`);
      console.log(`- Second half avg: ${secondHalfAvg.toFixed(0)}ms`);
      
      expect(successRate).toBeGreaterThanOrEqual(0.85); // 85% success rate
      expect(avgResponseTime).toBeLessThan(5000); // Under 5 seconds average
      
      // Performance shouldn't degrade significantly over time
      const degradationRatio = secondHalfAvg / firstHalfAvg;
      expect(degradationRatio).toBeLessThan(2.0); // Less than 2x slower
    });
  });

  test.describe('Throughput Testing', () => {
    test('should measure maximum throughput for read operations', async () => {
      const testDuration = 10000; // 10 seconds
      const maxConcurrency = 15;
      const startTime = Date.now();
      let completedRequests = 0;
      const errors = [];
      
      // Create worker function
      const worker = async (workerId) => {
        while (Date.now() - startTime < testDuration) {
          try {
            await apiHelpers.get('/api/predictions', { limit: 1 });
            completedRequests++;
          } catch (error) {
            errors.push({ workerId, error: error.message, timestamp: Date.now() });
          }
        }
      };
      
      // Start concurrent workers
      const workers = Array(maxConcurrency).fill().map((_, i) => worker(i));
      await Promise.all(workers);
      
      const actualDuration = Date.now() - startTime;
      const throughput = (completedRequests / actualDuration) * 1000; // requests per second
      const errorRate = errors.length / (completedRequests + errors.length);
      
      console.log(`Throughput test results:`);
      console.log(`- Duration: ${actualDuration}ms`);
      console.log(`- Completed requests: ${completedRequests}`);
      console.log(`- Throughput: ${throughput.toFixed(2)} req/sec`);
      console.log(`- Error rate: ${(errorRate * 100).toFixed(2)}%`);
      console.log(`- Errors: ${errors.length}`);
      
      // Validate throughput metrics
      expect(throughput).toBeGreaterThan(5); // At least 5 req/sec
      expect(errorRate).toBeLessThan(0.1); // Less than 10% error rate
    });
  });
});

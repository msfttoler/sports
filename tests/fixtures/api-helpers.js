// fixtures/api-helpers.js
/**
 * API testing helper functions for Sports Prediction System
 */

class APIHelpers {
  constructor(request) {
    this.request = request;
    this.baseURL = process.env.FUNCTION_APP_URL || 'http://localhost:7071';
  }

  /**
   * Make authenticated API request
   */
  async makeRequest(method, endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...options.headers
      },
      ...options
    };

    if (options.body && typeof options.body === 'object') {
      config.data = options.body;
    }

    return await this.request.fetch(url, config);
  }

  /**
   * GET request helper
   */
  async get(endpoint, params = {}, headers = {}) {
    const queryString = Object.keys(params).length 
      ? '?' + new URLSearchParams(params).toString()
      : '';
    
    return await this.makeRequest('GET', `${endpoint}${queryString}`, { headers });
  }

  /**
   * POST request helper
   */
  async post(endpoint, body = {}, headers = {}) {
    return await this.makeRequest('POST', endpoint, { body, headers });
  }

  /**
   * PUT request helper
   */
  async put(endpoint, body = {}, headers = {}) {
    return await this.makeRequest('PUT', endpoint, { body, headers });
  }

  /**
   * DELETE request helper
   */
  async delete(endpoint, headers = {}) {
    return await this.makeRequest('DELETE', endpoint, { headers });
  }

  /**
   * Validate response structure
   */
  validateResponse(response, expectedStatus, requiredFields = []) {
    // Check status code
    if (response.status() !== expectedStatus) {
      throw new Error(`Expected status ${expectedStatus}, got ${response.status()}`);
    }

    // Check content type
    const contentType = response.headers()['content-type'];
    if (!contentType || !contentType.includes('application/json')) {
      throw new Error(`Expected JSON response, got ${contentType}`);
    }

    return true;
  }

  /**
   * Validate JSON response data
   */
  async validateJSONResponse(response, requiredFields = []) {
    let data;
    try {
      data = await response.json();
    } catch (error) {
      throw new Error(`Failed to parse JSON response: ${error.message}`);
    }

    // Check required fields
    for (const field of requiredFields) {
      if (!(field in data)) {
        throw new Error(`Missing required field: ${field}`);
      }
    }

    return data;
  }

  /**
   * Wait for async operation to complete
   */
  async waitForOperation(checkFunction, timeout = 30000, interval = 1000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const result = await checkFunction();
      if (result) {
        return result;
      }
      await this.sleep(interval);
    }
    
    throw new Error(`Operation timed out after ${timeout}ms`);
  }

  /**
   * Sleep utility
   */
  async sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Generate test data for load testing
   */
  generateGameData(sport = 'NFL', count = 1) {
    const games = [];
    const teams = {
      NFL: [
        'Kansas City Chiefs', 'Buffalo Bills', 'New England Patriots', 
        'Miami Dolphins', 'Green Bay Packers', 'Chicago Bears'
      ],
      NBA: [
        'Los Angeles Lakers', 'Golden State Warriors', 'Boston Celtics',
        'Miami Heat', 'Chicago Bulls', 'New York Knicks'
      ]
    };

    for (let i = 0; i < count; i++) {
      const teamList = teams[sport] || teams.NFL;
      const homeTeam = teamList[Math.floor(Math.random() * teamList.length)];
      let awayTeam = teamList[Math.floor(Math.random() * teamList.length)];
      
      // Ensure different teams
      while (awayTeam === homeTeam) {
        awayTeam = teamList[Math.floor(Math.random() * teamList.length)];
      }

      games.push({
        id: `test_game_${sport.toLowerCase()}_${Date.now()}_${i}`,
        home_team: homeTeam,
        away_team: awayTeam,
        sport: sport,
        game_date: new Date(Date.now() + (i * 24 * 60 * 60 * 1000)).toISOString(),
        status: 'scheduled',
        home_score: 0,
        away_score: 0
      });
    }

    return count === 1 ? games[0] : games;
  }

  /**
   * Performance metrics collector
   */
  async measurePerformance(requestFunction) {
    const startTime = Date.now();
    const startMemory = process.memoryUsage();
    
    try {
      const result = await requestFunction();
      const endTime = Date.now();
      const endMemory = process.memoryUsage();
      
      return {
        success: true,
        duration: endTime - startTime,
        memoryDelta: {
          rss: endMemory.rss - startMemory.rss,
          heapUsed: endMemory.heapUsed - startMemory.heapUsed,
          heapTotal: endMemory.heapTotal - startMemory.heapTotal
        },
        result
      };
    } catch (error) {
      const endTime = Date.now();
      return {
        success: false,
        duration: endTime - startTime,
        error: error.message,
        result: null
      };
    }
  }

  /**
   * Batch request executor
   */
  async executeBatchRequests(requests, concurrency = 5) {
    const results = [];
    const chunks = this.chunkArray(requests, concurrency);
    
    for (const chunk of chunks) {
      const promises = chunk.map(async (request) => {
        try {
          const response = await this.makeRequest(
            request.method, 
            request.endpoint, 
            request.options
          );
          return { success: true, response, request };
        } catch (error) {
          return { success: false, error: error.message, request };
        }
      });
      
      const chunkResults = await Promise.all(promises);
      results.push(...chunkResults);
    }
    
    return results;
  }

  /**
   * Utility to chunk array
   */
  chunkArray(array, size) {
    const chunks = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  }

  /**
   * Health check utility
   */
  async healthCheck() {
    try {
      const response = await this.get('/api/health');
      return {
        isHealthy: response.status() === 200,
        status: response.status(),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        isHealthy: false,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Data cleanup utility
   */
  async cleanupTestData(testRunId) {
    // Implement cleanup logic for test data
    console.log(`Cleaning up test data for run: ${testRunId}`);
    // This would typically involve calling cleanup endpoints
    // or directly removing test data from the database
  }
}

module.exports = { APIHelpers };

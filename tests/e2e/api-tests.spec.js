// e2e/api-tests.spec.js
const { test, expect } = require('@playwright/test');
const { APIHelpers } = require('../fixtures/api-helpers');
const { 
  testGames, 
  testPredictions, 
  testAPIRequests, 
  expectedResponses 
} = require('../fixtures/test-data');

test.describe('Sports Prediction API Tests', () => {
  let apiHelpers;

  test.beforeEach(async ({ request }) => {
    apiHelpers = new APIHelpers(request);
    
    // Health check before each test
    const health = await apiHelpers.healthCheck();
    expect(health.isHealthy).toBe(true);
  });

  test.describe('Sports Data Ingestion API', () => {
    test('should successfully ingest NFL data', async () => {
      const request = testAPIRequests.sportsDataIngestion.valid;
      const response = await apiHelpers.post(request.endpoint, request.body);
      
      apiHelpers.validateResponse(response, 200);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'data']);
      
      expect(data.status).toBe('success');
      expect(data.data).toHaveProperty('games_processed');
      expect(data.data.games_processed).toBeGreaterThanOrEqual(0);
    });

    test('should handle invalid sport parameter', async () => {
      const request = testAPIRequests.sportsDataIngestion.invalidSport;
      const response = await apiHelpers.post(request.endpoint, request.body);
      
      apiHelpers.validateResponse(response, 400);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'error']);
      
      expect(data.status).toBe('error');
      expect(data.error).toContain('Invalid sport');
    });

    test('should handle invalid date format', async () => {
      const request = testAPIRequests.sportsDataIngestion.invalidDate;
      const response = await apiHelpers.post(request.endpoint, request.body);
      
      apiHelpers.validateResponse(response, 400);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'error']);
      
      expect(data.status).toBe('error');
      expect(data.error).toContain('Invalid date');
    });

    test('should handle empty request body', async () => {
      const response = await apiHelpers.post('/api/sports-data', {});
      
      // Should use defaults for empty body
      expect([200, 400]).toContain(response.status());
    });
  });

  test.describe('Game Prediction API', () => {
    test('should generate prediction for valid game data', async () => {
      const request = testAPIRequests.gamePrediction.valid;
      const response = await apiHelpers.post(request.endpoint, request.body);
      
      apiHelpers.validateResponse(response, 201);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'data']);
      
      expect(data.status).toBe('success');
      expect(data.data).toHaveProperty('prediction');
      
      const prediction = data.data.prediction;
      expect(prediction).toHaveProperty('predicted_outcome');
      expect(prediction).toHaveProperty('confidence_score');
      expect(prediction).toHaveProperty('reasoning');
      
      // Validate confidence score range
      expect(prediction.confidence_score).toBeGreaterThanOrEqual(0);
      expect(prediction.confidence_score).toBeLessThanOrEqual(100);
      
      // Validate outcome values
      expect(['home_win', 'away_win', 'tie']).toContain(prediction.predicted_outcome);
    });

    test('should handle missing required fields', async () => {
      const request = testAPIRequests.gamePrediction.missingRequiredFields;
      const response = await apiHelpers.post(request.endpoint, request.body);
      
      apiHelpers.validateResponse(response, 400);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'error']);
      
      expect(data.status).toBe('error');
      expect(data.error).toContain('missing required field');
    });

    test('should handle malformed game data', async () => {
      const malformedGame = {
        ...testGames.nfl.scheduled,
        game_date: 'invalid-date',
        home_score: 'not-a-number'
      };
      
      const response = await apiHelpers.post('/api/game-predictor', malformedGame);
      
      apiHelpers.validateResponse(response, 400);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'error']);
      
      expect(data.status).toBe('error');
    });
  });

  test.describe('Get Predictions API', () => {
    test('should retrieve predictions with default parameters', async () => {
      const request = testAPIRequests.getPredictions.valid;
      const response = await apiHelpers.get(request.endpoint, request.params);
      
      apiHelpers.validateResponse(response, 200);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'data']);
      
      expect(data.status).toBe('success');
      expect(data.data).toHaveProperty('predictions');
      expect(Array.isArray(data.data.predictions)).toBe(true);
      
      // Validate pagination metadata
      expect(data.data).toHaveProperty('total');
      expect(data.data).toHaveProperty('limit');
      expect(data.data).toHaveProperty('offset');
    });

    test('should filter predictions by confidence score', async () => {
      const request = testAPIRequests.getPredictions.withFilters;
      const response = await apiHelpers.get(request.endpoint, request.params);
      
      apiHelpers.validateResponse(response, 200);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'data']);
      
      // All returned predictions should meet confidence criteria
      data.data.predictions.forEach(prediction => {
        expect(prediction.confidence_score).toBeGreaterThanOrEqual(70);
      });
    });

    test('should handle invalid query parameters', async () => {
      const request = testAPIRequests.getPredictions.invalidParams;
      const response = await apiHelpers.get(request.endpoint, request.params);
      
      apiHelpers.validateResponse(response, 400);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'error']);
      
      expect(data.status).toBe('error');
    });

    test('should return empty results for future dates with no predictions', async () => {
      const futureDate = new Date();
      futureDate.setFullYear(futureDate.getFullYear() + 1);
      
      const response = await apiHelpers.get('/api/predictions', {
        date: futureDate.toISOString().split('T')[0]
      });
      
      apiHelpers.validateResponse(response, 200);
      const data = await apiHelpers.validateJSONResponse(response);
      
      expect(data.data.predictions).toHaveLength(0);
    });
  });

  test.describe('Team Statistics API', () => {
    test('should retrieve stats for existing team', async () => {
      const request = testAPIRequests.teamStats.valid;
      const response = await apiHelpers.get(request.endpoint);
      
      // Handle both success and not found gracefully
      if (response.status() === 200) {
        const data = await apiHelpers.validateJSONResponse(response, ['status', 'data']);
        
        expect(data.status).toBe('success');
        expect(data.data).toHaveProperty('team_stats');
        
        const stats = data.data.team_stats;
        expect(stats).toHaveProperty('team_name');
        expect(stats).toHaveProperty('win_percentage');
        expect(stats).toHaveProperty('games_played');
        
        // Validate statistical values
        expect(stats.win_percentage).toBeGreaterThanOrEqual(0);
        expect(stats.win_percentage).toBeLessThanOrEqual(1);
        expect(stats.games_played).toBeGreaterThanOrEqual(0);
      } else {
        expect(response.status()).toBe(404);
      }
    });

    test('should handle non-existent team', async () => {
      const request = testAPIRequests.teamStats.nonExistentTeam;
      const response = await apiHelpers.get(request.endpoint);
      
      apiHelpers.validateResponse(response, 404);
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'error']);
      
      expect(data.status).toBe('error');
      expect(data.error).toContain('not found');
    });

    test('should handle special characters in team name', async () => {
      const response = await apiHelpers.get('/api/team-stats/Team%20With%20Special%20Characters%21');
      
      // Should handle gracefully, either 404 or valid response
      expect([200, 404]).toContain(response.status());
    });
  });

  test.describe('Cross-API Integration Tests', () => {
    test('should create prediction and retrieve it', async ({ request }) => {
      // Step 1: Create a game prediction
      const gameData = apiHelpers.generateGameData('NFL');
      const predictionResponse = await apiHelpers.post('/api/game-predictor', gameData);
      
      if (predictionResponse.status() === 201) {
        const predictionData = await predictionResponse.json();
        const predictionId = predictionData.data.prediction.id;
        
        // Step 2: Retrieve the prediction
        await apiHelpers.sleep(1000); // Allow for async processing
        
        const retrieveResponse = await apiHelpers.get('/api/predictions', {
          game_id: gameData.id
        });
        
        if (retrieveResponse.status() === 200) {
          const retrieveData = await retrieveResponse.json();
          const foundPrediction = retrieveData.data.predictions.find(
            p => p.id === predictionId
          );
          
          expect(foundPrediction).toBeDefined();
          expect(foundPrediction.game_id).toBe(gameData.id);
        }
      }
    });

    test('should ingest data and generate predictions', async () => {
      // Step 1: Ingest sports data
      const ingestionResponse = await apiHelpers.post('/api/sports-data', {
        sport: 'NFL',
        date: new Date().toISOString().split('T')[0]
      });
      
      // Step 2: Check if predictions can be generated
      if (ingestionResponse.status() === 200) {
        await apiHelpers.sleep(2000); // Allow for processing
        
        const predictionsResponse = await apiHelpers.get('/api/predictions', {
          sport: 'NFL',
          limit: 1
        });
        
        expect([200, 404]).toContain(predictionsResponse.status());
      }
    });
  });

  test.describe('Error Handling and Edge Cases', () => {
    test('should handle large request payloads', async () => {
      const largeGameData = {
        ...testGames.nfl.scheduled,
        metadata: 'A'.repeat(10000) // 10KB of data
      };
      
      const response = await apiHelpers.post('/api/game-predictor', largeGameData);
      
      // Should either process successfully or reject with appropriate error
      expect([200, 201, 400, 413]).toContain(response.status());
    });

    test('should handle concurrent requests', async () => {
      const requests = Array(5).fill().map((_, i) => ({
        method: 'GET',
        endpoint: '/api/predictions',
        options: { 
          headers: { 'X-Request-ID': `concurrent-test-${i}` }
        }
      }));
      
      const results = await apiHelpers.executeBatchRequests(requests, 5);
      
      // All requests should complete (successfully or with appropriate errors)
      expect(results).toHaveLength(5);
      results.forEach(result => {
        expect(result).toHaveProperty('success');
        if (result.success) {
          expect([200, 404]).toContain(result.response.status());
        }
      });
    });

    test('should handle malformed JSON', async ({ request }) => {
      const response = await request.post(`${apiHelpers.baseURL}/api/game-predictor`, {
        data: 'invalid-json',
        headers: { 'Content-Type': 'application/json' }
      });
      
      expect(response.status()).toBe(400);
    });

    test('should handle missing content-type header', async ({ request }) => {
      const response = await request.post(`${apiHelpers.baseURL}/api/game-predictor`, {
        data: JSON.stringify(testGames.nfl.scheduled)
        // No Content-Type header
      });
      
      // Should handle gracefully
      expect([200, 201, 400, 415]).toContain(response.status());
    });
  });
});

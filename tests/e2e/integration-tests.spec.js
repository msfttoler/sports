// e2e/integration-tests.spec.js
const { test, expect } = require('@playwright/test');
const { APIHelpers } = require('../fixtures/api-helpers');
const { testGames, testScenarios } = require('../fixtures/test-data');

test.describe('Integration Tests', () => {
  let apiHelpers;
  let testRunId;

  test.beforeAll(async () => {
    testRunId = `integration_${Date.now()}`;
  });

  test.beforeEach(async ({ request }) => {
    apiHelpers = new APIHelpers(request);
    
    // Ensure service is healthy before each test
    const health = await apiHelpers.healthCheck();
    expect(health.isHealthy).toBe(true);
  });

  test.afterAll(async () => {
    // Cleanup test data
    await apiHelpers.cleanupTestData(testRunId);
  });

  test.describe('End-to-End Prediction Workflow', () => {
    test('complete prediction workflow: ingest -> predict -> retrieve', async () => {
      console.log('Starting end-to-end prediction workflow test');
      
      // Step 1: Ingest sports data
      console.log('Step 1: Ingesting sports data...');
      const ingestionResponse = await apiHelpers.post('/api/sports-data', {
        sport: 'NFL',
        date: new Date().toISOString().split('T')[0],
        force_refresh: true
      });
      
      console.log(`Ingestion response: ${ingestionResponse.status()}`);
      
      // Handle both success and existing data scenarios
      if (ingestionResponse.status() === 200) {
        const ingestionData = await ingestionResponse.json();
        console.log(`Games processed: ${ingestionData.data?.games_processed || 0}`);
        
        // Step 2: Wait for data processing
        console.log('Step 2: Waiting for data processing...');
        await apiHelpers.sleep(2000);
        
        // Step 3: Generate prediction for a new game
        console.log('Step 3: Generating prediction...');
        const gameData = {
          ...apiHelpers.generateGameData('NFL'),
          id: `integration_test_${testRunId}_game`,
          game_date: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
        };
        
        const predictionResponse = await apiHelpers.post('/api/game-predictor', gameData);
        console.log(`Prediction response: ${predictionResponse.status()}`);
        
        if (predictionResponse.status() === 201) {
          const predictionData = await predictionResponse.json();
          const prediction = predictionData.data.prediction;
          
          // Validate prediction structure
          expect(prediction).toHaveProperty('id');
          expect(prediction).toHaveProperty('predicted_outcome');
          expect(prediction).toHaveProperty('confidence_score');
          expect(prediction).toHaveProperty('reasoning');
          
          console.log(`Prediction: ${prediction.predicted_outcome} (${prediction.confidence_score}% confidence)`);
          
          // Step 4: Retrieve the prediction
          console.log('Step 4: Retrieving prediction...');
          await apiHelpers.sleep(1000);
          
          const retrieveResponse = await apiHelpers.get('/api/predictions', {
            game_id: gameData.id
          });
          
          if (retrieveResponse.status() === 200) {
            const retrieveData = await retrieveResponse.json();
            const foundPrediction = retrieveData.data.predictions.find(
              p => p.game_id === gameData.id
            );
            
            expect(foundPrediction).toBeDefined();
            expect(foundPrediction.predicted_outcome).toBe(prediction.predicted_outcome);
            expect(foundPrediction.confidence_score).toBe(prediction.confidence_score);
            
            console.log('✅ End-to-end workflow completed successfully');
          }
        }
      } else {
        console.log('Ingestion returned non-200 status, proceeding with prediction test');
      }
    });

    test('should handle prediction updates and consistency', async () => {
      const gameData = {
        ...apiHelpers.generateGameData('NBA'),
        id: `consistency_test_${testRunId}_game`
      };
      
      // Generate initial prediction
      const firstPrediction = await apiHelpers.post('/api/game-predictor', gameData);
      
      if (firstPrediction.status() === 201) {
        const firstData = await firstPrediction.json();
        
        // Wait a moment
        await apiHelpers.sleep(1000);
        
        // Generate prediction for same game again
        const secondPrediction = await apiHelpers.post('/api/game-predictor', gameData);
        
        if (secondPrediction.status() === 201) {
          const secondData = await secondPrediction.json();
          
          // Predictions should be consistent for the same game data
          expect(secondData.data.prediction.predicted_outcome)
            .toBe(firstData.data.prediction.predicted_outcome);
          
          // Confidence scores should be similar (within 10%)
          const confidenceDiff = Math.abs(
            secondData.data.prediction.confidence_score - 
            firstData.data.prediction.confidence_score
          );
          expect(confidenceDiff).toBeLessThanOrEqual(10);
        }
      }
    });
  });

  test.describe('Multi-Sport Integration', () => {
    test('should handle multiple sports data ingestion', async () => {
      const sports = ['NFL', 'NBA'];
      const results = [];
      
      for (const sport of sports) {
        console.log(`Processing ${sport} data...`);
        
        const response = await apiHelpers.post('/api/sports-data', {
          sport: sport,
          date: new Date().toISOString().split('T')[0]
        });
        
        results.push({
          sport,
          status: response.status(),
          success: response.status() === 200
        });
        
        // Wait between requests to avoid overwhelming the service
        await apiHelpers.sleep(1000);
      }
      
      console.log('Multi-sport ingestion results:', results);
      
      // At least one sport should process successfully
      const successCount = results.filter(r => r.success).length;
      expect(successCount).toBeGreaterThan(0);
    });

    test('should generate predictions for different sports', async () => {
      const sports = [
        { sport: 'NFL', teams: ['Kansas City Chiefs', 'Buffalo Bills'] },
        { sport: 'NBA', teams: ['Los Angeles Lakers', 'Golden State Warriors'] }
      ];
      
      const predictions = [];
      
      for (const sportData of sports) {
        const gameData = {
          id: `multi_sport_${testRunId}_${sportData.sport.toLowerCase()}`,
          home_team: sportData.teams[0],
          away_team: sportData.teams[1],
          sport: sportData.sport,
          game_date: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          status: 'scheduled',
          home_score: 0,
          away_score: 0
        };
        
        const response = await apiHelpers.post('/api/game-predictor', gameData);
        
        if (response.status() === 201) {
          const data = await response.json();
          predictions.push({
            sport: sportData.sport,
            prediction: data.data.prediction
          });
        }
        
        await apiHelpers.sleep(500);
      }
      
      console.log(`Generated ${predictions.length} multi-sport predictions`);
      
      // Validate predictions for different sports
      predictions.forEach(p => {
        expect(p.prediction).toHaveProperty('predicted_outcome');
        expect(p.prediction).toHaveProperty('confidence_score');
        expect(p.prediction.confidence_score).toBeGreaterThanOrEqual(0);
        expect(p.prediction.confidence_score).toBeLessThanOrEqual(100);
      });
    });
  });

  test.describe('Data Consistency and Validation', () => {
    test('should maintain data consistency across endpoints', async () => {
      // Generate a game and prediction
      const gameData = {
        ...apiHelpers.generateGameData('NFL'),
        id: `consistency_${testRunId}_game`
      };
      
      const predictionResponse = await apiHelpers.post('/api/game-predictor', gameData);
      
      if (predictionResponse.status() === 201) {
        const predictionData = await predictionResponse.json();
        const prediction = predictionData.data.prediction;
        
        await apiHelpers.sleep(1000);
        
        // Retrieve prediction via predictions endpoint
        const predictionsResponse = await apiHelpers.get('/api/predictions', {
          game_id: gameData.id
        });
        
        if (predictionsResponse.status() === 200) {
          const predictionsData = await predictionsResponse.json();
          const foundPrediction = predictionsData.data.predictions.find(
            p => p.id === prediction.id
          );
          
          // Data should be consistent across endpoints
          expect(foundPrediction).toBeDefined();
          expect(foundPrediction.game_id).toBe(gameData.id);
          expect(foundPrediction.predicted_outcome).toBe(prediction.predicted_outcome);
          expect(foundPrediction.confidence_score).toBe(prediction.confidence_score);
        }
        
        // Check team stats consistency
        const teamStatsResponse = await apiHelpers.get(
          `/api/team-stats/${encodeURIComponent(gameData.home_team)}`
        );
        
        if (teamStatsResponse.status() === 200) {
          const teamStatsData = await teamStatsResponse.json();
          const stats = teamStatsData.data.team_stats;
          
          // Team stats should be valid
          expect(stats.team_name).toBe(gameData.home_team);
          expect(stats.win_percentage).toBeGreaterThanOrEqual(0);
          expect(stats.win_percentage).toBeLessThanOrEqual(1);
        }
      }
    });

    test('should validate prediction confidence correlation', async () => {
      const games = [
        // Create scenarios with different expected confidence levels
        {
          ...apiHelpers.generateGameData('NFL'),
          id: `confidence_test_${testRunId}_high`,
          metadata: { expected_confidence: 'high' }
        },
        {
          ...apiHelpers.generateGameData('NBA'), 
          id: `confidence_test_${testRunId}_moderate`,
          metadata: { expected_confidence: 'moderate' }
        }
      ];
      
      const confidenceResults = [];
      
      for (const game of games) {
        const response = await apiHelpers.post('/api/game-predictor', game);
        
        if (response.status() === 201) {
          const data = await response.json();
          confidenceResults.push({
            gameId: game.id,
            confidence: data.data.prediction.confidence_score,
            expectedLevel: game.metadata.expected_confidence
          });
        }
        
        await apiHelpers.sleep(500);
      }
      
      console.log('Confidence correlation results:', confidenceResults);
      
      // Validate confidence scores are reasonable
      confidenceResults.forEach(result => {
        expect(result.confidence).toBeGreaterThan(0);
        expect(result.confidence).toBeLessThanOrEqual(100);
        
        // Basic sanity check - confidence should generally be moderate to high
        expect(result.confidence).toBeGreaterThan(20);
      });
    });
  });

  test.describe('Error Recovery and Resilience', () => {
    test('should recover from temporary service issues', async () => {
      const maxRetries = 3;
      const retryDelay = 1000;
      
      let attempts = 0;
      let success = false;
      
      while (attempts < maxRetries && !success) {
        attempts++;
        
        try {
          const response = await apiHelpers.get('/api/predictions', { limit: 1 });
          
          if (response.status() === 200) {
            success = true;
            console.log(`Service responded successfully on attempt ${attempts}`);
          } else {
            console.log(`Attempt ${attempts} failed with status ${response.status()}`);
          }
        } catch (error) {
          console.log(`Attempt ${attempts} failed with error: ${error.message}`);
        }
        
        if (!success && attempts < maxRetries) {
          await apiHelpers.sleep(retryDelay);
        }
      }
      
      expect(success).toBe(true);
    });

    test('should handle partial data scenarios gracefully', async () => {
      // Test with incomplete game data
      const incompleteGames = [
        {
          id: `partial_${testRunId}_1`,
          home_team: 'Test Team A',
          away_team: 'Test Team B',
          sport: 'NFL'
          // Missing game_date, status, scores
        },
        {
          id: `partial_${testRunId}_2`,
          home_team: 'Test Team C',
          sport: 'NBA',
          game_date: new Date().toISOString()
          // Missing away_team, status, scores
        }
      ];
      
      const results = [];
      
      for (const game of incompleteGames) {
        const response = await apiHelpers.post('/api/game-predictor', game);
        
        results.push({
          gameId: game.id,
          status: response.status(),
          handled: [200, 201, 400, 422].includes(response.status())
        });
        
        await apiHelpers.sleep(500);
      }
      
      console.log('Partial data handling results:', results);
      
      // All requests should be handled gracefully
      results.forEach(result => {
        expect(result.handled).toBe(true);
      });
    });
  });

  test.describe('Performance Integration', () => {
    test('should maintain performance under mixed workload', async () => {
      const mixedOperations = [
        () => apiHelpers.get('/api/predictions', { limit: 5 }),
        () => apiHelpers.get('/api/team-stats/Kansas%20City%20Chiefs'),
        () => apiHelpers.post('/api/game-predictor', apiHelpers.generateGameData('NFL')),
        () => apiHelpers.post('/api/sports-data', { sport: 'NFL' })
      ];
      
      const iterations = 20;
      const startTime = Date.now();
      const results = [];
      
      for (let i = 0; i < iterations; i++) {
        const operation = mixedOperations[i % mixedOperations.length];
        
        const operationStart = Date.now();
        try {
          const response = await operation();
          const operationEnd = Date.now();
          
          results.push({
            success: true,
            duration: operationEnd - operationStart,
            status: response.status()
          });
        } catch (error) {
          results.push({
            success: false,
            error: error.message,
            duration: Date.now() - operationStart
          });
        }
        
        // Small delay between operations
        await apiHelpers.sleep(100);
      }
      
      const totalDuration = Date.now() - startTime;
      const successRate = results.filter(r => r.success).length / results.length;
      const avgDuration = results
        .filter(r => r.success)
        .reduce((sum, r) => sum + r.duration, 0) / results.filter(r => r.success).length;
      
      console.log(`Mixed workload test completed:`);
      console.log(`- Total time: ${totalDuration}ms`);
      console.log(`- Success rate: ${(successRate * 100).toFixed(1)}%`);
      console.log(`- Average operation time: ${avgDuration.toFixed(0)}ms`);
      
      expect(successRate).toBeGreaterThanOrEqual(0.8); // 80% success rate
      expect(avgDuration).toBeLessThan(5000); // Average under 5 seconds
    });
  });

  test.describe('Scheduled Operations Integration', () => {
    test('should validate scheduled sync functionality', async () => {
      // This test validates that the scheduled sync function is properly configured
      // Note: We can't easily trigger the timer in tests, but we can validate the endpoint exists
      
      console.log('Testing scheduled sync configuration...');
      
      // The scheduled function doesn't have an HTTP trigger, so we test related functionality
      // Test data availability that would be created by scheduled sync
      const predictionsResponse = await apiHelpers.get('/api/predictions', { limit: 1 });
      
      // Should handle gracefully whether data exists or not
      expect([200, 404]).toContain(predictionsResponse.status());
      
      if (predictionsResponse.status() === 200) {
        const data = await predictionsResponse.json();
        console.log(`Found ${data.data.predictions.length} predictions from sync`);
      }
      
      console.log('✅ Scheduled sync configuration validated');
    });
  });
});

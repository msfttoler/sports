# Testing Documentation - Sports Prediction System

## 🎭 Playwright Testing Framework

This document provides comprehensive information about the Playwright testing framework implemented for the Sports Prediction System.

## 📁 Test Structure

```
tests/
├── e2e/                          # End-to-end test files
│   ├── api-tests.spec.js         # API functionality tests
│   ├── performance-tests.spec.js # Performance and load tests
│   ├── security-tests.spec.js    # Security and vulnerability tests
│   └── integration-tests.spec.js # Integration and workflow tests
├── fixtures/                     # Test data and utilities
│   ├── test-data.js             # Static test data
│   └── api-helpers.js           # API testing utilities
├── playwright.config.js         # Playwright configuration
├── package.json                 # Node.js dependencies
├── global-setup.js             # Global test setup
├── global-teardown.js          # Global test cleanup
└── run-tests.sh                # Test execution script
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- Azure Functions Core Tools
- Python 3.11+
- Sports Prediction System running locally or deployed

### Installation

```bash
# Navigate to tests directory
cd tests

# Install dependencies
npm install

# Install Playwright browsers
npx playwright install

# Make test script executable
chmod +x run-tests.sh
```

### Running Tests

#### Using the Test Runner Script

```bash
# Run all tests against local environment
./run-tests.sh

# Run specific test types
./run-tests.sh --type api
./run-tests.sh --type performance
./run-tests.sh --type security
./run-tests.sh --type integration

# Run tests in headed mode (visible browser)
./run-tests.sh --headed

# Run tests against different environments
./run-tests.sh --environment staging
./run-tests.sh --environment production

# Run with specific browser
./run-tests.sh --browser firefox
./run-tests.sh --browser webkit

# Custom timeout
./run-tests.sh --timeout 60000
```

#### Using Playwright Directly

```bash
# Run all tests
npx playwright test

# Run specific test file
npx playwright test e2e/api-tests.spec.js

# Run tests with UI mode
npx playwright test --ui

# Run tests in debug mode
npx playwright test --debug

# Generate HTML report
npx playwright show-report
```

## 📊 Test Categories

### 1. API Tests (`api-tests.spec.js`)

Tests the core API functionality of all Azure Functions endpoints.

**Coverage:**
- Sports Data Ingestion API
- Game Prediction API  
- Get Predictions API
- Team Statistics API
- Cross-API integration
- Error handling and edge cases

**Key Test Scenarios:**
```javascript
// Example API test
test('should generate prediction for valid game data', async () => {
  const response = await apiHelpers.post('/api/game-predictor', gameData);
  expect(response.status()).toBe(201);
  
  const data = await response.json();
  expect(data.data.prediction.confidence_score).toBeGreaterThanOrEqual(0);
  expect(data.data.prediction.confidence_score).toBeLessThanOrEqual(100);
});
```

### 2. Performance Tests (`performance-tests.spec.js`)

Validates system performance under various load conditions.

**Coverage:**
- Response time validation
- Concurrent request handling
- Memory leak detection
- Sustained load testing
- Throughput measurement

**Key Metrics:**
- API response times < 3000ms
- Health check < 500ms average
- 90%+ success rate under load
- Memory growth < 50MB over 50 requests

**Example Performance Test:**
```javascript
test('should handle concurrent prediction requests', async () => {
  const promises = Array(10).fill().map(() => 
    apiHelpers.post('/api/game-predictor', gameData)
  );
  
  const results = await Promise.all(promises);
  const successRate = results.filter(r => r.success).length / results.length;
  
  expect(successRate).toBeGreaterThanOrEqual(0.8);
});
```

### 3. Security Tests (`security-tests.spec.js`)

Comprehensive security testing to identify vulnerabilities.

**Coverage:**
- Input validation and sanitization
- XSS prevention
- SQL/NoSQL injection prevention
- Authentication and authorization
- Information leakage prevention
- DoS protection
- CORS validation

**Security Test Examples:**
```javascript
test('should prevent XSS attacks', async () => {
  const xssPayload = '<script>alert("xss")</script>';
  const response = await apiHelpers.get('/api/predictions', { team: xssPayload });
  
  if (response.status() === 200) {
    const responseText = JSON.stringify(await response.json());
    expect(responseText).not.toContain('<script>');
  }
});
```

### 4. Integration Tests (`integration-tests.spec.js`)

End-to-end workflow testing and system integration validation.

**Coverage:**
- Complete prediction workflow
- Multi-sport data handling
- Data consistency across endpoints
- Error recovery scenarios
- Mixed workload performance

**Integration Test Example:**
```javascript
test('complete prediction workflow', async () => {
  // 1. Ingest data
  await apiHelpers.post('/api/sports-data', { sport: 'NFL' });
  
  // 2. Generate prediction
  const prediction = await apiHelpers.post('/api/game-predictor', gameData);
  
  // 3. Retrieve prediction
  const retrieved = await apiHelpers.get('/api/predictions', { 
    game_id: gameData.id 
  });
  
  // Validate end-to-end consistency
  expect(retrieved.data.predictions[0].game_id).toBe(gameData.id);
});
```

## 🛠️ Test Utilities

### API Helpers (`fixtures/api-helpers.js`)

Provides reusable utilities for API testing:

```javascript
const apiHelpers = new APIHelpers(request);

// Make requests
await apiHelpers.get('/api/predictions');
await apiHelpers.post('/api/game-predictor', data);

// Validate responses
apiHelpers.validateResponse(response, 200, ['status', 'data']);

// Performance measurement
const metrics = await apiHelpers.measurePerformance(requestFunction);

// Batch operations
const results = await apiHelpers.executeBatchRequests(requests, 5);

// Health checks
const health = await apiHelpers.healthCheck();
```

### Test Data (`fixtures/test-data.js`)

Centralized test data management:

```javascript
// Game data
const nflGame = testGames.nfl.scheduled;
const nbaGame = testGames.nba.completed;

// Prediction data
const highConfidencePrediction = testPredictions.highConfidence;

// API request templates
const validRequest = testAPIRequests.sportsDataIngestion.valid;

// Security payloads
const xssPayloads = testScenarios.security.maliciousPayloads;
```

## 📈 Reporting and Monitoring

### HTML Reports

Playwright generates comprehensive HTML reports with:
- Test execution timeline
- Screenshots of failures
- Video recordings
- Network logs
- Performance metrics

Access via: `npx playwright show-report`

### CI/CD Integration

GitHub Actions workflow (`.github/workflows/playwright-tests.yml`) provides:
- Multi-browser testing (Chromium, Firefox, WebKit)
- Environment-specific testing
- Scheduled monitoring runs
- Performance regression detection
- Security vulnerability scanning
- Automated PR comments with results

### Test Metrics

Key metrics tracked:
- **Pass Rate**: Percentage of tests passing
- **Response Times**: API endpoint performance
- **Error Rates**: Failure patterns and trends
- **Coverage**: API endpoint and scenario coverage
- **Security Score**: Vulnerability assessment results

## 🔧 Configuration

### Environment Variables

```bash
# Function App URL (auto-detected for local)
FUNCTION_APP_URL=https://your-function-app.azurewebsites.net

# Test environment
TEST_ENVIRONMENT=local|staging|production

# Browser selection
BROWSER=chromium|firefox|webkit

# Timeout settings
PLAYWRIGHT_TIMEOUT=30000
```

### Playwright Configuration (`playwright.config.js`)

```javascript
module.exports = defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  use: {
    baseURL: process.env.FUNCTION_APP_URL || 'http://localhost:7071',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
```

## 🚦 Test Execution Strategies

### Local Development

```bash
# Quick API validation
./run-tests.sh --type api --browser chromium

# Debug specific test
npx playwright test --debug e2e/api-tests.spec.js

# UI mode for interactive testing
npx playwright test --ui
```

### Continuous Integration

```bash
# Full test suite
npx playwright test --workers=2

# Specific environment
FUNCTION_APP_URL=https://staging.example.com npx playwright test

# Security-focused run
npx playwright test e2e/security-tests.spec.js
```

### Production Monitoring

```bash
# Scheduled health monitoring
./run-tests.sh --type api --environment production --timeout 10000

# Performance baseline testing
./run-tests.sh --type performance --environment production
```

## 📋 Best Practices

### Test Writing Guidelines

1. **Test Isolation**: Each test should be independent
2. **Clear Naming**: Descriptive test names and descriptions
3. **Data Management**: Use fixtures and cleanup after tests
4. **Error Handling**: Graceful handling of various response scenarios
5. **Performance Awareness**: Include timing assertions for critical paths

### Example Best Practice Test:

```javascript
test.describe('Team Statistics API', () => {
  test('should retrieve valid team statistics', async ({ request }) => {
    // Arrange
    const apiHelpers = new APIHelpers(request);
    const teamName = 'Kansas City Chiefs';
    
    // Act
    const response = await apiHelpers.get(`/api/team-stats/${encodeURIComponent(teamName)}`);
    
    // Assert
    if (response.status() === 200) {
      const data = await apiHelpers.validateJSONResponse(response, ['status', 'data']);
      const stats = data.data.team_stats;
      
      expect(stats.team_name).toBe(teamName);
      expect(stats.win_percentage).toBeGreaterThanOrEqual(0);
      expect(stats.win_percentage).toBeLessThanOrEqual(1);
      expect(stats.games_played).toBeGreaterThanOrEqual(0);
    } else {
      // Handle gracefully when team doesn't exist
      expect(response.status()).toBe(404);
    }
  });
});
```

### Debugging Tips

1. **Use headed mode**: `--headed` for visual debugging
2. **Screenshots**: Automatic on failure, manual with `await page.screenshot()`
3. **Debug mode**: `--debug` for step-by-step execution
4. **Console logs**: `console.log()` statements in tests
5. **Network inspection**: Use browser dev tools in headed mode

### Performance Optimization

1. **Parallel execution**: Use `fullyParallel: true`
2. **Selective testing**: Run only necessary test suites
3. **Resource cleanup**: Proper teardown to prevent resource leaks
4. **Timeout management**: Appropriate timeouts for different operations
5. **Test data management**: Efficient test data generation and cleanup

## 🔍 Troubleshooting

### Common Issues

**Service Not Starting**
```bash
# Check if service is running
curl http://localhost:7071/api/health

# Start Azure Functions
func start
```

**Browser Installation Issues**
```bash
# Reinstall browsers
npx playwright install --with-deps

# Check browser status
npx playwright install --dry-run
```

**Test Timeouts**
```bash
# Increase timeout
./run-tests.sh --timeout 60000

# Or set in environment
export PLAYWRIGHT_TIMEOUT=60000
```

**Network Issues**
```bash
# Check connectivity
ping your-function-app.azurewebsites.net

# Verify SSL certificates
curl -I https://your-function-app.azurewebsites.net
```

### Debug Mode Usage

```bash
# Run single test in debug mode
npx playwright test --debug e2e/api-tests.spec.js -g "should generate prediction"

# Debug with browser console
npx playwright test --headed --debug
```

## 📊 Metrics and KPIs

### Test Quality Metrics

- **Test Coverage**: >95% API endpoint coverage
- **Pass Rate**: >98% in stable environments  
- **Execution Time**: <5 minutes for full suite
- **Flakiness**: <2% flaky test rate

### Performance Benchmarks

- **API Response Time**: <3000ms (95th percentile)
- **Health Check**: <500ms average
- **Concurrent Users**: 25+ simultaneous requests
- **Throughput**: >10 requests/second

### Security Standards

- **Vulnerability Detection**: 0 high/critical findings
- **Input Validation**: 100% malicious payload rejection
- **Authentication**: Proper auth error handling
- **Data Exposure**: No sensitive information leakage

## 🔄 Maintenance

### Regular Tasks

1. **Update Dependencies**: Monthly update of Playwright and test dependencies
2. **Browser Updates**: Automatic browser updates with Playwright releases
3. **Test Data Refresh**: Quarterly update of test datasets
4. **Performance Baselines**: Monthly review and update of performance thresholds
5. **Security Patterns**: Quarterly review of security test patterns

### Monitoring Setup

1. **Scheduled Runs**: Daily automated test execution
2. **Performance Alerts**: Automatic alerts for performance degradation
3. **Failure Notifications**: Immediate notifications for test failures
4. **Trend Analysis**: Weekly analysis of test metrics and trends

This comprehensive testing framework ensures the Sports Prediction System maintains high quality, performance, and security standards through automated validation and continuous monitoring.

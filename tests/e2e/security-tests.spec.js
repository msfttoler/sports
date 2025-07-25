// e2e/security-tests.spec.js
const { test, expect } = require('@playwright/test');
const { APIHelpers } = require('../fixtures/api-helpers');
const { testScenarios, testGames } = require('../fixtures/test-data');

test.describe('Security Tests', () => {
  let apiHelpers;

  test.beforeEach(async ({ request }) => {
    apiHelpers = new APIHelpers(request);
  });

  test.describe('Input Validation and Sanitization', () => {
    test('should prevent XSS attacks in request parameters', async () => {
      const xssPayloads = [
        '<script>alert("xss")</script>',
        'javascript:alert("xss")',
        '<img src=x onerror=alert("xss")>',
        '"><script>alert("xss")</script>',
        '<svg onload=alert("xss")>',
        '%3Cscript%3Ealert%28%22xss%22%29%3C%2Fscript%3E'
      ];

      for (const payload of xssPayloads) {
        // Test in query parameters
        const response = await apiHelpers.get('/api/predictions', {
          team: payload,
          sport: payload
        });

        // Should either reject with 400 or sanitize the input
        if (response.status() === 200) {
          const data = await response.json();
          const responseText = JSON.stringify(data);
          
          // Response should not contain raw script tags
          expect(responseText).not.toContain('<script>');
          expect(responseText).not.toContain('javascript:');
          expect(responseText).not.toContain('onerror=');
          expect(responseText).not.toContain('onload=');
        } else {
          expect([400, 422]).toContain(response.status());
        }
      }
    });

    test('should prevent SQL injection in request parameters', async () => {
      const sqlPayloads = [
        "'; DROP TABLE games; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM users --",
        "'; DELETE FROM predictions; --",
        "1' OR '1'='1' --",
        "admin'--",
        "' OR 1=1#"
      ];

      for (const payload of sqlPayloads) {
        const response = await apiHelpers.get('/api/team-stats/' + encodeURIComponent(payload));
        
        // Should handle gracefully without exposing database errors
        if (response.status() !== 404) {
          const data = await response.json();
          const responseText = JSON.stringify(data).toLowerCase();
          
          // Should not contain SQL error messages
          expect(responseText).not.toContain('sql');
          expect(responseText).not.toContain('database');
          expect(responseText).not.toContain('syntax error');
          expect(responseText).not.toContain('mysql');
          expect(responseText).not.toContain('postgresql');
        }
      }
    });

    test('should prevent NoSQL injection attacks', async () => {
      const noSqlPayloads = [
        { $ne: null },
        { $where: "function() { return true; }" },
        { $regex: ".*" },
        { $gt: "" },
        '{"$ne": null}',
        '{"$where": "1==1"}'
      ];

      for (const payload of noSqlPayloads) {
        const response = await apiHelpers.post('/api/game-predictor', {
          ...testGames.nfl.scheduled,
          home_team: payload,
          malicious_field: payload
        });

        // Should reject malformed data
        expect([400, 422]).toContain(response.status());
      }
    });

    test('should handle extremely large payloads', async () => {
      const largeString = 'A'.repeat(1000000); // 1MB string
      const oversizedGame = {
        ...testGames.nfl.scheduled,
        description: largeString,
        metadata: largeString
      };

      const response = await apiHelpers.post('/api/game-predictor', oversizedGame);
      
      // Should reject with appropriate status code
      expect([400, 413, 422]).toContain(response.status());
    });

    test('should prevent prototype pollution', async () => {
      const pollutionPayloads = [
        {
          "__proto__": { "polluted": true },
          ...testGames.nfl.scheduled
        },
        {
          "constructor": { "prototype": { "polluted": true } },
          ...testGames.nfl.scheduled
        }
      ];

      for (const payload of pollutionPayloads) {
        const response = await apiHelpers.post('/api/game-predictor', payload);
        
        // Should handle safely without prototype pollution
        expect([200, 201, 400, 422]).toContain(response.status());
        
        // Check if pollution occurred (this shouldn't happen)
        expect(({}).polluted).toBeUndefined();
      }
    });
  });

  test.describe('Authentication and Authorization', () => {
    test('should handle missing authentication headers gracefully', async () => {
      // Test with no auth headers
      const response = await apiHelpers.get('/api/predictions');
      
      // Should either work (if no auth required) or return proper auth error
      if (response.status() === 401) {
        const data = await response.json();
        expect(data).toHaveProperty('error');
      } else {
        expect(response.status()).toBe(200);
      }
    });

    test('should validate function key authentication', async () => {
      // Test with invalid function key
      const response = await apiHelpers.get('/api/predictions', {}, {
        'x-functions-key': 'invalid-key-12345'
      });
      
      // Should handle gracefully
      expect([200, 401, 403]).toContain(response.status());
    });

    test('should prevent privilege escalation', async () => {
      // Try to access admin-like endpoints that shouldn't exist
      const adminEndpoints = [
        '/api/admin',
        '/api/config',
        '/api/users',
        '/api/keys',
        '/api/secrets',
        '/api/debug'
      ];

      for (const endpoint of adminEndpoints) {
        const response = await apiHelpers.get(endpoint);
        
        // Should return 404 (not found) rather than 403 (forbidden)
        // This prevents endpoint enumeration
        expect(response.status()).toBe(404);
      }
    });
  });

  test.describe('Data Exposure and Information Leakage', () => {
    test('should not expose sensitive information in error messages', async () => {
      // Test various error conditions
      const errorTests = [
        { endpoint: '/api/game-predictor', method: 'POST', body: null },
        { endpoint: '/api/predictions', method: 'GET', params: { invalid: 'value' } },
        { endpoint: '/api/team-stats/nonexistent', method: 'GET' }
      ];

      for (const errorTest of errorTests) {
        let response;
        
        if (errorTest.method === 'GET') {
          response = await apiHelpers.get(errorTest.endpoint, errorTest.params || {});
        } else {
          response = await apiHelpers.post(errorTest.endpoint, errorTest.body);
        }

        if (response.status() >= 400) {
          const responseText = await response.text();
          const lowerText = responseText.toLowerCase();
          
          // Should not expose sensitive information
          expect(lowerText).not.toContain('password');
          expect(lowerText).not.toContain('connection string');
          expect(lowerText).not.toContain('api key');
          expect(lowerText).not.toContain('secret');
          expect(lowerText).not.toContain('token');
          expect(lowerText).not.toContain('cosmosdb');
          expect(lowerText).not.toContain('localhost');
          expect(lowerText).not.toContain('127.0.0.1');
          expect(lowerText).not.toContain('stack trace');
          expect(lowerText).not.toContain('file path');
        }
      }
    });

    test('should not expose internal server information', async () => {
      const response = await apiHelpers.get('/api/predictions');
      const headers = response.headers();
      
      // Should not expose server information
      expect(headers['server']).toBeUndefined();
      expect(headers['x-powered-by']).toBeUndefined();
      expect(headers['x-aspnet-version']).toBeUndefined();
      
      // Should have security headers
      expect(headers['x-content-type-options']).toBe('nosniff');
    });

    test('should handle directory traversal attempts', async () => {
      const traversalPayloads = [
        '../../../etc/passwd',
        '..\\..\\..\\windows\\system32\\drivers\\etc\\hosts',
        '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
        '....//....//....//etc/passwd',
        '..%c0%af..%c0%af..%c0%afetc%c0%afpasswd'
      ];

      for (const payload of traversalPayloads) {
        const response = await apiHelpers.get(`/api/team-stats/${encodeURIComponent(payload)}`);
        
        // Should return 404 or 400, not expose file contents
        expect([400, 404]).toContain(response.status());
        
        if (response.status() === 200) {
          const data = await response.json();
          const responseText = JSON.stringify(data);
          
          // Should not contain file system content
          expect(responseText).not.toContain('root:');
          expect(responseText).not.toContain('127.0.0.1');
          expect(responseText).not.toContain('localhost');
        }
      }
    });
  });

  test.describe('Rate Limiting and DoS Protection', () => {
    test('should handle rapid successive requests', async () => {
      const rapidRequests = 20;
      const promises = [];
      
      // Send rapid requests
      for (let i = 0; i < rapidRequests; i++) {
        promises.push(apiHelpers.get('/api/predictions', { limit: 1 }));
      }
      
      const responses = await Promise.all(promises.map(p => 
        p.catch(error => ({ error: error.message }))
      ));
      
      // Count successful responses
      const successfulResponses = responses.filter(r => !r.error && r.status() === 200);
      const rateLimitedResponses = responses.filter(r => !r.error && r.status() === 429);
      
      console.log(`Rapid requests: ${successfulResponses.length} successful, ${rateLimitedResponses.length} rate limited`);
      
      // Should either handle all requests or implement rate limiting
      if (rateLimitedResponses.length > 0) {
        expect(rateLimitedResponses.length).toBeGreaterThan(0);
      } else {
        expect(successfulResponses.length).toBeGreaterThan(rapidRequests * 0.8);
      }
    });

    test('should prevent resource exhaustion attacks', async () => {
      // Test resource-intensive operations
      const resourceTests = [
        { endpoint: '/api/predictions', params: { limit: 1000 } },
        { endpoint: '/api/predictions', params: { date: '1900-01-01' } }
      ];

      for (const test of resourceTests) {
        const startTime = Date.now();
        const response = await apiHelpers.get(test.endpoint, test.params);
        const duration = Date.now() - startTime;
        
        // Should complete within reasonable time or reject
        if (response.status() === 200) {
          expect(duration).toBeLessThan(30000); // 30 seconds max
        } else {
          expect([400, 422, 429]).toContain(response.status());
        }
      }
    });
  });

  test.describe('Content Security and Headers', () => {
    test('should have appropriate security headers', async () => {
      const response = await apiHelpers.get('/api/predictions');
      const headers = response.headers();
      
      // Check for security headers
      expect(headers['x-content-type-options']).toBeDefined();
      expect(headers['x-frame-options'] || headers['x-frame-options']).toBeDefined();
      
      // Content type should be properly set
      if (response.status() === 200) {
        expect(headers['content-type']).toContain('application/json');
      }
    });

    test('should prevent MIME type sniffing', async () => {
      const response = await apiHelpers.get('/api/predictions');
      const headers = response.headers();
      
      expect(headers['x-content-type-options']).toBe('nosniff');
    });

    test('should handle CORS properly', async ({ request }) => {
      const response = await request.fetch(`${apiHelpers.baseURL}/api/predictions`, {
        method: 'OPTIONS',
        headers: {
          'Origin': 'https://malicious-site.com',
          'Access-Control-Request-Method': 'GET'
        }
      });

      // Should handle CORS appropriately
      const corsHeader = response.headers()['access-control-allow-origin'];
      if (corsHeader) {
        // If CORS is enabled, it should be properly configured
        expect(corsHeader).not.toBe('*'); // Avoid wildcard for sensitive APIs
      }
    });
  });

  test.describe('Injection Attack Prevention', () => {
    test('should prevent command injection', async () => {
      const commandPayloads = [
        '; ls -la',
        '| whoami',
        '&& cat /etc/passwd',
        '`id`',
        '$(uname -a)',
        '; rm -rf /',
        '| nc -l -p 4444'
      ];

      for (const payload of commandPayloads) {
        const response = await apiHelpers.get('/api/team-stats/' + encodeURIComponent(payload));
        
        // Should not execute commands
        expect([400, 404, 422]).toContain(response.status());
        
        if (response.status() === 200) {
          const data = await response.json();
          const responseText = JSON.stringify(data);
          
          // Should not contain command output
          expect(responseText).not.toContain('root');
          expect(responseText).not.toContain('bin');
          expect(responseText).not.toContain('usr');
          expect(responseText).not.toContain('Linux');
          expect(responseText).not.toContain('uid=');
        }
      }
    });

    test('should prevent LDAP injection', async () => {
      const ldapPayloads = [
        '*)(&',
        '*)(uid=*',
        '*)((|(*',
        '*()|%26',
        '*)(|(mail=*))',
        '*)(&(objectClass=*)'
      ];

      for (const payload of ldapPayloads) {
        const response = await apiHelpers.get('/api/team-stats/' + encodeURIComponent(payload));
        
        // Should handle safely
        expect([400, 404, 422]).toContain(response.status());
      }
    });
  });
});

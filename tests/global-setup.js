// global-setup.js
const { chromium, firefox, webkit } = require('@playwright/test');

async function globalSetup() {
  console.log('🚀 Starting Playwright Global Setup');
  
  // Environment setup
  const baseURL = process.env.FUNCTION_APP_URL || 'http://localhost:7071';
  console.log(`Base URL: ${baseURL}`);
  
  // Health check to ensure the service is running
  try {
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    
    // Wait for the service to be ready
    let retries = 0;
    const maxRetries = 30;
    
    while (retries < maxRetries) {
      try {
        const response = await page.request.get(`${baseURL}/api/health`);
        if (response.ok()) {
          console.log('✅ Service is ready');
          break;
        }
      } catch (error) {
        console.log(`⏳ Waiting for service... (${retries + 1}/${maxRetries})`);
        await page.waitForTimeout(2000);
        retries++;
      }
    }
    
    if (retries >= maxRetries) {
      throw new Error('Service failed to start within timeout period');
    }
    
    await browser.close();
    
    // Store global test data
    process.env.TEST_START_TIME = new Date().toISOString();
    
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  }
  
  console.log('✅ Playwright Global Setup Complete');
}

module.exports = globalSetup;

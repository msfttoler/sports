// global-teardown.js
async function globalTeardown() {
  console.log('🧹 Starting Playwright Global Teardown');
  
  // Clean up any global test data
  console.log(`Test run completed. Started at: ${process.env.TEST_START_TIME}`);
  console.log(`Test run finished at: ${new Date().toISOString()}`);
  
  // Additional cleanup can be added here
  // - Clean up test data from Cosmos DB
  // - Reset any modified configuration
  // - Generate final test reports
  
  console.log('✅ Playwright Global Teardown Complete');
}

module.exports = globalTeardown;

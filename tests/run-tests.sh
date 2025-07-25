#!/bin/bash

# Playwright Test Runner Script for Sports Prediction System
# This script provides various testing options and configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Default values
TEST_TYPE="all"
HEADLESS=true
WORKERS=4
BROWSER="chromium"
ENVIRONMENT="local"
OUTPUT_DIR="test-results"
TIMEOUT=30000

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -h|--headed)
            HEADLESS=false
            shift
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -b|--browser)
            BROWSER="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -t, --type TYPE        Test type: api, performance, security, integration, all (default: all)"
            echo "  -h, --headed          Run tests in headed mode (default: headless)"
            echo "  -w, --workers NUM     Number of parallel workers (default: 4)"
            echo "  -b, --browser BROWSER Browser to use: chromium, firefox, webkit (default: chromium)"
            echo "  -e, --environment ENV Environment: local, staging, production (default: local)"
            echo "  --timeout MS          Test timeout in milliseconds (default: 30000)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_info "🎭 Sports Prediction System - Playwright Testing"
echo "=================================================="

# Change to tests directory
cd "$(dirname "$0")"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "package.json not found. Please run this script from the tests directory."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_info "Installing test dependencies..."
    npm install
fi

# Install Playwright browsers if needed
if [ ! -d "node_modules/@playwright/test" ]; then
    print_error "Playwright not installed. Run 'npm install' first."
    exit 1
fi

# Check if browsers are installed
print_info "Checking Playwright browser installation..."
npx playwright install --with-deps

# Set environment variables based on environment
case $ENVIRONMENT in
    local)
        export FUNCTION_APP_URL="http://localhost:7071"
        print_info "Testing against local environment: $FUNCTION_APP_URL"
        ;;
    staging)
        if [ -z "$STAGING_URL" ]; then
            print_error "STAGING_URL environment variable not set"
            exit 1
        fi
        export FUNCTION_APP_URL="$STAGING_URL"
        print_info "Testing against staging environment: $FUNCTION_APP_URL"
        ;;
    production)
        if [ -z "$PRODUCTION_URL" ]; then
            print_error "PRODUCTION_URL environment variable not set"
            exit 1
        fi
        export FUNCTION_APP_URL="$PRODUCTION_URL"
        print_warning "Testing against PRODUCTION environment: $FUNCTION_APP_URL"
        read -p "Are you sure you want to run tests against production? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Test cancelled by user"
            exit 0
        fi
        ;;
    *)
        print_error "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build Playwright command
PLAYWRIGHT_CMD="npx playwright test"

# Add browser selection
PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD --project=$BROWSER"

# Add headless/headed mode
if [ "$HEADLESS" = false ]; then
    PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD --headed"
fi

# Add workers
PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD --workers=$WORKERS"

# Add timeout
PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD --timeout=$TIMEOUT"

# Add test type filter
case $TEST_TYPE in
    api)
        PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD e2e/api-tests.spec.js"
        ;;
    performance)
        PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD e2e/performance-tests.spec.js"
        ;;
    security)
        PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD e2e/security-tests.spec.js"
        ;;
    integration)
        PLAYWRIGHT_CMD="$PLAYWRIGHT_CMD e2e/integration-tests.spec.js"
        ;;
    all)
        # Run all tests
        ;;
    *)
        print_error "Unknown test type: $TEST_TYPE"
        print_info "Available types: api, performance, security, integration, all"
        exit 1
        ;;
esac

# Health check before running tests
print_info "Performing health check..."
if [ "$ENVIRONMENT" = "local" ]; then
    # Check if local service is running
    if ! curl -s "$FUNCTION_APP_URL/api/health" > /dev/null; then
        print_warning "Local service not responding. Make sure your Azure Functions app is running."
        print_info "To start local service, run: func start"
        
        read -p "Continue with tests anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_status "Health check passed"
    fi
fi

# Run the tests
print_info "Running tests with command: $PLAYWRIGHT_CMD"
echo "Test configuration:"
echo "  Type: $TEST_TYPE"
echo "  Browser: $BROWSER"
echo "  Headless: $HEADLESS"
echo "  Workers: $WORKERS"
echo "  Environment: $ENVIRONMENT"
echo "  Timeout: ${TIMEOUT}ms"
echo ""

# Execute tests
if eval "$PLAYWRIGHT_CMD"; then
    print_status "All tests completed successfully!"
    
    # Generate and show report
    if [ -f "$OUTPUT_DIR/index.html" ]; then
        print_info "Test report generated: $OUTPUT_DIR/index.html"
        
        if command -v open &> /dev/null; then
            read -p "Open test report in browser? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                open "$OUTPUT_DIR/index.html"
            fi
        fi
    fi
    
    # Show results summary
    if [ -f "$OUTPUT_DIR/results.json" ]; then
        print_info "Generating test summary..."
        node -e "
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('$OUTPUT_DIR/results.json', 'utf8'));
            console.log('\\n📊 Test Summary:');
            console.log('================');
            console.log(\`Total: \${results.stats.total}\`);
            console.log(\`Passed: \${results.stats.passed}\`);
            console.log(\`Failed: \${results.stats.failed}\`);
            console.log(\`Skipped: \${results.stats.skipped}\`);
            console.log(\`Duration: \${Math.round(results.stats.duration / 1000)}s\`);
            
            if (results.stats.failed > 0) {
                console.log('\\n❌ Failed Tests:');
                results.suites.forEach(suite => {
                    suite.specs.forEach(spec => {
                        spec.tests.forEach(test => {
                            if (test.status === 'failed') {
                                console.log(\`  - \${test.title}\`);
                            }
                        });
                    });
                });
            }
        " 2>/dev/null || true
    fi
    
else
    print_error "Tests failed!"
    
    # Show quick error summary
    if [ -f "$OUTPUT_DIR/results.json" ]; then
        print_info "Quick error summary:"
        node -e "
            const fs = require('fs');
            try {
                const results = JSON.parse(fs.readFileSync('$OUTPUT_DIR/results.json', 'utf8'));
                console.log(\`Failed: \${results.stats.failed}\/\${results.stats.total} tests\`);
            } catch (e) {
                console.log('Could not read results file');
            }
        " 2>/dev/null || true
    fi
    
    exit 1
fi

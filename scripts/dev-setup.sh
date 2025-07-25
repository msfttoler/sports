#!/bin/bash

# Sports Prediction System - Local Development Setup
# This script sets up the development environment for local testing

set -e

echo "🛠️  Sports Prediction System - Local Setup"
echo "==========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check prerequisites for local development
check_prerequisites() {
    print_info "Checking prerequisites for local development..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check Azure Functions Core Tools
    if ! command -v func &> /dev/null; then
        print_warning "Azure Functions Core Tools not found. Installing..."
        
        if command -v npm &> /dev/null; then
            npm install -g azure-functions-core-tools@4 --unsafe-perm true
        elif command -v brew &> /dev/null; then
            brew tap azure/functions
            brew install azure-functions-core-tools@4
        else
            print_error "Could not install Azure Functions Core Tools. Please install manually."
            print_info "Visit: https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"
            exit 1
        fi
    fi
    
    print_status "Prerequisites checked"
}

# Install Python dependencies
install_python_dependencies() {
    print_info "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_status "Python dependencies installed"
    else
        print_warning "requirements.txt not found"
    fi
}

# Create local settings file
create_local_settings() {
    print_info "Creating local settings..."
    
    if [ ! -f "local.settings.json" ]; then
        cat > local.settings.json << EOF
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOS_DB_CONNECTION_STRING": "AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
    "AZURE_CLIENT_ID": "your-managed-identity-client-id",
    "ESPN_API_KEY": "your-espn-api-key",
    "SPORTS_API_KEY": "your-sports-api-key",
    "KEY_VAULT_URL": "https://your-keyvault.vault.azure.net/",
    "AZURE_LOG_LEVEL": "INFO"
  },
  "Host": {
    "CORS": "*",
    "CORSCredentials": false
  }
}
EOF
        print_status "Created local.settings.json"
        print_warning "Please update the connection strings and API keys in local.settings.json"
    else
        print_info "local.settings.json already exists"
    fi
}

# Start Cosmos DB Emulator instructions
cosmos_emulator_instructions() {
    print_info "Cosmos DB Emulator Setup:"
    echo "For local development, you can use the Cosmos DB Emulator:"
    echo "1. Download from: https://docs.microsoft.com/en-us/azure/cosmos-db/local-emulator"
    echo "2. Install and start the emulator"
    echo "3. The default connection string is already configured in local.settings.json"
    echo
}

# Create development data
create_dev_data() {
    read -p "Do you want to generate sample data for local development? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Generating sample data..."
        
        if [ -f "scripts/generate_sample_data.py" ]; then
            # Activate virtual environment
            source venv/bin/activate
            python scripts/generate_sample_data.py --local
            print_status "Sample data generated"
        else
            print_warning "Sample data generator not found"
        fi
    fi
}

# Start local development server
start_local_server() {
    print_info "Starting local Azure Functions host..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    print_status "Local setup complete!"
    echo
    print_info "Your Function App will be available at: http://localhost:7071"
    print_info "API endpoints:"
    echo "  - Sports Data: http://localhost:7071/api/sports-data"
    echo "  - Predictions: http://localhost:7071/api/predictions"
    echo "  - Team Stats: http://localhost:7071/api/team-stats"
    echo
    print_info "Starting Functions host... (Press Ctrl+C to stop)"
    
    func start
}

# Main setup flow
main() {
    echo "Setting up local development environment..."
    echo
    
    check_prerequisites
    install_python_dependencies
    create_local_settings
    cosmos_emulator_instructions
    create_dev_data
    
    read -p "Do you want to start the local development server now? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_local_server
    else
        print_status "Setup complete!"
        print_info "To start the development server later, run: ./scripts/dev-setup.sh"
        print_info "Or manually run: source venv/bin/activate && func start"
    fi
}

# Run main function
main "$@"

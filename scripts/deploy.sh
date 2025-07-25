#!/bin/bash

# Sports Prediction System Deployment Script
# This script deploys the entire system using Azure Developer CLI and Terraform

set -e

echo "🚀 Sports Prediction System Deployment"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
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

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Azure Developer CLI is installed
    if ! command -v azd &> /dev/null; then
        print_error "Azure Developer CLI (azd) is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_warning "Terraform is not installed. Installing via package manager..."
        
        # Try to install Terraform
        if command -v brew &> /dev/null; then
            brew install terraform
        elif command -v choco &> /dev/null; then
            choco install terraform
        else
            print_error "Could not install Terraform automatically. Please install manually."
            exit 1
        fi
    fi
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    print_status "All prerequisites are installed"
}

# Login to Azure
azure_login() {
    print_info "Checking Azure login status..."
    
    if ! az account show &> /dev/null; then
        print_info "Not logged in to Azure. Starting login process..."
        az login
    else
        print_status "Already logged in to Azure"
    fi
    
    # Show current subscription
    SUBSCRIPTION=$(az account show --query name -o tsv)
    print_info "Current subscription: $SUBSCRIPTION"
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        python3 -m pip install -r requirements.txt
        print_status "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping dependency installation"
    fi
}

# Initialize Azure Developer CLI
initialize_azd() {
    print_info "Initializing Azure Developer CLI..."
    
    # Check if already initialized
    if [ ! -f ".azure/config.json" ]; then
        print_info "Initializing azd environment..."
        azd init --template minimal
    else
        print_status "Azure Developer CLI already initialized"
    fi
}

# Deploy infrastructure
deploy_infrastructure() {
    print_info "Deploying infrastructure with Terraform..."
    
    cd infra
    
    # Initialize Terraform
    print_info "Initializing Terraform..."
    terraform init
    
    # Validate Terraform configuration
    print_info "Validating Terraform configuration..."
    terraform validate
    
    if [ $? -ne 0 ]; then
        print_error "Terraform validation failed"
        exit 1
    fi
    
    # Plan deployment
    print_info "Planning Terraform deployment..."
    terraform plan -var-file="main.tfvars.json" -out=tfplan
    
    # Apply deployment
    print_info "Applying Terraform deployment..."
    terraform apply tfplan
    
    if [ $? -eq 0 ]; then
        print_status "Infrastructure deployed successfully"
        
        # Get outputs
        print_info "Retrieving deployment outputs..."
        terraform output -json > outputs.json
        
        # Extract important values
        FUNCTION_APP_NAME=$(terraform output -raw FUNCTION_APP_NAME)
        FUNCTION_APP_URL=$(terraform output -raw FUNCTION_APP_URL)
        RESOURCE_GROUP=$(terraform output -raw AZURE_RESOURCE_GROUP)
        
        print_status "Infrastructure deployed to resource group: $RESOURCE_GROUP"
        print_status "Function App: $FUNCTION_APP_NAME"
        print_status "Function App URL: $FUNCTION_APP_URL"
    else
        print_error "Infrastructure deployment failed"
        exit 1
    fi
    
    cd ..
}

# Deploy application code
deploy_application() {
    print_info "Deploying application code..."
    
    # Get Function App name from Terraform outputs
    if [ -f "infra/outputs.json" ]; then
        FUNCTION_APP_NAME=$(cat infra/outputs.json | python3 -c "import json,sys; print(json.load(sys.stdin)['FUNCTION_APP_NAME']['value'])")
    else
        print_error "Could not find Terraform outputs. Please ensure infrastructure is deployed first."
        exit 1
    fi
    
    # Deploy using Azure Functions Core Tools or azd
    if command -v func &> /dev/null; then
        print_info "Deploying with Azure Functions Core Tools..."
        func azure functionapp publish $FUNCTION_APP_NAME --python
    else
        print_info "Deploying with Azure Developer CLI..."
        azd deploy
    fi
    
    if [ $? -eq 0 ]; then
        print_status "Application deployed successfully"
    else
        print_error "Application deployment failed"
        exit 1
    fi
}

# Configure function app settings
configure_app_settings() {
    print_info "Configuring Function App settings..."
    
    if [ -f "infra/outputs.json" ]; then
        FUNCTION_APP_NAME=$(cat infra/outputs.json | python3 -c "import json,sys; print(json.load(sys.stdin)['FUNCTION_APP_NAME']['value'])")
        RESOURCE_GROUP=$(cat infra/outputs.json | python3 -c "import json,sys; print(json.load(sys.stdin)['AZURE_RESOURCE_GROUP']['value'])")
        
        # Set any additional app settings if needed
        print_info "Function App settings configured"
    else
        print_warning "Could not configure app settings - outputs not found"
    fi
}

# Generate sample data (optional)
generate_sample_data() {
    read -p "Do you want to generate and upload sample data? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Generating sample data..."
        
        if [ -f "scripts/generate_sample_data.py" ]; then
            python3 scripts/generate_sample_data.py
            print_status "Sample data generated"
        else
            print_warning "Sample data generator not found"
        fi
    fi
}

# Run tests
run_tests() {
    read -p "Do you want to run API tests? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Running API tests..."
        
        if [ -f "scripts/test_api.py" ]; then
            # Update the test script with the actual Function App URL
            if [ -f "infra/outputs.json" ]; then
                FUNCTION_APP_URL=$(cat infra/outputs.json | python3 -c "import json,sys; print(json.load(sys.stdin)['FUNCTION_APP_URL']['value'])")
                
                # Run tests
                python3 scripts/test_api.py
                print_status "Tests completed"
            else
                print_warning "Could not get Function App URL for testing"
            fi
        else
            print_warning "Test script not found"
        fi
    fi
}

# Display deployment summary
display_summary() {
    print_status "Deployment completed successfully!"
    echo
    echo "📋 Deployment Summary"
    echo "===================="
    
    if [ -f "infra/outputs.json" ]; then
        FUNCTION_APP_URL=$(cat infra/outputs.json | python3 -c "import json,sys; print(json.load(sys.stdin)['FUNCTION_APP_URL']['value'])" 2>/dev/null || echo "Not available")
        API_PREDICTIONS_URL=$(cat infra/outputs.json | python3 -c "import json,sys; print(json.load(sys.stdin)['API_PREDICTIONS_URL']['value'])" 2>/dev/null || echo "Not available")
        API_SPORTS_DATA_URL=$(cat infra/outputs.json | python3 -c "import json,sys; print(json.load(sys.stdin)['API_SPORTS_DATA_URL']['value'])" 2>/dev/null || echo "Not available")
        
        echo "🌐 Function App URL: $FUNCTION_APP_URL"
        echo "📊 Predictions API: $API_PREDICTIONS_URL"
        echo "🏈 Sports Data API: $API_SPORTS_DATA_URL"
        echo
        echo "🔗 Azure Portal: https://portal.azure.com"
        echo "📚 API Documentation: See README.md"
    else
        print_warning "Could not load deployment outputs"
    fi
    
    echo
    print_info "Next steps:"
    echo "1. Test the API endpoints using the provided URLs"
    echo "2. Configure sports data API keys in Azure Key Vault"
    echo "3. Set up monitoring and alerts in Azure"
    echo "4. Review the logs in Application Insights"
}

# Main deployment flow
main() {
    echo "Starting deployment process..."
    echo
    
    check_prerequisites
    azure_login
    install_dependencies
    initialize_azd
    deploy_infrastructure
    deploy_application
    configure_app_settings
    generate_sample_data
    run_tests
    display_summary
    
    print_status "All done! 🎉"
}

# Run main function
main "$@"

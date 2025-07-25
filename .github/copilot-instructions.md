<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Sports Prediction System Instructions

This is an Azure Functions project for sports data aggregation and ML-powered game predictions.

## Code Generation Guidelines

- Always use managed identity for Azure service authentication
- Implement proper error handling with retry logic for external API calls
- Use Cosmos DB for storing both raw sports data and ML predictions
- Include confidence scores (0-100) for all predictions
- Follow Azure Functions best practices for scalability
- Use async/await patterns for all I/O operations
- Implement proper logging using Azure Application Insights
- Store sensitive configuration in Azure Key Vault
- Use Pydantic models for data validation
- Include comprehensive error handling for ML model operations

## Data Models

- Game data should include teams, scores, dates, and metadata
- Predictions should include outcome, confidence score, and reasoning
- Historical data should be used for model training
- Real-time data should trigger prediction updates

## Security

- Never hardcode API keys or connection strings
- Use Azure Key Vault for all secrets
- Implement proper RBAC for Cosmos DB access
- Enable diagnostic logging for all functions

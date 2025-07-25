# Sports Prediction System

An Azure Functions-based system that aggregates sports data and uses machine learning to predict game outcomes with confidence scores.

## 🏈 Overview

This system provides:
- **Sports Data Aggregation**: Collects real-time sports scores and statistics from multiple APIs
- **AI/ML Predictions**: Uses machine learning models to predict game outcomes
- **Confidence Scoring**: Provides confidence scores (0-100%) for all predictions
- **RESTful APIs**: Easy-to-use endpoints for accessing predictions and statistics
- **Scalable Architecture**: Built on Azure Functions with Cosmos DB for high availability

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sports APIs   │    │  Azure Functions │    │   Cosmos DB     │
│  (ESPN, etc.)   │───▶│   (Python 3.11)  │───▶│  (NoSQL Store)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  ML Prediction  │
                       │    Models       │
                       └─────────────────┘
```

### Components

- **Data Ingestion Functions**: Collect sports data from external APIs
- **Prediction Engine**: ML models for outcome prediction with confidence scoring
- **API Endpoints**: RESTful interfaces for data access
- **Scheduled Sync**: Automated data synchronization every 6 hours
- **Storage Layer**: Cosmos DB containers for games, predictions, and statistics

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Azure CLI
- Azure Developer CLI (azd)
- Azure Functions Core Tools
- Terraform (optional, for infrastructure)

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd sports
   chmod +x scripts/dev-setup.sh
   ./scripts/dev-setup.sh
   ```

2. **Configure local settings:**
   - Update `local.settings.json` with your API keys
   - Start Cosmos DB Emulator for local development

3. **Start development server:**
   ```bash
   func start
   ```

### Azure Deployment

1. **Automated deployment:**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

2. **Manual deployment:**
   ```bash
   # Deploy infrastructure
   cd infra
   terraform init
   terraform plan -var-file="main.tfvars.json"
   terraform apply

   # Deploy application
   func azure functionapp publish <function-app-name> --python
   ```

## 📊 API Endpoints

### Sports Data Ingestion
- **Endpoint**: `POST /api/sports-data`
- **Purpose**: Trigger data collection from sports APIs
- **Parameters**: `sport` (optional), `date` (optional)

### Game Predictions
- **Endpoint**: `POST /api/game-predictor`
- **Purpose**: Generate ML predictions for games
- **Body**: Game data JSON

### Get Predictions
- **Endpoint**: `GET /api/predictions`
- **Purpose**: Retrieve game predictions
- **Query Params**: `sport`, `date`, `team`, `confidence_min`

### Team Statistics
- **Endpoint**: `GET /api/team-stats/{team_name}`
- **Purpose**: Get team performance statistics
- **Returns**: Win rate, average scores, recent form

## 🤖 Machine Learning Models

### Prediction Features
- Team historical performance
- Head-to-head records
- Recent form (last 5 games)
- Home/away advantage
- Player statistics

### Confidence Scoring
- **90-100%**: Very high confidence (strong historical patterns)
- **70-89%**: High confidence (clear statistical advantage)
- **50-69%**: Moderate confidence (slight edge detected)
- **30-49%**: Low confidence (uncertain outcome)
- **0-29%**: Very low confidence (insufficient data)

## 💾 Data Models

### Game Data
```python
{
    "id": "game_123",
    "home_team": "Team A",
    "away_team": "Team B",
    "sport": "NFL",
    "game_date": "2024-01-15T18:00:00Z",
    "status": "scheduled",
    "home_score": 0,
    "away_score": 0
}
```

### Prediction Data
```python
{
    "id": "pred_123",
    "game_id": "game_123",
    "predicted_outcome": "home_win",
    "confidence_score": 85,
    "reasoning": "Home team has won 8 of last 10 meetings",
    "created_at": "2024-01-15T12:00:00Z"
}
```

## 🔧 Configuration

### Environment Variables
- `COSMOS_DB_CONNECTION_STRING`: Cosmos DB connection
- `ESPN_API_KEY`: ESPN API access key
- `SPORTS_API_KEY`: Additional sports API key
- `AZURE_CLIENT_ID`: Managed identity client ID
- `KEY_VAULT_URL`: Azure Key Vault URL

### Azure Resources
- **Function App**: Hosts the Python functions
- **Cosmos DB**: NoSQL database for all data storage
- **Key Vault**: Secure storage for API keys and secrets
- **Storage Account**: Function app storage and logs
- **Application Insights**: Monitoring and diagnostics

## 🧪 Testing

### Playwright End-to-End Testing (Recommended)
```bash
# Navigate to tests directory
cd tests

# Install dependencies
npm install
npx playwright install

# Run all tests
./run-tests.sh

# Run specific test types
./run-tests.sh --type api          # API functionality tests
./run-tests.sh --type performance  # Performance and load tests
./run-tests.sh --type security     # Security vulnerability tests
./run-tests.sh --type integration  # End-to-end workflow tests

# Run against different environments
./run-tests.sh --environment staging
./run-tests.sh --environment production

# Debug mode with visible browser
./run-tests.sh --headed --debug
```

### Python API Tests (Legacy)
```bash
python scripts/test_api.py
```

### Generate Sample Data
```bash
python scripts/generate_sample_data.py
```

### Load Testing
```bash
# Playwright load testing (recommended)
cd tests
./run-tests.sh --type performance

# Locust load testing (alternative)
pip install locust
locust -f scripts/load_test.py --host=https://your-function-app.azurewebsites.net
```

### Test Coverage
- **API Testing**: Complete endpoint validation with Playwright
- **Performance Testing**: Response time, throughput, and concurrency testing
- **Security Testing**: XSS, injection, authentication, and vulnerability scanning
- **Integration Testing**: End-to-end workflow validation
- **Multi-browser Testing**: Chromium, Firefox, and WebKit support
- **CI/CD Integration**: Automated testing in GitHub Actions

## 📁 Project Structure

```
sports/
├── models/                     # Pydantic data models
│   └── __init__.py
├── shared/                     # Common utilities
│   └── utils.py
├── sports_data_ingestion/      # Data collection function
│   ├── __init__.py
│   └── function.json
├── game_predictor/             # ML prediction function
│   ├── __init__.py
│   └── function.json
├── get_predictions/            # Predictions API
│   ├── __init__.py
│   └── function.json
├── get_team_stats/             # Team statistics API
│   ├── __init__.py
│   └── function.json
├── scheduled_data_sync/        # Automated sync function
│   ├── __init__.py
│   └── function.json
├── infra/                      # Terraform infrastructure
│   ├── main.tf
│   ├── outputs.tf
│   └── main.tfvars.json
├── scripts/                    # Deployment and utility scripts
│   ├── deploy.sh
│   ├── dev-setup.sh
│   ├── generate_sample_data.py
│   └── test_api.py
├── requirements.txt            # Python dependencies
├── host.json                   # Functions host configuration
├── local.settings.json.template # Local settings template
└── README.md                   # This file
```

## 🔐 Security

### Authentication
- **Managed Identity**: Used for Azure service authentication
- **Key Vault**: Secure storage for all secrets and API keys
- **RBAC**: Proper role assignments for Cosmos DB access

### Best Practices
- No hardcoded secrets in code
- Minimal required permissions
- Encrypted connections to all services
- Application Insights for security monitoring

## 📈 Monitoring

### Application Insights
- Function execution metrics
- API response times
- Error rates and exceptions
- Custom prediction accuracy metrics

### Alerts
- Function failures
- High API latency
- Low prediction confidence trends
- Data ingestion failures

## 🚀 Performance

### Optimization Features
- Async/await patterns for all I/O operations
- Connection pooling for Cosmos DB
- Retry logic with exponential backoff
- Efficient data models with Pydantic validation

### Scaling
- Azure Functions automatic scaling
- Cosmos DB request unit optimization
- Connection string caching
- Batch processing for large datasets

## 🛠️ Development

### Adding New Sports
1. Extend `SportType` enum in `models/__init__.py`
2. Add sport-specific data parsing in data ingestion function
3. Update ML features for the new sport
4. Add sport-specific validation rules

### Improving ML Models
1. Implement new feature extraction in `shared/utils.py`
2. Update prediction logic in `game_predictor/__init__.py`
3. Add model training scripts in `scripts/`
4. Update confidence calculation algorithms

### Adding New APIs
1. Create new function directory with `__init__.py` and `function.json`
2. Add route to API endpoints
3. Update Terraform configuration if needed
4. Add tests to `test_api.py`

## 📚 Documentation

### API Documentation
- Swagger/OpenAPI documentation available at function app URL
- Interactive API testing via Azure Functions portal
- Postman collection available in `docs/` directory

### Code Documentation
- Docstrings for all functions and classes
- Type hints throughout the codebase
- Comprehensive error handling documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues

**Cosmos DB Connection Errors**
- Verify connection string in Key Vault
- Check managed identity permissions
- Ensure Cosmos DB is in the same region

**Function App Deployment Failures**
- Check Python version compatibility
- Verify all dependencies in requirements.txt
- Review Application Insights logs

**Low Prediction Accuracy**
- Increase historical data volume
- Update ML model parameters
- Review feature selection

### Getting Help
- Check Application Insights for detailed error logs
- Review Azure Function App logs in the portal
- Use the test scripts to isolate issues
- Check the GitHub Issues page for known problems

## 🔮 Roadmap

### Upcoming Features
- Real-time streaming predictions
- Advanced ML models (neural networks)
- Multi-sport tournament predictions
- Social media sentiment analysis
- Mobile app integration

### Performance Improvements
- Redis caching layer
- GraphQL API endpoints
- Serverless SQL for analytics
- Edge deployment for global access
- **Azure Storage**: Blob storage for ML models and large datasets

## Features

- Real-time sports data ingestion from multiple APIs
- Data cleaning and aggregation
- ML-powered game outcome predictions
- Confidence scoring for predictions
- RESTful API for accessing predictions

## Functions

### Data Ingestion
- `sports_data_ingestion`: Scheduled function to collect sports data
- `game_schedule_sync`: Sync upcoming game schedules

### Data Processing
- `data_cleaner`: Clean and normalize sports data
- `data_aggregator`: Aggregate historical performance data

### ML Predictions
- `game_predictor`: Generate predictions for upcoming games
- `model_trainer`: Retrain ML models with new data

### API Endpoints
- `get_predictions`: HTTP endpoint to retrieve predictions
- `get_team_stats`: HTTP endpoint for team statistics

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Configure environment variables (see `.env.example`)
3. Deploy infrastructure: `azd up`
4. Deploy functions: `func azure functionapp publish <function-app-name>`

## Environment Variables

- `COSMOS_DB_ENDPOINT`: Cosmos DB endpoint URL
- `SPORTS_API_KEY`: API key for sports data service
- `ML_WORKSPACE_NAME`: Azure ML workspace name
- `STORAGE_ACCOUNT_NAME`: Azure Storage account name

## Development

Run locally: `func start`

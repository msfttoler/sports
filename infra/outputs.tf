# Outputs for the Sports Prediction System

output "AZURE_RESOURCE_GROUP" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "RESOURCE_GROUP_ID" {
  description = "Resource group ID"
  value       = azurerm_resource_group.main.id
}

output "AZURE_LOCATION" {
  description = "Azure region where resources are deployed"
  value       = azurerm_resource_group.main.location
}

output "FUNCTION_APP_NAME" {
  description = "Name of the Function App"
  value       = azurerm_linux_function_app.main.name
}

output "FUNCTION_APP_URL" {
  description = "URL of the Function App"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "COSMOS_DB_ENDPOINT" {
  description = "Cosmos DB endpoint URL"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "COSMOS_DB_NAME" {
  description = "Cosmos DB database name"
  value       = azurerm_cosmosdb_sql_database.main.name
}

output "STORAGE_ACCOUNT_NAME" {
  description = "Storage account name"
  value       = azurerm_storage_account.main.name
}

output "STORAGE_ACCOUNT_URL" {
  description = "Storage account blob endpoint"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "KEY_VAULT_NAME" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

output "KEY_VAULT_URL" {
  description = "Key Vault URL"
  value       = azurerm_key_vault.main.vault_uri
}

output "APPLICATION_INSIGHTS_CONNECTION_STRING" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "USER_ASSIGNED_IDENTITY_ID" {
  description = "User assigned managed identity ID"
  value       = azurerm_user_assigned_identity.main.id
}

output "USER_ASSIGNED_IDENTITY_CLIENT_ID" {
  description = "User assigned managed identity client ID"
  value       = azurerm_user_assigned_identity.main.client_id
}

# API Endpoints
output "API_PREDICTIONS_URL" {
  description = "URL for the predictions API endpoint"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}/api/get_predictions"
}

output "API_SPORTS_DATA_URL" {
  description = "URL for the sports data ingestion endpoint"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}/api/sports_data_ingestion"
}

output "API_GAME_PREDICTOR_URL" {
  description = "URL for the game predictor endpoint"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}/api/game_predictor"
}

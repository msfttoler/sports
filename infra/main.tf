# Sports Prediction System Infrastructure
# Terraform configuration for Azure resources

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azurecaf = {
      source  = "aztfmod/azurecaf"
      version = "~> 1.2"
    }
  }
}

# Configure the Microsoft Azure Provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Data source for current client configuration
data "azurerm_client_config" "current" {}

# Variables
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "resource_token" {
  description = "Resource token for naming"
  type        = string
  default     = "sports"
}

# Generate resource names using azurecaf
resource "azurecaf_name" "resource_group" {
  name          = var.resource_token
  resource_type = "azurerm_resource_group"
  suffixes      = [var.environment]
}

resource "azurecaf_name" "storage_account" {
  name          = var.resource_token
  resource_type = "azurerm_storage_account"
  suffixes      = [var.environment]
}

resource "azurecaf_name" "function_app" {
  name          = var.resource_token
  resource_type = "azurerm_function_app"
  suffixes      = [var.environment]
}

resource "azurecaf_name" "app_service_plan" {
  name          = var.resource_token
  resource_type = "azurerm_app_service_plan"
  suffixes      = [var.environment]
}

resource "azurecaf_name" "cosmos_account" {
  name          = var.resource_token
  resource_type = "azurerm_cosmosdb_account"
  suffixes      = [var.environment]
}

resource "azurecaf_name" "key_vault" {
  name          = var.resource_token
  resource_type = "azurerm_key_vault"
  suffixes      = [var.environment]
}

resource "azurecaf_name" "application_insights" {
  name          = var.resource_token
  resource_type = "azurerm_application_insights"
  suffixes      = [var.environment]
}

resource "azurecaf_name" "user_assigned_identity" {
  name          = var.resource_token
  resource_type = "azurerm_user_assigned_identity"
  suffixes      = [var.environment]
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = azurecaf_name.resource_group.result
  location = var.location

  tags = {
    azd-env-name = var.environment
    Environment  = var.environment
    Project      = "sports-prediction"
  }
}

# User Assigned Managed Identity
resource "azurerm_user_assigned_identity" "main" {
  name                = azurecaf_name.user_assigned_identity.result
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location

  tags = {
    Environment = var.environment
    Project     = "sports-prediction"
  }
}

# Storage Account
resource "azurerm_storage_account" "main" {
  name                     = azurecaf_name.storage_account.result
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  # Security settings
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  
  # Network access
  public_network_access_enabled = true
  
  # Blob properties
  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true
    
    delete_retention_policy {
      days = 7
    }
    
    container_delete_retention_policy {
      days = 7
    }
  }

  tags = {
    Environment = var.environment
    Project     = "sports-prediction"
  }
}

# Storage containers
resource "azurerm_storage_container" "ml_models" {
  name                 = "ml-models"
  storage_account_id   = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "data_exports" {
  name                 = "data-exports"
  storage_account_id   = azurerm_storage_account.main.id
  container_access_type = "private"
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = azurecaf_name.application_insights.result
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  application_type   = "other"
  retention_in_days  = 90

  tags = {
    Environment = var.environment
    Project     = "sports-prediction"
  }
}

# Log Analytics Workspace for Application Insights
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${azurecaf_name.application_insights.result}-law"
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  sku                = "PerGB2018"
  retention_in_days  = 90

  tags = {
    Environment = var.environment
    Project     = "sports-prediction"
  }
}

# Key Vault
resource "azurerm_key_vault" "main" {
  name                        = azurecaf_name.key_vault.result
  resource_group_name         = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  enabled_for_disk_encryption = true
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  sku_name                   = "standard"
  
  # Network access
  public_network_access_enabled = true
  
  # Access policies
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get", "List", "Create", "Delete", "Update", "Recover", "Backup", "Restore"
    ]

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Recover", "Backup", "Restore"
    ]

    storage_permissions = [
      "Get", "List", "Set", "Delete", "Recover", "Backup", "Restore"
    ]
  }
  
  # Access policy for managed identity
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_user_assigned_identity.main.principal_id

    secret_permissions = [
      "Get", "List"
    ]
  }

  tags = {
    Environment = var.environment
    Project     = "sports-prediction"
  }
}

# Cosmos DB Account
resource "azurerm_cosmosdb_account" "main" {
  name                = azurecaf_name.cosmos_account.result
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  offer_type         = "Standard"
  kind               = "GlobalDocumentDB"
  
  # Disable key-based access for security
  local_authentication_disabled = false  # Set to true in production
  
  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 300
    max_staleness_prefix    = 100000
  }
  
  geo_location {
    location          = var.location
    failover_priority = 0
  }
  
  # Backup policy
  backup {
    type                = "Periodic"
    interval_in_minutes = 240
    retention_in_hours  = 8
    storage_redundancy  = "Geo"
  }
  
  # Network access
  public_network_access_enabled = true
  is_virtual_network_filter_enabled = false

  tags = {
    Environment = var.environment
    Project     = "sports-prediction"
  }
}

# Cosmos DB Database
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "SportsData"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  throughput          = 400
}

# Cosmos DB Containers
resource "azurerm_cosmosdb_sql_container" "games" {
  name                  = "games"
  resource_group_name   = azurerm_resource_group.main.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/id"]
  partition_key_version = 1
  throughput            = 400

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
    
    excluded_path {
      path = "/\"_etag\"/?"
    }
  }

  unique_key {
    paths = ["/id"]
  }
}

resource "azurerm_cosmosdb_sql_container" "predictions" {
  name                  = "predictions"
  resource_group_name   = azurerm_resource_group.main.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/game_id"]
  partition_key_version = 1
  throughput            = 400

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
    
    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "team_stats" {
  name                  = "team_stats"
  resource_group_name   = azurerm_resource_group.main.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/team_id"]
  partition_key_version = 1
  throughput            = 400

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
    
    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

# App Service Plan
resource "azurerm_service_plan" "main" {
  name                = azurecaf_name.app_service_plan.result
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  os_type            = "Linux"
  sku_name           = "Y1"  # Consumption plan

  tags = {
    Environment = var.environment
    Project     = "sports-prediction"
  }
}

# Linux Function App
resource "azurerm_linux_function_app" "main" {
  name                = azurecaf_name.function_app.result
  resource_group_name = azurerm_resource_group.main.name
  location           = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id
  
  # Storage account connection (required for Function Apps)
  storage_account_name       = azurerm_storage_account.main.name
  storage_uses_managed_identity = true
  
  # Identity configuration
  identity {
    type = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }
  
  # Function app configuration
  site_config {
    application_insights_key = azurerm_application_insights.main.instrumentation_key
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    
    # Python runtime
    application_stack {
      python_version = "3.11"
    }
    
    # CORS configuration
    cors {
      allowed_origins = ["*"]
      support_credentials = false
    }
  }
  
  # Application settings
  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"             = "python"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    "COSMOS_DB_ENDPOINT"                   = azurerm_cosmosdb_account.main.endpoint
    "KEYVAULT_URL"                        = azurerm_key_vault.main.vault_uri
    "STORAGE_ACCOUNT_URL"                 = azurerm_storage_account.main.primary_blob_endpoint
    "AZURE_CLIENT_ID"                     = azurerm_user_assigned_identity.main.client_id
    "AZURE_RESOURCE_GROUP"                = azurerm_resource_group.main.name
    "AZURE_SUBSCRIPTION_ID"               = data.azurerm_client_config.current.subscription_id
  }

  tags = {
    Environment = var.environment
    Project     = "sports-prediction"
  }
  
  depends_on = [
    azurerm_role_assignment.storage_blob_data_owner,
    azurerm_role_assignment.cosmos_contributor
  ]
}

# Role assignments for managed identity
resource "azurerm_role_assignment" "storage_blob_data_owner" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "cosmos_contributor" {
  scope                = azurerm_cosmosdb_account.main.id
  role_definition_name = "Cosmos DB Built-in Data Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
  principal_type       = "ServicePrincipal"
}

# Key Vault secrets
resource "azurerm_key_vault_secret" "cosmos_connection_string" {
  name         = "cosmos-connection-string"
  value        = azurerm_cosmosdb_account.main.primary_sql_connection_string
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_key_vault.main]
}

resource "azurerm_key_vault_secret" "storage_connection_string" {
  name         = "storage-connection-string"
  value        = azurerm_storage_account.main.primary_connection_string
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_key_vault.main]
}

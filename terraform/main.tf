terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.60"
    }
  }

  backend "azurerm" {
    use_oidc = true
  }
}

provider "azurerm" {
  features {}
  use_oidc = true
}

# =============================================================================
# Locals — derived names, tags, and shortcuts
# =============================================================================

locals {
  env = var.app.environment

  # Naming conventions
  prefix         = "deploy-box"
  prefix_compact = "deploybox" # resources that forbid hyphens (ACR, etc.)

  names = {
    resource_group = "${local.prefix}-rg-${local.env}"
    container_app  = "${local.prefix}-website-contapp-${local.env}"
    identity       = "${local.prefix}-website-contapp-identity-${local.env}"
    acr            = "${local.prefix_compact}cr${local.env}"
    cae            = "${local.prefix}-cae-${local.env}"
    key_vault      = "${local.prefix}-kv-${local.env}"
    sbns           = "${local.prefix}-sbns-${local.env}"
  }

  common_tags = merge(
    {
      ManagedBy   = "Terraform"
      Environment = local.env
    },
    var.extra_tags,
  )
}

# =============================================================================
# Data sources
# =============================================================================

data "azurerm_client_config" "current" {}

data "azurerm_container_registry" "acr" {
  name                = local.names.acr
  resource_group_name = local.names.resource_group
}

data "azurerm_container_app_environment" "shared_container_env" {
  name                = local.names.cae
  resource_group_name = local.names.resource_group
}

data "azurerm_key_vault" "shared_key_vault" {
  name                = local.names.key_vault
  resource_group_name = local.names.resource_group
}

data "azurerm_resource_group" "main_rg" {
  name = local.names.resource_group
}

data "azurerm_servicebus_namespace" "service_bus" {
  name                = local.names.sbns
  resource_group_name = data.azurerm_resource_group.main_rg.name
}

# =============================================================================
# Container App
# =============================================================================

resource "azurerm_container_app" "container_app" {
  name                         = local.names.container_app
  resource_group_name          = data.azurerm_resource_group.main_rg.name
  revision_mode                = "Single"
  container_app_environment_id = data.azurerm_container_app_environment.shared_container_env.id

  tags = local.common_tags

  template {
    container {
      name   = "${local.prefix}-container"
      image  = var.image_name
      cpu    = 0.25
      memory = "0.5Gi"

      # --- Core ---
      env {
        name  = "ENV"
        value = upper(local.env)
      }
      env {
        name  = "HOST"
        value = var.app.host
      }

      # --- Azure identity ---
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.container_app_identity.client_id
      }
      env {
        name  = "AZURE_TENANT_ID"
        value = data.azurerm_client_config.current.tenant_id
      }
      env {
        name  = "AZURE_SUBSCRIPTION_ID"
        value = data.azurerm_client_config.current.subscription_id
      }

      # --- Auth / OAuth2 ---
      env {
        name  = "OAUTH2_PASSWORD_CREDENTIALS_CLIENT_ID"
        value = var.auth.oauth2_password_credentials_client_id
      }
      env {
        name  = "OAUTH2_AUTH_CODE_CLIENT_ID"
        value = var.auth.oauth2_auth_code_client_id
      }
      env {
        name  = "DEPLOY_BOX_GITHUB_CLIENT_ID"
        value = var.auth.github_client_id
      }

      # --- Database ---
      env {
        name  = "DB_NAME"
        value = var.database.name
      }
      env {
        name  = "DB_USER"
        value = var.database.user
      }
      env {
        name  = "DB_HOST"
        value = var.database.host
      }
      env {
        name  = "DB_PORT"
        value = var.database.port
      }

      # --- External services ---
      env {
        name  = "DEPLOY_BOX_STACK_ENDPOINT"
        value = var.services.stack_endpoint
      }
      env {
        name  = "EMAIL_HOST_USER"
        value = var.services.email_host_user
      }
      env {
        name  = "DEPLOY_BOX_API_BASE_URL"
        value = var.services.api_base_url
      }
      env {
        name  = "AZURE_FUNCTION_URL"
        value = var.services.azure_function_url
      }
      env {
        name  = "NPM_BIN_PATH"
        value = var.services.npm_bin_path
      }
      env {
        name  = "KEY_VAULT_NAME"
        value = local.names.key_vault
      }
      env {
        name  = "SERVICE_BUS_CONNECTION_STRING"
        value = data.azurerm_servicebus_namespace.service_bus.default_primary_connection_string
      }
    }

    min_replicas = 0
    max_replicas = 1
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = data.azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.container_app_identity.id
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_app_identity.id]
  }

  depends_on = [
    azurerm_role_assignment.container_app_acr_pull,
    azurerm_role_assignment.container_app_key_vault_secrets_user,
  ]
}

# =============================================================================
# Managed Identity & Role Assignments
# =============================================================================

resource "azurerm_user_assigned_identity" "container_app_identity" {
  name                = local.names.identity
  location            = data.azurerm_resource_group.main_rg.location
  resource_group_name = data.azurerm_resource_group.main_rg.name
  tags                = local.common_tags
}

resource "azurerm_role_assignment" "container_app_acr_pull" {
  scope                = data.azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_app_identity.principal_id
}

resource "azurerm_role_assignment" "container_app_key_vault_secrets_user" {
  scope                = data.azurerm_key_vault.shared_key_vault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.container_app_identity.principal_id
}

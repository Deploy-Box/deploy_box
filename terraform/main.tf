terraform {
  backend "azurerm" {
    use_oidc = true
  }
}

provider "azurerm" {
  features {}
  use_oidc = true
}

data "azurerm_client_config" "current" {}

data "azurerm_container_registry" "acr" {
  name                = "deployboxcr${var.environment}"
  resource_group_name = "deploy-box-rg-${var.environment}"
}

data "azurerm_container_app_environment" "shared_container_env" {
  name                = "deploy-box-cae-${var.environment}"
  resource_group_name = "deploy-box-shared-resources-rg-${var.environment}"
}

data "azurerm_key_vault" "shared_key_vault" {
  name                = "deploy-box-kv-${var.environment}"
  resource_group_name = "deploy-box-shared-resources-rg-${var.environment}"
}

resource "azurerm_resource_group" "main_rg" {
  location = var.azure_location
  name     = "deploy-box-rg-${var.environment}"

  tags = {
    ManagedBy = "Terraform"
  }
}

resource "azurerm_container_app" "container_app" {
  name                         = "deploy-box-contapp-${var.environment}"
  resource_group_name          = azurerm_resource_group.main_rg.name
  revision_mode                = "Single"
  container_app_environment_id = data.azurerm_container_app_environment.shared_container_env.id

  template {
    container {
      name   = "deploy-box-container"
      image  = var.image_name
      cpu    = 0.25
      memory = "0.5Gi"
      env {
        name  = "ENV"
        value = upper(var.environment)
      }
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
      env {
        name  = "HOST"
        value = var.host
      }
      env {
        name  = "OAUTH2_PASSWORD_CREDENTIALS_CLIENT_ID"
        value = var.oauth2_password_credentials_client_id
      }
      env {
        name  = "OAUTH2_AUTH_CODE_CLIENT_ID"
        value = var.oauth2_auth_code_client_id
      }
      env {
        name  = "DB_NAME"
        value = var.db_name
      }
      env {
        name  = "DB_USER"
        value = var.db_user
      }
      env {
        name  = "DB_HOST"
        value = var.db_host
      }
      env {
        name  = "DB_PORT"
        value = var.db_port
      }
      env {
        name  = "DEPLOY_BOX_STACK_ENDPOINT"
        value = var.deploy_box_stack_endpoint
      }
      env {
        name  = "EMAIL_HOST_USER"
        value = var.email_host_user
      }
      env {
        name  = "DEPLOY_BOX_GITHUB_CLIENT_ID"
        value = var.deploy_box_github_client_id
      }
      env {
        name  = "NPM_BIN_PATH"
        value = var.npm_bin_path
      }
      env {
        name  = "KEY_VAULT_NAME"
        value = var.key_vault_name
      }
      env {
        name  = "AZURE_FUNCTION_URL"
        value = var.azure_function_url
      }
      env {
        name  = "DEPLOY_BOX_API_BASE_URL"
        value = var.deploy_box_api_base_url
      }
    }

    min_replicas = 0
    max_replicas = 1
  }
  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"
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
    azurerm_role_assignment.container_app_key_vault_secrets_user
  ]
}

resource "azurerm_user_assigned_identity" "container_app_identity" {
  location            = azurerm_resource_group.main_rg.location
  name                = "deploy-box-container-app-identity-${var.environment}"
  resource_group_name = azurerm_resource_group.main_rg.name
  depends_on = [
    azurerm_resource_group.main_rg
  ]

  tags = {
    ManagedBy = "Terraform"
  }
}

resource "azurerm_role_assignment" "container_app_acr_pull" {
  scope                = data.azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_app_identity.principal_id

  depends_on = [
    azurerm_user_assigned_identity.container_app_identity,
    data.azurerm_container_registry.acr
  ]
}

resource "azurerm_role_assignment" "container_app_key_vault_secrets_user" {
  scope                = data.azurerm_key_vault.shared_key_vault.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.container_app_identity.principal_id

  depends_on = [
    azurerm_user_assigned_identity.container_app_identity,
    data.azurerm_key_vault.shared_key_vault
  ]
}

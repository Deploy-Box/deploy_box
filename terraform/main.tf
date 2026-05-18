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
    resource_group   = "${local.prefix}-rg-${local.env}"
    container_app    = "${local.prefix}-website-contapp-${local.env}"
    app_service_plan = "${local.prefix}-website-asp-${local.env}"
    web_app          = "${local.prefix}-website-app-${local.env}"
    identity         = "${local.prefix}-website-contapp-identity-${local.env}"
    acr              = "${local.prefix_compact}cr${local.env}"
    cae              = "${local.prefix}-cae-${local.env}"
    key_vault        = "${local.prefix}-kv-${local.env}"
    sbns             = "${local.prefix}-sbns-${local.env}"
  }

  web_app_port            = "8000"
  web_app_startup_command = "python manage.py collectstatic --noinput && gunicorn --bind=0.0.0.0:${local.web_app_port} --timeout 600 core.wsgi:application"

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

data "azurerm_key_vault_secret" "db_password" {
  name         = "deploy-box-website-db-password"
  key_vault_id = data.azurerm_key_vault.shared_key_vault.id
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
        name  = "DJANGO_SETTINGS_MODULE"
        value = var.app.django_settings_module
      }
      env {
        name  = "ENV"
        value = upper(local.env)
      }
      env {
        name  = "HOST"
        value = var.app.host
      }
      env {
        name  = "BASE_DOMAIN"
        value = var.app.base_domain
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
      env {
        name  = "WORKOS_CLIENT_ID"
        value = var.auth.workos_client_id
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
      env {
        name  = "DB_PASSWORD"
        value = data.azurerm_key_vault_secret.db_password.value
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
        name  = "NPM_BIN_PATH"
        value = var.services.npm_bin_path
      }
      env {
        name  = "KEY_VAULT_NAME"
        value = local.names.key_vault
      }
      env {
        name  = "AZURE_SERVICE_BUS_CONNECTION_STRING"
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
# App Service Web App (parallel migration target)
# =============================================================================

resource "azurerm_service_plan" "website" {
  name                = local.names.app_service_plan
  location            = data.azurerm_resource_group.main_rg.location
  resource_group_name = data.azurerm_resource_group.main_rg.name
  os_type             = "Linux"
  sku_name            = var.app_service_plan_sku
  tags                = local.common_tags
}

resource "azurerm_linux_web_app" "website" {
  name                = local.names.web_app
  location            = data.azurerm_resource_group.main_rg.location
  resource_group_name = data.azurerm_resource_group.main_rg.name
  service_plan_id     = azurerm_service_plan.website.id
  https_only          = true
  tags                = local.common_tags

  app_settings = {
    # --- App Service build/runtime ---
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true"
    ENABLE_ORYX_BUILD              = "true"
    PORT                           = local.web_app_port

    # --- Core ---
    DJANGO_SETTINGS_MODULE = var.app.django_settings_module
    ENV                    = upper(local.env)
    HOST                   = var.app.host
    BASE_DOMAIN            = var.app.base_domain

    # --- Azure identity ---
    AZURE_CLIENT_ID       = azurerm_user_assigned_identity.container_app_identity.client_id
    AZURE_TENANT_ID       = data.azurerm_client_config.current.tenant_id
    AZURE_SUBSCRIPTION_ID = data.azurerm_client_config.current.subscription_id

    # --- Auth / OAuth2 ---
    OAUTH2_PASSWORD_CREDENTIALS_CLIENT_ID = var.auth.oauth2_password_credentials_client_id
    OAUTH2_AUTH_CODE_CLIENT_ID            = var.auth.oauth2_auth_code_client_id
    DEPLOY_BOX_GITHUB_CLIENT_ID           = var.auth.github_client_id
    WORKOS_CLIENT_ID                      = var.auth.workos_client_id

    # --- Database ---
    DB_NAME     = var.database.name
    DB_USER     = var.database.user
    DB_HOST     = var.database.host
    DB_PORT     = var.database.port
    DB_PASSWORD = data.azurerm_key_vault_secret.db_password.value

    # --- External services ---
    DEPLOY_BOX_STACK_ENDPOINT           = var.services.stack_endpoint
    EMAIL_HOST_USER                     = var.services.email_host_user
    DEPLOY_BOX_API_BASE_URL             = var.services.api_base_url
    NPM_BIN_PATH                        = var.services.npm_bin_path
    KEY_VAULT_NAME                      = local.names.key_vault
    AZURE_SERVICE_BUS_CONNECTION_STRING = data.azurerm_servicebus_namespace.service_bus.default_primary_connection_string
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_app_identity.id]
  }

  site_config {
    always_on        = true
    app_command_line = local.web_app_startup_command
    ftps_state       = "Disabled"

    application_stack {
      python_version = var.app_service_python_version
    }
  }

  depends_on = [
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

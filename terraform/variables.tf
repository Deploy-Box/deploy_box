variable "acr_name" {
  description = "Name of the Azure Container Registry"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group for deployed resources"
  type        = string
}

variable "azure_location" {
  description = "Azure region for resource deployment"
  type        = string
}

variable "image_name" {
  description = "Name of the image to be deployed"
  type        = string
}

variable "environment" {
  description = "Deployment environment suffix used in resource names (e.g., dev, test, prod)"
  type        = string
}

variable "host" {
  description = "HOST environment variable for the container app."
  type        = string
}

variable "oauth2_password_credentials_client_id" {
  description = "OAUTH2_PASSWORD_CREDENTIALS_CLIENT_ID for the app."
  type        = string
}

variable "oauth2_auth_code_client_id" {
  description = "OAUTH2_AUTH_CODE_CLIENT_ID for the app."
  type        = string
}

variable "db_name" {
  description = "DB_NAME for the app."
  type        = string
}

variable "db_user" {
  description = "DB_USER for the app."
  type        = string
}

variable "db_host" {
  description = "DB_HOST for the app."
  type        = string
}

variable "db_port" {
  description = "DB_PORT for the app."
  type        = string
  default     = "5432"
}

variable "deploy_box_stack_endpoint" {
  description = "DEPLOY_BOX_STACK_ENDPOINT for the app."
  type        = string
}

variable "email_host_user" {
  description = "EMAIL_HOST_USER for the app."
  type        = string
}

variable "deploy_box_github_client_id" {
  description = "DEPLOY_BOX_GITHUB_CLIENT_ID for the app."
  type        = string
}

variable "npm_bin_path" {
  description = "NPM_BIN_PATH for the app."
  type        = string
}

variable "key_vault_name" {
  description = "KEY_VAULT_NAME for the app."
  type        = string
}

variable "azure_function_url" {
  description = "AZURE_FUNCTION_URL for the app."
  type        = string
}

variable "deploy_box_api_base_url" {
  description = "DEPLOY_BOX_API_BASE_URL for the app."
  type        = string
}

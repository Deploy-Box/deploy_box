# =============================================================================
# Core application configuration
# =============================================================================

variable "app" {
  description = "Core application settings: environment, region, container image, and public hostname."
  type = object({
    environment = string
    location    = string
    image_name  = string
    host        = string
  })

  validation {
    condition     = contains(["dev", "test", "prod"], var.app.environment)
    error_message = "app.environment must be one of: dev, test, prod."
  }
}

# =============================================================================
# Authentication / OAuth2
# =============================================================================

variable "auth" {
  description = "OAuth2 and GitHub OAuth client IDs."
  sensitive   = true
  type = object({
    oauth2_password_credentials_client_id = string
    oauth2_auth_code_client_id            = string
    github_client_id                      = string
  })
}

# =============================================================================
# Database connection
# =============================================================================

variable "database" {
  description = "PostgreSQL connection parameters."
  type = object({
    name = string
    user = string
    host = string
    port = optional(string, "5432")
  })

  validation {
    condition     = can(regex("^[0-9]+$", var.database.port))
    error_message = "database.port must be a numeric string."
  }
}

# =============================================================================
# External service endpoints & integrations
# =============================================================================

variable "services" {
  description = "Endpoints and config for external services consumed by the app."
  type = object({
    stack_endpoint     = string
    email_host_user    = string
    azure_function_url = string
    api_base_url       = string
    npm_bin_path       = string
  })
}

# =============================================================================
# Tags (optional overrides merged with computed defaults)
# =============================================================================

variable "extra_tags" {
  description = "Additional tags to merge onto every resource."
  type        = map(string)
  default     = {}
}

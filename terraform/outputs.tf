output "app_host" {
  value = var.app["host"]
  description = "The host URL for the app environment."
}

output "key_vault_name" {
  value = local.names.key_vault
  description = "The name of the Key Vault for the app environment."
}

output "database_name" {
  value       = var.database["name"]
  description = "The name of the database."
}

output "database_port" {
  value       = var.database["port"]
  description = "The port the database is listening on."
}

output "database_host" {
  value       = var.database["host"]
  description = "The host URL for the database."
}

output "database_user" {
  value       = var.database["user"]
  description = "The username for the database."
}

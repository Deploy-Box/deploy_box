output "app_host" {
  value       = var.app["host"]
  description = "The host URL for the app environment."
}

output "resource_group_name" {
  value       = data.azurerm_resource_group.main_rg.name
  description = "The resource group that contains the app resources."
}

output "web_app_name" {
  value       = azurerm_linux_web_app.website.name
  description = "The code-based Azure Linux Web App name."
}

output "web_app_default_hostname" {
  value       = azurerm_linux_web_app.website.default_hostname
  description = "The default azurewebsites.net hostname for validating the Web App before DNS cutover."
}

output "key_vault_name" {
  value       = local.names.key_vault
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

output "app_host" {
  value = var.app["host"]
  description = "The host URL for the app environment."
}

output "key_vault_name" {
  value = local.names.key_vault
  description = "The name of the Key Vault for the app environment."
}
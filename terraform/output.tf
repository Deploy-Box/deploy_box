output "container_app_identity_client_id" {
  description = "The client ID of the user-assigned managed identity for the container app"
  value       = azurerm_user_assigned_identity.container_app_identity.client_id
}

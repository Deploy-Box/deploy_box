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

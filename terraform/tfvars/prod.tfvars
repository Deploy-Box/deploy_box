# =============================================================================
# Prod environment — secrets and image_name injected via CI / Terraform Cloud
# =============================================================================

app = {
  environment = "prod"
  location    = "eastus"
  image_name  = ""          # set by CI at apply-time via -var
  host        = ""          # set by CI or Terraform Cloud variable set
}

# auth, database, and services blocks are provided via
# Terraform Cloud variable sets or CI -var flags (never committed).
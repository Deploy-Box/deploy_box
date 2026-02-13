app = {
  environment = "dev"
  location    = "eastus"
  host        = "https://dev.deploy-box.com"
}

auth = {
  oauth2_password_credentials_client_id = "G5uGZZZnMojr0pRo4MiZDr6FLjkRxk2PrkuR3Ymd"
  oauth2_auth_code_client_id            = "R5nrUKC0JQnAhoaM5jExJb5USgftZahkeitEXOsV"
  github_client_id                      = "Ov23liehxn12PYLCJG5c"
}

database = {
  name = "deploy_box_dev"
  user = "kalebwbishop"
  host = "deploy-box-postgres.postgres.database.azure.com"
  port = "5432"
}

services = {
  stack_endpoint     = "https://deployboxsharedsadev.blob.core.windows.net/stack-source-code-container"
  email_host_user    = "noreplydeploybbox@gmail.com"
  azure_function_url = "https://deploy-box-iac-contapp-dev.internal.agreeablesky-c9998b70.eastus2.azurecontainerapps.io/iac/v1"
  api_base_url       = "http://deploy-box-apis-func-dev.azurewebsites.net"
  npm_bin_path       = "C:\\Program Files\\nodejs\\npm.cmd"
}
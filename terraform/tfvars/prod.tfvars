app = {
  environment            = "prod"
  location               = "eastus"
  host                   = "https://www.deploy-box.com"
  django_settings_module = "core.settings.dev" # Override to use dev settings for prod deployment
}

auth = {
  oauth2_password_credentials_client_id = "G5uGZZZnMojr0pRo4MiZDr6FLjkRxk2PrkuR3Ymd"
  oauth2_auth_code_client_id            = "R5nrUKC0JQnAhoaM5jExJb5USgftZahkeitEXOsV"
  github_client_id                      = "Ov23liehxn12PYLCJG5c"
  workos_client_id                      = "client_01KHR6E4TF92DDY76R09658TFY"
}

database = {
  name = "deploy_box_prod"
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
app = {
  environment            = "test"
  location               = "eastus"
  host                   = "https://test.deploy-box.com"
  django_settings_module = "core.settings.dev"
  base_domain            = "test.deploy-box.com"
}

auth = {
  oauth2_password_credentials_client_id = ""
  oauth2_auth_code_client_id            = ""
  github_client_id                      = ""
  workos_client_id                      = ""
}

database = {
  name = "deploy_box_test"
  user = "deploy_box_website"
  host = "deploy-box-postgres.postgres.database.azure.com"
  port = "5432"
}

services = {
  stack_endpoint     = ""
  email_host_user    = "noreplydeploybbox@gmail.com"
  api_base_url       = ""
  npm_bin_path       = "C:\\Program Files\\nodejs\\npm.cmd"
}

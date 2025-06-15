from Azure.main import AzureDeployBoxIAC
import requests
# Download the zip file from the GitHub repository
azure_deploy_box = AzureDeployBoxIAC()

# # Download the zip file from the GitHub repository
# response = requests.get("https://github.com/kalebwbishop/VBHS-music-manager/archive/refs/heads/main.zip")
# with open("./Azure/VBHS-music-manager-main.zip", "wb") as file:
#     file.write(response.content)


# azure_deploy_box.upload_zip_to_blob(
#     zip_file_path="./Azure/test.zip",
#     storage_account_url="https://deployboxsadev.blob.core.windows.net",
#     container_name="main",
#     blob_name="VBHS-music-manager-main.zip",
#     sas_token="sp=racwdli&st=2025-06-15T03:48:09Z&se=2025-06-15T11:48:09Z&sv=2024-11-04&sr=c&sig=I08PUxfUSJ3hih5MCgX9ip6eaaeH%2BqRGuhwEZ41I20w%3D"  # Replace with your actual SAS token
#     )


# Example usage
resource_group_name = "testing-mern-free"
environment_name = "testing-mern-free-cae"
app_name = "testing-mern-free-frontend"
image = "kalebwbishop/mern-pro-frontend:latest"
token = azure_deploy_box.access_token

azure_deploy_box.create_resource_group(resource_group_name)
azure_deploy_box.create_log_analytics_workspace(
    resource_group_name, "testing-mern-free-law"
)
workspace_id = azure_deploy_box.get_log_analytics_workspace_id(
    resource_group_name, "testing-mern-free-law"
)
workspace_key = azure_deploy_box.get_log_analytics_workspace_key(
    resource_group_name, "testing-mern-free-law"
)
azure_deploy_box.create_container_app_environment(
    resource_group_name, environment_name, workspace_id, workspace_key
)
run_id = azure_deploy_box.build_container_image(
    "myimage:latest",
)
# print("run id", run_id)
# azure_deploy_box.wait_for_build_completion(run_id)
# azure_deploy_box.deploy_container_app(
#     resource_group_name, environment_name, app_name, image
# )
import datetime
import requests
import time
import json

# from azure.storage.blob import BlobServiceClient


class AzureDeployBoxIAC:
    def __init__(self):
        """
        Initialize the AzureDeployBoxIAC class with Azure credentials.
        """
        client_id = ""
        client_secret = ""
        tenant_id = ""

        self.client_id = client_id
        self.client_secret = client_secret  # Store credentials as instance variables
        self.tenant_id = tenant_id
        self.subscription_id = "3106bb2d-2f28-445e-ab1e-79d93bd15979"
        self.location = "eastus"
        self.resource_group = "deploy-box-rg-dev"
        self.regestry_name = "deployboxcrdev"

        self.access_token = self.get_azure_token()

    def get_azure_token(self):
        """
        Get an Azure access token using client credentials.

        Returns:
            str: Access token if successful, None otherwise.
        """
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://management.azure.com/.default",
        }

        response = requests.post(url, headers=headers, data=data)

        if response.status_code in [200, 201]:
            return response.json().get("access_token")

        return None

    def request_helper(self, url, method="GET", data=None):
        """
        Helper function to make requests to Azure API.

        Args:
            url (str): The URL for the request.
            method (str): HTTP method (GET, POST, PUT, DELETE).
            data (dict): Data to send in the request body.

        Returns:
            dict: JSON response from the API.
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError("Unsupported HTTP method")

        if response.status_code in [200, 201]:
            return response.json()

        print(f"Error: {response.status_code} - {response.text}")
        return None

    def get_provisioning_state(self, url):
        """
        Get the provisioning state of a resource in Azure.

        Args:
            resource_group_name (str): Name of the resource group.
            resource_name (str): Name of the resource.

        Returns:
            str: Provisioning state if found, None otherwise.
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)

        if response.status_code in [200, 201]:
            print("response", response.json())
            return response.json().get("properties", {}).get("provisioningState")

        print(f"Error getting provisioning state: {response.text}")
        return None

    def wait_for_provisioning(self, url):
        """
        Wait for the provisioning state of a resource to be 'Succeeded'.
        Args:
        Returns:
            bool: True if provisioning succeeded, False otherwise.
        """

        while True:
            state = self.get_provisioning_state(url)
            if state == "Succeeded":
                print("Provisioning succeeded.")
                return True
            elif state in ["Failed", "Canceled"]:
                print(f"Provisioning failed with state: {state}")
                return False
            else:
                print(f"Current provisioning state: {state}. Waiting...")
            time.sleep(10)  # Wait for 10 seconds before checking again

    def create_resource_group(self, resource_group_name):
        """
        Create an Azure resource group.

        Args:
            resource_group_name (str): Name of the resource group.
            location (str): Azure region for the resource group.

        Returns:
            dict: Response from the Azure API.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourcegroups/{resource_group_name}?api-version=2021-04-01"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "location": self.location,
        }

        response = requests.put(url, headers=headers, json=data)

        print(f"Creating Resource Group: {response.status_code}")
        if response.status_code != 200:
            print(f"Error creating Resource Group: {response.text}")
            return None

        return response.json()

    def create_log_analytics_workspace(self, resource_group_name, workspace_name):
        """
        Create an Azure Log Analytics workspace.

        Args:
            resource_group_name (str): Name of the resource group.
            workspace_name (str): Name of the Log Analytics workspace.

        Returns:
            dict: Response from the Azure API.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}?api-version=2020-08-01"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "location": self.location,
            "properties": {
                "sku": {"name": "PerGB2018"},
                "retentionInDays": 30,
            },
        }

        response = requests.put(url, headers=headers, json=data)

        print(f"Creating Log Analytics Workspace: {response.status_code}")
        if response.status_code != 200:
            print(f"Error creating Log Analytics Workspace: {response.text}")
            return None

        return response.json()

    def get_log_analytics_workspace_id(self, resource_group_name, workspace_name):
        """
        Get the ID of an Azure Log Analytics workspace.

        Args:
            resource_group_name (str): Name of the resource group.
            workspace_name (str): Name of the Log Analytics workspace.

        Returns:
            str: Workspace ID if found, None otherwise.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}?api-version=2020-08-01"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json().get("properties", {}).get("customerId")

        print(f"Error getting Log Analytics Workspace ID: {response.text}")
        return None

    def get_log_analytics_workspace_key(self, resource_group_name, workspace_name):
        """
        Get the primary key of an Azure Log Analytics workspace.

        Args:
            resource_group_name (str): Name of the resource group.
            workspace_name (str): Name of the Log Analytics workspace.

        Returns:
            str: Primary key if found, None otherwise.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}/sharedKeys?api-version=2020-08-01"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers)

        if response.status_code == 200:
            return response.json().get("primarySharedKey")

        print(f"Error getting Log Analytics Workspace Key: {response.text}")
        return None

    def create_container_app_environment(
        self, resource_group_name, environment_name, workspace_id, workspace_key
    ):
        """
        Create an Azure Container App environment.

        Args:
            resource_group_name (str): Name of the resource group.
            environment_name (str): Name of the container app environment.
            location (str): Azure region for the environment.

        Returns:
            dict: Response from the Azure API.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.App/managedEnvironments/{environment_name}?api-version=2022-03-01"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "location": self.location,
            "properties": {
                "appLogsConfiguration": {
                    "destination": "log-analytics",
                    "logAnalyticsConfiguration": {
                        "customerId": workspace_id,
                        "sharedKey": workspace_key,
                    },
                }
            },
        }

        response = requests.put(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"Error creating Container App Environment: {response.text}")
            return None
        print(f"Creating Container App Environment: {response.status_code}")

        # Wait for the provisioning to complete
        if not self.wait_for_provisioning(url):
            return None
        return response.json()

    def get_container_app_environment_id(self, resource_group_name, environment_name):
        """
        Get the ID of an Azure Container App environment.

        Args:
            resource_group_name (str): Name of the resource group.
            environment_name (str): Name of the container app environment.

        Returns:
            str: Environment ID if found, None otherwise.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.App/managedEnvironments/{environment_name}?api-version=2022-03-01"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json().get("id")

        print(f"Error getting Container App Environment ID: {response.text}")
        return None

    def upload_zip_to_blob(
        self, zip_file_path, storage_account_url, container_name, blob_name, sas_token
    ):
        """
        Upload a ZIP file to Azure Blob Storage.

        Args:
            zip_file_path (str): Path to the ZIP file.
            storage_account_url (str): URL to the Azure Storage account.
            container_name (str): Name of the container in Blob Storage.
            blob_name (str): Name of the blob to create.
            sas_token (str): Shared Access Signature token.

        Returns:
            str: URL to the uploaded blob.
        """
        blob_service_client = BlobServiceClient(
            account_url=storage_account_url, credential=sas_token
        )
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )

        with open(zip_file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        blob_url = f"{storage_account_url}/{container_name}/{blob_name}"
        print(f"Uploaded ZIP to: {blob_url}")
        return blob_url

    def build_container_image(self, image_name):
        """
        Build a Docker image using an Azure Container Registry task defined in a YAML file.

        Args:
            image_name (str): Name of the Docker image to build.

        Returns:
            str: The run ID of the queued build, or None if failed.
        """

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # ACR Task definition
        task_definition = {
            "location": "eastus",
            "properties": {
                "status": "Enabled",
                "platform": {"os": "Linux"},
                "agentConfiguration": {"cpu": 2},
                "step": {
                    "type": "Docker",
                    "contextPath": "https://github.com/Deploy-Box/MERN.git#main:source_code/backend",
                    "dockerFilePath": "Dockerfile",
                    "imageNames": ["mern-app:{{.Run.ID}}"],
                    "isPushEnabled": True,
                },
                "trigger": {
                    "sourceTriggers": [],
                    "baseImageTrigger": {
                        "type": "Runtime",
                        "baseImageTriggerType": "Runtime",
                        "name": "defaultBaseimageTrigger",
                        "status": "Disabled",
                    },
                    "timerTriggers": [],
                },
            },
        }

        task_name = "build-task-test"
        api_version = "2025-03-01-preview"

        # Create task
        create_url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}/"
            f"resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/"
            f"registries/{self.regestry_name}/tasks/{task_name}?api-version={api_version}"
        )

        response = requests.put(create_url, headers=headers, json=task_definition)
        print("Create Task Response:", response.status_code, response.json())

        # Run task
        run_definition = {
            "type": "TaskRunRequest",
            "taskId": f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/registries/{self.regestry_name}/tasks/{task_name}",
        }

        run_url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}/"
            f"resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/"
            f"registries/{self.regestry_name}/scheduleRun?api-version={api_version}"
        )

        run_response = requests.post(run_url, headers=headers, json=run_definition)

        return run_response.json().get("properties", {}).get("runId")

    def wait_for_build_completion(self, run_id):
        """
        Wait for the Docker build to complete.

        Args:
            run_id (str): The ID of the build run.

        Returns:
            bool: True if the build succeeded, False otherwise.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/registries/{self.regestry_name}/runs/{run_id}?api-version=2019-06-01-preview"

        while True:
            response = self.request_helper(url)
            print("wait response", response)
            if response is None:
                print("Error: No response received while checking build status.")
                time.sleep(10)
                continue
            properties = response.get("properties", {})
            print(response)
            if properties.get("status") == "Succeeded":
                print("Build completed successfully.")
                return True
            elif properties.get("status") in ["Failed", "Canceled"]:
                print(f"Build failed with status: {properties.get('status')}")
                return False
            else:
                status = properties.get("status")
                print(f"Build is in progress... Current status: {status}")
                time.sleep(10)

    def deploy_container_app(
        self, resource_group_name, environment_name, app_name, image
    ):
        """
        Deploy an Azure Container App.

        Args:
            resource_group_name (str): Name of the resource group.
            environment_name (str): Name of the container app environment.
            app_name (str): Name of the container app.
            image (str): Docker image to deploy.

        Returns:
            dict: Response from the Azure API.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.App/containerApps/{app_name}?api-version=2022-03-01"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "location": self.location,
            "properties": {
                "managedEnvironmentId": f"/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.App/managedEnvironments/{environment_name}",
                "configuration": {
                    "ingress": {
                        "external": True,
                        "targetPort": 5000,
                        "transport": "auto",
                    },
                    "secrets": [
                        {
                            "name": "acr-password",
                            "value": "",
                        }
                    ],
                    "registries": [
                        {
                            "server": "deployboxcrdev.azurecr.io",
                            "username": self.regestry_name,
                            "passwordSecretRef": "acr-password",
                        }
                    ],
                },
                "template": {
                    "containers": [
                        {
                            "name": app_name,
                            "image": image,
                            "resources": {"cpu": 0.25, "memory": "0.5Gi"},
                            "env": [
                                {
                                    "name": "MONGO_URI",
                                    "value": "mongodb+srv://deployBoxUser-b61c956f6f634710:O5IIWezIuphA1xSa@cluster0.yjaoi.mongodb.net/db-b61c956f6f634710?retryWrites=true&w=majority&appName=Cluster0",
                                },
                            ],
                        }
                    ]
                },
            },
        }

        response = requests.put(url, headers=headers, json=data)

        print(f"Deploying Container App: {response.status_code}")
        if response.status_code not in [200, 201]:
            print(f"Error deploying Container App: {response.text}")
            return None

        # Wait for the provisioning to complete
        if not self.wait_for_provisioning(url):
            return None

        return response.json()

    def post_build_and_deploy(
        self, resource_group_name, environment_name, workspace_name, app_name, image
    ):
        """
        Orchestrates the Azure deployment steps after a build.

        Args:
            resource_group_name (str): Name of the resource group.
            environment_name (str): Name of the container app environment.
            workspace_name (str): Name of the Log Analytics workspace.
            app_name (str): Name of the container app.
            image (str): Docker image to deploy.

        Returns:
            dict: Deployment result or None if any step fails.
        """
        print("Starting Azure post-build deployment...")

        # Step 1: Create Resource Group
        if not self.create_resource_group(resource_group_name):
            print("Failed to create resource group.")
            return None

        # Step 2: Create Log Analytics Workspace
        if not self.create_log_analytics_workspace(resource_group_name, workspace_name):
            print("Failed to create Log Analytics workspace.")
            return None

        # Step 3: Get Workspace ID and Key
        workspace_id = self.get_log_analytics_workspace_id(
            resource_group_name, workspace_name
        )
        workspace_key = self.get_log_analytics_workspace_key(
            resource_group_name, workspace_name
        )
        if not workspace_id or not workspace_key:
            print("Failed to retrieve workspace credentials.")
            return None

        # Step 4: Create Container App Environment
        if not self.create_container_app_environment(
            resource_group_name, environment_name, workspace_id, workspace_key
        ):
            print("Failed to create container app environment.")
            return None

        # Step 5: Deploy Container App
        result = self.deploy_container_app(
            resource_group_name, environment_name, app_name, image
        )
        if not result:
            print("Failed to deploy container app.")
            return None

        print("Azure deployment completed successfully.")
        return result

    def get_resource_group_usage(self, subscription_id, resource_group_name, token):
        """
        Get the usage data for a specific Azure Container App.

        Args:
            subscription_id (str): Azure subscription ID.
            resource_group_name (str): Name of the resource group.
            app_name (str): Name of the container app.
            token (str): Azure access token.

        Returns:
            dict: Usage data if successful, None otherwise.
        """
        url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/query?api-version=2023-03-01"

        body = {
            "type": "ActualCost",
            "timeframe": "MonthToDate",
            "dataset": {
                "granularity": "Daily",
                "aggregation": {"totalCost": {"name": "PreTaxCost", "function": "Sum"}},
                "filter": {
                    "dimensions": {
                        "name": "resourceGroupName",
                        "operator": "In",
                        "values": [resource_group_name],
                    }
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            return response.json()

        print(f"Error getting container app usage: {response.text}")
        return None

    def add_container_app_envs_as_secrets(
        self, resource_group_name, app_name, env_vars: dict, container_name=None
    ):
        """
        Adds/updates secrets in an Azure Container App and links them as environment variables using secretRef,
        waiting for provisioning to complete between steps.
        """
        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/"
            f"{resource_group_name}/providers/Microsoft.App/containerApps/{app_name}?api-version=2022-03-01"
        )
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # Step 1: Fetch current app definition
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching container app: {response.text}")
            return None
        app_def = response.json()

        # Step 2: Merge new secrets with existing ones
        config = app_def["properties"].setdefault("configuration", {})
        existing_secrets = {s["name"]: s for s in config.get("secrets", [])}
        for key, value in env_vars.items():
            existing_secrets[key] = {"name": key, "value": value}
        config["secrets"] = list(existing_secrets.values())

        # Step 3: PUT updated secrets
        put_response = requests.put(url, headers=headers, json=app_def)
        if put_response.status_code not in [200, 201]:
            print(f"Error updating app secrets: {put_response.text}")
            return None
        print("Secrets added. Waiting for provisioning to complete...")
        print("put response", json.dumps(put_response.json(), indent=2))

        # Step 4: Wait for provisioning to complete
        self.wait_for_provisioning(url)

        # Step 5: Wait until secrets are visible in GET response
        max_retries = 12  # Wait up to 2 minutes (12 * 10s)
        for attempt in range(max_retries):
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(
                    f"Error fetching container app after secrets update: {response.text}"
                )
                return None
            app_def = response.json()
            config = app_def["properties"].get("configuration", {})
            current_secrets = {s["name"] for s in config.get("secrets", [])}
            if all(key in current_secrets for key in env_vars):
                print("Secrets are now present in the app definition.")
                break
            print("Secrets not yet present in app definition. Waiting...")
            time.sleep(10)
        else:
            print("Timed out waiting for secrets to appear in app definition.")
            return None

        # Step 6: Add secretRef envs to the container
        containers = app_def["properties"]["template"]["containers"]
        updated = False
        for container in containers:
            if container_name is None or container["name"] == container_name:
                # Remove any old env entries with the same name
                env_list = [
                    e
                    for e in container.get("env", [])
                    if e["name"] not in [k.upper().replace("-", "_") for k in env_vars]
                ]
                # Add new secretRef env entries
                for key in env_vars:
                    env_list.append(
                        {"name": key.upper().replace("-", "_"), "secretRef": key}
                    )
                container["env"] = env_list
                updated = True
                break

        if not updated:
            print(f"Container '{container_name}' not found.")
            return None

        # Step 7: Ensure secrets have values before PUT
        # Always include the values for the secrets you want to keep
        config = app_def["properties"].setdefault("configuration", {})
        existing_secrets = {s["name"]: s for s in config.get("secrets", [])}
        for key, value in env_vars.items():
            existing_secrets[key] = {"name": key, "value": value}
        config["secrets"] = list(existing_secrets.values())

        # Now PUT updated envs and secrets
        put_response = requests.put(url, headers=headers, json=app_def)
        if put_response.status_code not in [200, 201]:
            print(f"Error updating app envs: {put_response.text}")
            return None

        print("Secrets linked to container environment successfully.")
        return put_response.json()


if __name__ == "__main__":
    azure_deploy_box = AzureDeployBoxIAC()

    # Example usage
    resource_group_name = "testing-mern-free4"
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
    # run_id = azure_deploy_box.build_container_image(
    #     "kalebwbishop/VBHS:latest",
    # )
    # print("run id", run_id)
    # azure_deploy_box.wait_for_build_completion(run_id)
    run_id = "ca2n"
    azure_deploy_box.deploy_container_app(
        resource_group_name,
        environment_name,
        app_name,
        f"{azure_deploy_box.regestry_name}.azurecr.io/mern-app:{run_id}",
    )

    # usage_data = azure_deploy_box.get_resource_group_usage(
    #     azure_deploy_box.subscription_id, resource_group_name, token
    # )

    # print("Usage Data:", usage_data)

    # # Example of updating environment variables
    # env_vars = {
    #     "node-env": "production_again",
    #     "api-url": "https://api.example.com",
    # }

    # # azure_deploy_box.put_service_envs(
    # azure_deploy_box.add_container_app_envs_as_secrets(
    #     resource_group_name,
    #     app_name,
    #     env_vars,
    #     container_name="testing-mern-free-frontend",
    # )

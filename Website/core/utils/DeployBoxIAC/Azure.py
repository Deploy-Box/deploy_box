import os
import dotenv
import requests
import time
import re

dotenv.load_dotenv()

PROVIDER_NAME = "azurerm"


class AzureDeployBoxIAC:
    api_version = "2025-03-01-preview"

    def __init__(self):
        """
        Initialize the AzureDeployBoxIAC class with Azure credentials.
        """
        self.client_id = os.getenv("ARM_CLIENT_ID")
        self.client_secret = os.getenv("ARM_CLIENT_SECRET")
        self.tenant_id = os.getenv("ARM_TENANT_ID")
        self.subscription_id = os.getenv("ARM_SUBSCRIPTION_ID")
        self.location = "eastus"
        self.resource_group = "deploy-box-rg-dev"
        self.registry_name = "deployboxcrdev"

        self.state = {}

        self.access_token = self.get_azure_token()

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def plan(self, terraform: dict, deploy_box_iac: dict, state: dict):
        self.state = state.setdefault("azure", {})

        provider = terraform.get("provider", {})
        assert isinstance(provider, dict)

        resource = terraform.get("resource", {})
        assert isinstance(resource, dict)

        provider.update(
            {
                PROVIDER_NAME: {
                    "features": {},
                    "subscription_id": os.getenv("ARM_SUBSCRIPTION_ID"),
                    "client_id": os.getenv("ARM_CLIENT_ID"),
                    "client_secret": os.getenv("ARM_CLIENT_SECRET"),
                    "tenant_id": os.getenv("ARM_TENANT_ID"),
                }
            }
        )

        azure_deploy_box_iac = {
            k: v for k, v in deploy_box_iac.items() if k.startswith(PROVIDER_NAME)
        }

        azure_deploy_box_iac = self.build_container_image(azure_deploy_box_iac)

        resource.update(azure_deploy_box_iac)

        return {"provider": provider, "resource": resource}

    # def apply(self):
    #     pass

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

    def check_for_updates(self, context_directory: str, context_path) -> bool:
        """
        Check if updates have been made to the specified context path in the repository.

        Args:
            context_directory (str): The directory within the repository to check.
            context_path (str): The full path to the repository including branch.

        Returns:
            bool: True if updates are found, False otherwise.
        """
        result = re.match(r"https:\/\/github\.com\/(.+)\/(.+)\.git#(.+)", context_path)
        if not result:
            print("Invalid context path format.")
            return False

        owner, repo, _ = result.groups()
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits?path={context_directory}"
        )
        if response.status_code != 200:
            print(f"Error fetching commits: {response.status_code} - {response.text}")
            return False

        print(f"Response: {response.json()}")

        if self.state.get(f"{context_path}/{context_directory}-sha") == response.json()[
            0
        ].get("sha"):
            print("No updates found since the last check.")
            return False

        # Update the state with the latest commit SHA
        self.state[f"{context_path}/{context_directory}-sha"] = response.json()[0].get(
            "sha"
        )
        print("Updates found in the specified path.")
        return True


    def build_container_image(self, azure_deploy_box_iac: dict) -> dict:
        """ """

        def build_container_image_helper(task: dict) -> str:
            task_name = f"build-task-{int(time.time())}"  # Unique task name
            print(task)

            assert (
                isinstance(task, dict) and "contextDirectory" in task.keys()
            ), "contextDirectory is required"

            context_directory = task.pop("contextDirectory")
            context_path = task.get("contextPath")

            if not context_path:
                raise ValueError("contextPath is required in the step definition")

            # Parse GitHub URL to get repo info
            result = re.match(
                r"https:\/\/github\.com\/(.+)\/(.+)\.git(?:#(.+))?", context_path
            )
            if not result:
                raise ValueError("Invalid GitHub repository URL format")

            owner, repo, branch = result.groups()
            branch = branch or "main"
            repo_url = f"https://github.com/{owner}/{repo}#{branch}:{context_directory}"

            # Create task configuration for private repo
            task_config = {
                "location": self.location,
                "properties": {
                    "status": "Enabled",
                    "platform": {"os": "Linux", "architecture": "amd64"},
                    "agentConfiguration": {"cpu": 2},
                    "step": {
                        "type": "Docker",
                        "dockerFilePath": task.get("dockerFilePath", "Dockerfile"),
                        "contextPath": repo_url,
                        "contextAccessToken": task.get("contextAccessToken"),  # GitHub token for private repo access
                        "imageNames": task.get("imageNames", []),
                        "isPushEnabled": True,
                        "noCache": False,
                        "arguments": task.get("arguments", []),
                    },
                },
            }

            print(task_config)

            # Create task
            create_url = (
                f"https://management.azure.com/subscriptions/{self.subscription_id}/"
                f"resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/"
                f"registries/{self.registry_name}/tasks/{task_name}?api-version={AzureDeployBoxIAC.api_version}"
            )

            response = requests.put(create_url, headers=self.headers, json=task_config)

            if response.status_code not in [200, 201]:
                raise Exception(
                    f"Failed to create task: {response.status_code} - {response.text}"
                )

            print("Task created successfully:", response.json())

            # Run task manually
            run_definition = {
                "type": "TaskRunRequest",
                "taskId": f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/registries/{self.registry_name}/tasks/{task_name}",
                "values": [
                    {
                        "name": "sourceLocation",
                        "value": f"{repo_url}#{branch}:{context_directory}",
                    }
                ],
            }

            run_url = (
                f"https://management.azure.com/subscriptions/{self.subscription_id}/"
                f"resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/"
                f"registries/{self.registry_name}/scheduleRun?api-version={AzureDeployBoxIAC.api_version}"
            )

            run_response = requests.post(
                run_url, headers=self.headers, json=run_definition
            )

            if run_response.status_code not in [200, 201]:
                raise Exception(
                    f"Failed to run task: {run_response.status_code} - {run_response.text}"
                )

            return run_response.json().get("properties", {}).get("runId")

        # Find all `task` definitions
        for app in azure_deploy_box_iac.get("azurerm_container_app", {}).values():
            containers = app.get("template", {}).get("container", [])
            for container in containers:
                image = container.get("image")

                if not isinstance(image, dict):
                    continue

                task = image.get("task")
                if task:
                    run_id = (
                        f"{build_container_image_helper(task=task)}"
                    )
                    image = self.wait_for_build_completion(run_id)
                    container.update({"image": image})

        return azure_deploy_box_iac

    def wait_for_build_completion(self, run_id):
        """
        Wait for the Docker build to complete.

        Args:
            run_id (str): The ID of the build run.

        Returns:
            bool: True if the build succeeded, False otherwise.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/registries/{self.registry_name}/runs/{run_id}?api-version=2019-06-01-preview"

        while True:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(
                    f"Error checking build status: {response.status_code} - {response.text}"
                )
                return
            response = response.json()
            print("wait response", response)
            if response is None:
                print("Error: No response received while checking build status.")
                time.sleep(10)
                continue
            properties = response.get("properties", {})
            print(response)
            if properties.get("status") == "Succeeded":
                print("Build completed successfully.")
                output_image = properties.get("outputImages", [{}])[0]
                return f"{output_image.get('registry')}/{output_image.get('repository')}:latest"
            elif properties.get("status") in ["Failed", "Canceled"]:
                print(f"Build failed with status: {properties.get('status')}")
                return
            else:
                status = properties.get("status")
                print(f"Build is in progress... Current status: {status}")
                time.sleep(10)

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

    def delete_resource_group(self, resource_group_name):
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}?api-version=2023-03-01"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        print(f"Error deleting resource group: {response.text}")
        return None

    def add_container_app_envs_as_secrets(
        self, iac, app_name, env_vars: dict, container_name=None
    ):
        secrets = (
            iac.get("azurerm_container_app", {}).get(app_name, {}).get("secret", [])
        )
        config = (
            iac.get("azurerm_container_app", {})
            .get(app_name, {})
            .get("template", {})
            .get("container", [{}])[0]
            .setdefault("env", [])
        )

        for key, value in env_vars.items():
            secret_key = key.lower().replace("_", "-")
            # Check if the secret already exists
            existing_secret = next(
                (s for s in secrets if s["name"] == secret_key), None
            )
            if existing_secret:
                # Update the existing secret value
                existing_secret["value"] = value
            else:
                # Add a new secret
                secrets.append(
                    {
                        "name": key.lower().replace("_", "-"),
                        "value": value,
                    }
                )

            env_entry = {
                "name": key,
                "secret_name": secret_key,
            }

            # Find the index of the existing env variable
            index = next((i for i, e in enumerate(config) if e["name"] == key), None)

            if index is not None:
                config[index] = env_entry  # Replace the existing entry
            else:
                config.append(env_entry)  # Add new entry

        return True

import os
import dotenv
import requests
import time
import json

dotenv.load_dotenv()

PROVIDER_NAME = "azurerm"

class AzureDeployBoxIAC:
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
        self.regestry_name = "deployboxcrdev"

        self.state = {}

        self.access_token = self.get_azure_token()

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def plan(self, terraform: dict, deploy_box_IAC: dict, state: dict) -> dict:
        self.state = state

        provider = terraform.get("provider", {})
        assert isinstance(provider, dict)

        resource = terraform.get("resource", {})
        assert isinstance(resource, dict)

        provider.update({PROVIDER_NAME: {
            "features": {},
            "subscription_id": os.getenv("ARM_SUBSCRIPTION_ID"),
            "client_id": os.getenv("ARM_CLIENT_ID"),
            "client_secret": os.getenv("ARM_CLIENT_SECRET"),
            "tenant_id": os.getenv("ARM_TENANT_ID")
        }})

        azure_deploy_box_IAC = {k: v for k, v in deploy_box_IAC.items() if k.startswith(PROVIDER_NAME)}

        azure_deploy_box_IAC = self.build_container_image(azure_deploy_box_IAC)

        resource.update(azure_deploy_box_IAC)
        
        return {
            "provider": provider,
            "resource": resource
        }
    
    def apply(self):
        pass

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

    def get_provisioning_state(self, url):
        """
        Get the provisioning state of a resource in Azure.

        Args:
            resource_group_name (str): Name of the resource group.
            resource_name (str): Name of the resource.

        Returns:
            str: Provisioning state if found, None otherwise.
        """
        response = requests.get(url, headers=self.headers)

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

    def build_container_image(self, azure_deploy_box_IAC: dict) -> dict:
        """
        """
        def build_container_image_helper(task: dict) -> str:
            task_name = "build-task-test"
            api_version = "2025-03-01-preview"

            step = task.get("properties", {}).get("step", {})

            assert isinstance(step, dict) and "contextDirectory" in step.keys(), "properties.step.contextDirectory is required"

            contextDirectory = step.pop("contextDirectory")
            contextPath = step.get("contextPath")

            # Check if updates have been made
            response = requests.get(f"https://api.github.com/repos/OWNER/REPO/commits?path=path/to/file.js")

            contextPath = contextPath if contextDirectory == "." else f"{contextPath}:{contextDirectory}"
            step.update({"contextPath": contextPath})

            # Create task
            create_url = (
                f"https://management.azure.com/subscriptions/{self.subscription_id}/"
                f"resourceGroups/{self.resource_group}/providers/Microsoft.ContainerRegistry/"
                f"registries/{self.regestry_name}/tasks/{task_name}?api-version={api_version}"
            )

            response = requests.put(create_url, headers=self.headers, json=task)
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

            run_response = requests.post(run_url, headers=self.headers, json=run_definition)

            return run_response.json().get("properties", {}).get("runId")


        # Find all `task` definitions
        for app in azure_deploy_box_IAC.get("azurerm_container_app", {}).values():
            containers = app.get("template", {}).get("container", [])
            for container in containers:
                image = container.get("image")
                
                if not isinstance(image, dict):
                    continue

                task = image.get("task")
                if task:
                    run_id = f"{build_container_image_helper(task=task)}"
                    image = self.wait_for_build_completion(run_id)
                    container.update({"image": image})

        return azure_deploy_box_IAC

        

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
            response = requests.get(url, headers=self.headers).json()
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
                return f"{output_image.get('registry')}/{output_image.get('repository')}:{run_id}"
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

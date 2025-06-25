import requests
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

class AzureBilling:

    def __init__(self):
        self.subscription_id = os.environ.get("ARM_SUBSCRIPTION_ID")
        self.tenant_id = os.environ.get("ARM_TENANT_ID")
        self.client_id = os.environ.get("ARM_CLIENT_ID")
        self.client_secret = os.environ.get("ARM_CLIENT_SECRET")
        self.token = self.get_azure_token()


    def get_azure_token(self) -> str:
        """
        This function retrieves the Azure access token using client credentials.
        """
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://management.azure.com/.default",
        }
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            raise Exception(f"Error retrieving Azure token: {response.text}")

    def get_resource_group_usage(self, resource_group_names: list) -> dict:
        """
        This function retrieves the resource group usage from Azure and returns it as a JSON object.
        """

        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/providers/Microsoft.CostManagement/query?api-version=2023-03-01"
        body ={
                "type": "ActualCost",
                "timeframe": "MonthToDate",
                "dataset": {
                    "granularity": "Monthly",
                    "aggregation": {
                    "totalCost": {
                        "name": "PreTaxCost",
                        "function": "Sum"
                    }
                    },
                    "grouping": [
                        {
                            "type": "Dimension",
                            "name": "ResourceGroupName"
                        }
                    ],
                    "filter": {
                    "dimensions": {
                        "name": "ResourceGroupName",
                        "operator": "In",
                        "values": resource_group_names
                    }
                    }
                }
                }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=body, headers=headers)
        if response.status_code == 200:
            rows = response.json().get("properties").get("rows")
            output = {}

            for row in rows:
                cost = row[0]
                resource_group_name = row[2]
                output[resource_group_name] = cost

            return output
        else:
            raise Exception(f"Error retrieving resource group usage: {response.text}")

    def get_all_resource_groups(self) -> tuple[list, list, dict]:
        """
        This function retrieves all resource groups in the subscription.
        """
        url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourcegroups?api-version=2021-04-01"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "content-type": "application/json",
        }
        response = requests.get(url, headers=headers)
        print("response: ", json.dumps(response.json(), indent=2))
        if response.status_code == 200:
            value = response.json().get("value")
            resource_groups = [group["name"] for group in value]
            resource_groups_tags = [group.get("tags", {}).get("org") for group in value]
            resource_group_to_org = {group["name"]: group.get("tags", {}).get("org") for group in value}

            return resource_groups, resource_groups_tags, resource_group_to_org
        else:
            raise Exception(f"Error retrieving resource groups: {response.text}")

if __name__ == "__main__":
    billing = AzureBilling()
    # Get all resource groups
    resource_groups, resource_group_tags, resource_group_to_org = billing.get_all_resource_groups()
    # print(f"Resource Groups: {resource_groups}")
    # Get usage for all resource groups
    usage = billing.get_resource_group_usage(resource_groups)
    # print(f"Usage for Resource Groups: {usage}")

import requests
import json
from pymongo import MongoClient
import os
import requests
# from Website.core.helpers.exchange_client_credentials import exchange_client_credentials_for_token
from dotenv import load_dotenv
from azure_billing import AzureBilling

load_dotenv()


def exchange_client_credentials_for_token(
    client_id, client_secret, token_url
) -> dict | None:
    """Exchanges client credentials for an access token."""
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            print(f"Error obtaining client credentials token: {response.text}")
            return None

        return response.json()  # Contains the access token
    except Exception as e:
        print(f"Error during client credentials token exchange: {str(e)}")
        return None


def invoice(data, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "http://localhost:8000/api/v1/payments/invoices/create/"

    response = requests.post(url, json=data, headers=headers)
    print(response.json())

    return response


def get_customer_id(org_id, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "http://localhost:8000/api/v1/payments/customers/get_customer_id/"

    org_id = {"org_id": org_id}
    org_id = json.dumps(org_id)

    return requests.post(url, org_id, headers=headers)


def update_invoice_billing(stack_id, cost, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "https://localhost:8000/api/v1/payments/update_invoice_billing"

    data = {"stack_id": stack_id, "cost": cost}
    data = json.dumps(data)

    response = requests.post(url, data=data, headers=headers)

    return response

def upcharge(data: dict) -> dict:

    for stack_id, usage in data.items():
        if usage < 1:
            data[stack_id] = 1
        else:
            data[stack_id] = usage * 1.5

    return data

def merg_data(group_name_and_usage: dict, group_name_and_org_id: dict) -> dict:

    data = {}

    for group_name, usage in group_name_and_usage.items():
        org_id = group_name_and_org_id.get(group_name)
        data[group_name] = (org_id, usage)

    return data

def create_invoice_data(data: dict) -> dict:
    """
    Create invoice data based on the provided usage data.

    Args:
        data (dict): Dictionary containing stack IDs and their respective usage.

    Returns:
        dict: Dictionary containing customer IDs, amounts, and descriptions.
    """
    invoice_data = {}

    for stack_id, (org_id, usage) in data.items():
        invoice_data[stack_id] = {
            "org_id": org_id,
            "amount": usage,
            "description": f"Here is your invoice for the database usage totaling {usage}",
        }

    return invoice_data


def charge_customer() -> None:
    """
    Charge the customer based on their database usage.

    Args:
        data (dict): Dictionary containing stack IDs and their respective usage.

    Returns:
        None
    """

    # Initialize AzureBilling instance to get resource group usage
    billing_instance = AzureBilling()
    resource_groups, resource_group_tags, resource_group_to_org = billing_instance.get_all_resource_groups()
    usage = billing_instance.get_resource_group_usage(resource_groups)

    #get token for deploy box api
    token_url = "http://localhost:8000/o/token/"
    token = exchange_client_credentials_for_token(
        os.environ.get("OAUTH2_CLIENT_CREDENTIALS_CLIENT_ID"), os.environ.get("OAUTH2_CLIENT_CREDENTIALS_CLIENT_SECRET"), token_url
    )

    #makes call to update the database usage
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "data": json.dumps(usage),
    }
    response = requests.post(
        "http://localhost:8000/api/v1/stacks/admin/databases/update_database_usage/",
        headers=headers,
        json=body,
    )

    customer_cost_data = upcharge(usage)
    customer_cost_data = merg_data(customer_cost_data, resource_group_to_org)
    invoice_data = create_invoice_data(customer_cost_data)
    # print("invoice_data: ", invoice_data)

    for data in invoice_data.items():
        stack_id = data[0]
        org_id = data[1].get('org_id')
        customer_id = get_customer_id(org_id=org_id, token=token)
        if customer_id.status_code != 200:
            invoice_data[stack_id].update({"customer_id": None})
            continue
        invoice_data[stack_id].update({"customer_id": customer_id.json().get("customer_id")})

    # print("invoice_data: ", invoice_data)

    for item in invoice_data.items():
        invoice_data = item[1]
        invoice(invoice_data, token)


if __name__ == "__main__":
    charge_customer()

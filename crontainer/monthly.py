import requests
import json
from pymongo import MongoClient
import os
import requests
# from Website.core.helpers.exchange_client_credentials import exchange_client_credentials_for_token
from dotenv import load_dotenv

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
    url = "https://deploy-box.onrender.com/payments/create-invoice"

    response = requests.post(url, data=data, headers=headers)
    print(response.json())

    return response


def get_customer_id(org_id, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "https://localhost:8000/payments/get_customer_id"

    org_id = {"org_id": org_id}
    org_id = json.dumps(org_id)

    return requests.post(url, org_id, headers=headers)


def update_invoice_billing(stack_id, cost, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "https://localhost:8000/payments/update_invoice_billing"

    data = {"stack_id": stack_id, "cost": cost}
    data = json.dumps(data)

    response = requests.post(url, data=data, headers=headers)

    return response


def charge_customer():

    token_url = "http://localhost:8000/o/token/"

    token = exchange_client_credentials_for_token(
        os.environ.get("OAUTH2_CLIENT_CREDENTIALS_CLIENT_ID"), os.environ.get("OAUTH2_CLIENT_CREDENTIALS_CLIENT_SECRET"), token_url
    )
    if token is None:
        raise ValueError("Failed to obtain token from exchange_client_credentials_for_token")
    token = token.get("access_token")

    headers = {"Authorization": f"Bearer {token}"}
    data = requests.post(
        "http://localhost:8000/admin/databases/update_database_usage/",
        headers=headers,
    )
    if data == None:
        raise ValueError("Failed to retrieve data from the API")

    print("data: ", data.json())

    for stack_id, values in data.json().get("stacks").items():
        org_id, usage = values
        cost = (
            int(round(((usage / 1_000_000) * 0.01) * 100, 0))
            if int(round(((usage / 1_000_000) * 0.01) * 100, 0)) >= 50
            else 50
        )
        customer_id = get_customer_id(org_id=org_id, token=token)
        customer_id = customer_id.json().get("customer_id")

        data = {
            "customer_id": customer_id,
            "amount": cost,
            "description": f"here is your invoice for the database usage totaling {usage}",
        }

        data = json.dumps(data)

        invoice(data, token)

        response = update_invoice_billing(stack_id, cost, token)

        # if response.status_code == 200:
        #     return response.json()
        # else:
        #     return {"error": f"Failed to create invoice for user {user_id} stack {stack_id}. Status code: {response.status_code}"}


if __name__ == "__main__":
    charge_customer()

import requests
import json
from pymongo import MongoClient
import os

import requests

def exchange_client_credentials_for_token(client_id, client_secret, token_url):
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
    headers ={
        "Authorization": f"Bearer {token}",
        'Content-Type': 'application/json'
    }  
    url = "https://deploy-box.onrender.com/payments/create-invoice"

    response = requests.post(url, data=data, headers=headers)
    print(response.json())

    return response
    
def get_customer_id(user_id, token):
    headers ={
        "Authorization": f"Bearer {token}",
        'Content-Type': 'application/json'
    }  
    url = "https://deploy-box.onrender.com/payments/get_customer_id"

    user_id = {"user_id": user_id}
    user_id = json.dumps(user_id)

    return requests.post(url, user_id,headers=headers)


def update_invoice_billing(stack_id, cost, token):
    headers ={
        "Authorization": f"Bearer {token}",
        'Content-Type': 'application/json'
    }  
    url = "https://deploy-box.onrender.com/payments/update_invoice_billing"

    data = {"stack_id": stack_id, "cost": cost}
    data = json.dumps(data)

    response = requests.post(url, data=data, headers=headers)

    return response



def charge_customer():

    token_url = 'https://deploy-box.onrender.com/accounts/o/token/'

    token = exchange_client_credentials_for_token(os.environ.get("CLIENT_ID"), os.environ.get("CLIENT_SECRET"), token_url)
    token = token.get("access_token")

    headers ={
        "Authorization": f"Bearer {token}"
    }    
    data = requests.get("https://deploy-box.onrender.com/api/stacks/get_stack_usage_from_db", headers=headers)
    print("data: ", data.json())

    for stack_id, values in data.json().get('stacks').items():
        user_id, usage = values
        cost = int(round(((usage/1_000_000) * 0.01)*100, 0)) if int(round(((usage/1_000_000) * 0.01)*100, 0)) >= 50 else 50
        customer_id = get_customer_id(user_id=user_id, token=token)
        customer_id = customer_id.json().get("customer_id")

        data = {"customer_id": customer_id, "amount": cost, "description": f"here is your invoice for the database usage totaling {usage}"}

        data = json.dumps(data)

        invoice(data, token)

        response = update_invoice_billing(stack_id, cost, token)

        # if response.status_code == 200:
        #     return response.json() 
        # else:
        #     return {"error": f"Failed to create invoice for user {user_id} stack {stack_id}. Status code: {response.status_code}"}



if __name__ == '__main__':
    charge_customer()
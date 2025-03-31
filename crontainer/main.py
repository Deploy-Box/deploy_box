import requests
import json
from pymongo import MongoClient
import os

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

def send_data(data, token):
    headers ={
        "Authorization": f"Bearer {token}",
        'Content-Type': 'application/json'
    }  
    url = "https://deploy-box.onrender.com/api/stacks/update_database_usage"
    requests.post(url, data=data, headers=headers)


def check_db_size():

    token_url = 'https://deploy-box.onrender.com/accounts/o/token/'

    token = exchange_client_credentials_for_token(os.environ.get("CLIENT_ID"), os.environ.get("CLIENT_SECRET"), token_url)
    token = token.get("access_token")

    headers ={
        "Authorization": f"Bearer {token}"
    }    
    data = requests.get("https://deploy-box.onrender.com/api/stacks/get_all_stacks", headers=headers)

    storage_amounts_dict = {}

    for stack_id, uris in data.json().get("stacks").items():
        for uri in uris:
            client = MongoClient(uri)
            db = client.get_default_database()
            stats = db.command("dbstats")
            storage_size = stats.get("storageSize")

            if stack_id in storage_amounts_dict:
                storage_amounts_dict[stack_id] += storage_size
            else:
                storage_amounts_dict[stack_id] = storage_size

    json_data = json.dumps(storage_amounts_dict)
    send_data(json_data, token)


if __name__ == '__main__':
    check_db_size()




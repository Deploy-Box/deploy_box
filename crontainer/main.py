import requests
import json
from pymongo import MongoClient
import os
from Website.core.helpers.exchange_client_credentials import exchange_client_credentials_for_token


def send_data(data, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "https://deploy-box.onrender.com/api/stack/update_database_usage"
    requests.post(url, data=data, headers=headers)


def check_db_size():

    token_url = "https://deploy-box.onrender.com/o/token/"

    token = exchange_client_credentials_for_token(
        os.environ.get("CLIENT_ID"), os.environ.get("CLIENT_SECRET"), token_url
    )

    assert token is not None, "Token is None"
    token = token.get("access_token")

    headers = {"Authorization": f"Bearer {token}"}
    data = requests.get(
        "https://deploy-box.onrender.com/api/stack/get_all_stacks", headers=headers
    )

    storage_amounts_dict = {}

    for stack_id, uris in data.json().get("data").items():
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


if __name__ == "__main__":
    check_db_size()

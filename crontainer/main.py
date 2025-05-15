import requests
import json
from pymongo import MongoClient
import os
from helpers import make_authenticated_api_request
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")

def send_data(data, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{BASE_URL}/api/stack/update_database_usage"
    requests.post(url, data=data, headers=headers)


def check_db_size():
    data = make_authenticated_api_request(
        "/api/v1/stacks/admin/databases/"
    )

    print(json.dumps(data, indent=4))

    storage_amounts_dict = {}

    for database in data.get("data"):
        stack_id = database.get("stack")
        uri = database.get("uri")

        print(stack_id, uri)

        client = MongoClient(uri)
        db = client.get_default_database()
        stats = db.command("dbstats")
        storage_size = stats.get("storageSize")

        if stack_id in storage_amounts_dict:
            storage_amounts_dict[stack_id] += storage_size
        else:
            storage_amounts_dict[stack_id] = storage_size

    response = make_authenticated_api_request(
        "/api/v1/stacks/admin/databases/update_database_usage/",
        "POST",
        {"success": True, "data": storage_amounts_dict}
    )

    print(response)


if __name__ == "__main__":
    check_db_size()

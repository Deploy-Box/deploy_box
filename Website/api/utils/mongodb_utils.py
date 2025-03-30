import requests
import time
import hashlib
from pymongo import MongoClient
from django.conf import settings

mongo_db_token = None


def get_mongodb_token() -> None:
    global mongo_db_token

    if mongo_db_token:
        return mongo_db_token

    url = "https://cloud.mongodb.com/api/oauth/token"
    payload = {"grant_type": "client_credentials"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth = (settings.MONGO_DB.get("CLIENT_ID"), settings.MONGO_DB.get("CLIENT_SECRET"))
    response = requests.post(url, data=payload, headers=headers, auth=auth)

    if not response.ok:
        print(response.status_code)
        print(response.json())
        raise Exception({"error": response.json()})

    mongo_db_token = response.json().get("access_token")


def request_helper(url, method="GET", data=None):
    global mongo_db_token

    url = f"https://cloud.mongodb.com/api/atlas/v2{url}"

    while True:
        headers = {
            "Authorization": f"Bearer {mongo_db_token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.atlas.2023-01-01+json",
        }

        response = None
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)

        print(response.status_code)
        if response.status_code == 401:
            mongo_db_token = None
            get_mongodb_token()
            continue

        elif response.ok:
            return response.json()

        return response


def deploy_mongodb_database(stack_id: str) -> str:
    print("Deploying MongoDB database...")
    database_name = f"db-{stack_id}"
    username = f"deployBoxUser{stack_id}"
    password = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]
    project_id = settings.MONGO_DB.get("PROJECT_ID")

    # Check if user already exists
    # TODO: Update password if the user already exists
    response = request_helper(
        f"/groups/{project_id}/databaseUsers/admin/{username}", "GET"
    )

    if isinstance(response, requests.models.Response):
        # if response.status_code != 404:
        #     raise Exception("Error: Failed to check if the user exists.")

        # Create a new database user
        user_data = {
            "groupId": project_id,
            "databaseName": "admin",
            "username": username,
            "password": password,
            "roles": [{"databaseName": database_name, "roleName": "readWrite"}],
        }

        response = request_helper(
            f"/groups/{project_id}/databaseUsers", "POST", user_data
        )

        # TODO: Check if the user was created successfully

    connection_string = f"mongodb+srv://{username}:{password}@cluster0.yjaoi.mongodb.net/{database_name}?retryWrites=true&w=majority&appName=Cluster0"

    return connection_string





import os
import dotenv
import requests
import time
import re
import requests
import time
import hashlib
from pymongo import MongoClient
from django.conf import settings

dotenv.load_dotenv()

PROVIDER_NAME = "mongodbatlas"

class MongoDBAtlasDeployBoxIAC:
    def __init__(self):
        """
        Initialize the class MongoDBAtlasDeployBoxIAC:
        """
        self.client_id = os.getenv("ARM_CLIENT_ID")
        self.client_secret = os.getenv("ARM_CLIENT_SECRET")
        self.tenant_id = os.getenv("ARM_TENANT_ID")
        self.subscription_id = os.getenv("ARM_SUBSCRIPTION_ID")
        self.location = "eastus"
        self.resource_group = "deploy-box-rg-dev"
        self.registry_name = "deployboxcrdev"

        self.state = {}

    def plan(self, terraform: dict, deploy_box_iac: dict, state: dict):
        self.state = state.setdefault(PROVIDER_NAME, {})

        provider = terraform.get("provider", {})
        assert isinstance(provider, dict)

        resource = terraform.get("resource", {})
        assert isinstance(resource, dict)

        provider.update(
            {
                PROVIDER_NAME: {
                    "mongodbatlas": {
                        "public_key": "wvnwflmq",
                        "private_key": "bcee2cc4-bc05-4ec9-bee3-f27f7c496abb"
                    }
                }
            }
        )

        mongodb_deploy_box_iac = {
            k: v for k, v in deploy_box_iac.items() if k.startswith(PROVIDER_NAME)
        }

        resource.update(mongodb_deploy_box_iac)

        return {"provider": provider, "resource": resource}


class MongoDBUtils:
    __mongo_db_token = None
    __MONGODB_PROJECT_ID = settings.MONGO_DB.get("PROJECT_ID")
    __MONGODB_CLIENT_ID = settings.MONGO_DB.get("CLIENT_ID")
    __MONGODB_CLIENT_SECRET = settings.MONGO_DB.get("CLIENT_SECRET")

    def __init__(self):
        """
        Initialize the MongoDBUtils class. This method ensures that the MongoDB token is retrieved
        when an instance of the class is created. The token is used for authenticating API requests.
        """
        if not MongoDBUtils.__mongo_db_token:
            self.__get_token()

    def __get_token(self) -> None:
        """ "
        Retrieve a MongoDB token using the OAuth2 client credentials flow."
        """
        if MongoDBUtils.__mongo_db_token:
            return

        url = "https://cloud.mongodb.com/api/oauth/token"
        payload = {"grant_type": "client_credentials"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        auth = (MongoDBUtils.__MONGODB_CLIENT_ID, MongoDBUtils.__MONGODB_CLIENT_SECRET)
        response = requests.post(url, data=payload, headers=headers, auth=auth)

        if not response.ok:
            print(response.status_code)
            print(response.json())
            raise Exception({"error": response.json()})

        MongoDBUtils.__mongo_db_token = response.json().get("access_token")

    def __request_helper(self, url, method="GET", data=None) -> dict:
        url = f"https://cloud.mongodb.com/api/atlas/v2{url}"

        while True:
            headers = {
                "Authorization": f"Bearer {MongoDBUtils.__mongo_db_token}",
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

            if response is None:
                # Handle unsupported method
                raise Exception(
                    f"Unsupported HTTP method: {method}. Please use GET, POST, PUT, DELETE, or PATCH."
                )

            if response.status_code == 401:
                MongoDBUtils.__mongo_db_token = None
                self.__get_token()
                continue

            elif response.ok:
                return response.json()

            raise Exception(
                f"Response: {response.json() if response.content else 'No content'}"
            )

    def __generate_password(self) -> str:
        """
        Generate a secure password for MongoDB user.
        This method generates a random password using the current time and hashes it to ensure uniqueness.
        The length of the password is limited to 12 characters for compatibility with MongoDB.
        """
        # Generate a unique password using the current time
        password = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]

        # Ensure the password meets MongoDB's requirements (at least 8 characters, contains letters and digits)
        return password

    def __check_if_user_exists(self, username: str) -> bool:
        """
        Check if a MongoDB user exists by username.
        This method queries the MongoDB Atlas API to check for the existence of a user with the given username.
        """
        try:
            response = self.__request_helper(
                f"/groups/{MongoDBUtils.__MONGODB_PROJECT_ID}/databaseUsers/admin/{username}",
                "GET",
            )

            if isinstance(response, dict) and "error" in response:
                # Handle error response
                return False

            # If the response is a valid user object, return True
            return (
                True
                if isinstance(response, dict) and response.get("username") == username
                else False
            )
        except Exception as e:
            return False

    def __update_user_password(self, username: str, new_password: str) -> None:
        """
        Update the password for an existing MongoDB user.
        This method sends a request to the MongoDB Atlas API to update the password for the specified username.
        """
        user_data = {"password": new_password}

        response = self.__request_helper(
            f"/groups/{MongoDBUtils.__MONGODB_PROJECT_ID}/databaseUsers/admin/{username}",
            "PATCH",
            user_data,
        )

        if isinstance(response, dict) and "error" in response:
            # Handle error response
            raise Exception(
                f"Failed to update password for user {username}: {response['error']}"
            )

        # Successfully updated the password
        print(f"Password for user {username} updated successfully.")

    def deploy_mongodb_database(self, stack_id: str) -> str:
        print("Deploying MongoDB database...")

        MONGODB_PROJECT_ID = MongoDBUtils.__MONGODB_PROJECT_ID

        database_name = f"db-{stack_id}"
        username = f"deployBoxUser-{stack_id}"

        password = (
            self.__generate_password()
        )  # Ensure we have a valid token before proceeding

        # Check if user already exists
        user_exists = self.__check_if_user_exists(username)

        if user_exists:
            # User already exists, we can reuse the existing user
            self.__update_user_password(username, password)

        else:
            # Create a new database user
            user_data = {
                "groupId": MONGODB_PROJECT_ID,
                "databaseName": "admin",
                "username": username,
                "password": password,
                "roles": [{"databaseName": database_name, "roleName": "readWrite"}],
            }

            self.__request_helper(
                f"/groups/{MONGODB_PROJECT_ID}/databaseUsers", "POST", user_data
            )

            user_exists = self.__check_if_user_exists(username)

            if not user_exists:
                # If the user was not created successfully, raise an exception
                raise Exception(
                    f"Failed to create MongoDB user {username}. Please check the API response."
                )

        connection_string = f"mongodb+srv://{username}:{password}@cluster0.yjaoi.mongodb.net/{database_name}?retryWrites=true&w=majority&appName=Cluster0"

        return connection_string

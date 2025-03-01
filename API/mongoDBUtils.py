import dotenv
import os
import requests
import time
import uuid
import hashlib
dotenv.load_dotenv()

MONGODB_TOKEN = os.environ.get("MONGODB_TOKEN")
MONGODB_ORG_ID = os.environ.get("MONGODB_ORG_ID")
MONGODB_CLIENT_ID = os.environ.get("MONGODB_CLIENT_ID")
MONGODB_CLIENT_SECRET = os.environ.get("MONGODB_CLIENT_SECRET")

def get_mongodb_token():
    global MONGODB_TOKEN

    if MONGODB_TOKEN:
        return MONGODB_TOKEN

    url = "https://cloud.mongodb.com/api/oauth/token"
    payload = {
        "grant_type": "client_credentials"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    auth = (MONGODB_CLIENT_ID, MONGODB_CLIENT_SECRET)
    response = requests.post(url, data=payload, headers=headers, auth=auth)
    response.raise_for_status()
    MONGODB_TOKEN = response.json().get("access_token")
    print(f"MONGODB_TOKEN={MONGODB_TOKEN}")
    return MONGODB_TOKEN


def request_helper(url, method="GET", data=None):
    global MONGODB_TOKEN

    url = f"https://cloud.mongodb.com/api/atlas/v2/{url}"

    while True:
        headers = {
            "Authorization": f"Bearer {MONGODB_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.atlas.2023-01-01+json"
        }
            
        try:
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

            if response.status_code == 401:
                MONGODB_TOKEN = None
                get_mongodb_token()
                continue

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            return err
        except Exception as e:
            return e


def deploy_mongodb():
    # Get all projects
    projects = request_helper("groups")

    if (isinstance(projects, requests.exceptions.HTTPError)):
        print(projects)
        return {"error": "Error fetching projects"}

    project_id = None
    cluster_connection_uri = None

    for project in projects["results"]:
        project_name = project["name"]

        # Skip if the project name doesn't contain the placeholder
        if "DEPLOY-BOX-PROJECT-PLACEHOLDER" not in project_name:
            continue


        clusters = request_helper(f"groups/{project['id']}/clusters")

        # Skip if the cluster doesn't have a cluster
        if clusters["totalCount"] == 0:
            continue

        for cluster in clusters["results"]:
            if "Cluster0" not in cluster["name"]:
                continue

            cluster_connection_uri = cluster["connectionStrings"]["standardSrv"]
            cluster_connection_uri = cluster_connection_uri.replace("mongodb+srv://", "")
            break
        
        project_id = project["id"]
        break

    
    if not project_id or not cluster_connection_uri:
        return {"error": "No empty projects available"}

    # TODO: Create user role to prevent unauthorized access

    # Create a new database user
    user_password = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]
    user_data = {
            "groupId": project_id,
            "databaseName": "admin",
            "username": "admin",
            "password": user_password,
            "roles": [
                {
                    "collectionName": "Cluster0",
                    "databaseName": "admin",
                    "roleName": "read"
                }
            ]
        }
    
    request_helper(f"groups/{project_id}/databaseUsers", "POST", user_data)

    connection_string = f"mongodb+srv://admin:{user_password}@{cluster_connection_uri}/?retryWrites=true&w=majority&appName=Cluster0"

    # Rename the project
    project_name = str(uuid.uuid4())
    project_data = {
        "name": project_name
    }

    request_helper(f"groups/{project_id}", "PATCH", project_data)

    return connection_string

if __name__ == '__main__':
    print(deploy_mongodb())
    
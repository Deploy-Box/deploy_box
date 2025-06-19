import json
import subprocess
import tempfile
import os
from azure.storage.blob import BlobServiceClient

from Azure import AzureDeployBoxIAC
from dotenv import load_dotenv

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING=os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME=os.environ.get("CONTAINER_NAME")


deploy_box_IAC = {
    "azurerm_resource_group": {
        "rg": {
            "name": "example-containerapp-rg4",
            "location": "East US"
        }
    },
    "azurerm_log_analytics_workspace": {
        "law": {
            "name": "example-law",
            "location": "East US",
            "resource_group_name": "${azurerm_resource_group.rg.name}",
            "sku": "PerGB2018",
            "retention_in_days": 30
        }
    },
    "azurerm_container_app_environment": {
        "env": {
            "name": "example-env",
            "location": "East US",
            "resource_group_name": "${azurerm_resource_group.rg.name}",
            "log_analytics_workspace_id": "${azurerm_log_analytics_workspace.law.id}"
        }
    },
    "azurerm_container_app": {
        "app1": {
            "name": "example-app",
            "resource_group_name": "${azurerm_resource_group.rg.name}",
            "container_app_environment_id": "${azurerm_container_app_environment.env.id}",
            "revision_mode": "Single",
            "ingress": {
                "external_enabled": True,
                "target_port": 5000,
                "transport": "auto",
                "traffic_weight": [
                    {
                        "latest_revision": True,
                        "percentage": 100
                    }
                ]
            },
            "secret": [
                {
                "name": "acr-password",
                "value": os.environ.get("ACR_PASSWORD")
                }
            ],
            "registry": [
                {
                    "server": "deployboxcrdev.azurecr.io",
                    "username": "deployboxcrdev",
                    "password_secret_name": "acr-password"
                }
            ],
            "template": {
                "container": [
                    {
                        "name": "testing-mern",
                        "image": {
                            "task": {
                                "location": "eastus",
                                "properties": {
                                    "status": "Enabled",
                                    "platform": {"os": "Linux"},
                                    "agentConfiguration": {"cpu": 1},
                                    "step": {
                                        "type": "Docker",
                                        "contextPath": "https://github.com/kalebwbishop/VBHS-music-manager.git#main:backend",
                                        "dockerFilePath": "dockerfile",
                                        "imageNames": ["mern-app:{{.Run.ID}}"],
                                        "isPushEnabled": True,
                                    },
                                    "trigger": {
                                        "sourceTriggers": [],
                                        "baseImageTrigger": {
                                            "type": "Runtime",
                                            "baseImageTriggerType": "Runtime",
                                            "name": "defaultBaseimageTrigger",
                                            "status": "Disabled",
                                        },
                                        "timerTriggers": [],
                                    },
                                },
                            }
                        },
                        "cpu": 0.25,
                        "memory": "0.5Gi",
                        "env": [
                            {
                                "name": "MONGO_URI",
                                "value": "mongodb+srv://deployBoxUser-b61c956f6f634710:O5IIWezIuphA1xSa@cluster0.yjaoi.mongodb.net/db-b61c956f6f634710?retryWrites=true&w=majority&appName=Cluster0",
                            }
                        ],
                    }
                ]
            },
        },
        "app2": {
            "name": "example-app2",
            "resource_group_name": "${azurerm_resource_group.rg.name}",
            "container_app_environment_id": "${azurerm_container_app_environment.env.id}",
            "revision_mode": "Single",
            "ingress": {
                "external_enabled": True,
                "target_port": 5000,
                "transport": "auto",
                "traffic_weight": [
                    {
                        "latest_revision": True,
                        "percentage": 100
                    }
                ]
            },
            "secret": [
                {
                "name": "acr-password",
                "value": os.environ.get("ACR_PASSWORD")
                }
            ],
            "registry": [
                {
                    "server": "deployboxcrdev.azurecr.io",
                    "username": "deployboxcrdev",
                    "password_secret_name": "acr-password"
                }
            ],
            "template": {
                "container": [
                    {
                        "name": "testing-mern",
                        "image": {
                            "task": {
                                "location": "eastus",
                                "properties": {
                                    "status": "Enabled",
                                    "platform": {"os": "Linux"},
                                    "agentConfiguration": {"cpu": 1},
                                    "step": {
                                        "type": "Docker",
                                        "contextPath": "https://github.com/kalebwbishop/VBHS-music-manager.git#main:backend",
                                        "dockerFilePath": "dockerfile",
                                        "imageNames": ["mern-app:{{.Run.ID}}"],
                                        "isPushEnabled": True,
                                    },
                                    "trigger": {
                                        "sourceTriggers": [],
                                        "baseImageTrigger": {
                                            "type": "Runtime",
                                            "baseImageTriggerType": "Runtime",
                                            "name": "defaultBaseimageTrigger",
                                            "status": "Disabled",
                                        },
                                        "timerTriggers": [],
                                    },
                                },
                            }
                        },
                        "cpu": 0.25,
                        "memory": "0.5Gi",
                        "env": [
                            {
                                "name": "MONGO_URI",
                                "value": "mongodb+srv://deployBoxUser-b61c956f6f634710:O5IIWezIuphA1xSa@cluster0.yjaoi.mongodb.net/db-b61c956f6f634710?retryWrites=true&w=majority&appName=Cluster0",
                            }
                        ],
                    }
                ]
            },
        },
    }
}

# Function to run terraform command
def run_terraform_cmd(command, cwd):
    result = subprocess.run(
        ["terraform"] + command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"\nterraform {' '.join(command)}")
    print("STDOUT:\n", result.stdout)
    if result.stderr:
        print("STDERR:\n", result.stderr)
    return result

def upload_directory_to_blob(local_dir, blob_prefix="terraform"):
    assert AZURE_STORAGE_CONNECTION_STRING is not None
    assert CONTAINER_NAME is not None
    blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service.get_container_client(CONTAINER_NAME)

    # Ensure container exists
    try:
        container_client.create_container()
    except Exception:
        pass

    for root, _, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_dir)
            blob_path = f"{blob_prefix}/{relative_path}".replace("\\", "/")
            print(f"Uploading: {local_path} -> {blob_path}")
            with open(local_path, "rb") as data:
                container_client.upload_blob(blob_path, data, overwrite=True)

def download_directory_from_blob(blob_prefix, local_dir):
    assert AZURE_STORAGE_CONNECTION_STRING is not None
    assert CONTAINER_NAME is not None
    blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service.get_container_client(CONTAINER_NAME)

    blobs = container_client.list_blobs(name_starts_with=blob_prefix)
    for blob in blobs:
        blob_name = blob.name
        relative_path = os.path.relpath(blob_name, blob_prefix)
        local_path = os.path.join(local_dir, relative_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        print(f"Downloading: {blob_name} -> {local_path}")
        with open(local_path, "wb") as file:
            blob_data = container_client.download_blob(blob_name)
            file.write(blob_data.readall())

# Main logic
temp_dir = tempfile.mkdtemp()
print(f"Debugging temp dir: {temp_dir}")

tf_file = os.path.join(temp_dir, "main.tf.json")

# Generate TF JSON config
terraform = AzureDeployBoxIAC().azure_helper({}, deploy_box_IAC)
print(json.dumps(terraform, indent=3))
with open(tf_file, "w") as f:
    json.dump(terraform, f, indent=2)

# Optionally download from Azure Blob (if restoring from prior state)
download_directory_from_blob("terraform4", temp_dir)

# Run Terraform commands
run_terraform_cmd(["init"], temp_dir)
run_terraform_cmd(["plan"], temp_dir)
run_terraform_cmd(["apply", "-auto-approve"], temp_dir)

# Delete the main.tf.json file
os.remove(tf_file)

# Upload results (including .tfstate) to blob storage
upload_directory_to_blob(temp_dir, blob_prefix="terraform4")

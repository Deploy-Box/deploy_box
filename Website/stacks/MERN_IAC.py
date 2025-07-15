import os
import time
import hashlib
from django.conf import settings


def get_MERN_IAC(stack_id: str, project_id: str, org_id: str):
    """
    Returns the stack name for the MERN IAC stack.
    """

    resource_group_name = f"{stack_id}-rg"

    return resource_group_name, {
        "mongodbatlas_database_user": {
            "user": {
                "username": f"deployBoxUser{stack_id}",
                "password": hashlib.sha256(str(time.time()).encode()).hexdigest()[:12],
                "project_id": settings.MONGO_DB["PROJECT_ID"],
                "auth_database_name": "admin",
                "roles": [
                {
                    "role_name": "readWrite",
                    "database_name": f"db-{stack_id}"
                }
                ]
            }
        },
        "azurerm_resource_group": {
            "rg": {
                "name": resource_group_name,
                "location": "eastus",
                "tags": {
                    "deploy-box-environment": "dev",
                    "org": org_id,
                    "project": project_id,
                },
            }
        },
        "azurerm_log_analytics_workspace": {
            "law": {
                "name": "example-law",
                "location": "eastus",
                "resource_group_name": "${azurerm_resource_group.rg.name}",
                "sku": "PerGB2018",
                "retention_in_days": 30,
            }
        },
        "azurerm_container_app_environment": {
            "env": {
                "name": "example-env",
                "location": "eastus",
                "resource_group_name": "${azurerm_resource_group.rg.name}",
                "log_analytics_workspace_id": "${azurerm_log_analytics_workspace.law.id}",
            }
        },
        "azurerm_container_app": {
            f"mern-backend-{stack_id}": {
                "name": f"mern-backend-{stack_id}",
                "resource_group_name": "${azurerm_resource_group.rg.name}",
                "container_app_environment_id": "${azurerm_container_app_environment.env.id}",
                "revision_mode": "Single",
                "ingress": {
                    "external_enabled": True,
                    "target_port": 5000,
                    "transport": "auto",
                    "traffic_weight": [{"latest_revision": True, "percentage": 100}],
                },
                "secret": [
                    {"name": "acr-password", "value": os.environ.get("ACR_PASSWORD")}
                ],
                "registry": [
                    {
                        "server": f"{settings.AZURE['ACR_NAME']}.azurecr.io",
                        "username": settings.AZURE['ACR_NAME'],
                        "password_secret_name": "acr-password",
                    }
                ],
                "template": {
                    "container": [
                        {
                            "name": "testing-mern",
                            "image": f"{settings.AZURE['ACR_NAME']}.azurecr.io/mern-backend:latest",
                            "cpu": 0.25,
                            "memory": "0.5Gi",
                            "env": [
                                {
                                    "name": "MONGO_URI",
                                    "value": "mongodb+srv://${mongodbatlas_database_user.user.username}:${mongodbatlas_database_user.user.password}@cluster0.yjaoi.mongodb.net/",
                                },
                                {
                                    "name": "MONGO_DB_NAME",
                                    "value": f"db-{stack_id}",
                                }
                            ],
                        }
                    ]
                },
            },
            f"mern-frontend-{stack_id}": {
                "name": f"mern-frontend-{stack_id}",
                "resource_group_name": "${azurerm_resource_group.rg.name}",
                "container_app_environment_id": "${azurerm_container_app_environment.env.id}",
                "revision_mode": "Single",
                "ingress": {
                    "external_enabled": True,
                    "target_port": 8080,
                    "transport": "auto",
                    "traffic_weight": [{"latest_revision": True, "percentage": 100}],
                },
                "secret": [
                    {"name": "acr-password", "value": os.environ.get("ACR_PASSWORD")}
                ],
                "registry": [
                    {
                        "server": f"{settings.AZURE['ACR_NAME']}.azurecr.io",
                        "username": settings.AZURE['ACR_NAME'],
                        "password_secret_name": "acr-password",
                    }
                ],
                "template": {
                    "container": [
                        {
                            "name": "testing-mern",
                            "image": f"{settings.AZURE['ACR_NAME']}.azurecr.io/mern-frontend:latest",
                            "cpu": 0.25,
                            "memory": "0.5Gi",
                            "env": [
                                {
                                    "name": "REACT_APP_BACKEND_URL",
                                    "value": "REACT_APP_BACKEND_URL_PLACEHOLDER",
                                }
                            ],
                        }
                    ]
                },
            },
        },
    }

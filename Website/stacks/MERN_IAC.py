import os


def get_MERN_IAC(stack_id: str, project_id: str, org_id: str, mongo_uri: str):
    """
    Returns the stack name for the MERN IAC stack.
    """

    resource_group_name = f"{stack_id}-rg"

    return resource_group_name, {
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
                        "server": "deployboxcrdev.azurecr.io",
                        "username": "deployboxcrdev",
                        "password_secret_name": "acr-password",
                    }
                ],
                "template": {
                    "container": [
                        {
                            "name": "testing-mern",
                            "image":
                            #   "deployboxcrdev.azurecr.io/1f102b02298e494a1:latest",
                            {
                                "task": {
                                    "location": "eastus",
                                    "properties": {
                                        "status": "Enabled",
                                        "platform": {"os": "Linux"},
                                        "agentConfiguration": {"cpu": 2},
                                        "step": {
                                            "type": "Docker",
                                            "contextPath": "https://github.com/Deploy-Box/MERN.git#main",
                                            "contextDirectory": "source_code/backend",
                                            "dockerFilePath": "Dockerfile",
                                            "imageNames": [f"{stack_id}1:latest"],
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
                                    "value": mongo_uri,
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
                        "server": "deployboxcrdev.azurecr.io",
                        "username": "deployboxcrdev",
                        "password_secret_name": "acr-password",
                    }
                ],
                "template": {
                    "container": [
                        {
                            "name": "testing-mern",
                            "image": "deployboxcrdev.azurecr.io/1f102b02298e494a2:latest",
                            # {
                            #     "task": {
                            #         "location": "eastus",
                            #         "properties": {
                            #             "status": "Enabled",
                            #             "platform": {"os": "Linux"},
                            #             "agentConfiguration": {"cpu": 2},
                            #             "step": {
                            #                 "type": "Docker",
                            #                 "contextPath": "https://github.com/Deploy-Box/MERN.git#main",
                            #                 "contextDirectory": "source_code/frontend",
                            #                 "dockerFilePath": "dockerfile",
                            #                 "imageNames": [f"{stack_id}2:latest"],
                            #                 "isPushEnabled": True,
                            #             },
                            #             "trigger": {
                            #                 "sourceTriggers": [],
                            #                 "baseImageTrigger": {
                            #                     "type": "Runtime",
                            #                     "baseImageTriggerType": "Runtime",
                            #                     "name": "defaultBaseimageTrigger",
                            #                     "status": "Disabled",
                            #                 },
                            #                 "timerTriggers": [],
                            #             },
                            #         },
                            #     }
                            # },
                            "cpu": 0.25,
                            "memory": "0.5Gi",
                            "env": [
                                {
                                    "name": "REACT_APP_BACKEND_URL",
                                    "value": "https://backend.wittyocean-13982f09.eastus.azurecontainerapps.io",
                                }
                            ],
                        }
                    ]
                },
            },
        },
    }

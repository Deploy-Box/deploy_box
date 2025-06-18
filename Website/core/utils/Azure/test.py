from azure.identity import DefaultAzureCredential
import requests

# Azure details
subscription_id = "3106bb2d-2f28-445e-ab1e-79d93bd15979"
resource_group = "deploy-box-rg-dev"
registry_name = "deployboxcrdev"
task_name = "build-task-test"
api_version = "2025-03-01-preview"

# Authentication
credential = DefaultAzureCredential()
token = credential.get_token("https://management.azure.com/.default")
headers = {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}

# ACR Task definition
task_definition = {
    "location": "eastus",
    "properties": {
        "status": "Enabled",
        "platform": {"os": "Linux"},
        "agentConfiguration": {"cpu": 2},
        "step": {
            "type": "Docker",
            "contextPath": "https://github.com/Deploy-Box/MERN.git#main:source_code/backend",
            "dockerFilePath": "Dockerfile",
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

# Create task
create_url = (
    f"https://management.azure.com/subscriptions/{subscription_id}/"
    f"resourceGroups/{resource_group}/providers/Microsoft.ContainerRegistry/"
    f"registries/{registry_name}/tasks/{task_name}?api-version={api_version}"
)

response = requests.put(create_url, headers=headers, json=task_definition)
print("Create Task Response:", response.status_code, response.json())

# Run task
run_definition = {
    "type": "TaskRunRequest",
    "taskId": f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ContainerRegistry/registries/{registry_name}/tasks/{task_name}",
}

run_url = (
    f"https://management.azure.com/subscriptions/{subscription_id}/"
    f"resourceGroups/{resource_group}/providers/Microsoft.ContainerRegistry/"
    f"registries/{registry_name}/scheduleRun?api-version={api_version}"
)

run_response = requests.post(run_url, headers=headers, json=run_definition)
print("Run Task Response:", run_response.status_code)
if run_response.text:
    try:
        print(run_response.json())
    except Exception as e:
        print("Could not parse JSON:", e)
        print("Raw response text:", run_response.text)
else:
    print("No content in response.")
    print("URL:", run_url)

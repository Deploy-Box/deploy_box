# Stack IAC Update Endpoint

This document describes the new stack IAC update endpoint that allows full overwrite of the Infrastructure as Code (IAC) configuration for a stack given its ID. **This endpoint only updates the database field and does not trigger cloud deployment.**

## Endpoint

**URL:** `POST /api/stacks/{stack_id}/update_iac/`

**Method:** POST

**Authentication:** Required (OAuth)

## Request

### Headers
```
Content-Type: application/json
Authorization: Bearer <your_oauth_token>
```

### Body
```json
{
    "data": {
        "azure": {
            "resource_group": "my-resource-group",
            "location": "eastus"
        },
        "container_apps": {
            "frontend": {
                "name": "frontend-app",
                "image": "nginx:latest",
                "replicas": 3
            },
            "backend": {
                "name": "backend-app",
                "image": "node:16",
                "replicas": 2
            }
        },
        "databases": {
            "mongodb": {
                "enabled": true,
                "version": "4.4"
            }
        }
    }
}
```

### Parameters
- `stack_id` (path parameter): The unique identifier of the stack to update
- `data` (body parameter): The complete new IAC configuration to replace the existing one
- `section` (body parameter, optional): Ignored for full overwrite operations

## Response

### Success Response (200 OK)
```json
{
    "success": true,
    "message": "IAC configuration updated successfully (no deployment)",
    "stack_id": "stack_uuid_here",
    "old_iac": {
        "existing": "configuration"
    },
    "new_iac": {
        "azure": {
            "resource_group": "my-resource-group",
            "location": "eastus"
        },
        "container_apps": {
            "frontend": {
                "name": "frontend-app",
                "image": "nginx:latest",
                "replicas": 3
            },
            "backend": {
                "name": "backend-app",
                "image": "node:16",
                "replicas": 2
            }
        },
        "databases": {
            "mongodb": {
                "enabled": true,
                "version": "4.4"
            }
        }
    }
}
```

### Error Responses

#### 400 Bad Request (Invalid Data)
```json
{
    "data": [
        "This field is required."
    ]
}
```

#### 400 Bad Request (Empty IAC)
```json
{
    "error": "IAC configuration is required."
}
```

#### 400 Bad Request (Invalid JSON)
```json
{
    "error": "IAC configuration must be a valid JSON object."
}
```

#### 404 Not Found (Stack Not Found)
```json
{
    "detail": "Not found."
}
```

#### 500 Internal Server Error (Update Failed)
```json
{
    "error": "Failed to update IAC configuration"
}
```

## Important Notes

⚠️ **Full Overwrite**: This endpoint performs a **complete overwrite** of the existing IAC configuration. The entire IAC will be replaced with the new configuration provided.

⚠️ **Database Only**: This endpoint **only updates the database field** and does not trigger any cloud deployment. The IAC configuration is stored but not applied to the cloud infrastructure.

⚠️ **No Deployment**: No Azure resources are created, updated, or modified by this endpoint.

## Example Usage

### Using curl
```bash
curl -X POST \
  https://your-domain.com/api/stacks/stack-uuid-here/update_iac/ \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your_oauth_token' \
  -d '{
    "data": {
        "azure": {
            "resource_group": "my-rg",
            "location": "eastus"
        },
        "container_apps": {
            "frontend": {
                "name": "frontend-app",
                "image": "nginx:latest"
            }
        }
    }
  }'
```

### Using Python requests
```python
import requests

url = "https://your-domain.com/api/stacks/stack-uuid-here/update_iac/"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your_oauth_token"
}
data = {
    "data": {
        "azure": {
            "resource_group": "my-rg",
            "location": "eastus"
        },
        "container_apps": {
            "frontend": {
                "name": "frontend-app",
                "image": "nginx:latest"
            }
        }
    }
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## IAC Configuration Structure

The IAC configuration typically includes:

### Azure Configuration
```json
{
    "azure": {
        "resource_group": "string",
        "location": "string"
    }
}
```

### Container Apps
```json
{
    "container_apps": {
        "frontend": {
            "name": "string",
            "image": "string",
            "replicas": "number"
        },
        "backend": {
            "name": "string",
            "image": "string",
            "replicas": "number"
        }
    }
}
```

### Databases
```json
{
    "databases": {
        "mongodb": {
            "enabled": "boolean",
            "version": "string"
        }
    }
}
```

## Notes

- The endpoint requires OAuth authentication
- The `data` field is required and must contain a valid JSON object
- The entire IAC configuration is replaced (full overwrite)
- **No cloud deployment is triggered** - only the database field is updated
- All IAC updates are logged for audit purposes
- The `section` parameter is ignored for full overwrite operations

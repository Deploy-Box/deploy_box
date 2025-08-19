# Stack IAC Overwrite Endpoint

This document describes the new endpoint that allows complete overwriting of a stack's Infrastructure as Code (IAC) configuration.

## Overview

The IAC overwrite endpoint provides a way to completely replace the existing IAC configuration of a stack with a new configuration. This is different from the existing `update_iac` endpoint which only updates specific sections of the IAC.

## Endpoints

### 1. ViewSet Action (Recommended)

**URL:** `POST /api/stacks/{stack_id}/overwrite_iac/`

**Authentication:** Required (OAuth)

**Request Body:**
```json
{
    "iac": {
        "azure": {
            "resource_group": "new-rg",
            "location": "eastus"
        },
        "container_apps": {
            "frontend": {
                "name": "frontend-app",
                "image": "nginx:latest"
            },
            "backend": {
                "name": "backend-app",
                "image": "node:16"
            }
        }
    }
}
```

**Response (Success - 200):**
```json
{
    "success": true,
    "message": "IAC configuration overwritten successfully.",
    "stack_id": "stack-uuid",
    "old_iac": {
        "previous": "configuration"
    },
    "new_iac": {
        "azure": {
            "resource_group": "new-rg",
            "location": "eastus"
        }
    }
}
```

**Response (Error - 400):**
```json
{
    "iac": ["This field is required."]
}
```

**Response (Error - 404):**
```json
{
    "error": "Stack not found."
}
```

**Response (Error - 500):**
```json
{
    "error": "Failed to overwrite IAC configuration. [error details]"
}
```

### 2. Legacy Function-Based View

**URL:** `POST /api/stacks/overwrite-iac/{stack_id}/`

**Authentication:** Required (OAuth)

**Request Body:** Same as ViewSet action

**Response:** Same as ViewSet action

## Features

1. **Complete Overwrite:** Replaces the entire IAC configuration, not just specific sections
2. **Validation:** Ensures the new IAC is a valid JSON object
3. **Deployment:** Automatically deploys the new IAC configuration using DeployBoxIAC
4. **Logging:** Comprehensive logging for debugging and audit purposes
5. **Error Handling:** Proper error responses for various failure scenarios
6. **Backward Compatibility:** Legacy function-based view available

## Usage Examples

### Python Requests

```python
import requests
import json

# ViewSet Action
url = "https://your-domain.com/api/stacks/stack-uuid/overwrite_iac/"
headers = {
    "Authorization": "Bearer your-oauth-token",
    "Content-Type": "application/json"
}

new_iac = {
    "azure": {
        "resource_group": "production-rg",
        "location": "eastus",
        "tags": {
            "environment": "production",
            "project": "my-project"
        }
    },
    "container_apps": {
        "frontend": {
            "name": "frontend-prod",
            "image": "my-frontend:latest",
            "replicas": 3
        },
        "backend": {
            "name": "backend-prod",
            "image": "my-backend:latest",
            "replicas": 2
        }
    }
}

response = requests.post(url, headers=headers, json={"iac": new_iac})
print(response.json())
```

### cURL

```bash
curl -X POST \
  https://your-domain.com/api/stacks/stack-uuid/overwrite_iac/ \
  -H "Authorization: Bearer your-oauth-token" \
  -H "Content-Type: application/json" \
  -d '{
    "iac": {
        "azure": {
            "resource_group": "new-rg",
            "location": "eastus"
        }
    }
}'
```

## Differences from update_iac

| Feature | update_iac | overwrite_iac |
|---------|------------|---------------|
| **Scope** | Updates specific sections | Replaces entire configuration |
| **Parameters** | `data` + `section` | `iac` (complete config) |
| **Use Case** | Incremental updates | Complete replacement |
| **Validation** | Section-specific | Full configuration validation |
| **Deployment** | Yes | Yes |

## Security Considerations

1. **Authentication Required:** All endpoints require OAuth authentication
2. **Authorization:** Users can only overwrite IAC for stacks they have access to
3. **Validation:** Input validation prevents malformed IAC configurations
4. **Logging:** All operations are logged for audit purposes

## Error Handling

The endpoint handles various error scenarios:

- **400 Bad Request:** Invalid JSON, missing required fields
- **404 Not Found:** Stack doesn't exist
- **500 Internal Server Error:** Deployment failures, database errors

## Testing

Run the test suite to verify functionality:

```bash
python manage.py test stacks.tests.StackIACOverwriteTestCase
python manage.py test stacks.tests.StackIACOverwriteIntegrationTestCase
```

## Migration from update_iac

If you're currently using `update_iac` and want to switch to `overwrite_iac`:

1. **Old approach:**
```python
# Update specific sections
data = {"resource_group": "new-rg"}
section = ["azure"]
update_iac(stack_id, data, section)
```

2. **New approach:**
```python
# Overwrite entire configuration
new_iac = {
    "azure": {
        "resource_group": "new-rg",
        "location": "eastus"
    }
}
overwrite_iac(stack_id, new_iac)
```

## Support

For issues or questions about the IAC overwrite functionality, please refer to the test cases in `stacks/tests.py` or contact the development team.

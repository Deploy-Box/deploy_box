# Stack Status Update Endpoint

This document describes the new stack status update endpoint that allows updating the status of a stack given its ID.

## Endpoint

**URL:** `POST /api/stacks/{stack_id}/update_status/`

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
    "status": "RUNNING"
}
```

### Parameters
- `stack_id` (path parameter): The unique identifier of the stack to update
- `status` (body parameter): The new status to set for the stack

## Response

### Success Response (200 OK)
```json
{
    "success": true,
    "message": "Stack status updated successfully to 'RUNNING'",
    "stack_id": "stack_uuid_here",
    "old_status": "STARTING",
    "new_status": "RUNNING"
}
```

### Error Responses

#### 400 Bad Request (Invalid Data)
```json
{
    "status": [
        "This field is required."
    ]
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
    "success": false,
    "error": "Failed to update stack status"
}
```

## Common Status Values

The following are common status values that can be used:

- `STARTING` - Stack is in the process of starting up
- `PROVISIONING` - Stack infrastructure is being provisioned
- `RUNNING` - Stack is running and operational
- `STOPPED` - Stack has been stopped
- `ERROR` - Stack encountered an error
- `DELETING` - Stack is being deleted

## Example Usage

### Using curl
```bash
curl -X POST \
  https://your-domain.com/api/stacks/stack-uuid-here/update_status/ \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your_oauth_token' \
  -d '{
    "status": "RUNNING"
  }'
```

### Using Python requests
```python
import requests

url = "https://your-domain.com/api/stacks/stack-uuid-here/update_status/"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your_oauth_token"
}
data = {
    "status": "RUNNING"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## Notes

- The endpoint requires OAuth authentication
- The status field is required and cannot be empty
- The response includes both the old and new status for tracking purposes
- The stack status is updated in the database immediately upon successful request
- All status updates are logged for audit purposes

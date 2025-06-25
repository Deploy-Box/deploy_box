# Stacks API Documentation

This document describes the new Django REST Framework (DRF) class-based views for the Stacks application.

## Overview

The stacks API has been refactored to use DRF ViewSets and APIViews instead of function-based views. This provides better structure, automatic serialization, and improved error handling.

## ViewSets

### StackViewSet

Manages stack operations with the following endpoints:

#### Base URL: `/api/stacks/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stacks/` | List stacks (requires `stack_id` query parameter) |
| POST | `/api/stacks/` | Create a new stack |
| GET | `/api/stacks/{id}/` | Retrieve a specific stack |
| PUT | `/api/stacks/{id}/` | Update a stack |
| PATCH | `/api/stacks/{id}/` | Partially update a stack |
| DELETE | `/api/stacks/{id}/` | Delete a stack |
| GET | `/api/stacks/{id}/env/` | Get environment variables for a stack |
| POST | `/api/stacks/{id}/env/` | Update environment variables for a stack |
| DELETE | `/api/stacks/{id}/env/` | Delete environment variables for a stack |
| GET | `/api/stacks/{id}/download/` | Download stack source code |

#### Example Usage

**Create a new stack:**
```bash
POST /api/stacks/
Content-Type: application/json

{
    "project_id": "project-uuid",
    "purchasable_stack_id": "stack-uuid",
    "name": "My New Stack"
}
```

**Get a specific stack:**
```bash
GET /api/stacks/stack-uuid/
```

**Update a stack:**
```bash
PATCH /api/stacks/stack-uuid/
Content-Type: application/json

{
    "root_directory": "/app"
}
```

### PurchasableStackViewSet

Manages purchasable stack operations:

#### Base URL: `/api/purchasable-stacks/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/purchasable-stacks/` | List purchasable stacks |
| POST | `/api/purchasable-stacks/` | Create a new purchasable stack |
| GET | `/api/purchasable-stacks/{id}/` | Retrieve a specific purchasable stack |
| PUT | `/api/purchasable-stacks/{id}/` | Update a purchasable stack |
| PATCH | `/api/purchasable-stacks/{id}/` | Partially update a purchasable stack |
| DELETE | `/api/purchasable-stacks/{id}/` | Delete a purchasable stack |

#### Example Usage

**Create a new purchasable stack:**
```bash
POST /api/purchasable-stacks/
Content-Type: application/json

{
    "type": "MERN",
    "variant": "premium",
    "version": "1.0",
    "price_id": "price_stripe_id"
}
```

### StackDatabaseViewSet

Manages stack database operations:

#### Base URL: `/api/stack-databases/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stack-databases/` | List all stack databases |
| POST | `/api/stack-databases/update_usage/` | Update stack database usage |

#### Example Usage

**Get all stack databases:**
```bash
GET /api/stack-databases/
```

**Update database usage:**
```bash
POST /api/stack-databases/update_usage/
Content-Type: application/json

{
    "data": {
        "stack-id-1": 100,
        "stack-id-2": 200
    }
}
```

## API Views

### LogsAPIView

Manages log operations:

#### Base URL: `/api/logs/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/logs/{service_name}/` | Get logs for a specific service |

#### Example Usage

**Get logs for a service:**
```bash
GET /api/logs/my-service/
```

## Authentication

All endpoints require authentication. The API uses the `IsAuthenticated` permission class from DRF.

## Serializers

The API uses the following serializers for data validation and transformation:

- `StackSerializer`: For stack model serialization
- `PurchasableStackSerializer`: For purchasable stack model serialization
- `StackDatabaseSerializer`: For stack database model serialization
- `StackCreateSerializer`: For stack creation validation
- `StackUpdateSerializer`: For stack update validation
- `PurchasableStackCreateSerializer`: For purchasable stack creation validation
- `StackDatabaseUpdateSerializer`: For database usage update validation

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `501 Not Implemented`: Feature not yet implemented

## Legacy Support

The original function-based views are still available for backward compatibility but are deprecated. They will be removed in a future version.

## Migration Guide

To migrate from the old function-based views to the new DRF views:

1. Update your API calls to use the new endpoints
2. Use the new serializers for data validation
3. Handle the new response format (DRF Response objects)
4. Update authentication if needed

## Example Migration

**Old (function-based):**
```python
# Old URL pattern
response = requests.get('/stacks/stack-id/')
```

**New (DRF ViewSet):**
```python
# New URL pattern
response = requests.get('/api/stacks/stack-id/')
```

The response format remains the same, but the underlying implementation is now more robust and follows DRF best practices. 
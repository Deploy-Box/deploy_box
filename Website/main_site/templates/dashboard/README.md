# Stack Dashboard Templates

This directory contains specialized dashboard templates for different stack types in the DeployBox platform.

## Overview

The stack dashboard system provides unique, tailored experiences for different technology stacks, displaying stack-specific properties and functionality.

## Available Templates

### 1. Generic Stack Dashboard (`stack_dashboard.html`)
- **Purpose**: Default dashboard for all stack types
- **Features**: 
  - Basic stack overview
  - Google Cloud Run services
  - Live logs terminal
  - Stack actions (GitHub integration, root directory, download)

### 2. MERN Stack Dashboard (`mern_stack_dashboard.html`)
- **Purpose**: Specialized dashboard for MERN (MongoDB, Express.js, React, Node.js) stacks
- **Features**:
  - MERN-specific service cards (React Frontend, Express.js Backend, MongoDB Database)
  - Service-specific URLs and status monitoring
  - MERN-focused service selector in logs terminal
  - Enhanced visual design with MERN branding

### 3. Django Stack Dashboard (`django_stack_dashboard.html`)
- **Purpose**: Specialized dashboard for Django web application stacks
- **Features**:
  - Django-specific service cards (Django Web Application, MongoDB Database)
  - Django Admin Panel section with direct access
  - Django-focused service selector in logs terminal
  - Django-specific management capabilities

## Template Selection Logic

The system automatically selects the appropriate template based on the stack type:

```python
# In views.py - stack_dashboard method
stack_type = stack.purchased_stack.type.lower()
if stack_type == "mern":
    template_name = "dashboard/mern_stack_dashboard.html"
elif stack_type == "django":
    template_name = "dashboard/django_stack_dashboard.html"
else:
    template_name = "dashboard/stack_dashboard.html"
```

## Stack Properties

### MERN Stack Properties
- `stack.mern_frontend_url` - React frontend application URL
- `stack.mern_backend_url` - Express.js backend API URL
- `stack.mern_mongodb_uri` - MongoDB database connection URI

### Django Stack Properties
- `stack.django_url` - Django web application URL
- `stack.django_mongodb_uri` - MongoDB database connection URI

## JavaScript Integration

Each specialized dashboard includes its own JavaScript file:

### MERN Stack JavaScript (`mern_stack_dashboard.js`)
- MERN-specific service monitoring
- Frontend/Backend/Database health checks
- Service-specific log filtering
- MERN deployment methods

### Django Stack JavaScript (`django_stack_dashboard.js`)
- Django-specific service monitoring
- Django admin panel integration
- Django management commands
- Django app and model management

## Usage

### For MERN Stacks
1. Navigate to a MERN stack dashboard
2. View React Frontend, Express.js Backend, and MongoDB Database service cards
3. Monitor service health and status
4. Access service-specific logs
5. Use MERN-specific deployment features

### For Django Stacks
1. Navigate to a Django stack dashboard
2. View Django Web Application and MongoDB Database service cards
3. Access Django Admin Panel directly
4. Monitor Django application health
5. Use Django-specific management features

## Customization

### Adding New Stack Types
1. Create a new template file (e.g., `mean_stack_dashboard.html`)
2. Create corresponding JavaScript file (e.g., `mean_stack_dashboard.js`)
3. Add stack type logic to the `stack_dashboard` view
4. Define stack-specific properties in the Stack model

### Template Structure
Each specialized template should include:
- Stack-specific header with branding
- Service cards showing stack components
- Service-specific URLs and status
- Customized service selector for logs
- Stack-specific actions and features

## Data Attributes

The dashboard div includes stack type information:
```html
<div id="dashboard" 
     data-organization-id="{{ organization_id }}" 
     data-project-id="{{ project_id }}"
     data-stack-id="{{ stack.id }}" 
     data-service-name="{{ stack_google_cloud_runs.0.id }}" 
     data-stack-type="mern">
</div>
```

## Future Enhancements

- Add more stack types (MEAN, LAMP, MEVN)
- Implement real-time service monitoring
- Add stack-specific metrics and analytics
- Create stack-specific deployment workflows
- Add stack comparison features 
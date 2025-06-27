# Organization Member Management

This document describes the functionality for managing organization members, including leaving and removing members from organizations.

## Features Implemented

### 1. Leave Organization
- **Functionality**: Users can leave an organization themselves
- **Access**: Available to all organization members
- **Restrictions**: 
  - Cannot leave if you're the last admin (must transfer admin role or delete organization first)
- **Email Notification**: Users receive a confirmation email when they leave
- **UI**: Prominent "Leave Organization" button in the members page

### 2. Remove Organization Member
- **Functionality**: Admins can remove other members from the organization
- **Access**: Only organization admins
- **Restrictions**:
  - Cannot remove the last admin from the organization
  - Cannot remove yourself (use "Leave Organization" instead)
- **Email Notification**: Removed members receive a notification email
- **UI**: "Remove" button next to each member (only visible to admins)

## API Endpoints

### Leave Organization
```
POST /api/v1/organizations/{organization_id}/leave_organization
```
- **Authentication**: Required
- **Permissions**: Must be a member of the organization
- **Response**: JSON with success/error message

### Remove Organization Member
```
POST /api/v1/organizations/{organization_id}/remove_org_member/{member_id}
```
- **Authentication**: Required
- **Permissions**: Must be an admin of the organization
- **Response**: JSON with success/error message

## User Interface

### Organization Members Page
The organization members page (`/dashboard/organizations/{organization_id}/members/`) now includes:

1. **Leave Organization Section**: 
   - Prominent amber-colored section at the top
   - Clear explanation of the action
   - Confirmation dialog before leaving

2. **Member List**:
   - Shows all organization members
   - Displays member roles
   - "You" badge for the current user
   - Remove buttons for admins (hidden for non-admins and for the current user)

3. **Permission-Based UI**:
   - Remove buttons only show for admins
   - Remove buttons are hidden for the current user
   - Proper error handling and user feedback

## Security Features

### Permission Checks
- All operations verify user permissions before execution
- Admin-only operations are properly restricted
- Organization membership is validated

### Data Protection
- Cannot remove the last admin (prevents orphaned organizations)
- Cannot leave as the last admin (must transfer or delete)
- Proper error handling and logging

### Email Notifications
- Users receive confirmation emails for all member changes
- Helps maintain audit trail of organization changes

## Error Handling

The system provides clear error messages for various scenarios:

- **Permission Denied**: When non-admins try to remove members
- **Last Admin Protection**: When trying to remove the last admin
- **Not Found**: When organization or member doesn't exist
- **Validation Errors**: When operations would create invalid states

## Usage Examples

### Leaving an Organization
1. Navigate to the organization members page
2. Click the "Leave Organization" button
3. Confirm the action in the dialog
4. Receive confirmation email
5. Redirected to dashboard

### Removing a Member (Admin Only)
1. Navigate to the organization members page
2. Click "Remove" next to the member's name
3. Confirm the action in the dialog
4. Member receives removal notification email
5. Page refreshes to show updated member list

## Technical Implementation

### Backend Components
- **Services**: `organizations/services.py` - Core business logic
- **Handlers**: `organizations/handlers.py` - Request handling
- **Views**: `organizations/views.py` - API endpoints
- **Email Helpers**: `organizations/helpers/email_helpers/invite_org_member.py` - Email notifications

### Frontend Components
- **Template**: `main_site/templates/dashboard/organization_members.html` - UI
- **JavaScript**: Embedded in template for AJAX calls
- **Styling**: Tailwind CSS classes for consistent design

### Database
- Uses existing `OrganizationMember` model
- No schema changes required
- Proper foreign key relationships maintained 
# DEPLOY_BOX_STACK_ENDPOINT Setup Guide

## Overview

The `DEPLOY_BOX_STACK_ENDPOINT` environment variable allows you to configure a custom endpoint for downloading stack source files from each stack dashboard. This provides a flexible way to host stack source files on your own infrastructure while maintaining the existing fallback mechanisms.

## Configuration

### Environment Variable

Set the `DEPLOY_BOX_STACK_ENDPOINT` environment variable to point to your file hosting service:

```bash
export DEPLOY_BOX_STACK_ENDPOINT="https://your-file-server.com/stacks"
```

### URL Structure

The system will construct download URLs by appending the stack ID and filename to your endpoint:

```
{DEPLOY_BOX_STACK_ENDPOINT}/{stack_id}/source.zip
```

**Example:**
- Environment variable: `https://api.deploybox.com/stacks`
- Stack ID: `abc123`
- Final URL: `https://api.deploybox.com/stacks/abc123/source.zip`

## File Requirements

Your file server should:

1. **Host files at the correct path**: `/{stack_id}/source.zip`
2. **Return proper HTTP headers**: The file should be downloadable
3. **Handle authentication**: If required, configure your server appropriately
4. **Return appropriate status codes**: 200 for success, 404 for not found, etc.

## Fallback Behavior

If the `DEPLOY_BOX_STACK_ENDPOINT` is not configured or the download fails, the system will fall back to:

1. **Google Cloud Storage**: `deploy-box-prod-source-code` bucket
2. **GitHub**: Raw GitHub URLs for Deploy-Box repositories

## Testing

To test the functionality:

1. Set the environment variable
2. Navigate to any stack dashboard
3. Click the "Download Stack" button
4. The file should download from your configured endpoint

## Security Considerations

- Ensure your endpoint is properly secured
- Consider implementing rate limiting
- Validate stack IDs to prevent unauthorized access
- Use HTTPS for production environments

## Troubleshooting

### Common Issues

1. **404 Errors**: Ensure files exist at the expected path
2. **Timeout Errors**: Check network connectivity and server response times
3. **Authentication Errors**: Verify any required authentication is properly configured

### Debugging

The system logs download attempts to help with debugging:

```
Attempting to download from: https://your-endpoint.com/stacks/abc123/source.zip
Failed to download from DEPLOY_BOX_STACK_ENDPOINT: [error details]
```

## Example Implementation

Here's a simple example of how your file server might be structured:

```
https://your-file-server.com/
├── stacks/
│   ├── abc123/
│   │   └── source.zip
│   ├── def456/
│   │   └── source.zip
│   └── ghi789/
│       └── source.zip
```

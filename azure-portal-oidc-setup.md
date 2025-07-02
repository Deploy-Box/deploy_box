# Azure OIDC Setup via Azure Portal

This guide walks you through setting up OIDC authentication for GitHub Actions using the Azure Portal website.

## Prerequisites
- Access to Azure Portal (https://portal.azure.com)
- Owner or Contributor access to your Azure subscription
- Your GitHub username

## Step 1: Create App Registration

1. **Go to Azure Portal**: Navigate to https://portal.azure.com
2. **Search for "App registrations"**: In the search bar at the top, type "App registrations" and select it
3. **Click "New registration"**
4. **Fill in the details**:
   - **Name**: `github-actions-oidc`
   - **Supported account types**: Choose "Accounts in this organizational directory only"
   - **Redirect URI**: Leave blank (not needed for OIDC)
5. **Click "Register"**
6. **Copy the Application (client) ID** - you'll need this later

## Step 2: Create Federated Credentials

1. **In your new app registration**, go to the left menu and click **"Certificates & secrets"**
2. **Click the "Federated credentials" tab**
3. **Click "Add credential"**
4. **Choose "GitHub Actions deploying Azure resources"**
5. **Fill in the details**:
   - **Credential name**: `github-actions-main`
   - **Repository**: `YOUR_GITHUB_USERNAME/deploy_box`
   - **Branch**: `main`
   - **Environment**: Leave blank
6. **Click "Add"**
7. **Repeat for dev branch**:
   - **Credential name**: `github-actions-dev`
   - **Repository**: `YOUR_GITHUB_USERNAME/deploy_box`
   - **Branch**: `dev`
   - **Environment**: Leave blank
8. **Click "Add"**

## Step 3: Assign RBAC Permissions

### Understanding Azure Roles

Azure has many roles with "Contributor" in the name. For GitHub Actions to deploy to Azure, you need the **standard "Contributor" role**. Here's how to find it:

**The role you need:**
- **Name**: `Contributor` (exactly this, nothing else)
- **Description**: "Grants full access to manage all resources, but does not allow you to assign roles in Azure RBAC, manage assignments in Azure Blueprints, or share image galleries."
- **Role ID**: `b24988ac-6180-42a0-ab88-20f7382dd24c`

**Roles you DON'T want:**
- Resource Policy Contributor
- Network Contributor  
- Storage Account Contributor
- Any other specific contributor roles

### Assign the Role

1. **Go to your resource group**: Navigate to your `deploy-box-rg-dev` resource group
2. **Click "Access control (IAM)"** in the left menu
3. **Click "Add"** then **"Add role assignment"**
4. **Choose role**: 
   - In the search box, type "Contributor" 
   - Look for the role named exactly **"Contributor"** (not "Resource Policy Contributor" or any other variation)
   - It should have the description: "Grants full access to manage all resources, but does not allow you to assign roles in Azure RBAC, manage assignments in Azure Blueprints, or share image galleries."
5. **Click "Next"**
6. **Assign access to**: Choose "User, group, or service principal"
7. **Click "Select members"**
8. **Search for your app**: Type `github-actions-oidc` and select it
9. **Click "Select"**
10. **Click "Review + assign"**
11. **Click "Assign"**

## Step 4: Get Your Tenant ID

1. **Go to Azure Active Directory**: Search for "Azure Active Directory" in the portal
2. **Copy the Tenant ID** from the Overview page

## Step 5: Add GitHub Secrets

1. **Go to your GitHub repository**: https://github.com/YOUR_USERNAME/deploy_box
2. **Click "Settings"** tab
3. **Click "Secrets and variables"** → **"Actions"**
4. **Click "New repository secret"** and add these three secrets:

   **AZURE_CLIENT_ID**
   - Value: The Application (client) ID from Step 1

   **AZURE_TENANT_ID**
   - Value: The Tenant ID from Step 4

   **AZURE_SUBSCRIPTION_ID**
   - Value: `3106bb2d-2f28-445e-ab1e-79d93bd15979`

## Step 6: Update Your GitHub Actions Workflow

Your workflow is already set up correctly! The `.github/workflows/CICD-oidc.yml` file uses the OIDC authentication method.

## Verification

To verify everything is working:

1. **Push a change** to your main or dev branch
2. **Check the GitHub Actions logs**
3. **Look for the "Log in to Azure" step** - it should succeed without asking for a password

## Troubleshooting

### Common Issues:

1. **"Subject mismatch" error**:
   - Double-check the repository name in the federated credential
   - Ensure it matches exactly: `YOUR_USERNAME/deploy_box`

2. **"Permission denied" error**:
   - Verify the Contributor role is assigned to the app registration
   - Check that the scope is correct (resource group level)

3. **"Audience mismatch" error**:
   - This should be automatic when using the GitHub Actions template in Azure Portal

### If you need to check your setup:

1. **In Azure Portal**: Go to your app registration → Certificates & secrets → Federated credentials
2. **Verify the credentials** are listed correctly
3. **Check role assignments**: Go to your resource group → Access control (IAM) → Role assignments

## Benefits of Portal Setup

- **Visual interface**: Easier to understand and verify
- **No CLI required**: No need to install or troubleshoot Azure CLI
- **Built-in validation**: Portal validates inputs as you enter them
- **Easy to modify**: Simple to update or add new branches/environments

## Next Steps

Once you've completed the setup:

1. **Test the workflow** by pushing a change to your repository
2. **Monitor the logs** to ensure authentication works
3. **Consider adding more branches** if needed (staging, feature branches, etc.)
4. **Set up environment-specific credentials** if you have different environments 
# Deploy Box — Features & User Stories

## Overview

Deploy Box is a Platform-as-a-Service (PaaS) that lets developers deploy pre-configured technology stacks to the cloud. The platform supports multiple stack types (MERN, Django, Redis, Mobile, AI/ML, and more), provides a full organizational hierarchy for team collaboration, handles billing through Stripe, integrates with GitHub for continuous deployment, and offers an API marketplace for consuming and publishing APIs.

**Core hierarchy:** User → Organization → Project → Stack → Cloud Resources

**Infrastructure pipeline:** User actions trigger messages on Azure Service Bus, which are processed by an IAC (Infrastructure-as-Code) container that provisions cloud resources and calls back to the platform with status updates.

---

## 1. Accounts & Authentication

Users can sign up via local credentials or SSO (WorkOS AuthKit supporting Google, GitHub, and email-based login). Every user has a `UserProfile` identified by a ShortUUID, with support for email verification and multiple auth providers.

### Features

- Local account signup with email and password
- WorkOS AuthKit SSO (Google, GitHub, email)
- Invite-based signup that auto-joins the user to an organization
- Transfer-based signup that auto-joins the user to an org and accepts a project transfer
- User profile management (username, email, name)
- Account deletion
- Email verification

### User Stories

#### US-1.1: Local Account Signup

> **As a** new developer, **I want to** sign up with my email and password, **so that** I can create an account and start using the platform.

**Acceptance Criteria:**
- User provides username, email, first name, last name, password, and password confirmation.
- Passwords must match; validation errors are returned otherwise.
- A `UserProfile` is created with `auth_provider = "local"` and a ShortUUID primary key.
- If a `PendingInvite` exists for the user's email, the user is automatically added to the corresponding organization as a member and the invite is deleted.
- The user is logged in immediately after signup.

#### US-1.2: WorkOS SSO Login

> **As a** developer, **I want to** sign in via Google, GitHub, or email through WorkOS AuthKit, **so that** I can use my existing identity provider without managing another password.

**Acceptance Criteria:**
- Clicking "Login" or "Signup" redirects the user to the WorkOS AuthKit hosted login page.
- After authenticating, WorkOS redirects back to the callback endpoint with an authorization code.
- The system exchanges the code for a user profile, creates or links a `UserProfile` by `workos_user_id` or email.
- SSO users have unusable passwords set on their Django user record.
- The WorkOS session ID is stored in the Django session to support SSO logout.
- If a `PendingInvite` exists for the user's email, the user is auto-joined to the organization.

#### US-1.3: Invite-Based Signup

> **As a** person who received an organization invitation, **I want to** sign up using my invite link, **so that** I am automatically added to the inviting organization.

**Acceptance Criteria:**
- The signup request includes an `invite_id` parameter.
- The system validates that the invite exists and the provided email matches the invite's email.
- On successful signup, the user is added to the organization as a member.
- The `PendingInvite` record is deleted after the user joins.
- If the email does not match the invite, a `400` error is returned.

#### US-1.4: Transfer + Invite Signup

> **As a** client who received a project transfer invitation, **I want to** sign up and accept the transfer in one step, **so that** I get immediate access to the transferred project.

**Acceptance Criteria:**
- The signup request includes both `invite_id` and `transfer_id` parameters.
- The user is created, joins the organization, and the project transfer is automatically accepted.
- The transferred project appears in the user's project list under the new organization.

#### US-1.5: Profile Management

> **As a** logged-in user, **I want to** view and update my profile (username, email, first name, last name), **so that** my account information stays current.

**Acceptance Criteria:**
- `GET /api/v1/accounts/profile/` returns the current user's username, email, first name, and last name.
- `POST /api/v1/accounts/profile/` updates the specified fields.
- Username uniqueness is enforced; a `400` error is returned if the username is already taken.
- Email changes are supported with validation.

#### US-1.6: Account Deletion

> **As a** user, **I want to** permanently delete my account, **so that** my data is removed from the platform.

**Acceptance Criteria:**
- `DELETE /api/v1/accounts/delete-account/` logs the user out and deletes the `UserProfile`.
- All associated data (memberships, tokens, webhooks) is cascade-deleted.

---

## 2. Organizations

Organizations are the top-level grouping entity. Each organization has a Stripe customer, a tier (free or consumption), and members with roles. Organizations support inviting new members, managing roles, and transferring projects between organizations.

### Features

- Create, read, update, and delete organizations
- Member management with admin and member roles
- Invite existing platform users to an organization
- Invite non-platform users via email (creates a `PendingInvite`)
- Role toggling (admin ↔ member) with last-admin protection
- Self-removal (leave organization)
- Project transfer between organizations (internal and external)
- Project transfer to external email recipients (with signup flow)
- Transfer audit trail
- Auto-creation of a "Welcome Project" for new organizations

### User Stories

#### US-2.1: Create Organization

> **As a** developer, **I want to** create a new organization, **so that** I have a workspace to manage my projects and team.

**Acceptance Criteria:**
- A Stripe customer is created for the organization before the org record is saved.
- The creating user is added as an `admin` `OrganizationMember`.
- A default "Welcome Project" is automatically created.
- The organization has a `tier` defaulting to `free`.

#### US-2.2: Invite Existing User

> **As an** organization admin, **I want to** add an existing platform user to my organization by username, **so that** they can collaborate on our projects.

**Acceptance Criteria:**
- Only admins can add members.
- The user is looked up by username and added as an `OrganizationMember` with `member` role.
- If the user is already a member, an appropriate error is returned.

#### US-2.3: Invite New User via Email

> **As an** organization admin, **I want to** invite someone who doesn't have a Deploy Box account by email, **so that** they can join my organization when they sign up.

**Acceptance Criteria:**
- Only admins can send invitations.
- A `PendingInvite` record is created with the organization and email.
- An invitation email is sent to the recipient with a signup link containing the invite ID.
- The invite is unique per organization+email combination.
- When the recipient signs up, they are auto-joined to the organization.

#### US-2.4: Update Member Role

> **As an** organization admin, **I want to** toggle a member's role between admin and member, **so that** I can manage permissions within my team.

**Acceptance Criteria:**
- `POST /api/v1/organizations/<org_id>/update_role/<user_id>` toggles the role.
- The last remaining admin cannot be downgraded to member.
- An email notification is sent to the affected user.

#### US-2.5: Remove Organization Member

> **As an** organization admin, **I want to** remove a member from my organization, **so that** they no longer have access to our projects.

**Acceptance Criteria:**
- Only admins can remove members.
- Admins cannot remove themselves (they must use "leave" instead).
- An email notification is sent to the removed user.

#### US-2.6: Leave Organization

> **As an** organization member, **I want to** leave an organization I belong to, **so that** I am no longer associated with it.

**Acceptance Criteria:**
- `POST /api/v1/organizations/<org_id>/leave_organization` removes the user's membership.
- An email notification is sent to the remaining organization members.

#### US-2.7: Initiate Project Transfer (External)

> **As an** organization admin, **I want to** transfer a project to an external client by email, **so that** they can take ownership of the deployed infrastructure.

**Acceptance Criteria:**
- A `ProjectTransferInvitation` is created with status `pending` and a 7-day expiry.
- A `ProjectTransferAudit` entry is logged with action `initiated`.
- If the recipient has no account, a `PendingInvite` is also created and a combined signup+transfer email is sent.
- If the recipient has an account, a transfer-only email is sent.
- The invitation includes `to_email`, `to_name`, `to_company`, and `keep_developer` flag.

#### US-2.8: Accept Project Transfer

> **As a** client who received a transfer invitation, **I want to** accept the project transfer, **so that** the project moves to my organization.

**Acceptance Criteria:**
- The system checks that the invitation has not expired.
- The client's organization is retrieved (or created if it doesn't exist).
- The project's `organization` field is reassigned to the client's org.
- If `keep_developer` is true, the original developer remains as a project member; otherwise, project members are replaced.
- Three audit entries are created: `accepted`, `billing_transferred`, `infrastructure_transferred`.
- Confirmation emails are sent to both the original owner and the client.
- The invitation status is updated to `accepted`.

#### US-2.9: Cancel Project Transfer

> **As an** organization admin who initiated a transfer, **I want to** cancel the pending transfer, **so that** the project remains in my organization.

**Acceptance Criteria:**
- Only pending transfers can be cancelled.
- The invitation status is updated to `declined`.
- An audit entry is logged.

#### US-2.10: View Transfer Status

> **As a** user, **I want to** check the status of a project transfer invitation, **so that** I know whether it is pending, accepted, declined, or expired.

**Acceptance Criteria:**
- `GET /api/v1/organizations/transfers/<transfer_id>/status` returns the current status and audit trail.
- `GET /api/v1/organizations/transfers` lists all transfer invitations for the authenticated user.

---

## 3. Projects

Projects belong to an organization and group stacks together. Each project has members with roles, and membership is enforced for all operations.

### Features

- Create, read, and delete projects
- Auto-assign creator as project admin
- Project membership enforcement
- Project settings (name, description)

### User Stories

#### US-3.1: Create Project

> **As an** organization member, **I want to** create a new project within my organization, **so that** I can group related stacks together.

**Acceptance Criteria:**
- The user must be a member of the target organization.
- A `Project` is created with the given name and description.
- The creating user is automatically added as an admin `ProjectMember`.
- The user is redirected to the organization dashboard after creation.

#### US-3.2: List Projects

> **As a** user, **I want to** see all projects I am a member of, **so that** I can navigate to the ones I work on.

**Acceptance Criteria:**
- `GET /api/v1/projects/` returns only projects where the user is a `ProjectMember`.
- Projects from multiple organizations are included.

#### US-3.3: Delete Project

> **As a** project admin, **I want to** delete a project, **so that** it and its associated stacks are removed.

**Acceptance Criteria:**
- The user must be a member of the project.
- The project and all associated stacks, members, and resources are deleted.

---

## 4. Stacks (Core Product)

Stacks are the heart of Deploy Box. A `PurchasableStack` is a template defining a technology stack (e.g., MERN, Django, Redis). A `Stack` is a deployed instance of a purchasable stack. All stacks are free to deploy. Stack creation triggers an Infrastructure-as-Code pipeline via Azure Service Bus, and resources are provisioned asynchronously.

### Features

- Browse and deploy purchasable stack templates (MERN, Django, Redis, Pong, Mobile, AI/ML)
- Auto-generated stack names (adjective + noun)
- Asynchronous infrastructure provisioning via Azure Service Bus (IAC.CREATE, IAC.UPDATE, IAC.DELETE)
- Stack status tracking (STARTING → Ready → Deleted)
- IAC state stored as JSON (Terraform state)
- Stack-specific computed URLs (frontend, backend, database, Redis)
- Environment variable management (KEY=VALUE pairs and .env file upload)
- Environment management (child stacks linked via `parent_stack`)
- Source code upload (ZIP, max 100MB) and download
- Auto-triggered IAC update on source code upload
- Pre-built stacks for instant delivery
- Traefik edge routing configuration (polled every 60 seconds)
- Resource management system (10+ resource types with per-type managers)
- Bulk resource update callback for IAC pipeline
- Infrastructure diagram generation (nodes, connections, wrappers)
- QR code generation for frontend URLs

### User Stories

#### US-4.1: Browse Available Stacks

> **As a** developer, **I want to** browse the stack marketplace to see all available technology stacks, **so that** I can choose the right one for my project.

**Acceptance Criteria:**
- The stack marketplace page lists all `PurchasableStack` records with name, type, variant, description, and features.
- Stacks are accessible from the project dashboard via the marketplace link.
- The user must be a member of the organization to access the project's marketplace.

#### US-4.2: Deploy a Stack

> **As a** developer, **I want to** deploy a stack to the cloud with one click, **so that** I get a running instance of my chosen technology without manual setup.

**Acceptance Criteria:**
- `POST /api/v1/stacks/` with `project_id` and `purchasable_stack_id` creates a new `Stack`.
- The stack receives an auto-generated name (random adjective + noun).
- The stack status is set to `STARTING`.
- Cloud resources are created via `ResourcesManager.create()` based on the `stack_infrastructure` JSON template.
- An `IAC.CREATE` message is sent to the Azure Service Bus queue with the resource definitions.
- The user can monitor the stack status on the dashboard until it reaches `Ready`.

#### US-4.3: Delete a Stack

> **As a** developer, **I want to** delete a deployed stack, **so that** the cloud resources are deprovisioned and I stop incurring usage.

**Acceptance Criteria:**
- `DELETE /api/v1/stacks/<stack_id>/` sends an `IAC.DELETE` message to the queue.
- The stack status is updated to `Deleted`.
- Deleted stacks are excluded from all list queries.

#### US-4.4: Upload Source Code

> **As a** developer, **I want to** upload my application source code as a ZIP file, **so that** it is deployed to my running stack.

**Acceptance Criteria:**
- `POST /api/v1/stacks/<stack_id>/upload/` accepts a ZIP file (validated by magic bytes).
- The file must be 100MB or smaller.
- The file is uploaded to Azure Blob Storage at `{stack_id}/user-files.zip`.
- An `IAC.UPDATE` is automatically triggered after a successful upload.

#### US-4.5: Download Source Code

> **As a** developer, **I want to** download the current source code deployed on my stack, **so that** I can review or modify it locally.

**Acceptance Criteria:**
- `GET /api/v1/stacks/<stack_id>/download/` returns the ZIP file from the configured download endpoint.

#### US-4.6: Trigger IAC Update

> **As a** developer, **I want to** manually trigger an infrastructure update on my stack, **so that** configuration changes or new code are applied.

**Acceptance Criteria:**
- `POST /api/v1/stacks/<stack_id>/trigger-iac-update/` serializes the stack's resources and sends an `IAC.UPDATE` message.
- If a GitHub webhook is connected, the repository URL and encrypted access token are included in the message.

#### US-4.7: Manage Environment Variables

> **As a** developer, **I want to** set environment variables on my stack, **so that** my application can use configuration values like API keys and database URLs.

**Acceptance Criteria:**
- The environment variables page accepts KEY=VALUE pairs in a textarea or via .env file upload.
- Submitting the form posts the variables to the stack and triggers an IAC update.
- The user can choose the framework (mern/django) and location for the .env file.

#### US-4.8: Manage Stack Environments

> **As a** developer, **I want to** create child environments (e.g., dev, staging) for my stack, **so that** I can test changes without affecting production.

**Acceptance Criteria:**
- Child stacks are linked to a parent via the `parent_stack` foreign key.
- Each child has an `environment_type` (e.g., DEV) and `environment_name`.
- The environments page lists all child stacks for the parent.

#### US-4.9: Traefik Edge Routing

> **As the** platform, **I want to** serve a dynamic Traefik configuration for all active stacks, **so that** the edge router can route traffic to the correct stack by subdomain.

**Acceptance Criteria:**
- `GET /api/v1/stacks/traefik-config/` returns a JSON config with HTTP routers, services, and middleware.
- The config is built from all `DeployBoxrmEdge` resources.
- Routing is subdomain-based with API path stripping middleware.
- The endpoint is unauthenticated (polled by Traefik every 60 seconds).

#### US-4.10: Bulk Resource Update (IAC Callback)

> **As the** IAC pipeline, **I want to** send resource status updates back to the platform, **so that** stack resources reflect their actual provisioned state.

**Acceptance Criteria:**
- `PATCH /api/v1/stacks/bulk-update-resources/` accepts resource updates without authentication (webhook callback).
- Resource model fields are updated in-place based on the payload.
- Stack status may transition from `STARTING` to `Ready` based on resource states.

#### US-4.11: View Stack Dashboard

> **As a** developer, **I want to** see my stack's status, URLs, and infrastructure diagram on a dashboard, **so that** I can monitor and manage my deployment.

**Acceptance Criteria:**
- The stack dashboard shows type-specific information (MERN frontend/backend URLs, Django URL and port, PostgreSQL host/database, Redis URL).
- An infrastructure diagram is rendered with nodes, connections, and wrappers.
- A QR code is generated for the frontend URL.
- GitHub repository info is displayed if a webhook is connected.

---

## 5. Payments & Billing

Deploy Box uses Stripe for payment processing. Organizations are Stripe customers. The billing model is consumption-based with rate cards, monthly invoices, and tiered pricing.

### Features

- Stripe checkout integration (payment and setup modes)
- Payment method management (add, remove, set default)
- Stripe webhook handling
- Consumption-based billing with rate cards (flat rate, per unit, tiered)
- Monthly invoices per organization (draft → open → paid → void)
- Invoice line items auto-calculated from rate cards
- Stripe invoice sync
- Free tier support (card setup without immediate charge)

### User Stories

#### US-5.1: Add Payment Method

> **As an** organization admin, **I want to** add a credit card to my organization, **so that** I can pay for usage and deploy stacks.

**Acceptance Criteria:**
- `POST /api/v1/payments/create-intent/` creates a Stripe `SetupIntent` for securely collecting card details.
- `POST /api/v1/payments/save-payment-method/` attaches the payment method to the org's Stripe customer and sets it as default.
- The card appears in the organization's payment methods list.

#### US-5.2: Manage Payment Methods

> **As an** organization admin, **I want to** view, set default, and remove payment methods, **so that** I can control how my organization is billed.

**Acceptance Criteria:**
- `GET /api/v1/payments/payment-method/<org_id>/` lists all payment methods for the organization.
- `POST /api/v1/payments/payment-method/set-default/` sets a specific payment method as default.
- `DELETE /api/v1/payments/payment-method/delete/` removes a payment method — but the last payment method cannot be deleted.
- When a non-default method is deleted, the next available method becomes the default.

#### US-5.3: Checkout Flow

> **As a** developer, **I want to** go through a checkout flow when deploying a stack, **so that** billing is set up for my usage.

**Acceptance Criteria:**
- `POST /api/v1/payments/checkout/create/<org_id>/` creates a Stripe checkout session.
- If the stack is free and the org has no payment method, the session uses setup mode (card collection only).
- If the stack has a price or the org already has a payment method, the session uses payment mode with `setup_future_usage` for off-session billing.
- On `checkout.session.completed` webhook, the stack is created via `stack_services.add_stack`.

#### US-5.4: View Organization Billing

> **As an** organization admin, **I want to** view my organization's billing dashboard, **so that** I can see payment methods, invoices, and usage.

**Acceptance Criteria:**
- The billing page shows all Stripe payment methods with card brand, last four digits, and default indicator.
- Current month usage and invoice status are displayed.
- The free tier credit ($10) is shown for applicable organizations.

#### US-5.5: Monthly Invoice Generation

> **As the** platform, **I want to** generate monthly invoices for each organization, **so that** usage is billed accurately.

**Acceptance Criteria:**
- An `Invoice` is created per organization per month with status `draft`.
- `InvoiceLineItem` records are created for each stack's metric usage.
- Line amounts are auto-calculated from the associated `RateCard`:
  - **Flat rate:** Fixed amount regardless of usage.
  - **Per unit:** `price_per_unit × units_used`.
  - **Tiered:** Applies escalating rates based on `tiered_pricing_json` tiers.
- The invoice is synced to Stripe and finalized.

---

## 6. Marketplace

The developer marketplace connects clients with developers who specialize in specific stack types. Developers can register their profile and advertise their expertise.

### Features

- Developer profile creation with specializations, hourly rate, and availability
- Browse and filter developers by stack type
- Developer detail pages with bio, links, and specializations

### User Stories

#### US-6.1: Register as Developer

> **As a** developer, **I want to** register my profile on the marketplace, **so that** potential clients can find and hire me.

**Acceptance Criteria:**
- `POST /marketplace/register/` creates a `DeveloperProfile` linked to the user's account.
- The profile includes tagline, bio, hourly rate, availability toggle, and website/GitHub/LinkedIn URLs.
- Specializations are saved as a many-to-many relationship to `PurchasableStack`.
- A user cannot register more than one developer profile (redirects if already registered).

#### US-6.2: Browse Developers

> **As a** client, **I want to** browse available developers and filter by stack specialization, **so that** I can find someone with the right skills for my project.

**Acceptance Criteria:**
- `GET /marketplace/` lists all developers where `is_available = True`.
- The `?stack=<type>` query parameter filters developers by stack specialization.
- Each listing shows the developer's tagline, hourly rate, and specializations.

#### US-6.3: View Developer Profile

> **As a** client, **I want to** view a developer's full profile, **so that** I can assess their experience and contact them.

**Acceptance Criteria:**
- `GET /marketplace/profile/<profile_id>/` shows the full developer profile including bio, hourly rate, availability, specializations, and external links (website, GitHub, LinkedIn).

---

## 7. GitHub Integration

Deploy Box integrates with GitHub for continuous deployment. Users connect their GitHub account via OAuth, link a repository to a stack, and pushes to `main` automatically trigger redeployments.

### Features

- GitHub OAuth flow with encrypted token storage (Fernet)
- List user's GitHub repositories
- Create webhooks on GitHub repos linked to stacks
- Automatic repo switching (old webhook disconnected, new one connected)
- Push-to-deploy: pushes to `main` trigger IAC.UPDATE
- HMAC-SHA256 webhook signature verification
- Unlink GitHub account (removes all webhooks and tokens)

### User Stories

#### US-7.1: Connect GitHub Account

> **As a** developer, **I want to** connect my GitHub account to Deploy Box, **so that** I can link repositories to my stacks for automated deployments.

**Acceptance Criteria:**
- `GET /api/v1/github/auth/login/` redirects to GitHub OAuth with `repo` scope.
- The state parameter is encrypted with `{user_id, next_url}` to prevent CSRF.
- After authorization, the callback exchanges the code for an access token.
- The access token is encrypted with Fernet and stored in the `Token` model.
- GitHub user info is saved in the Django session.

#### US-7.2: List GitHub Repositories

> **As a** developer, **I want to** see a list of my GitHub repositories, **so that** I can choose which one to link to my stack.

**Acceptance Criteria:**
- `GET /api/v1/github/repositories/json/` returns up to 100 repositories as JSON.
- The endpoint requires an active GitHub connection (valid encrypted token).

#### US-7.3: Create GitHub Webhook

> **As a** developer, **I want to** link a GitHub repository to my stack, **so that** pushes to the repository automatically trigger deployments.

**Acceptance Criteria:**
- `POST /api/v1/github/webhook/create/` creates a webhook on the specified GitHub repo.
- If the stack already has a webhook to a different repo, the old webhook is disconnected first.
- The webhook listens for `push` events.
- A `Webhook` record is created with the repo name, GitHub webhook ID, and HMAC secret.
- An IAC update is triggered immediately after webhook creation.

#### US-7.4: Push-to-Deploy

> **As a** developer, **I want** pushes to the `main` branch of my linked repository to automatically redeploy my stack, **so that** my live environment stays up to date.

**Acceptance Criteria:**
- `POST /api/v1/github/webhook/` receives GitHub push events.
- The webhook payload signature is verified using HMAC-SHA256 with the stored secret.
- Only `push` events on the `main` branch are processed.
- An `IAC.UPDATE` message is sent to the Azure Service Bus queue to trigger redeployment.

#### US-7.5: Disconnect GitHub Webhook

> **As a** developer, **I want to** disconnect a GitHub repository from my stack, **so that** pushes no longer trigger deployments.

**Acceptance Criteria:**
- `POST /api/v1/github/webhook/disconnect/` deletes the webhook from GitHub's API and removes the local `Webhook` record.
- The user must be a project member to disconnect.

#### US-7.6: Unlink GitHub Account

> **As a** developer, **I want to** unlink my GitHub account from Deploy Box entirely, **so that** all repository connections are removed and my token is deleted.

**Acceptance Criteria:**
- `POST /api/v1/github/unlink/` deletes all of the user's webhooks from the GitHub API and the local database.
- The encrypted token is deleted from the `Token` model.
- GitHub session data is cleared.

---

## 8. Blog & Content

The platform includes a blog for publishing articles, tutorials, and announcements. Blog posts support rich text editing and tagging.

### Features

- Blog post creation with CKEditor5 rich text editor
- Auto-generated slugs from titles
- Tag support via django-taggit
- Blog listing and detail views

### User Stories

#### US-8.1: Read Blog Posts

> **As a** visitor, **I want to** browse and read blog posts on the Deploy Box website, **so that** I can learn about the platform and stay informed about updates.

**Acceptance Criteria:**
- `GET /blogs/` lists all blog posts with title, author, tags, and publication date.
- `GET /blogs/<slug>/` displays the full blog post with CKEditor5-rendered rich text content.
- Blog pages are publicly accessible (no authentication required).

#### US-8.2: Publish Blog Post

> **As an** admin, **I want to** create and publish blog posts with rich text formatting and tags, **so that** I can communicate with the platform's user community.

**Acceptance Criteria:**
- Blog posts are created via the Django admin interface.
- The `slug` field is auto-generated from the `title` on first save.
- Rich text content is authored using CKEditor5.
- Tags are managed via django-taggit and displayed on the listing and detail pages.

---

## 9. API Marketplace

The API Marketplace allows projects to consume platform APIs. It supports two authentication mechanisms: OAuth2 client credentials for server-to-server communication, and Google-style public API keys (prefixed with `dbx_`).

### Features

- Browse available APIs with descriptions, pricing, and features
- OAuth2 client credentials generation, revocation, and rotation
- Token generation via client credentials grant
- Public API key generation (`dbx_` prefix, SHA-256 hash storage)
- API key revocation (soft delete) and listing
- API key validation (internal endpoint for the Functions app)
- Per-project API usage tracking
- Service Bus-triggered usage increment

### User Stories

#### US-9.1: Browse APIs

> **As a** developer, **I want to** browse the API marketplace to see available APIs, their features, and pricing, **so that** I can decide which APIs to integrate into my project.

**Acceptance Criteria:**
- The API marketplace page lists all `API` records with name, description, category, price per 1,000 requests, response time, and feature list.
- Per-project usage counts are displayed for each API.

#### US-9.2: Generate OAuth2 Client Credentials

> **As a** developer, **I want to** generate OAuth2 client credentials for my project, **so that** my server can authenticate with Deploy Box APIs.

**Acceptance Criteria:**
- `POST /api/v1/deploy-box-apis/generate/` creates an `APICredential` with `client_id` and `client_secret` for the project.
- The `client_secret_hint` (masked version) is stored for display.
- One credential set per project (OneToOne relationship).

#### US-9.3: Rotate Client Credentials

> **As a** developer, **I want to** rotate my project's client credentials, **so that** I can maintain security without service interruption.

**Acceptance Criteria:**
- `POST /api/v1/deploy-box-apis/rotate/` generates new credentials via the external API service.
- The local `APICredential` record is updated with the new values.

#### US-9.4: Generate API Token

> **As a** developer, **I want to** exchange my client credentials for a short-lived access token, **so that** I can make authenticated API requests.

**Acceptance Criteria:**
- `POST /api/v1/deploy-box-apis/generate_token/` accepts `client_id` and `client_secret`.
- Returns an access token via the OAuth2 client credentials grant flow.

#### US-9.5: Generate Public API Key

> **As a** developer, **I want to** generate a public API key for my project, **so that** I can make API calls from client-side code.

**Acceptance Criteria:**
- `POST /api/v1/deploy-box-apis/keys/generate/` creates a `dbx_` prefixed key (40 URL-safe characters).
- The raw key is returned only once in the response.
- The key is stored as a SHA-256 hash in the `APIKey` model.
- A `key_hint` (masked display version) is stored for the UI.

#### US-9.6: Revoke API Key

> **As a** developer, **I want to** revoke an API key, **so that** it can no longer be used to access APIs.

**Acceptance Criteria:**
- `POST /api/v1/deploy-box-apis/keys/revoke/` sets `is_active = False` on the key (soft delete).
- The key hash remains in the database but is no longer valid.

#### US-9.7: List API Keys

> **As a** developer, **I want to** see all API keys for my project, **so that** I can manage and audit access.

**Acceptance Criteria:**
- `GET /api/v1/deploy-box-apis/keys/` returns all API keys for the project with name, hint, active status, and creation date.

#### US-9.8: Validate API Key (Internal)

> **As the** platform's Functions app, **I want to** validate an incoming API key, **so that** I can authorize the request and identify the project.

**Acceptance Criteria:**
- `POST /api/v1/deploy-box-apis/keys/validate/` accepts a raw key, computes the SHA-256 hash, and looks up the matching `APIKey`.
- Returns the associated `project_id` if the key is active.
- Returns an error if the key is invalid or revoked.

---

## 10. Dashboard & Frontend

The dashboard provides a hierarchical navigation experience: organizations → projects → stacks. It is the primary UI for managing all platform resources.

### Features

- Organization dashboard with projects, members, and admin controls
- Project dashboard with stack listing and deletion
- Stack dashboard with type-specific views, infrastructure diagrams, and QR codes
- Stack settings, environment variables, and environment management pages
- Billing dashboard with payment method management
- Member management with invite and role controls
- Transfer invitation management
- Welcome screen for new users
- Public marketing pages (home, stacks, pricing, contact)
- Stack landing pages per technology type

### User Stories

#### US-10.1: Navigate Dashboard Hierarchy

> **As a** logged-in user, **I want to** navigate from my organizations to their projects and then to individual stacks, **so that** I can manage all my deployments from one interface.

**Acceptance Criteria:**
- `/dashboard/` redirects to the first organization's dashboard, or shows a welcome screen if the user has no organizations.
- The organization dashboard lists all projects and members.
- Each project links to its project dashboard, which lists non-deleted stacks.
- Each stack links to its type-specific stack dashboard.

#### US-10.2: Organization Members Page

> **As an** organization admin, **I want to** manage members and invitations from the members page, **so that** I can control who has access.

**Acceptance Criteria:**
- `/dashboard/organizations/<org_id>/members/` shows current members with roles and pending invitations.
- Admins can add existing users, invite new users by email, toggle roles, and remove members.

#### US-10.3: Stack Settings

> **As a** developer, **I want to** rename my stack from the settings page, **so that** I can give it a meaningful name.

**Acceptance Criteria:**
- `/dashboard/.../stacks/<stack_id>/settings/` provides a form to edit the stack name.
- Changes are saved and reflected across the dashboard.

#### US-10.4: Project Transfer Acceptance Page

> **As a** client who received a transfer invitation, **I want to** accept the transfer from a dedicated page, **so that** the process is clear and straightforward.

**Acceptance Criteria:**
- `/project-transfer/accept/<transfer_id>/` displays transfer details and an acceptance form.
- Email validation is performed to confirm the recipient's identity.
- On acceptance, the project is reassigned as described in US-2.8.

#### US-10.5: View Transfer Invitations

> **As a** user, **I want to** see all pending transfer invitations sent to me, **so that** I can accept or decline them.

**Acceptance Criteria:**
- `/dashboard/transfers/` lists all `ProjectTransferInvitation` records associated with the user.
- Each invitation shows the project name, source organization, status, and expiry date.

---

## 11. Cron Jobs

Scheduled tasks run as standalone Python scripts in a container (crontainer), authenticating via OAuth2 client credentials.

### Features

- MongoDB database size monitoring for all stacks
- Monthly billing history update trigger

### User Stories

#### US-11.1: Monitor MongoDB Database Size

> **As the** platform, **I want to** periodically check the MongoDB storage size for all stacks, **so that** usage can be tracked and billed accurately.

**Acceptance Criteria:**
- The `check_db_size` cron job authenticates via OAuth2 client credentials.
- It connects to each stack's MongoDB database and runs `dbstats` to measure `storageSize`.
- The results are reported back to the Deploy Box API for recording.

#### US-11.2: Trigger Monthly Billing Update

> **As the** platform, **I want to** trigger monthly billing history generation automatically, **so that** invoices are created on schedule without manual intervention.

**Acceptance Criteria:**
- The `update_billing_history` cron job runs on a monthly schedule.
- It calls `POST /api/v1/payments/update_billing_history/` to generate or update invoices for all organizations.
- The job authenticates via OAuth2 client credentials.

---

## 12. Platform Infrastructure & Middleware

### Features

- Login-required middleware with configurable public paths
- ShortUUID primary keys across all models
- Encrypted OAuth state parameters
- HMAC webhook signature verification
- Custom request body parser (JSON and form-urlencoded)
- LoginRequiredMiddleware with public URL allowlist

### User Stories

#### US-12.1: Authenticated Access Enforcement

> **As the** platform, **I want to** require authentication for all dashboard and API routes while keeping marketing pages public, **so that** user data is protected.

**Acceptance Criteria:**
- The `LoginRequiredMiddleware` intercepts all requests.
- Public paths (`/`, `/login/`, `/signup/`, `/stacks/`, `/pricing/`, `/contact/`, `/marketplace/`, `/blogs/`, `/admin/`, `/api/`, `/static/`, `/media/`, etc.) are accessible without authentication.
- All other routes redirect unauthenticated users to the login page.
- API endpoints return `401 Unauthorized` JSON responses for unauthenticated requests.

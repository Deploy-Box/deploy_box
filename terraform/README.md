# Terraform Best Practices

A reference guide for building and maintaining a well-structured Terraform project. Every pattern described here is demonstrated in this directory — follow the layout and conventions below to recreate the setup from scratch.

---

## Table of Contents

1. [Directory Layout](#1-directory-layout)
2. [File Organization](#2-file-organization)
3. [Backend & Remote State](#3-backend--remote-state)
4. [Environment Separation](#4-environment-separation)
5. [Naming Conventions](#5-naming-conventions)
6. [Variables](#6-variables)
7. [Locals](#7-locals)
8. [Data Sources](#8-data-sources)
9. [Resources](#9-resources)
10. [Outputs](#10-outputs)
11. [Tagging Strategy](#11-tagging-strategy)
12. [Identity & Least-Privilege Access](#12-identity--least-privilege-access)
13. [Dependency Management](#13-dependency-management)
14. [CI/CD Integration](#14-cicd-integration)
15. [Security](#15-security)
16. [General Rules of Thumb](#16-general-rules-of-thumb)

---

## 1. Directory Layout

Keep the root flat and push per-environment configuration into subdirectories.

```
terraform/
├── main.tf              # Provider, locals, data sources, resources
├── variables.tf         # All input variable declarations
├── outputs.tf           # All output declarations
├── config/              # Backend configuration per environment
│   ├── backend-dev.conf
│   ├── backend-test.conf
│   └── backend-prod.conf
└── tfvars/              # Variable values per environment
    ├── dev.tfvars
    ├── test.tfvars
    └── prod.tfvars
```

### Why this layout?

- **One set of `.tf` files** — the same code path is used for every environment. Drift between environments is eliminated because there is only one definition of the infrastructure.
- **`config/`** — partial backend configs let you point `terraform init` at a different state file per environment without duplicating the backend block.
- **`tfvars/`** — each file holds the values that make an environment unique (hostnames, database names, client IDs, etc.). `terraform plan` and `apply` accept `-var-file=tfvars/<env>.tfvars`.

### When to add more files

As the project grows, split `main.tf` along resource boundaries:

```
terraform/
├── main.tf              # Provider config + locals
├── container_app.tf     # Container App resource
├── identity.tf          # Managed Identity + role assignments
├── variables.tf
├── outputs.tf
├── config/
└── tfvars/
```

A good rule: **if you have to scroll past multiple section banners to find what you need, it's time to split.**

### When to add modules

Introduce a `modules/` directory when you find yourself **repeating** the same cluster of resources (e.g., the same Container App + identity + role assignments for multiple services):

```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
├── modules/
│   └── container-app/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── config/
└── tfvars/
```

Do **not** create a module for a single use-case — modules add indirection and should earn their place.

---

## 2. File Organization

Within each `.tf` file, use section banners to group logically related blocks. This makes scanning a long file fast and predictable.

```hcl
# =============================================================================
# Section Name
# =============================================================================
```

### Recommended ordering inside `main.tf`

| Order | Section | Contents |
|-------|---------|----------|
| 1 | Terraform / Backend | `terraform {}` block |
| 2 | Provider | `provider` blocks |
| 3 | Locals | `locals {}` — derived names, tags, shortcuts |
| 4 | Data Sources | `data` blocks (existing infrastructure lookups) |
| 5 | Resources | `resource` blocks, grouped by logical service |

### In `variables.tf`

Group variables by domain and place the most important / most-referenced groups first:

```hcl
# Core application configuration
variable "app" { ... }

# Authentication / OAuth2
variable "auth" { ... }

# Database connection
variable "database" { ... }

# External service endpoints
variable "services" { ... }

# Tags
variable "extra_tags" { ... }
```

### In `outputs.tf`

Mirror the variable grouping so consumers of this configuration can find outputs intuitively.

---

## 3. Backend & Remote State

### Always use remote state

Local `.tfstate` files are a single point of failure and cannot be shared. Use a remote backend with locking. For Azure, that means an **Azure Storage Account** with blob containers:

```hcl
terraform {
  backend "azurerm" {
    use_oidc = true   # Authenticate via OIDC — no storage keys needed
  }
}
```

### Use partial configuration files

Hardcoding the backend in `main.tf` ties the code to one environment. Instead, extract the varying parts into `config/backend-<env>.conf`:

```properties
# config/backend-dev.conf
resource_group_name  = "deploy-box-rg-dev"
storage_account_name = "tfstatedeployboxsadev"
container_name       = "tfstate"
key                  = "deploy-box-dev-terraform.tfstate"
```

Initialize with:

```bash
terraform init -backend-config=config/backend-dev.conf
```

### State file per environment

Every environment **must** have its own state file (the `key` field). This guarantees that `terraform destroy` in dev can never touch prod resources.

### State file naming convention

Use a predictable pattern: `<project>-<env>-terraform.tfstate`. This makes it easy to locate state files in the storage account.

---

## 4. Environment Separation

### Same code, different values

Environment-specific values live **exclusively** in `tfvars/` files. The `.tf` files themselves contain **zero** environment-specific values.

```bash
# Dev
terraform plan -var-file=tfvars/dev.tfvars

# Prod
terraform plan -var-file=tfvars/prod.tfvars
```

### Mirror `tfvars` files exactly

Every `tfvars` file should declare the same set of variables in the same order. This makes diffing across environments trivial:

```bash
diff tfvars/dev.tfvars tfvars/prod.tfvars
```

### Never use `terraform.tfvars`

The auto-loaded `terraform.tfvars` file silently injects values that are easy to forget about. Always use explicit `-var-file` flags so the intent is clear.

---

## 5. Naming Conventions

### Derive all names in `locals`

Define a central `locals` block that computes every resource name from a small set of inputs (prefix + environment). This guarantees consistency:

```hcl
locals {
  env            = var.app.environment
  prefix         = "deploy-box"
  prefix_compact = "deploybox"       # For resources that forbid hyphens

  names = {
    resource_group = "${local.prefix}-rg-${local.env}"
    container_app  = "${local.prefix}-website-contapp-${local.env}"
    acr            = "${local.prefix_compact}cr${local.env}"
    key_vault      = "${local.prefix}-kv-${local.env}"
  }
}
```

### Benefits

- **One place to change** — renaming a service or changing the pattern is a single edit.
- **Readable references** — `local.names.container_app` is self-documenting compared to a raw interpolation string scattered across resources.
- **Compact variant** — some Azure resources (ACR, Storage Accounts) prohibit hyphens. Keep a `prefix_compact` so the pattern is still systematic.

### Pattern

```
<project>-<resource-type>-<environment>
```

Use short, well-known abbreviations for resource types (`rg`, `kv`, `cr`, `cae`, `contapp`, `sbns`, `sa`, etc.).

---

## 6. Variables

### Use structured objects over flat variables

Group related inputs into typed objects. This reduces variable count, improves readability, and makes `tfvars` files scannable:

```hcl
variable "database" {
  description = "PostgreSQL connection parameters."
  type = object({
    name = string
    user = string
    host = string
    port = optional(string, "5432")    # Defaults keep tfvars minimal
  })

  validation {
    condition     = can(regex("^[0-9]+$", var.database.port))
    error_message = "database.port must be a numeric string."
  }
}
```

### Every variable must have

| Attribute | Required? | Purpose |
|-----------|-----------|---------|
| `description` | **Yes** | Documents intent for plan output and future contributors |
| `type` | **Yes** | Catches misconfiguration early |
| `default` | When sensible | Use `optional()` inside objects for individual field defaults |
| `sensitive` | When applicable | Prevents values from being displayed in plan/apply output |
| `validation` | When applicable | Fail fast with a clear message rather than a cryptic provider error |

### Mark secrets as `sensitive`

```hcl
variable "auth" {
  description = "OAuth2 and GitHub OAuth client IDs."
  sensitive   = true
  type = object({ ... })
}
```

Terraform will redact these values from CLI output and state won't be stored in plain text in logs.

### Use `optional()` with defaults

For fields that have a sensible default, use the `optional()` modifier so environments that match the default don't need to declare them:

```hcl
port = optional(string, "5432")
```

---

## 7. Locals

### What belongs in `locals`

- **Derived names** — any string that combines a variable with a constant pattern.
- **Computed tags** — merge base tags with user-supplied extras.
- **Shortcuts** — values referenced more than once (`local.env` is shorter than `var.app.environment`).

### What does NOT belong in `locals`

- **Configurable values** — those belong in `variables.tf`.
- **Secrets** — those belong in a vault, referenced via data sources.
- **Logic with side effects** — keep locals purely computational.

```hcl
locals {
  common_tags = merge(
    {
      ManagedBy   = "Terraform"
      Environment = local.env
    },
    var.extra_tags,
  )
}
```

---

## 8. Data Sources

### Use data sources for pre-existing infrastructure

Resources that are created outside of this Terraform configuration (or by a different state) should be referenced as `data` blocks, not `resource` blocks:

```hcl
data "azurerm_resource_group" "main_rg" {
  name = local.names.resource_group
}

data "azurerm_key_vault" "shared_key_vault" {
  name                = local.names.key_vault
  resource_group_name = local.names.resource_group
}
```

### When to use `data` vs `resource`

| Use `data` when… | Use `resource` when… |
|-------------------|----------------------|
| The resource is managed elsewhere (other team, ClickOps, different state) | This Terraform config is the source of truth |
| You only need to read attributes (IDs, endpoints) | You need to create, update, or destroy the resource |
| The resource's lifecycle should not be tied to this `terraform destroy` | The resource should be torn down with this config |

---

## 9. Resources

### Group related resources together

Keep a resource and its direct dependencies (identity, role assignments, etc.) in the same section:

```hcl
# =============================================================================
# Container App
# =============================================================================

resource "azurerm_container_app" "container_app" { ... }

# =============================================================================
# Managed Identity & Role Assignments
# =============================================================================

resource "azurerm_user_assigned_identity" "container_app_identity" { ... }

resource "azurerm_role_assignment" "container_app_acr_pull" { ... }

resource "azurerm_role_assignment" "container_app_key_vault_secrets_user" { ... }
```

### Use meaningful resource names

The label after the resource type should describe **what** the resource is, not just repeat the type:

```hcl
# Good
resource "azurerm_role_assignment" "container_app_acr_pull" { ... }

# Bad
resource "azurerm_role_assignment" "role1" { ... }
```

### Pin resource configuration with `depends_on` only when necessary

Terraform infers most dependencies automatically from attribute references. Use explicit `depends_on` only when there is a dependency that **cannot** be inferred (e.g., IAM propagation delays):

```hcl
depends_on = [
  azurerm_role_assignment.container_app_acr_pull,
  azurerm_role_assignment.container_app_key_vault_secrets_user,
]
```

---

## 10. Outputs

### Output what consumers need

Outputs serve two audiences: **humans** reading plan output and **other Terraform configs** consuming this state via `terraform_remote_state` or data sources.

```hcl
output "app_host" {
  value       = var.app["host"]
  description = "The host URL for the app environment."
}
```

### Every output must have a `description`

Without descriptions, outputs become opaque to anyone who didn't write them.

### Avoid outputting secrets

If you must output a sensitive value, mark it `sensitive = true`. Prefer referencing secrets from Key Vault at runtime rather than passing them through Terraform outputs.

---

## 11. Tagging Strategy

### Tag every resource

Tags are the primary mechanism for cost allocation, access auditing, and filtering in the Azure portal.

### Compute a base tag set in `locals`

```hcl
locals {
  common_tags = merge(
    {
      ManagedBy   = "Terraform"
      Environment = local.env
    },
    var.extra_tags,
  )
}
```

### Apply `local.common_tags` to every resource

```hcl
resource "azurerm_user_assigned_identity" "container_app_identity" {
  ...
  tags = local.common_tags
}
```

### Minimum recommended tags

| Tag | Value | Purpose |
|-----|-------|---------|
| `ManagedBy` | `Terraform` | Identifies IaC-managed resources vs manual ones |
| `Environment` | `dev` / `test` / `prod` | Cost filtering, access policies |

Allow teams to add extra tags via the `extra_tags` variable without modifying the Terraform code.

---

## 12. Identity & Least-Privilege Access

### Use User-Assigned Managed Identities

Prefer **user-assigned** identities over system-assigned when the identity needs to be referenced before the resource exists, or when multiple resources share the same identity:

```hcl
resource "azurerm_user_assigned_identity" "container_app_identity" {
  name                = local.names.identity
  location            = data.azurerm_resource_group.main_rg.location
  resource_group_name = data.azurerm_resource_group.main_rg.name
  tags                = local.common_tags
}
```

### Scope role assignments as tightly as possible

Grant only the permissions the workload actually needs, scoped to the specific resource — never the subscription:

```hcl
resource "azurerm_role_assignment" "container_app_acr_pull" {
  scope                = data.azurerm_container_registry.acr.id        # Scoped to this ACR only
  role_definition_name = "AcrPull"                                      # Read-only
  principal_id         = azurerm_user_assigned_identity.container_app_identity.principal_id
}
```

---

## 13. Dependency Management

### Pin your provider version

Use the `.terraform.lock.hcl` lock file (committed to version control) to ensure every team member and CI runner uses the exact same provider version:

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.60"
    }
  }
  required_version = ">= 1.5"
}
```

### Commit `.terraform.lock.hcl`

This file is the Terraform equivalent of a `package-lock.json`. Always commit it.

### Do NOT commit `.terraform/`

The `.terraform/` directory contains downloaded providers (hundreds of MB). Add it to `.gitignore`:

```
.terraform/
*.tfstate
*.tfstate.backup
```

---

## 14. CI/CD Integration

### Inject dynamic values via `-var`

Values that change every deployment (like a container image tag) should be passed at apply-time, not baked into `tfvars`:

```hcl
variable "image_name" {
  description = "Fully-qualified container image (injected by CI at apply-time)."
  type        = string
}
```

```bash
terraform apply \
  -var-file=tfvars/prod.tfvars \
  -var="image_name=deployboxcrprod.azurecr.io/website:abc123"
```

### Use OIDC authentication

Avoid storing service principal secrets. Use OpenID Connect (OIDC) federation so your CI pipeline authenticates without long-lived credentials:

```hcl
terraform {
  backend "azurerm" {
    use_oidc = true
  }
}

provider "azurerm" {
  features {}
  use_oidc = true
}
```

### Standard CI pipeline steps

```
1. terraform init   -backend-config=config/backend-<env>.conf
2. terraform plan   -var-file=tfvars/<env>.tfvars -var="image_name=..." -out=tfplan
3. terraform apply  tfplan
```

Always save the plan to a file (`-out=tfplan`) and apply **that exact plan**. This prevents changes between plan and apply.

---

## 15. Security

### Never store secrets in `tfvars`

Use a secrets manager (Azure Key Vault, GitHub Actions secrets, etc.) and pass secrets via environment variables or `-var` flags in CI. If a secret must appear in a `tfvars` file for local development, ensure the file is in `.gitignore`.

### Mark sensitive variables

```hcl
variable "auth" {
  sensitive = true
  ...
}
```

### Use Key Vault references at runtime

Rather than injecting secrets as plain-text environment variables, have the application read from Key Vault using its managed identity at startup. The Terraform config only needs to grant `Key Vault Secrets User` access.

### Encrypt state at rest

Azure Storage backend encrypts blobs by default. Verify this is enabled. Never store state in a public blob container.

---

## 16. General Rules of Thumb

| Rule | Why |
|------|-----|
| **Format your code** — run `terraform fmt -recursive` before every commit | Consistent style, cleaner diffs |
| **Validate early** — run `terraform validate` in CI before plan | Catches syntax and type errors without provider calls |
| **Plan before apply** — never run `apply` without reviewing a plan | Prevents accidental destruction |
| **One state per environment** | Isolates blast radius |
| **Minimize `depends_on`** | Let Terraform infer the graph; explicit deps hide implicit relationships |
| **Don't hardcode** — if a value varies per environment, it's a variable | Keeps the code reusable |
| **Use `terraform import`** for existing resources | Brings manually-created resources under Terraform management without recreation |
| **Review plan output in PRs** | Post `terraform plan` output as a PR comment so reviewers see the real impact |

---

## Quick Start — Recreating This Setup

```bash
# 1. Create the directory structure
mkdir -p terraform/config terraform/tfvars

# 2. Create the files
touch terraform/main.tf
touch terraform/variables.tf
touch terraform/outputs.tf
touch terraform/config/backend-{dev,test,prod}.conf
touch terraform/tfvars/{dev,test,prod}.tfvars

# 3. Add .gitignore entries
echo ".terraform/" >> terraform/.gitignore
echo "*.tfstate" >> terraform/.gitignore
echo "*.tfstate.backup" >> terraform/.gitignore

# 4. Initialize for a specific environment
cd terraform
terraform init -backend-config=config/backend-dev.conf

# 5. Plan
terraform plan -var-file=tfvars/dev.tfvars -out=tfplan

# 6. Apply
terraform apply tfplan
```

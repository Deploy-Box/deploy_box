"""ResourceTypeRegistry — defines per-type defaults, naming, and parent mapping.

Adding a new resource type = adding one ResourceTypeDefinition here.
No model or migration needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from stacks.models import Stack


def _env() -> str:
    return os.getenv("ENV", "DEV").lower()


def _azurerm_provider_name(stack: "Stack", index: int, prefix: str) -> str:
    env = _env()
    if env == "prod":
        return f"{prefix}-{index}-{stack.pk}"
    return f"{prefix}-{index}-{stack.pk}-{env}"


def _storage_account_provider_name(stack: "Stack", index: int, prefix: str) -> str:
    env = _env()
    if env == "prod":
        return f"sa{index}{stack.pk}"
    return f"sa{index}{stack.pk}{env}"


def _nile_provider_name(stack: "Stack", index: int, prefix: str) -> str:
    env = _env()
    if env == "prod":
        return f"{prefix}_{index}_{stack.pk}"
    return f"{prefix}_{index}_{stack.pk}_{env}"


@dataclass(frozen=True)
class ResourceTypeDefinition:
    """Immutable definition for a resource type."""

    resource_type: str
    prefix: str
    display_name: str
    category: str = "Other"
    parent_type: str | None = None

    # Default attribute values applied on creation
    default_attributes: dict[str, Any] = field(default_factory=dict)

    # Callable: (stack, index, prefix) → provider_name
    generate_provider_name: Callable[..., str] | None = None


# ---------------------------------------------------------------------------
# Type definitions (one per resource type, replaces 17 model files)
# ---------------------------------------------------------------------------

AZURERM_RESOURCE_GROUP = ResourceTypeDefinition(
    resource_type="azurerm_resource_group",
    prefix="res000",
    display_name="Resource Group",
    category="Infrastructure",
    parent_type=None,
    default_attributes={"location": "eastus"},
    generate_provider_name=lambda s, i, p: (
        f"{p}_{i}_{s.pk}" if _env() == "prod" else f"{p}_{i}_{s.pk}_{_env()}"
    ),
)

AZURERM_STORAGE_ACCOUNT = ResourceTypeDefinition(
    resource_type="azurerm_storage_account",
    prefix="res002",
    display_name="Storage Account",
    category="Storage",
    parent_type="azurerm_resource_group",
    default_attributes={
        "location": "eastus",
        "account_tier": "Standard",
        "account_replication_type": "LRS",
        "account_kind": "StorageV2",
        "min_tls_version": "TLS1_2",
        "access_tier": "Hot",
        "https_traffic_only_enabled": True,
        "public_network_access_enabled": True,
        "large_file_share_enabled": True,
        "local_user_enabled": True,
        "shared_access_key_enabled": True,
        "blob_container_delete_retention_days": 7,
        "blob_delete_retention_days": 7,
        "share_retention_policy_days": 7,
    },
    generate_provider_name=_storage_account_provider_name,
)

AZURERM_STORAGE_CONTAINER = ResourceTypeDefinition(
    resource_type="azurerm_storage_container",
    prefix="res003",
    display_name="Storage Container",
    category="Storage",
    parent_type="azurerm_storage_account",
    default_attributes={"container_access_type": "private"},
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_STORAGE_ACCOUNT_STATIC_WEBSITE = ResourceTypeDefinition(
    resource_type="azurerm_storage_account_static_website",
    prefix="res00A",
    display_name="Static Website",
    category="Storage",
    parent_type="azurerm_storage_account",
    default_attributes={
        "index_document": "index.html",
        "error_404_document": "404.html",
    },
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_CONTAINER_APP_ENVIRONMENT = ResourceTypeDefinition(
    resource_type="azurerm_container_app_environment",
    prefix="res006",
    display_name="Container App Environment",
    category="Compute",
    parent_type="azurerm_resource_group",
    default_attributes={"location": "eastus"},
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_CONTAINER_APP = ResourceTypeDefinition(
    resource_type="azurerm_container_app",
    prefix="res007",
    display_name="Container App",
    category="Compute",
    parent_type="azurerm_container_app_environment",
    default_attributes={
        "revision_mode": "Single",
        "ingress_external_enabled": True,
        "ingress_target_port": 80,
        "ingress_transport": "auto",
        "ingress_allow_insecure_connections": False,
        "template_min_replicas": 0,
        "template_max_replicas": 1,
        "template_container_cpu": "0.25",
        "template_container_memory": "0.5Gi",
        "template_termination_grace_period_seconds": 30,
        "liveness_probe_transport": "TCP",
        "liveness_probe_port": 80,
        "liveness_probe_interval_seconds": 10,
        "liveness_probe_timeout": 5,
        "liveness_probe_failure_count_threshold": 3,
        "readiness_probe_transport": "TCP",
        "readiness_probe_port": 80,
        "readiness_probe_interval_seconds": 5,
        "readiness_probe_timeout": 5,
        "readiness_probe_failure_count_threshold": 48,
        "readiness_probe_success_count_threshold": 1,
        "startup_probe_transport": "TCP",
        "startup_probe_port": 80,
        "startup_probe_initial_delay": 1,
        "startup_probe_interval_seconds": 1,
        "startup_probe_timeout": 3,
        "startup_probe_failure_count_threshold": 240,
        "configuration_active_revision_mode": "Single",
        "configuration_ingress_external": True,
        "configuration_ingress_target_port": 80,
    },
    generate_provider_name=_azurerm_provider_name,
)

DEPLOYBOXRM_WORKOS_INTEGRATION = ResourceTypeDefinition(
    resource_type="deployboxrm_workos_integration",
    prefix="res008",
    display_name="WorkOS Integration",
    category="Authentication",
    parent_type=None,
    default_attributes={},
    generate_provider_name=_azurerm_provider_name,
)

THENILERM_DATABASE = ResourceTypeDefinition(
    resource_type="thenilerm_database",
    prefix="res009",
    display_name="Nile Database",
    category="Database",
    parent_type=None,
    default_attributes={
        "region": "AZURE_EASTUS",
        "expandable": False,
        "sharded": True,
    },
    generate_provider_name=_nile_provider_name,
)

DEPLOYBOXRM_EDGE = ResourceTypeDefinition(
    resource_type="deployboxrm_edge",
    prefix="res00B",
    display_name="Edge Router",
    category="Networking",
    parent_type=None,
    default_attributes={},
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_LOG_ANALYTICS_WORKSPACE = ResourceTypeDefinition(
    resource_type="azurerm_log_analytics_workspace",
    prefix="res00C",
    display_name="Log Analytics Workspace",
    category="Monitoring",
    parent_type="azurerm_resource_group",
    default_attributes={"location": "eastus"},
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_KEY_VAULT = ResourceTypeDefinition(
    resource_type="azurerm_key_vault",
    prefix="res00D",
    display_name="Key Vault",
    category="Security",
    parent_type="azurerm_resource_group",
    default_attributes={"location": "eastus"},
    generate_provider_name=_azurerm_provider_name,
)

DEPLOYBOXRM_POSTGRES_DATABASE = ResourceTypeDefinition(
    resource_type="deployboxrm_postgres_database",
    prefix="res00E",
    display_name="Postgres Database",
    category="Database",
    parent_type=None,
    default_attributes={
        "db_host": "deploy-box-postgres.postgres.database.azure.com",
        "db_port": 5432,
        "sslmode": "require",
        "status": "pending",
        "region": "eastus",
    },
    generate_provider_name=None,
)

AZURERM_PUBLIC_IP = ResourceTypeDefinition(
    resource_type="azurerm_public_ip",
    prefix="res00F",
    display_name="Public IP",
    category="Networking",
    parent_type="azurerm_resource_group",
    default_attributes={"location": "eastus"},
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_NETWORK_SECURITY_GROUP = ResourceTypeDefinition(
    resource_type="azurerm_network_security_group",
    prefix="res010",
    display_name="Network Security Group",
    category="Networking",
    parent_type="azurerm_resource_group",
    default_attributes={"location": "eastus"},
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_VIRTUAL_NETWORK = ResourceTypeDefinition(
    resource_type="azurerm_virtual_network",
    prefix="res011",
    display_name="Virtual Network",
    category="Networking",
    parent_type="azurerm_resource_group",
    default_attributes={"location": "eastus"},
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_NETWORK_INTERFACE = ResourceTypeDefinition(
    resource_type="azurerm_network_interface",
    prefix="res012",
    display_name="Network Interface",
    category="Networking",
    parent_type="azurerm_resource_group",
    default_attributes={"location": "eastus"},
    generate_provider_name=_azurerm_provider_name,
)

AZURERM_LINUX_VIRTUAL_MACHINE = ResourceTypeDefinition(
    resource_type="azurerm_linux_virtual_machine",
    prefix="res013",
    display_name="Linux Virtual Machine",
    category="Compute",
    parent_type="azurerm_resource_group",
    default_attributes={"location": "eastus"},
    generate_provider_name=_azurerm_provider_name,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ALL_DEFINITIONS: list[ResourceTypeDefinition] = [
    AZURERM_RESOURCE_GROUP,
    AZURERM_STORAGE_ACCOUNT,
    AZURERM_STORAGE_CONTAINER,
    AZURERM_STORAGE_ACCOUNT_STATIC_WEBSITE,
    AZURERM_CONTAINER_APP_ENVIRONMENT,
    AZURERM_CONTAINER_APP,
    DEPLOYBOXRM_WORKOS_INTEGRATION,
    THENILERM_DATABASE,
    DEPLOYBOXRM_EDGE,
    AZURERM_LOG_ANALYTICS_WORKSPACE,
    AZURERM_KEY_VAULT,
    DEPLOYBOXRM_POSTGRES_DATABASE,
    AZURERM_PUBLIC_IP,
    AZURERM_NETWORK_SECURITY_GROUP,
    AZURERM_VIRTUAL_NETWORK,
    AZURERM_NETWORK_INTERFACE,
    AZURERM_LINUX_VIRTUAL_MACHINE,
]


class ResourceTypeRegistry:
    """Central registry for all resource type definitions."""

    _by_type: dict[str, ResourceTypeDefinition] = {}
    _by_prefix: dict[str, ResourceTypeDefinition] = {}

    @classmethod
    def _ensure_loaded(cls) -> None:
        if not cls._by_type:
            for defn in _ALL_DEFINITIONS:
                cls._by_type[defn.resource_type] = defn
                cls._by_prefix[defn.prefix] = defn

    @classmethod
    def get_by_type(cls, resource_type: str) -> ResourceTypeDefinition | None:
        cls._ensure_loaded()
        return cls._by_type.get(resource_type) or cls._by_type.get(resource_type.lower())

    @classmethod
    def get_by_prefix(cls, prefix: str) -> ResourceTypeDefinition | None:
        cls._ensure_loaded()
        return cls._by_prefix.get(prefix)

    @classmethod
    def get_defaults(cls, resource_type: str) -> dict[str, Any]:
        """Get default attributes for a resource type."""
        defn = cls.get_by_type(resource_type)
        return dict(defn.default_attributes) if defn else {}

    @classmethod
    def get_display_name(cls, resource_type: str) -> str:
        defn = cls.get_by_type(resource_type)
        return defn.display_name if defn else resource_type

    @classmethod
    def get_category(cls, resource_type: str) -> str:
        defn = cls.get_by_type(resource_type)
        return defn.category if defn else "Other"

    @classmethod
    def get_parent_type(cls, resource_type: str) -> str | None:
        defn = cls.get_by_type(resource_type)
        return defn.parent_type if defn else None

    @classmethod
    def all_types(cls) -> list[ResourceTypeDefinition]:
        cls._ensure_loaded()
        return list(cls._by_type.values())

    @classmethod
    def all_type_names(cls) -> list[str]:
        cls._ensure_loaded()
        return list(cls._by_type.keys())

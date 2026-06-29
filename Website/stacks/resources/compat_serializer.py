"""Compatibility serializer for the unified Resource model.

Produces output identical to the legacy per-type ModelSerializers (`fields='__all__'`)
so that downstream consumers (IaC container-app) see no change in payload format.

The legacy format flattens ALL model fields to top-level keys including:
- Base fields: id, index, name, type, stack, created_at, updated_at
- Provider fields under their ORIGINAL names (azurerm_id, thenilerm_id, etc.)
- Type-specific fields from the attributes JSONField promoted to top-level
"""
from __future__ import annotations

from stacks.resources.resource import Resource


# Mapping: resource_type → (provider_id_field_name, provider_name_field_name | None)
_PROVIDER_FIELD_MAP: dict[str, tuple[str, str | None]] = {
    "azurerm_resource_group": ("azurerm_id", "azurerm_name"),
    "azurerm_container_app": ("azurerm_id", "azurerm_name"),
    "azurerm_storage_account": ("azurerm_id", "azurerm_name"),
    "azurerm_storage_container": ("azurerm_id", "azurerm_name"),
    "azurerm_dns_cname_record": ("azurerm_id", "azurerm_name"),
    "azurerm_container_app_environment": ("azurerm_id", "azurerm_name"),
    "azurerm_storage_account_static_website": ("azurerm_id", "azurerm_name"),
    "azurerm_log_analytics_workspace": ("azurerm_id", "azurerm_name"),
    "azurerm_key_vault": ("azurerm_id", "azurerm_name"),
    "azurerm_public_ip": ("azurerm_id", "azurerm_name"),
    "azurerm_network_security_group": ("azurerm_id", "azurerm_name"),
    "azurerm_virtual_network": ("azurerm_id", "azurerm_name"),
    "azurerm_network_interface": ("azurerm_id", "azurerm_name"),
    "azurerm_linux_virtual_machine": ("azurerm_id", "azurerm_name"),
    "thenilerm_database": ("thenilerm_id", "thenilerm_name"),
    "deployboxrm_workos_integration": (None, None),
    "deployboxrm_edge": (None, None),
    "deployboxrm_postgres_database": ("deploybox_database_id", None),
}


def serialize_resource_compat(resource: Resource) -> dict:
    """Serialize a unified Resource instance to match the legacy flat format.

    Output format is identical to what `PerTypeSerializer(fields='__all__').data`
    would produce, allowing IaC and other consumers to work unchanged.
    """
    rt = resource.resource_type
    provider_id_field, provider_name_field = _PROVIDER_FIELD_MAP.get(rt, (None, None))

    # Start with base fields (matching BaseResourceModel's __all__)
    data: dict = {
        "id": resource.pk,
        "index": resource.index,
        "name": resource.name,
        "type": "RESOURCE",  # BaseResourceModel.type default
        "stack": str(resource.stack_id),
        "created_at": (
            resource.created_at.isoformat() if resource.created_at else None
        ),
        "updated_at": (
            resource.updated_at.isoformat() if resource.updated_at else None
        ),
    }

    # Add provider_id under its original field name
    if provider_id_field:
        data[provider_id_field] = resource.provider_id or ""

    # Add provider_name under its original field name
    if provider_name_field:
        data[provider_name_field] = resource.provider_name or ""

    # Add promoted fields that are stored directly on Resource
    # (not in attributes) but need to appear in legacy output
    if rt.startswith("azurerm") or rt in ("thenilerm_database", "deployboxrm_postgres_database"):
        data["location"] = resource.location or ""

    if hasattr(resource, "status") and resource.status:
        data["status"] = resource.status

    # Flatten attributes to top-level (type-specific fields)
    if resource.attributes:
        data.update(resource.attributes)

    # Add tags if the type has a tags field (most azurerm types do)
    if rt.startswith("azurerm") or rt == "thenilerm_database":
        data.setdefault("tags", resource.tags or {})

    return data


def serialize_resources_compat(resources) -> list[dict]:
    """Serialize a queryset or list of Resource instances to legacy format."""
    return [serialize_resource_compat(r) for r in resources]

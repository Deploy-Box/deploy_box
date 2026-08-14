"""ResourcesManager — unified CRUD for all stack resources.

Phase 4: All resources live in the single ``Resource`` table. The 17 legacy
per-type tables have been dropped. Type-specific configuration lives in
``Resource.attributes`` (JSONField). The ``ResourceTypeRegistry`` provides
per-type defaults, naming logic, and parent mapping.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, overload

from django.conf import settings
from django.db import models
from django.db.models import Max

from stacks.resources.resource import Resource
from stacks.resources.type_registry import ResourceTypeRegistry

if TYPE_CHECKING:
    from stacks.models import Stack

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Supported resource types (derived from the registry)
# ---------------------------------------------------------------------------

def _build_type_map() -> dict[str, str]:
    """UPPERCASE key → lowercase resource_type for all registered types."""
    return {
        defn.resource_type.upper(): defn.resource_type
        for defn in ResourceTypeRegistry.all_types()
    }


RESOURCE_MANAGER_MAPPING: dict[str, str] = _build_type_map()
"""Backwards-compatible mapping: UPPERCASE key → lowercase resource_type.

Used by serializers for ChoiceField validation and by views for type listings.
"""

RESOURCE_TYPE_DISPLAY_NAMES: dict[str, str] = {
    defn.resource_type.upper(): defn.display_name
    for defn in ResourceTypeRegistry.all_types()
}

RESOURCE_TYPE_CATEGORIES: dict[str, str] = {
    defn.resource_type.upper(): defn.category
    for defn in ResourceTypeRegistry.all_types()
}


# ---------------------------------------------------------------------------
# Type-specific creation hooks
# ---------------------------------------------------------------------------

def _prepare_edge_attributes(stack: "Stack", index: int, attrs: dict) -> dict:
    """Auto-generate subdomain and resolved_root_base_url for edge resources."""
    if not attrs.get("subdomain"):
        attrs["subdomain"] = f"{stack.pk}{index}"
    if not attrs.get("resolved_root_base_url"):
        host = getattr(settings, "HOST", os.getenv("HOST", "https://deploybox.io"))
        attrs["resolved_root_base_url"] = f"{host}/still-configuring/"
    if "root_base_url" not in attrs:
        attrs["root_base_url"] = ""
    if "api_base_url" not in attrs:
        attrs["api_base_url"] = ""
    if "resolved_api_base_url" not in attrs:
        attrs["resolved_api_base_url"] = ""
    return attrs


def _prepare_container_app_attributes(stack: "Stack", index: int, attrs: dict) -> dict:
    """Auto-generate template_container_name for container apps."""
    if not attrs.get("template_container_name"):
        attrs["template_container_name"] = f"container-{stack.pk}"
    return attrs


def _prepare_storage_account_attributes(stack: "Stack", index: int, attrs: dict) -> dict:
    """Inject resource_group_name Terraform reference for the parent resource group."""
    if not attrs.get("resource_group_name"):
        # Find the parent resource group's name to build the reference
        rg = Resource.objects.filter(
            stack=stack, resource_type="azurerm_resource_group"
        ).first()
        if rg:
            attrs["resource_group_name"] = (
                f"${{azurerm_resource_group.{rg.name}.azurerm_name}}"
            )
    return attrs


def _prepare_static_website_attributes(stack: "Stack", index: int, attrs: dict) -> dict:
    """Inject storage_account_id Terraform reference for the parent storage account."""
    if not attrs.get("storage_account_id"):
        sa = Resource.objects.filter(
            stack=stack, resource_type="azurerm_storage_account"
        ).first()
        if sa:
            attrs["storage_account_id"] = (
                f"${{azurerm_storage_account.{sa.name}.azurerm_id}}"
            )
    return attrs


_CREATION_HOOKS: dict[str, Any] = {
    "deployboxrm_edge": _prepare_edge_attributes,
    "azurerm_container_app": _prepare_container_app_attributes,
    "azurerm_storage_account": _prepare_storage_account_attributes,
    "azurerm_storage_account_static_website": _prepare_static_website_attributes,
}


# ---------------------------------------------------------------------------
# ResourcesManager — public API
# ---------------------------------------------------------------------------

class ResourcesManager:

    @staticmethod
    def create(resources: list[dict], stack: "Stack") -> list[Resource]:
        """Create multiple resources from a stack infrastructure definition.

        Each entry in *resources* is a dict with at minimum ``resource_type``
        and optionally type-specific field overrides.
        """
        created_resources: list[Resource] = []

        for idx, resource_data in enumerate(resources):
            assert isinstance(resource_data, dict), (
                f"Expected resource to be a dict, got {type(resource_data)}"
            )

            resource_type_raw = resource_data.get("resource_type", "")
            assert isinstance(resource_type_raw, str) and resource_type_raw, (
                "resource_type must be a non-empty string"
            )

            key = resource_type_raw.upper()
            rt = RESOURCE_MANAGER_MAPPING.get(key)
            if rt is None:
                raise ValueError(f"Unknown resource type: {resource_type_raw}")

            defn = ResourceTypeRegistry.get_by_type(rt)
            assert defn is not None

            # Merge: registry defaults → provided overrides
            attributes = dict(defn.default_attributes)
            SKIP_KEYS = {"resource_type", "stack", "index", "name"}
            for k, v in resource_data.items():
                if k not in SKIP_KEYS:
                    attributes[k] = v

            # Run type-specific creation hook
            hook = _CREATION_HOOKS.get(rt)
            if hook:
                attributes = hook(stack, idx, attributes)

            # Infer parent
            parent = None
            if defn.parent_type:
                parent = Resource.objects.filter(
                    stack=stack, resource_type=defn.parent_type
                ).first()

            resource = Resource(
                stack=stack,
                index=idx,
                resource_type=rt,
                prefix=defn.prefix,
                parent=parent,
                location=attributes.pop("location", "") or "",
                status=attributes.pop("status", "") or "",
                tags=attributes.pop("tags", {}) or {},
                attributes=attributes,
            )
            resource.save()  # triggers provider_name + name auto-gen
            created_resources.append(resource)

        return created_resources

    @staticmethod
    def add_resource(stack: "Stack", resource_type: str, config: dict | None = None) -> Resource:
        """Add a single resource to an existing stack.

        Returns the newly created Resource instance.
        Raises ``ValueError`` if *resource_type* is unknown.
        """
        key = resource_type.upper()
        rt = RESOURCE_MANAGER_MAPPING.get(key)
        if rt is None:
            raise ValueError(f"Unknown resource type: {resource_type}")

        defn = ResourceTypeRegistry.get_by_type(rt)
        assert defn is not None

        # Use Max(index)+1 to avoid collisions after deletions
        max_index = Resource.objects.filter(
            stack=stack, resource_type=rt
        ).aggregate(mi=Max("index"))["mi"]
        next_index = (max_index + 1) if max_index is not None else 0

        # Merge defaults + config
        attributes = dict(defn.default_attributes)
        if config:
            for k, v in config.items():
                if k not in {"resource_type", "stack", "index", "name"}:
                    attributes[k] = v

        # Run type-specific creation hook
        hook = _CREATION_HOOKS.get(rt)
        if hook:
            attributes = hook(stack, next_index, attributes)

        # Infer parent
        parent = None
        if defn.parent_type:
            parent = Resource.objects.filter(
                stack=stack, resource_type=defn.parent_type
            ).first()

        resource = Resource(
            stack=stack,
            index=next_index,
            name=f"{defn.display_name} {next_index + 1}",
            resource_type=rt,
            prefix=defn.prefix,
            parent=parent,
            location=attributes.pop("location", "") or "",
            status=attributes.pop("status", "") or "",
            tags=attributes.pop("tags", {}) or {},
            attributes=attributes,
        )
        resource.save()
        return resource

    @staticmethod
    def remove_resource(resource_id: str) -> bool:
        """Delete a single resource by ID.

        Returns ``True`` if deleted, ``False`` if not found.
        Note: if the resource has children (via parent FK), they will also
        be deleted due to on_delete=CASCADE.
        """
        deleted_count, _ = Resource.objects.filter(pk=resource_id).delete()
        return deleted_count > 0

    @staticmethod
    def get_available_resource_types() -> list[dict[str, str]]:
        """Return a catalogue of resource types that can be added to a stack."""
        return [
            {
                "resource_type": key,
                "display_name": RESOURCE_TYPE_DISPLAY_NAMES[key],
                "category": RESOURCE_TYPE_CATEGORIES[key],
            }
            for key in RESOURCE_MANAGER_MAPPING
        ]

    @staticmethod
    def get_from_stack(stack: "Stack") -> list[Resource]:
        """Return all resources for a stack (single query)."""
        return list(
            Resource.objects.filter(stack=stack)
            .select_related("parent")
            .order_by("index")
        )

    @staticmethod
    def _read_one(resource_id: str) -> Resource | None:
        return Resource.objects.filter(pk=resource_id).first()

    @overload
    @staticmethod
    def read(resource_id: str) -> Resource | None: ...

    @overload
    @staticmethod
    def read(resource_id: list[str]) -> list[Resource | None]: ...

    @staticmethod
    def read(resource_id: str | list[str]) -> Resource | list[Resource | None] | None:
        if isinstance(resource_id, list):
            return [ResourcesManager._read_one(rid) for rid in resource_id]
        return ResourcesManager._read_one(resource_id)

    @staticmethod
    def delete(stack: "Stack"):
        """Delete all resources for a stack."""
        Resource.objects.filter(stack=stack).delete()

    @staticmethod
    def serialize(resource: Resource | list[Resource]):
        """Serialize resources to the flat legacy dict format."""
        from stacks.resources.compat_serializer import serialize_resource_compat

        if isinstance(resource, list):
            return [serialize_resource_compat(r) for r in resource]
        return serialize_resource_compat(resource)

    @staticmethod
    def update_resource(resource_id: str, update_data: dict) -> Resource | None:
        """Update a resource from a flat dict (e.g. IaC callback payload).

        Maps promoted fields (provider_id, location, status, etc.) to model
        columns and stores everything else in attributes.
        """
        resource = ResourcesManager._read_one(resource_id)
        if resource is None:
            return None

        from stacks.resources.compat_serializer import _PROVIDER_FIELD_MAP

        rt = resource.resource_type
        provider_id_field, provider_name_field = _PROVIDER_FIELD_MAP.get(rt, (None, None))

        # Promoted fields that map to real columns
        PROMOTED_COLUMNS = {"location", "status", "tags"}
        SKIP_KEYS = {"id", "stack", "index", "type", "created_at", "updated_at"}

        attrs = dict(resource.attributes) if resource.attributes else {}

        for k, v in update_data.items():
            if k in SKIP_KEYS:
                continue
            elif k == "name":
                resource.name = v
            elif k in PROMOTED_COLUMNS:
                setattr(resource, k, v)
            elif provider_id_field and k == provider_id_field:
                resource.provider_id = v or ""
            elif provider_name_field and k == provider_name_field:
                resource.provider_name = v or ""
            else:
                attrs[k] = v

        resource.attributes = attrs
        resource.save()
        return resource

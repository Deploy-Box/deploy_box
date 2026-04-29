"""Data migration: populate unified Resource table from existing 17 resource tables.

Iterates all old-style resource model tables and copies rows into the
stacks_resource table, inferring parent relationships from ResourceTypeRegistry.
"""
from django.db import migrations


# Mapping from old model's db_table (or app_label + model name) to resource_type
MODEL_TYPE_MAP = [
    ("stacks_azurermresourcegroup", "azurerm_resource_group", "res000"),
    ("stacks_azurermstorageaccount", "azurerm_storage_account", "res002"),
    ("stacks_azurermstoragecontainer", "azurerm_storage_container", "res003"),
    ("stacks_azurermdnscnamerecord", "azurerm_dns_cname_record", "res004"),
    ("stacks_azurermstorageaccountstaticwebsite", "azurerm_storage_account_static_website", "res005"),
    ("stacks_azurermcontainerappenvironment", "azurerm_container_app_environment", "res006"),
    ("stacks_azurermcontainerapp", "azurerm_container_app", "res007"),
    ("stacks_deployboxrmworkosintegration", "deployboxrm_workos_integration", "res008"),
    ("stacks_deployboxrmedge", "deployboxrm_edge", "res009"),
    ("stacks_azurermloganalyticsworkspace", "azurerm_log_analytics_workspace", "res00A"),
    ("stacks_azurermkeyvault", "azurerm_key_vault", "res00B"),
    ("stacks_azurermpublicip", "azurerm_public_ip", "res00C"),
    ("stacks_deployboxrmpostgresdatabase", "deployboxrm_postgres_database", "res00D"),
    ("stacks_azurermnetworksecuritygroup", "azurerm_network_security_group", "res00E"),
    ("stacks_azurermvirtualnetwork", "azurerm_virtual_network", "res00F"),
    ("stacks_azurermnetworkinterface", "azurerm_network_interface", "res010"),
    ("stacks_azurermlinuxvirtualmachine", "azurerm_linux_virtual_machine", "res011"),
]

# Parent type lookup: child_type → parent_type
PARENT_TYPE_MAP = {
    "azurerm_storage_container": "azurerm_storage_account",
    "azurerm_storage_account_static_website": "azurerm_storage_account",
    "azurerm_container_app": "azurerm_container_app_environment",
    "azurerm_container_app_environment": "azurerm_resource_group",
    "azurerm_key_vault": "azurerm_resource_group",
    "azurerm_log_analytics_workspace": "azurerm_resource_group",
    "azurerm_public_ip": "azurerm_resource_group",
    "azurerm_network_security_group": "azurerm_resource_group",
    "azurerm_virtual_network": "azurerm_resource_group",
    "azurerm_network_interface": "azurerm_resource_group",
    "azurerm_linux_virtual_machine": "azurerm_resource_group",
    "azurerm_storage_account": "azurerm_resource_group",
    "azurerm_dns_cname_record": "azurerm_resource_group",
}

# Fields that are common/promoted to Resource columns (not put into attributes)
COMMON_FIELDS = {"id", "index", "name", "type", "stack_id", "created_at", "updated_at"}
PROVIDER_ID_FIELDS = {"azurerm_id", "thenilerm_id", "deploybox_database_id"}
PROVIDER_NAME_FIELDS = {"azurerm_name", "thenilerm_name"}
PROMOTED_FIELDS = PROVIDER_ID_FIELDS | PROVIDER_NAME_FIELDS | {"location", "status", "tags"}


def populate_resources(apps, schema_editor):
    """Copy all rows from the 17 old resource tables into the unified Resource table."""
    from django.db import connection

    Resource = apps.get_model("stacks", "Resource")
    db_vendor = connection.vendor  # 'sqlite' or 'postgresql'

    # First pass: create all Resource rows (without parent)
    created_resources = {}  # {pk: resource_type}

    for db_table, resource_type, prefix in MODEL_TYPE_MAP:
        # Check if the old table exists (database-agnostic)
        with connection.cursor() as cursor:
            if db_vendor == "sqlite":
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=%s",
                    [db_table],
                )
            else:
                cursor.execute(
                    "SELECT tablename FROM pg_tables WHERE tablename=%s",
                    [db_table],
                )
            if not cursor.fetchone():
                continue

            # Get column names and rows
            if db_vendor == "sqlite":
                cursor.execute(f"PRAGMA table_info({db_table})")
                columns = [row[1] for row in cursor.fetchall()]
            else:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name=%s ORDER BY ordinal_position",
                    [db_table],
                )
                columns = [row[0] for row in cursor.fetchall()]

            # Read all rows
            cursor.execute(f'SELECT * FROM "{db_table}"')
            rows = cursor.fetchall()

        for row in rows:
            row_dict = dict(zip(columns, row))

            # Extract provider_id
            provider_id = ""
            for field in PROVIDER_ID_FIELDS:
                if field in row_dict and row_dict[field]:
                    provider_id = row_dict[field]
                    break

            # Extract provider_name
            provider_name = ""
            for field in PROVIDER_NAME_FIELDS:
                if field in row_dict and row_dict[field]:
                    provider_name = row_dict[field]
                    break

            # Build attributes from remaining fields
            attributes = {}
            for col, val in row_dict.items():
                if col in COMMON_FIELDS or col in PROMOTED_FIELDS:
                    continue
                if val is not None and val != "" and val != "[]" and val != "{}":
                    attributes[col] = val

            Resource.objects.update_or_create(
                pk=row_dict["id"],
                defaults={
                    "stack_id": row_dict["stack_id"],
                    "index": row_dict.get("index", 0),
                    "name": row_dict.get("name", ""),
                    "resource_type": resource_type,
                    "prefix": prefix,
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "location": row_dict.get("location", "") or "",
                    "status": row_dict.get("status", "") or "",
                    "tags": row_dict.get("tags", {}) if isinstance(row_dict.get("tags"), dict) else {},
                    "attributes": attributes,
                },
            )
            created_resources[row_dict["id"]] = resource_type

    # Second pass: set parent relationships
    for pk, resource_type in created_resources.items():
        parent_type = PARENT_TYPE_MAP.get(resource_type)
        if not parent_type:
            continue

        try:
            resource = Resource.objects.get(pk=pk)
            parent = Resource.objects.filter(
                stack_id=resource.stack_id,
                resource_type=parent_type,
            ).first()
            if parent:
                resource.parent = parent
                resource.save(update_fields=["parent"])
        except Resource.DoesNotExist:
            pass


def reverse_populate(apps, schema_editor):
    """Clear all rows from the unified Resource table."""
    Resource = apps.get_model("stacks", "Resource")
    Resource.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stacks", "0032_unified_resource_model"),
    ]

    operations = [
        migrations.RunPython(populate_resources, reverse_populate),
    ]

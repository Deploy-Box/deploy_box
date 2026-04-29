"""Data migration: create a "Static Website (React)" PurchasableStack."""

from django.db import migrations


STACK_INFRASTRUCTURE = [
    {"resource_type": "AZURERM_RESOURCE_GROUP"},
    {"resource_type": "AZURERM_STORAGE_ACCOUNT"},
    {
        "resource_type": "AZURERM_STORAGE_ACCOUNT_STATIC_WEBSITE",
        "static_file_directory": ".",
        "static_file_build_command": "npm install && npm run build",
        "static_file_build_output_directory": "build",
        "index_document": "index.html",
        "error_404_document": "index.html",
    },
    {"resource_type": "DEPLOYBOXRM_EDGE"},
]


def create_static_stack(apps, schema_editor):
    PurchasableStack = apps.get_model("stacks", "PurchasableStack")
    PurchasableStack.objects.get_or_create(
        type="STATIC",
        variant="BASIC",
        version="1.0",
        defaults={
            "name": "Static Website (React)",
            "description": (
                "Deploy a React single-page application on Azure Storage "
                "with automatic builds, a custom subdomain via the Deploy Box "
                "edge router, and CDN-ready static hosting."
            ),
            "price_id": "price_static_basic",
            "features": [
                "React SPA",
                "Automatic npm build",
                "Azure Storage static hosting",
                "Custom subdomain",
                "SPA routing (404 → index.html)",
                "CDN-ready",
            ],
            "stack_infrastructure": STACK_INFRASTRUCTURE,
            "source_code_location": "",
        },
    )


def remove_static_stack(apps, schema_editor):
    PurchasableStack = apps.get_model("stacks", "PurchasableStack")
    PurchasableStack.objects.filter(
        type="STATIC", variant="BASIC", version="1.0"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("stacks", "0029_rename_stacks_depl_stack_i_idx_stacks_depl_stack_i_78fc88_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(create_static_stack, remove_static_stack),
    ]

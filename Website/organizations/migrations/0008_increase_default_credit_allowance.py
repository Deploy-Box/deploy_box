"""Increase default free-tier credit allowance from $5 to $10."""

from decimal import Decimal
from django.db import migrations, models


def bump_existing_free_tier(apps, schema_editor):
    """Upgrade free-tier orgs still at the old $5 default to $10."""
    Organization = apps.get_model("organizations", "Organization")
    Organization.objects.filter(
        tier="free",
        monthly_credit_allowance=Decimal("5.00"),
    ).update(monthly_credit_allowance=Decimal("10.00"))


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0007_add_billing_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="monthly_credit_allowance",
            field=models.DecimalField(
                decimal_places=2,
                default=10.00,
                help_text="Maximum monthly spend before auto-pause kicks in (dollars).",
                max_digits=10,
            ),
        ),
        migrations.RunPython(bump_existing_free_tier, migrations.RunPython.noop),
    ]

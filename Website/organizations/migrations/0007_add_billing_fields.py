from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0006_alter_organization_stripe_customer_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="monthly_credit_allowance",
            field=models.DecimalField(
                decimal_places=2,
                default=5.00,
                help_text="Maximum monthly spend before auto-pause kicks in (dollars).",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="auto_pause_on_limit",
            field=models.BooleanField(
                default=True,
                help_text="Automatically pause stacks when monthly usage exceeds the credit allowance.",
            ),
        ),
    ]

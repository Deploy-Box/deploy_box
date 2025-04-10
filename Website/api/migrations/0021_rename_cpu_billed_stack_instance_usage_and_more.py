# Generated by Django 5.1.6 on 2025-04-10 13:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_rename_pending_billed_stack_cpu_billed_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='stack',
            old_name='cpu_billed',
            new_name='instance_usage',
        ),
        migrations.RenameField(
            model_name='stack',
            old_name='cpu_usage',
            new_name='instance_usage_bill_amount',
        ),
        migrations.RemoveField(
            model_name='stack',
            name='memory_billed',
        ),
        migrations.RemoveField(
            model_name='stack',
            name='memory_usage',
        ),
    ]

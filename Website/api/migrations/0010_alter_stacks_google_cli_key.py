# Generated by Django 5.1.6 on 2025-03-16 02:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_stacks_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stacks',
            name='google_cli_key',
            field=models.TextField(max_length=2400, null=True),
        ),
    ]

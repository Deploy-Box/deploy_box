# Generated by Django 5.1.6 on 2025-04-09 01:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_remove_stack_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='stack',
            name='pending_billed',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='stack',
            name='usage',
            field=models.IntegerField(default=0),
        ),
    ]

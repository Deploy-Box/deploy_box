# Generated by Django 5.1.6 on 2025-04-03 00:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('github', '0003_remove_webhookevents_repository_webhookevents_stack'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='webhookevents',
            name='event_type',
        ),
    ]

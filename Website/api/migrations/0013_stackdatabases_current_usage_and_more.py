# Generated by Django 5.1.6 on 2025-03-28 23:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_availablestacks_price_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='stackdatabases',
            name='current_usage',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='stackdatabases',
            name='pending_billed',
            field=models.IntegerField(default=0),
        ),
    ]

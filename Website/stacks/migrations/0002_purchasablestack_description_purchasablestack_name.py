# Generated by Django 5.1.6 on 2025-04-24 00:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stacks', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchasablestack',
            name='description',
            field=models.CharField(default='check out this stack'),
        ),
        migrations.AddField(
            model_name='purchasablestack',
            name='name',
            field=models.CharField(default='this is a stack'),
        ),
    ]

# Generated by Django 5.1.6 on 2025-06-25 04:00

import core.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('stacks', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Token',
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('encrypted_token', models.BinaryField()),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Webhook',
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('repository', models.CharField(max_length=255)),
                ('webhook_id', models.IntegerField(unique=True)),
                ('url', models.URLField()),
                ('secret', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('stack', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stacks.stack')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

# Generated by Django 5.1.6 on 2025-04-03 02:20

import core.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_organization_organizationmember_project_and_more'),
        ('api', '0013_stackdatabases_current_usage_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AvailableStack',
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('type', models.CharField(max_length=10)),
                ('variant', models.CharField(max_length=10)),
                ('version', models.CharField(max_length=10)),
                ('price_id', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='stacks',
            name='purchased_stack',
        ),
        migrations.RemoveField(
            model_name='stackbackends',
            name='stack',
        ),
        migrations.RemoveField(
            model_name='stackdatabases',
            name='stack',
        ),
        migrations.RemoveField(
            model_name='stackfrontends',
            name='stack',
        ),
        migrations.RemoveField(
            model_name='stacks',
            name='user',
        ),
        migrations.CreateModel(
            name='Stack',       
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.project')),
                ('purchased_stack', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api.availablestack')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='StackBackend',
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('url', models.URLField()),
                ('image_url', models.URLField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('stack', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.stack')),
            ],
        ),
        migrations.CreateModel(
            name='StackDatabase',
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('uri', models.URLField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('current_usage', models.IntegerField(default=0)),
                ('pending_billed', models.IntegerField(default=0)),
                ('stack', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.stack')),
            ],
        ),
        migrations.CreateModel(
            name='StackFrontend',
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('url', models.URLField()),
                ('image_url', models.URLField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('stack', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.stack')),
            ],
        ),
        migrations.DeleteModel(
            name='AvailableStacks',
        ),
        migrations.DeleteModel(
            name='StackBackends',
        ),
        migrations.DeleteModel(
            name='StackDatabases',
        ),
        migrations.DeleteModel(
            name='StackFrontends',
        ),
    ]

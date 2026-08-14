# Generated manually

import core.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stacks', '0027_add_deployment_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='Operation',
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('operation_type', models.CharField(choices=[('APPLY', 'Apply'), ('DELETE', 'Delete'), ('PAUSE', 'Pause'), ('RESUME', 'Resume'), ('DEPLOY', 'Deploy')], max_length=20)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('RUNNING', 'Running'), ('SUCCEEDED', 'Succeeded'), ('FAILED', 'Failed'), ('TIMED_OUT', 'Timed Out')], default='PENDING', max_length=20)),
                ('error_message', models.TextField(blank=True, default='')),
                ('attempt_id', models.CharField(blank=True, default='', help_text='Unique token set by the claiming worker to prove ownership.', max_length=64)),
                ('lease_expires_at', models.DateTimeField(blank=True, help_text='If RUNNING and this time is passed, the operation is considered stuck.', null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('stack', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operations', to='stacks.stack')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['stack', '-created_at'], name='stacks_oper_stack_i_idx'),
                    models.Index(fields=['status', 'created_at'], name='stacks_oper_status_idx'),
                ],
            },
        ),
    ]

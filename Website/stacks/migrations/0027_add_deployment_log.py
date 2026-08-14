# Generated manually

import core.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stacks', '0026_azurermlinuxvirtualmachine_azurermnetworkinterface_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeploymentLog',
            fields=[
                ('id', core.fields.ShortUUIDField(editable=False, max_length=16, primary_key=True, serialize=False, unique=True)),
                ('operation', models.CharField(choices=[('APPLY', 'Apply'), ('DELETE', 'Delete'), ('PAUSE', 'Pause'), ('RESUME', 'Resume')], max_length=20)),
                ('status', models.CharField(choices=[('RUNNING', 'Running'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='RUNNING', max_length=20)),
                ('log_text', models.TextField(blank=True, default='')),
                ('line_count', models.IntegerField(default=0)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(null=True, blank=True)),
                ('stack', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deployment_logs', to='stacks.stack')),
            ],
            options={
                'ordering': ['-started_at'],
                'indexes': [
                    models.Index(fields=['stack', '-started_at'], name='stacks_depl_stack_i_idx'),
                ],
            },
        ),
    ]

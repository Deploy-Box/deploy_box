# Generated by Django 5.1.6 on 2025-04-10 00:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_alter_userprofile_id'),
        ('api', '0017_stack_pending_billed_stack_usage'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='stack',
            constraint=models.UniqueConstraint(fields=('project', 'name'), name='unique_stack_name_per_project'),
        ),
    ]

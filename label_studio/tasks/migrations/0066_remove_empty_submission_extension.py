from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0065_remove_skip_reason_fields'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='annotation',
            name='task_comple_is_empt_b0c283_idx',
        ),
        migrations.RemoveField(
            model_name='annotation',
            name='is_empty_submission',
        ),
        migrations.AlterField(
            model_name='taskworkflowauditlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('submitted', 'Submitted'),
                    ('skipped', 'Skipped'),
                ],
                help_text='Workflow action type',
                max_length=32,
            ),
        ),
    ]

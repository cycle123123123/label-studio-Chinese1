from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0063_annotation_skip_reason_and_workflow_audit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskworkflowauditlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('submitted', 'Submitted'),
                    ('skipped', 'Skipped'),
                    ('empty_submitted', 'Empty Submitted'),
                ],
                help_text='Workflow action type',
                max_length=32,
            ),
        ),
    ]
